"""Failing tests for #1302: Memory schema model tests.

AC coverage:
  AC1: MemoryCategory enum has 9 values (domain-knowledge, behaviour, pitfall,
       process, tool-usage, goal, personality, preference, env-context)
  AC2: MemoryState enum has 4 values (pending, curated, approved, deleted)
  AC3: Entry model fields: id, title, categories, confidence, state, scope_agents,
       source_agent, created_at, updated_at, approved_at
  AC4: confidence validation rejects values outside [0.7, 1.0]
  AC5: content length validation rejects >1024 chars
  AC6: categories validation requires >=1 value from enum
  AC7: source_agent is required and rejects reassignment after construction
  AC8: scope_agents defaults to [] (empty list, not None)
  AC9: frontmatter YAML serialization roundtrip — write metadata fields → read
       preserves all fields; content is markdown body, not frontmatter
  (AC10: test module fails — RED state guaranteed by category name changes,
   missing source_agent/approved_at fields, and missing validations)

All tests are RED: category enum names changed, source_agent/approved_at
missing, content length not validated, scope_agents defaults to None.
"""

from __future__ import annotations

import asyncio
import enum
import tempfile
from unittest.mock import MagicMock

import pytest
import yaml
from pydantic import ValidationError

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryCategory, MemoryEntry, MemoryState
from owlbear_mcp_memory.tools import store_learning

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ID = "550e8400-e29b-41d4-a716-446655440000"
_VALID_TS = "2026-05-01T10:00:00+00:00"


def _valid_old() -> dict:
    """Base data valid in the CURRENT model (old category names, no new fields).

    Used for rejection tests that isolate a specific NEW validation so the test
    fails because the new validation is absent — not because of unrelated errors.
    Constructs MemoryEntry successfully in current code.
    """
    return {
        "id": _VALID_ID,
        "title": "Test memory entry",
        "categories": ["knowledge"],
        "confidence": 0.85,
        "state": "pending",
        "content": "Entry body text.",
        "created_at": _VALID_TS,
        "updated_at": _VALID_TS,
    }


def _make_valid_entry(**overrides: object) -> MemoryEntry:
    """Return a valid new-design MemoryEntry.

    Uses the new schema: source_agent required, approved_at present,
    scope_agents defaults to [], categories use new enum names.
    Construction will fail in RED phase because of missing/extra fields.
    """
    defaults: dict[str, object] = {
        "id": _VALID_ID,
        "title": "Test memory entry",
        "categories": ["domain-knowledge"],
        "confidence": 0.9,
        "state": "pending",
        "content": "Test content body.",
        "source_agent": "builder",
        "scope_agents": [],
        "created_at": _VALID_TS,
        "updated_at": _VALID_TS,
        "approved_at": None,
    }
    defaults.update(overrides)
    return MemoryEntry(**defaults)


# ---------------------------------------------------------------------------
# AC1: MemoryCategory enum
# ---------------------------------------------------------------------------


