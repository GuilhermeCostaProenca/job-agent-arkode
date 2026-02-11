import typer

from src.core.config import get_settings
from src.domain.pipeline import run_pipeline
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
        typer.echo(f"{row.id} | {row.score} | {row.company} | {row.title}")


@app.command()
def artifacts(job_id: str) -> None:
    with get_session() as session:
        rows = TrackerRepository(session).list_artifacts(job_id)
    for row in rows:
        typer.echo(f"{row.kind}: {row.path}")


@app.command()
def approve(
    approval_id: str, yes: bool = typer.Option(False), no: bool = typer.Option(False)
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


if __name__ == "__main__":
    app()
