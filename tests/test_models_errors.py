"""Model and error-contract regression tests.

Covers behavior not addressed by the engine model suite:

  - Error classes importable from ``owlbear_kanban.errors`` module.
  - KANBAN_ERROR_CODES accessible from ``owlbear_kanban.errors``.
  - Error classes from ``owlbear_kanban.errors`` are the *same objects* as
    those re-exported from ``owlbear_kanban.models`` (backward-compat contract).
  - ``dep_status`` is absent from the Task *storage* model (D38: pure function,
    not stored — projection-only field on TaskSummary).
  - ``archival_reason`` is ``str | None`` at the model level with no enum
    restriction; enum validation belongs at write sites, not the model (§3.1).
  - ``archival_refs`` on TaskSummary is ``list[int]`` (not ``list[str]``),
    defaulting to the empty list.
"""

from __future__ import annotations

import pytest

from owlbear_kanban.errors import (
    KANBAN_ERROR_CODES,
    ConcurrencyError,
    ConfigError,
    KanbanError,
    MigrationRequiredError,
    NotFoundError,
    ValidationError,
)
from owlbear_kanban.models import Task, TaskFull, TaskSummary

# Promoted from archived task #1066.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SUMMARY_REQUIRED = {
    "id": 1,
    "title": "A task",
    "status": "todo",
    "priority": "needed",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
}

_TASK_REQUIRED = {
    "id": 1,
    "title": "A task",
    "status": "todo",
    "priority": "needed",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
}


def _make_summary(**kwargs: object) -> TaskSummary:
    return TaskSummary(**{**_SUMMARY_REQUIRED, **kwargs})


def _make_full(**kwargs: object) -> TaskFull:
    return TaskFull(**{**_SUMMARY_REQUIRED, **kwargs})


def _make_task(**kwargs: object) -> Task:
    return Task(**{**_TASK_REQUIRED, **kwargs})


# ---------------------------------------------------------------------------
# AC6 — Error classes importable from owlbear_kanban.errors
# ---------------------------------------------------------------------------


class TestFromAC_ErrorsModuleAccess:
    """Error classes and KANBAN_ERROR_CODES are accessible from owlbear_kanban.errors."""

    def test_kanban_error_importable_from_errors(self) -> None:
        """KanbanError is the base class, exported from errors module."""
        assert KanbanError is not None

    def test_validation_error_importable_from_errors(self) -> None:
        assert ValidationError is not None

    def test_not_found_error_importable_from_errors(self) -> None:
        assert NotFoundError is not None

    def test_concurrency_error_importable_from_errors(self) -> None:
        assert ConcurrencyError is not None

    def test_config_error_importable_from_errors(self) -> None:
        assert ConfigError is not None

    def test_migration_required_error_importable_from_errors(self) -> None:
        assert MigrationRequiredError is not None

    def test_kanban_error_codes_importable_from_errors(self) -> None:
        assert KANBAN_ERROR_CODES is not None

    def test_kanban_error_codes_is_frozenset(self) -> None:
        """KANBAN_ERROR_CODES must be immutable — frozenset per D57."""
        assert isinstance(KANBAN_ERROR_CODES, frozenset)

    def test_errors_module_classes_usable(self) -> None:
        """Error classes imported from errors module must be instantiable."""
        error = ValidationError(code="ERR_NO_OP", user_message="no-op")
        assert error.code == "ERR_NO_OP"
        assert error.user_message == "no-op"

    def test_errors_module_not_found_error_raiseable(self) -> None:
        with pytest.raises(NotFoundError):
            raise NotFoundError(code="ERR_NOT_FOUND", user_message="not found")

    def test_errors_module_kanban_error_codes_non_empty(self) -> None:
        """Catalogue must contain all 37 ERR_* codes from §4/D57."""
        assert len(KANBAN_ERROR_CODES) >= 37


# ---------------------------------------------------------------------------
# AC6 — errors module classes are the same objects as models re-exports
# ---------------------------------------------------------------------------


class TestFromAC_ErrorsBackwardCompat:
    """owlbear_kanban.errors classes are the same objects re-exported from models.

    models.py must import from errors.py (or vice versa) so that existing
    consumers importing from owlbear_kanban.models continue to work without
    change.
    """

    def test_kanban_error_is_same_class_as_from_models(self) -> None:
        from owlbear_kanban.models import KanbanError as KanbanErrorFromModels

        assert KanbanError is KanbanErrorFromModels

    def test_validation_error_is_same_class_as_from_models(self) -> None:
        from owlbear_kanban.models import ValidationError as VEFromModels

        assert ValidationError is VEFromModels

    def test_not_found_error_is_same_class_as_from_models(self) -> None:
        from owlbear_kanban.models import NotFoundError as NFEFromModels

        assert NotFoundError is NFEFromModels

    def test_concurrency_error_is_same_class_as_from_models(self) -> None:
        from owlbear_kanban.models import ConcurrencyError as CEFromModels

        assert ConcurrencyError is CEFromModels

    def test_config_error_is_same_class_as_from_models(self) -> None:
        from owlbear_kanban.models import ConfigError as ConfigEFromModels

        assert ConfigError is ConfigEFromModels

    def test_migration_required_error_is_same_class_as_from_models(self) -> None:
        from owlbear_kanban.models import MigrationRequiredError as MREFromModels

        assert MigrationRequiredError is MREFromModels

    def test_kanban_error_codes_is_same_object_as_from_models(self) -> None:
        from owlbear_kanban.models import (
            KANBAN_ERROR_CODES as KANBAN_ERROR_CODES_FROM_MODELS,
        )

        assert KANBAN_ERROR_CODES is KANBAN_ERROR_CODES_FROM_MODELS


