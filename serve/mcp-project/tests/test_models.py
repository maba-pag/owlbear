"""Failing tests for task #74: OwlbearProjectFile Pydantic model.

TDD RED phase — all tests fail on import because
packages/mcp-project/src/owlbear_mcp_project/models.py does not exist yet.

Related tasks: #68 (builder), #74 (this test task), #41 (scaffold).
Model spec: docs/research/owlbear-project-json-schema.md §3.7
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from owlbear_mcp_project.models import OwlbearProjectFile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_data(**overrides: object) -> dict[str, object]:
    """Return a minimal valid field dict for OwlbearProjectFile."""
    base: dict[str, object] = {
        "schema_version": 1,
        "name": "my-project",
        "type": "python-uv",
        "owlbear_path": "../owlbear",
        "created_at": "2026-03-27T02:30:00Z",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestFromAC_OwlbearProjectFile
# ---------------------------------------------------------------------------


class TestFromAC_OwlbearProjectFile:
    """AC-driven tests for the OwlbearProjectFile Pydantic model.

    Each test group maps to a specific line in the task AC.
    """

    # ------------------------------------------------------------------
    # AC1: Valid model construction with all 5 required fields
    # ------------------------------------------------------------------

    def test_valid_construction_all_fields(self) -> None:
        """Model accepts valid data and exposes all 5 required fields."""
        model = OwlbearProjectFile(**_valid_data())
        assert model.schema_version == 1
        assert model.name == "my-project"
        assert model.type == "python-uv"
        assert model.owlbear_path == "../owlbear"
        assert model.created_at.tzinfo is not None  # timezone-aware

    # ------------------------------------------------------------------
    # AC2: Extra fields preserved (extra='allow' verified via model_extra)
    # ------------------------------------------------------------------

    def test_extra_fields_preserved_in_model_extra(self) -> None:
        """Unknown fields are stored in model_extra (extra='allow')."""
        data = _valid_data(custom_metadata="hello", another_extra=42)
        model = OwlbearProjectFile(**data)
        assert model.model_extra is not None
        assert model.model_extra.get("custom_metadata") == "hello"
        assert model.model_extra.get("another_extra") == 42

    def test_extra_fields_do_not_raise(self) -> None:
        """Construction with unknown fields does not raise ValidationError."""
        data = _valid_data(unknown_field="some_value")
        OwlbearProjectFile(**data)  # must not raise

    # ------------------------------------------------------------------
    # AC3: Invalid schema_version (0, 2, -1) rejected
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("bad_version", [0, -1, 2, 100])
    def test_invalid_schema_version_rejected(self, bad_version: int) -> None:
        """schema_version outside the exclusive range [1, 1] raises ValidationError."""
        with pytest.raises(ValidationError):
            OwlbearProjectFile(**_valid_data(schema_version=bad_version))

    def test_schema_version_one_is_valid(self) -> None:
        """schema_version=1 is the only accepted value."""
        model = OwlbearProjectFile(**_valid_data(schema_version=1))
        assert model.schema_version == 1

    # ------------------------------------------------------------------
    # AC4: Empty name rejected; name >100 chars rejected
    # ------------------------------------------------------------------

    def test_empty_name_rejected(self) -> None:
        """Empty string for name raises ValidationError (min_length=1)."""
        with pytest.raises(ValidationError):
            OwlbearProjectFile(**_valid_data(name=""))

    def test_name_101_chars_rejected(self) -> None:
        """Name of 101 characters raises ValidationError (max_length=100)."""
        with pytest.raises(ValidationError):
            OwlbearProjectFile(**_valid_data(name="a" * 101))

    def test_name_exactly_100_chars_accepted(self) -> None:
        """Name of exactly 100 characters is valid (upper boundary)."""
        model = OwlbearProjectFile(**_valid_data(name="a" * 100))
        assert len(model.name) == 100

    def test_name_single_char_accepted(self) -> None:
        """Name of exactly 1 character is valid (lower boundary)."""
        model = OwlbearProjectFile(**_valid_data(name="x"))
        assert model.name == "x"

    # ------------------------------------------------------------------
    # AC5: Invalid type enum value rejected
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "bad_type",
        ["django", "ruby", "", "PYTHON-UV", "python_uv", "nodejs"],
    )
    def test_invalid_type_rejected(self, bad_type: str) -> None:
        """Non-Literal type values raise ValidationError."""
        with pytest.raises(ValidationError):
            OwlbearProjectFile(**_valid_data(type=bad_type))

    # ------------------------------------------------------------------
    # AC6: Empty owlbear_path rejected
    # ------------------------------------------------------------------

    def test_empty_owlbear_path_rejected(self) -> None:
        """Empty string for owlbear_path raises ValidationError (min_length=1)."""
        with pytest.raises(ValidationError):
            OwlbearProjectFile(**_valid_data(owlbear_path=""))

    def test_nonempty_owlbear_path_accepted(self) -> None:
        """Non-empty owlbear_path string is accepted."""
        model = OwlbearProjectFile(**_valid_data(owlbear_path="../owlbear"))
        assert model.owlbear_path == "../owlbear"

    # ------------------------------------------------------------------
    # AC7: Naive datetime (no timezone) rejected
    # ------------------------------------------------------------------

    def test_naive_datetime_object_rejected(self) -> None:
        """A naive datetime object (no tzinfo) raises ValidationError."""
        naive = datetime(2026, 3, 27, 2, 30, 0)  # no tzinfo
        with pytest.raises(ValidationError):
            OwlbearProjectFile(**_valid_data(created_at=naive))

    def test_naive_datetime_string_rejected(self) -> None:
        """ISO 8601 string without timezone offset raises ValidationError."""
        with pytest.raises(ValidationError):
            OwlbearProjectFile(**_valid_data(created_at="2026-03-27T02:30:00"))

    # ------------------------------------------------------------------
    # AC8: Invalid datetime string rejected
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "bad_dt",
        ["not-a-date", "2026/03/27", "yesterday", ""],
    )
    def test_invalid_datetime_string_rejected(self, bad_dt: str) -> None:
        """Unparseable datetime strings raise ValidationError."""
        with pytest.raises(ValidationError):
            OwlbearProjectFile(**_valid_data(created_at=bad_dt))

    # ------------------------------------------------------------------
    # AC9: model_validate_json round-trip works
    # ------------------------------------------------------------------

    def test_model_validate_json_roundtrip(self) -> None:
        """model_validate_json deserializes a valid JSON string correctly."""
        json_str = json.dumps(_valid_data())
        model = OwlbearProjectFile.model_validate_json(json_str)
        assert model.schema_version == 1
        assert model.name == "my-project"
        assert model.created_at.tzinfo is not None

    def test_model_validate_json_preserves_extra_fields(self) -> None:
        """model_validate_json also stores extra fields in model_extra."""
        data = _valid_data(extra_note="preserved")
        json_str = json.dumps(data)
        model = OwlbearProjectFile.model_validate_json(json_str)
        assert model.model_extra is not None
        assert model.model_extra.get("extra_note") == "preserved"

    # ------------------------------------------------------------------
    # AC10: Missing required field raises ValidationError (all 5 fields)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "missing_field",
        ["schema_version", "name", "type", "owlbear_path", "created_at"],
    )
    def test_missing_required_field_raises(self, missing_field: str) -> None:
        """Omitting any single required field raises ValidationError."""
        data = _valid_data()
        del data[missing_field]  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            OwlbearProjectFile(**data)

    # ------------------------------------------------------------------
    # AC11: Each valid type value accepted (bare, python-uv, python-pip, node)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("valid_type", ["bare", "python-uv", "python-pip", "node"])
    def test_valid_type_values_accepted(self, valid_type: str) -> None:
        """Each Literal type value is accepted without error."""
        model = OwlbearProjectFile(**_valid_data(type=valid_type))
        assert model.type == valid_type
