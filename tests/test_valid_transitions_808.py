"""Tests for Add valid_transitions(status) (#808, RED phase).

AC coverage:
  AC4 - end_work() docstring documents linear success progression as agent-specific
        convention, not a general state machine rule

Note: AC1-AC3 (valid_transitions contract) are covered by the paired test file
test_valid_transitions_807.py (#807). This file covers the AC unique to #808.
AC5 (#807 tests pass GREEN) and AC6 (existing MCP tests pass) are builder
verification steps that cannot be expressed as isolated unit tests here.
"""

from __future__ import annotations

from owlbear_kanban import KanbanEngine


class TestFromAC_EndWorkDocstring:
    """Tests for AC4: end_work() docstring documents linear behavior as agent-specific."""

    # -----------------------------------------------------------------------
    # AC4: linear success behavior documented as agent-specific in docstring
    # -----------------------------------------------------------------------

    def test_end_work_docstring_uses_word_agent(self) -> None:
        """AC4 (happy): The word 'agent' must appear in end_work()'s docstring.

        The docstring must explicitly note that linear advancement on outcome='success'
        is an agent workflow convention, not a constraint of the underlying state machine.
        The word 'agent' is the minimum signal that this distinction is communicated.
        """
        doc = KanbanEngine.end_work.__doc__ or ""
        assert "agent" in doc.lower(), (
            "end_work() docstring must document that the linear success progression "
            "is an agent-specific convention. The word 'agent' was not found. "
            f"Current docstring: {doc!r}"
        )

    def test_end_work_docstring_notes_linear_success_is_a_convention(self) -> None:
        """AC4 (edge): Docstring explicitly labels linear advancement as a convention.

        One of the words 'convention', 'agent-specific', or 'agent specific' must appear
        so that consumers understand the success path advances linearly by pipeline
        protocol, not because the state machine prohibits other transitions.
        """
        doc = KanbanEngine.end_work.__doc__ or ""
        convention_signals = ("convention", "agent-specific", "agent specific")
        assert any(s in doc.lower() for s in convention_signals), (
            "end_work() docstring should explicitly label linear success progression "
            "as a convention. None of the expected signals "
            f"{convention_signals!r} were found. "
            f"Current docstring: {doc!r}"
        )

    def test_end_work_docstring_contrasts_linear_with_general_state_machine(
        self,
    ) -> None:
        """AC4 (boundary): Docstring must distinguish agent convention from state-machine rule.

        The note should help consumers understand that valid_transitions() returns the
        full reachable set while end_work/success only steps forward by convention.
        The docstring must contain 'agent' OR reference 'valid_transitions' as context.
        """
        doc = KanbanEngine.end_work.__doc__ or ""
        has_agent = "agent" in doc.lower()
        has_cross_ref = "valid_transitions" in doc
        assert has_agent or has_cross_ref, (
            "end_work() docstring must either use 'agent' to denote the convention "
            "or cross-reference valid_transitions() for flexible routing. "
            f"Current docstring: {doc!r}"
        )
