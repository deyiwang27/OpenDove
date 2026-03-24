from typing import List

import typer
from rich.console import Console
from rich.table import Table

from opendove.cli.client import APIClient

app = typer.Typer(name="opendove", help="OpenDove autonomous development system CLI.")
project_app = typer.Typer(help="Manage projects.")
task_app = typer.Typer(help="Manage tasks.")
app.add_typer(project_app, name="project")
app.add_typer(task_app, name="task")
console = Console()


# ---------------------------------------------------------------------------
# Project commands
# ---------------------------------------------------------------------------


@project_app.command("add")
def project_add(
    name: str = typer.Argument(..., help="Project name."),
    repo_url: str = typer.Argument(..., help="Git repository URL."),
    branch: str = typer.Option("main", "--branch", help="Default branch."),
) -> None:
    """Register a new project."""
    client = APIClient()
    try:
        result = client.register_project(name, repo_url, branch)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    console.print(f"Project registered: {result['id']}")


@project_app.command("list")
def project_list() -> None:
    """List all registered projects."""
    client = APIClient()
    try:
        projects = client.list_projects()
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    if not projects:
        console.print("No projects registered.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Active Task")
    table.add_column("Queued")

    for project in projects:
        table.add_row(
            str(project.get("id", "")),
            str(project.get("name", "")),
            str(project.get("status", "")),
            str(project.get("active_task_id", "") or ""),
            str(project.get("queued_task_count", 0)),
        )

    console.print(table)


@project_app.command("status")
def project_status(project_id: str = typer.Argument(..., help="Project ID.")) -> None:
    """Show status of a project."""
    client = APIClient()
    try:
        project = client.get_project(project_id)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")

    for key, value in project.items():
        table.add_row(str(key), str(value) if value is not None else "")

    console.print(table)


# ---------------------------------------------------------------------------
# Task commands
# ---------------------------------------------------------------------------


@task_app.command("submit")
def task_submit(
    project_id: str = typer.Argument(..., help="Project ID."),
    title: str = typer.Option(..., "--title", help="Task title."),
    intent: str = typer.Option(..., "--intent", help="Task intent."),
    criteria: List[str] = typer.Option(..., "--criteria", help="Success criteria (repeatable)."),
    risk: str = typer.Option("low", "--risk", help="Risk level (low|architectural)."),
    retries: int = typer.Option(3, "--retries", help="Maximum retries."),
) -> None:
    """Submit a new task for a project."""
    client = APIClient()
    try:
        result = client.submit_task(project_id, title, intent, criteria, risk, retries)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    console.print(f"Task submitted: {result['id']}  status: {result.get('status', '')}")


@task_app.command("status")
def task_status(task_id: str = typer.Argument(..., help="Task ID.")) -> None:
    """Show status of a task."""
    client = APIClient()
    try:
        task = client.get_task(task_id)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")

    for key, value in task.items():
        table.add_row(str(key), str(value) if value is not None else "")

    console.print(table)


@task_app.command("list")
def task_list(project_id: str = typer.Argument(..., help="Project ID.")) -> None:
    """List tasks for a project."""
    client = APIClient()
    try:
        tasks = client.list_tasks(project_id)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    if not tasks:
        console.print("No tasks found.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Retries")

    for task in tasks:
        table.add_row(
            str(task.get("id", "")),
            str(task.get("title", "")),
            str(task.get("status", "")),
            str(task.get("retry_count", 0)),
        )

    console.print(table)


if __name__ == "__main__":
    app()
