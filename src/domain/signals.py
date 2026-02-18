from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class Signal:
    signal_type: str
    job_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    run_id: str = "manual"
    user_id: str = "default"
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def record_signal(repo: Any, signal: Signal) -> Any:
    return repo.create_signal(
        signal_id=signal.id,
        run_id=signal.run_id,
        job_id=signal.job_id,
        signal_type=signal.signal_type,
        payload_json=signal.payload,
        created_at=signal.created_at,
        user_id=signal.user_id,
    )
