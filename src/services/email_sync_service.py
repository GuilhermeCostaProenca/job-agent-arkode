from __future__ import annotations

import re
from uuid import uuid4

from src.tracker.repo import TrackerRepository


STATUS_HINTS = {
    "interview": ("interview", "entrevista", "call with recruiter"),
    "rejected": ("unfortunately", "regret", "rejected"),
    "offer": ("offer", "proposal"),
    "replied": ("reply", "recruiter", "next steps"),
}


def infer_email_status(subject: str, snippet: str) -> tuple[str, bool]:
    text = f"{subject} {snippet}".lower()
    for status, hints in STATUS_HINTS.items():
        if any(hint in text for hint in hints):
            return status, status in {"interview", "offer", "replied"}
    return "applied", False


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def _extract_sender_domain(sender: str) -> str:
    match = re.search(r"@([a-z0-9.-]+\.[a-z]{2,})", sender.lower())
    return match.group(1) if match else ""


def _company_tokens(company: str) -> set[str]:
    stopwords = {"inc", "llc", "ltda", "company", "corp", "co", "sa", "tech"}
    return {token for token in _tokenize(company) if token not in stopwords}


def _match_application(repo: TrackerRepository, user_id: str, sender: str, subject: str, snippet: str) -> object | None:
    message_text = f"{sender} {subject} {snippet}"
    message_tokens = _tokenize(message_text)
    sender_domain = _extract_sender_domain(sender)

    best_application = None
    best_score = 0
    for application in repo.list_applications(user_id=user_id):
        job = repo.get_job(application.job_id)
        if job is None:
            continue

        score = 0
        company_tokens = _company_tokens(job.company)
        title_tokens = _tokenize(job.title)

        if company_tokens & message_tokens:
            score += 5
        if title_tokens & message_tokens:
            score += 3
        if sender_domain:
            if any(token in sender_domain for token in company_tokens):
                score += 4
            if job.company.lower() in sender_domain:
                score += 2
        if job.source and job.source.lower() in message_tokens:
            score += 1

        if score > best_score:
            best_score = score
            best_application = application

    return best_application if best_score > 0 else None


def sync_email_events(repo: TrackerRepository, messages: list[dict[str, str]], user_id: str) -> dict[str, int]:
    inserted = 0
    updated = 0
    if not repo.list_applications(user_id=user_id):
        return {"inserted": 0, "updated": 0}
    for message in messages:
        sender = message.get("sender", "")
        subject = message.get("subject", "")
        snippet = message.get("snippet", "")
        application = _match_application(repo, user_id, sender, subject, snippet)
        if application is None:
            continue
        status, action_required = infer_email_status(subject, snippet)
        repo.create_email_event(
            event_id=str(uuid4()),
            application_id=application.id,
            provider="gmail",
            external_id=message.get("id", str(uuid4())),
            subject=subject,
            sender=sender,
            snippet=snippet,
            status_inferred=status,
            action_required=action_required,
            raw_payload=message,
            user_id=user_id,
        )
        inserted += 1
        if status in {"replied", "interview", "offer", "rejected"}:
            repo.update_application_status(application.job_id, status, notes=f"gmail:{sender}", user_id=user_id)
            updated += 1
    return {"inserted": inserted, "updated": updated}
