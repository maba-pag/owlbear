"""Tests for task #1654: Expose source health fields in list_sources MCP tool.

TDD RED phase — SourceInfo TypedDict has only 4 fields; list_sources response
dict does not include the 5 new health fields. All tests fail until the builder
implements the changes.

AC coverage:
  AC-1: SourceInfo TypedDict includes last_refreshed_at: str | None,
        last_checked_at: str | None, last_error: str | None, enabled: bool,
        fetch_method: str keys with correct types.
  AC-2: list_sources response dict maps the 5 new fields from the corresponding
        KnowledgeSource model attributes for each source returned.
"""

from __future__ import annotations

import typing
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_knowledge.server import SourceInfo, list_sources, mcp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(source_store: object = None) -> MagicMock:
    """Return a minimal FastMCP Context mock with source_store in lifespan_context."""
    ctx = MagicMock()
    app_ctx = MagicMock()
    app_ctx.source_store = source_store
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_source(  # noqa: PLR0913
    *,
    source_id: str = "src-id",
    name: str = "my-source",
    source_type: str = "url_list",
    scope: str = "global",
    last_refreshed_at: str | None = None,
    last_checked_at: str | None = None,
    last_error: str | None = None,
    enabled: bool = True,
    fetch_method: str = "",
) -> MagicMock:
    """Return a mock KnowledgeSource with all required attributes."""
    src = MagicMock()
    src.id = source_id
    src.name = name
    src.source_type = source_type
    src.scope = scope
    src.last_refreshed_at = last_refreshed_at
    src.last_checked_at = last_checked_at
    src.last_error = last_error
    src.enabled = enabled
    src.fetch_method = fetch_method
    return src


def _get_output_schema(tool_name: str) -> dict | None:
    """Return fn_metadata.output_schema for the named tool, or None if not found."""
    if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
        for t in mcp._tool_manager._tools.values():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(getattr(t, "fn_metadata", None), "output_schema", None)
    return None


# ---------------------------------------------------------------------------
# TestFromAC_SourceInfoShape
# AC-1: SourceInfo TypedDict must declare 5 new health annotation keys
# ---------------------------------------------------------------------------


class TestFromAC_SourceInfoShape:
    """AC-1: SourceInfo TypedDict must include 5 new health keys with correct types."""

    # Use get_type_hints to evaluate lazy string annotations (from __future__ import annotations)

    def test_source_info_has_last_refreshed_at(self) -> None:
        """SourceInfo must declare 'last_refreshed_at' annotation."""
        hints = typing.get_type_hints(SourceInfo)
        assert "last_refreshed_at" in hints, f"SourceInfo missing 'last_refreshed_at'; declared keys: {list(hints)}"

    def test_source_info_last_refreshed_at_is_optional_str(self) -> None:
        """SourceInfo.last_refreshed_at must be str | None."""
        hints = typing.get_type_hints(SourceInfo)
        ann = hints["last_refreshed_at"]
        args = typing.get_args(ann)
        assert str in args, f"SourceInfo.last_refreshed_at expected str in union, got: {ann!r}"
        assert type(None) in args, f"SourceInfo.last_refreshed_at expected None in union, got: {ann!r}"

    def test_source_info_has_last_checked_at(self) -> None:
        """SourceInfo must declare 'last_checked_at' annotation."""
        hints = typing.get_type_hints(SourceInfo)
        assert "last_checked_at" in hints, f"SourceInfo missing 'last_checked_at'; declared keys: {list(hints)}"

    def test_source_info_last_checked_at_is_optional_str(self) -> None:
        """SourceInfo.last_checked_at must be str | None."""
        hints = typing.get_type_hints(SourceInfo)
        ann = hints["last_checked_at"]
        args = typing.get_args(ann)
        assert str in args, f"SourceInfo.last_checked_at expected str in union, got: {ann!r}"
        assert type(None) in args, f"SourceInfo.last_checked_at expected None in union, got: {ann!r}"

    def test_source_info_has_last_error(self) -> None:
        """SourceInfo must declare 'last_error' annotation."""
        hints = typing.get_type_hints(SourceInfo)
        assert "last_error" in hints, f"SourceInfo missing 'last_error'; declared keys: {list(hints)}"

    def test_source_info_last_error_is_optional_str(self) -> None:
        """SourceInfo.last_error must be str | None."""
        hints = typing.get_type_hints(SourceInfo)
        ann = hints["last_error"]
        args = typing.get_args(ann)
        assert str in args, f"SourceInfo.last_error expected str in union, got: {ann!r}"
        assert type(None) in args, f"SourceInfo.last_error expected None in union, got: {ann!r}"

    def test_source_info_has_enabled(self) -> None:
        """SourceInfo must declare 'enabled' annotation."""
        hints = typing.get_type_hints(SourceInfo)
        assert "enabled" in hints, f"SourceInfo missing 'enabled'; declared keys: {list(hints)}"

    def test_source_info_enabled_is_bool(self) -> None:
        """SourceInfo.enabled must be bool."""
        hints = typing.get_type_hints(SourceInfo)
        ann = hints["enabled"]
        assert ann is bool, f"SourceInfo.enabled expected 'bool', got: {ann!r}"

    def test_source_info_has_fetch_method(self) -> None:
        """SourceInfo must declare 'fetch_method' annotation."""
        hints = typing.get_type_hints(SourceInfo)
        assert "fetch_method" in hints, f"SourceInfo missing 'fetch_method'; declared keys: {list(hints)}"

    def test_source_info_fetch_method_is_str(self) -> None:
        """SourceInfo.fetch_method must be str."""
        hints = typing.get_type_hints(SourceInfo)
        ann = hints["fetch_method"]
        assert ann is str, f"SourceInfo.fetch_method expected 'str', got: {ann!r}"


