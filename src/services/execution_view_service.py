from __future__ import annotations

from typing import Any

from src.domain.pause_control import build_pause_context


def serialize_execution(row: Any) -> dict[str, Any]:
    payload = row.model_dump() if hasattr(row, "model_dump") else dict(row)
    reason = payload.get("pause_reason", "")
    payload["recommended_action"] = build_pause_context(reason)["recommended_action"] if reason else ""
    return payload
