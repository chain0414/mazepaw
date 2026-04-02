# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request

from ..agent_context import get_agent_for_request
from ..insights.bootstrap import ensure_governance_files
from ..insights.models import (
    DailyDigestItem,
    ReviewQueueItem,
    ReviewQueueResolution,
)
from ..insights.service import InsightsService

router = APIRouter(prefix="/insights", tags=["insights"])


async def _get_service(request: Request) -> tuple[str, InsightsService]:
    workspace = await get_agent_for_request(request)
    ensure_governance_files(workspace.workspace_dir)
    return workspace.agent_id, InsightsService(workspace.workspace_dir)


@router.get("/daily-digests", response_model=list[DailyDigestItem])
async def list_daily_digests(request: Request) -> list[DailyDigestItem]:
    _, service = await _get_service(request)
    return service.list_daily_digests()


@router.post("/daily-digests", response_model=DailyDigestItem, status_code=201)
async def create_daily_digest(
    request: Request,
    item: DailyDigestItem = Body(...),
) -> DailyDigestItem:
    _, service = await _get_service(request)
    return service.append_daily_digest(item)


@router.get("/review-queue", response_model=list[ReviewQueueItem])
async def list_review_queue(request: Request) -> list[ReviewQueueItem]:
    agent_id, service = await _get_service(request)
    return await service.list_review_queue(agent_id=agent_id)


@router.post("/review-queue", response_model=ReviewQueueItem, status_code=201)
async def create_review_queue_item(
    request: Request,
    item: ReviewQueueItem = Body(...),
) -> ReviewQueueItem:
    _, service = await _get_service(request)
    return service.append_review_item(item)


@router.post("/review-queue/{item_id}/resolve", response_model=ReviewQueueItem)
async def resolve_review_queue_item(
    item_id: str,
    request: Request,
    resolution: ReviewQueueResolution = Body(...),
) -> ReviewQueueItem:
    _, service = await _get_service(request)
    item = await service.resolve_review_item(item_id, resolution)
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")
    return item
