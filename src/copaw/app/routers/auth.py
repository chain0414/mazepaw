# -*- coding: utf-8 -*-
"""Authentication API endpoints."""
from __future__ import annotations

import logging
import os
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..auth import (
    authenticate,
    create_token,
    get_console_profile,
    has_registered_users,
    is_auth_enabled,
    register_user,
    upsert_console_profile,
    verify_token,
)
from ..feishu_oauth import (
    allowed_tenant_keys,
    build_feishu_state,
    console_login_path,
    decode_feishu_state,
    exchange_code_for_token,
    extract_access_token,
    extract_tenant_key,
    feishu_authorize_redirect_url,
    fetch_feishu_user_profile,
    get_public_origin,
    is_feishu_auth_configured,
    is_localhost_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class AuthStatusResponse(BaseModel):
    enabled: bool
    has_users: bool
    feishu_login_available: bool
    password_login_allowed: bool


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """Authenticate with username and password."""
    if not is_auth_enabled():
        return LoginResponse(token="", username="")

    if is_feishu_auth_configured() and not is_localhost_client(request):
        raise HTTPException(
            status_code=403,
            detail="password_login_local_only",
        )

    token = authenticate(req.username, req.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    u = req.username.strip()
    upsert_console_profile(u, u, "")
    return LoginResponse(token=token, username=u)


@router.post("/register")
async def register(req: RegisterRequest):
    """Register the single user account (only allowed once)."""
    env_flag = os.environ.get("COPAW_AUTH_ENABLED", "").strip().lower()
    if env_flag not in ("true", "1", "yes"):
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    if is_feishu_auth_configured():
        raise HTTPException(
            status_code=403,
            detail="registration_disabled_use_feishu",
        )

    if has_registered_users():
        raise HTTPException(
            status_code=403,
            detail="User already registered",
        )

    if not req.username.strip() or not req.password.strip():
        raise HTTPException(
            status_code=400,
            detail="Username and password are required",
        )

    username = req.username.strip()
    token = register_user(username, req.password)
    if token is None:
        raise HTTPException(
            status_code=409,
            detail="Registration failed",
        )

    upsert_console_profile(username, username, "")
    return LoginResponse(token=token, username=username)


@router.get("/status")
async def auth_status(request: Request):
    """Check if authentication is enabled and whether a user exists."""
    feishu_on = is_feishu_auth_configured()
    pwd_ok = not feishu_on or is_localhost_client(request)
    return AuthStatusResponse(
        enabled=is_auth_enabled(),
        has_users=has_registered_users(),
        feishu_login_available=feishu_on,
        password_login_allowed=pwd_ok,
    )


@router.get("/feishu")
async def feishu_start(request: Request, returnTo: str | None = None):
    """Redirect browser to Feishu OAuth authorize page."""
    if not is_auth_enabled():
        raise HTTPException(status_code=403, detail="Authentication is not enabled")
    if not is_feishu_auth_configured():
        raise HTTPException(status_code=503, detail="Feishu login is not configured")
    state = build_feishu_state(returnTo)
    url = feishu_authorize_redirect_url(state)
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback/feishu")
async def feishu_callback(request: Request):
    """OAuth redirect_uri handler: exchange code, check tenant, issue CoPaw token."""
    origin = get_public_origin(request)
    params = request.query_params
    err = params.get("error")
    code = params.get("code")
    state_raw = params.get("state")
    return_to = decode_feishu_state(state_raw)
    login_path = console_login_path(return_to)

    def redirect_login(extra: dict[str, str]) -> RedirectResponse:
        loc = f"{origin}{login_path}?{urlencode(extra)}"
        return RedirectResponse(url=loc, status_code=302)

    if err:
        return redirect_login({"error": err})

    if not code:
        return redirect_login({"error": "no_code"})

    if not is_feishu_auth_configured():
        return redirect_login({"error": "feishu_not_configured"})

    try:
        token_payload = exchange_code_for_token(code)
    except RuntimeError:
        return redirect_login({"error": "auth_failed"})

    access = extract_access_token(token_payload)
    if not access:
        return redirect_login({"error": "auth_failed"})

    tenant_key = extract_tenant_key(token_payload)
    try:
        fs_profile = fetch_feishu_user_profile(access)
    except RuntimeError:
        return redirect_login({"error": "auth_failed"})

    user_id = fs_profile.user_id
    tenant_from_profile = fs_profile.tenant_key

    if not tenant_key and tenant_from_profile:
        tenant_key = tenant_from_profile

    allowed = allowed_tenant_keys()
    if not tenant_key or tenant_key not in allowed:
        logger.warning(
            "Feishu OAuth: tenant not in allowlist (received tenant_key=%r). "
            "Put this value in FEISHU_ALLOWED_TENANT_KEYS if it is your company tenant.",
            tenant_key,
        )
        return redirect_login({"error": "forbidden_tenant"})

    username = f"feishu:{user_id}"
    upsert_console_profile(
        username,
        fs_profile.display_name,
        fs_profile.avatar_url,
    )
    if not (fs_profile.display_name or "").strip():
        logger.warning(
            "Feishu login: user_info returned no display name for %s; "
            "check application scopes (at least contact:user.base:readonly).",
            username,
        )
    copaw_token = create_token(username)
    q = urlencode({"token": copaw_token, "redirect": return_to})
    return RedirectResponse(url=f"{origin}{login_path}?{q}", status_code=302)


@router.get("/verify")
async def verify(request: Request):
    """Verify that the caller's Bearer token is still valid."""
    if not is_auth_enabled():
        return {
            "valid": True,
            "username": "",
            "display_name": "",
            "avatar_url": "",
        }

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    prof = get_console_profile(username)
    display_name = prof.get("display_name", "")
    avatar_url = prof.get("avatar_url", "")
    if not display_name and not username.startswith("feishu:"):
        display_name = username
    return {
        "valid": True,
        "username": username,
        "display_name": display_name,
        "avatar_url": avatar_url,
    }
