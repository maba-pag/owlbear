"""Tests for src/owlbear/memory/knowledge/cancellation.py (task #870).

All tests in this file fail against current HEAD because the
``owlbear.memory.knowledge.cancellation`` module does not yet exist.
"""

from __future__ import annotations

import ast
import asyncio
import pathlib

# ---------------------------------------------------------------------------
# TDD RED: CancelSignal protocol (#870)
# ---------------------------------------------------------------------------


class TestFromAC_CancelSignalProtocol:
    """CancelSignal is a runtime-checkable Protocol exposing only is_set() -> bool.

    AC 1: Add cancellation.py with CancelSignal protocol and LinkedCancelSignal
    adapter that composes multiple asyncio.Event sources without importing daemon
    code into memory/.
    """

    def test_cancel_signal_protocol_can_be_imported(self) -> None:
        """CancelSignal can be imported from the cancellation module."""
        from owlbear.memory.knowledge.cancellation import CancelSignal  # noqa: F401

    def test_asyncio_event_satisfies_cancel_signal_protocol(self) -> None:
        """asyncio.Event is structurally compatible with CancelSignal (has is_set())."""
        from owlbear.memory.knowledge.cancellation import CancelSignal

        event = asyncio.Event()
        assert isinstance(event, CancelSignal)

    def test_custom_class_with_is_set_satisfies_protocol(self) -> None:
        """Any class exposing is_set() -> bool satisfies CancelSignal."""
        from owlbear.memory.knowledge.cancellation import CancelSignal

        class _MySignal:
            def is_set(self) -> bool:
                return False

        assert isinstance(_MySignal(), CancelSignal)

    def test_class_without_is_set_does_not_satisfy_protocol(self) -> None:
        """A class without is_set() does not satisfy CancelSignal."""
        from owlbear.memory.knowledge.cancellation import CancelSignal

        class _NoIsSet:
            pass

        assert not isinstance(_NoIsSet(), CancelSignal)


# ---------------------------------------------------------------------------
# TDD RED: LinkedCancelSignal adapter (#870)
# ---------------------------------------------------------------------------


class TestFromAC_LinkedCancelSignal:
    """LinkedCancelSignal composes multiple CancelSignal sources.

    AC 1: linked adapter that composes multiple asyncio.Event sources without
    importing daemon code into memory/.
    AC 3: check cancel.is_set() at each loop boundary; stop cooperatively by
    returning only work completed before cancellation.
    """

    def test_linked_cancel_signal_can_be_imported(self) -> None:
        """LinkedCancelSignal can be imported from the cancellation module."""
        from owlbear.memory.knowledge.cancellation import LinkedCancelSignal  # noqa: F401

    def test_empty_sources_never_set(self) -> None:
        """LinkedCancelSignal with no sources always returns False from is_set()."""
        from owlbear.memory.knowledge.cancellation import LinkedCancelSignal

        sig = LinkedCancelSignal()
        assert sig.is_set() is False

    def test_single_set_source_is_set(self) -> None:
        """LinkedCancelSignal is set when its one source event is set."""
        from owlbear.memory.knowledge.cancellation import LinkedCancelSignal

        event = asyncio.Event()
        event.set()
        sig = LinkedCancelSignal(event)
        assert sig.is_set() is True

    def test_single_unset_source_not_set(self) -> None:
        """LinkedCancelSignal is not set when its one source event is not set."""
        from owlbear.memory.knowledge.cancellation import LinkedCancelSignal

        event = asyncio.Event()
        sig = LinkedCancelSignal(event)
        assert sig.is_set() is False

    def test_multiple_sources_any_set_means_set(self) -> None:
        """LinkedCancelSignal.is_set() is True when any of its sources is set."""
        from owlbear.memory.knowledge.cancellation import LinkedCancelSignal

        e1 = asyncio.Event()
        e2 = asyncio.Event()
        e2.set()  # only e2 is set
        sig = LinkedCancelSignal(e1, e2)
        assert sig.is_set() is True

    def test_multiple_sources_none_set_is_not_set(self) -> None:
        """LinkedCancelSignal.is_set() is False when none of its sources are set."""
        from owlbear.memory.knowledge.cancellation import LinkedCancelSignal

        e1 = asyncio.Event()
        e2 = asyncio.Event()
        sig = LinkedCancelSignal(e1, e2)
        assert sig.is_set() is False

    def test_reflects_live_source_state_set_after_construction(self) -> None:
        """LinkedCancelSignal.is_set() reflects the current live state of sources.

        This is the core correctness requirement: unlike a snapshot copy, the
        linked signal must dynamically delegate to its sources each time
        is_set() is called.
        """
        from owlbear.memory.knowledge.cancellation import LinkedCancelSignal

        event = asyncio.Event()
        sig = LinkedCancelSignal(event)

        assert sig.is_set() is False  # starts unset
        event.set()  # set AFTER the signal was constructed
        assert sig.is_set() is True  # must reflect live state

    def test_accepts_any_cancel_signal_not_just_asyncio_event(self) -> None:
        """LinkedCancelSignal accepts any CancelSignal-conformant object as a source."""
        from owlbear.memory.knowledge.cancellation import LinkedCancelSignal

        class _AlwaysSet:
            def is_set(self) -> bool:
                return True

        class _NeverSet:
            def is_set(self) -> bool:
                return False

        assert LinkedCancelSignal(_AlwaysSet()).is_set() is True
        assert LinkedCancelSignal(_NeverSet()).is_set() is False

    def test_satisfies_cancel_signal_protocol_itself(self) -> None:
        """LinkedCancelSignal itself satisfies the CancelSignal protocol."""
        from owlbear.memory.knowledge.cancellation import CancelSignal, LinkedCancelSignal

        sig = LinkedCancelSignal()
        assert isinstance(sig, CancelSignal)


