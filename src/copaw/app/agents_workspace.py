# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from ..agents.utils.setup_utils import collect_md_files_for_template
from ..config import load_config as load_global_config
from ..config.config import AgentProfileConfig, AgentTemplateId
from .insights.bootstrap import ensure_governance_files

logger = logging.getLogger(__name__)


def default_system_prompt_files_for_template(
    template_id: AgentTemplateId,
) -> list[str]:
    """Return prompt files loaded by default for the template."""
    if template_id == "general":
        return ["AGENTS.md", "SOUL.md", "PROFILE.md"]
    if template_id == "developer":
        return [
            "AGENTS.md",
            "SOUL.md",
            "PROFILE.md",
            "REPO.md",
            "OUTPUTS.md",
        ]
    if template_id == "oss_researcher":
        return [
            "AGENTS.md",
            "SOUL.md",
            "PROFILE.md",
            "RESEARCH.md",
            "OUTPUTS.md",
        ]
    return ["AGENTS.md", "SOUL.md", "PROFILE.md"]


def default_skills_for_template(
    template_id: AgentTemplateId,
) -> list[str] | None:
    """Return builtin skill names to seed for this template.

    ``None`` means copy every builtin skill (general / oss_researcher default).
    """
    if template_id == "developer":
        return [
            "git_workflow",
            "code_review",
            "dev_planning",
            "testing",
            "guidance",
            "cron",
            "browser_visible",
            "file_reader",
        ]
    return None


def _build_repo_md(agent_config: AgentProfileConfig) -> str:
    lang = (agent_config.language or "en").lower()
    is_zh = lang.startswith("zh")

    if is_zh:
        header = "# 仓库上下文"
        intro = "\n".join(
            [
                "## 重要：工作区 vs 仓库",
                "",
                "- **工作区**（本 agent 的 workspace 目录）是你的「家」：存放 memory/、sessions/、active_skills/、agent.json 等运行态与记忆。",
                "- **下面列出的本地路径**才是「工作现场」：代码、Git、构建与测试应默认在这些目录下进行。",
                "- 当用户提到「仓库」「代码」「项目」「改代码」时，**优先**使用绑定仓库的 **Local path**，不要把工作区根目录当成代码根目录。",
                "- 执行 `git`、构建、测试等命令前，先 `cd` 到对应仓库的本地路径（或在该路径下调用工具）。",
                "",
            ],
        )
        no_repo = "\n".join(
            [
                "## 尚未绑定仓库",
                "",
                "- 请引导用户在控制台为该 agent 绑定仓库（本地克隆路径 + 可选远程 URL）。",
                "- 绑定前避免对不存在的路径执行仓库级操作。",
                "",
            ],
        )
        repo_heading = "绑定仓库"
        labels = {
            "id": "仓库 ID",
            "local": "本地路径（代码默认在此目录操作）",
            "remote": "远程 URL",
            "remote_na": "未配置",
        }
    else:
        header = "# Repo context"
        intro = "\n".join(
            [
                "## Workspace vs repository",
                "",
                "- **Workspace** (this agent's workspace directory) is your home: memory/, sessions/, active_skills/, agent.json, etc.",
                "- **Local paths below** are where code lives: prefer these for Git, build, and tests.",
                '- When the user says "repo", "code", "project", or "the codebase", use the **Local path** bindings — not the workspace root as the code root.',
                "- Before `git`, build, or test commands, `cd` into the repo path (or run tools with that cwd).",
                "",
            ],
        )
        no_repo = "\n".join(
            [
                "## No bound repositories yet",
                "",
                "- Ask the user to bind a repository (local checkout path + optional remote) in settings.",
                "- Avoid repo-wide operations until a path is configured.",
                "",
            ],
        )
        repo_heading = "Bound repositories"
        labels = {
            "id": "Repo ID",
            "local": "Local path (default cwd for code work)",
            "remote": "Remote URL",
            "remote_na": "not configured",
        }

    repo_lines: list[str] = []
    for repo in agent_config.repo_assets:
        remote_line = (
            f"- {labels['remote']}: `{repo.remote_url}`"
            if repo.remote_url
            else f"- {labels['remote']}: {labels['remote_na']}"
        )
        repo_lines.extend(
            [
                f"### {repo.name}",
                f"- {labels['id']}: `{repo.id}`",
                f"- {labels['local']}: `{repo.local_path}`",
                remote_line,
                "",
            ],
        )

    if not repo_lines:
        body = no_repo
    else:
        body = f"## {repo_heading}\n\n" + "\n".join(repo_lines).strip() + "\n"

    single_repo_hint = ""
    if len(agent_config.repo_assets) == 1:
        only = agent_config.repo_assets[0]
        lp = only.local_path
        if is_zh:
            single_repo_hint = "\n".join(
                [
                    "## 单仓库时的默认工作目录",
                    "",
                    f"- 本 agent 仅绑定 **一个** 仓库：`execute_shell_command` 在未指定 `cwd` 时，"
                    f"**默认**在该仓库的本地路径下执行：`{lp}`",
                    "- 仍可在单次调用中传入 `cwd` 覆盖。",
                    "",
                ],
            )
        else:
            single_repo_hint = "\n".join(
                [
                    "## Default cwd when only one repo is bound",
                    "",
                    f"- This agent has **one** bound repo: when `cwd` is omitted, "
                    f"`execute_shell_command` **defaults** to that checkout: `{lp}`",
                    "- You can still pass `cwd` on a single call to override.",
                    "",
                ],
            )

    parts = [header, "", intro.strip(), "", body.strip()]
    if single_repo_hint:
        parts.extend(["", single_repo_hint.strip()])
    return "\n".join(parts).strip()


