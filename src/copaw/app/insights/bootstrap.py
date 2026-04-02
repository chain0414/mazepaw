# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from .models import DailyDigestFile, ReviewQueueFile


def ensure_governance_files(workspace_dir: Path) -> None:
    """Ensure inbox-compatible governance files exist."""
    daily_digest = workspace_dir / "daily_digest.json"
    review_queue = workspace_dir / "review_queue.json"

    if not daily_digest.exists():
        daily_digest.write_text(
            DailyDigestFile().model_dump_json(indent=2),
            encoding="utf-8",
        )

    if not review_queue.exists():
        review_queue.write_text(
            ReviewQueueFile().model_dump_json(indent=2),
            encoding="utf-8",
        )
