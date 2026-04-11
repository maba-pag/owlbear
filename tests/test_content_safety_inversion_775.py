"""Unit tests for the should_wrap() content-safety predicate (#781 / parent #775).

Tests the contract for:
  - owlbear_knowledge.content_safety.should_wrap(source_type) — deny-list predicate

AC1: should_wrap() returns True for url_list, authenticated_web, and any unknown future type
     (defense-in-depth: unknown types are wrapped by default).
AC2: should_wrap() returns False for file, text, file_glob, and None
     (trusted exempt set + backward-compat None path).
"""

from __future__ import annotations


class TestFromAC_ShouldWrapPredicate:
    """should_wrap() deny-list predicate — AC1 (wrap) and AC2 (no-wrap) coverage."""

    # ------------------------------------------------------------------
    # AC1 — returns True for untrusted / unknown source types
    # ------------------------------------------------------------------

    def test_url_list_returns_true(self) -> None:
        """should_wrap('url_list') returns True — URL-list ingestion is untrusted."""
        from owlbear_knowledge.content_safety import should_wrap

        assert should_wrap("url_list") is True

    def test_authenticated_web_returns_true(self) -> None:
        """should_wrap('authenticated_web') returns True — web content is untrusted."""
        from owlbear_knowledge.content_safety import should_wrap

        assert should_wrap("authenticated_web") is True

    def test_unknown_future_type_returns_true(self) -> None:
        """should_wrap() returns True for an unrecognised future source type (defense-in-depth)."""
        from owlbear_knowledge.content_safety import should_wrap

        assert should_wrap("rss_feed") is True

    def test_arbitrary_invented_string_returns_true(self) -> None:
        """Any string not in the trusted exempt set returns True (deny-list, not allow-list)."""
        from owlbear_knowledge.content_safety import should_wrap

        assert should_wrap("some_future_source") is True

    # ------------------------------------------------------------------
    # AC2 — returns False for the trusted exempt set
    # ------------------------------------------------------------------

    def test_file_returns_false(self) -> None:
        """should_wrap('file') returns False — local file content is trusted."""
        from owlbear_knowledge.content_safety import should_wrap

        assert should_wrap("file") is False

    def test_text_returns_false(self) -> None:
        """should_wrap('text') returns False — direct user text is trusted."""
        from owlbear_knowledge.content_safety import should_wrap

        assert should_wrap("text") is False

    def test_file_glob_returns_false(self) -> None:
        """should_wrap('file_glob') returns False — local glob content is trusted."""
        from owlbear_knowledge.content_safety import should_wrap

        assert should_wrap("file_glob") is False

    # ------------------------------------------------------------------
    # AC2 boundary — None backward-compat path
    # ------------------------------------------------------------------

    def test_none_returns_false(self) -> None:
        """should_wrap(None) returns False — backward compat for callers that omit source_type."""
        from owlbear_knowledge.content_safety import should_wrap

        assert should_wrap(None) is False

    def test_empty_string_returns_false(self) -> None:
        """should_wrap('') returns False — empty/missing source_type treated as trusted (falsy guard)."""
        from owlbear_knowledge.content_safety import should_wrap

        assert should_wrap("") is False

    # ------------------------------------------------------------------
    # Return-type guarantee
    # ------------------------------------------------------------------

    def test_return_type_is_bool_for_truthy_input(self) -> None:
        """should_wrap() returns a strict bool, not just a truthy value, for untrusted input."""
        from owlbear_knowledge.content_safety import should_wrap

        result = should_wrap("url_list")
        assert result is True

    def test_return_type_is_bool_for_falsy_input(self) -> None:
        """should_wrap() returns a strict bool, not just a falsy value, for trusted input."""
        from owlbear_knowledge.content_safety import should_wrap

        result = should_wrap("file")
        assert result is False
