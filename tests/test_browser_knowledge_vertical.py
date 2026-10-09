"""End-to-end Browser MCP capture and Knowledge MCP ingestion journey."""

from __future__ import annotations

import os
import socket
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from playwright.async_api import Request, Route

from owlbear_browser.playwright_launcher import PlaywrightLauncher
from owlbear_browser_mcp import server as browser_server
from owlbear_browser_mcp.allowlist import DomainAllowlist
from owlbear_knowledge.fetcher import HttpxContentFetcher
from owlbear_knowledge_mcp import server as knowledge_server

_HOST = "pages.synthetic.example"
_URL_A = f"https://{_HOST}/a"
_URL_B = f"https://{_HOST}/b"
_CREDENTIAL_ENVIRONMENT_MARKERS = (
    "ACCESS_KEY",
    "API_KEY",
    "AUTH",
    "CREDENTIAL",
    "PASSWORD",
    "SECRET",
    "TOKEN",
)
_ALPHA_INITIAL_HTML = """\
<html>
<head><title>Alpha page</title></head>
<body><main><h1>Alpha page</h1><p>ALPHA-ARTICLE: original Alpha capture.</p></main></body>
</html>
"""
_ALPHA_REVISED_HTML = """\
<html>
<head><title>Alpha page</title></head>
<body><main><h1>Alpha page</h1><p>ALPHA-ARTICLE: revised Alpha capture.</p></main></body>
</html>
"""
_BETA_HTML = """\
<html>
<head><title>Beta page</title></head>
<body><main><h1>Beta page</h1><p>BETA-ARTICLE: stable Beta capture.</p></main></body>
</html>
"""
_HTTP_ERROR_HTML = "<html><body>Not found</body></html>"
_ACCESS_DENIED_HTML = "<html><body>Forbidden</body></html>"


def _public_addresses(port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]


def _browser_public_resolver(_hostname: str, port: int) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return _public_addresses(port)


async def _knowledge_public_resolver(
    _hostname: str,
    port: int,
) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return _public_addresses(port)


class _DeterministicEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text) + 1)] for text in texts]


class _DeterministicVectorStore:
    def __init__(self) -> None:
        self._scopes: dict[str, str] = {}

    def store_embedding(
        self,
        entity_or_doc_id: str,
        _embedding: object,
        _embedding_type: str,
        *,
        scope: str,
    ) -> None:
        self._scopes[entity_or_doc_id] = scope

    def delete_embedding(self, entity_or_doc_id: str) -> bool:
        return self._scopes.pop(entity_or_doc_id, None) is not None

    def search_similar(
        self,
        _query_embedding: object,
        *,
        top_k: int,
        embedding_type: str,
        scopes: list[str] | None,
    ) -> list[tuple[str, float]]:
        del embedding_type
        return [(item_id, 1.0) for item_id, scope in self._scopes.items() if scopes is None or scope in scopes][:top_k]


class _FailingContentReadConnection(sqlite3.Connection):
    fail_content_reads = False

    def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
        if self.fail_content_reads and "FROM CONTENT_DOCUMENTS" in sql.upper():
            raise _PrivatePersistenceError
        return super().execute(sql, parameters)


class _PrivatePersistenceError(sqlite3.OperationalError):
    def __init__(self) -> None:
        super().__init__("private persistence secret")


def _build_knowledge_context(
    tmp_path: Path,
) -> tuple[
    SimpleNamespace,
    _FailingContentReadConnection,
    list[Path],
    Path,
]:
    database_path = tmp_path / ".owlbear" / "knowledge" / "local.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path), factory=_FailingContentReadConnection)
    embedding_provider = _DeterministicEmbeddingProvider()
    vector_store = _DeterministicVectorStore()
    vector_locations: list[Path] = []

    def vector_store_factory(location: str) -> object:
        vector_locations.append(Path(location))
        return vector_store

    app_context = knowledge_server.build_app_context(
        workspace_root=tmp_path,
        conn=connection,
        factories=knowledge_server.KnowledgeRuntimeFactories(
            http_response_fetcher_factory=lambda: HttpxContentFetcher(resolver=_knowledge_public_resolver),
            embedding_provider_factory=lambda: embedding_provider,
            vector_store_factory=vector_store_factory,
        ),
    )
    tool_context = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=app_context))
    return tool_context, connection, vector_locations, database_path


def _is_within_tmp_path(path: Path, tmp_path: Path) -> bool:
    return path.resolve().is_relative_to(tmp_path.resolve())


