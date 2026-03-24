from contextlib import asynccontextmanager

from fastapi import FastAPI

from opendove.api.dependencies import (
    get_project_store,
    get_scheduler,
    register_project_sync_job,
    register_worker_job,
)
from opendove.api.routers import projects, tasks

_scheduler = get_scheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    _scheduler.start()
    for project in get_project_store().list_projects():
        register_project_sync_job(project)
    register_worker_job()
    yield
    _scheduler.shutdown()


app = FastAPI(title="OpenDove", version="0.1.0", lifespan=lifespan)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
