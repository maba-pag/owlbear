"""CRUD store for persisting Project models as JSON files.

Each :class:`~owlbear.projects.models.Project` is stored as
``{projects_dir}/{id}.json``.  The store handles creation, retrieval,
listing, update, and archival.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — needed at runtime

from owlbear.projects.models import Project


class ProjectStore:
    """File-backed CRUD store for :class:`Project` instances.

    Args:
        projects_dir (Path): Directory where ``{id}.json`` files are stored.
            Created on first write if it does not exist.
    """

    def __init__(self, projects_dir: Path) -> None:
        self.projects_dir = projects_dir

    # -- helpers -------------------------------------------------------------

    def _path_for(self, project_id: str) -> Path:
        return self.projects_dir / f"{project_id}.json"

    def _read(self, project_id: str) -> Project:
        """Read and validate a project from disk, raising on missing."""
        path = self._path_for(project_id)
        if not path.exists():
            msg = f"No project file for id '{project_id}'"
            raise FileNotFoundError(msg)
        return Project.model_validate_json(path.read_text(encoding="utf-8"))

    def _write(self, project: Project) -> None:
        """Write a project to disk, creating the directory if needed."""
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self._path_for(project.id).write_text(
            project.model_dump_json(indent=2), encoding="utf-8"
        )

    # -- public API ----------------------------------------------------------

    def create(self, name: str, workspace_path: Path) -> Project:
        """Create and persist a new project.

        Raises ``ValueError`` on duplicate name.
        """
        for existing in self._iter_all():
            if existing.name == name:
                msg = f"Project '{name}' already exists"
                raise ValueError(msg)
        project = Project(name=name, workspace_path=workspace_path)
        self._write(project)
        return project

    def get(self, project_id: str) -> Project:
        """Return a project by *id*, or raise ``FileNotFoundError``."""
        return self._read(project_id)

    def get_by_name(self, name: str) -> Project:
        """Return the project matching *name*, or raise ``KeyError``."""
        for project in self._iter_all():
            if project.name == name:
                return project
        msg = f"No project named '{name}'"
        raise KeyError(msg)

    def list_active(self) -> list[Project]:
        """Return all active projects sorted by ``last_active`` descending."""
        return sorted(
            (p for p in self._iter_all() if p.status == "active"),
            key=lambda p: p.last_active,
            reverse=True,
        )

    def list_all(self) -> list[Project]:
        """Return all projects (active + archived) sorted by ``last_active`` descending."""
        return sorted(
            self._iter_all(),
            key=lambda p: p.last_active,
            reverse=True,
        )

    def update(self, project: Project) -> None:
        """Overwrite an existing project.  Raises if not found."""
        if not self._path_for(project.id).exists():
            msg = f"No project file for id '{project.id}'"
            raise FileNotFoundError(msg)
        self._write(project)

    def archive(self, project_id: str) -> None:
        """Set a project's status to ``'archived'``."""
        project = self._read(project_id)
        archived = project.model_copy(update={"status": "archived"})
        self._write(archived)

    # -- iteration -----------------------------------------------------------

    def _iter_all(self) -> list[Project]:
        """Load every ``*.json`` file in the projects directory."""
        if not self.projects_dir.exists():
            return []
        return [
            Project.model_validate_json(p.read_text(encoding="utf-8"))
            for p in self.projects_dir.glob("*.json")
        ]
