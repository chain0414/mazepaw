# -*- coding: utf-8 -*-
"""Multi-agent management API.

Provides RESTful API for managing multiple agent instances.
"""
import asyncio
import logging
import os
import subprocess
from pathlib import Path
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi import Path as PathParam
from pydantic import BaseModel, Field

from ...config.config import (
    AgentProfileConfig,
    AgentProfileRef,
    AgentTemplateId,
    IntegrationRef,
    OutputPrefsConfig,
    RepoAssetRef,
    load_agent_config,
    save_agent_config,
    generate_short_agent_id,
)
from ...config.utils import load_config, save_config
from ...agents.memory.agent_md_manager import AgentMdManager
from ..agents_workspace import (
    default_system_prompt_files_for_template,
    initialize_agent_workspace,
    refresh_developer_repo_md,
)
from ..multi_agent_manager import MultiAgentManager
from ...constant import WORKING_DIR
from ...config.git_credential_env import merge_git_credential_env_for_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentSummary(BaseModel):
    """Agent summary information."""

    id: str
    name: str
    description: str
    workspace_dir: str
    module_id: str = "general"
    template_id: str = "general"
    repo_count: int = 0


class AgentListResponse(BaseModel):
    """Response for listing agents."""

    agents: list[AgentSummary]


class CreateAgentRequest(BaseModel):
    """Request model for creating a new agent (id is auto-generated)."""

    name: str
    description: str = ""
    workspace_dir: str | None = None
    language: str = "en"
    module_id: str = "general"
    template_id: AgentTemplateId = "general"
    repo_assets: list[RepoAssetRef] = Field(default_factory=list)
    integrations: list[IntegrationRef] = Field(default_factory=list)
    output_prefs: OutputPrefsConfig = Field(default_factory=OutputPrefsConfig)
    git_credential_id: str = ""


class MdFileInfo(BaseModel):
    """Markdown file metadata."""

    filename: str
    path: str
    size: int
    created_time: str
    modified_time: str


class MdFileContent(BaseModel):
    """Markdown file content."""

    content: str


class RepoConnectivityEntry(BaseModel):
    """Optional git remote reachability probe for one bound repo."""

    repo_id: str
    local_path: str
    reachable: bool | None = None
    message: str = ""


def _probe_repo_remote(
    repo: RepoAssetRef,
    agent_cfg: AgentProfileConfig | None = None,
) -> tuple[bool | None, str]:
    """Return (reachable, message). ``None`` means skipped or inconclusive."""
    p = Path(repo.local_path).expanduser()
    if not (p / ".git").exists():
        return False, "not a git repository"
    url = (repo.remote_url or "").strip()
    env = os.environ.copy()
    merge_git_credential_env_for_agent(env, agent_cfg)
    if not url:
        try:
            r = subprocess.run(
                ["git", "-C", str(p), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
                env=env,
            )
            if r.returncode != 0:
                return None, "no remote_url and no git remote named origin"
            url = (r.stdout or "").strip()
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)[:200]
    try:
        r = subprocess.run(
            ["git", "-C", str(p), "ls-remote", "--heads", url],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        if r.returncode == 0:
            return True, ""
        err = (r.stderr or r.stdout or "ls-remote failed").strip()
        return False, err[:500]
    except subprocess.TimeoutExpired:
        return False, "timeout after 15s"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:500]


def _validate_repo_local_paths(repo_assets: list[RepoAssetRef]) -> None:
    """Ensure each bound ``local_path`` exists on disk and is a Git checkout."""
    for r in repo_assets:
        lp = (r.local_path or "").strip()
        if not lp:
            raise HTTPException(
                status_code=400,
                detail="repo_assets[].local_path must not be empty when repo is listed",
            )
        path = Path(lp).expanduser()
        if not path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"local_path does not exist or is not a directory: {lp}",
            )
        if not (path / ".git").exists():
            raise HTTPException(
                status_code=400,
                detail=f"local_path is not a Git repository (missing .git): {lp}",
            )


def _validate_git_credential(agent_config: AgentProfileConfig) -> None:
    """Ensure git_credential_id references a git credential profile."""
    cid = (agent_config.git_credential_id or "").strip()
    if not cid:
        return
    config = load_config()
    for p in config.credentials.profiles:
        if p.id == cid:
            if p.type != "git":
                raise HTTPException(
                    status_code=400,
                    detail="Credential profile must have type git",
                )
            return
    raise HTTPException(status_code=400, detail=f"Unknown credential id: {cid}")


def _apply_template_defaults(agent_config: AgentProfileConfig) -> AgentProfileConfig:
    """Normalize template-derived fields before saving."""
    if agent_config.template_id == "developer":
        agent_config.module_id = "codeops"
        if not agent_config.system_prompt_files:
            agent_config.system_prompt_files = default_system_prompt_files_for_template(
                "developer",
            )
    elif agent_config.template_id == "oss_researcher":
        agent_config.module_id = "general"
        if not agent_config.system_prompt_files:
            agent_config.system_prompt_files = default_system_prompt_files_for_template(
                "oss_researcher",
            )
    return agent_config


