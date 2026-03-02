"""Tests for Project Pydantic model — slug generation, defaults, JSON round-trip.

TDD red-phase: these tests define the expected behavior of the Project model.
The model does not exist yet — all tests should fail on import.

See docs/multi-project-session-research.md §3.2 for field spec.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from owlbear.projects.models import Project

# ---------------------------------------------------------------------------
# Fields
# ---------------------------------------------------------------------------


class TestProjectFields:
    """Project model has the expected fields with correct types."""

    def test_has_required_fields(self, tmp_path: Path) -> None:
        """Project has: id, name, workspace_path, created_at, last_active, status."""
        p = Project(name="Test Project", workspace_path=tmp_path)
        assert hasattr(p, "id")
        assert hasattr(p, "name")
        assert hasattr(p, "workspace_path")
        assert hasattr(p, "created_at")
        assert hasattr(p, "last_active")
        assert hasattr(p, "status")

    def test_name_stored(self, tmp_path: Path) -> None:
        p = Project(name="My Project", workspace_path=tmp_path)
        assert p.name == "My Project"

    def test_workspace_path_is_absolute_path(self, tmp_path: Path) -> None:
        """workspace_path is stored as an absolute Path."""
        p = Project(name="Abs", workspace_path=tmp_path)
        assert isinstance(p.workspace_path, Path)
        assert p.workspace_path.is_absolute()


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------


class TestProjectSlugGeneration:
    """id is auto-derived from name via slugify."""

    def test_slug_from_name(self, tmp_path: Path) -> None:
        """'My Project' -> 'my-project'."""
        p = Project(name="My Project", workspace_path=tmp_path)
        assert p.id == "my-project"

    def test_slug_lowercase(self, tmp_path: Path) -> None:
        """Name is lowercased in slug."""
        p = Project(name="LOUD PROJECT", workspace_path=tmp_path)
        assert p.id == "loud-project"

    def test_duplicate_slug_from_different_cases(self, tmp_path: Path) -> None:
        """'My Project' and 'my project' produce the same slug."""
        p1 = Project(name="My Project", workspace_path=tmp_path)
        p2 = Project(name="my project", workspace_path=tmp_path)
        assert p1.id == p2.id

    def test_slug_strips_extra_whitespace(self, tmp_path: Path) -> None:
        """Multiple spaces collapse to single hyphen."""
        p = Project(name="My   Project", workspace_path=tmp_path)
        assert p.id == "my-project"


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestProjectDefaults:
    """Default values for status, created_at, and last_active."""

    def test_status_defaults_to_active(self, tmp_path: Path) -> None:
        p = Project(name="Def", workspace_path=tmp_path)
        assert p.status == "active"

    def test_created_at_defaults_to_now(self, tmp_path: Path) -> None:
        before = datetime.now(tz=UTC)
        p = Project(name="Time", workspace_path=tmp_path)
        after = datetime.now(tz=UTC)
        assert before <= p.created_at <= after

    def test_last_active_defaults_to_now(self, tmp_path: Path) -> None:
        before = datetime.now(tz=UTC)
        p = Project(name="Active", workspace_path=tmp_path)
        after = datetime.now(tz=UTC)
        assert before <= p.last_active <= after


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestProjectValidation:
    """Validation rules for the Project model."""

    def test_invalid_status_raises_validation_error(self, tmp_path: Path) -> None:
        """Only 'active' and 'archived' are valid status values."""
        with pytest.raises(ValidationError):
            Project(
                name="Bad",
                workspace_path=tmp_path,
                status="deleted",  # type: ignore[arg-type]
            )

    def test_valid_status_active(self, tmp_path: Path) -> None:
        p = Project(name="A", workspace_path=tmp_path, status="active")
        assert p.status == "active"

    def test_valid_status_archived(self, tmp_path: Path) -> None:
        p = Project(name="A", workspace_path=tmp_path, status="archived")
        assert p.status == "archived"


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------


class TestProjectJsonRoundTrip:
    """model_dump_json() -> model_validate_json() preserves all fields."""

    def test_round_trip_preserves_all_fields(self, tmp_path: Path) -> None:
        original = Project(name="Round Trip", workspace_path=tmp_path)
        json_str = original.model_dump_json()
        restored = Project.model_validate_json(json_str)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.workspace_path == original.workspace_path
        assert restored.created_at == original.created_at
        assert restored.last_active == original.last_active
        assert restored.status == original.status

    def test_round_trip_with_explicit_status(self, tmp_path: Path) -> None:
        original = Project(
            name="Archived",
            workspace_path=tmp_path,
            status="archived",
        )
        json_str = original.model_dump_json()
        restored = Project.model_validate_json(json_str)
        assert restored.status == "archived"
