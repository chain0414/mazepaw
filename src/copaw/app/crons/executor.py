# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Dict

from .models import CronJobSpec

logger = logging.getLogger(__name__)


class CronExecutor:
    def __init__(self, *, runner: Any, channel_manager: Any):
        self._runner = runner
        self._channel_manager = channel_manager

    async def execute(self, job: CronJobSpec) -> None:
        """Execute one job once.

        - task_type text: send fixed text to channel
        - task_type agent: ask agent with prompt, send reply to channel (
            stream_query + send_event)
        """
        target_user_id = job.dispatch.target.user_id
        target_session_id = job.dispatch.target.session_id
        dispatch_meta: Dict[str, Any] = dict(job.dispatch.meta or {})
        logger.info(
            "cron execute: job_id=%s channel=%s task_type=%s "
            "target_user_id=%s target_session_id=%s",
            job.id,
            job.dispatch.channel,
            job.task_type,
            target_user_id[:40] if target_user_id else "",
            target_session_id[:40] if target_session_id else "",
        )

        if job.task_type == "text" and job.text:
            logger.info(
                "cron send_text: job_id=%s channel=%s len=%s",
                job.id,
                job.dispatch.channel,
                len(job.text or ""),
            )
            await self._channel_manager.send_text(
                channel=job.dispatch.channel,
                user_id=target_user_id,
                session_id=target_session_id,
                text=job.text.strip(),
                meta=dispatch_meta,
            )
            await self._persist_governance_outputs(
                dispatch_meta=dispatch_meta,
                content=job.text.strip(),
            )
            return

        # agent: run request as the dispatch target user so context matches
        logger.info(
            "cron agent: job_id=%s channel=%s stream_query then send_event",
            job.id,
            job.dispatch.channel,
        )
        assert job.request is not None
        req: Dict[str, Any] = job.request.model_dump(mode="json")
        req["user_id"] = target_user_id or "cron"
        req["session_id"] = target_session_id or f"cron:{job.id}"
        completed_text = ""

        async def _run() -> None:
            nonlocal completed_text
            async for event in self._runner.stream_query(req):
                extracted = self._extract_completed_message_text(event)
                if extracted:
                    completed_text = extracted
                await self._channel_manager.send_event(
                    channel=job.dispatch.channel,
                    user_id=target_user_id,
                    session_id=target_session_id,
                    event=event,
                    meta=dispatch_meta,
                )

        await asyncio.wait_for(_run(), timeout=job.runtime.timeout_seconds)
        await self._persist_governance_outputs(
            dispatch_meta=dispatch_meta,
            content=completed_text,
        )

    @staticmethod
    def _extract_completed_message_text(event: Any) -> str:
        """Best-effort extraction of a final text summary from stream events."""
        if isinstance(event, dict):
            if isinstance(event.get("content"), str):
                return str(event["content"])
            data = event.get("data")
            if isinstance(data, dict) and isinstance(data.get("content"), str):
                return str(data["content"])
        content = getattr(event, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(str(block.get("text", "")))
                elif hasattr(block, "text"):
                    texts.append(str(getattr(block, "text")))
            return "\n".join(filter(None, texts)).strip()
        return ""

    async def _persist_governance_outputs(
        self,
        *,
        dispatch_meta: dict[str, Any],
        content: str,
    ) -> None:
        """Persist digest/review outputs into agent workspace files."""
        workspace_dir = dispatch_meta.get("workspace_dir")
        if not workspace_dir:
            return

        try:
            from ..insights.bootstrap import ensure_governance_files
            from ..insights.models import (
                DailyDigestItem,
                ReviewQueueItem,
            )
            from ..insights.service import InsightsService

            workspace_path = Path(str(workspace_dir)).expanduser()
            ensure_governance_files(workspace_path)
            service = InsightsService(workspace_path)
            source_agent = str(dispatch_meta.get("source_agent") or "cron")
            repo_scope = list(dispatch_meta.get("repo_scope") or [])

            digest_meta = dispatch_meta.get("daily_digest") or {}
            if digest_meta:
                service.append_daily_digest(
                    DailyDigestItem(
                        id=str(uuid.uuid4()),
                        title=str(digest_meta.get("title") or "Scheduled digest"),
                        summary=content or str(digest_meta.get("summary") or ""),
                        source_agent=source_agent,
                        repo_scope=repo_scope,
                        sources=list(digest_meta.get("sources") or ["manual"]),
                        metadata=dict(digest_meta.get("metadata") or {}),
                    ),
                )

            review_meta = dispatch_meta.get("review_queue") or {}
            if review_meta:
                service.append_review_item(
                    ReviewQueueItem(
                        id=str(uuid.uuid4()),
                        title=str(review_meta.get("title") or "Review required"),
                        summary=content or str(review_meta.get("summary") or ""),
                        item_type=review_meta.get("item_type") or "digest_followup",
                        source_agent=source_agent,
                        repo_scope=repo_scope,
                        action_payload=dict(review_meta.get("action_payload") or {}),
                    ),
                )
        except Exception:
            logger.exception("Failed to persist governance outputs")
