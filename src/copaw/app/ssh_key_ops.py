# -*- coding: utf-8 -*-
"""SSH key listing, generation, GitHub connectivity test, and ~/.ssh/config helpers."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

_SSH_DIR_NAME = ".ssh"
_KEY_NAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")
_HOST_ALIAS_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def _ssh_dir() -> Path:
    return Path.home() / _SSH_DIR_NAME


def _ensure_under_ssh(path: Path) -> Path:
    """Resolve path and ensure it stays under ``~/.ssh``."""
    ssh = _ssh_dir().resolve()
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(ssh)
    except ValueError as exc:
        raise ValueError("path must be under ~/.ssh") from exc
    return resolved


class SSHKeyInfo(BaseModel):
    """One SSH public key pair discoverable under ``~/.ssh``."""

    name: str = Field(..., description="Basename without .pub, e.g. id_ed25519_work")
    private_path: str
    public_path: str
    pub_content: str
    comment: str = ""
    key_type: str = ""


def list_ssh_keys() -> list[SSHKeyInfo]:
    """List key pairs: for each ``*.pub`` with a matching private file."""
    ssh = _ssh_dir()
    if not ssh.is_dir():
        return []
    out: list[SSHKeyInfo] = []
    for pub in sorted(ssh.glob("*.pub")):
        priv = pub.with_suffix("")
        if pub == priv:
            continue
        if not priv.is_file():
            continue
        try:
            raw = pub.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not raw:
            continue
        parts = raw.split(None, 2)
        key_type = parts[0] if len(parts) > 0 else ""
        comment = parts[2] if len(parts) > 2 else ""
        out.append(
            SSHKeyInfo(
                name=pub.stem,
                private_path=str(priv),
                public_path=str(pub),
                pub_content=raw + "\n",
                comment=comment,
                key_type=key_type,
            ),
        )
    return out


def generate_ssh_key(
    name: str,
    comment: str = "",
    key_type: str = "ed25519",
) -> SSHKeyInfo:
    """Generate a new key pair under ``~/.ssh`` using ``ssh-keygen``."""
    if not _KEY_NAME_RE.match(name or ""):
        raise ValueError("invalid key name; use letters, digits, ._- only")
    if key_type not in ("ed25519", "rsa"):
        raise ValueError("key_type must be ed25519 or rsa")
    ssh = _ssh_dir()
    ssh.mkdir(mode=0o700, exist_ok=True)
    priv = ssh / name
    pub = ssh / f"{name}.pub"
    if priv.exists() or pub.exists():
        raise ValueError(f"key file already exists: {name}")

    cmd = [
        "ssh-keygen",
        "-t",
        key_type,
        "-f",
        str(priv),
        "-N",
        "",
    ]
    if comment:
        cmd.extend(["-C", comment])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "ssh-keygen failed").strip()
        raise RuntimeError(err[:500])

    raw = pub.read_text(encoding="utf-8").strip()
    parts = raw.split(None, 2)
    kt = parts[0] if len(parts) > 0 else ""
    cmt = parts[2] if len(parts) > 2 else ""
    return SSHKeyInfo(
        name=name,
        private_path=str(priv),
        public_path=str(pub),
        pub_content=raw + "\n",
        comment=cmt,
        key_type=kt,
    )


class SSHTestResult(BaseModel):
    success: bool
    message: str = ""
    github_username: str | None = None


def test_ssh_github(key_path: str, host: str = "github.com") -> SSHTestResult:
    """Run ``ssh -T git@host`` with a specific identity file."""
    if not _HOST_ALIAS_RE.match(host):
        raise ValueError("invalid host")
    p = _ensure_under_ssh(Path(key_path))
    if not p.is_file():
        raise ValueError("private key file not found")

    cmd = [
        "ssh",
        "-T",
        "-i",
        str(p),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "BatchMode=yes",
        f"git@{host}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    combined = combined.strip()

    # GitHub returns 1 on success with message on stderr
    if not combined:
        combined = f"exit {proc.returncode}"

    m = re.search(r"Hi\s+([^!]+)!", combined, re.IGNORECASE)
    username = m.group(1).strip() if m else None
    if username and (
        "successfully authenticated" in combined.lower()
        or "You've successfully authenticated" in combined
    ):
        return SSHTestResult(success=True, message=combined, github_username=username)

    if "permission denied" in combined.lower():
        return SSHTestResult(success=False, message=combined, github_username=None)

    # Some ssh versions put success on stdout
    if username and "authenticated" in combined.lower():
        return SSHTestResult(success=True, message=combined, github_username=username)

    return SSHTestResult(
        success=False,
        message=combined[:2000],
        github_username=username,
    )


class SSHConfigRead(BaseModel):
    content: str
    exists: bool


def read_ssh_config() -> SSHConfigRead:
    """Return full ``~/.ssh/config`` contents."""
    path = _ssh_dir() / "config"
    if not path.is_file():
        return SSHConfigRead(content="", exists=False)
    try:
        return SSHConfigRead(content=path.read_text(encoding="utf-8"), exists=True)
    except OSError as exc:
        raise RuntimeError(str(exc)) from exc


class SSHConfigApplyBlock(BaseModel):
    host_alias: str = Field(..., description="Host entry name, e.g. github.com-work")
    hostname: str = Field(default="github.com")
    identity_file: str = Field(..., description="Path to private key under ~/.ssh")
    user: str = "git"


class SSHConfigApplyResult(BaseModel):
    full_content: str


def apply_ssh_config_block(block: SSHConfigApplyBlock) -> SSHConfigApplyResult:
    """Append a Host block to ``~/.ssh/config`` if the Host name is not already present."""
    if not _HOST_ALIAS_RE.match(block.host_alias):
        raise ValueError("invalid host_alias")
    if not _HOST_ALIAS_RE.match(block.hostname):
        raise ValueError("invalid hostname")
    ident = Path(block.identity_file).expanduser()
    if not ident.is_absolute():
        ident = _ssh_dir() / block.identity_file
    ident = _ensure_under_ssh(ident)
    if not ident.is_file():
        raise ValueError("identity_file must exist under ~/.ssh")

    ssh = _ssh_dir()
    ssh.mkdir(mode=0o700, exist_ok=True)
    cfg_path = ssh / "config"

    ident_str = str(ident)
    if ident_str.startswith(str(Path.home())):
        ident_str = f"~{ident_str[len(str(Path.home())):]}"

    block_text = (
        f"\nHost {block.host_alias}\n"
        f"  HostName {block.hostname}\n"
        f"  User {block.user}\n"
        f"  IdentityFile {ident_str}\n"
        f"  IdentitiesOnly yes\n"
    )

    existing = ""
    if cfg_path.is_file():
        existing = cfg_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^\s*Host\s+{re.escape(block.host_alias)}\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    if pattern.search(existing):
        raise ValueError(
            f"Host {block.host_alias}\n"
            f" already exists in ~/.ssh/config; remove it manually or pick another alias.",
        )

    new_content = existing.rstrip() + block_text
    if not new_content.endswith("\n"):
        new_content += "\n"
    cfg_path.write_text(new_content, encoding="utf-8")
    return SSHConfigApplyResult(full_content=cfg_path.read_text(encoding="utf-8"))
