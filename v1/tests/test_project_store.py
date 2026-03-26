"""Tests for ProjectStore — CRUD for project persistence as JSON files.

TDD red-phase: these tests define the expected behavior of ProjectStore.
The module does not exist yet — all tests should fail on import.

See docs/multi-project-session-research.md §3.3 for design rationale.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear.projects.models import Project
from owlbear.projects.store import ProjectStore


@pytest.fixture
def store(tmp_path: Path) -> ProjectStore:
    """Return a ProjectStore backed by a temp directory."""
    return ProjectStore(tmp_path / "projects")


@pytest.fixture
def sample_project(tmp_path: Path) -> Project:
    """Return a sample Project for testing."""
    return Project(name="My Project", workspace_path=tmp_path / "workspace")


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------


class TestCreate:
    """ProjectStore.create() persists a Project as {id}.json."""

    def test_create_writes_json_file(
        self, store: ProjectStore, sample_project: Project
    ) -> None:
        """create() writes {id}.json to the projects directory."""
        created = store.create(sample_project.name, sample_project.workspace_path)

        json_path = store.projects_dir / f"{created.id}.json"
        assert json_path.exists()

    def test_create_json_contains_all_fields(
        self, store: ProjectStore, sample_project: Project
    ) -> None:
        """The written JSON contains all Project fields."""
        created = store.create(sample_project.name, sample_project.workspace_path)

        json_path = store.projects_dir / f"{created.id}.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))

        assert data["id"] == created.id
        assert data["name"] == created.name
        assert data["status"] == "active"

    def test_create_duplicate_name_raises(
        self, store: ProjectStore, sample_project: Project
    ) -> None:
        """create() with a duplicate name raises ValueError."""
        store.create(sample_project.name, sample_project.workspace_path)

        with pytest.raises(ValueError, match="already exists"):
            store.create(sample_project.name, sample_project.workspace_path)

    def test_create_creates_projects_dir_if_missing(
        self, tmp_path: Path, sample_project: Project
    ) -> None:
        """ProjectStore auto-creates the projects directory on first create()."""
        projects_dir = tmp_path / "nonexistent" / "projects"
        new_store = ProjectStore(projects_dir)
        created = new_store.create(sample_project.name, sample_project.workspace_path)

        assert projects_dir.exists()
        assert (projects_dir / f"{created.id}.json").exists()


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


class TestGet:
    """ProjectStore.get() reads and validates a Project from JSON."""

    def test_get_returns_project(
        self, store: ProjectStore, sample_project: Project
    ) -> None:
        """get(id) returns a valid Project matching the original."""
        created = store.create(sample_project.name, sample_project.workspace_path)
        retrieved = store.get(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.workspace_path == created.workspace_path
        assert retrieved.status == "active"

    def test_get_nonexistent_raises(self, store: ProjectStore) -> None:
        """get() with a nonexistent id raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            store.get("nonexistent-id")


# ---------------------------------------------------------------------------
# get_by_name()
# ---------------------------------------------------------------------------


class TestGetByName:
    """ProjectStore.get_by_name() finds a project by display name."""

    def test_get_by_name_returns_matching_project(
        self, store: ProjectStore, sample_project: Project
    ) -> None:
        """get_by_name() returns the project with the given display name."""
        created = store.create(sample_project.name, sample_project.workspace_path)
        retrieved = store.get_by_name("My Project")

        assert retrieved.id == created.id
        assert retrieved.name == "My Project"

    def test_get_by_name_not_found_raises(self, store: ProjectStore) -> None:
        """get_by_name() raises KeyError when no project matches."""
        with pytest.raises(KeyError, match="No project"):
            store.get_by_name("Nonexistent")


# ---------------------------------------------------------------------------
# list_active()
# ---------------------------------------------------------------------------


class TestListActive:
    """ProjectStore.list_active() returns only active projects."""

    def test_list_active_returns_active_only(
        self, store: ProjectStore, tmp_path: Path
    ) -> None:
        """list_active() includes active projects, excludes archived."""
        store.create("Active One", tmp_path / "a")
        archived = store.create("Old One", tmp_path / "b")
        store.archive(archived.id)

        result = store.list_active()
        names = [p.name for p in result]

        assert "Active One" in names
        assert "Old One" not in names

    def test_list_active_empty_dir_returns_empty(
        self, store: ProjectStore
    ) -> None:
        """list_active() on an empty directory returns an empty list."""
        result = store.list_active()
        assert result == []


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------


class TestUpdate:
    """ProjectStore.update() rewrites the project JSON."""

    def test_update_rewrites_fields(
        self, store: ProjectStore, sample_project: Project
    ) -> None:
        """update() persists changed fields (e.g. last_active)."""
        created = store.create(sample_project.name, sample_project.workspace_path)

        new_time = datetime(2030, 6, 15, tzinfo=UTC)
        updated = created.model_copy(update={"last_active": new_time})
        store.update(updated)

        retrieved = store.get(created.id)
        assert retrieved.last_active == new_time

    def test_update_nonexistent_raises(
        self, store: ProjectStore, sample_project: Project
    ) -> None:
        """update() raises FileNotFoundError if project doesn't exist."""
        with pytest.raises(FileNotFoundError):
            store.update(sample_project)


# ---------------------------------------------------------------------------
# archive()
# ---------------------------------------------------------------------------


class TestArchive:
    """ProjectStore.archive() sets status='archived' without deleting."""

    def test_archive_sets_status(
        self, store: ProjectStore, sample_project: Project
    ) -> None:
        """archive() sets status to 'archived'."""
        created = store.create(sample_project.name, sample_project.workspace_path)
        store.archive(created.id)

        retrieved = store.get(created.id)
        assert retrieved.status == "archived"

    def test_archive_preserves_file(
        self, store: ProjectStore, sample_project: Project
    ) -> None:
        """archive() does not delete the JSON file."""
        created = store.create(sample_project.name, sample_project.workspace_path)
        store.archive(created.id)

        json_path = store.projects_dir / f"{created.id}.json"
        assert json_path.exists()

    def test_archive_nonexistent_raises(self, store: ProjectStore) -> None:
        """archive() raises FileNotFoundError for unknown id."""
        with pytest.raises(FileNotFoundError):
            store.archive("ghost-project")
