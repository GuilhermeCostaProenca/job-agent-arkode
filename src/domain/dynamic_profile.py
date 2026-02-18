from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def update_dynamic_profile(
    output_path: Path,
    weights: dict[str, Any],
    applications_summary: dict[str, int],
    interview_notes: list[str] | None = None,
) -> None:
    skills = weights.get("skills", {})
    top_skills = [
        key for key, _ in sorted(skills.items(), key=lambda item: item[1], reverse=True)[:8]
    ]

    locations = weights.get("locations", {})
    preferred_locations = [
        key
        for key, value in sorted(locations.items(), key=lambda item: item[1], reverse=True)
        if value > 0
    ]

    company_type = weights.get("company_type", {})
    preferred_company_type = max(company_type, key=company_type.get) if company_type else "product"

    data = {
        "top_skills_inferred": top_skills,
        "preferred_locations": preferred_locations,
        "preferred_company_type": preferred_company_type,
        "writing_style_vector": weights.get("writing_style", {}),
        "applied_history_summary": applications_summary,
        "interview_questions_memory": interview_notes or [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
