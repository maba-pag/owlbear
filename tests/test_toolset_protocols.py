"""Tests for owlbear.tools.protocols — unwrap() and find_toolset() utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

from pydantic_ai.toolsets.wrapper import WrapperToolset

from owlbear.tools.protocols import find_toolset, unwrap

# ---------------------------------------------------------------------------
# Helpers — lightweight stubs
# ---------------------------------------------------------------------------


class _PlainToolset:
    """Minimal non-wrapper toolset stub."""

    async def tool_defs(self) -> list[Any]:
        return []


@dataclass
class _FakeWrapper(WrapperToolset):  # type: ignore[type-arg]
    """Minimal WrapperToolset for testing."""


# ---------------------------------------------------------------------------
# unwrap()
# ---------------------------------------------------------------------------


class TestUnwrap:
    """Unit tests for unwrap() — peels WrapperToolset layers."""

    def test_plain_toolset_returned_as_is(self) -> None:
        """A non-wrapper toolset is returned unchanged."""
        plain = _PlainToolset()
        assert unwrap(plain) is plain

    def test_single_wrapper_peeled(self) -> None:
        """A single WrapperToolset layer is peeled off."""
        plain = _PlainToolset()
        wrapper = _FakeWrapper(wrapped=plain)
        assert unwrap(wrapper) is plain

    def test_nested_wrappers_fully_peeled(self) -> None:
        """Multiple WrapperToolset layers are all peeled off."""
        plain = _PlainToolset()
        w1 = _FakeWrapper(wrapped=plain)
        w2 = _FakeWrapper(wrapped=w1)
        w3 = _FakeWrapper(wrapped=w2)
        assert unwrap(w3) is plain


# ---------------------------------------------------------------------------
# find_toolset()
# ---------------------------------------------------------------------------


class TestFindToolset:
    """Unit tests for find_toolset() — finds toolset by type through wrappers."""

    def test_match_plain(self) -> None:
        """Finds a matching toolset in a plain (unwrapped) list."""
        plain = _PlainToolset()
        result = find_toolset([plain], _PlainToolset)
        assert result is plain

    def test_no_match_returns_none(self) -> None:
        """Returns None when no match is found."""
        mock_ts = MagicMock()
        result = find_toolset([mock_ts], _PlainToolset)
        assert result is None

    def test_match_through_wrappers(self) -> None:
        """Finds a matching toolset after unwrapping layers."""
        plain = _PlainToolset()
        w1 = _FakeWrapper(wrapped=plain)
        w2 = _FakeWrapper(wrapped=w1)
        result = find_toolset([w2], _PlainToolset)
        assert result is plain

    def test_first_match_returned(self) -> None:
        """Returns the first matching toolset when multiple exist."""
        p1 = _PlainToolset()
        p2 = _PlainToolset()
        result = find_toolset([p1, p2], _PlainToolset)
        assert result is p1
