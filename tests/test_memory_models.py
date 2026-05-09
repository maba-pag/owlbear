"""Failing tests for MemoryEntry Pydantic model — new schema (task #1268).

Tests import MemoryEntry from owlbear_mcp_memory.models and verify the
new schema contract: field types, validation constraints, state enum,
category enum, confidence range, and required vs optional fields.

All tests must FAIL (RED phase) — the current model does not implement
the new schema.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear_mcp_memory.models import MemoryEntry

VALID_CATEGORIES = [
    "knowledge",
    "behaviour",
    "pitfall",
    "process",
    "tool",
    "goal",
    "personality",
    "preference",
    "context",
]


def _valid() -> dict:
    """Minimal valid entry per new schema."""
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


class TestFromAC_MemoryEntryModel:
    """Contract tests for MemoryEntry new schema."""

    # ---- Happy path: valid entry constructs ----

    def test_valid_entry_constructs(self) -> None:
        """Valid entry with all required fields constructs successfully."""
        entry = MemoryEntry(**_valid())
        assert entry.id == "550e8400-e29b-41d4-a716-446655440000"
        assert entry.title == "Test memory entry title"
        assert entry.content == "This is the entry content."
        assert entry.categories == ["knowledge"]
        assert entry.confidence == pytest.approx(0.85)
        assert entry.state == "pending"

    def test_valid_entry_with_scope_agents(self) -> None:
        """Valid entry with optional scope_agents list constructs successfully."""
        data = {**_valid(), "scope_agents": ["builder", "reviewer"]}
        entry = MemoryEntry(**data)
        assert entry.scope_agents == ["builder", "reviewer"]

    def test_valid_entry_with_multi_categories(self) -> None:
        """Valid entry with multiple categories constructs successfully."""
        data = {**_valid(), "categories": ["knowledge", "pitfall", "process"]}
        entry = MemoryEntry(**data)
        assert len(entry.categories) == 3

    # ---- AC: State defaults to "pending" ----

    def test_state_defaults_to_pending(self) -> None:
        """State field defaults to 'pending' when omitted."""
        data = {**_valid()}
        del data["state"]
        entry = MemoryEntry(**data)
        assert entry.state == "pending"

    # ---- AC: scope_agents optional, defaults to None ----

    def test_scope_agents_defaults_to_none(self) -> None:
        """scope_agents defaults to None when omitted."""
        entry = MemoryEntry(**_valid())
        assert entry.scope_agents is None

    def test_scope_agents_accepts_list(self) -> None:
        """scope_agents accepts a list of agent name strings."""
        data = {**_valid(), "scope_agents": ["builder"]}
        entry = MemoryEntry(**data)
        assert entry.scope_agents == ["builder"]

    # ---- AC: All 4 state values valid ----

    def test_state_curated_valid(self) -> None:
        """State value 'curated' is accepted."""
        data = {**_valid(), "state": "curated"}
        entry = MemoryEntry(**data)
        assert entry.state == "curated"

    def test_state_approved_valid(self) -> None:
        """State value 'approved' is accepted."""
        data = {**_valid(), "state": "approved"}
        entry = MemoryEntry(**data)
        assert entry.state == "approved"

    def test_state_deleted_valid(self) -> None:
        """State value 'deleted' is accepted."""
        data = {**_valid(), "state": "deleted"}
        entry = MemoryEntry(**data)
        assert entry.state == "deleted"

    # ---- AC: Invalid state raises ValidationError ----

    def test_invalid_state_raises(self) -> None:
        """Invalid state value raises ValidationError on 'state' field."""
        data = {**_valid(), "state": "archived"}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "state" in field_errors

    def test_legacy_approval_state_name_rejected(self) -> None:
        """Old field name 'approval_state' is not accepted as 'state'."""
        # Construct without state; set via legacy key — must not resolve to state
        data = {**_valid()}
        del data["state"]
        data["approval_state"] = "pending"
        entry = MemoryEntry(**data)
        # state must still default to "pending" from the model default,
        # not be set by the legacy key alias
        assert entry.state == "pending"
        # the legacy field must not appear as an attribute on the new model
        assert not hasattr(entry, "approval_state")

    # ---- AC: All 9 category enum values valid ----

    @pytest.mark.parametrize("cat", VALID_CATEGORIES)
    def test_each_category_valid(self, cat: str) -> None:
        """Each of the 9 category enum values is accepted in a list."""
        data = {**_valid(), "categories": [cat]}
        entry = MemoryEntry(**data)
        assert cat in entry.categories

    # ---- AC: Invalid category raises ValidationError ----

    def test_invalid_category_raises(self) -> None:
        """Unknown category value raises ValidationError on 'categories' field."""
        data = {**_valid(), "categories": ["invalid_cat"]}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "categories" in field_errors

    def test_behavior_spelling_rejected(self) -> None:
        """Old US-English spelling 'behavior' (not 'behaviour') is rejected."""
        data = {**_valid(), "categories": ["behavior"]}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "categories" in field_errors

    # ---- AC: categories must be a non-empty list ----

    def test_categories_empty_list_raises(self) -> None:
        """Empty categories list raises ValidationError on 'categories' field."""
        data = {**_valid(), "categories": []}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "categories" in field_errors

    # ---- AC: Confidence range [0.7, 1.0] — boundary valid ----

    def test_confidence_at_min_boundary_valid(self) -> None:
        """Confidence at 0.7 (minimum boundary) is valid."""
        data = {**_valid(), "confidence": 0.7}
        entry = MemoryEntry(**data)
        assert entry.confidence == pytest.approx(0.7)

    def test_confidence_at_max_boundary_valid(self) -> None:
        """Confidence at 1.0 (maximum boundary) is valid."""
        data = {**_valid(), "confidence": 1.0}
        entry = MemoryEntry(**data)
        assert entry.confidence == pytest.approx(1.0)

    # ---- AC: Confidence < 0.7 raises ValidationError ----

    def test_confidence_below_min_raises(self) -> None:
        """Confidence < 0.7 raises ValidationError on 'confidence' field."""
        data = {**_valid(), "confidence": 0.69}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "confidence" in field_errors

    def test_confidence_zero_raises(self) -> None:
        """Confidence = 0.0 raises ValidationError on 'confidence' field."""
        data = {**_valid(), "confidence": 0.0}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "confidence" in field_errors

    def test_confidence_just_below_min_raises(self) -> None:
        """Confidence at 0.699 (just below 0.7) raises ValidationError."""
        data = {**_valid(), "confidence": 0.699}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "confidence" in field_errors

    # ---- AC: Confidence > 1.0 raises ValidationError ----

    def test_confidence_above_max_raises(self) -> None:
        """Confidence > 1.0 raises ValidationError on 'confidence' field."""
        data = {**_valid(), "confidence": 1.01}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "confidence" in field_errors

    def test_confidence_just_above_max_raises(self) -> None:
        """Confidence at 1.001 (just above 1.0) raises ValidationError."""
        data = {**_valid(), "confidence": 1.001}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "confidence" in field_errors

    # ---- AC: title is a non-empty string ----

    def test_title_empty_string_raises(self) -> None:
        """Empty title raises ValidationError on 'title' field."""
        data = {**_valid(), "title": ""}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "title" in field_errors

    def test_title_whitespace_only_raises(self) -> None:
        """Whitespace-only title raises ValidationError on 'title' field."""
        data = {**_valid(), "title": "   "}
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "title" in field_errors

    # ---- AC: Missing required fields raise ValidationError ----

    def test_missing_title_raises(self) -> None:
        """Missing required field 'title' raises ValidationError."""
        data = {**_valid()}
        del data["title"]
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "title" in field_errors

    def test_missing_categories_raises(self) -> None:
        """Missing required field 'categories' raises ValidationError."""
        data = {**_valid()}
        del data["categories"]
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        field_errors = {e["loc"][0] for e in exc_info.value.errors()}
        assert "categories" in field_errors

    # id, content, confidence, created_at, updated_at are already required
    # in the current model — those "missing field" tests would pass with the
    # old model and are therefore not new behaviour to test here. The builder
    # must preserve them (tested via the successful-construction test above).
