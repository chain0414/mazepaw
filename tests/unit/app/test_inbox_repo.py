# -*- coding: utf-8 -*-
"""Tests for inbox-compatible digest and review repositories."""
from pathlib import Path

from copaw.app.insights.models import (
    DailyDigestItem,
    ReviewQueueItem,
    ReviewQueueResolution,
)
from copaw.app.insights.repo import DailyDigestRepository, ReviewQueueRepository


def test_daily_digest_repository_round_trip(tmp_path: Path) -> None:
    """Daily digest entries should persist and reload."""
    repo = DailyDigestRepository(tmp_path / "daily_digest.json")

    item = DailyDigestItem(
        id="digest-1",
        title="chainOS review summary",
        summary="Detected a candidate skill cleanup.",
        source_agent="chainos-agent",
        repo_scope=["chainOS"],
        sources=["curated"],
    )

    repo.append(item)
    items = repo.list_items()

    assert len(items) == 1
    assert items[0].title == "chainOS review summary"
    assert items[0].repo_scope == ["chainOS"]


def test_review_queue_repository_can_resolve_item(tmp_path: Path) -> None:
    """Review queue items should be resolvable."""
    repo = ReviewQueueRepository(tmp_path / "review_queue.json")

    item = ReviewQueueItem(
        id="review-1",
        title="Approve chainOS commit",
        summary="Commit AGENT.md cleanup after review.",
        item_type="approval",
        source_agent="chainos-agent",
        repo_scope=["chainOS"],
    )

    repo.append(item)
    resolved = repo.resolve(
        "review-1",
        ReviewQueueResolution(status="approved", note="Looks safe"),
    )

    assert resolved is not None
    assert resolved.status == "approved"
    assert resolved.resolution_note == "Looks safe"
    assert repo.list_items()[0].status == "approved"
