from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from src.autopilot.linkedin_easy_apply import LinkedInPlaywrightRuntime
from src.autopilot.playwright_runner import run_autopilot_preview
from src.domain.models import ConnectorType, ExecutionCheckpoint
from src.domain.pause_control import build_pause_context


@dataclass(slots=True)
class ApplicationContext:
    application_url: str
    resume_path: Path
    html_snapshot: str
    browser_profile_dir: Path
    artifacts_dir: Path
    live_browser_enabled: bool = False
    headless: bool = True
    answers: dict[str, str] = field(default_factory=dict)
    effective_profile: dict[str, object] = field(default_factory=dict)


class BaseConnector:
    connector_type: ConnectorType = ConnectorType.GENERIC_EXTERNAL
    domains: tuple[str, ...] = ()

    def probe(self, job_url: str) -> str:
        host = urlparse(job_url).netloc.lower()
        return "high" if any(domain in host for domain in self.domains) else "none"

    def prepare(self, context: ApplicationContext) -> ExecutionCheckpoint:
        return ExecutionCheckpoint(step="prepare", status="completed", message=f"{self.connector_type.value} connector selected")

    def fill_form(self, context: ApplicationContext) -> ExecutionCheckpoint:
        return ExecutionCheckpoint(step="fill_form", status="completed", message="Base fields prepared for application")

    def upload_artifacts(self, context: ApplicationContext) -> ExecutionCheckpoint:
        return ExecutionCheckpoint(step="upload_artifacts", status="completed", message=f"Resume staged from {context.resume_path}")

    def answer_questions(self, context: ApplicationContext) -> ExecutionCheckpoint:
        return ExecutionCheckpoint(step="answer_questions", status="completed", message="Generated answers attached to execution context")

    def submit(self, context: ApplicationContext, allow_submit: bool = False) -> ExecutionCheckpoint:
        result = run_autopilot_preview(context.application_url, context.resume_path, context.html_snapshot, allow_submit=allow_submit)
        return ExecutionCheckpoint(step="submit", status=result["status"], message=result["summary"], payload=result)

    def checkpoint(self, context: ApplicationContext) -> ExecutionCheckpoint:
        return ExecutionCheckpoint(step="checkpoint", status="completed", message="Checkpoint captured for audit trail")

    def close(self) -> None:
        return None