def _get_multi_agent_manager(request: Request) -> MultiAgentManager:
    """Get MultiAgentManager from app state."""
    if not hasattr(request.app.state, "multi_agent_manager"):
        raise HTTPException(
            status_code=500,
            detail="MultiAgentManager not initialized",
        )
    return request.app.state.multi_agent_manager


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List all agents",
    description="Get list of all configured agents",
)
async def list_agents() -> AgentListResponse:
    """List all configured agents."""
    config = load_config()

    agents = []
    for agent_id, agent_ref in config.agents.profiles.items():
        # Load agent config to get name and description
        try:
            agent_config = load_agent_config(agent_id)
            agents.append(
                AgentSummary(
                    id=agent_id,
                    name=agent_config.name,
                    description=agent_config.description,
                    workspace_dir=agent_ref.workspace_dir,
                    module_id=agent_config.module_id,
                    template_id=agent_config.template_id,
                    repo_count=len(agent_config.repo_assets),
                ),
            )
        except Exception:  # noqa: E722
            # If agent config load fails, use basic info
            agents.append(
                AgentSummary(
                    id=agent_id,
                    name=agent_id.title(),
                    description="",
                    workspace_dir=agent_ref.workspace_dir,
                    module_id="general",
                    template_id="general",
                    repo_count=0,
                ),
            )

    return AgentListResponse(
        agents=agents,
    )


@router.get(
    "/{agentId}",
    response_model=AgentProfileConfig,
    summary="Get agent details",
    description="Get complete configuration for a specific agent",
)
async def get_agent(agentId: str = PathParam(...)) -> AgentProfileConfig:
    """Get agent configuration."""
    try:
        agent_config = load_agent_config(agentId)
        return agent_config
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "",
    response_model=AgentProfileRef,
    status_code=201,
    summary="Create new agent",
    description="Create a new agent (ID is auto-generated by server)",
)
async def create_agent(
    request: CreateAgentRequest = Body(...),
) -> AgentProfileRef:
    """Create a new agent with auto-generated ID."""
    config = load_config()

    # Always generate a unique short UUID (6 characters)
    max_attempts = 10
    new_id = None
    for _ in range(max_attempts):
        candidate_id = generate_short_agent_id()
        if candidate_id not in config.agents.profiles:
            new_id = candidate_id
            break

    if new_id is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate unique agent ID after 10 attempts",
        )

    # Create workspace directory
    workspace_dir = Path(
        request.workspace_dir or f"{WORKING_DIR}/workspaces/{new_id}",
    ).expanduser()
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Build complete agent config with generated ID
    from ...config.config import (
        ChannelConfig,
        MCPConfig,
        HeartbeatConfig,
        ToolsConfig,
    )

    agent_config = AgentProfileConfig(
        id=new_id,
        name=request.name,
        description=request.description,
        workspace_dir=str(workspace_dir),
        language=request.language,
        module_id=request.module_id,
        template_id=request.template_id,
        repo_assets=request.repo_assets,
        integrations=request.integrations,
        output_prefs=request.output_prefs,
        git_credential_id=request.git_credential_id or "",
        system_prompt_files=default_system_prompt_files_for_template(
            request.template_id,
        ),
        channels=ChannelConfig(),
        mcp=MCPConfig(),
        heartbeat=HeartbeatConfig(),
        tools=ToolsConfig(),
    )
    agent_config = _apply_template_defaults(agent_config)
    _validate_git_credential(agent_config)
    if request.repo_assets:
        _validate_repo_local_paths(request.repo_assets)

    # Initialize workspace with default files
    initialize_agent_workspace(workspace_dir, agent_config)
    if agent_config.template_id == "developer":
        refresh_developer_repo_md(workspace_dir, agent_config)

    # Save agent configuration to workspace/agent.json
    agent_ref = AgentProfileRef(
        id=new_id,
        workspace_dir=str(workspace_dir),
    )

    # Add to root config
    config.agents.profiles[new_id] = agent_ref
    save_config(config)

    # Save agent config to workspace
    save_agent_config(new_id, agent_config)

    logger.info(f"Created new agent: {new_id} (name={request.name})")

    return agent_ref


