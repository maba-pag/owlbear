"""Tests for #1515: ac and proof_bundle model fields + storage canonical fields.

AC lines tested:
  - AC1: Task constructor accepts ac/proof_bundle with correct defaults; both in model_dump
  - AC2: TaskSummary/DispatchEntry include proof_bundle, not ac; TaskFull inherits
         proof_bundle and adds ac
  - AC3: Task.proof_bundle field_validator normalizes case and sorts modifiers
         alphabetically; unknown strings pass through normalized
  - AC4: storage._CANONICAL_FIELDS has 'ac' and 'proof_bundle' immediately after
         'depends_on' and before 'blocked'
"""

from __future__ import annotations

from owlbear_kanban.models import DispatchEntry, Task, TaskFull, TaskSummary
from owlbear_kanban.storage import _CANONICAL_FIELDS

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_BASE_TASK_KWARGS: dict = {
    "id": 1,
    "title": "Test Task",
    "status": "todo",
    "priority": "needed",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
}

_BASE_SUMMARY_KWARGS: dict = {
    "id": 1,
    "title": "Test Task",
    "status": "todo",
    "priority": "needed",
    "updated": "2026-01-01T00:00:00+00:00",
}

_BASE_DISPATCH_KWARGS: dict = {
    "id": 1,
    "status": "todo",
    "priority": "needed",
    "title": "Test Task",
    "tags": [],
    "agent": "builder",
}


# ---------------------------------------------------------------------------
# AC1 — Task constructor accepts ac and proof_bundle with correct defaults
# ---------------------------------------------------------------------------


class TestFromAC_TaskModelFields:
    """AC1: Task declares ac and proof_bundle as typed fields with correct defaults."""

    def test_ac_is_declared_model_field(self) -> None:
        """AC1: 'ac' is a declared typed model field (not an extra)."""
        assert "ac" in Task.model_fields

    def test_proof_bundle_is_declared_model_field(self) -> None:
        """AC1: 'proof_bundle' is a declared typed model field (not an extra)."""
        assert "proof_bundle" in Task.model_fields

    def test_ac_default_is_empty_list(self) -> None:
        """AC1: ac defaults to [] when not provided."""
        task = Task(**_BASE_TASK_KWARGS)
        assert task.ac == []

    def test_proof_bundle_default_is_none(self) -> None:
        """AC1: proof_bundle defaults to None when not provided."""
        task = Task(**_BASE_TASK_KWARGS)
        assert task.proof_bundle is None

    def test_ac_in_model_dump_when_default(self) -> None:
        """AC1: ac appears in model_dump() output with default value."""
        task = Task(**_BASE_TASK_KWARGS)
        dumped = task.model_dump()
        assert "ac" in dumped
        assert dumped["ac"] == []

    def test_proof_bundle_in_model_dump_when_default(self) -> None:
        """AC1: proof_bundle appears in model_dump() output with default None."""
        task = Task(**_BASE_TASK_KWARGS)
        dumped = task.model_dump()
        assert "proof_bundle" in dumped
        assert dumped["proof_bundle"] is None

    def test_ac_round_trip_preserves_list_values(self) -> None:
        """AC1: ac with multiple entries survives model_dump() → model_validate().

        Gates on field declaration so the round-trip assertion is only reached
        once the field is properly declared.
        """
        assert "ac" in Task.model_fields  # gate: must be declared typed field
        task = Task(**_BASE_TASK_KWARGS, ac=["AC1: foo must pass", "AC2: bar must work"])
        restored = Task.model_validate(task.model_dump())
        assert restored.ac == ["AC1: foo must pass", "AC2: bar must work"]

    def test_proof_bundle_round_trip_preserves_non_default_value(self) -> None:
        """AC1: non-default proof_bundle survives model_dump() → model_validate().

        Discriminating test: a regression that drops or alters proof_bundle during
        revalidation would still pass without this assertion.
        """
        assert "proof_bundle" in Task.model_fields  # gate: must be declared typed field
        task = Task(**_BASE_TASK_KWARGS, proof_bundle="behavioral+challenge")
        restored = Task.model_validate(task.model_dump())
        assert restored.proof_bundle == "behavioral+challenge"


# ---------------------------------------------------------------------------
# AC2 — Projection field presence across TaskSummary, DispatchEntry, TaskFull
# ---------------------------------------------------------------------------


