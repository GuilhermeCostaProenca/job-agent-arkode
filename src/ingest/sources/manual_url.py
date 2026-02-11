from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from src.domain.models import JobPosting


def fetch_manual_url(url: str) -> JobPosting:
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    title = urlparse(url).path.strip("/").split("/")[-1].replace("-", " ").title() or "Manual Job"
    text = response.text[:3000]
    return JobPosting(
        external_id=url,
        source="manual",
        url=url,
        title=title,
        company=urlparse(url).netloc,
        location="não informado",
        description=text,
        requirements=[],
        posted_at=datetime.now(UTC),
    )
