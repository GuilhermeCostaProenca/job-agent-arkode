from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from src.api.routes import applications, approvals, artifacts, feed, jobs, runs, signals
from src.core.logging import configure_logging
from src.tracker.db import init_db

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    init_db()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="job-agent-arkode", lifespan=lifespan)
app.include_router(jobs.router)
app.include_router(runs.router)
app.include_router(approvals.router)
app.include_router(artifacts.router)
app.include_router(signals.router)
app.include_router(applications.router)
app.include_router(feed.router)
