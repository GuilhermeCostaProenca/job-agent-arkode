from __future__ import annotations

APPROVED_REASONS = {
    "like_company",
    "like_role",
    "good_growth",
    "good_learning",
    "good_stack_match",
}

REJECTED_REASONS = {
    "stack_mismatch",
    "seniority_too_high",
    "salary_low",
    "location_bad",
    "company_type_bad",
    "description_generic",
    "red_flag_pj",
    "red_flag_unpaid",
    "support_disguised",
    "commute_too_far",
}

ALL_REASONS = APPROVED_REASONS.union(REJECTED_REASONS)


def is_valid_reason(value: str) -> bool:
    return value in ALL_REASONS
