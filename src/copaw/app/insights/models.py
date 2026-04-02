# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


DigestSource = Literal["trending", "starred", "curated", "x", "manual"]
ReviewItemType = Literal[
    "digest_followup",
    "adoption_decision",
    "fork_request",
    "push_request",
    "merge_request",
    "approval",
]
ReviewStatus = Literal["pending", "approved", "denied", "resolved", "timeout"]


class DailyDigestItem(BaseModel):
    id: str
    title: str
    summary: str
    source_agent: str
    created_at: str = Field(default_factory=utc_now_iso)
    repo_scope: list[str] = Field(default_factory=list)
    sources: list[DigestSource] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DailyDigestFile(BaseModel):
    version: int = 1
    items: list[DailyDigestItem] = Field(default_factory=list)


class ReviewQueueItem(BaseModel):
    id: str
    title: str
    summary: str
    item_type: ReviewItemType
    source_agent: str
    status: ReviewStatus = "pending"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    repo_scope: list[str] = Field(default_factory=list)
    action_payload: dict[str, Any] = Field(default_factory=dict)
    resolution_note: str = ""


class ReviewQueueResolution(BaseModel):
    status: Literal["approved", "denied", "resolved", "timeout"]
    note: str = ""


class ReviewQueueFile(BaseModel):
    version: int = 1
    items: list[ReviewQueueItem] = Field(default_factory=list)
