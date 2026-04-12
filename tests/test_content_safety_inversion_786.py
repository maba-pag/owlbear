"""Failing tests for content safety predicate inversion — constant deduplication (#786).

Task: Content safety predicate inversion
File: serve/knowledge/src/owlbear_knowledge/content_safety.py

AC mapping:
  AC1: predicate changed from ``== "url"`` to ``not in ("file", "text", "file_glob")``
       → behavioral contract covered by #781 tests (test_content_safety_inversion_775.py).
  AC-quality: duplicate ``_ADVISORY``, ``_OPEN_TAG``, ``_CLOSE_TAG`` constant blocks
              must be removed — each module-level constant defined exactly once.
              This is the remaining builder work (arch review note).
"""

from __future__ import annotations

import inspect


class TestFromAC_ConstantDeduplication:
    """Constant deduplication — each sentinel constant must appear exactly once in the module.

    Current state: ``_ADVISORY``, ``_OPEN_TAG``, and ``_CLOSE_TAG`` are each assigned
    twice in ``content_safety.py`` (lines 9-17 and lines 44-52).  The second block is
    dead code introduced during initial scaffolding.  These three tests enforce the
    single-definition invariant so the builder knows exactly what to remove.
    """

    def test_advisory_constant_defined_exactly_once(self) -> None:
        """``_ADVISORY`` must not be redefined anywhere in content_safety.py."""
        import owlbear_knowledge.content_safety as cs_mod

        source = inspect.getsource(cs_mod)
        count = source.count("_ADVISORY = ")
        assert count == 1, (
            f"_ADVISORY is assigned {count} times in content_safety.py; "
            "deduplicate to a single module-level definition."
        )

    def test_open_tag_constant_defined_exactly_once(self) -> None:
        """``_OPEN_TAG`` must not be redefined anywhere in content_safety.py."""
        import owlbear_knowledge.content_safety as cs_mod

        source = inspect.getsource(cs_mod)
        count = source.count("_OPEN_TAG = ")
        assert count == 1, (
            f"_OPEN_TAG is assigned {count} times in content_safety.py; "
            "deduplicate to a single module-level definition."
        )

    def test_close_tag_constant_defined_exactly_once(self) -> None:
        """``_CLOSE_TAG`` must not be redefined anywhere in content_safety.py."""
        import owlbear_knowledge.content_safety as cs_mod

        source = inspect.getsource(cs_mod)
        count = source.count("_CLOSE_TAG = ")
        assert count == 1, (
            f"_CLOSE_TAG is assigned {count} times in content_safety.py; "
            "deduplicate to a single module-level definition."
        )