# ---------------------------------------------------------------------------
# TDD RED: core -> memory layer constraint (#870 retry)
# ---------------------------------------------------------------------------

_SRC_ROOT = pathlib.Path(__file__).parent.parent / "src"
_RETRO_HOOK_SRC = _SRC_ROOT / "owlbear" / "core" / "retrospective_hook.py"


class TestFromAC_870_CoreLayerConstraint:
    """retrospective_hook.py must not import from owlbear.memory.knowledge at runtime.

    AC 5 architecture note: ``core/retrospective_hook.py`` must import
    ``CancelSignal`` only under ``TYPE_CHECKING`` and must never contain a
    top-level (runtime) import from ``owlbear.memory.knowledge``.  Bootstrap
    owns ``LinkedCancelSignal`` construction and injects it into
    ``RetrospectiveHook`` at construction time.

    Note: the pre-existing ``from owlbear.memory.usage import record_agent_usage``
    is an acknowledged layering bend from before this task and is therefore excluded
    from this constraint.  Only new ``owlbear.memory.knowledge`` imports are tested.

    Fails on current HEAD because retrospective_hook.py:22 has:

        from owlbear.memory.knowledge.cancellation import LinkedCancelSignal

    at the module top level (outside ``if TYPE_CHECKING:``).
    """

    def test_retrospective_hook_has_no_runtime_memory_knowledge_imports(self) -> None:
        """retrospective_hook.py has no top-level imports from owlbear.memory.knowledge.

        Top-level means: ``ImportFrom`` nodes at the module body level, i.e.
        not guarded by ``if TYPE_CHECKING:``.  Imports inside a
        ``TYPE_CHECKING`` block are invisible at runtime and are allowed.
        The pre-existing ``owlbear.memory.usage`` import is out of scope.
        """
        src = _RETRO_HOOK_SRC.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(_RETRO_HOOK_SRC))

        violations: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("owlbear.memory.knowledge"):
                    names = [alias.name for alias in node.names]
                    violations.append(f"from {module} import {names}")

        assert not violations, (
            "retrospective_hook.py must not import from owlbear.memory.knowledge at runtime "
            "(only under TYPE_CHECKING). Found forbidden top-level imports: "
            + ", ".join(violations)
            + ". LinkedCancelSignal composition must live in bootstrap/__init__.py."
        )
