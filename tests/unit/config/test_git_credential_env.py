# -*- coding: utf-8 -*-
"""Tests for git credential env merging."""

from copaw.config.config import CredentialProfile
from copaw.config.git_credential_env import merge_git_credential_profile_into_env


def test_merge_sets_author_from_git_identity() -> None:
    env: dict[str, str] = {}
    profile = CredentialProfile(
        id="x",
        type="git",
        auth_method="ssh_key_path",
        secret_ref="",
        git_user_name="Ada",
        git_user_email="ada@example.com",
    )
    merge_git_credential_profile_into_env(env, profile)
    assert env.get("GIT_AUTHOR_NAME") == "Ada"
    assert env.get("GIT_COMMITTER_NAME") == "Ada"
    assert env.get("GIT_AUTHOR_EMAIL") == "ada@example.com"
    assert env.get("GIT_COMMITTER_EMAIL") == "ada@example.com"


def test_merge_ssh_key_with_identity(tmp_path, monkeypatch) -> None:
    """SSH key path + commit identity."""
    key = tmp_path / "k"
    key.write_text("x", encoding="utf-8")
    env: dict[str, str] = {}
    profile = CredentialProfile(
        id="x",
        type="git",
        auth_method="ssh_key_path",
        secret_ref=str(key),
        git_user_name="B",
        git_user_email="b@example.com",
    )
    merge_git_credential_profile_into_env(env, profile)
    assert "GIT_SSH_COMMAND" in env
    assert "GIT_AUTHOR_NAME" in env


def test_merge_token_env(monkeypatch) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    env: dict[str, str] = {}
    profile = CredentialProfile(
        id="x",
        type="git",
        auth_method="token_env",
        secret_ref="MY_TOKEN",
    )
    merge_git_credential_profile_into_env(env, profile)
    assert env.get("GITHUB_TOKEN") == "tok"
    assert env.get("GIT_TERMINAL_PROMPT") == "0"
