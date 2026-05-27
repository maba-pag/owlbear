"""Failing tests for task #1893 — wire ingest_document to IngestCoordinator.ingest.

Source file under test:
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (ingest_document tool)

AC coverage:
  AC1 — tool delegates to IngestCoordinator.ingest(); guards on ingest_coordinator
         and source_store_v2 being non-None
  AC2 — inline source resolved via source_store_v2.list_sources() filtered by name+kind;
         created via register_source() if not found
  AC3 — IngestRequest constructed with source_id, IngestDocument with title/text/uri/metadata,
         enrich=True
  AC4 — response string surfaces IngestResult.documents_processed, chunks_created,
         chunks_enqueued
  AC5 — old IngestPipeline.ingest_text() call removed; exception handling preserved
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.protocols.ingest import (
    IngestDocument,
    IngestRequest,
    IngestResult,
)
from owlbear_knowledge.protocols.sources import (
    FetchTransport,
    InlineConfig,
    SourceKind,
    SourceRegistration,
    SourceState,
)
from owlbear_knowledge.stores.sources import SqliteSourceStore
from owlbear_mcp_knowledge.server import app_lifespan, knowledge_ingest as ingest_document


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source_record(
    source_id: str = "src-inline-1893",
    name: str = "mcp-inline-global",
    kind: SourceKind = SourceKind.INLINE,
    state: SourceState = SourceState.ACTIVE,
    scope: str = "global",
) -> MagicMock:
    """Return a minimal mock source record."""
    record = MagicMock()
    record.id = source_id
    record.name = name
    record.kind = kind
    record.state = state
    record.scope = scope
    return record


def _make_ingest_result(
    *,
    documents_processed: int = 1,
    chunks_created: int = 3,
    chunks_enqueued: int = 3,
) -> MagicMock:
    """Return a minimal mock IngestResult."""
    result = MagicMock(spec=IngestResult)
    result.documents_processed = documents_processed
    result.chunks_created = chunks_created
    result.chunks_enqueued = chunks_enqueued
    return result


def _make_pipeline_mock() -> MagicMock:
    """Return a mock IngestPipeline that returns a successful non-error result.

    Used in guard tests to ensure old code doesn't short-circuit on pipeline=None
    before reaching the new coordinator/store guard logic.
    """
    pipeline = MagicMock()
    old_result = MagicMock()
    old_result.status = "ok"
    old_result.document_id = "old-doc-id"
    old_result.chunk_count = 1
    old_result.entity_count = 0
    old_result.edge_count = 0
    old_result.warnings = []
    pipeline.ingest_text = AsyncMock(return_value=old_result)
    return pipeline


def _make_ctx(
    *,
    ingest_coordinator: object = "auto",
    source_store_v2: object = "auto",
    ingest_pipeline: object = "sentinel",
    source_record: MagicMock | None = None,
    ingest_result: MagicMock | None = None,
) -> MagicMock:
    """Build a mock MCP context with configurable app-context fields.

    Pass ``ingest_coordinator=None`` to simulate the coordinator guard path.
    Pass ``source_store_v2=None`` to simulate the store guard path.
    Pass ``ingest_pipeline=None`` to explicitly set pipeline to None.
    Default pipeline is a configured AsyncMock returning a success result so
    old-code guard tests don't short-circuit before reaching new guard logic.
    """
    if source_record is None:
        source_record = _make_source_record()
    if ingest_result is None:
        ingest_result = _make_ingest_result()

    app_ctx = MagicMock()
    if ingest_pipeline == "sentinel":
        app_ctx.ingest_pipeline = _make_pipeline_mock()
    else:
        app_ctx.ingest_pipeline = ingest_pipeline

    if source_store_v2 is None:
        app_ctx.source_store_v2 = None
    elif source_store_v2 == "auto":
        store = MagicMock()
        # Default: list_sources returns tuple with matching source
        store.list_sources.return_value = (source_record,)
        store.register_source.return_value = source_record
        app_ctx.source_store_v2 = store
    else:
        app_ctx.source_store_v2 = source_store_v2

    if ingest_coordinator is None:
        app_ctx.ingest_coordinator = None
    elif ingest_coordinator == "auto":
        coordinator = MagicMock()
        coordinator.ingest = AsyncMock(return_value=ingest_result)
        app_ctx.ingest_coordinator = coordinator
    else:
        app_ctx.ingest_coordinator = ingest_coordinator

    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_IngestDocumentCoordinatorWiring
# ---------------------------------------------------------------------------


class TestFromAC_IngestDocumentCoordinatorWiring:
    """AC coverage for task #1893 — ingest_document wired to IngestCoordinator."""

    # -- AC1: Guard checks — ingest_coordinator is None ---------------------

    @pytest.mark.asyncio
    async def test_returns_error_when_ingest_coordinator_is_none(self) -> None:
        """ingest_document returns an error string when ingest_coordinator is None.

        Currently FAILS: the old code checks 'pipeline is None' not 'ingest_coordinator'.
        With a non-None pipeline the old code returns a success string, not an error.
        """
        # Use a real pipeline mock so old code doesn't bail on pipeline=None;
        # old code will then return a success string → assertion fails before fix.
        ctx = _make_ctx(ingest_coordinator=None)
        result = await ingest_document(ctx, text="some text")
        assert isinstance(result, str), "result must be a string"
        assert "error" in result.lower(), f"expected error string, got: {result!r}"

    @pytest.mark.asyncio
    async def test_returns_error_when_source_store_v2_is_none(self) -> None:
        """ingest_document returns an error string when source_store_v2 is None.

        Currently FAILS: the old code does not check source_store_v2 at all;
        with a non-None pipeline it returns a success string, not an error.
        """
        ctx = _make_ctx(source_store_v2=None)
        result = await ingest_document(ctx, text="some text")
        assert isinstance(result, str), "result must be a string"
        assert "error" in result.lower(), f"expected error string, got: {result!r}"

    @pytest.mark.asyncio
    async def test_returns_error_when_both_guards_fail(self) -> None:
        """Returns error when both ingest_coordinator and source_store_v2 are None.

        Currently FAILS: old code returns success string via non-None pipeline mock.
        """
        ctx = _make_ctx(ingest_coordinator=None, source_store_v2=None)
        result = await ingest_document(ctx, text="some text")
        assert isinstance(result, str), "result must be a string"
        assert "error" in result.lower(), f"expected error string, got: {result!r}"

    @pytest.mark.asyncio
    async def test_proceeds_when_both_guards_satisfied(self) -> None:
        """Does not return an error; response uses the new coordinator format.

        Currently FAILS: old code returns old pipeline format (no 'documents_processed').
        """
        ctx = _make_ctx()
        result = await ingest_document(ctx, text="hello")
        assert isinstance(result, str), "result must be a string"
        assert "error" not in result.lower(), f"unexpected error: {result!r}"
        # New format must include coordinator result fields, not old pipeline fields
        assert "documents_processed" in result, (
            f"response must use new coordinator format, got: {result!r}"
        )

    # -- AC1 (continued): does NOT use ingest_pipeline as the guard ----------

    @pytest.mark.asyncio
    async def test_ingest_pipeline_none_is_not_an_error(self) -> None:
        """Old pipeline being None is NOT a guard condition anymore.

        Currently FAILS: old code returns 'error: ingest pipeline not available'
        when ingest_pipeline is None, even if coordinator is present.
        """
        ctx = _make_ctx(ingest_pipeline=None)  # pipeline explicitly None
        result = await ingest_document(ctx, text="hello")
        assert "error" not in result.lower(), (
            f"ingest_pipeline=None must not trigger an error now that coordinator is used; got: {result!r}"
        )

    # -- AC2: Source resolution — source found in list_sources ---------------

    @pytest.mark.asyncio
    async def test_list_sources_called_with_scope_and_active_state(self) -> None:
        """list_sources called with scope=scope, state=SourceState.ACTIVE.

        Currently FAILS: old code does not call list_sources.
        """
        ctx = _make_ctx()
        await ingest_document(ctx, text="hello", scope="myproject")
        ctx.request_context.lifespan_context.source_store_v2.list_sources.assert_called_once_with(
            scope="myproject",
            state=SourceState.ACTIVE,
        )

    @pytest.mark.asyncio
    async def test_register_source_not_called_when_source_found(self) -> None:
        """register_source NOT called when list_sources already returns matching source.

        Currently FAILS: old code never reaches the coordinator path at all;
        coordinator.ingest.assert_called_once() fails before fix.
        """
        source_record = _make_source_record(
            name="mcp-inline-global",
            kind=SourceKind.INLINE,
        )
        store = MagicMock()
        store.list_sources.return_value = (source_record,)
        ctx = _make_ctx(source_store_v2=store)
        await ingest_document(ctx, text="hello", scope="global")
        store.register_source.assert_not_called()
        # Positive assertion: coordinator.ingest was invoked (new path ran)
        ctx.request_context.lifespan_context.ingest_coordinator.ingest.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_source_called_when_no_matching_source(self) -> None:
        """register_source called when list_sources returns no matching inline source.

        Currently FAILS: old code does not call register_source.
        """
        store = MagicMock()
        store.list_sources.return_value = ()  # nothing found
        registered = _make_source_record(name="mcp-inline-global", kind=SourceKind.INLINE)
        store.register_source.return_value = registered
        ctx = _make_ctx(source_store_v2=store)
        await ingest_document(ctx, text="hello", scope="global")
        store.register_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_source_registration_params_correct(self) -> None:
        """register_source called with correct SourceRegistration fields.

        Currently FAILS: old code does not call register_source.
        """
        store = MagicMock()
        store.list_sources.return_value = ()
        registered = _make_source_record(name="mcp-inline-global", kind=SourceKind.INLINE)
        store.register_source.return_value = registered
        ctx = _make_ctx(source_store_v2=store)
        await ingest_document(ctx, text="hello", scope="global")

        store.register_source.assert_called_once()
        reg: SourceRegistration = store.register_source.call_args[0][0]
        assert isinstance(reg, SourceRegistration), (
            f"register_source must receive a SourceRegistration, got: {type(reg)}"
        )
        assert reg.name == "mcp-inline-global", f"Expected 'mcp-inline-global', got: {reg.name!r}"
        assert reg.kind == SourceKind.INLINE, f"Expected INLINE, got: {reg.kind!r}"
        assert reg.fetch_method == FetchTransport.NONE, f"Expected NONE, got: {reg.fetch_method!r}"
        assert isinstance(reg.config, InlineConfig), f"config must be InlineConfig, got: {type(reg.config)}"
        assert reg.scope == "global", f"Expected 'global', got: {reg.scope!r}"
        assert reg.enrich is True, f"enrich must be True, got: {reg.enrich!r}"
        assert reg.refreshable is False, f"refreshable must be False, got: {reg.refreshable!r}"

    @pytest.mark.asyncio
    async def test_source_name_uses_scope_prefix(self) -> None:
        """Inline source name is 'mcp-inline-{scope}' for arbitrary scope values.

        Currently FAILS: old code does not resolve any inline source.
        """
        scope = "workspace-42"
        expected_name = f"mcp-inline-{scope}"

        store = MagicMock()
        store.list_sources.return_value = ()
        registered = _make_source_record(name=expected_name, kind=SourceKind.INLINE, scope=scope)
        store.register_source.return_value = registered
        ctx = _make_ctx(source_store_v2=store)
        await ingest_document(ctx, text="hello", scope=scope)

        store.register_source.assert_called_once()
        reg: SourceRegistration = store.register_source.call_args[0][0]
        assert reg.name == expected_name, f"Expected {expected_name!r}, got: {reg.name!r}"
        assert reg.scope == scope, f"Expected {scope!r}, got: {reg.scope!r}"

    @pytest.mark.asyncio
    async def test_source_with_wrong_kind_not_used_triggers_register(self) -> None:
        """A non-INLINE source in list_sources does not satisfy the filter; register_source called.

        Currently FAILS: old code does not filter by kind at all.
        """
        wrong_kind_record = _make_source_record(
            name="mcp-inline-global",
            kind=SourceKind.URL_LIST,  # wrong kind
        )
        store = MagicMock()
        store.list_sources.return_value = (wrong_kind_record,)
        registered = _make_source_record(name="mcp-inline-global", kind=SourceKind.INLINE)
        store.register_source.return_value = registered
        ctx = _make_ctx(source_store_v2=store)
        await ingest_document(ctx, text="hello", scope="global")
        store.register_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_source_with_wrong_name_not_used_triggers_register(self) -> None:
        """A source with non-matching name in list_sources triggers register_source.

        Currently FAILS: old code does not filter by name.
        """
        wrong_name_record = _make_source_record(
            name="some-other-source",
            kind=SourceKind.INLINE,
        )
        store = MagicMock()
        store.list_sources.return_value = (wrong_name_record,)
        registered = _make_source_record(name="mcp-inline-global", kind=SourceKind.INLINE)
        store.register_source.return_value = registered
        ctx = _make_ctx(source_store_v2=store)
        await ingest_document(ctx, text="hello", scope="global")
        store.register_source.assert_called_once()

    # -- AC3: IngestRequest / IngestDocument construction -------------------

    @pytest.mark.asyncio
    async def test_coordinator_ingest_called_with_ingest_request(self) -> None:
        """coordinator.ingest() called with an IngestRequest instance.

        Currently FAILS: old code calls pipeline.ingest_text(), not coordinator.ingest().
        """
        ctx = _make_ctx()
        await ingest_document(ctx, text="some content")
        coordinator = ctx.request_context.lifespan_context.ingest_coordinator
        coordinator.ingest.assert_called_once()
        request = coordinator.ingest.call_args[0][0]
        assert isinstance(request, IngestRequest), (
            f"coordinator.ingest must receive an IngestRequest, got: {type(request)}"
        )

    @pytest.mark.asyncio
    async def test_ingest_request_source_id_from_resolved_source(self) -> None:
        """IngestRequest.source_id is the id of the resolved inline source.

        Currently FAILS: old code does not build IngestRequest.
        """
        source_record = _make_source_record(source_id="resolved-src-777")
        store = MagicMock()
        store.list_sources.return_value = (source_record,)
        ctx = _make_ctx(source_store_v2=store)
        await ingest_document(ctx, text="hello")
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        assert request.source_id == "resolved-src-777", (
            f"IngestRequest.source_id must match resolved source id, got: {request.source_id!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_request_source_id_from_newly_registered_source(self) -> None:
        """IngestRequest.source_id is the id returned by register_source (create branch).

        AC3 gap: when list_sources finds no matching source, register_source is called and
        its returned source.id must flow into IngestRequest.source_id — not a stale or
        hardcoded value.
        """
        store = MagicMock()
        store.list_sources.return_value = ()  # nothing found — triggers register_source
        registered = _make_source_record(source_id="newly-registered-123")
        store.register_source.return_value = registered
        ctx = _make_ctx(source_store_v2=store)
        await ingest_document(ctx, text="hello", scope="global")
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        assert request.source_id == "newly-registered-123", (
            f"IngestRequest.source_id must match register_source return value id, got: {request.source_id!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_request_enrich_is_true(self) -> None:
        """IngestRequest.enrich is always True.

        Currently FAILS: old code does not build IngestRequest.
        """
        ctx = _make_ctx()
        await ingest_document(ctx, text="hello")
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        assert request.enrich is True, f"IngestRequest.enrich must be True, got: {request.enrich!r}"

    @pytest.mark.asyncio
    async def test_ingest_document_text_passed_correctly(self) -> None:
        """IngestDocument.text is the text argument.

        Currently FAILS: old code does not build IngestDocument.
        """
        ctx = _make_ctx()
        await ingest_document(ctx, text="the actual document body")
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        doc: IngestDocument = request.documents[0]
        assert doc.text == "the actual document body", (
            f"IngestDocument.text must match input, got: {doc.text!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_title_from_metadata_title(self) -> None:
        """IngestDocument.title is metadata['title'] when present.

        Currently FAILS: old code does not build IngestDocument.
        """
        ctx = _make_ctx()
        await ingest_document(
            ctx,
            text="content",
            metadata={"title": "My Custom Title"},
            source_url="https://example.com/page",
        )
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        doc: IngestDocument = request.documents[0]
        assert doc.title == "My Custom Title", (
            f"title must come from metadata['title'], got: {doc.title!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_title_falls_back_to_source_url(self) -> None:
        """IngestDocument.title falls back to source_url when metadata has no title.

        Currently FAILS: old code does not build IngestDocument.
        """
        ctx = _make_ctx()
        await ingest_document(
            ctx,
            text="content",
            metadata={"author": "Alice"},  # no 'title' key
            source_url="https://example.com/article",
        )
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        doc: IngestDocument = request.documents[0]
        assert doc.title == "https://example.com/article", (
            f"title must fall back to source_url when metadata has no title, got: {doc.title!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_title_untitled_when_no_title_no_url(self) -> None:
        """IngestDocument.title is 'Untitled inline document' when no title and no source_url.

        Currently FAILS: old code does not build IngestDocument.
        """
        ctx = _make_ctx()
        await ingest_document(ctx, text="content", metadata=None, source_url=None)
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        doc: IngestDocument = request.documents[0]
        assert doc.title == "Untitled inline document", (
            f"title must be 'Untitled inline document' when no title/url, got: {doc.title!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_uri_is_source_url(self) -> None:
        """IngestDocument.uri is source_url (may be None).

        Currently FAILS: old code does not build IngestDocument.
        """
        ctx = _make_ctx()
        await ingest_document(ctx, text="content", source_url="https://example.com/doc")
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        doc: IngestDocument = request.documents[0]
        assert doc.uri == "https://example.com/doc", (
            f"IngestDocument.uri must equal source_url, got: {doc.uri!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_uri_is_none_when_no_source_url(self) -> None:
        """IngestDocument.uri is None when source_url not provided.

        Currently FAILS: old code does not build IngestDocument.
        """
        ctx = _make_ctx()
        await ingest_document(ctx, text="content")
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        doc: IngestDocument = request.documents[0]
        assert doc.uri is None, f"IngestDocument.uri must be None when source_url absent, got: {doc.uri!r}"

    @pytest.mark.asyncio
    async def test_ingest_document_metadata_none_becomes_empty_dict(self) -> None:
        """IngestDocument.metadata is {} when metadata=None.

        Currently FAILS: old code does not build IngestDocument.
        """
        ctx = _make_ctx()
        await ingest_document(ctx, text="content", metadata=None)
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        doc: IngestDocument = request.documents[0]
        assert doc.metadata == {}, (
            f"IngestDocument.metadata must be empty dict when metadata=None, got: {doc.metadata!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_metadata_passed_through(self) -> None:
        """IngestDocument.metadata matches the provided metadata dict.

        Currently FAILS: old code does not build IngestDocument.
        """
        ctx = _make_ctx()
        await ingest_document(ctx, text="content", metadata={"key": "value", "num": 42})
        request = ctx.request_context.lifespan_context.ingest_coordinator.ingest.call_args[0][0]
        doc: IngestDocument = request.documents[0]
        assert doc.metadata == {"key": "value", "num": 42}, (
            f"IngestDocument.metadata must match input, got: {doc.metadata!r}"
        )

    # -- AC4: Response string surfaces IngestResult fields ------------------

    @pytest.mark.asyncio
    async def test_response_contains_documents_processed(self) -> None:
        """Response string includes documents_processed from IngestResult.

        Currently FAILS: old code formats a completely different response string.
        """
        ingest_result = _make_ingest_result(documents_processed=1, chunks_created=5, chunks_enqueued=5)
        ctx = _make_ctx(ingest_result=ingest_result)
        result = await ingest_document(ctx, text="hello")
        assert "documents_processed" in result, (
            f"response must mention 'documents_processed', got: {result!r}"
        )
        assert "1" in result, f"response must include the count 1, got: {result!r}"

    @pytest.mark.asyncio
    async def test_response_contains_chunks_created(self) -> None:
        """Response string includes chunks_created from IngestResult.

        Currently FAILS: old code formats 'chunk_count' instead of 'chunks_created'.
        """
        ingest_result = _make_ingest_result(documents_processed=1, chunks_created=7, chunks_enqueued=7)
        ctx = _make_ctx(ingest_result=ingest_result)
        result = await ingest_document(ctx, text="hello")
        assert "chunks_created" in result, (
            f"response must mention 'chunks_created', got: {result!r}"
        )
        assert "7" in result, f"response must include count 7, got: {result!r}"

    @pytest.mark.asyncio
    async def test_response_contains_chunks_enqueued(self) -> None:
        """Response string includes chunks_enqueued from IngestResult.

        Currently FAILS: old code does not mention 'chunks_enqueued'.
        """
        ingest_result = _make_ingest_result(documents_processed=1, chunks_created=4, chunks_enqueued=4)
        ctx = _make_ctx(ingest_result=ingest_result)
        result = await ingest_document(ctx, text="hello")
        assert "chunks_enqueued" in result, (
            f"response must mention 'chunks_enqueued', got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_response_values_match_ingest_result(self) -> None:
        """Response string values match the actual IngestResult field values.

        Currently FAILS: old code reads doc_id/chunk_count/entity_count from old result.
        """
        ingest_result = _make_ingest_result(documents_processed=2, chunks_created=9, chunks_enqueued=6)
        ctx = _make_ctx(ingest_result=ingest_result)
        result = await ingest_document(ctx, text="hello")
        # All three counts must appear in the string
        assert "2" in result, f"documents_processed=2 must appear in: {result!r}"
        assert "9" in result, f"chunks_created=9 must appear in: {result!r}"
        assert "6" in result, f"chunks_enqueued=6 must appear in: {result!r}"

    # -- AC5: Old IngestPipeline.ingest_text removed; exception handling preserved

    @pytest.mark.asyncio
    async def test_ingest_pipeline_ingest_text_not_called(self) -> None:
        """pipeline.ingest_text() is NOT called even when pipeline is present.

        Currently FAILS: old code calls pipeline.ingest_text() as its main path.
        """
        pipeline = MagicMock()
        pipeline.ingest_text = AsyncMock()
        ctx = _make_ctx(ingest_pipeline=pipeline)
        await ingest_document(ctx, text="hello")
        pipeline.ingest_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_coordinator_exception_returns_error_string(self) -> None:
        """Exception in coordinator.ingest() is caught; returns error string.

        Currently FAILS: old code uses pipeline.ingest_text() which succeeds
        (via the pipeline mock), so no exception occurs and no error is returned.
        """
        failing_coordinator = MagicMock()
        failing_coordinator.ingest = AsyncMock(side_effect=RuntimeError("coordinator blew up"))
        ctx = _make_ctx(ingest_coordinator=failing_coordinator)
        result = await ingest_document(ctx, text="hello")
        assert isinstance(result, str), "exception must produce a string result"
        assert "error" in result.lower(), (
            f"error string expected on exception, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_register_source_exception_returns_error_string(self) -> None:
        """Exception in register_source() is caught; returns error string.

        Currently FAILS: old code never calls register_source, so no exception
        is raised there. Pipeline mock returns a success string instead.
        """
        store = MagicMock()
        store.list_sources.return_value = ()
        store.register_source.side_effect = ValueError("bad registration")
        ctx = _make_ctx(source_store_v2=store)
        result = await ingest_document(ctx, text="hello")
        assert isinstance(result, str), "exception must produce a string result"
        assert "error" in result.lower(), (
            f"error string expected on register_source exception, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_list_sources_exception_returns_error_string(self) -> None:
        """Exception in list_sources() is caught by the broad handler; returns error string.

        AC5 gap: the broad try/except wraps list_sources, register_source, AND
        coordinator.ingest. Prove the handler covers the first protected operation
        (list_sources) so narrowing the try boundary above list_sources would be
        caught by this test.
        """
        store = MagicMock()
        store.list_sources.side_effect = RuntimeError("db locked")
        coordinator = MagicMock()
        coordinator.ingest = AsyncMock()
        ctx = _make_ctx(source_store_v2=store, ingest_coordinator=coordinator)
        result = await ingest_document(ctx, text="hello")
        assert isinstance(result, str), "exception must produce a string result"
        assert "error" in result.lower(), (
            f"error string expected on list_sources exception, got: {result!r}"
        )
        coordinator.ingest.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_IngestDocumentLifespanProof
# ---------------------------------------------------------------------------


@pytest.fixture
def _lifespan_heavy_mocks(tmp_path: object) -> object:
    """Patch heavy lifespan deps; yield a bare server mock for app_lifespan.

    SqliteSourceStore is real (in-memory SQLite). Only Qdrant and embedding
    providers are patched to avoid loading heavyweight ML dependencies.
    """
    server_mock = MagicMock()
    env_overrides = {
        "OWLBEAR_LOCAL_KB_PATH": ":memory:",
        "OWLBEAR_QDRANT_PATH": str(tmp_path) + "/vectors",  # type: ignore[operator]
    }
    with (
        patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
        patch.dict(os.environ, env_overrides),
    ):
        yield server_mock


class TestFromAC_IngestDocumentLifespanProof:
    """Integration proof: ingest_document resolves/creates sources via real SqliteSourceStore.

    Drives ingest_document through app_lifespan with a real in-memory SqliteSourceStore
    (only coordinator.ingest and heavy infra deps are mocked). Required by reviewer
    retry-2 (AC2/AC4): the task-scoped suite proves the coordinator contract via mocks;
    this class proves the real runtime source-store wiring boundary.
    """

    @pytest.mark.asyncio
    async def test_ingest_document_creates_inline_source_in_real_store(
        self, _lifespan_heavy_mocks: object
    ) -> None:
        """ingest_document registers mcp-inline-global in real SqliteSourceStore when absent.

        AC2: list_sources finds no match → register_source is called on the real store →
        source appears in list_sources after the call with correct name and kind.
        """
        async with app_lifespan(_lifespan_heavy_mocks) as app_ctx:
            assert isinstance(app_ctx.source_store_v2, SqliteSourceStore)

            fake_result = MagicMock(spec=IngestResult)
            fake_result.documents_processed = 1
            fake_result.chunks_created = 2
            fake_result.chunks_enqueued = 2
            app_ctx.ingest_coordinator.ingest = AsyncMock(return_value=fake_result)

            mcp_ctx = MagicMock()
            mcp_ctx.request_context.lifespan_context = app_ctx

            result = await ingest_document(mcp_ctx, text="hello world", scope="global")

            assert isinstance(result, str)
            assert "error" not in result.lower(), f"unexpected error: {result!r}"

            sources = app_ctx.source_store_v2.list_sources(
                scope="global", state=SourceState.ACTIVE
            )
            inline = [s for s in sources if s.name == "mcp-inline-global"]
            assert len(inline) == 1, (
                f"expected 1 inline source, found {len(inline)}: {inline}"
            )
            assert inline[0].kind == SourceKind.INLINE

    @pytest.mark.asyncio
    async def test_ingest_document_reuses_existing_inline_source(
        self, _lifespan_heavy_mocks: object
    ) -> None:
        """ingest_document does not create a duplicate source on repeat calls.

        AC2: second call finds source via list_sources → skips register_source →
        exactly one source record persists in the real store.
        """
        async with app_lifespan(_lifespan_heavy_mocks) as app_ctx:
            fake_result = MagicMock(spec=IngestResult)
            fake_result.documents_processed = 1
            fake_result.chunks_created = 1
            fake_result.chunks_enqueued = 1
            app_ctx.ingest_coordinator.ingest = AsyncMock(return_value=fake_result)

            mcp_ctx = MagicMock()
            mcp_ctx.request_context.lifespan_context = app_ctx

            await ingest_document(mcp_ctx, text="first doc", scope="global")
            await ingest_document(mcp_ctx, text="second doc", scope="global")

            sources = app_ctx.source_store_v2.list_sources(
                scope="global", state=SourceState.ACTIVE
            )
            inline = [s for s in sources if s.name == "mcp-inline-global"]
            assert len(inline) == 1, (
                f"expected exactly 1 source after two calls, found {len(inline)}"
            )

    @pytest.mark.asyncio
    async def test_ingest_document_response_surfaces_coordinator_counters_real_wiring(
        self, _lifespan_heavy_mocks: object
    ) -> None:
        """Response string surfaces coordinator counters under real app_lifespan wiring.

        AC4: response must include documents_processed, chunks_created, chunks_enqueued
        from the IngestResult even when source_store_v2 is a real SqliteSourceStore.
        """
        async with app_lifespan(_lifespan_heavy_mocks) as app_ctx:
            fake_result = MagicMock(spec=IngestResult)
            fake_result.documents_processed = 3
            fake_result.chunks_created = 7
            fake_result.chunks_enqueued = 7
            app_ctx.ingest_coordinator.ingest = AsyncMock(return_value=fake_result)

            mcp_ctx = MagicMock()
            mcp_ctx.request_context.lifespan_context = app_ctx

            result = await ingest_document(mcp_ctx, text="test content", scope="global")

            assert "documents_processed=3" in result, f"missing counter in: {result!r}"
            assert "chunks_created=7" in result, f"missing counter in: {result!r}"
            assert "chunks_enqueued=7" in result, f"missing counter in: {result!r}"
