"""Tests for ToolStats TypedDict — AC contract for task #531."""

from __future__ import annotations

import typing

from owlbear.core.observability import EventStore, ToolStats


class TestFromAC_ToolStatsTypedDict:  # noqa: N801
    """ToolStats TypedDict exists with the correct shape (AC1)."""

    def test_importable(self) -> None:
        """ToolStats can be imported from owlbear.core.observability."""
        assert ToolStats is not None

    def test_is_typed_dict(self) -> None:
        """ToolStats is a TypedDict (dict subclass with __annotations__)."""
        assert issubclass(ToolStats, dict)
        assert hasattr(ToolStats, "__annotations__")

    def test_has_call_count_int(self) -> None:
        """ToolStats declares call_count: int."""
        hints = typing.get_type_hints(ToolStats)
        assert hints.get("call_count") is int

    def test_has_error_count_int(self) -> None:
        """ToolStats declares error_count: int."""
        hints = typing.get_type_hints(ToolStats)
        assert hints.get("error_count") is int

    def test_has_avg_duration_ms_float(self) -> None:
        """ToolStats declares avg_duration_ms: float."""
        hints = typing.get_type_hints(ToolStats)
        assert hints.get("avg_duration_ms") is float

    def test_exactly_three_keys(self) -> None:
        """ToolStats has exactly 3 keys — no extras."""
        hints = typing.get_type_hints(ToolStats)
        assert len(hints) == 3


class TestFromAC_ToolStatsReturnAnnotation:  # noqa: N801
    """tool_stats() return type references ToolStats (AC2)."""

    def test_return_annotation_is_dict_str_toolstats(self) -> None:
        """EventStore.tool_stats() return hint is dict[str, ToolStats]."""
        hints = typing.get_type_hints(EventStore.tool_stats)
        ret = hints["return"]
        assert typing.get_origin(ret) is dict
        assert typing.get_args(ret) == (str, ToolStats)
