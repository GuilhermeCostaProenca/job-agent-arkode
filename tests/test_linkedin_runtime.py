from src.autopilot.linkedin_easy_apply import resolve_prompt_answer


def test_resolve_prompt_answer_prefers_effective_profile_location() -> None:
    answer = resolve_prompt_answer(
        "Current location",
        {"fit_summary": "Strong backend fit."},
        {
            "target_role": "Junior Backend Engineer",
            "location": "remoto",
            "focus_stacks": ["Python", "FastAPI", "SQL"],
            "fit_summary": "Strong backend fit.",
        },
    )

    assert answer == "remoto"


def test_resolve_prompt_answer_prefers_effective_profile_stacks() -> None:
    answer = resolve_prompt_answer(
        "Main tech stack",
        {"fit_summary": "Strong backend fit."},
        {
            "target_role": "Junior Backend Engineer",
            "location": "remoto",
            "focus_stacks": ["Python", "FastAPI", "SQL"],
            "fit_summary": "Strong backend fit.",
        },
    )

    assert answer == "Python, FastAPI, SQL"


def test_resolve_prompt_answer_falls_back_to_fit_summary() -> None:
    answer = resolve_prompt_answer(
        "Why are you interested in this role?",
        {"fit_summary": "Strong backend fit."},
        {
            "target_role": "Junior Backend Engineer",
            "location": "remoto",
            "focus_stacks": ["Python", "FastAPI", "SQL"],
            "fit_summary": "Strong backend fit.",
        },
    )

    assert answer == "Strong backend fit."