class TestFromAC_MemoryCategory:
    """AC1: MemoryCategory is an enum with 9 specified values."""

    def test_is_enum_class(self) -> None:
        # Literal type aliases are not enum.Enum subclasses → fails in RED
        assert isinstance(MemoryCategory, type)
        assert issubclass(MemoryCategory, enum.Enum)

    def test_has_nine_members(self) -> None:
        # len() is not defined on Literal type aliases → TypeError in RED
        assert len(MemoryCategory) == 9

    def test_domain_knowledge_member(self) -> None:
        # Calling Literal type alias as function raises TypeError in RED
        member = MemoryCategory("domain-knowledge")
        assert member.value == "domain-knowledge"

    def test_behaviour_member(self) -> None:
        member = MemoryCategory("behaviour")
        assert member.value == "behaviour"

    def test_pitfall_member(self) -> None:
        member = MemoryCategory("pitfall")
        assert member.value == "pitfall"

    def test_process_member(self) -> None:
        member = MemoryCategory("process")
        assert member.value == "process"

    def test_tool_usage_member(self) -> None:
        # Old name was "tool" → renamed to "tool-usage"
        member = MemoryCategory("tool-usage")
        assert member.value == "tool-usage"

    def test_goal_member(self) -> None:
        member = MemoryCategory("goal")
        assert member.value == "goal"

    def test_personality_member(self) -> None:
        member = MemoryCategory("personality")
        assert member.value == "personality"

    def test_preference_member(self) -> None:
        member = MemoryCategory("preference")
        assert member.value == "preference"

    def test_env_context_member(self) -> None:
        # Old name was "context" → renamed to "env-context"
        member = MemoryCategory("env-context")
        assert member.value == "env-context"

    def test_old_knowledge_name_absent(self) -> None:
        # "knowledge" was renamed to "domain-knowledge"; old name must not be valid
        # In RED: Literal not callable → TypeError; pytest.raises(ValueError) fails ✓
        with pytest.raises(ValueError):
            MemoryCategory("knowledge")

    def test_old_tool_name_absent(self) -> None:
        # "tool" was renamed to "tool-usage"
        with pytest.raises(ValueError):
            MemoryCategory("tool")

    def test_old_context_name_absent(self) -> None:
        # "context" was renamed to "env-context"
        with pytest.raises(ValueError):
            MemoryCategory("context")

    def test_all_nine_values_present(self) -> None:
        expected = {
            "domain-knowledge",
            "behaviour",
            "pitfall",
            "process",
            "tool-usage",
            "goal",
            "personality",
            "preference",
            "env-context",
        }
        actual = {m.value for m in MemoryCategory}
        assert actual == expected


# ---------------------------------------------------------------------------
# AC2: MemoryState enum
# ---------------------------------------------------------------------------


class TestFromAC_MemoryState:
    """AC2: MemoryState is an enum with 4 values."""

    def test_is_enum_class(self) -> None:
        assert isinstance(MemoryState, type)
        assert issubclass(MemoryState, enum.Enum)

    def test_has_four_members(self) -> None:
        assert len(MemoryState) == 4

    def test_pending_member(self) -> None:
        assert MemoryState("pending").value == "pending"

    def test_curated_member(self) -> None:
        assert MemoryState("curated").value == "curated"

    def test_approved_member(self) -> None:
        assert MemoryState("approved").value == "approved"

    def test_deleted_member(self) -> None:
        assert MemoryState("deleted").value == "deleted"


# ---------------------------------------------------------------------------
# AC3: Entry model fields
# ---------------------------------------------------------------------------


class TestFromAC_EntryFields:
    """AC3: MemoryEntry has all required fields including source_agent and approved_at."""

    def test_source_agent_field_present(self) -> None:
        # model_fields contains all declared fields; source_agent must be declared
        assert "source_agent" in MemoryEntry.model_fields

    def test_approved_at_field_present(self) -> None:
        assert "approved_at" in MemoryEntry.model_fields

    def test_entry_creation_with_all_fields(self) -> None:
        # Full new-design construction — fails in RED due to missing/extra fields
        entry = _make_valid_entry()
        assert entry.id == _VALID_ID
        assert entry.title == "Test memory entry"
        assert entry.source_agent == "builder"
        assert entry.approved_at is None

    def test_entry_has_approved_at_none_by_default(self) -> None:
        entry = _make_valid_entry()
        assert entry.approved_at is None

    def test_entry_approved_at_accepts_timestamp(self) -> None:
        entry = _make_valid_entry(approved_at="2026-05-02T10:00:00+00:00")
        assert entry.approved_at == "2026-05-02T10:00:00+00:00"

    def test_id_non_uuid_string_rejected(self) -> None:
        # UUIDv4 validator already present in model — confirms contract.
        # Uses _valid_old() base so only the id varies; passes in RED.
        with pytest.raises(ValidationError):
            MemoryEntry(**{**_valid_old(), "id": "not-a-uuid"})

    def test_id_uuid_v1_format_rejected(self) -> None:
        # Version digit is '1' not '4' → regex rejects it.
        with pytest.raises(ValidationError):
            MemoryEntry(
                **{**_valid_old(), "id": "550e8400-e29b-11d4-a716-446655440000"}
            )

    def test_id_uuid_without_hyphens_rejected(self) -> None:
        # Canonical format requires hyphens.
        with pytest.raises(ValidationError):
            MemoryEntry(**{**_valid_old(), "id": "550e8400e29b41d4a716446655440000"})