async def _capture_round(
    browser_context: SimpleNamespace,
    urls: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    captures: list[dict[str, Any]] = []
    acquisitions: list[dict[str, Any]] = []
    for url in urls:
        result = await browser_server.acquire(browser_context, url)
        acquisitions.append(result)
        if result["status"] == "success":
            captures.append(
                {
                    "url": url,
                    "captured": {
                        "text": result["markdown"],
                        "title": result["title"],
                        "canonical_url": result["canonical_url"],
                        "fetched_at": result["fetched_at"],
                        "content_hash": result["content_hash"],
                    },
                },
            )
        else:
            captures.append({"url": url, "failed": {"status": result["status"], "message": ""}})
    return captures, acquisitions


async def _search_by_uri(tool_context: SimpleNamespace) -> dict[str, dict[str, Any]]:
    results = await knowledge_server.knowledge_search(
        tool_context,
        query="vertical capture",
        scopes=["project:vertical"],
        limit=10,
    )
    assert isinstance(results, list)
    return {item["source"]["uri"]: item for item in results}


async def _register_and_ingest_initial_round(
    knowledge_context: SimpleNamespace,
    browser_context: SimpleNamespace,
    urls: list[str],
) -> str:
    source = await knowledge_server.register_knowledge_source(
        knowledge_context,
        name="Vertical browser fixture",
        kind="url_list",
        fetch_method="browser",
        config={"kind": "url_list", "urls": urls},
        scope="project:vertical",
        enrich=True,
    )
    source_id = source["id"]
    listed = await knowledge_server.list_knowledge_sources(knowledge_context)
    source_row = next(item for item in listed if item["id"] == source_id)
    assert source_row["urls"] == urls

    first_captures, first_acquisitions = await _capture_round(browser_context, urls)
    assert [item["status"] for item in first_acquisitions] == ["success", "success"]
    first_ingest = await knowledge_server.knowledge_ingest(
        knowledge_context,
        source_id=source_id,
        captures=first_captures,
    )
    assert isinstance(first_ingest, dict)
    assert first_ingest["documents_created"] == 2
    assert first_ingest["health"] == "ok"

    scoped_results = await _search_by_uri(knowledge_context)
    assert set(scoped_results) == set(urls)
    assert all(item["source"]["id"] == source_id for item in scoped_results.values())
    global_results = await knowledge_server.knowledge_search(
        knowledge_context,
        query="vertical capture",
        scopes=["global"],
        limit=10,
    )
    assert global_results == []

    refresh = await knowledge_server.refresh_knowledge_source(knowledge_context, source_id)
    assert refresh["errors"][0]["code"] == "agent_capture_required"

    identical_captures, identical_acquisitions = await _capture_round(browser_context, urls)
    assert [item["status"] for item in identical_acquisitions] == ["success", "success"]
    identical = await knowledge_server.knowledge_ingest(
        knowledge_context,
        source_id=source_id,
        captures=identical_captures,
    )
    assert isinstance(identical, dict)
    assert identical["documents_unchanged"] == 2
    assert identical["health"] == "ok"
    return source_id


async def _assert_enrichment_cleanup_and_replacement(
    knowledge_context: SimpleNamespace,
    browser_context: SimpleNamespace,
    source_id: str,
    fixtures: dict[str, tuple[int, str]],
) -> None:
    enrichment_batch = await knowledge_server.claim_enrichment_batch(knowledge_context)
    alpha_chunk = next(item for item in enrichment_batch if "ALPHA-ARTICLE" in item["text"])
    await knowledge_server.store_enrichment(
        knowledge_context,
        chunk_id=alpha_chunk["chunk_id"],
        entities=[{"id": "alpha-local", "name": "Alpha", "entity_type": "concept"}],
        edges=[],
        claim_token=alpha_chunk["claim_token"],
    )
    entity = await knowledge_server.lookup_knowledge_entity(knowledge_context, entity_name="Alpha")
    assert entity["entity"]["name"] == "Alpha"

    fixtures[_URL_A] = (200, _ALPHA_REVISED_HTML)
    captures, acquisitions = await _capture_round(browser_context, [_URL_A, _URL_B])
    assert [item["status"] for item in acquisitions] == ["success", "success"]
    revised = await knowledge_server.knowledge_ingest(
        knowledge_context,
        source_id=source_id,
        captures=captures,
    )
    assert isinstance(revised, dict)
    assert revised["documents_replaced"] == 1
    revised_results = await _search_by_uri(knowledge_context)
    assert "revised Alpha capture" in revised_results[_URL_A]["snippet"]
    with pytest.raises(ToolError, match="entity not found"):
        await knowledge_server.lookup_knowledge_entity(knowledge_context, entity_name="Alpha")


async def _assert_acquisition_failures_preserve_last_good_content(
    knowledge_context: SimpleNamespace,
    browser_context: SimpleNamespace,
    source_id: str,
    fixtures: dict[str, tuple[int, str]],
) -> None:
    fixtures[_URL_A] = (404, _HTTP_ERROR_HTML)
    captures, acquisitions = await _capture_round(browser_context, [_URL_A, _URL_B])
    assert [item["status"] for item in acquisitions] == ["http_error", "success"]
    degraded = await knowledge_server.knowledge_ingest(
        knowledge_context,
        source_id=source_id,
        captures=captures,
    )
    assert isinstance(degraded, dict)
    assert degraded["documents_failed"] == 1
    assert degraded["health"] == "degraded"
    degraded_results = await _search_by_uri(knowledge_context)
    assert "revised Alpha capture" in degraded_results[_URL_A]["snippet"]

    fixtures[_URL_A] = (403, _ACCESS_DENIED_HTML)
    denied = await browser_server.acquire(browser_context, _URL_A)
    assert denied["status"] == "access_denied"

    fixtures[_URL_B] = (404, _HTTP_ERROR_HTML)
    captures, acquisitions = await _capture_round(browser_context, [_URL_A, _URL_B])
    assert [item["status"] for item in acquisitions] == ["access_denied", "http_error"]
    failed = await knowledge_server.knowledge_ingest(
        knowledge_context,
        source_id=source_id,
        captures=captures,
    )
    assert isinstance(failed, dict)
    assert failed["documents_failed"] == 2
    assert failed["health"] == "failed"
    assert failed["documents_created"] == 0
    assert failed["documents_replaced"] == 0
    assert failed["documents_unchanged"] == 0
    retained_results = await _search_by_uri(knowledge_context)
    assert set(retained_results) == {_URL_A, _URL_B}
    assert "revised Alpha capture" in retained_results[_URL_A]["snippet"]
    assert "stable Beta capture" in retained_results[_URL_B]["snippet"]


async def _assert_persistence_failure_is_typed_and_redacted(
    knowledge_context: SimpleNamespace,
    browser_context: SimpleNamespace,
    connection: _FailingContentReadConnection,
    source_id: str,
    fixtures: dict[str, tuple[int, str]],
) -> None:
    fixtures[_URL_A] = (200, _ALPHA_REVISED_HTML)
    fixtures[_URL_B] = (200, _BETA_HTML)
    captures, acquisitions = await _capture_round(browser_context, [_URL_A, _URL_B])
    assert [item["status"] for item in acquisitions] == ["success", "success"]

    connection.fail_content_reads = True
    result = await knowledge_server.knowledge_ingest(
        knowledge_context,
        source_id=source_id,
        captures=captures,
    )
    assert isinstance(result, dict)
    assert result["documents_failed"] == 2
    assert result["health"] == "failed"
    assert result["documents_created"] == 0
    assert result["documents_replaced"] == 0
    assert result["documents_unchanged"] == 0
    errors = result["errors"]
    assert len(errors) == 2
    assert all(error["stage"] == "persistence" for error in errors)
    assert all(error["code"] == "persistence_failed" for error in errors)
    assert all("private persistence secret" not in error["message"] for error in errors)
    listed = await knowledge_server.list_knowledge_sources(knowledge_context)
    source_row = next(item for item in listed if item["id"] == source_id)
    assert source_row["health"] == "failed"


@pytest.mark.asyncio
@pytest.mark.browser
async def test_browser_capture_ingests_and_preserves_knowledge_through_public_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in tuple(os.environ):
        if any(marker in name.upper() for marker in _CREDENTIAL_ENVIRONMENT_MARKERS):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("SSO_EXTENSION_PATH", raising=False)

    urls = [_URL_A, _URL_B]
    fixtures = {
        _URL_A: (200, _ALPHA_INITIAL_HTML),
        _URL_B: (200, _BETA_HTML),
    }
    aborted_non_synthetic_requests: list[str] = []

    async def route_request(route: Route, request: Request) -> None:
        parsed_url = urlsplit(request.url)
        if parsed_url.hostname == _HOST:
            status, body = fixtures.get(request.url, (404, "not found"))
            await route.fulfill(
                status=status,
                headers={"content-type": "text/html; charset=utf-8"},
                body=body,
            )
            return
        aborted_non_synthetic_requests.append(request.url)
        await route.abort()

    profile_path = tmp_path / "browser-profile"
    async with PlaywrightLauncher(user_data_dir=str(profile_path), headless=True) as launcher:
        page = await launcher.page()
        await page.context.route("**/*", route_request)
        browser_app_context = browser_server.AppContext(
            allowlist=DomainAllowlist(domains=[_HOST]),
            launcher=launcher,
            resolver=_browser_public_resolver,
        )
        browser_tool_context = SimpleNamespace(
            request_context=SimpleNamespace(lifespan_context=browser_app_context),
        )
        knowledge_tool_context, connection, vector_locations, database_path = _build_knowledge_context(tmp_path)

        try:
            assert _is_within_tmp_path(database_path, tmp_path)
            assert _is_within_tmp_path(profile_path, tmp_path)
            assert vector_locations
            assert all(_is_within_tmp_path(path, tmp_path) for path in vector_locations)
            source_id = await _register_and_ingest_initial_round(knowledge_tool_context, browser_tool_context, urls)
            await _assert_enrichment_cleanup_and_replacement(
                knowledge_tool_context,
                browser_tool_context,
                source_id,
                fixtures,
            )
            await _assert_acquisition_failures_preserve_last_good_content(
                knowledge_tool_context,
                browser_tool_context,
                source_id,
                fixtures,
            )
            await _assert_persistence_failure_is_typed_and_redacted(
                knowledge_tool_context,
                browser_tool_context,
                connection,
                source_id,
                fixtures,
            )
            assert aborted_non_synthetic_requests == []
        finally:
            connection.close()