@router.put(
    "/{agentId}",
    response_model=AgentProfileConfig,
    summary="Update agent",
    description="Update agent configuration and trigger reload",
)
async def update_agent(
    agentId: str = PathParam(...),
    agent_config: AgentProfileConfig = Body(...),
    request: Request = None,
) -> AgentProfileConfig:
    """Update agent configuration."""
    config = load_config()

    if agentId not in config.agents.profiles:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agentId}' not found",
        )

    # Ensure ID doesn't change
    agent_config.id = agentId
    agent_config = _apply_template_defaults(agent_config)
    _validate_git_credential(agent_config)
    if agent_config.repo_assets:
        _validate_repo_local_paths(agent_config.repo_assets)

    # Save agent configuration
    save_agent_config(agentId, agent_config)
    if agent_config.template_id == "developer":
        refresh_developer_repo_md(
            Path(agent_config.workspace_dir).expanduser(),
            agent_config,
        )

    # Trigger hot reload if agent is running (async, non-blocking)
    # IMPORTANT: Get manager before creating background task to avoid
    # accessing request object after its lifecycle ends
    manager = _get_multi_agent_manager(request)

    async def reload_in_background():
        try:
            await manager.reload_agent(agentId)
        except Exception as e:
            logger.warning(f"Background reload failed for {agentId}: {e}")

    asyncio.create_task(reload_in_background())

    return agent_config


@router.delete(
    "/{agentId}",
    summary="Delete agent",
    description="Delete agent and workspace (cannot delete default agent)",
)
async def delete_agent(
    agentId: str = PathParam(...),
    request: Request = None,
) -> dict:
    """Delete an agent."""
    config = load_config()

    if agentId not in config.agents.profiles:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agentId}' not found",
        )

    if agentId == "default":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the default agent",
        )

    # Stop agent instance if running
    manager = _get_multi_agent_manager(request)
    await manager.stop_agent(agentId)

    # Remove from config
    del config.agents.profiles[agentId]
    save_config(config)

    # Note: We don't delete the workspace directory for safety
    # Users can manually delete it if needed

    return {"success": True, "agent_id": agentId}


@router.get(
    "/{agentId}/repo-connectivity",
    response_model=list[RepoConnectivityEntry],
    summary="Probe remote reachability for bound repos",
    description=(
        "Runs ``git ls-remote`` per bound repository (optional; may be slow). "
        "Uses ``remote_url`` when set, otherwise ``origin`` from the checkout."
    ),
)
async def repo_connectivity(agentId: str = PathParam(...)) -> list[RepoConnectivityEntry]:
    """Best-effort remote connectivity check for developer agent repos."""
    try:
        agent_config = load_agent_config(agentId)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    out: list[RepoConnectivityEntry] = []
    for repo in agent_config.repo_assets:
        ok, msg = _probe_repo_remote(repo, agent_config)
        out.append(
            RepoConnectivityEntry(
                repo_id=repo.id,
                local_path=repo.local_path,
                reachable=ok,
                message=msg,
            ),
        )
    return out


@router.get(
    "/{agentId}/files",
    response_model=list[MdFileInfo],
    summary="List agent workspace files",
    description="List all markdown files in agent's workspace",
)
async def list_agent_files(
    agentId: str = PathParam(...),
    request: Request = None,
) -> list[MdFileInfo]:
    """List agent workspace files."""
    manager = _get_multi_agent_manager(request)

    try:
        workspace = await manager.get_agent(agentId)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    workspace_manager = AgentMdManager(str(workspace.workspace_dir))

    try:
        files = [
            MdFileInfo.model_validate(file)
            for file in workspace_manager.list_working_mds()
        ]
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{agentId}/files/{filename}",
    response_model=MdFileContent,
    summary="Read agent workspace file",
    description="Read a markdown file from agent's workspace",
)
async def read_agent_file(
    agentId: str = PathParam(...),
    filename: str = PathParam(...),
    request: Request = None,
) -> MdFileContent:
    """Read agent workspace file."""
    manager = _get_multi_agent_manager(request)

    try:
        workspace = await manager.get_agent(agentId)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    workspace_manager = AgentMdManager(str(workspace.workspace_dir))

    try:
        content = workspace_manager.read_working_md(filename)
        return MdFileContent(content=content)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found",
        ) from exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put(
    "/{agentId}/files/{filename}",
    response_model=dict,
    summary="Write agent workspace file",
    description="Create or update a markdown file in agent's workspace",
)
async def write_agent_file(
    agentId: str = PathParam(...),
    filename: str = PathParam(...),
    file_content: MdFileContent = Body(...),
    request: Request = None,
) -> dict:
    """Write agent workspace file."""
    manager = _get_multi_agent_manager(request)

    try:
        workspace = await manager.get_agent(agentId)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    workspace_manager = AgentMdManager(str(workspace.workspace_dir))

    try:
        workspace_manager.write_working_md(filename, file_content.content)
        return {"written": True, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{agentId}/memory",
    response_model=list[MdFileInfo],
    summary="List agent memory files",
    description="List all memory files for an agent",
)
async def list_agent_memory(
    agentId: str = PathParam(...),
    request: Request = None,
) -> list[MdFileInfo]:
    """List agent memory files."""
    manager = _get_multi_agent_manager(request)

    try:
        workspace = await manager.get_agent(agentId)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    workspace_manager = AgentMdManager(str(workspace.workspace_dir))

    try:
        files = [
            MdFileInfo.model_validate(file)
            for file in workspace_manager.list_memory_mds()
        ]
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