# ---------------------------------------------------------------------------
# AC4: Confidence validation
# ---------------------------------------------------------------------------


class TestFromAC_ConfidenceValidation:
    """AC4: confidence must be within [0.7, 1.0]."""

    def test_confidence_below_minimum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_valid_entry(confidence=0.69)

    def test_confidence_above_maximum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_valid_entry(confidence=1.01)

    def test_confidence_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_valid_entry(confidence=0.0)

    def test_confidence_at_minimum_accepted(self) -> None:
        entry = _make_valid_entry(confidence=0.7)
        assert entry.confidence == pytest.approx(0.7)

    def test_confidence_at_maximum_accepted(self) -> None:
        entry = _make_valid_entry(confidence=1.0)
        assert entry.confidence == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# AC5: Content length validation
# ---------------------------------------------------------------------------


class TestFromAC_ContentValidation:
    """AC5: content must be <=1024 characters."""

    def test_content_at_1024_chars_accepted(self) -> None:
        entry = _make_valid_entry(content="x" * 1024)
        assert len(entry.content) == 1024

    def test_content_at_1025_chars_rejected(self) -> None:
        # Uses _valid_old() so failure is specifically about missing length validation,
        # not about unrelated new-schema fields. In RED: no length check → no error → FAILS.
        with pytest.raises(ValidationError):
            MemoryEntry(**{**_valid_old(), "content": "x" * 1025})

    def test_content_at_2000_chars_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MemoryEntry(**{**_valid_old(), "content": "x" * 2000})

    def test_content_empty_accepted(self) -> None:
        # Empty string is a valid (if sparse) body
        entry = _make_valid_entry(content="")
        assert entry.content == ""

    def test_content_at_1025_chars_rejected_new_schema(self) -> None:
        """Discriminating: ValidationError must be on the 'content' field specifically.

        In RED: source_agent is extra → error is on source_agent, not content
        → assertion fails (wrong field). Fails for wrong reason but is RED.
        In GREEN: length validator fires on content → 'content' in field_names → PASS.
        """
        with pytest.raises(ValidationError) as exc_info:
            _make_valid_entry(content="x" * 1025)
        errors = exc_info.value.errors()
        field_names = [str(e["loc"][0]) for e in errors if e["loc"]]
        assert "content" in field_names, (
            f"Expected ValidationError on 'content' field, got errors on: {field_names}"
        )


# ---------------------------------------------------------------------------
# AC6: Categories validation
# ---------------------------------------------------------------------------


class TestFromAC_CategoriesValidation:
    """AC6: categories requires >=1 value from the enum."""

    def test_empty_categories_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_valid_entry(categories=[])

    def test_single_valid_category_accepted(self) -> None:
        entry = _make_valid_entry(categories=["domain-knowledge"])
        assert len(entry.categories) == 1

    def test_multiple_valid_categories_accepted(self) -> None:
        entry = _make_valid_entry(categories=["domain-knowledge", "pitfall"])
        assert len(entry.categories) == 2

    def test_invalid_category_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_valid_entry(categories=["invalid-category-name"])

    def test_old_knowledge_category_rejected(self) -> None:
        # "knowledge" renamed to "domain-knowledge"; old name must be rejected.
        # Uses _valid_old() base so the ONLY reason for rejection is the category name.
        # In RED: "knowledge" IS valid in current Literal → no ValidationError → FAILS.
        with pytest.raises(ValidationError):
            MemoryEntry(**{**_valid_old(), "categories": ["knowledge"]})

    def test_old_tool_category_rejected(self) -> None:
        # "tool" renamed to "tool-usage".
        with pytest.raises(ValidationError):
            MemoryEntry(**{**_valid_old(), "categories": ["tool"]})

    def test_old_context_category_rejected(self) -> None:
        # "context" renamed to "env-context".
        with pytest.raises(ValidationError):
            MemoryEntry(**{**_valid_old(), "categories": ["context"]})

    def test_old_knowledge_category_rejected_new_schema(self) -> None:
        """Discriminating: ValidationError must be specifically on 'categories' field.

        In RED: source_agent is extra → error on source_agent, not categories
        → assertion fails. In GREEN: 'knowledge' not in new enum → 'categories' error.
        """
        with pytest.raises(ValidationError) as exc_info:
            _make_valid_entry(categories=["knowledge"])
        errors = exc_info.value.errors()
        field_names = [str(e["loc"][0]) for e in errors if e["loc"]]
        assert "categories" in field_names, (
            f"Expected ValidationError on 'categories' field, got: {field_names}"
        )


