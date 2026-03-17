from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import applications, approvals, artifacts, dashboard, email, feed, jobs, mcp, profile, runs, signals
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs.router)
app.include_router(runs.router)
app.include_router(approvals.router)
app.include_router(artifacts.router)
app.include_router(signals.router)
app.include_router(applications.router)
app.include_router(feed.router)
app.include_router(profile.router)
app.include_router(dashboard.router)
app.include_router(email.router)
app.include_router(mcp.router)
