# -*- coding: utf-8 -*-
"""Credential profiles API (global, stored in root config.json)."""

from fastapi import APIRouter, Body, HTTPException
from fastapi import Path as PathParam
from pydantic import BaseModel, Field

from ...config.config import CredentialProfile, CredentialType, generate_short_agent_id
from ...config.utils import load_config, save_config
from ..ssh_key_ops import (
    SSHConfigApplyBlock,
    SSHConfigApplyResult,
    SSHConfigRead,
    SSHKeyInfo,
    SSHTestResult,
    apply_ssh_config_block,
    generate_ssh_key,
    list_ssh_keys,
    read_ssh_config,
    test_ssh_github,
)

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredentialListResponse(BaseModel):
    profiles: list[CredentialProfile]


class CredentialCreateRequest(BaseModel):
    type: CredentialType
    provider: str = ""
    name: str = ""
    auth_method: str = "secret_ref"
    secret_ref: str = ""
    metadata: dict = Field(default_factory=dict)
    acquisition_notes: str = ""
    git_user_name: str = ""
    git_user_email: str = ""


class SSHKeyGenerateBody(BaseModel):
    name: str
    comment: str = ""
    key_type: str = "ed25519"


class SSHTestBody(BaseModel):
    key_path: str
    host: str = "github.com"


def _only_git_mutations(ctype: CredentialType) -> None:
    if ctype != "git":
        raise HTTPException(
            status_code=400,
            detail="Only git credential profiles can be created or updated in this version",
        )


@router.get("", response_model=CredentialListResponse)
async def list_credentials() -> CredentialListResponse:
    config = load_config()
    return CredentialListResponse(profiles=list(config.credentials.profiles))


@router.get("/ssh-keys", response_model=list[SSHKeyInfo])
async def get_ssh_keys() -> list[SSHKeyInfo]:
    """List SSH public key pairs under ``~/.ssh``."""
    return list_ssh_keys()


@router.post("/ssh-keys/generate", response_model=SSHKeyInfo)
async def post_ssh_keys_generate(body: SSHKeyGenerateBody) -> SSHKeyInfo:
    """Generate a new SSH key pair with ``ssh-keygen``."""
    try:
        return generate_ssh_key(
            name=body.name,
            comment=body.comment,
            key_type=body.key_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ssh-test", response_model=SSHTestResult)
async def post_ssh_test(body: SSHTestBody) -> SSHTestResult:
    """Test ``ssh -T git@host`` with a specific private key."""
    try:
        return test_ssh_github(key_path=body.key_path, host=body.host)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/ssh-config", response_model=SSHConfigRead)
async def get_ssh_config() -> SSHConfigRead:
    """Read ``~/.ssh/config``."""
    try:
        return read_ssh_config()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ssh-config/apply", response_model=SSHConfigApplyResult)
async def post_ssh_config_apply(body: SSHConfigApplyBlock) -> SSHConfigApplyResult:
    """Append a Host block to ``~/.ssh/config``."""
    try:
        return apply_ssh_config_block(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("", response_model=CredentialProfile, status_code=201)
async def create_credential(body: CredentialCreateRequest) -> CredentialProfile:
    _only_git_mutations(body.type)
    config = load_config()
    new_id = None
    for _ in range(12):
        cand = generate_short_agent_id()
        if not any(p.id == cand for p in config.credentials.profiles):
            new_id = cand
            break
    if new_id is None:
        raise HTTPException(status_code=500, detail="Failed to allocate credential id")

    profile = CredentialProfile(
        id=new_id,
        type=body.type,
        provider=body.provider,
        name=body.name,
        auth_method=body.auth_method,
        secret_ref=body.secret_ref,
        metadata=body.metadata,
        acquisition_notes=body.acquisition_notes,
        git_user_name=body.git_user_name,
        git_user_email=body.git_user_email,
    )
    config.credentials.profiles.append(profile)
    save_config(config)
    return profile


@router.put("/{credential_id}", response_model=CredentialProfile)
async def update_credential(
    credential_id: str = PathParam(...),
    body: CredentialProfile = Body(...),
) -> CredentialProfile:
    if body.id != credential_id:
        raise HTTPException(status_code=400, detail="Credential id mismatch")
    _only_git_mutations(body.type)
    config = load_config()
    for i, p in enumerate(config.credentials.profiles):
        if p.id == credential_id:
            config.credentials.profiles[i] = body
            save_config(config)
            return body
    raise HTTPException(status_code=404, detail=f"Credential '{credential_id}' not found")


@router.delete("/{credential_id}")
async def delete_credential(credential_id: str = PathParam(...)) -> dict:
    config = load_config()
    before = len(config.credentials.profiles)
    config.credentials.profiles = [
        p for p in config.credentials.profiles if p.id != credential_id
    ]
    if len(config.credentials.profiles) == before:
        raise HTTPException(status_code=404, detail=f"Credential '{credential_id}' not found")
    save_config(config)
    return {"success": True, "id": credential_id}
