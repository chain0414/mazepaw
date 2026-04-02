# -*- coding: utf-8 -*-
"""Git helpers for developer agents: propose commit card payload and server-side commit."""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

from ...constant import WORKING_DIR
from ...config.config import AgentProfileConfig
from ...config.context import get_current_workspace_dir
from ...config.git_credential_env import merge_git_credential_env_for_agent
from .shell import (
    _resolve_default_cwd_for_shell,
    _try_load_agent_profile_from_workspace,
)

logger = logging.getLogger(__name__)

SCHEMA_V1 = "copaw_git_propose_commit_v1"
MAX_DIFF_BYTES = 50 * 1024


def _build_agent_env(agent_cfg: AgentProfileConfig | None) -> dict[str, str]:
    env = os.environ.copy()
    python_bin_dir = str(Path(sys.executable).parent)
    existing_path = env.get("PATH", "")
    if existing_path:
        env["PATH"] = python_bin_dir + os.pathsep + existing_path
    else:
        env["PATH"] = python_bin_dir
    merge_git_credential_env_for_agent(env, agent_cfg)
    return env


def _sync_git_exec(
    repo: Path,
    args: list[str],
    env: dict[str, str],
    timeout: int = 120,
) -> tuple[int, str, str]:
    cmd = ["git", "-C", str(repo), *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "git command timed out"
    except Exception as e:  # noqa: BLE001
        return -1, "", str(e)


async def _git_exec(
    repo: Path,
    args: list[str],
    env: dict[str, str],
    timeout: int = 120,
) -> tuple[int, str, str]:
    if sys.platform == "win32":
        return await asyncio.to_thread(_sync_git_exec, repo, args, env, timeout)

    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(repo),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "git command timed out"
    stdout = stdout_b.decode("utf-8", errors="replace") if stdout_b else ""
    stderr = stderr_b.decode("utf-8", errors="replace") if stderr_b else ""
    return proc.returncode or 0, stdout, stderr


def _parse_numstat(text: str) -> dict[str, tuple[int, int]]:
    stats: dict[str, tuple[int, int]] = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add_s, del_s, path = parts[0], parts[1], parts[2]
        try:
            additions = 0 if add_s == "-" else int(add_s)
            deletions = 0 if del_s == "-" else int(del_s)
        except ValueError:
            additions, deletions = 0, 0
        if path not in stats:
            stats[path] = (0, 0)
        oa, od = stats[path]
        stats[path] = (oa + additions, od + deletions)
    return stats


def _status_char_from_porcelain(xy: str) -> str:
    """Map first two status chars to a single display status."""
    if xy == "??":
        return "?"
    # staged in first column
    idx = xy[0] if xy[0] != " " and xy[0] != "?" else ""
    wk = xy[1] if xy[1] != " " else ""
    if idx == "R" or wk == "R":
        return "R"
    if idx == "A" or (wk == "A" and not idx):
        return "A"
    if idx == "D" or wk == "D":
        return "D"
    if idx or wk:
        return "M"
    return "M"


def _parse_porcelain_paths(status_out: str) -> list[tuple[str, str, str]]:
    """Return list of (xy, path, display_status)."""
    rows: list[tuple[str, str, str]] = []
    for line in status_out.splitlines():
        if len(line) < 3:
            continue
        xy = line[:2]
        rest = line[3:].strip()
        if " -> " in rest and xy[0] in ("R", "C"):
            # rename: take new name after arrow
            path = rest.split(" -> ", 1)[-1].strip()
        else:
            path = rest
        if not path:
            continue
        rows.append((xy, path, _status_char_from_porcelain(xy)))
    return rows


def _truncate_diff(text: str) -> str:
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_DIFF_BYTES:
        return text
    cut = encoded[: MAX_DIFF_BYTES - 30].decode("utf-8", errors="replace")
    return cut + "\n\n... (diff truncated)"


def _untracked_line_count(repo: Path, rel_path: str) -> tuple[int, int]:
    full = (repo / rel_path).resolve()
    try:
        full.relative_to(repo.resolve())
    except ValueError:
        return 0, 0
    if not full.is_file():
        return 0, 0
    try:
        data = full.read_bytes()
        lines = data.count(b"\n")
        if data and not data.endswith(b"\n"):
            lines += 1
        return lines, 0
    except OSError:
        return 0, 0


async def _diff_for_path(
    repo: Path,
    rel_path: str,
    xy: str,
    env: dict[str, str],
) -> str:
    parts: list[str] = []
    if xy != "??":
        code, out, _ = await _git_exec(repo, ["diff", "--", rel_path], env)
        if code == 0 and out.strip():
            parts.append(out)
        code_s, out_s, _ = await _git_exec(
            repo,
            ["diff", "--cached", "--", rel_path],
            env,
        )
        if code_s == 0 and out_s.strip():
            parts.append(out_s)
    else:
        null = os.devnull
        code, out, err = await _git_exec(
            repo,
            ["diff", "--no-index", "--", null, rel_path],
            env,
        )
        if code in (0, 1) and out.strip():
            parts.append(out)
        elif err:
            # fallback: synthetic
            add, _ = _untracked_line_count(repo, rel_path)
            parts.append(f"--- /dev/null\n+++ b/{rel_path}\n@@ New file @@\n+({add} lines)\n")
    return _truncate_diff("\n".join(parts))


def _build_markdown_summary(
    summary: str,
    files: list[dict[str, Any]],
    total_add: int,
    total_del: int,
) -> str:
    title = summary.strip() or "Git changes"
    lines = [
        f"📋 **Git 变更摘要**: {title}",
        "",
        "| 文件 | 状态 | +行 | -行 |",
        "|------|------|-----|-----|",
    ]
    for f in files:
        lines.append(
            f"| `{f['path']}` | {f['status']} | {f['additions']} | {f['deletions']} |",
        )
    lines.extend(
        [
            "",
            f"**总计**: {len(files)} 个文件, +{total_add} 行, -{total_del} 行",
            "",
            "_请回复 **提交** 以确认提交，或 **放弃** 跳过（控制台用户可使用提交卡片）。_",
        ],
    )
    return "\n".join(lines)


async def propose_git_commit(
    files: Optional[list[str]] = None,
    cwd: Optional[str] = None,
    summary: str = "",
) -> ToolResponse:
    """Collect git status, per-file stats and diffs for the console commit card.

    Also sets ``markdown_summary`` for non-console channels (see renderer).

    Args:
        files: Optional subset of repo-relative paths; if omitted, all changes.
        cwd: Repository root; defaults like ``execute_shell_command``.
        summary: Short description for the suggested commit message.
    """
    workspace_ctx = get_current_workspace_dir()
    if cwd is not None:
        repo = Path(cwd).expanduser().resolve()
    else:
        repo = _resolve_default_cwd_for_shell(workspace_ctx).resolve()

    agent_cfg = (
        _try_load_agent_profile_from_workspace(workspace_ctx)
        if workspace_ctx
        else None
    )
    env = _build_agent_env(agent_cfg)

    if not repo.is_dir():
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=json.dumps(
                        {
                            "schema": SCHEMA_V1,
                            "error": f"Not a directory: {repo}",
                            "repo_path": str(repo),
                            "summary": summary,
                            "files": [],
                            "total_additions": 0,
                            "total_deletions": 0,
                            "markdown_summary": f"错误：路径不存在或不是目录 `{repo}`",
                        },
                        ensure_ascii=False,
                    ),
                ),
            ],
        )

    code, _, stderr = await _git_exec(repo, ["rev-parse", "--git-dir"], env)
    if code != 0:
        err = (stderr or "").strip() or "not a git repository"
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=json.dumps(
                        {
                            "schema": SCHEMA_V1,
                            "error": err,
                            "repo_path": str(repo),
                            "summary": summary,
                            "files": [],
                            "total_additions": 0,
                            "total_deletions": 0,
                            "markdown_summary": f"**Git 错误**（非仓库或无法读取）: {err}",
                        },
                        ensure_ascii=False,
                    ),
                ),
            ],
        )

    _, status_out, _ = await _git_exec(repo, ["status", "--porcelain=v1"], env)
    rows = _parse_porcelain_paths(status_out)
    if not rows:
        payload = {
            "schema": SCHEMA_V1,
            "repo_path": str(repo),
            "summary": summary,
            "files": [],
            "total_additions": 0,
            "total_deletions": 0,
            "markdown_summary": "工作区干净，没有待提交的变更。",
        }
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=json.dumps(payload, ensure_ascii=False),
                ),
            ],
        )

    filter_set = None
    if files:
        filter_set = {f.strip().replace("\\", "/") for f in files if f.strip()}

    def _keep(path: str) -> bool:
        if filter_set is None:
            return True
        norm = path.replace("\\", "/")
        if norm in filter_set:
            return True
        return any(norm.endswith("/" + item) for item in filter_set)

    rows = [(xy, p, st) for xy, p, st in rows if _keep(p)]
    if not rows:
        payload = {
            "schema": SCHEMA_V1,
            "repo_path": str(repo),
            "summary": summary,
            "files": [],
            "total_additions": 0,
            "total_deletions": 0,
            "markdown_summary": "没有与本次请求匹配的文件变更（请检查路径或先保存修改）。",
        }
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=json.dumps(payload, ensure_ascii=False),
                ),
            ],
        )

    _, unstaged_ns, _ = await _git_exec(repo, ["diff", "--numstat"], env)
    _, staged_ns, _ = await _git_exec(repo, ["diff", "--cached", "--numstat"], env)
    num_u = _parse_numstat(unstaged_ns)
    num_s = _parse_numstat(staged_ns)

    file_entries: list[dict[str, Any]] = []
    total_add = 0
    total_del = 0

    for xy, rel_path, disp in rows:
        key = rel_path.replace("\\", "/")
        add_u, del_u = num_u.get(key, (0, 0))
        add_s, del_s = num_s.get(key, (0, 0))
        additions = add_u + add_s
        deletions = del_u + del_s
        if xy == "??" and additions == 0 and deletions == 0:
            additions, deletions = _untracked_line_count(repo, rel_path)

        diff_text = await _diff_for_path(repo, rel_path, xy, env)
        file_entries.append(
            {
                "path": key,
                "status": disp,
                "additions": additions,
                "deletions": deletions,
                "diff": diff_text,
            },
        )
        total_add += additions
        total_del += deletions

    md = _build_markdown_summary(summary, file_entries, total_add, total_del)
    payload = {
        "schema": SCHEMA_V1,
        "repo_path": str(repo),
        "summary": summary,
        "files": file_entries,
        "total_additions": total_add,
        "total_deletions": total_del,
        "markdown_summary": md,
    }
    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text=json.dumps(payload, ensure_ascii=False),
            ),
        ],
    )