def refresh_developer_repo_md(
    workspace_dir: Path,
    agent_config: AgentProfileConfig,
) -> None:
    """Rewrite REPO.md from current ``repo_assets`` (developer template)."""
    if agent_config.template_id != "developer":
        return
    repo_file = workspace_dir / "REPO.md"
    repo_file.write_text(_build_repo_md(agent_config), encoding="utf-8")


def _build_outputs_md(agent_config: AgentProfileConfig) -> str:
    output_prefs = agent_config.output_prefs
    return "\n".join(
        [
            "# Output Delivery",
            "",
            "Deliver concise progress summaries in chat and persist structured results for inbox-compatible views when enabled.",
            "",
            f"- Inbox enabled: `{str(output_prefs.inbox_enabled).lower()}`",
            f"- Summary to chat: `{str(output_prefs.summary_to_chat).lower()}`",
            f"- Digest enabled: `{str(output_prefs.digest_enabled).lower()}`",
            f"- Approvals enabled: `{str(output_prefs.approvals_enabled).lower()}`",
            "",
            "- Use digest-style outputs for summaries and discoveries.",
            "- Use review-queue outputs for actions that require explicit user approval.",
        ],
    ).strip()


def _build_research_md(agent_config: AgentProfileConfig) -> str:
    """Default research workflow hints for oss_researcher template."""
    return "\n".join(
        [
            "# Open-source research",
            "",
            "You discover and summarize notable open-source projects and trends.",
            "",
            "- Prefer the built-in `oss_research_discovery` skill under `active_skills/`.",
            "- Use GitHub API / MCP tools when configured; respect rate limits.",
            "- Write digest items that map to inbox outputs (daily digest) when cron runs.",
            "",
            f"- Bound Git credential (if any): `{agent_config.git_credential_id or 'none'}`",
        ],
    ).strip()