# ---------------------------------------------------------------------------
# AC7: source_agent validation
# ---------------------------------------------------------------------------


class TestFromAC_SourceAgentValidation:
    """AC7: source_agent is required and immutable after construction."""

    def test_source_agent_required(self) -> None:
        # Omitting source_agent must raise ValidationError in new design.
        # Uses _valid_old() base (no source_agent present) so the failure is
        # specifically about source_agent being required — not unrelated fields.
        # In RED: source_agent is not required in current model → no error → FAILS ✓
        with pytest.raises(ValidationError):
            MemoryEntry(**_valid_old())

    def test_source_agent_immutable_after_construction(self) -> None:
        # Reassignment must raise — either ValidationError (frozen field) or
        # AttributeError (frozen model). In RED: source_agent field absent → fails ✓
        entry = _make_valid_entry()
        with pytest.raises((ValidationError, AttributeError)):
            entry.source_agent = "other-agent"

    def test_source_agent_required_new_schema(self) -> None:
        """Discriminating: omitting source_agent from a new-schema payload raises
        ValidationError specifically on the source_agent field.

        In RED: approved_at is extra → error on 'approved_at', not 'source_agent'
        → assertion fails. In GREEN: source_agent missing → 'source_agent' error.
        """
        data = {
            "id": _VALID_ID,
            "title": "Test memory entry",
            "categories": ["domain-knowledge"],
            "confidence": 0.9,
            "state": "pending",
            "content": "Test body.",
            "created_at": _VALID_TS,
            "updated_at": _VALID_TS,
            "approved_at": None,
            # source_agent intentionally omitted
        }
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(**data)
        errors = exc_info.value.errors()
        field_names = [str(e["loc"][0]) for e in errors if e["loc"]]
        assert "source_agent" in field_names, (
            f"Expected ValidationError on 'source_agent' field, got: {field_names}"
        )


# ---------------------------------------------------------------------------
# AC8: scope_agents default
# ---------------------------------------------------------------------------


class TestFromAC_ScopeAgentsDefault:
    """AC8: scope_agents defaults to [] (not None)."""

    def test_scope_agents_default_is_empty_list(self) -> None:
        # Current model defaults scope_agents to None → assertion fails ✓
        entry = _make_valid_entry()
        assert entry.scope_agents == []

    def test_scope_agents_default_is_not_none(self) -> None:
        entry = _make_valid_entry()
        assert entry.scope_agents is not None

    def test_scope_agents_accepts_empty_list(self) -> None:
        entry = _make_valid_entry(scope_agents=[])
        assert entry.scope_agents == []

    def test_scope_agents_accepts_wildcard(self) -> None:
        entry = _make_valid_entry(scope_agents=["*"])
        assert entry.scope_agents == ["*"]

    def test_scope_agents_accepts_agent_names(self) -> None:
        entry = _make_valid_entry(scope_agents=["builder", "reviewer"])
        assert entry.scope_agents == ["builder", "reviewer"]

    def test_scope_agents_default_when_not_provided(self) -> None:
        """scope_agents must default to [] when omitted from constructor.

        In RED: source_agent/approved_at are extra → ValidationError before
        reaching default assignment → test errors (FAIL).
        In GREEN: construction succeeds; default is [] not None → PASS.
        """
        data = {
            "id": _VALID_ID,
            "title": "Test memory entry",
            "categories": ["domain-knowledge"],
            "confidence": 0.9,
            "state": "pending",
            "content": "Test body.",
            "source_agent": "builder",
            "created_at": _VALID_TS,
            "updated_at": _VALID_TS,
            "approved_at": None,
            # scope_agents intentionally omitted — must default to []
        }
        entry = MemoryEntry(**data)
        assert entry.scope_agents == []


