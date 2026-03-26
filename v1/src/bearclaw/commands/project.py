"""Project subcommands — manage OwlBear projects."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from bearclaw.commands import _cli_error
from owlbear.config import get_settings

if TYPE_CHECKING:
    from owlbear.projects.store import ProjectStore

app = typer.Typer(
    name="project",
    help="Manage OwlBear projects.",
    no_args_is_help=True,
)


def _get_project_store() -> ProjectStore:
    """Return a ProjectStore rooted at ``config_dir/projects``."""
    from owlbear.projects.store import ProjectStore  # noqa: PLC0415

    settings = get_settings()
    return ProjectStore(Path(str(settings.config_dir)) / "projects")


@app.command("create")
def project_create(
    name: Annotated[str, typer.Option("--name", "-n", help="Project name.")],
    workspace: Annotated[
        str,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace directory path (default: current directory).",
        ),
    ] = "",
) -> None:
    """Create a new project."""
    ws = Path(workspace) if workspace else Path.cwd()
    store = _get_project_store()
    try:
        project = store.create(name, ws)
    except ValueError as exc:
        _cli_error(str(exc))
    typer.echo(f"Created project '{project.name}' (id: {project.id})")


@app.command("list")
def project_list(
    show_all: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--all", "-a", help="Include archived projects."),
    ] = False,
) -> None:
    """List projects in a table."""
    store = _get_project_store()
    projects = store.list_all() if show_all else store.list_active()
    if not projects:
        typer.echo("No projects found.")
        return

    from rich.console import Console  # noqa: PLC0415
    from rich.table import Table  # noqa: PLC0415

    table = Table("Name", "Workspace", "Last Active", "Status")
    for p in projects:
        table.add_row(
            p.name,
            str(p.workspace_path),
            p.last_active.strftime("%Y-%m-%d %H:%M"),
            p.status,
        )
    Console().print(table)


@app.command("switch")
def project_switch(
    name: Annotated[str, typer.Argument(help="Name of the project to switch to.")],
) -> None:
    """Switch the active project."""
    store = _get_project_store()
    try:
        project = store.get_by_name(name)
    except KeyError:
        _cli_error(f"No project named '{name}'")

    settings = get_settings()
    active_path = Path(str(settings.config_dir)) / "active_project"
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(project.id, encoding="utf-8")
    typer.echo(f"Switched to project '{project.name}'")


@app.command("archive")
def project_archive(
    name: Annotated[str, typer.Argument(help="Name of the project to archive.")],
) -> None:
    """Archive a project (set status to archived)."""
    store = _get_project_store()
    try:
        project = store.get_by_name(name)
    except KeyError:
        _cli_error(f"No project named '{name}'")

    store.archive(project.id)
    typer.echo(f"Archived project '{project.name}'")


@app.command("new")
def project_new(
    name: Annotated[str, typer.Argument(help="Name of the new project.")],
    template: Annotated[
        str,
        typer.Option(
            "--template",
            "-t",
            help="Project template: bare, python-uv, python-pip, node.",
        ),
    ] = "bare",
) -> None:
    """Scaffold a new project under project_root with a template."""
    from owlbear.projects.workspace import ProjectWorkspace  # noqa: PLC0415

    settings = get_settings()
    store = _get_project_store()
    ws = ProjectWorkspace(project_root=settings.project_root, store=store)
    try:
        path = ws.create_project(name, template)
    except (ValueError, FileExistsError) as exc:
        _cli_error(str(exc))
    typer.echo(str(path))
