"""Tests for _sanitize_agent_strings — LLM encoding normalization at MCP boundary.

Verifies that common LLM mistakes (e.g. passing '""' when meaning empty string)
are normalized before reaching the kanban engine, preventing unintended side
effects like blocking a task when trying to clear block_reason.
"""

from __future__ import annotations

from owlbear_mcp_kanban.server import _sanitize_agent_strings


class TestSanitizeAgentStrings:
    """Unit tests for _sanitize_agent_strings helper."""

    def test_double_quotes_normalized_to_empty(self) -> None:
        kwargs: dict[str, object] = {"block_reason": '""'}
        _sanitize_agent_strings(kwargs)
        assert kwargs["block_reason"] == ""

    def test_single_quotes_normalized_to_empty(self) -> None:
        kwargs: dict[str, object] = {"block_reason": "''"}
        _sanitize_agent_strings(kwargs)
        assert kwargs["block_reason"] == ""

    def test_legitimate_string_unchanged(self) -> None:
        kwargs: dict[str, object] = {"block_reason": "waiting on infra"}
        _sanitize_agent_strings(kwargs)
        assert kwargs["block_reason"] == "waiting on infra"

    def test_empty_string_unchanged(self) -> None:
        kwargs: dict[str, object] = {"block_reason": ""}
        _sanitize_agent_strings(kwargs)
        assert kwargs["block_reason"] == ""

    def test_non_string_values_ignored(self) -> None:
        kwargs: dict[str, object] = {"parent": 42, "tags": ["a", "b"], "ac": None}
        _sanitize_agent_strings(kwargs)
        assert kwargs == {"parent": 42, "tags": ["a", "b"], "ac": None}

    def test_multiple_fields_normalized(self) -> None:
        kwargs: dict[str, object] = {
            "title": "real title",
            "block_reason": '""',
            "archival_reason": "''",
            "body": "real body",
        }
        _sanitize_agent_strings(kwargs)
        assert kwargs["title"] == "real title"
        assert kwargs["block_reason"] == ""
        assert kwargs["archival_reason"] == ""
        assert kwargs["body"] == "real body"

    def test_string_with_surrounding_quotes_not_stripped(self) -> None:
        """A string like '"reason"' (quotes around content) should NOT be stripped."""
        kwargs: dict[str, object] = {"block_reason": '"waiting on decision"'}
        _sanitize_agent_strings(kwargs)
        assert kwargs["block_reason"] == '"waiting on decision"'

    def test_whitespace_only_not_modified(self) -> None:
        """Whitespace-only is not in scope — only exact '""' and \"''\"."""
        kwargs: dict[str, object] = {"block_reason": "   "}
        _sanitize_agent_strings(kwargs)
        assert kwargs["block_reason"] == "   "
