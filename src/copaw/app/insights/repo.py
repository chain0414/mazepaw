# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

from .models import (
    DailyDigestFile,
    DailyDigestItem,
    ReviewQueueFile,
    ReviewQueueItem,
    ReviewQueueResolution,
    utc_now_iso,
)

TFile = TypeVar("TFile", bound=BaseModel)


class _JsonFileRepository(Generic[TFile]):
    """Simple JSON file repository with atomic writes."""

    def __init__(self, path: Path, file_model: type[TFile]) -> None:
        self.path = path
        self.file_model = file_model

    def _load(self) -> TFile:
        if not self.path.exists():
            return self.file_model()  # type: ignore[call-arg]
        with open(self.path, "r", encoding="utf-8") as file:
            return self.file_model.model_validate(json.load(file))

    def _save(self, payload: TFile) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(
                payload.model_dump(mode="json"),
                file,
                ensure_ascii=False,
                indent=2,
            )
        temp_path.replace(self.path)


class DailyDigestRepository(_JsonFileRepository[DailyDigestFile]):
    def __init__(self, path: Path) -> None:
        super().__init__(path, DailyDigestFile)

    def list_items(self) -> list[DailyDigestItem]:
        return self._load().items

    def append(self, item: DailyDigestItem) -> DailyDigestItem:
        payload = self._load()
        payload.items.append(item)
        self._save(payload)
        return item


class ReviewQueueRepository(_JsonFileRepository[ReviewQueueFile]):
    def __init__(self, path: Path) -> None:
        super().__init__(path, ReviewQueueFile)

    def list_items(self) -> list[ReviewQueueItem]:
        return self._load().items

    def append(self, item: ReviewQueueItem) -> ReviewQueueItem:
        payload = self._load()
        payload.items.append(item)
        self._save(payload)
        return item

    def resolve(
        self,
        item_id: str,
        resolution: ReviewQueueResolution,
    ) -> ReviewQueueItem | None:
        payload = self._load()
        for item in payload.items:
            if item.id != item_id:
                continue
            item.status = resolution.status
            item.updated_at = utc_now_iso()
            item.resolution_note = resolution.note
            self._save(payload)
            return item
        return None
