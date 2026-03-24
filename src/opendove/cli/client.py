import os

import httpx

BASE_URL = os.getenv("OPENDOVE_API_URL", "http://localhost:8000")


class APIClient:
    def __init__(self, base_url: str = BASE_URL):
        self._base = base_url.rstrip("/")

    def _get(self, path: str) -> httpx.Response:
        url = f"{self._base}{path}"
        try:
            response = httpx.get(url)
        except httpx.ConnectError:
            raise RuntimeError(f"Cannot connect to OpenDove server at {self._base}. Is it running?")
        if response.status_code >= 400:
            raise RuntimeError(response.json().get("detail", "Unknown error"))
        return response

    def _post(self, path: str, json: dict) -> httpx.Response:
        url = f"{self._base}{path}"
        try:
            response = httpx.post(url, json=json)
        except httpx.ConnectError:
            raise RuntimeError(f"Cannot connect to OpenDove server at {self._base}. Is it running?")
        if response.status_code >= 400:
            raise RuntimeError(response.json().get("detail", "Unknown error"))
        return response

    def register_project(self, name: str, repo_url: str, default_branch: str = "main") -> dict:
        response = self._post(
            "/projects",
            {"name": name, "repo_url": repo_url, "default_branch": default_branch},
        )
        return response.json()

    def list_projects(self) -> list[dict]:
        response = self._get("/projects")
        return response.json()

    def get_project(self, project_id: str) -> dict:
        response = self._get(f"/projects/{project_id}")
        return response.json()

    def submit_task(
        self,
        project_id: str,
        title: str,
        intent: str,
        success_criteria: list[str],
        risk_level: str = "low",
        max_retries: int = 3,
    ) -> dict:
        response = self._post(
            f"/projects/{project_id}/tasks",
            {
                "title": title,
                "intent": intent,
                "success_criteria": success_criteria,
                "risk_level": risk_level,
                "max_retries": max_retries,
            },
        )
        return response.json()

    def get_task(self, task_id: str) -> dict:
        response = self._get(f"/tasks/{task_id}")
        return response.json()

    def list_tasks(self, project_id: str) -> list[dict]:
        response = self._get(f"/projects/{project_id}/tasks")
        return response.json()