# ---------------------------------------------------------------------------
# AC9: Frontmatter YAML serialization roundtrip
# ---------------------------------------------------------------------------


class TestFromAC_SerializationRoundtrip:
    """AC9: metadata fields serialize to/from YAML frontmatter; content is body."""

    def test_content_excluded_from_frontmatter_dict(self) -> None:
        # Simulate frontmatter extraction: model_dump excluding content
        # In RED: _make_valid_entry() fails → test errors ✓
        entry = _make_valid_entry()
        frontmatter = entry.model_dump(exclude={"content"})
        assert "content" not in frontmatter

    def test_source_agent_in_frontmatter(self) -> None:
        entry = _make_valid_entry()
        frontmatter = entry.model_dump(exclude={"content"})
        assert "source_agent" in frontmatter
        assert frontmatter["source_agent"] == "builder"

    def test_approved_at_in_frontmatter(self) -> None:
        entry = _make_valid_entry(approved_at="2026-05-02T10:00:00+00:00")
        frontmatter = entry.model_dump(exclude={"content"})
        assert "approved_at" in frontmatter
        assert frontmatter["approved_at"] == "2026-05-02T10:00:00+00:00"

    def test_yaml_roundtrip_preserves_all_fields(self) -> None:
        entry = _make_valid_entry(
            approved_at="2026-05-02T10:00:00+00:00",
            scope_agents=["builder"],
        )
        body = entry.content
        frontmatter = entry.model_dump(exclude={"content"})

        yaml_str = yaml.safe_dump(frontmatter)
        loaded = yaml.safe_load(yaml_str)
        loaded["content"] = body

        restored = MemoryEntry(**loaded)
        assert restored.id == entry.id
        assert restored.title == entry.title
        assert restored.source_agent == entry.source_agent
        assert restored.approved_at == entry.approved_at
        assert restored.scope_agents == entry.scope_agents
        assert restored.content == entry.content
        assert restored.categories == entry.categories
        assert restored.confidence == entry.confidence
        assert restored.state == entry.state
        assert restored.created_at == entry.created_at
        assert restored.updated_at == entry.updated_at

    def test_content_is_body_not_in_frontmatter(self) -> None:
        content_body = "This is the markdown body of the memory entry."
        entry = _make_valid_entry(content=content_body)
        frontmatter = entry.model_dump(exclude={"content"})

        fm_yaml = yaml.safe_dump(frontmatter)
        assert content_body not in fm_yaml
        assert entry.content == content_body

    def test_null_approved_at_roundtrips_correctly(self) -> None:
        entry = _make_valid_entry(approved_at=None)
        frontmatter = entry.model_dump(exclude={"content"})
        yaml_str = yaml.safe_dump(frontmatter)
        loaded = yaml.safe_load(yaml_str)
        loaded["content"] = entry.content
        restored = MemoryEntry(**loaded)
        assert restored.approved_at is None


# ---------------------------------------------------------------------------
# AC9: Real engine frontmatter roundtrip
# ---------------------------------------------------------------------------


