# -*- coding: utf-8 -*-
"""Feishu OAuth helpers for console login (enterprise tenant allowlist)."""
from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import Request

logger = logging.getLogger(__name__)

FEISHU_AUTHORIZE_URL = (
    "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
)
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
FEISHU_USER_INFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"

# Minimal scopes for Web Console login (fixed; not configurable).
# OAuth authorize still requires a scope string — this is not an extra env var.
DEFAULT_OAUTH_SCOPES = (
    "contact:user.base:readonly contact:user.email:readonly"
)


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def is_feishu_auth_configured() -> bool:
    if not (
        _env("FEISHU_APP_ID")
        and _env("FEISHU_APP_SECRET")
        and _env("FEISHU_REDIRECT_URI")
        and _env("FEISHU_ALLOWED_TENANT_KEYS")
    ):
        return False
    return bool(allowed_tenant_keys())


def allowed_tenant_keys() -> frozenset[str]:
    raw = _env("FEISHU_ALLOWED_TENANT_KEYS")
    if not raw:
        return frozenset()
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


def is_safe_return_to(path: str) -> bool:
    if not path or not isinstance(path, str):
        return False
    if not path.startswith("/"):
        return False
    if path.startswith("//"):
        return False
    if ".." in path:
        return False
    if any(c in path for c in ("\x00", "\n", "\r")):
        return False
    if len(path) > 512:
        return False
    return True


def build_feishu_state(return_to: Optional[str]) -> str:
    payload: dict[str, str] = {"nonce": secrets.token_urlsafe(16)}
    if return_to and is_safe_return_to(return_to):
        payload["returnTo"] = return_to
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_feishu_state(state: Optional[str]) -> str:
    if not state:
        return "/chat"
    try:
        pad = (4 - len(state) % 4) % 4
        padded = state + ("=" * pad)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
        rt = payload.get("returnTo")
        if isinstance(rt, str) and is_safe_return_to(rt):
            return rt
    except (json.JSONDecodeError, ValueError, TypeError, UnicodeError) as e:
        logger.debug("Invalid Feishu OAuth state: %s", e)
    return "/chat"


def get_public_origin(request: Request) -> str:
    explicit = _env("COPAW_PUBLIC_ORIGIN")
    if explicit:
        return explicit.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host_hdr = request.headers.get("x-forwarded-host") or request.headers.get(
        "host",
    )
    if host_hdr:
        host = host_hdr.split(",")[0].strip()
        return f"{proto}://{host}"
    base = str(request.base_url)
    return base.rstrip("/")


def feishu_authorize_redirect_url(state: str) -> str:
    params = urllib.parse.urlencode(
        {
            "client_id": _env("FEISHU_APP_ID"),
            "redirect_uri": _env("FEISHU_REDIRECT_URI"),
            "response_type": "code",
            "scope": DEFAULT_OAUTH_SCOPES,
            "state": state,
        },
    )
    return f"{FEISHU_AUTHORIZE_URL}?{params}"


