# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from ..approvals import get_approval_service
from ...security.tool_guard.approval import ApprovalDecision
from .models import (
    DailyDigestItem,
    ReviewQueueItem,
    ReviewQueueResolution,
    utc_now_iso,
)
from .repo import DailyDigestRepository, ReviewQueueRepository


class InsightsService:
    """Agent-scoped service for digest and review queue views."""

    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir
        self.daily_digests = DailyDigestRepository(
            workspace_dir / "daily_digest.json",
        )
        self.review_queue = ReviewQueueRepository(
            workspace_dir / "review_queue.json",
        )

    def list_daily_digests(self) -> list[DailyDigestItem]:
        return self.daily_digests.list_items()

    def append_daily_digest(self, item: DailyDigestItem) -> DailyDigestItem:
        return self.daily_digests.append(item)

    async def list_review_queue(self, agent_id: str | None = None) -> list[ReviewQueueItem]:
        items = list(self.review_queue.list_items())
        approval_service = get_approval_service()
        approvals = [
            *await approval_service.list_pending(),
            *await approval_service.list_completed(),
        ]
        for approval in approvals:
            item = self._approval_to_item(approval, agent_id=agent_id)
            if item is not None:
                items.append(item)
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    def append_review_item(self, item: ReviewQueueItem) -> ReviewQueueItem:
        return self.review_queue.append(item)

    async def resolve_review_item(
        self,
        item_id: str,
        resolution: ReviewQueueResolution,
    ):
        if item_id.startswith("approval:"):
            return await self._resolve_approval_item(item_id, resolution)
        return self.review_queue.resolve(item_id, resolution)

    def _approval_to_item(self, approval, agent_id: str | None = None) -> ReviewQueueItem | None:
        approval_agent_id = str(approval.extra.get("agent_id") or "")
        if agent_id and approval_agent_id and approval_agent_id != agent_id:
            return None
        repo_scope = []
        workspace_dir = str(approval.extra.get("workspace_dir") or "")
        if workspace_dir:
            repo_scope.append(Path(workspace_dir).name)
        created_at = utc_now_iso()
        updated_at = utc_now_iso()
        try:
            from datetime import datetime, timezone

            created_at = datetime.fromtimestamp(
                approval.created_at,
                timezone.utc,
            ).isoformat().replace("+00:00", "Z")
            if approval.resolved_at:
                updated_at = datetime.fromtimestamp(
                    approval.resolved_at,
                    timezone.utc,
                ).isoformat().replace("+00:00", "Z")
            else:
                updated_at = created_at
        except Exception:
            pass
        return ReviewQueueItem(
            id=f"approval:{approval.request_id}",
            title=f"Approve `{approval.tool_name}`",
            summary=approval.result_summary or "Pending tool guard approval.",
            item_type="approval",
            source_agent=approval_agent_id or "unknown",
            status=approval.status,
            created_at=created_at,
            updated_at=updated_at,
            repo_scope=repo_scope,
            action_payload=approval.extra,
            resolution_note="",
        )

    async def _resolve_approval_item(
        self,
        item_id: str,
        resolution: ReviewQueueResolution,
    ):
        decision_map = {
            "approved": ApprovalDecision.APPROVED,
            "denied": ApprovalDecision.DENIED,
            "resolved": ApprovalDecision.DENIED,
            "timeout": ApprovalDecision.TIMEOUT,
        }
        request_id = item_id.split("approval:", 1)[1]
        approval_service = get_approval_service()
        pending = await approval_service.resolve_request(
            request_id,
            decision_map[resolution.status],
        )
        return self._approval_to_item(pending) if pending is not None else None