# ---------------------------------------------------------------------------
# AC2 — dep_status NOT in Task storage model (D38: not stored)
# ---------------------------------------------------------------------------


class TestFromAC_DepStatusNotStored:
    """D38: dep_status is a pure-function projection — not a field on Task storage model.

    The Task model represents what is persisted to disk. dep_status must never
    appear in Task.model_fields; it is computed at projection time and lives
    only on TaskSummary (and its subclasses).
    """

    def test_dep_status_absent_from_task_model_fields(self) -> None:
        """dep_status must not appear in Task.model_fields (D38: not stored)."""
        assert "dep_status" not in Task.model_fields

    def test_task_model_excludes_dep_status_in_serialization(self) -> None:
        """Serialized Task dict must not include dep_status key."""
        task = _make_task()
        dumped = task.model_dump()
        assert "dep_status" not in dumped

    def test_dep_status_present_on_task_summary(self) -> None:
        """dep_status is on the projection model (TaskSummary), not the storage model."""
        assert "dep_status" in TaskSummary.model_fields

    def test_dep_status_present_on_task_full(self) -> None:
        """TaskFull inherits dep_status from TaskSummary."""
        assert "dep_status" in TaskFull.model_fields


# ---------------------------------------------------------------------------
# AC7 — archival_reason is str | None at model level; enum at write sites only
# ---------------------------------------------------------------------------


class TestFromAC_ArchivalReasonModelLevel:
    """archival_reason is typed str | None on projection models — no enum enforcement.

    §3.1: enum validation belongs at engine write sites (move_task, edit_task,
    end_work), not in the Pydantic model. This allows the model to round-trip
    arbitrary archival_reason values without rejecting them.
    """

    def test_task_summary_accepts_arbitrary_archival_reason(self) -> None:
        """Model must not restrict archival_reason to the enum set (§3.1)."""
        summary = _make_summary(archival_reason="custom_non_enum_reason")
        assert summary.archival_reason == "custom_non_enum_reason"

    def test_task_full_accepts_arbitrary_archival_reason(self) -> None:
        full = _make_full(archival_reason="completely_arbitrary_string")
        assert full.archival_reason == "completely_arbitrary_string"

    def test_task_summary_archival_reason_accepts_none(self) -> None:
        summary = _make_summary(archival_reason=None)
        assert summary.archival_reason is None

    def test_task_full_archival_reason_accepts_none(self) -> None:
        full = _make_full(archival_reason=None)
        assert full.archival_reason is None

    def test_task_summary_archival_reason_accepts_all_enum_values(self) -> None:
        """Enum values are a subset of accepted strings — all five must round-trip."""
        for reason in ("completed", "deprecated", "dropped", "duplicate", "wontfix"):
            summary = _make_summary(archival_reason=reason)
            assert summary.archival_reason == reason


# ---------------------------------------------------------------------------
# AC8 — archival_refs is list[int] with default empty list on projections
# ---------------------------------------------------------------------------


class TestFromAC_ArchivalRefsTyping:
    """archival_refs is list[int] with default [] on TaskSummary and TaskFull."""

    def test_task_summary_archival_refs_default_is_empty_list(self) -> None:
        summary = _make_summary()
        assert summary.archival_refs == []

    def test_task_full_archival_refs_default_is_empty_list(self) -> None:
        full = _make_full()
        assert full.archival_refs == []

    def test_task_summary_archival_refs_elements_are_int(self) -> None:
        summary = _make_summary(archival_refs=[10, 20, 30])
        assert all(isinstance(ref, int) for ref in summary.archival_refs)

    def test_task_full_archival_refs_elements_are_int(self) -> None:
        full = _make_full(archival_refs=[42])
        assert all(isinstance(ref, int) for ref in full.archival_refs)

    def test_task_summary_archival_refs_annotation_is_list_of_int(self) -> None:
        """Field annotation must reflect list[int], not list[str] (§2.1)."""
        from typing import get_args, get_origin

        field = TaskSummary.model_fields["archival_refs"]
        annotation = field.annotation
        assert get_origin(annotation) is list
        (inner,) = get_args(annotation)
        assert inner is int
