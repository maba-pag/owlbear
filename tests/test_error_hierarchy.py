"""Error hierarchy regression tests.

Promoted from the task-scoped suite for task #1201.

AC coverage:
- AC1: CorruptionError inherits from KanbanError (td:2)
- AC2: CorruptionError.__init__ calls KanbanError.__init__(code, user_message) (td:2)
- AC3: KANBAN_ERROR_CODES contains all 9 ERR_CORRUPT_* string codes (td:1)
- AC4: errors.py re-exports CorruptionError (td:1)
- AC5: isinstance(CorruptionError(...), KanbanError) is True (td:1)
- AC6: All 9 ERR_CORRUPT_* dynamic subclasses remain CorruptionError subclasses (td:1)
- AC7: Existing consumers importing from corruption.py or errors.py still work (td:1)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban.errors import KANBAN_ERROR_CODES, KanbanError
from owlbear_kanban.corruption import (
    CorruptionError,
    ERR_CORRUPT_DELIMITERS,
    ERR_CORRUPT_DUPLICATE_ID,
    ERR_CORRUPT_DUPLICATE_LOCATION,
    ERR_CORRUPT_ID_FILENAME_MISMATCH,
    ERR_CORRUPT_INVALID_PRIORITY,
    ERR_CORRUPT_INVALID_STATUS,
    ERR_CORRUPT_MISSING_FIELD,
    ERR_CORRUPT_TYPE_MISMATCH,
    ERR_CORRUPT_YAML_PARSE,
)

# Provenance: promoted from task-scoped suite for task #1201.

_ALL_NINE_CODES = [
    "ERR_CORRUPT_DELIMITERS",
    "ERR_CORRUPT_DUPLICATE_ID",
    "ERR_CORRUPT_MISSING_FIELD",
    "ERR_CORRUPT_TYPE_MISMATCH",
    "ERR_CORRUPT_YAML_PARSE",
    "ERR_CORRUPT_ID_FILENAME_MISMATCH",
    "ERR_CORRUPT_DUPLICATE_LOCATION",
    "ERR_CORRUPT_INVALID_STATUS",
    "ERR_CORRUPT_INVALID_PRIORITY",
]

_ALL_NINE_TYPES = [
    ERR_CORRUPT_DELIMITERS,
    ERR_CORRUPT_DUPLICATE_ID,
    ERR_CORRUPT_MISSING_FIELD,
    ERR_CORRUPT_TYPE_MISMATCH,
    ERR_CORRUPT_YAML_PARSE,
    ERR_CORRUPT_ID_FILENAME_MISMATCH,
    ERR_CORRUPT_DUPLICATE_LOCATION,
    ERR_CORRUPT_INVALID_STATUS,
    ERR_CORRUPT_INVALID_PRIORITY,
]


# ---------------------------------------------------------------------------
# AC1: CorruptionError inherits from KanbanError
# ---------------------------------------------------------------------------


class TestFromAC_ErrorHierarchy:
    """AC1: CorruptionError inherits from KanbanError (td:2)."""

    def test_corruption_error_is_subclass_of_kanban_error(self) -> None:
        """Happy: issubclass(CorruptionError, KanbanError) is True."""
        assert issubclass(CorruptionError, KanbanError)

    def test_kanban_error_in_mro(self) -> None:
        """Edge: KanbanError appears in CorruptionError.__mro__."""
        assert KanbanError in CorruptionError.__mro__

    def test_corruption_error_caught_by_kanban_error_handler(self) -> None:
        """Error: CorruptionError raised inside a function is caught by except KanbanError."""
        with pytest.raises(KanbanError):
            raise CorruptionError(
                code="ERR_CORRUPT_DELIMITERS",
                detail="delimiter missing",
            )


# ---------------------------------------------------------------------------
# AC2: CorruptionError.__init__ calls KanbanError.__init__(code, user_message)
# ---------------------------------------------------------------------------


class TestFromAC_ConstructorCallsSuper:
    """AC2: __init__ calls KanbanError.__init__ before setting extra attrs (td:2)."""

    def test_instance_is_kanban_error_and_code_attr_set(self) -> None:
        """Happy: constructed instance is KanbanError; .code == string code name."""
        err = CorruptionError(
            code="ERR_CORRUPT_DELIMITERS",
            detail="no closing delimiter",
        )
        assert isinstance(err, KanbanError)
        assert err.code == "ERR_CORRUPT_DELIMITERS"

    def test_user_message_kwarg_propagated_via_super(self) -> None:
        """Happy: user_message kwarg is set on the instance via KanbanError contract."""
        err = CorruptionError(
            code="ERR_CORRUPT_MISSING_FIELD",
            detail="field absent",
            user_message="required field 'title' is missing",
        )
        assert isinstance(err, KanbanError)
        assert err.user_message == "required field 'title' is missing"

    def test_invalid_code_raises_value_error_via_kanban_validation(self) -> None:
        """Error: code not in KANBAN_ERROR_CODES triggers KanbanError code validation."""
        with pytest.raises(ValueError, match="Unknown error code"):
            CorruptionError(code="NOT_A_RECOGNIZED_CODE", detail="some detail")

    def test_extra_attrs_preserved_alongside_kanban_error_attrs(self) -> None:
        """Edge: detail, path, file_path survive after super().__init__ call."""
        task_path = Path("/kanban/tasks/42-some-task.md")
        err = CorruptionError(
            code="ERR_CORRUPT_YAML_PARSE",
            detail="yaml broken",
            path=task_path,
            user_message="YAML parse failure",
            file_path="/kanban/tasks/42-some-task.md",
        )
        assert isinstance(err, KanbanError)
        assert err.detail == "yaml broken"
        assert err.path == task_path
        assert err.file_path == "/kanban/tasks/42-some-task.md"

    def test_detail_fallback_when_no_user_message(self) -> None:
        """Boundary: when user_message is absent, detail becomes the effective message."""
        err = CorruptionError(
            code="ERR_CORRUPT_DELIMITERS",
            detail="no closing ---",
        )
        assert isinstance(err, KanbanError)
        assert err.user_message == "no closing ---"


# ---------------------------------------------------------------------------
# AC3: KANBAN_ERROR_CODES contains all 9 ERR_CORRUPT_* string codes
# ---------------------------------------------------------------------------


class TestFromAC_KanbanErrorCodes:
    """AC3: KANBAN_ERROR_CODES contains all 9 ERR_CORRUPT_* codes (td:1)."""

    @pytest.mark.parametrize("code", _ALL_NINE_CODES)
    def test_err_corrupt_code_in_kanban_error_codes(self, code: str) -> None:
        """Smoke: each ERR_CORRUPT_* code string is present in KANBAN_ERROR_CODES."""
        assert code in KANBAN_ERROR_CODES

    def test_all_nine_corrupt_codes_present(self) -> None:
        """Boundary: all 9 codes are present — no partial addition."""
        missing = [c for c in _ALL_NINE_CODES if c not in KANBAN_ERROR_CODES]
        assert missing == [], f"Missing codes: {missing}"


# ---------------------------------------------------------------------------
# AC4: errors.py re-exports CorruptionError
# ---------------------------------------------------------------------------


class TestFromAC_ReExport:
    """AC4: errors.py re-exports CorruptionError (td:1)."""

    def test_corruption_error_importable_from_errors_module(self) -> None:
        """Smoke: from owlbear_kanban.errors import CorruptionError succeeds."""
        from owlbear_kanban.errors import CorruptionError as CE  # noqa: N817

        assert CE is CorruptionError


# ---------------------------------------------------------------------------
# AC5: isinstance(CorruptionError(...), KanbanError) is True
# ---------------------------------------------------------------------------


class TestFromAC_InstanceCheck:
    """AC5: isinstance check returns True (td:1)."""

    def test_isinstance_of_kanban_error(self) -> None:
        """Smoke: a constructed CorruptionError is a KanbanError instance."""
        err = CorruptionError(
            code="ERR_CORRUPT_DUPLICATE_ID",
            detail="duplicate id 42",
        )
        assert isinstance(err, KanbanError) is True


# ---------------------------------------------------------------------------
# AC6: All 9 ERR_CORRUPT_* dynamic subclasses remain CorruptionError subclasses
# ---------------------------------------------------------------------------


class TestFromAC_DynamicSubclasses:
    """AC6: 9 dynamic subclasses remain CorruptionError subclasses (td:1)."""

    @pytest.mark.parametrize("cls", _ALL_NINE_TYPES)
    def test_dynamic_subclass_remains_corruption_error_and_is_kanban_error(self, cls: type) -> None:
        """Smoke+regression: subclass is still CorruptionError and also KanbanError."""
        assert issubclass(cls, CorruptionError), f"{cls.__name__} lost CorruptionError base"
        assert issubclass(cls, KanbanError), f"{cls.__name__} is not a KanbanError subclass"


# ---------------------------------------------------------------------------
# AC7: Existing consumers importing from corruption.py or errors.py still work
# ---------------------------------------------------------------------------


class TestFromAC_ConsumerImports:
    """AC7: existing import paths continue to resolve correctly (td:1)."""

    def test_corruption_py_import_still_works(self) -> None:
        """Regression: from owlbear_kanban.corruption import CorruptionError; instance is KanbanError."""
        from owlbear_kanban.corruption import CorruptionError as CE  # noqa: N817

        assert CE is CorruptionError
        err = CE(code="ERR_CORRUPT_DELIMITERS", detail="test regression")
        assert isinstance(err, KanbanError)

    def test_errors_py_import_still_works(self) -> None:
        """Regression: from owlbear_kanban.errors import CorruptionError; same class."""
        from owlbear_kanban.errors import CorruptionError as CE  # noqa: N817

        assert CE is CorruptionError
        err = CE(code="ERR_CORRUPT_DELIMITERS", detail="test regression via errors")
        assert isinstance(err, KanbanError)