class TestFromAC_EngineRoundtrip:
    """AC9: Real MemoryEngine.write() + load() roundtrip covers the actual
    serialization path — not simulated dict/YAML manipulation.

    All tests fail in RED because _make_valid_entry() raises ValidationError
    (source_agent is an extra field in the current model) before write() is
    ever called.  In GREEN the engine must also write source_agent and
    approved_at to frontmatter so _load_file() can reconstruct the entry.
    """

    def test_write_and_load_preserves_all_fields(self) -> None:
        """write() then load() restores all metadata fields."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = MemoryEngine(tmp)
            entry = _make_valid_entry(
                approved_at="2026-05-02T10:00:00+00:00",
                scope_agents=["builder"],
            )
            engine.write(entry)
            entries = engine.load()
            assert len(entries) == 1
            restored = entries[0]
            assert restored.id == entry.id
            assert restored.title == entry.title
            assert restored.source_agent == entry.source_agent
            assert restored.approved_at == entry.approved_at
            assert restored.scope_agents == entry.scope_agents
            assert restored.content == entry.content
            assert restored.categories == entry.categories
            assert restored.confidence == entry.confidence
            assert restored.state == entry.state
            assert restored.created_at == entry.created_at
            assert restored.updated_at == entry.updated_at

    def test_content_is_body_not_frontmatter_in_file(self) -> None:
        """write() places content in the markdown body section, not in YAML frontmatter."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = MemoryEngine(tmp)
            content = "UNIQUE_BODY_MARKER: must not appear in YAML frontmatter section."
            entry = _make_valid_entry(content=content)
            path = engine.write(entry)
            raw = path.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            assert len(parts) == 3, (
                "File must have opening and closing frontmatter delimiters"
            )
            frontmatter_section = parts[1]
            body_section = parts[2]
            assert content not in frontmatter_section
            assert content in body_section

    def test_source_agent_written_to_frontmatter(self) -> None:
        """write() includes source_agent in the YAML frontmatter block."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = MemoryEngine(tmp)
            entry = _make_valid_entry(source_agent="reviewer")
            path = engine.write(entry)
            raw = path.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            assert "source_agent" in frontmatter
            assert frontmatter["source_agent"] == "reviewer"

    def test_load_round_trips_approved_at_null(self) -> None:
        """load() correctly restores approved_at=None written as null in frontmatter."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = MemoryEngine(tmp)
            entry = _make_valid_entry(approved_at=None)
            engine.write(entry)
            entries = engine.load()
            assert len(entries) == 1
            assert entries[0].approved_at is None


# ---------------------------------------------------------------------------
# AC11: store_learning() normalizes scope_agents=None → []
# ---------------------------------------------------------------------------


class TestFromAC_StoreLearningNormalization:
    """AC11: store_learning() normalizes scope_agents=None to [] before constructing MemoryEntry.

    Regression from builder commit 269f11d6: tools.py passes scope_agents=scope_agents
    directly to MemoryEntry, but MemoryEntry.scope_agents is list[str] (not list[str]|None).
    Passing None explicitly bypasses the default_factory and raises ValidationError,
    which tools.py wraps as ToolError instead of returning an entry with scope_agents=[].

    In RED: store_learning raises ToolError (via ValidationError for scope_agents=None) →
            assertion is never reached → test FAILS.
    In GREEN: tools.py normalizes scope_agents or []  (or omits the kwarg) →
              MemoryEntry.scope_agents defaults to [] → result["scope_agents"] == [] → PASS.
    """

    def test_store_learning_scope_agents_none_normalized_to_empty_list(self) -> None:
        """Omitting scope_agents (default None) must produce scope_agents=[] in the result.

        Current code: MemoryEntry(scope_agents=None, ...) → ValidationError (list[str] rejects
        None) → ToolError raised before return → assertion unreachable → FAIL (RED).
        """
        with tempfile.TemporaryDirectory() as tmp:
            engine = MemoryEngine(tmp)
            ctx = MagicMock()
            ctx.request_context.lifespan_context.engine = engine
            ctx.request_context.lifespan_context.caller = "builder"

            result = asyncio.run(
                store_learning(
                    ctx,
                    title="Normalization test entry",
                    content="Test content body.",
                    categories=[MemoryCategory("domain-knowledge")],
                    confidence=0.85,
                    # scope_agents intentionally omitted — defaults to None in signature
                )
            )
            assert result["scope_agents"] == []
