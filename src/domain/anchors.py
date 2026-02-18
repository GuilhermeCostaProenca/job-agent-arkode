from __future__ import annotations

import re
from collections import Counter

from src.domain.models import JobAnchors, JobPosting

SECTION_PATTERNS = {
    "responsibilities": re.compile(r"(responsabilidades?|responsibilities|what you will do)", re.I),
    "must_have": re.compile(r"(requisitos|requirements|must have|obrigat[oó]rio)", re.I),
    "nice_to_have": re.compile(r"(diferenciais|nice to have|desej[aá]vel)", re.I),
    "mission": re.compile(r"(about|sobre|miss[aã]o|impact)", re.I),
}
SKILL_HINTS = {
    "flutter",
    "kotlin",
    "java",
    "python",
    "sql",
    "power bi",
    "bi",
    "dashboard",
    "fastapi",
    "aws",
    "docker",
    "git",
}
TOOL_HINTS = {"jira", "figma", "notion", "excel", "power bi", "tableau", "github"}
SOFT_HINTS = {
    "comunicação",
    "communication",
    "colaboração",
    "collaboration",
    "ownership",
    "proatividade",
    "autonomia",
    "teamwork",
}
STOPWORDS = {
    "de",
    "da",
    "do",
    "e",
    "em",
    "para",
    "com",
    "the",
    "and",
    "a",
    "o",
    "na",
    "no",
}


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {
        "responsibilities": [],
        "must_have": [],
        "nice_to_have": [],
        "mission": [],
    }
    current = "mission"
    for raw in text.splitlines():
        line = raw.strip(" -•\t")
        if not line:
            continue
        if SECTION_PATTERNS["responsibilities"].search(line):
            current = "responsibilities"
            continue
        if SECTION_PATTERNS["must_have"].search(line):
            current = "must_have"
            continue
        if SECTION_PATTERNS["nice_to_have"].search(line):
            current = "nice_to_have"
            continue
        if SECTION_PATTERNS["mission"].search(line):
            current = "mission"
            continue
        sections[current].append(line)
    return sections


def _normalize_token(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip().lower())


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        norm = _normalize_token(item)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def extract_job_anchors(job: JobPosting) -> JobAnchors:
    text = f"{job.title}\n{job.description}\n" + "\n".join(job.requirements)
    sections = _split_sections(text)

    tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9+#.]{2,}", text.lower())
    filtered = [tok for tok in tokens if tok not in STOPWORDS and len(tok) > 2]
    frequency = Counter(filtered)

    top_skills = [term for term in SKILL_HINTS if term in text.lower()]
    freq_candidates = [word for word, _ in frequency.most_common(20) if word in SKILL_HINTS]
    top_skills.extend(freq_candidates)

    tools = [tool for tool in TOOL_HINTS if tool in text.lower()]
    soft = [word for word in SOFT_HINTS if word in text.lower()]

    mission_keywords = [word for word, count in frequency.most_common(15) if count >= 2][:8]

    return JobAnchors(
        top_skills=_dedupe(top_skills),
        responsibilities=_dedupe(sections["responsibilities"]),
        tools=_dedupe(tools),
        soft_keywords=_dedupe(soft),
        must_have=_dedupe(sections["must_have"]),
        nice_to_have=_dedupe(sections["nice_to_have"]),
        mission_keywords=_dedupe(mission_keywords),
    )
