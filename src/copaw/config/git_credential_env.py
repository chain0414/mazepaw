# -*- coding: utf-8 -*-
"""Apply git credential profiles to subprocess environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import AgentProfileConfig, CredentialProfile


def merge_git_credential_profile_into_env(
    env: dict[str, str],
    profile: "CredentialProfile",
) -> None:
    """Inject SSH/token and optional commit identity from a git credential profile."""
    auth = (profile.auth_method or "secret_ref").lower()
    ref = (profile.secret_ref or "").strip()

    if ref:
        if auth in ("ssh_key_env", "ssh_key_path"):
            key_path: str | None = None
            exp = Path(ref).expanduser()
            if exp.is_file():
                key_path = str(exp)
            elif ref in os.environ:
                cand = Path(os.environ[ref]).expanduser()
                if cand.is_file():
                    key_path = str(cand)
            if key_path:
                safe = key_path.replace('"', '\\"')
                env["GIT_SSH_COMMAND"] = (
                    f'ssh -i "{safe}" -o IdentitiesOnly=yes '
                    f"-o StrictHostKeyChecking=accept-new"
                )
        elif auth in ("token_env", "github_token", "secret_ref"):
            token = os.environ.get(ref, "")
            if token:
                env["GIT_TERMINAL_PROMPT"] = "0"
                env["GITHUB_TOKEN"] = token

    name = (profile.git_user_name or "").strip()
    email = (profile.git_user_email or "").strip()
    if name:
        env["GIT_AUTHOR_NAME"] = name
        env["GIT_COMMITTER_NAME"] = name
    if email:
        env["GIT_AUTHOR_EMAIL"] = email
        env["GIT_COMMITTER_EMAIL"] = email


def merge_git_credential_env_for_agent(
    env: dict[str, str],
    agent_cfg: "AgentProfileConfig | None",
) -> None:
    """Load agent-bound git credential from config and merge into ``env``."""
    if agent_cfg is None:
        return
    cid = (agent_cfg.git_credential_id or "").strip()
    if not cid:
        return
    from .utils import load_config

    cfg = load_config()
    profile = next((p for p in cfg.credentials.profiles if p.id == cid), None)
    if not profile or profile.type != "git":
        return
    merge_git_credential_profile_into_env(env, profile)
