import re

from src.domain.models import JobPosting

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def resolve_contact_email(job: JobPosting) -> str | None:
    match = EMAIL_PATTERN.search(job.description)
    return match.group(0) if match else None
