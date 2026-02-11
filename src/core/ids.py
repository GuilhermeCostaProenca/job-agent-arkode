from datetime import UTC, datetime
from uuid import uuid4


def generate_run_id(prefix: str = "run") -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{ts}_{uuid4().hex[:8]}"


def generate_job_id(company: str, title: str) -> str:
    compact = f"{company}-{title}".lower().replace(" ", "-")
    return f"job_{compact[:40]}_{uuid4().hex[:6]}"
