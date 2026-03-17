from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app
from src.core.config import get_settings
from src.domain.models import ApplicationRecord
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository


def _setup(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "agent.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("USER_ID", "default")
    get_settings.cache_clear()
    init_db()


def _seed_job(repo: TrackerRepository) -> None:
    repo.upsert_job(
        id="job-apply",
        user_id="default",
        run_id="run-1",
        external_id="linkedin-1",
        source="manual",
        url="https://www.linkedin.com/jobs/view/123",
        title="Software Engineer",
        company="Acme",
        location="Remote",
        description="No captcha here, regular application flow.",
        score=90,
        score_reasons="",
        anchors_json="{}",
        score_breakdown_json="{}",
        recommendation="APPLY",
        status="new",
    )
    repo.upsert_application(ApplicationRecord(id="app-job-apply", job_id="job-apply", status="prepared"), link="https://www.linkedin.com/jobs/view/123", user_id="default", connector="linkedin")


def _seed_secondary_job(repo: TrackerRepository) -> None:
    repo.upsert_job(
        id="job-apply-2",
        user_id="default",
        run_id="run-1",
        external_id="greenhouse-1",
        source="manual",
        url="https://boards.greenhouse.io/betacorp/jobs/456",
        title="Backend Engineer",
        company="Beta Corp",
        location="Remote",
        description="Regular application flow.",
        score=86,
        score_reasons="",
        anchors_json="{}",
        score_breakdown_json="{}",
        recommendation="APPLY",
        status="new",
    )
    repo.upsert_application(ApplicationRecord(id="app-job-apply-2", job_id="job-apply-2", status="prepared"), link="https://boards.greenhouse.io/betacorp/jobs/456", user_id="default", connector="greenhouse")


def test_apply_endpoint_creates_execution_and_artifacts(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with get_session() as session:
        _seed_job(TrackerRepository(session))

    client = TestClient(app)
    response = client.post("/applications/apply", json={"job_id": "job-apply"})

    assert response.status_code == 200
    body = response.json()
    assert body["connector"] == "linkedin"
    assert body["answers_generated"] >= 1
    assert body["status"] == "paused"
    assert body["current_step"] == "submit"
    assert body["pause_reason"] == "manual_review_before_submit"
    assert body["recommended_action"]
    assert body["fit_summary"]


def test_resume_execution_completes_paused_application(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with get_session() as session:
        _seed_job(TrackerRepository(session))

    client = TestClient(app)
    apply_response = client.post("/applications/apply", json={"job_id": "job-apply"})
    assert apply_response.status_code == 200
    execution_id = apply_response.json()["execution_id"]

    resume_response = client.post(f"/runs/{execution_id}/resume")

    assert resume_response.status_code == 200
    body = resume_response.json()
    assert body["status"] == "completed"
    assert body["current_step"] == "checkpoint"
    assert body["retry_count"] == 1

    with get_session() as session:
        repo = TrackerRepository(session)
        application = repo.get_application("app-job-apply", user_id="default")
        execution = repo.get_execution_run(execution_id, user_id="default")

    assert application is not None
    assert execution is not None
    assert application.status == "applied"
    assert execution.status == "completed"
    assert execution.pause_reason == ""
    assert execution.retry_count == 1


def test_profile_endpoint_reads_default_profile(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    client = TestClient(app)
    response = client.get("/profile")

    assert response.status_code == 200
    body = response.json()
    assert "profile" in body
    assert "name" in body["profile"]


def test_profile_chat_updates_brain_memory(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/profile/chat",
        json={"message": "Agora quero focar em vaga junior backend remota e terminei um projeto com FastAPI e PostgreSQL."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"]
    assert body["brain"]["profile"]["target_role"] == "junior"
    assert any(item["kind"] == "project" for item in body["brain"]["memory_items"])
    assert any(turn["role"] == "user" for turn in body["brain"]["conversation"])

    snapshot = client.get("/profile/brain")
    assert snapshot.status_code == 200
    brain = snapshot.json()
    assert any("fastapi" in stack.lower() for stack in brain["profile"]["stacks"])
    assert any(evidence["source"] == "chat" for evidence in brain["evidences"])


def test_profile_imports_github_repositories(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    class FakeRepo:
        def __init__(self, name: str, html_url: str, description: str, language: str, topics: list[str], stargazers_count: int, fork: bool, pushed_at: str):
            self.name = name
            self.html_url = html_url
            self.description = description
            self.language = language
            self.topics = topics
            self.stargazers_count = stargazers_count
            self.fork = fork
            self.pushed_at = pushed_at

    monkeypatch.setattr(
        "src.services.github_profile_service._fetch_repositories",
        lambda settings, username: [
            FakeRepo(
                name="portfolio-api",
                html_url="https://github.com/test/portfolio-api",
                description="API com FastAPI e PostgreSQL para portfolio.",
                language="Python",
                topics=["fastapi", "postgresql", "backend"],
                stargazers_count=3,
                fork=False,
                pushed_at="2026-03-16T12:00:00Z",
            )
        ],
    )

    client = TestClient(app)
    response = client.post("/profile/import/github", json={"github_url": "https://github.com/test"})

    assert response.status_code == 200
    body = response.json()
    assert body["github_username"] == "test"
    assert body["imported_repositories"] == 1
    assert any(project["name"] == "portfolio-api" for project in body["brain"]["profile"]["projects"])
    assert any(item["source"] == "github" for item in body["brain"]["memory_items"])


def test_profile_imports_linkedin_profile(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    monkeypatch.setattr(
        "src.services.linkedin_profile_service.LinkedInPlaywrightRuntime.scrape_profile",
        lambda self, url: {
            "status": "completed",
            "summary": "Perfil do LinkedIn lido com a sessao persistente.",
            "screenshot_path": "",
            "snapshot_path": "",
            "data": {
                "name": "Guilherme Teste",
                "headline": "Desenvolvedor Backend Junior | FastAPI | Python",
                "location": "Sao Paulo, Brasil",
                "about": "Construo produtos backend com foco em entrega e automacao.",
                "experiences": [
                    ["Backend Intern @ Acme", "2025 - Atual", "FastAPI", "PostgreSQL"],
                ],
            },
        },
    )

    client = TestClient(app)
    response = client.post("/profile/import/linkedin", json={"linkedin_url": "https://www.linkedin.com/in/teste"})

    assert response.status_code == 200
    body = response.json()
    assert body["linkedin_url"] == "https://www.linkedin.com/in/teste"
    assert body["brain"]["profile"]["name"] == "Guilherme Teste"
    assert any("Backend Intern" in item["company"] for item in body["brain"]["profile"]["experiences"])
    assert any(item["source"] == "linkedin" for item in body["brain"]["memory_items"])


def test_profile_brain_exposes_conflicts_between_sources(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    monkeypatch.setattr(
        "src.services.linkedin_profile_service.LinkedInPlaywrightRuntime.scrape_profile",
        lambda self, url: {
            "status": "completed",
            "summary": "Perfil do LinkedIn lido com a sessao persistente.",
            "screenshot_path": "",
            "snapshot_path": "",
            "data": {
                "name": "Guilherme Teste",
                "headline": "Desenvolvedor Full Stack Pleno | React | Node.js",
                "location": "Sao Paulo presencial",
                "about": "Atuo com stack full stack em produto B2B.",
                "experiences": [],
            },
        },
    )

    client = TestClient(app)
    chat_response = client.post(
        "/profile/chat",
        json={"message": "Agora quero focar em vaga junior backend remota com FastAPI e Python."},
    )
    assert chat_response.status_code == 200

    import_response = client.post("/profile/import/linkedin", json={"linkedin_url": "https://www.linkedin.com/in/teste"})
    assert import_response.status_code == 200

    brain_response = client.get("/profile/brain")
    assert brain_response.status_code == 200
    conflicts = brain_response.json()["conflicts"]
    assert any(conflict["field"] == "target_role" for conflict in conflicts)
    assert any(conflict["field"] == "location" for conflict in conflicts)


def test_profile_conflict_resolution_confirms_choice(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    monkeypatch.setattr(
        "src.services.linkedin_profile_service.LinkedInPlaywrightRuntime.scrape_profile",
        lambda self, url: {
            "status": "completed",
            "summary": "Perfil do LinkedIn lido com a sessao persistente.",
            "screenshot_path": "",
            "snapshot_path": "",
            "data": {
                "name": "Guilherme Teste",
                "headline": "Desenvolvedor Full Stack Pleno | React | Node.js",
                "location": "Sao Paulo presencial",
                "about": "Atuo com stack full stack em produto B2B.",
                "experiences": [],
            },
        },
    )

    client = TestClient(app)
    client.post("/profile/chat", json={"message": "Agora quero focar em vaga junior backend remota com FastAPI e Python."})
    client.post("/profile/import/linkedin", json={"linkedin_url": "https://www.linkedin.com/in/teste"})

    resolve_response = client.post("/profile/conflicts/resolve", json={"field": "target_role", "chosen_value": "junior"})

    assert resolve_response.status_code == 200
    body = resolve_response.json()
    assert body["brain"]["profile"]["target_role"] == "junior"
    assert all(conflict["field"] != "target_role" for conflict in body["brain"]["conflicts"])


def test_email_sync_updates_status(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with get_session() as session:
        _seed_job(TrackerRepository(session))

    client = TestClient(app)
    response = client.post("/email/sync", json={"messages": [{"sender": "talent@acme.com", "subject": "Interview invitation", "snippet": "Lets schedule an interview."}]})

    assert response.status_code == 200
    assert response.json()["updated"] == 1


def test_email_sync_matches_the_correct_application(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with get_session() as session:
        repo = TrackerRepository(session)
        _seed_job(repo)
        _seed_secondary_job(repo)

    client = TestClient(app)
    response = client.post(
        "/email/sync",
        json={
            "messages": [
                {
                    "sender": "talent@betacorp.com",
                    "subject": "Backend Engineer interview invitation",
                    "snippet": "Beta Corp would like to schedule an interview.",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 1

    with get_session() as session:
        repo = TrackerRepository(session)
        first_application = repo.get_application("app-job-apply", user_id="default")
        second_application = repo.get_application("app-job-apply-2", user_id="default")
        email_events = repo.list_email_events(user_id="default")

    assert first_application is not None
    assert second_application is not None
    assert first_application.status == "prepared"
    assert second_application.status == "interview"
    assert len(email_events) == 1
    assert email_events[0].application_id == "app-job-apply-2"


def test_apply_endpoint_pauses_on_captcha(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with get_session() as session:
        repo = TrackerRepository(session)
        repo.upsert_job(
            id="job-captcha",
            user_id="default",
            run_id="run-1",
            external_id="linkedin-2",
            source="manual",
            url="https://www.linkedin.com/jobs/view/999",
            title="Software Engineer",
            company="Acme",
            location="Remote",
            description="Application flow contains captcha verification before final submit.",
            score=90,
            score_reasons="",
            anchors_json="{}",
            score_breakdown_json="{}",
            recommendation="APPLY",
            status="new",
        )
        repo.upsert_application(ApplicationRecord(id="app-job-captcha", job_id="job-captcha", status="prepared"), link="https://www.linkedin.com/jobs/view/999", user_id="default", connector="linkedin")

    client = TestClient(app)
    response = client.post("/applications/apply", json={"job_id": "job-captcha"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paused"
    assert body["pause_reason"] == "captcha_detected"
    assert "captcha" in body["recommended_action"].lower()


def test_apply_endpoint_pauses_on_low_confidence_answers(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with get_session() as session:
        repo = TrackerRepository(session)
        repo.upsert_job(
            id="job-salary",
            user_id="default",
            run_id="run-1",
            external_id="greenhouse-2",
            source="manual",
            url="https://boards.greenhouse.io/acme/jobs/888",
            title="Backend Engineer",
            company="Acme",
            location="Remote",
            description="Please include your expected salary expectation in the application form.",
            score=88,
            score_reasons="",
            anchors_json="{}",
            score_breakdown_json="{}",
            recommendation="APPLY",
            status="new",
        )
        repo.upsert_application(ApplicationRecord(id="app-job-salary", job_id="job-salary", status="prepared"), link="https://boards.greenhouse.io/acme/jobs/888", user_id="default", connector="greenhouse")

    client = TestClient(app)
    response = client.post("/applications/apply", json={"job_id": "job-salary"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paused"
    assert body["current_step"] == "answer_questions"
    assert body["pause_reason"] == "low_confidence_answer"
    assert "revisar" in body["recommended_action"].lower()


def test_pending_actions_route_returns_execution_and_email_items(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with get_session() as session:
        repo = TrackerRepository(session)
        _seed_job(repo)
        repo.create_execution_run(
            execution_id="exec-1",
            application_id="app-job-apply",
            job_id="job-apply",
            connector="linkedin",
            phase="application",
            status="paused",
            user_id="default",
        )
        repo.update_execution_run("exec-1", current_step="submit", pause_reason="captcha_detected")
        repo.create_email_event(
            event_id="mail-1",
            application_id="app-job-apply",
            provider="gmail",
            external_id="gmail-1",
            subject="Interview invitation",
            sender="talent@acme.com",
            snippet="Please choose a time slot.",
            status_inferred="interview",
            action_required=True,
            raw_payload={},
            user_id="default",
        )

    client = TestClient(app)
    response = client.get("/dashboard/pending-actions")

    assert response.status_code == 200
    body = response.json()
    kinds = {item["kind"] for item in body}
    assert "execution_pause" in kinds
    assert "email_followup" in kinds


def test_apply_endpoint_respects_retry_backoff(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    monkeypatch.setenv("MAX_RETRIES_PER_CONNECTOR", "1")
    get_settings.cache_clear()
    init_db()
    with get_session() as session:
        repo = TrackerRepository(session)
        _seed_job(repo)
        repo.create_execution_run(
            execution_id="failed-1",
            application_id="app-job-apply",
            job_id="job-apply",
            connector="linkedin",
            phase="application",
            status="failed",
            user_id="default",
        )
        repo.update_execution_run("failed-1", current_step="submit", error_message="timeout")

    client = TestClient(app)
    response = client.post("/applications/apply", json={"job_id": "job-apply"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paused"
    assert body["pause_reason"] == "retry_backoff"


def test_apply_endpoint_blocks_stale_session(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with get_session() as session:
        repo = TrackerRepository(session)
        _seed_job(repo)
        repo.upsert_browser_session(
            session_id="default:linkedin",
            platform="linkedin",
            state="stale",
            profile_dir="artifacts/browser/linkedin",
            user_id="default",
        )

    client = TestClient(app)
    response = client.post("/applications/apply", json={"job_id": "job-apply"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paused"
    assert body["pause_reason"] == "session_invalid"


def test_live_linkedin_connector_pauses_when_playwright_is_missing(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    monkeypatch.setenv("LIVE_BROWSER_ENABLED", "true")
    get_settings.cache_clear()
    init_db()
    from src.autopilot.linkedin_easy_apply import LinkedInPlaywrightRuntime

    def fail_playwright(*args, **kwargs):
        raise RuntimeError("playwright_not_installed")

    monkeypatch.setattr(LinkedInPlaywrightRuntime, "_ensure_page", fail_playwright)
    with get_session() as session:
        _seed_job(TrackerRepository(session))

    client = TestClient(app)
    response = client.post("/applications/apply", json={"job_id": "job-apply"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paused"
    assert body["pause_reason"] == "browser_dependency_missing"


def test_linkedin_diagnostic_route(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    def fake_diagnostic(repo, settings, job_url):
        return {
            "step": "submit",
            "status": "paused",
            "message": "LinkedIn pronto para envio final.",
            "pause_reason": "manual_review_before_submit",
            "recommended_action": "Revisar os artefatos e confirmar a submissao final.",
            "screenshot_path": "artifacts/browser/linkedin/test.png",
            "snapshot_path": "artifacts/browser/linkedin/test.html",
        }

    monkeypatch.setattr("src.api.routes.mcp.run_linkedin_diagnostic", fake_diagnostic)
    client = TestClient(app)
    response = client.post("/mcp/linkedin/diagnose", params={"job_url": "https://www.linkedin.com/jobs/view/123"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paused"
    assert body["pause_reason"] == "manual_review_before_submit"


def test_linkedin_diagnostic_route_validates_url(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    client = TestClient(app)
    response = client.post("/mcp/linkedin/diagnose", params={"job_url": "https://example.com/job"})

    assert response.status_code == 400
    assert response.json()["detail"] == "job_url must be a LinkedIn job URL"


def test_linkedin_session_setup_route(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    def fake_setup(repo, settings):
        return {
            "step": "prepare",
            "status": "paused",
            "message": "LinkedIn exige autenticacao.",
            "pause_reason": "session_setup_required",
            "recommended_action": "Abrir a sessao persistente da plataforma e concluir o login manualmente.",
            "screenshot_path": "artifacts/browser/linkedin/setup.png",
            "snapshot_path": "artifacts/browser/linkedin/setup.html",
        }

    monkeypatch.setattr("src.api.routes.mcp.run_linkedin_session_setup", fake_setup)
    client = TestClient(app)
    response = client.post("/mcp/linkedin/session/setup")

    assert response.status_code == 200
    body = response.json()
    assert body["step"] == "prepare"
    assert body["pause_reason"] == "session_setup_required"


def test_linkedin_discovery_preview_route(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    def fake_preview(repo, settings, limit):
        return {
            "status": "completed",
            "message": "Foram capturadas 2 vagas do LinkedIn para o foco confirmado.",
            "effective_profile": {
                "target_role": "Junior Backend",
                "location": "remoto",
                "stacks": ["Python", "FastAPI"],
            },
            "jobs": [
                {
                    "url": "https://www.linkedin.com/jobs/view/1",
                    "title": "Backend Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "description": "Need Python and FastAPI",
                }
            ],
        }

    monkeypatch.setattr("src.api.routes.mcp.run_linkedin_discovery_preview", fake_preview)
    client = TestClient(app)
    response = client.post("/mcp/linkedin/discover", params={"limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["effective_profile"]["target_role"] == "Junior Backend"
    assert len(body["jobs"]) == 1


def test_linkedin_repair_route(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    def fake_repair(repo, settings, limit):
        return {
            "status": "completed",
            "message": "Foram reparadas 2 vagas antigas do LinkedIn.",
            "repaired_jobs": [
                {"id": "job-1", "url": "https://www.linkedin.com/jobs/view/1", "title": "Backend Engineer", "company": "Acme"}
            ],
        }

    monkeypatch.setattr("src.api.routes.mcp.repair_linkedin_jobs", fake_repair)
    client = TestClient(app)
    response = client.post("/mcp/linkedin/repair", params={"limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["repaired_jobs"]) == 1


def test_linkedin_purge_route(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    def fake_purge(repo, user_id, limit):
        return {
            "status": "completed",
            "message": "Foram removidas 2 vagas LinkedIn de baixo fit.",
            "purged_jobs": [
                {"id": "job-1", "title": "Content Reviewer", "company": "Acme"}
            ],
        }

    monkeypatch.setattr("src.api.routes.mcp.purge_low_fit_linkedin_jobs", fake_purge)
    client = TestClient(app)
    response = client.post("/mcp/linkedin/purge", params={"limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["purged_jobs"]) == 1


def test_apply_shortlist_route(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    def fake_apply_shortlist(repo, settings, user_id, limit):
        return {
            "status": "completed",
            "message": "Shortlist executada para 2 vagas APPLY.",
            "results": [
                {
                    "job_id": "job-1",
                    "title": "Backend Engineer",
                    "company": "Acme",
                    "status": "paused",
                    "execution_id": "exec-1",
                    "pause_reason": "manual_review_before_submit",
                }
            ],
        }

    monkeypatch.setattr("src.api.routes.applications.apply_shortlist", fake_apply_shortlist)
    client = TestClient(app)
    response = client.post("/applications/apply-shortlist", json={"limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["results"]) == 1


def test_apply_selected_route(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    def fake_apply_selected(repo, settings, user_id, job_ids):
        return {
            "status": "completed",
            "message": "Selecao executada para 1 vagas APPLY.",
            "results": [
                {
                    "job_id": "job-1",
                    "title": "Backend Engineer",
                    "company": "Acme",
                    "status": "paused",
                    "execution_id": "exec-1",
                    "pause_reason": "manual_review_before_submit",
                }
            ],
        }

    monkeypatch.setattr("src.api.routes.applications.apply_selected_jobs", fake_apply_selected)
    client = TestClient(app)
    response = client.post("/applications/apply-selected", json={"job_ids": ["job-1"]})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["results"]) == 1


def test_shortlist_preview_route(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)

    class Row:
        id = "job-1"
        title = "Backend Engineer"
        company = "Acme"
        score = 92
        source = "manual"
        url = "https://example.com/job-1"

    monkeypatch.setattr("src.api.routes.applications.shortlist_candidates", lambda repo, user_id, limit: [Row()])
    client = TestClient(app)
    response = client.get("/applications/shortlist-preview", params={"limit": 3})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Backend Engineer"


def test_dashboard_includes_recent_shortlist_results(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with get_session() as session:
        repo = TrackerRepository(session)
        _seed_job(repo)
        repo.upsert_application(ApplicationRecord(id="app-job-apply", job_id="job-apply", status="prepared"), link="https://www.linkedin.com/jobs/view/123", user_id="default", connector="linkedin")
        repo.create_execution_run(
            execution_id="exec-shortlist-1",
            application_id="app-job-apply",
            job_id="job-apply",
            connector="linkedin",
            phase="application",
            status="paused",
            trigger="shortlist",
            user_id="default",
        )
        repo.update_execution_run("exec-shortlist-1", current_step="submit", pause_reason="manual_review_before_submit")

    client = TestClient(app)
    response = client.get("/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert len(body["recent_shortlist_results"]) == 1
    assert body["recent_shortlist_results"][0]["id"] == "exec-shortlist-1"


def test_mcp_discover_jobs_uses_effective_profile(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    client = TestClient(app)

    client.post("/profile/conflicts/resolve", json={"field": "target_role", "chosen_value": "Junior Backend"})
    client.post("/profile/conflicts/resolve", json={"field": "location", "chosen_value": "remoto"})
    client.post("/profile/conflicts/resolve", json={"field": "stacks", "chosen_value": "Python, FastAPI, SQL"})

    captured: dict[str, object] = {}

    def fake_run_pipeline(profile, sources, limit, rss_urls, manual_urls, artifacts_dir=None):
        captured["target_role"] = profile.target_role
        captured["location"] = profile.location
        captured["stacks"] = profile.stacks
        return "run-effective-profile"

    monkeypatch.setattr("src.api.routes.mcp.run_pipeline", fake_run_pipeline)

    response = client.post(
        "/mcp/jobs/discover",
        json={"sources": ["manual"], "limit": 1, "manual_urls": ["https://example.com/job"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run-effective-profile"
    assert body["effective_profile"]["target_role"] == "Junior Backend"
    assert captured["target_role"] == "Junior Backend"
    assert captured["location"] == "remoto"
    assert captured["stacks"] == ["Python", "FastAPI", "SQL"]