class TestFromAC_ProjectionFields:
    """AC2: proof_bundle in summaries/dispatch; ac only in TaskFull."""

    def test_task_summary_has_proof_bundle_field(self) -> None:
        """AC2: TaskSummary declares proof_bundle."""
        assert "proof_bundle" in TaskSummary.model_fields

    def test_dispatch_entry_has_proof_bundle_field(self) -> None:
        """AC2: DispatchEntry declares proof_bundle."""
        assert "proof_bundle" in DispatchEntry.model_fields

    def test_task_full_has_proof_bundle_field(self) -> None:
        """AC2: TaskFull includes proof_bundle (inherited from TaskSummary)."""
        assert "proof_bundle" in TaskFull.model_fields

    def test_task_full_has_ac_field(self) -> None:
        """AC2: TaskFull declares ac: list[str]."""
        assert "ac" in TaskFull.model_fields

    def test_task_summary_proof_bundle_propagated_to_instance(self) -> None:
        """AC2: TaskSummary instance constructed with proof_bundle exposes the value."""
        summary = TaskSummary(**_BASE_SUMMARY_KWARGS, proof_bundle="critical")
        assert summary.proof_bundle == "critical"

    def test_dispatch_entry_proof_bundle_propagated_to_instance(self) -> None:
        """AC2: DispatchEntry instance constructed with proof_bundle exposes the value."""
        entry = DispatchEntry(**_BASE_DISPATCH_KWARGS, proof_bundle="smoke")
        assert entry.proof_bundle == "smoke"

    def test_task_full_ac_accessible_on_instance(self) -> None:
        """AC2: TaskFull instance constructed with ac exposes the list."""
        full = TaskFull(
            **_BASE_SUMMARY_KWARGS,
            created="2026-01-01T00:00:00+00:00",
            ac=["- must pass"],
        )
        assert full.ac == ["- must pass"]

    def test_task_summary_does_not_have_ac_field(self) -> None:
        """AC2: 'ac' is absent from TaskSummary — regression guard.

        AC2 requires proof_bundle but NOT ac in summaries. Without this assertion
        a regression adding ac to TaskSummary would still pass all other tests.
        """
        assert "ac" not in TaskSummary.model_fields

    def test_dispatch_entry_does_not_have_ac_field(self) -> None:
        """AC2: 'ac' is absent from DispatchEntry — regression guard.

        AC2 requires proof_bundle but NOT ac in dispatch entries. Without this
        assertion a regression adding ac to DispatchEntry would still pass.
        """
        assert "ac" not in DispatchEntry.model_fields


# ---------------------------------------------------------------------------
# AC3 — proof_bundle field_validator normalizes case and sorts modifiers
# ---------------------------------------------------------------------------


class TestFromAC_ProofBundleNormalization:
    """AC3: proof_bundle field_validator on Task normalizes case and sorts modifiers."""

    def test_mixed_case_normalized_to_lowercase(self) -> None:
        """AC3: 'Behavioral+Challenge' → 'behavioral+challenge' (lowercased)."""
        task = Task(**_BASE_TASK_KWARGS, proof_bundle="Behavioral+Challenge")
        assert task.proof_bundle == "behavioral+challenge"

    def test_modifiers_sorted_alphabetically(self) -> None:
        """AC3: 'critical+reader+challenge' → 'critical+challenge+reader' per AC example."""
        task = Task(**_BASE_TASK_KWARGS, proof_bundle="critical+reader+challenge")
        assert task.proof_bundle == "critical+challenge+reader"

    def test_unknown_string_passed_through_normalized(self) -> None:
        """AC3: 'Garbage' → 'garbage'; unknown strings normalized without rejection."""
        task = Task(**_BASE_TASK_KWARGS, proof_bundle="Garbage")
        assert task.proof_bundle == "garbage"

    def test_none_passes_through_unchanged(self) -> None:
        """AC3 boundary: proof_bundle=None not transformed by validator.

        Gates on field declaration so that if the builder's validator does not
        handle None gracefully, this test catches the crash.
        """
        assert "proof_bundle" in Task.model_fields  # gate: field must be declared
        task = Task(**_BASE_TASK_KWARGS, proof_bundle=None)
        assert task.proof_bundle is None

    def test_two_modifiers_sorted(self) -> None:
        """AC3 boundary: two modifiers — 'smoke+behavioral' → 'behavioral+smoke'."""
        task = Task(**_BASE_TASK_KWARGS, proof_bundle="smoke+behavioral")
        assert task.proof_bundle == "behavioral+smoke"


# ---------------------------------------------------------------------------
# AC4 — storage._CANONICAL_FIELDS ordering
# ---------------------------------------------------------------------------


class TestFromAC_CanonicalFieldsOrdering:
    """AC4: _CANONICAL_FIELDS contains 'ac' and 'proof_bundle' after 'depends_on', before 'blocked'."""

    def test_ac_present_in_canonical_fields(self) -> None:
        """AC4: 'ac' is present in _CANONICAL_FIELDS."""
        assert "ac" in _CANONICAL_FIELDS

    def test_proof_bundle_present_in_canonical_fields(self) -> None:
        """AC4: 'proof_bundle' is present in _CANONICAL_FIELDS."""
        assert "proof_bundle" in _CANONICAL_FIELDS

    def test_ac_immediately_after_depends_on(self) -> None:
        """AC4: 'ac' appears at index depends_on+1."""
        idx = _CANONICAL_FIELDS.index("depends_on")
        assert _CANONICAL_FIELDS[idx + 1] == "ac"

    def test_proof_bundle_immediately_after_ac(self) -> None:
        """AC4: 'proof_bundle' appears at index ac+1."""
        idx = _CANONICAL_FIELDS.index("ac")
        assert _CANONICAL_FIELDS[idx + 1] == "proof_bundle"

    def test_blocked_immediately_after_proof_bundle(self) -> None:
        """AC4: 'blocked' appears at index proof_bundle+1."""
        idx = _CANONICAL_FIELDS.index("proof_bundle")
        assert _CANONICAL_FIELDS[idx + 1] == "blocked"

    def test_exact_sublist_order(self) -> None:
        """AC4: exact sublist ['depends_on', 'ac', 'proof_bundle', 'blocked'] in order."""
        idx = _CANONICAL_FIELDS.index("depends_on")
        assert _CANONICAL_FIELDS[idx : idx + 4] == [
            "depends_on",
            "ac",
            "proof_bundle",
            "blocked",
        ]