class LinkedInConnector(BaseConnector):
    connector_type = ConnectorType.LINKEDIN
    domains = ("linkedin.com",)

    def __init__(self) -> None:
        self._runtime: LinkedInPlaywrightRuntime | None = None

    def prepare(self, context: ApplicationContext) -> ExecutionCheckpoint:
        if not context.live_browser_enabled:
            return super().prepare(context)
        result = self._run_real("prepare", lambda runtime: runtime.open_job(context.application_url), context)
        return ExecutionCheckpoint(
            step="prepare",
            status=result["status"],
            message=result["summary"],
            screenshot_path=result.get("screenshot_path"),
            snapshot_path=result.get("snapshot_path"),
            payload=result,
        )

    def fill_form(self, context: ApplicationContext) -> ExecutionCheckpoint:
        if not context.live_browser_enabled:
            return super().fill_form(context)
        result = self._run_real("fill_form", lambda runtime: runtime.ensure_easy_apply(context.application_url), context)
        return ExecutionCheckpoint(
            step="fill_form",
            status=result["status"],
            message=result["summary"],
            screenshot_path=result.get("screenshot_path"),
            snapshot_path=result.get("snapshot_path"),
            payload=result,
        )

    def upload_artifacts(self, context: ApplicationContext) -> ExecutionCheckpoint:
        if not context.live_browser_enabled:
            return super().upload_artifacts(context)
        result = self._run_real("upload_artifacts", lambda runtime: runtime.upload_resume(context.resume_path, context.application_url), context)
        return ExecutionCheckpoint(
            step="upload_artifacts",
            status=result["status"],
            message=result["summary"],
            screenshot_path=result.get("screenshot_path"),
            snapshot_path=result.get("snapshot_path"),
            payload=result,
        )

    def answer_questions(self, context: ApplicationContext) -> ExecutionCheckpoint:
        if not context.live_browser_enabled:
            return super().answer_questions(context)
        result = self._run_real(
            "answer_questions",
            lambda runtime: runtime.answer_questions(context.answers, context.effective_profile, context.application_url),
            context,
        )
        return ExecutionCheckpoint(
            step="answer_questions",
            status=result["status"],
            message=result["summary"],
            screenshot_path=result.get("screenshot_path"),
            snapshot_path=result.get("snapshot_path"),
            payload=result,
        )

    def submit(self, context: ApplicationContext, allow_submit: bool = False) -> ExecutionCheckpoint:
        if not context.live_browser_enabled:
            return super().submit(context, allow_submit=allow_submit)
        result = self._run_real("submit", lambda runtime: runtime.advance_or_submit(context.application_url, allow_submit=allow_submit), context)
        return ExecutionCheckpoint(
            step="submit",
            status=result["status"],
            message=result["summary"],
            screenshot_path=result.get("screenshot_path"),
            snapshot_path=result.get("snapshot_path"),
            payload=result,
        )

    def checkpoint(self, context: ApplicationContext) -> ExecutionCheckpoint:
        if not context.live_browser_enabled:
            return super().checkpoint(context)
        result = self._run_real(
            "checkpoint",
            lambda runtime: _linkedin_checkpoint_payload(runtime),
            context,
        )
        return ExecutionCheckpoint(
            step="checkpoint",
            status=result["status"],
            message=result["summary"],
            screenshot_path=result.get("screenshot_path"),
            snapshot_path=result.get("snapshot_path"),
            payload=result,
        )

    def close(self) -> None:
        if self._runtime is not None:
            self._runtime.close()
            self._runtime = None

    def _run_real(self, _: str, action: Callable[[LinkedInPlaywrightRuntime], dict[str, str]], context: ApplicationContext) -> dict[str, str]:
        try:
            runtime = self._get_runtime(context)
            return action(runtime)
        except RuntimeError as exc:
            if str(exc) == "playwright_not_installed":
                return {
                    "status": "paused",
                    "summary": "Playwright nao esta instalado no ambiente Python.",
                    **build_pause_context("browser_dependency_missing"),
                }
            raise

    def _get_runtime(self, context: ApplicationContext) -> LinkedInPlaywrightRuntime:
        if self._runtime is None:
            self._runtime = LinkedInPlaywrightRuntime(
                profile_dir=context.browser_profile_dir,
                artifacts_dir=context.artifacts_dir,
                headless=context.headless,
            )
        return self._runtime


class GupyConnector(BaseConnector):
    connector_type = ConnectorType.GUPY
    domains = ("gupy.io", "gupy",)


class GreenhouseConnector(BaseConnector):
    connector_type = ConnectorType.GREENHOUSE
    domains = ("greenhouse.io", "boards.greenhouse",)


class LeverConnector(BaseConnector):
    connector_type = ConnectorType.LEVER
    domains = ("lever.co",)


class GenericConnector(BaseConnector):
    connector_type = ConnectorType.GENERIC_EXTERNAL

    def probe(self, job_url: str) -> str:
        return "medium"


CONNECTOR_TYPES = (
    LinkedInConnector,
    GupyConnector,
    GreenhouseConnector,
    LeverConnector,
    GenericConnector,
)


def choose_connector(job_url: str) -> BaseConnector:
    best_class: type[BaseConnector] = GenericConnector
    best_score = "none"
    ranking = {"none": 0, "medium": 1, "high": 2}
    for connector_class in CONNECTOR_TYPES:
        connector = connector_class()
        level = connector.probe(job_url)
        if ranking[level] > ranking[best_score]:
            best_class = connector_class
            best_score = level
    return best_class()


def _linkedin_checkpoint_payload(runtime: LinkedInPlaywrightRuntime) -> dict[str, str]:
    screenshot_path, snapshot_path = runtime.capture("linkedin-checkpoint")
    return {
        "status": "completed",
        "summary": "Checkpoint real do LinkedIn capturado.",
        "screenshot_path": screenshot_path,
        "snapshot_path": snapshot_path,
    }
