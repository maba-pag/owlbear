"""Tests for knowledge_register_source MCP tool (task #1890).

Source files under test:
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py

Target interface:
  knowledge_register_source — new MCP tool that accepts registration params,
  validates them as a SourceRegistration (Pydantic, strict=False at boundary),
  delegates to SqliteSourceStore.register_source(), and returns a serialized
  dict with (id, name, state, kind, scope).

AC coverage:
  AC1 — knowledge_register_source registered with readOnlyHint=False, destructiveHint=False
  AC2 — Pydantic validation errors returned as MCP ToolError with detail
  AC3 — SourceRegistration constructed from params, passed to SqliteSourceStore.register_source
  AC4 — Returns serialized SourceRecord (id, name, state, kind, scope)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.protocols.sources import (
    FetchTransport,
    SourceKind,
    SourceRegistration,
)
from owlbear_mcp_knowledge.server import knowledge_sources_register as knowledge_register_source, mcp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations object for a named mcp-knowledge tool, or None."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


def _make_source_record(
    source_id: str = "src-1890",
    name: str = "test-source-1890",
    scope: str = "global",
    kind: str = "inline",
    state: str = "active",
) -> MagicMock:
    """Minimal mock ConfiguredSourceRecord for return-value tests."""
    record = MagicMock()
    record.id = source_id
    record.name = name
    record.scope = scope
    record.kind = kind
    record.state = state
    return record


def _make_ctx(
    *,
    source_record: MagicMock | None = None,
    store_is_none: bool = False,
) -> MagicMock:
    """Return a mock FastMCP Context whose lifespan_context has source_store_v2 wired."""
    if source_record is None:
        source_record = _make_source_record()

    app_ctx = MagicMock()
    if store_is_none:
        app_ctx.source_store_v2 = None
    else:
        app_ctx.source_store_v2.register_source.return_value = source_record

    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# Minimal valid inline registration payload (all required fields, plain strings).
_INLINE_PAYLOAD = {
    "name": "my-inline-source",
    "kind": "inline",
    "fetch_method": "none",
    "config": {"kind": "inline"},
}


# ---------------------------------------------------------------------------
# TestFromAC_RegisterSourceTool
# ---------------------------------------------------------------------------


class TestFromAC_RegisterSourceTool:
    """AC coverage for knowledge_register_source MCP tool (#1890)."""

    # -- AC1: tool registered with correct ToolAnnotations -------------------

    def test_tool_importable(self) -> None:
        """knowledge_register_source must be importable from the server module."""
        # The import at the top of this file already exercises this;
        # the explicit assert ensures a meaningful failure message.
        assert callable(knowledge_register_source), (
            "knowledge_register_source must be a callable defined in server.py"
        )

    def test_tool_in_mcp_registry(self) -> None:
        """knowledge_register_source must appear in the mcp tool registry."""
        tool_names = {
            getattr(t, "name", None)
            for t in mcp._tool_manager.list_tools()  # noqa: SLF001
        }
        assert "knowledge_register_source" in tool_names, (
            "knowledge_register_source not found in mcp._tool_manager; "
            "register it with @mcp.tool()"
        )

    def test_readonlyhint_is_false(self) -> None:
        """readOnlyHint must be False — the tool writes to the source registry."""
        ann = _get_tool_annotations("knowledge_register_source")
        assert ann is not None, "knowledge_register_source has no ToolAnnotations"
        assert ann.readOnlyHint is False, (  # type: ignore[union-attr]
            "readOnlyHint must be False; register_source writes to the DB"
        )

    def test_destructivehint_is_false(self) -> None:
        """destructiveHint must be False — registration does not delete data."""
        ann = _get_tool_annotations("knowledge_register_source")
        assert ann is not None, "knowledge_register_source has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            "destructiveHint must be False; registration is additive, not destructive"
        )

    # -- AC2: Pydantic validation errors → ToolError --------------------------

    @pytest.mark.asyncio
    async def test_invalid_kind_raises_tool_error(self) -> None:
        """Invalid 'kind' value must raise ToolError, not ValidationError."""
        ctx = _make_ctx()
        with pytest.raises(ToolError):
            await knowledge_register_source(
                ctx,
                name="src",
                kind="not_a_valid_kind",
                fetch_method="none",
                config={"kind": "inline"},
            )

    @pytest.mark.asyncio
    async def test_invalid_fetch_method_raises_tool_error(self) -> None:
        """Invalid 'fetch_method' value must raise ToolError, not ValidationError."""
        ctx = _make_ctx()
        with pytest.raises(ToolError):
            await knowledge_register_source(
                ctx,
                name="src",
                kind="inline",
                fetch_method="not_a_transport",
                config={"kind": "inline"},
            )

    @pytest.mark.asyncio
    async def test_file_glob_config_missing_patterns_raises_tool_error(self) -> None:
        """FileGlobConfig without required 'patterns' field must raise ToolError."""
        ctx = _make_ctx()
        with pytest.raises(ToolError):
            await knowledge_register_source(
                ctx,
                name="src",
                kind="file_glob",
                fetch_method="filesystem",
                config={"kind": "file_glob"},  # patterns is required, missing here
            )

    # -- AC3: SourceRegistration constructed, delegated to store --------------

    @pytest.mark.asyncio
    async def test_delegates_to_source_store_v2_register_source(self) -> None:
        """Happy path: store.register_source must be called exactly once."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name=_INLINE_PAYLOAD["name"],
            kind=_INLINE_PAYLOAD["kind"],
            fetch_method=_INLINE_PAYLOAD["fetch_method"],
            config=_INLINE_PAYLOAD["config"],
        )

        app_ctx.source_store_v2.register_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_source_receives_source_registration_instance(self) -> None:
        """The argument passed to register_source must be a SourceRegistration."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name="my-source",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        assert call_args is not None
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert isinstance(registration, SourceRegistration), (
            "register_source must receive a SourceRegistration instance, "
            f"got {type(registration)}"
        )

    @pytest.mark.asyncio
    async def test_registration_name_matches_input(self) -> None:
        """SourceRegistration.name must equal the 'name' parameter."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context
        source_name = "explicit-name-check"

        await knowledge_register_source(
            ctx,
            name=source_name,
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.name == source_name

    @pytest.mark.asyncio
    async def test_registration_kind_coerced_from_string_enum(self) -> None:
        """String 'inline' must be coerced to SourceKind.INLINE via model_validate(strict=False)."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",  # raw string, not SourceKind enum
            fetch_method="none",
            config={"kind": "inline"},
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.kind == SourceKind.INLINE

    @pytest.mark.asyncio
    async def test_registration_fetch_method_coerced_from_string(self) -> None:
        """String 'none' for fetch_method must be coerced to FetchTransport.NONE."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",  # raw string
            config={"kind": "inline"},
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.fetch_method == FetchTransport.NONE

    @pytest.mark.asyncio
    async def test_scope_defaults_to_global(self) -> None:
        """Omitting scope must produce SourceRegistration.scope == 'global'."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.scope == "global"

    @pytest.mark.asyncio
    async def test_non_default_scope_passed_through(self) -> None:
        """Custom scope must be forwarded to SourceRegistration.scope."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
            scope="project-alpha",
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.scope == "project-alpha"

    @pytest.mark.asyncio
    async def test_source_store_v2_none_raises_tool_error(self) -> None:
        """When source_store_v2 is None, a ToolError must be raised before delegation."""
        ctx = _make_ctx(store_is_none=True)
        with pytest.raises(ToolError):
            await knowledge_register_source(
                ctx,
                name="src",
                kind="inline",
                fetch_method="none",
                config={"kind": "inline"},
            )

    # -- AC4: Returns serialized SourceRecord (id, name, state, kind, scope) --

    @pytest.mark.asyncio
    async def test_return_contains_id(self) -> None:
        """Result dict must include 'id' key with the source's ID."""
        record = _make_source_record(source_id="ret-id-1890")
        ctx = _make_ctx(source_record=record)

        result = await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
        )

        assert "id" in result
        assert result["id"] == "ret-id-1890"

    @pytest.mark.asyncio
    async def test_return_contains_name(self) -> None:
        """Result dict must include 'name' key with the source's name."""
        record = _make_source_record(name="named-source-1890")
        ctx = _make_ctx(source_record=record)

        result = await knowledge_register_source(
            ctx,
            name="named-source-1890",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
        )

        assert "name" in result
        assert result["name"] == "named-source-1890"

    @pytest.mark.asyncio
    async def test_return_contains_state(self) -> None:
        """Result dict must include 'state' key."""
        record = _make_source_record(state="active")
        ctx = _make_ctx(source_record=record)

        result = await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
        )

        assert "state" in result
        assert result["state"] == "active"

    @pytest.mark.asyncio
    async def test_return_contains_kind(self) -> None:
        """Result dict must include 'kind' key."""
        record = _make_source_record(kind="inline")
        ctx = _make_ctx(source_record=record)

        result = await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
        )

        assert "kind" in result
        assert result["kind"] == "inline"

    @pytest.mark.asyncio
    async def test_return_contains_scope(self) -> None:
        """Result dict must include 'scope' key."""
        record = _make_source_record(scope="team-scope")
        ctx = _make_ctx(source_record=record)

        result = await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
            scope="team-scope",
        )

        assert "scope" in result
        assert result["scope"] == "team-scope"

    @pytest.mark.asyncio
    async def test_return_has_exactly_five_keys(self) -> None:
        """Serialized result must contain exactly (id, name, state, kind, scope)."""
        ctx = _make_ctx()

        result = await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
        )

        assert set(result.keys()) == {"id", "name", "state", "kind", "scope"}, (
            f"Expected exactly {{id, name, state, kind, scope}}, got {set(result.keys())}"
        )

    # -- AC2/AC3: store ValueError must be normalized to ToolError (retry, finding #1) ----

    @pytest.mark.asyncio
    async def test_store_valueerror_converted_to_tool_error(self) -> None:
        """When register_source raises ValueError, tool must raise ToolError (not let it propagate)."""
        ctx = _make_ctx()
        ctx.request_context.lifespan_context.source_store_v2.register_source.side_effect = ValueError(
            "kind does not match config kind"
        )
        with pytest.raises(ToolError):
            await knowledge_register_source(
                ctx,
                name="src",
                kind="inline",
                fetch_method="none",
                config={"kind": "inline"},
            )

    @pytest.mark.asyncio
    async def test_kind_config_mismatch_raises_tool_error(self) -> None:
        """Payload with kind=inline but config.kind=url_list must raise ToolError, not ValueError.

        This is a Pydantic-valid SourceRegistration (both fields independently valid) that is
        rejected by the real store. The MCP layer must normalize the ValueError to ToolError.
        """
        ctx = _make_ctx()
        ctx.request_context.lifespan_context.source_store_v2.register_source.side_effect = ValueError(
            "kind does not match config kind"
        )
        with pytest.raises(ToolError):
            await knowledge_register_source(
                ctx,
                name="src",
                kind="inline",
                fetch_method="none",
                config={"kind": "url_list", "urls": ["http://example.com"]},
            )

    @pytest.mark.asyncio
    async def test_store_valueerror_tool_error_includes_detail(self) -> None:
        """ToolError raised from store ValueError must carry the original exception's detail text."""
        ctx = _make_ctx()
        detail = "kind does not match config kind"
        ctx.request_context.lifespan_context.source_store_v2.register_source.side_effect = ValueError(detail)
        with pytest.raises(ToolError) as exc_info:
            await knowledge_register_source(
                ctx,
                name="src",
                kind="inline",
                fetch_method="none",
                config={"kind": "inline"},
            )
        assert detail in str(exc_info.value), (
            "ToolError from store ValueError must include the original error detail text"
        )

    # -- AC2: ToolError detail text present (retry, finding #2) -----------------------

    @pytest.mark.asyncio
    async def test_invalid_kind_tool_error_includes_detail(self) -> None:
        """ToolError for invalid kind must include descriptive detail text, not be blank or generic."""
        ctx = _make_ctx()
        with pytest.raises(ToolError) as exc_info:
            await knowledge_register_source(
                ctx,
                name="src",
                kind="not_a_valid_kind",
                fetch_method="none",
                config={"kind": "inline"},
            )
        assert len(str(exc_info.value)) > 0, "ToolError detail must be non-empty"
        assert "not_a_valid_kind" in str(exc_info.value), (
            "ToolError detail must reference the invalid input value 'not_a_valid_kind'"
        )

    @pytest.mark.asyncio
    async def test_invalid_fetch_method_tool_error_includes_detail(self) -> None:
        """ToolError for invalid fetch_method must include descriptive detail text."""
        ctx = _make_ctx()
        with pytest.raises(ToolError) as exc_info:
            await knowledge_register_source(
                ctx,
                name="src",
                kind="inline",
                fetch_method="not_a_transport",
                config={"kind": "inline"},
            )
        assert len(str(exc_info.value)) > 0, "ToolError detail must be non-empty"
        assert "not_a_transport" in str(exc_info.value), (
            "ToolError detail must reference the invalid input value 'not_a_transport'"
        )

    # -- AC3: enrich/refreshable/priority/metadata forwarding (retry, finding #3) ------

    @pytest.mark.asyncio
    async def test_enrich_forwarded_to_registration(self) -> None:
        """Non-default enrich=True must be forwarded into SourceRegistration.enrich."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
            enrich=True,
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.enrich is True, "enrich=True must be forwarded to SourceRegistration"

    @pytest.mark.asyncio
    async def test_refreshable_forwarded_to_registration(self) -> None:
        """Non-default refreshable=False must be forwarded into SourceRegistration.refreshable."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
            refreshable=False,
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.refreshable is False, "refreshable=False must be forwarded to SourceRegistration"

    @pytest.mark.asyncio
    async def test_priority_forwarded_to_registration(self) -> None:
        """Non-default priority value must be forwarded into SourceRegistration.priority."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
            priority=42,
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.priority == 42, "priority=42 must be forwarded to SourceRegistration"

    @pytest.mark.asyncio
    async def test_metadata_forwarded_to_registration(self) -> None:
        """Custom metadata dict must be forwarded into SourceRegistration.metadata unchanged."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context
        custom_metadata: dict[str, object] = {"author": "tester", "version": "1.0"}

        await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
            metadata=custom_metadata,
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.metadata == custom_metadata, (
            "metadata must be forwarded to SourceRegistration unchanged"
        )

    @pytest.mark.asyncio
    async def test_metadata_none_forwarded_as_empty_dict(self) -> None:
        """When metadata=None (default), SourceRegistration.metadata must be {}."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_register_source(
            ctx,
            name="src",
            kind="inline",
            fetch_method="none",
            config={"kind": "inline"},
        )

        call_args = app_ctx.source_store_v2.register_source.call_args
        registration = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert registration.metadata == {}, (
            "metadata=None must be forwarded as {} to SourceRegistration (not None)"
        )
