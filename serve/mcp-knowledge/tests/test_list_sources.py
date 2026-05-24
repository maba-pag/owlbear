"""Durable tests for the list_sources MCP tool in owlbear_mcp_knowledge.server."""

from __future__ import annotations

import typing
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_knowledge.server import (  # type: ignore[import]
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


def _make_source(
    name: str = "my-source",
    source_type: str = "url_list",
    scope: str = "global",
    **overrides: object,
) -> MagicMock:
    src = MagicMock()
    src.id = f"id-{name}"
    src.name = name
    src.source_type = source_type
    src.scope = scope
    src.last_refreshed_at = overrides.get("last_refreshed_at")
    src.last_checked_at = overrides.get("last_checked_at")
    src.last_error = overrides.get("last_error")
    src.enabled = overrides.get("enabled", True)
    src.refreshable = True
    src.enrich = True
    src.fetch_method = overrides.get("fetch_method", "http")
    return src


def _get_output_schema(tool_name: str) -> dict | None:
    """Return fn_metadata.output_schema for the named tool when available."""
    if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
        for tool in mcp._tool_manager._tools.values():  # noqa: SLF001
            if getattr(tool, "name", None) == tool_name:
                metadata = getattr(tool, "fn_metadata", None)
                return getattr(metadata, "output_schema", None)
    return None


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestFromAC_ListSources:
    """Contract tests for list_sources MCP tool."""

    # ------------------------------------------------------------------
    # AC: returns formatted bullet list "- {name} ({source_type}): scope={scope}"
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_returns_formatted_bullet_list(self) -> None:
        """list_sources returns a list of dicts with name, source_type, and scope."""
        source = _make_source(name="src-one", source_type="url_list", scope="work")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert isinstance(result, list)
        assert result[0]["name"] == "src-one"
        assert result[0]["source_type"] == "url_list"
        assert result[0]["scope"] == "work"

    # ------------------------------------------------------------------
    # AC: scope filter passes scope to list_all(scope=scope)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_with_scope_filter_passes_scope_to_list_all(self) -> None:
        """list_sources(scope='work') calls store.list_all(scope='work')."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        await list_sources(ctx, scope="work")

        store.list_all.assert_called_once_with(scope="work")

    # ------------------------------------------------------------------
    # AC: without scope passes None to list_all
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_without_scope_passes_none_to_list_all(self) -> None:
        """list_sources() without scope calls store.list_all with scope=None."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        await list_sources(ctx)

        store.list_all.assert_called_once_with(scope=None)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("null_scope", [None, "", "null", "None", " NULL "])
    async def test_null_like_scope_passes_none_to_list_all(self, null_scope: str | None) -> None:
        """Explicit null-like MCP scope values behave the same as omission."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        await list_sources(ctx, scope=null_scope)

        store.list_all.assert_called_once_with(scope=None)

    # ------------------------------------------------------------------
    # AC: empty result returns "No sources found."
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self) -> None:
        """list_sources returns [] when list_all returns []."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result == []

    # ------------------------------------------------------------------
    # AC: calls list_all directly on the owning SQLite thread
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_calls_list_all_directly(self) -> None:
        """list_sources calls list_all on the same thread that owns the SQLite connection."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        await list_sources(ctx)

        store.list_all.assert_called_once_with(scope=None)


# ---------------------------------------------------------------------------
# TestFromAC_ListSourcesStructuredReturn (#507)
# ---------------------------------------------------------------------------


class TestFromAC_ListSourcesStructuredReturn:
    """Contract tests: list_sources returns list[dict] on success, [] on empty."""

    # ------------------------------------------------------------------
    # AC: success returns list not str
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_success_returns_list(self) -> None:
        """list_sources returns a list (not str) when sources exist."""
        source = _make_source(name="s1", source_type="url_list", scope="global")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_success_result_items_are_dicts(self) -> None:
        """Each item in the returned list is a dict."""
        store = MagicMock()
        store.list_all.return_value = [_make_source(), _make_source(name="s2")]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert all(isinstance(item, dict) for item in result)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_each_dict_has_name_source_type_scope_keys(self) -> None:
        """Each dict in the returned list has 'name', 'source_type', and 'scope' keys."""
        store = MagicMock()
        store.list_all.return_value = [_make_source(name="n", source_type="url_list", scope="work")]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        item = result[0]  # type: ignore[index]
        assert "name" in item
        assert "source_type" in item
        assert "scope" in item

    @pytest.mark.asyncio
    async def test_dict_values_match_source_fields(self) -> None:
        """name, source_type, scope values come from the source object fields."""
        store = MagicMock()
        store.list_all.return_value = [_make_source(name="my-src", source_type="file_glob", scope="work")]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        item = result[0]  # type: ignore[index]
        assert item["name"] == "my-src"
        assert item["source_type"] == "file_glob"
        assert item["scope"] == "work"

    @pytest.mark.asyncio
    async def test_all_fields_are_str(self) -> None:
        """name, source_type, and scope are all str values."""
        store = MagicMock()
        store.list_all.return_value = [_make_source()]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        item = result[0]  # type: ignore[index]
        assert isinstance(item["name"], str)
        assert isinstance(item["source_type"], str)
        assert isinstance(item["scope"], str)

    @pytest.mark.asyncio
    async def test_multiple_sources_list_length_matches(self) -> None:
        """List length equals the number of sources returned by list_all."""
        store = MagicMock()
        store.list_all.return_value = [
            _make_source(name="a"),
            _make_source(name="b"),
            _make_source(name="c"),
        ]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert len(result) == 3  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # AC: empty results return [] not a string message
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self) -> None:
        """list_sources returns [] (not 'No sources found.') when list_all returns []."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_result_is_list_not_str(self) -> None:
        """Empty result is a list type, confirming no string sentinel is returned."""
        store = MagicMock()
        store.list_all.return_value = []
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert isinstance(result, list)


# From task #1654: health-field schema and sanitization coverage for list_sources.


class TestSourceInfoShape:
    """SourceInfo TypedDict exposes the list_sources health fields."""

    def test_source_info_has_last_refreshed_at(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        assert "last_refreshed_at" in hints

    def test_source_info_last_refreshed_at_is_optional_str(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        args = typing.get_args(hints["last_refreshed_at"])
        assert str in args
        assert type(None) in args

    def test_source_info_has_last_checked_at(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        assert "last_checked_at" in hints

    def test_source_info_last_checked_at_is_optional_str(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        args = typing.get_args(hints["last_checked_at"])
        assert str in args
        assert type(None) in args

    def test_source_info_has_last_error(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        assert "last_error" in hints

    def test_source_info_last_error_is_optional_str(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        args = typing.get_args(hints["last_error"])
        assert str in args
        assert type(None) in args

    def test_source_info_has_enabled(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        assert "enabled" in hints

    def test_source_info_enabled_is_bool(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        assert hints["enabled"] is bool

    def test_source_info_has_fetch_method(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        assert "fetch_method" in hints

    def test_source_info_fetch_method_is_str(self) -> None:
        hints = typing.get_type_hints(SourceInfo)
        assert hints["fetch_method"] is str


class TestListSourcesOutputSchema:
    """The MCP output schema advertises the health fields on SourceInfo."""

    def test_schema_source_info_has_last_refreshed_at(self) -> None:
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "last_refreshed_at" in props

    def test_schema_source_info_has_last_checked_at(self) -> None:
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "last_checked_at" in props

    def test_schema_source_info_has_last_error(self) -> None:
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "last_error" in props

    def test_schema_source_info_has_enabled(self) -> None:
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "enabled" in props

    def test_schema_source_info_enabled_is_boolean_type(self) -> None:
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert props.get("enabled", {}).get("type") == "boolean"

    def test_schema_source_info_has_fetch_method(self) -> None:
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert "fetch_method" in props

    def test_schema_source_info_fetch_method_is_string_type(self) -> None:
        schema = _get_output_schema("list_sources")
        assert schema is not None
        props = schema.get("$defs", {}).get("SourceInfo", {}).get("properties", {})
        assert props.get("fetch_method", {}).get("type") == "string"


class TestSanitizeError:
    """_sanitize_error exposes only safe, stable error summaries."""

    def test_none_input_returns_none(self) -> None:
        assert _sanitize_error(None) is None

    def test_extracts_error_class_name(self) -> None:
        assert _sanitize_error("ValueError: bad value") == "ValueError"

    def test_extracts_exception_suffix_class(self) -> None:
        assert _sanitize_error("RuntimeException: unexpected state") == "RuntimeException"

    def test_extracts_http_status_code(self) -> None:
        assert _sanitize_error("HTTP 200 OK received") == "HTTP 200"

    def test_first_error_class_wins_when_multiple_present(self) -> None:
        raw = "ConnectionError: refused; TimeoutError: timed out"
        assert _sanitize_error(raw) == "ConnectionError"

    def test_http_pattern_returned_when_no_error_class_in_string(self) -> None:
        raw = "upstream returned HTTP 429 Too Many Requests"
        assert _sanitize_error(raw) == "HTTP 429"

    def test_output_within_120_chars_for_very_long_input(self) -> None:
        result = _sanitize_error("ValueError: " + "x" * 300)
        assert result is not None
        assert len(result) <= 120

    def test_no_pattern_match_returns_error_fallback(self) -> None:
        assert _sanitize_error("connection refused") == "error"

    def test_empty_string_returns_error_fallback(self) -> None:
        assert _sanitize_error("") == "error"

    def test_permission_error_with_path_returns_token_only(self) -> None:
        raw = "PermissionError: [Errno 13] Permission denied: '/home/user/secret.pem'"
        assert _sanitize_error(raw) == "PermissionError"

    def test_http_503_with_internal_host_returns_status_only(self) -> None:
        raw = "HTTP 503 Service Unavailable from internal.corp:8080"
        assert _sanitize_error(raw) == "HTTP 503"

    def test_no_pattern_match_returns_error(self) -> None:
        raw = "no files matched source path '/secret/data'"
        assert _sanitize_error(raw) == "error"

    def test_path_preceded_error_token_returns_fallback(self) -> None:
        raw = "no files matched source path '/secret/TimeoutError'"
        assert _sanitize_error(raw) == "error"

    def test_backslash_preceded_error_token_returns_fallback(self) -> None:
        raw = r"no files matched source path '\\secret\\TimeoutError'"
        assert _sanitize_error(raw) == "error"

    def test_long_error_token_truncated_to_120_chars(self) -> None:
        raw = "V" + "a" * 119 + "Error: x"
        result = _sanitize_error(raw)
        assert result == "V" + "a" * 119
        assert len(result) == 120

    def test_reject_and_continue_returns_later_valid_token(self) -> None:
        raw = "path '/opt/TimeoutError' triggered PermissionError"
        assert _sanitize_error(raw) == "PermissionError"


class TestListSourcesHealthMapping:
    """list_sources maps health fields and sanitizes last_error."""

    @pytest.mark.asyncio
    async def test_response_includes_last_refreshed_at_with_value(self) -> None:
        source = _make_source(last_refreshed_at="2026-05-01T12:00:00Z")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_refreshed_at"] == "2026-05-01T12:00:00Z"

    @pytest.mark.asyncio
    async def test_response_last_refreshed_at_is_none_when_unset(self) -> None:
        source = _make_source(last_refreshed_at=None)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_refreshed_at"] is None

    @pytest.mark.asyncio
    async def test_response_includes_last_checked_at_with_value(self) -> None:
        source = _make_source(last_checked_at="2026-05-02T08:00:00Z")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_checked_at"] == "2026-05-02T08:00:00Z"

    @pytest.mark.asyncio
    async def test_response_last_checked_at_is_none_when_unset(self) -> None:
        source = _make_source(last_checked_at=None)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_checked_at"] is None

    @pytest.mark.asyncio
    async def test_response_last_error_is_none_when_source_has_no_error(self) -> None:
        source = _make_source(last_error=None)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_error"] is None

    @pytest.mark.asyncio
    async def test_response_includes_enabled_true(self) -> None:
        source = _make_source(enabled=True)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_response_includes_enabled_false(self) -> None:
        source = _make_source(enabled=False)
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["enabled"] is False

    @pytest.mark.asyncio
    async def test_response_includes_fetch_method_with_value(self) -> None:
        source = _make_source(fetch_method="http_get")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["fetch_method"] == "http_get"

    @pytest.mark.asyncio
    async def test_response_fetch_method_empty_string_when_unset(self) -> None:
        source = _make_source(fetch_method="")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["fetch_method"] == ""

    @pytest.mark.asyncio
    async def test_all_five_health_fields_present_in_single_response(self) -> None:
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
    async def test_response_last_error_sanitized_to_error_class(self) -> None:
        source = _make_source(last_error="PermissionError: [Errno 13] /home/user/secret")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_error"] == "PermissionError"

    @pytest.mark.asyncio
    async def test_response_last_error_sanitized_to_http_status(self) -> None:
        source = _make_source(last_error="HTTP 404 Not Found from internal.corp/api")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_error"] == "HTTP 404"

    @pytest.mark.asyncio
    async def test_response_last_error_sanitized_to_error_for_no_pattern_match(self) -> None:
        source = _make_source(last_error="connection refused")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_error"] == "error"

    @pytest.mark.asyncio
    async def test_response_last_error_does_not_leak_path_details(self) -> None:
        source = _make_source(last_error="PermissionError: [Errno 13] '/home/user/secret.pem'")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        error_val = result[0]["last_error"]
        assert error_val is not None
        assert "/" not in error_val

    @pytest.mark.asyncio
    async def test_health_field_values_match_sanitized_contract(self) -> None:
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
        assert item["last_error"] == "PermissionError"
        assert item["enabled"] is False
        assert item["fetch_method"] == "atom_feed"

    @pytest.mark.asyncio
    async def test_response_last_error_path_preceded_token_sanitized_to_fallback(self) -> None:
        source = _make_source(last_error="no files matched source path '/secret/TimeoutError'")
        store = MagicMock()
        store.list_all.return_value = [source]
        ctx = _make_ctx(source_store=store)

        result = await list_sources(ctx)

        assert result[0]["last_error"] == "error"
