# -*- coding: utf-8 -*-
"""Tests for repo agent templates and workspace initialization."""
from pathlib import Path
import sys
import types

import json

fake_google = types.ModuleType("google")
fake_genai = types.ModuleType("google.genai")
fake_genai.Client = object
fake_genai_errors = types.ModuleType("google.genai.errors")
fake_genai_errors.APIError = Exception
fake_genai_types = types.ModuleType("google.genai.types")
fake_genai_types.HttpOptions = object
fake_genai.types = fake_genai_types
fake_google.genai = fake_genai
sys.modules.setdefault("google", fake_google)
sys.modules.setdefault("google.genai", fake_genai)
sys.modules.setdefault("google.genai.errors", fake_genai_errors)
sys.modules.setdefault("google.genai.types", fake_genai_types)

from copaw.config.config import (
    AgentProfileConfig,
    AgentProfileRef,
    AgentsConfig,
    Config,
    IntegrationRef,
    OutputPrefsConfig,
    RepoAssetRef,
    load_agent_config,
    save_agent_config,
)
from copaw.config import utils as config_utils
from copaw.config import config as config_module
from copaw.agents.utils.setup_utils import collect_md_files_for_template
from copaw.app.agents_workspace import (
    default_skills_for_template,
    initialize_agent_workspace,
)


def _write_root_config(config_path: Path, workspace_dir: Path, agent_id: str) -> None:
    root_config = Config(
        agents=AgentsConfig(
            active_agent=agent_id,
            profiles={
                agent_id: AgentProfileRef(
                    id=agent_id,
                    workspace_dir=str(workspace_dir),
                ),
            },
        ),
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as file:
        json.dump(root_config.model_dump(exclude_none=True), file)


def test_repo_agent_profile_persists_template_assets_and_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Repo agent metadata should round-trip through agent.json."""
    agent_id = "dev-agent"
    workspace_dir = tmp_path / "workspaces" / agent_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_utils, "WORKING_DIR", tmp_path)
    monkeypatch.setattr(config_module, "WORKING_DIR", tmp_path)
    _write_root_config(config_path, workspace_dir, agent_id)

    agent_config = AgentProfileConfig(
        id=agent_id,
        name="Developer Agent",
        template_id="developer",
        module_id="codeops",
        repo_assets=[
            RepoAssetRef(
                id="my-repo",
                name="demo",
                local_path="/tmp/demo",
                remote_url="git@github.com:owner/demo.git",
            ),
        ],
        integrations=[
            IntegrationRef(
                id="chainos-runtime",
                kind="chainos",
                name="chainOS Runtime",
            ),
        ],
        output_prefs=OutputPrefsConfig(
            inbox_enabled=True,
            summary_to_chat=True,
            digest_enabled=True,
            approvals_enabled=True,
        ),
    )

    save_agent_config(agent_id, agent_config)
    reloaded = load_agent_config(agent_id)

    assert reloaded.template_id == "developer"
    assert reloaded.module_id == "codeops"
    assert reloaded.repo_assets[0].name == "demo"
    assert reloaded.repo_assets[0].remote_url.endswith("demo.git")
    assert reloaded.integrations[0].kind == "chainos"
    assert reloaded.output_prefs.inbox_enabled is True
    assert reloaded.output_prefs.approvals_enabled is True


def test_initialize_developer_workspace_creates_repo_prompt_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """developer template should seed repo-specific prompt files."""
    agent_id = "dev-agent"
    workspace_dir = tmp_path / "workspaces" / agent_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_utils, "WORKING_DIR", tmp_path)
    monkeypatch.setattr(config_module, "WORKING_DIR", tmp_path)
    _write_root_config(config_path, workspace_dir, agent_id)

    agent_config = AgentProfileConfig(
        id=agent_id,
        name="Developer Agent",
        template_id="developer",
        module_id="codeops",
        repo_assets=[
            RepoAssetRef(
                id="my-repo",
                name="demo",
                local_path="/tmp/demo",
            ),
        ],
    )

    initialize_agent_workspace(workspace_dir, agent_config)

    assert (workspace_dir / "REPO.md").exists()
    assert (workspace_dir / "OUTPUTS.md").exists()
    repo_text = (workspace_dir / "REPO.md").read_text(encoding="utf-8")
    assert "工作区" in repo_text or "Workspace" in repo_text
    assert "/tmp/demo" in repo_text

    ag_dev = (workspace_dir / "AGENTS.md").read_text(encoding="utf-8")
    assert "仓库优先" in ag_dev

    active = {p.name for p in (workspace_dir / "active_skills").iterdir() if p.is_dir()}
    assert "git_workflow" in active
    assert "pptx" not in active
    assert default_skills_for_template("developer") is not None


def test_initialize_oss_researcher_workspace_creates_research_prompt_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """oss_researcher template should seed research + repo stubs."""
    agent_id = "research-agent"
    workspace_dir = tmp_path / "workspaces" / agent_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_utils, "WORKING_DIR", tmp_path)
    monkeypatch.setattr(config_module, "WORKING_DIR", tmp_path)
    _write_root_config(config_path, workspace_dir, agent_id)

    agent_config = AgentProfileConfig(
        id=agent_id,
        name="OSS Researcher",
        template_id="oss_researcher",
        module_id="general",
        repo_assets=[],
    )

    initialize_agent_workspace(workspace_dir, agent_config)

    assert (workspace_dir / "RESEARCH.md").exists()
    assert (workspace_dir / "REPO.md").exists()
    assert (workspace_dir / "OUTPUTS.md").exists()
    # oss_researcher uses full builtin skill set (no allowlist)
    active = {p.name for p in (workspace_dir / "active_skills").iterdir() if p.is_dir()}
    assert "pptx" in active or "pdf" in active


def test_legacy_chainos_template_id_coerced_to_developer_on_load(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Old template_id values in agent.json map to developer when loading."""
    agent_id = "legacy-agent"
    workspace_dir = tmp_path / "workspaces" / agent_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_utils, "WORKING_DIR", tmp_path)
    monkeypatch.setattr(config_module, "WORKING_DIR", tmp_path)
    _write_root_config(config_path, workspace_dir, agent_id)

    base = AgentProfileConfig(
        id=agent_id,
        name="Legacy",
        template_id="developer",
        module_id="codeops",
        workspace_dir=str(workspace_dir),
    )
    raw = base.model_dump()
    raw["template_id"] = "chainos_agent"
    agent_json = workspace_dir / "agent.json"
    with open(agent_json, "w", encoding="utf-8") as f:
        json.dump(raw, f)

    loaded = load_agent_config(agent_id)
    assert loaded.template_id == "developer"


def test_collect_md_files_zh_developer_overlays_general() -> None:
    """developer template should pick AGENTS.md from zh/developer/."""
    files = collect_md_files_for_template("zh", "developer")
    assert "AGENTS.md" in files
    content = files["AGENTS.md"].read_text(encoding="utf-8")
    assert "仓库优先" in content
