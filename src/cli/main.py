from datetime import UTC, datetime
from pathlib import Path

import typer

from src.core.config import get_settings
from src.domain.pipeline import breakdown_for_job, export_jobs_csv, run_pipeline
from src.domain.profile_loader import load_profile
from src.tracker.db import get_session, init_db
from src.tracker.repo import TrackerRepository

app = typer.Typer(help="Job Agent Arkode CLI")


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
def list_jobs(top: int = typer.Option(20), min_score: int = typer.Option(0)) -> None:
    with get_session() as session:
        rows = TrackerRepository(session).list_jobs(limit=top, min_score=min_score)
    for row in rows:
        breakdown = breakdown_for_job(row)
        typer.echo(
            f"{row.id} | score: {row.score} | {row.company} | {row.title}\n"
            f"[skills +{breakdown.get('skill_match_score', 0)} | "
            f"seniority +{breakdown.get('seniority_score', 0)} | "
            f"location +{breakdown.get('location_score', 0)} | "
            f"keywords +{breakdown.get('keyword_density_score', 0)} | "
            f"red_flags -{breakdown.get('red_flag_penalty', 0)}]"
        )


@app.command()
def artifacts(job_id: str) -> None:
    with get_session() as session:
        rows = TrackerRepository(session).list_artifacts(job_id)
    for row in rows:
        typer.echo(f"{row.kind}: {row.path}")


@app.command()
def approve(
    approval_id: str,
    yes: bool = typer.Option(False),
    no: bool = typer.Option(False),
) -> None:
    if yes == no:
        raise typer.BadParameter("Use exactly one of --yes or --no")
    status = "approved" if yes else "rejected"
    with get_session() as session:
        updated = TrackerRepository(session).update_approval_status(approval_id, status)
    if not updated:
        typer.echo("Approval not found")
        raise typer.Exit(code=1)
    typer.echo(f"Approval {approval_id} -> {status}")


@app.command()
def export(
    format: str = typer.Option("csv", help="Export format, currently only csv"),
    min_score: int = typer.Option(70),
) -> None:
    if format != "csv":
        raise typer.BadParameter("Only csv is supported in v0.2.0")
    path = export_jobs_csv(min_score=min_score, output_dir=Path("exports"))
    typer.echo(f"Export created: {path}")


@app.command()
def followups() -> None:
    today = datetime.now(UTC).date()
    with get_session() as session:
        rows = TrackerRepository(session).list_due_followups(today)
    if not rows:
        typer.echo("No follow-ups due.")
        return
    for row in rows:
        typer.echo(
            f"{row.id} | {row.job_id} | {row.status} | due: {row.follow_up_date} | {row.link}"
        )


if __name__ == "__main__":
    app()
