from __future__ import annotations

import json
from pathlib import Path


def load_feed_items_from_file(path: Path) -> list[dict[str, str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def load_feed_items_from_url(url: str) -> list[dict[str, str]]:
    return [{"source": "manual_url", "url": url, "text": url}]
