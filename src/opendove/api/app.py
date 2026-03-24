from fastapi import FastAPI

from opendove.api.routers import projects, tasks

app = FastAPI(title="OpenDove", version="0.1.0")
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