# ---------------------------------------------------------------------------
# TestFromAC_SourceInfoOutputSchema
# AC-1: list_sources output_schema must expose 5 new fields in SourceInfo $defs
# ---------------------------------------------------------------------------


class TestFromAC_SourceInfoOutputSchema:
    """AC-1: output schema for list_sources must include 5 new fields in SourceInfo."""

    def test_schema_source_info_has_last_refreshed_at(self) -> None:
        """SourceInfo in $defs must include 'last_refreshed_at' property."""
        schema = _get_output_schema("list_sources")
        assert schema is not None, "list_sources tool or fn_metadata not found"
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "last_refreshed_at" in props, f"SourceInfo schema missing 'last_refreshed_at'; found: {list(props)}"

    def test_schema_source_info_has_last_checked_at(self) -> None:
        """SourceInfo in $defs must include 'last_checked_at' property."""
        schema = _get_output_schema("list_sources")
        assert schema is not None, "list_sources tool not found"
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "last_checked_at" in props, f"SourceInfo schema missing 'last_checked_at'; found: {list(props)}"

    def test_schema_source_info_has_last_error(self) -> None:
        """SourceInfo in $defs must include 'last_error' property."""
        schema = _get_output_schema("list_sources")
        assert schema is not None, "list_sources tool not found"
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "last_error" in props, f"SourceInfo schema missing 'last_error'; found: {list(props)}"

    def test_schema_source_info_has_enabled(self) -> None:
        """SourceInfo in $defs must include 'enabled' property."""
        schema = _get_output_schema("list_sources")
        assert schema is not None, "list_sources tool not found"
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "enabled" in props, f"SourceInfo schema missing 'enabled'; found: {list(props)}"

    def test_schema_source_info_enabled_is_boolean_type(self) -> None:
        """SourceInfo.enabled in schema must have type=boolean."""
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        enabled_schema = props.get("enabled", {})
        assert enabled_schema.get("type") == "boolean", (
            f"SourceInfo.enabled type expected 'boolean', got: {enabled_schema.get('type')!r}"
        )

    def test_schema_source_info_has_fetch_method(self) -> None:
        """SourceInfo in $defs must include 'fetch_method' property."""
        schema = _get_output_schema("list_sources")
        assert schema is not None, "list_sources tool not found"
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "fetch_method" in props, f"SourceInfo schema missing 'fetch_method'; found: {list(props)}"

    def test_schema_source_info_fetch_method_is_string_type(self) -> None:
        """SourceInfo.fetch_method in schema must have type=string."""
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        fetch_schema = props.get("fetch_method", {})
        assert fetch_schema.get("type") == "string", (
            f"SourceInfo.fetch_method type expected 'string', got: {fetch_schema.get('type')!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ListSourcesHealthMapping
# AC-2: list_sources response dict maps 5 new fields from KnowledgeSource attributes
# ---------------------------------------------------------------------------


class TestFromAC_ListSourcesHealthMapping:
    """AC-2: list_sources response dict must map the 5 new health fields per source."""

    @pytest.mark.asyncio
    async def test_response_includes_last_refreshed_at_with_value(self) -> None:
        """Response dict includes 'last_refreshed_at' mapped from source attribute."""
        source = _make_source(last_refreshed_at="2026-05-01T12:00:00Z")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "last_refreshed_at" in result[0], "Response dict missing 'last_refreshed_at'"
        assert result[0]["last_refreshed_at"] == "2026-05-01T12:00:00Z"

    @pytest.mark.asyncio
    async def test_response_last_refreshed_at_is_none_when_unset(self) -> None:
        """Response dict has 'last_refreshed_at'=None when source attribute is None."""
        source = _make_source(last_refreshed_at=None)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "last_refreshed_at" in result[0], "Response dict missing 'last_refreshed_at'"
        assert result[0]["last_refreshed_at"] is None

    @pytest.mark.asyncio
    async def test_response_includes_last_checked_at_with_value(self) -> None:
        """Response dict includes 'last_checked_at' mapped from source attribute."""
        source = _make_source(last_checked_at="2026-05-02T08:00:00Z")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "last_checked_at" in result[0], "Response dict missing 'last_checked_at'"
        assert result[0]["last_checked_at"] == "2026-05-02T08:00:00Z"

    @pytest.mark.asyncio
    async def test_response_last_checked_at_is_none_when_unset(self) -> None:
        """Response dict has 'last_checked_at'=None when source attribute is None."""
        source = _make_source(last_checked_at=None)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "last_checked_at" in result[0], "Response dict missing 'last_checked_at'"
        assert result[0]["last_checked_at"] is None

    @pytest.mark.asyncio
    async def test_response_includes_last_error_with_value(self) -> None:
        """Response dict includes 'last_error' mapped from source attribute."""
        source = _make_source(last_error="Connection refused")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "last_error" in result[0], "Response dict missing 'last_error'"
        assert result[0]["last_error"] == "Connection refused"

    @pytest.mark.asyncio
    async def test_response_last_error_is_none_when_no_error(self) -> None:
        """Response dict has 'last_error'=None when source has no error."""
        source = _make_source(last_error=None)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "last_error" in result[0], "Response dict missing 'last_error'"
        assert result[0]["last_error"] is None

    @pytest.mark.asyncio
    async def test_response_includes_enabled_true(self) -> None:
        """Response dict includes 'enabled'=True from enabled source."""
        source = _make_source(enabled=True)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "enabled" in result[0], "Response dict missing 'enabled'"
        assert result[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_response_includes_enabled_false(self) -> None:
        """Response dict includes 'enabled'=False from disabled source."""
        source = _make_source(enabled=False)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "enabled" in result[0], "Response dict missing 'enabled'"
        assert result[0]["enabled"] is False

    @pytest.mark.asyncio
    async def test_response_includes_fetch_method_with_value(self) -> None:
        """Response dict includes 'fetch_method' mapped from source attribute."""
        source = _make_source(fetch_method="http_get")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "fetch_method" in result[0], "Response dict missing 'fetch_method'"
        assert result[0]["fetch_method"] == "http_get"

    @pytest.mark.asyncio
    async def test_response_fetch_method_empty_string_when_unset(self) -> None:
        """Response dict has 'fetch_method'='' when source has empty fetch_method."""
        source = _make_source(fetch_method="")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "fetch_method" in result[0], "Response dict missing 'fetch_method'"
        assert result[0]["fetch_method"] == ""

    @pytest.mark.asyncio
    async def test_all_five_health_fields_present_in_single_response(self) -> None:
        """Response dict for a source contains all 5 new health fields."""
        source = _make_source(
            last_refreshed_at="2026-01-01T00:00:00Z",
            last_checked_at="2026-01-02T00:00:00Z",
            last_error=None,
            enabled=True,
            fetch_method="rss",
        )
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        item = result[0]
        assert "last_refreshed_at" in item
        assert "last_checked_at" in item
        assert "last_error" in item
        assert "enabled" in item
        assert "fetch_method" in item

    @pytest.mark.asyncio
    async def test_all_five_fields_present_across_multi_source_response(self) -> None:
        """All items in a multi-source response include the 5 new health fields."""
        sources = [
            _make_source(name="s1", enabled=True, fetch_method="http"),
            _make_source(name="s2", enabled=False, last_error="timeout"),
            _make_source(name="s3", last_refreshed_at="2026-03-01T00:00:00Z"),
        ]
        store = MagicMock()
        store.list_all.return_value = sources
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert len(result) == 3
        for item in result:
            assert "last_refreshed_at" in item
            assert "last_checked_at" in item
            assert "last_error" in item
            assert "enabled" in item
            assert "fetch_method" in item

    @pytest.mark.asyncio
    async def test_health_field_values_match_source_attributes_exactly(self) -> None:
        """All 5 health field values in response match the source model attributes exactly."""
        source = _make_source(
            last_refreshed_at="2025-12-31T23:59:59Z",
            last_checked_at="2026-01-01T00:00:01Z",
            last_error="HTTP 503",
            enabled=False,
            fetch_method="atom_feed",
        )
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        item = result[0]
        assert item["last_refreshed_at"] == "2025-12-31T23:59:59Z"
        assert item["last_checked_at"] == "2026-01-01T00:00:01Z"
        assert item["last_error"] == "HTTP 503"
        assert item["enabled"] is False
        assert item["fetch_method"] == "atom_feed"
