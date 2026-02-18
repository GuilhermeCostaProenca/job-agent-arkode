from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import typer

from src.core.config import get_settings
from src.domain.hiring_signals import detect_hiring_signal
from src.domain.models import ApplicationRecord
from src.domain.pipeline import breakdown_for_job, export_jobs_csv, run_pipeline
from src.domain.preference_engine import DEFAULT_WEIGHTS, load_preference_model
from src.domain.profile_loader import load_profile
from src.domain.reasons import APPROVED_REASONS, REJECTED_REASONS, is_valid_reason
from src.domain.signals import Signal, record_signal
from src.domain.writing_style import compute_writing_delta
from src.ingest.sources.feed_manual import load_feed_items_from_file, load_feed_items_from_url
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository

app = typer.Typer(help="Job Agent Arkode CLI")
signal_app = typer.Typer(help="Signal commands")
preferences_app = typer.Typer(help="Preferences commands")
feed_app = typer.Typer(help="Feed hunter commands")
app.add_typer(signal_app, name="signal")
app.add_typer(preferences_app, name="preferences")
app.add_typer(feed_app, name="feed")


def _record_job_signal(job_id: str, signal_type: str, payload: dict[str, object]) -> None:
    settings = get_settings()
    with get_session() as session:
        repo = TrackerRepository(session)
        record_signal(
            repo,
            Signal(
                signal_type=signal_type,
                job_id=job_id,
                payload=payload,
                user_id=settings.user_id,
            ),
        )


def _set_application_status(job_id: str, status: str, notes: str = "") -> None:
    settings = get_settings()
    with get_session() as session:
        repo = TrackerRepository(session)
        updated = repo.update_application_status(
            job_id, status, notes=notes, user_id=settings.user_id
        )
        if updated is None:
            repo.upsert_application(
                ApplicationRecord(id=f"app-{job_id}", job_id=job_id, status=status),
                link="",
                notes=notes,
                user_id=settings.user_id,
            )


@app.command()
def run(
    sources: str = typer.Option("rss,manual", help="Comma-separated sources: rss,manual"),
    limit: int = typer.Option(30, help="Max jobs per run"),
    rss_feed: str = typer.Option("https://stackoverflow.com/jobs/feed", help="RSS URL"),
    manual_url: list[str] = typer.Option([], help="Manual URL(s) for job descriptions"),
) -> None:
    init_db()
    settings = get_settings()
    profile = load_profile(settings.profile_path)
    run_id = run_pipeline(
        profile=profile,
        sources=[item.strip() for item in sources.split(",")],
        limit=limit,
        rss_urls=[rss_feed],
        manual_urls=manual_url,
    )
    typer.echo(f"Run completed: {run_id}")


@app.command(name="list")
def list_jobs(
    top: int = typer.Option(20),
    min_score: int = typer.Option(0),
    explore: bool = typer.Option(False, help="Enable 80/20 exploration mode"),
) -> None:
    settings = get_settings()
    with get_session() as session:
        rows = TrackerRepository(session).list_recommendations(
            limit=top,
            min_score=min_score,
            user_id=settings.user_id,
            explore=explore,
        )
    for item in rows:
        row = item["job"]
        breakdown = breakdown_for_job(row)
        extra = " [exploration]" if item["is_exploration"] else ""
        typer.echo(
            f"{row.id} | score: {row.score} | {row.company} | {row.title}{extra}\n"
            f"[skills +{breakdown.get('skill_match_score', 0)} | "
            f"seniority +{breakdown.get('seniority_score', 0)} | "
            f"location +{breakdown.get('location_score', 0)} | "
            f"keywords +{breakdown.get('keyword_density_score', 0)} | "
            f"red_flags -{breakdown.get('red_flag_penalty', 0)}]"
        )


@app.command()
def artifacts(job_id: str) -> None:
    settings = get_settings()
    with get_session() as session:
        rows = TrackerRepository(session).list_artifacts(job_id, user_id=settings.user_id)
    for row in rows:
        typer.echo(f"{row.kind}: {row.path}")


@app.command()
def approve(
    approval_id: str,
    yes: bool = typer.Option(False),
    no: bool = typer.Option(False),
    reason: str = typer.Option("like_role"),
    notes: str = typer.Option(""),
) -> None:
    settings = get_settings()
    if yes == no:
        raise typer.BadParameter("Use exactly one of --yes or --no")
    if yes and reason not in APPROVED_REASONS:
        raise typer.BadParameter(f"Invalid approved reason. Allowed: {sorted(APPROVED_REASONS)}")
    if no and reason not in REJECTED_REASONS:
        raise typer.BadParameter(f"Invalid rejected reason. Allowed: {sorted(REJECTED_REASONS)}")

    status = "approved" if yes else "rejected"
    signal_type = "approval" if yes else "rejection"
    with get_session() as session:
        repo = TrackerRepository(session)
        updated = repo.update_approval_status(approval_id, status)
        if not updated:
            typer.echo("Approval not found")
            raise typer.Exit(code=1)
        record_signal(
            repo,
            Signal(
                signal_type=signal_type,
                job_id=updated.job_id,
                payload={"approval_id": approval_id, "reason": reason, "notes": notes},
                run_id=updated.run_id,
                user_id=settings.user_id,
            ),
        )
    typer.echo(f"Approval {approval_id} -> {status}")


@app.command()
def reject(
    job_id: str, reason: str = typer.Option("stack_mismatch"), notes: str = typer.Option("")
) -> None:
    if not is_valid_reason(reason) or reason not in REJECTED_REASONS:
        raise typer.BadParameter(f"Invalid rejection reason. Allowed: {sorted(REJECTED_REASONS)}")
    _set_application_status(job_id, "rejected", notes=notes)
    _record_job_signal(job_id, "rejection", {"reason": reason, "notes": notes})
    typer.echo(f"Job {job_id} marked as rejected")


