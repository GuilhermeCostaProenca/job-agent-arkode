import hashlib
from datetime import UTC, datetime
from uuid import uuid4


def generate_run_id(prefix: str = "run") -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{ts}_{uuid4().hex[:8]}"


def generate_job_id(source: str, external_id: str, company: str, title: str) -> str:
    normalized_external_id = (external_id or "").strip().lower()
    if normalized_external_id:
        base = f"{source}|{normalized_external_id}"
    else:
        base = f"{source}|{company}|{title}".lower()
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:14]
    return f"job_{digest}"