def exchange_code_for_token(code: str) -> dict[str, Any]:
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": _env("FEISHU_APP_ID"),
            "client_secret": _env("FEISHU_APP_SECRET"),
            "code": code,
            "redirect_uri": _env("FEISHU_REDIRECT_URI"),
        },
    )
    req = urllib.request.Request(
        FEISHU_TOKEN_URL,
        data=body.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.warning("Feishu token HTTP %s: %s", e.code, err_body[:500])
        raise RuntimeError("feishu_token_http_error") from e
    except urllib.error.URLError as e:
        logger.warning("Feishu token network error: %s", e)
        raise RuntimeError("feishu_token_network_error") from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("Feishu token invalid JSON")
        raise RuntimeError("feishu_token_bad_json") from e

    if not isinstance(data, dict):
        raise RuntimeError("feishu_token_bad_shape")

    code_val = data.get("code")
    if code_val not in (None, 0):
        logger.warning(
            "Feishu token API error code=%s msg=%s",
            code_val,
            data.get("msg"),
        )
        raise RuntimeError("feishu_token_api_error")

    return data


def extract_access_token(payload: dict[str, Any]) -> Optional[str]:
    token = payload.get("access_token")
    if isinstance(token, str) and token:
        return token
    data = payload.get("data")
    if isinstance(data, dict):
        t2 = data.get("access_token")
        if isinstance(t2, str) and t2:
            return t2
    return None


@dataclass(frozen=True)
class FeishuUserProfile:
    """Subset of authen ``user_info`` used for console display and CoPaw identity."""

    user_id: str
    tenant_key: Optional[str]
    display_name: str
    avatar_url: str


def _feishu_display_name(block: dict[str, Any]) -> str:
    for key in ("name", "en_name", "nickname"):
        val = block.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    for key in ("enterprise_email", "email"):
        val = block.get(key)
        if isinstance(val, str) and "@" in val:
            local = val.split("@", 1)[0].strip()
            if local:
                return local
    return ""


def _coerce_feishu_avatar_url(raw: Optional[Any]) -> str:
    """Feishu often returns host/path without scheme, e.g. ``www.feishu.cn/avatar/icon``."""
    if not isinstance(raw, str):
        return ""
    u = raw.strip()
    if not u:
        return ""
    if u.startswith("//"):
        return f"https:{u}"
    if u.startswith("http://") or u.startswith("https://"):
        return u
    # Bare host or host/path (official doc example)
    return f"https://{u.lstrip('/')}"


def _feishu_avatar_url(block: dict[str, Any]) -> str:
    av = block.get("avatar")
    if isinstance(av, str) and av.strip():
        return _coerce_feishu_avatar_url(av)
    if isinstance(av, dict):
        for key in (
            "avatar_640",
            "avatar_240",
            "avatar_192",
            "avatar_72",
            "avatar_middle",
        ):
            url = _coerce_feishu_avatar_url(av.get(key))
            if url:
                return url
        for v in av.values():
            url = _coerce_feishu_avatar_url(v)
            if url:
                return url
    for key in (
        "picture",
        "avatar_big",
        "avatar_middle",
        "avatar_thumb",
        "avatar_url",
    ):
        url = _coerce_feishu_avatar_url(block.get(key))
        if url:
            return url
    return ""


def extract_tenant_key(payload: dict[str, Any]) -> Optional[str]:
    data = payload.get("data")
    if isinstance(data, dict):
        tk = data.get("tenant_key")
        if tk is not None and str(tk):
            return str(tk)
    tk = payload.get("tenant_key")
    if tk is not None and str(tk):
        return str(tk)
    return None


def fetch_feishu_user_profile(access_token: str) -> FeishuUserProfile:
    """Return identity + display fields from authen ``user_info``."""
    req = urllib.request.Request(
        FEISHU_USER_INFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.warning("Feishu user_info HTTP %s: %s", e.code, err_body[:500])
        raise RuntimeError("feishu_userinfo_http_error") from e
    except urllib.error.URLError as e:
        logger.warning("Feishu user_info network error: %s", e)
        raise RuntimeError("feishu_userinfo_network_error") from e

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError("feishu_userinfo_bad_json") from e

    if not isinstance(parsed, dict):
        raise RuntimeError("feishu_userinfo_bad_shape")

    if parsed.get("code") not in (None, 0):
        raise RuntimeError("feishu_userinfo_api_error")

    block = parsed.get("data", parsed)
    if not isinstance(block, dict):
        raise RuntimeError("feishu_userinfo_no_data")

    uid = block.get("user_id") or block.get("open_id") or block.get("union_id")
    if uid is None or not str(uid):
        raise RuntimeError("feishu_userinfo_no_user_id")
    tk = block.get("tenant_key")
    tenant = str(tk) if tk not in (None, "") else None
    display = _feishu_display_name(block)
    avatar = _feishu_avatar_url(block)
    return FeishuUserProfile(
        user_id=str(uid),
        tenant_key=tenant,
        display_name=display,
        avatar_url=avatar,
    )


def is_localhost_client(request: Request) -> bool:
    if not request.client:
        return False
    return request.client.host in ("127.0.0.1", "::1")


def console_login_path(return_to: str) -> str:
    """Path to SPA login (supports root or /console alias)."""
    configured = _env("COPAW_CONSOLE_BASE_PATH").rstrip("/")
    if configured:
        return f"{configured}/login"
    if return_to.startswith("/console/") or return_to == "/console":
        return "/console/login"
    return "/login"