@app.command()
def applied(job_id: str) -> None:
    _set_application_status(job_id, "applied")
    _record_job_signal(job_id, "applied", {})
    typer.echo(f"Job {job_id} marked as applied")


@app.command()
def replied(job_id: str, channel: str = typer.Option("email")) -> None:
    _set_application_status(job_id, "replied", notes=f"channel={channel}")
    _record_job_signal(job_id, "replied", {"channel": channel})
    typer.echo(f"Job {job_id} marked as replied via {channel}")


@app.command()
def interview(
    job_id: str,
    date_value: str = typer.Option(..., "--date"),
    notes: str = typer.Option(""),
) -> None:
    parsed = date.fromisoformat(date_value)
    _set_application_status(job_id, "interview", notes=notes)
    _record_job_signal(job_id, "interview", {"date": parsed.isoformat(), "notes": notes})
    typer.echo(f"Job {job_id} marked as interview")


@app.command()
def offer(job_id: str, notes: str = typer.Option("")) -> None:
    _set_application_status(job_id, "offer", notes=notes)
    _record_job_signal(job_id, "offer", {"notes": notes})
    typer.echo(f"Job {job_id} marked as offer")


@signal_app.command("list")
def signal_list(last: int = typer.Option(50)) -> None:
    settings = get_settings()
    with get_session() as session:
        rows = TrackerRepository(session).list_signals(limit=last, user_id=settings.user_id)
    for row in rows:
        typer.echo(f"{row.created_at} | {row.job_id} | {row.signal_type} | {row.payload_json}")


@app.command()
def artifact_edit(
    job_id: str,
    name: str = typer.Option(...),
    file: Path = typer.Option(...),
) -> None:
    settings = get_settings()
    final_text = file.read_text(encoding="utf-8")
    with get_session() as session:
        repo = TrackerRepository(session)
        artifact = repo.find_artifact(job_id, name, user_id=settings.user_id)
        if artifact is None:
            raise typer.BadParameter("Artifact not found for job")
        original_text = Path(artifact.path).read_text(encoding="utf-8")
        delta = compute_writing_delta(original_text, final_text)
        repo.create_writing_delta(
            delta_id=str(uuid4()),
            job_id=job_id,
            artifact_name=name,
            original_text=original_text,
            final_text=final_text,
            delta_json=delta,
            user_id=settings.user_id,
        )
        record_signal(
            repo,
            Signal(
                signal_type="artifact_edit",
                job_id=job_id,
                payload={"artifact_name": name, "delta": delta},
                user_id=settings.user_id,
            ),
        )
    typer.echo(f"Artifact edit captured for {job_id}:{name}")


@feed_app.command("add")
def feed_add(url: str | None = typer.Option(None), file: Path | None = typer.Option(None)) -> None:
    settings = get_settings()
    if not url and not file:
        raise typer.BadParameter("Provide --url or --file")

    items: list[dict[str, str]] = []
    if url:
        items.extend(load_feed_items_from_url(url))
    if file:
        items.extend(load_feed_items_from_file(file))

    with get_session() as session:
        repo = TrackerRepository(session)
        for item in items:
            text = item.get("text") or item.get("url", "")
            result = detect_hiring_signal(text)
            repo.create_feed_item(
                feed_id=str(uuid4()),
                source=item.get("source", "manual"),
                url=item.get("url", ""),
                text=text,
                is_hiring=result.is_hiring,
                confidence=result.confidence,
                user_id=settings.user_id,
            )
    typer.echo(f"Feed items added: {len(items)}")


@feed_app.command("list")
def feed_list(hiring_only: bool = typer.Option(False, "--hiring-only")) -> None:
    settings = get_settings()
    with get_session() as session:
        rows = TrackerRepository(session).list_feed_items(
            hiring_only=hiring_only, user_id=settings.user_id
        )
    for row in rows:
        typer.echo(f"{row.id} | hiring={row.is_hiring} | conf={row.confidence:.2f} | {row.url}")


@app.command()
def export(
    format: str = typer.Option("csv", help="Export format, currently only csv"),
    min_score: int = typer.Option(70),
) -> None:
    if format != "csv":
        raise typer.BadParameter("Only csv is supported in v0.4.0")
    path = export_jobs_csv(min_score=min_score, output_dir=Path("exports"))
    typer.echo(f"Export created: {path}")


@app.command()
def followups() -> None:
    settings = get_settings()
    today = datetime.now(UTC).date()
    with get_session() as session:
        rows = TrackerRepository(session).list_due_followups(today, user_id=settings.user_id)
    if not rows:
        typer.echo("No follow-ups due.")
        return
    for row in rows:
        typer.echo(
            f"{row.id} | {row.job_id} | {row.status} | due: {row.follow_up_date} | {row.link}"
        )


@preferences_app.command("show")
def preferences_show() -> None:
    settings = get_settings()
    with get_session() as session:
        repo = TrackerRepository(session)
        model = load_preference_model(repo, user_id=settings.user_id)
    typer.echo(str(model.weights))


@preferences_app.command("reset")
def preferences_reset() -> None:
    settings = get_settings()
    with get_session() as session:
        repo = TrackerRepository(session)
        repo.upsert_preference_model("default", DEFAULT_WEIGHTS, user_id=settings.user_id)
    typer.echo("Preferences reset to defaults")


if __name__ == "__main__":
    app()
