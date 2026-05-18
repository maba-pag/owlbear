"""Tests for task #1654: Expose source health fields in list_sources MCP tool.

Retry-cycle rewrite: adds AC-3/AC-4 (_sanitize_error) coverage and replaces
raw last_error passthrough assertions with safe-disclosure contract assertions.

AC coverage:
  AC-1: SourceInfo TypedDict includes 5 new health keys (shape + output schema).
  AC-2: list_sources maps all 5 fields; last_error is passed through _sanitize_error.
  AC-3: _sanitize_error returns None for None; extracts first Error/Exception class
        name or HTTP NNN; falls back to "error"; output never exceeds 120 chars.
  AC-4: Canonical input/output pairs as specified by the architect.
"""

from __future__ import annotations

import typing
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_knowledge.server import (
    SourceInfo,
    _sanitize_error,
    list_sources,
    mcp,
)


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

    def test_source_info_has_last_refreshed_at(self) -> None:
        """SourceInfo must declare 'last_refreshed_at' annotation."""
        hints = typing.get_type_hints(SourceInfo)
        assert "last_refreshed_at" in hints, f"SourceInfo missing 'last_refreshed_at'; declared: {list(hints)}"

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
        assert "last_checked_at" in hints, f"SourceInfo missing 'last_checked_at'; declared: {list(hints)}"

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
        assert "last_error" in hints, f"SourceInfo missing 'last_error'; declared: {list(hints)}"

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
        assert "enabled" in hints, f"SourceInfo missing 'enabled'; declared: {list(hints)}"

    def test_source_info_enabled_is_bool(self) -> None:
        """SourceInfo.enabled must be bool."""
        hints = typing.get_type_hints(SourceInfo)
        ann = hints["enabled"]
        assert ann is bool, f"SourceInfo.enabled expected 'bool', got: {ann!r}"

    def test_source_info_has_fetch_method(self) -> None:
        """SourceInfo must declare 'fetch_method' annotation."""
        hints = typing.get_type_hints(SourceInfo)
        assert "fetch_method" in hints, f"SourceInfo missing 'fetch_method'; declared: {list(hints)}"

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
# TestFromAC_SanitizeError
# AC-3/AC-4: module-private _sanitize_error strips sensitive detail from errors
# ---------------------------------------------------------------------------


class TestFromAC_SanitizeError:
    """AC-3/AC-4: _sanitize_error extracts safe error token or returns fixed fallback."""

    # --- Happy path ---

    def test_none_input_returns_none(self) -> None:
        """AC-3: None input must return None."""
        assert _sanitize_error(None) is None

    def test_extracts_error_class_name(self) -> None:
        """AC-3: first [A-Z][a-zA-Z]*(Error|Exception) match is extracted."""
        assert _sanitize_error("ValueError: bad value") == "ValueError"

    def test_extracts_exception_suffix_class(self) -> None:
        """AC-3: class ending in 'Exception' suffix is extracted."""
        assert _sanitize_error("RuntimeException: unexpected state") == "RuntimeException"

    def test_extracts_http_status_code(self) -> None:
        """AC-3: HTTP NNN pattern extracted when error/exception class absent."""
        assert _sanitize_error("HTTP 200 OK received") == "HTTP 200"

    # --- Edge cases ---

    def test_first_error_class_wins_when_multiple_present(self) -> None:
        """AC-3: leftmost Error/Exception match is returned, not subsequent ones."""
        result = _sanitize_error("ConnectionError: refused; TimeoutError: timed out")
        assert result == "ConnectionError"

    def test_http_pattern_returned_when_no_error_class_in_string(self) -> None:
        """AC-3: HTTP NNN matched when no Error/Exception class present."""
        result = _sanitize_error("upstream returned HTTP 429 Too Many Requests")
        assert result == "HTTP 429"

    def test_output_within_120_chars_for_very_long_input(self) -> None:
        """AC-3: output never exceeds 120 characters even for pathological input."""
        long_raw = "ValueError: " + "x" * 300
        result = _sanitize_error(long_raw)
        assert result is not None
        assert len(result) <= 120

    # --- Error paths ---

    def test_no_pattern_match_returns_error_fallback(self) -> None:
        """AC-3: raw string with no pattern match returns the fixed string 'error'."""
        assert _sanitize_error("connection refused") == "error"

    def test_empty_string_returns_error_fallback(self) -> None:
        """AC-3: empty string has no pattern match; returns 'error'."""
        assert _sanitize_error("") == "error"

    # --- Boundary (AC-4 canonical input/output pairs) ---

    def test_ac4_permission_error_with_path(self) -> None:
        """AC-4: PermissionError with path detail -> 'PermissionError' with no path."""
        raw = "PermissionError: [Errno 13] Permission denied: '/home/user/secret.pem'"
        assert _sanitize_error(raw) == "PermissionError"

    def test_ac4_http_503_with_internal_host(self) -> None:
        """AC-4: HTTP 503 with internal hostname -> 'HTTP 503' with no host."""
        raw = "HTTP 503 Service Unavailable from internal.corp:8080"
        assert _sanitize_error(raw) == "HTTP 503"

    def test_ac4_no_pattern_match_returns_error(self) -> None:
        """AC-4: raw without error class or HTTP code -> 'error'."""
        raw = "no files matched source path '/secret/data'"
        assert _sanitize_error(raw) == "error"

    def test_ac4_connection_error_is_first_match(self) -> None:
        """AC-4: ConnectionError returned before later TimeoutError in same string."""
        raw = "ConnectionError: refused; TimeoutError: timed out"
        assert _sanitize_error(raw) == "ConnectionError"