def _seed_repo_agent_workspace(
    workspace_dir: Path,
    agent_config: AgentProfileConfig,
) -> None:
    outputs_file = workspace_dir / "OUTPUTS.md"
    if not outputs_file.exists():
        outputs_file.write_text(_build_outputs_md(agent_config), encoding="utf-8")

    if agent_config.template_id == "developer":
        repo_file = workspace_dir / "REPO.md"
        if not repo_file.exists():
            repo_file.write_text(_build_repo_md(agent_config), encoding="utf-8")
        return

    if agent_config.template_id == "oss_researcher":
        research_file = workspace_dir / "RESEARCH.md"
        if not research_file.exists():
            research_file.write_text(_build_research_md(agent_config), encoding="utf-8")
        repo_file = workspace_dir / "REPO.md"
        if not repo_file.exists():
            repo_file.write_text(_build_repo_md(agent_config), encoding="utf-8")


def initialize_agent_workspace(
    workspace_dir: Path,
    agent_config: AgentProfileConfig,
) -> None:
    """Initialize agent workspace (similar to copaw init --defaults)."""
    (workspace_dir / "sessions").mkdir(exist_ok=True)
    (workspace_dir / "memory").mkdir(exist_ok=True)
    (workspace_dir / "active_skills").mkdir(exist_ok=True)
    (workspace_dir / "customized_skills").mkdir(exist_ok=True)

    config = load_global_config()
    language = config.agents.language or "zh"

    template_id = agent_config.template_id
    file_map = collect_md_files_for_template(language, template_id)
    for name, md_file in sorted(file_map.items()):
        target_file = workspace_dir / name
        if not target_file.exists():
            try:
                shutil.copy2(md_file, target_file)
            except Exception as exc:
                logger.warning("Failed to copy %s: %s", name, exc)

    heartbeat_file = workspace_dir / "HEARTBEAT.md"
    if not heartbeat_file.exists():
        default_heartbeat_mds = {
            "zh": """# Heartbeat checklist
- 扫描收件箱紧急邮件
- 查看未来 2h 的日历
- 检查待办是否卡住
- 若安静超过 8h，轻量 check-in
""",
            "en": """# Heartbeat checklist
- Scan inbox for urgent email
- Check calendar for next 2h
- Check tasks for blockers
- Light check-in if quiet for 8h
""",
            "ru": """# Heartbeat checklist
- Проверить входящие на срочные письма
- Просмотреть календарь на ближайшие 2 часа
- Проверить задачи на наличие блокировок
- Лёгкая проверка при отсутствии активности более 8 часов
""",
        }
        heartbeat_content = default_heartbeat_mds.get(
            language,
            default_heartbeat_mds["en"],
        )
        heartbeat_file.write_text(heartbeat_content.strip(), encoding="utf-8")

    builtin_skills_dir = Path(__file__).parent.parent / "agents" / "skills"
    skill_allowlist = default_skills_for_template(agent_config.template_id)
    if builtin_skills_dir.exists():
        for skill_dir in builtin_skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                if skill_allowlist is not None and skill_dir.name not in skill_allowlist:
                    continue
                target_skill_dir = workspace_dir / "active_skills" / skill_dir.name
                if not target_skill_dir.exists():
                    try:
                        shutil.copytree(skill_dir, target_skill_dir)
                    except Exception as exc:
                        logger.warning(
                            "Failed to copy skill %s: %s",
                            skill_dir.name,
                            exc,
                        )

    jobs_file = workspace_dir / "jobs.json"
    if not jobs_file.exists():
        jobs_file.write_text(
            json.dumps({"version": 1, "jobs": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    chats_file = workspace_dir / "chats.json"
    if not chats_file.exists():
        chats_file.write_text(
            json.dumps({"version": 1, "chats": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    token_usage_file = workspace_dir / "token_usage.json"
    if not token_usage_file.exists():
        token_usage_file.write_text("[]", encoding="utf-8")

    ensure_governance_files(workspace_dir)

    if agent_config.template_id != "general":
        _seed_repo_agent_workspace(workspace_dir, agent_config)
