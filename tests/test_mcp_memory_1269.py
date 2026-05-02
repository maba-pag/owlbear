"""Failing tests for P1-03: Implement MemoryEntry Pydantic model (#1269).

Scope items NOT covered by test_memory_models_1268.py:
  SC1: id field must validate as UUIDv4 format (current: plain str, no validation)
  SC2: created_at must validate as ISO 8601 datetime (current: plain str)
  SC3: updated_at must validate as ISO 8601 datetime (current: plain str)

AC items already covered and their disposition:
  AC1 (all tests from #1268 pass GREEN) — deferred to test_memory_models_1268.py;
      tests there PASS because models.py satisfies the contract already.
  AC2 (confidence [0.7, 1.0]) — fully covered in test_memory_models_1268.py.
  AC3 (Category enum has exactly 9 values) — models.py Literal already has
      exactly 9; a count test would pass immediately → removed per RED-phase rule.
  AC4 (State enum has exactly 4 values, "pending" default) — covered in
      test_memory_models_1268.py; model satisfies already.
  AC5 (No SQLite references in models.py) — models.py is clean; inspection test
      passes immediately → removed per RED-phase rule.

All tests in this file FAIL (RED phase) — current model uses plain str for id,
created_at, and updated_at with no format validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear_mcp_memory.models import MemoryEntry


def _valid() -> dict:
    """Minimal valid entry per new schema (mirrors test_memory_models_1268.py)."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Test memory entry title",
        "content": "This is the entry content.",
        "categories": ["knowledge"],
        "confidence": 0.85,
        "state": "pending",
        "created_at": "2026-05-02T10:00:00Z",
        "updated_at": "2026-05-02T10:00:00Z",
    }


class TestFromAC_IdValidation:
    """Scope: id must validate as UUIDv4 format — rejects arbitrary strings."""

    # ---- Error paths: invalid id values must raise ValidationError ----

    def test_non_uuid_string_rejected(self) -> None:
        """id='not-a-uuid' must raise ValidationError on the 'id' field."""
        data = {**_valid(), "id": "not-a-uuid"}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "id" in field_errors

    def test_short_numeric_string_rejected(self) -> None:
        """id='12345' (not UUID format) must raise ValidationError on 'id'."""
        data = {**_valid(), "id": "12345"}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "id" in field_errors

    def test_empty_id_rejected(self) -> None:
        """Empty string id must raise ValidationError on 'id'."""
        data = {**_valid(), "id": ""}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "id" in field_errors

    def test_uuid_without_hyphens_rejected(self) -> None:
        """id with valid UUID hex but no hyphens must raise ValidationError."""
        data = {**_valid(), "id": "550e8400e29b41d4a716446655440000"}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "id" in field_errors

    def test_uuid_with_braces_rejected(self) -> None:
        """id in Windows GUID format {xxxxxxxx-...} must raise ValidationError."""
        data = {**_valid(), "id": "{550e8400-e29b-41d4-a716-446655440000}"}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "id" in field_errors


class TestFromAC_TimestampValidation:
    """Scope: created_at / updated_at must validate as ISO 8601 datetimes."""

    # ---- Error paths: non-datetime strings must raise ValidationError ----

    def test_created_at_non_date_string_rejected(self) -> None:
        """created_at='not-a-date' must raise ValidationError on 'created_at'."""
        data = {**_valid(), "created_at": "not-a-date"}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "created_at" in field_errors

    def test_updated_at_non_date_string_rejected(self) -> None:
        """updated_at='not-a-date' must raise ValidationError on 'updated_at'."""
        data = {**_valid(), "updated_at": "not-a-date"}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "updated_at" in field_errors

    def test_created_at_empty_string_rejected(self) -> None:
        """created_at='' must raise ValidationError on 'created_at'."""
        data = {**_valid(), "created_at": ""}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "created_at" in field_errors

    def test_updated_at_empty_string_rejected(self) -> None:
        """updated_at='' must raise ValidationError on 'updated_at'."""
        data = {**_valid(), "updated_at": ""}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "updated_at" in field_errors

    def test_created_at_integer_timestamp_rejected(self) -> None:
        """Unix epoch integer (as string) must not satisfy ISO datetime validation."""
        data = {**_valid(), "created_at": "1746180000"}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "created_at" in field_errors

    def test_updated_at_integer_timestamp_rejected(self) -> None:
        """Unix epoch integer (as string) must not satisfy ISO datetime validation."""
        data = {**_valid(), "updated_at": "1746180000"}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "updated_at" in field_errors