# ---------------------------------------------------------------------------
# TestFromAC_ListSourcesHealthMapping
# AC-2: list_sources response maps all 5 fields; last_error via _sanitize_error
# ---------------------------------------------------------------------------


class TestFromAC_ListSourcesHealthMapping:
    """AC-2: list_sources response dict maps 5 new health fields; last_error sanitized."""

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

        assert "last_refreshed_at" in result[0]
        assert result[0]["last_refreshed_at"] is None

    @pytest.mark.asyncio
    async def test_response_includes_last_checked_at_with_value(self) -> None:
        """Response dict includes 'last_checked_at' mapped from source attribute."""
        source = _make_source(last_checked_at="2026-05-02T08:00:00Z")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "last_checked_at" in result[0]
        assert result[0]["last_checked_at"] == "2026-05-02T08:00:00Z"

    @pytest.mark.asyncio
    async def test_response_last_checked_at_is_none_when_unset(self) -> None:
        """Response dict has 'last_checked_at'=None when source attribute is None."""
        source = _make_source(last_checked_at=None)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "last_checked_at" in result[0]
        assert result[0]["last_checked_at"] is None

    @pytest.mark.asyncio
    async def test_response_last_error_is_none_when_source_has_no_error(self) -> None:
        """AC-2: _sanitize_error(None) -> None; response has last_error=None."""
        source = _make_source(last_error=None)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "last_error" in result[0]
        assert result[0]["last_error"] is None

    @pytest.mark.asyncio
    async def test_response_includes_enabled_true(self) -> None:
        """Response dict includes 'enabled'=True from enabled source."""
        source = _make_source(enabled=True)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "enabled" in result[0]
        assert result[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_response_includes_enabled_false(self) -> None:
        """Response dict includes 'enabled'=False from disabled source."""
        source = _make_source(enabled=False)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "enabled" in result[0]
        assert result[0]["enabled"] is False

    @pytest.mark.asyncio
    async def test_response_includes_fetch_method_with_value(self) -> None:
        """Response dict includes 'fetch_method' mapped from source attribute."""
        source = _make_source(fetch_method="http_get")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "fetch_method" in result[0]
        assert result[0]["fetch_method"] == "http_get"

    @pytest.mark.asyncio
    async def test_response_fetch_method_empty_string_when_unset(self) -> None:
        """Response dict has 'fetch_method'='' when source has empty fetch_method."""
        source = _make_source(fetch_method="")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert "fetch_method" in result[0]
        assert result[0]["fetch_method"] == ""

    @pytest.mark.asyncio
    async def test_all_five_health_fields_present_in_single_response(self) -> None:
        """Response dict for a single source contains all 5 new health fields."""
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
        """All items in a multi-source response include all 5 new health fields."""
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

    # --- Sanitized last_error contract (AC-2: last_error via _sanitize_error) ---

    @pytest.mark.asyncio
    async def test_response_last_error_sanitized_to_error_class(self) -> None:
        """AC-2: raw last_error with PermissionError + path -> 'PermissionError' only."""
        source = _make_source(last_error="PermissionError: [Errno 13] /home/user/secret")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_error"] == "PermissionError"

    @pytest.mark.asyncio
    async def test_response_last_error_sanitized_to_http_status(self) -> None:
        """AC-2: raw last_error with HTTP status + host info -> HTTP NNN only."""
        source = _make_source(last_error="HTTP 404 Not Found from internal.corp/api")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_error"] == "HTTP 404"

    @pytest.mark.asyncio
    async def test_response_last_error_sanitized_to_error_for_no_pattern_match(self) -> None:
        """AC-2: raw last_error with no error class or HTTP code -> 'error'."""
        source = _make_source(last_error="connection refused")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_error"] == "error"

    @pytest.mark.asyncio
    async def test_response_last_error_does_not_leak_path_details(self) -> None:
        """AC-2: sanitized last_error must not contain path separators from raw value."""
        raw_with_path = "PermissionError: [Errno 13] '/home/user/secret.pem'"
        source = _make_source(last_error=raw_with_path)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        error_val = result[0]["last_error"]
        assert error_val is not None
        assert "/" not in error_val, f"Path detail leaked into last_error: {error_val!r}"

    @pytest.mark.asyncio
    async def test_health_field_values_match_sanitized_contract(self) -> None:
        """AC-2: all 5 health field values correct; last_error is sanitized output."""
        source = _make_source(
            last_refreshed_at="2025-12-31T23:59:59Z",
            last_checked_at="2026-01-01T00:00:01Z",
            last_error="PermissionError: [Errno 13] /secret/data",
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
        assert item["last_error"] == "PermissionError"  # sanitized, not raw
        assert item["enabled"] is False
        assert item["fetch_method"] == "atom_feed"