def resolve_default_repo_path() -> Path:
    """Default git repo root for current workspace (for API fallback)."""
    workspace_ctx = get_current_workspace_dir()
    if workspace_ctx:
        return _resolve_default_cwd_for_shell(workspace_ctx).resolve()
    return Path(WORKING_DIR).resolve()


async def execute_git_commit(
    repo: Path,
    paths: list[str],
    message: str,
    do_push: bool,
    agent_cfg: AgentProfileConfig | None,
) -> dict[str, Any]:
    """Stage paths, commit, and optionally push. Used by HTTP API."""
    env = _build_agent_env(agent_cfg)
    repo = repo.expanduser().resolve()
    if not message.strip():
        return {"success": False, "error": "commit message is required"}
    code, _, stderr = await _git_exec(repo, ["rev-parse", "--git-dir"], env)
    if code != 0:
        return {
            "success": False,
            "error": (stderr or "not a git repository").strip(),
        }

    root = repo.resolve()

    def _safe_rel(p: str) -> str | None:
        cand = (root / p).resolve()
        try:
            cand.relative_to(root)
        except ValueError:
            return None
        return p.replace("\\", "/")

    rels = []
    for raw in paths:
        s = _safe_rel(raw.strip())
        if s:
            rels.append(s)
    if not rels:
        return {"success": False, "error": "no valid files to commit"}

    for rel in rels:
        code, _, err = await _git_exec(repo, ["add", "--", rel], env)
        if code != 0:
            return {"success": False, "error": f"git add failed: {err or rel}"}

    code, out, err = await _git_exec(
        repo,
        ["commit", "-m", message.strip()],
        env,
    )
    if code != 0:
        return {
            "success": False,
            "error": (err or out or "git commit failed").strip(),
        }

    hc, ho, _ = await _git_exec(repo, ["rev-parse", "HEAD"], env)
    commit_hash = ho.strip() if hc == 0 else ""

    push_msg = ""
    if do_push:
        pc, _, pe = await _git_exec(repo, ["push"], env, timeout=300)
        if pc != 0:
            return {
                "success": False,
                "commit_hash": commit_hash,
                "error": (pe or "git push failed").strip(),
            }
        push_msg = "pushed"

    return {
        "success": True,
        "commit_hash": commit_hash,
        "message": push_msg or "committed",
    }
