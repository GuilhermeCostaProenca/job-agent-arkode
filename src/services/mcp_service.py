from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class MCPTool:
    name: str
    description: str
    category: str


TOOLS = [
    MCPTool("import_github_profile", "Import repositories, languages and project evidence from the candidate GitHub profile.", "profile"),
    MCPTool("import_linkedin_profile", "Import headline, experiences and profile signals from the authenticated LinkedIn profile.", "profile"),
    MCPTool("search_jobs", "Discover and normalize jobs from RSS, manual URLs and authenticated LinkedIn using the current confirmed profile focus.", "intake"),
    MCPTool("score_job", "Score a job posting against the saved profile.", "decision"),
    MCPTool("generate_resume", "Generate a tailored resume for a job.", "tailoring"),
    MCPTool("generate_cover_letter", "Generate a tailored cover letter for a job.", "tailoring"),
    MCPTool("answer_application_questions", "Generate answers for common application questions.", "tailoring"),
    MCPTool("apply_linkedin_job", "Execute LinkedIn Easy Apply through the connector.", "browser"),
    MCPTool("diagnose_linkedin_easy_apply", "Open a LinkedIn job URL and verify session, Easy Apply availability and submit readiness.", "browser"),
    MCPTool("discover_linkedin_jobs", "Read authenticated LinkedIn search results and preview Easy Apply jobs for the confirmed profile focus.", "browser"),
    MCPTool("repair_linkedin_jobs", "Re-open low-quality LinkedIn job records and refresh title, company, location and description from the authenticated session.", "browser"),
    MCPTool("purge_low_fit_linkedin_jobs", "Remove stale LinkedIn jobs with low fit and no real application progress.", "browser"),
    MCPTool("apply_gupy_job", "Execute Gupy applications through the connector.", "browser"),
    MCPTool("apply_greenhouse_job", "Execute Greenhouse applications through the connector.", "browser"),
    MCPTool("apply_lever_job", "Execute Lever applications through the connector.", "browser"),
    MCPTool("apply_generic_external_job", "Fallback external connector with guarded submit behavior.", "browser"),
    MCPTool("sync_gmail_updates", "Read inbox updates and reconcile application statuses.", "email"),
    MCPTool("get_application_status", "Return application status, executions and inbox events.", "read"),
    MCPTool("capture_browser_checkpoint", "Persist a checkpoint entry for the current execution.", "browser"),
]


def list_tools() -> list[dict[str, str]]:
    return [asdict(tool) for tool in TOOLS]
