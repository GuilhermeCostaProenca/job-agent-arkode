import hashlib
from datetime import UTC, datetime
from uuid import uuid4


def generate_run_id(prefix: str = "run") -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{ts}_{uuid4().hex[:8]}"


def generate_job_id(source: str, external_id: str, company: str, title: str) -> str:
    base = f"{source}|{external_id}|{company}|{title}".lower()
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:14]
    return f"job_{digest}"
