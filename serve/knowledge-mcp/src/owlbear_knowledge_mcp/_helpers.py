"""Utility functions: normalization and serialization helpers."""

from __future__ import annotations

import re
from typing import Any, get_args
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from mcp.server.mcpserver.exceptions import ToolError

from owlbear_knowledge.fetcher import MAX_RESPONSE_BYTES, ContentFetcher, HttpxContentFetcher
from owlbear_knowledge.protocols.failures import KnowledgeFailure, KnowledgeFailureStage
from owlbear_knowledge.protocols.ingest import IngestAcquisitionFailure, IngestDocument

from ._types import (
    _MAX_ENRICHMENT_BATCH_SIZE,
    CaptureEntry,
    CaptureFailureStatus,
    RelatedSource,
    SearchEntity,
    SearchSource,
    _BrowserContentFetcher,
)

_SANITIZED_ERROR_MAX_LEN = 120
_ERROR_CLASS_OR_HTTP_RE = re.compile(r"(?<![/\\])[A-Z][a-zA-Z]*(?:Error|Exception)|HTTP \d{3}")
_NULL_LIKE_SCOPE_VALUES = {"", "none", "null"}
_CAPTURE_FAILURE_STATUSES = frozenset(get_args(CaptureFailureStatus))
_CREDENTIAL_QUERY_TOKENS = frozenset(
    {"auth", "authorization", "cookie", "credential", "key", "passwd", "password", "secret", "session", "sig"}
)
_CREDENTIAL_QUERY_MARKERS = (
    "token",
    "secret",
    "password",
    "passwd",
    "credential",
    "authorization",
    "signature",
    "session",
    "cookie",
    "apikey",
    "accesskey",
)


def _sanitize_error(raw: str | None) -> str | None:
    """Return a safe error token for read surfaces without leaking raw details."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        return "error"
    match = _ERROR_CLASS_OR_HTTP_RE.search(raw)
    if match is None:
        return "error"
    return match.group(0)[:_SANITIZED_ERROR_MAX_LEN]


def _is_credential_query_parameter(name: str) -> bool:
    normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()
    tokens = set(re.split(r"[^a-z0-9]+", normalized))
    return bool(tokens & _CREDENTIAL_QUERY_TOKENS) or any(marker in normalized for marker in _CREDENTIAL_QUERY_MARKERS)


def _redact_capture_url(url: str) -> str:
    """Remove URL userinfo and credential-bearing query values from provenance."""
    try:
        parsed = urlsplit(url)
        safe_netloc = parsed.netloc.rsplit("@", 1)[-1]
        safe_query = urlencode(
            [
                (name, value)
                for name, value in parse_qsl(parsed.query, keep_blank_values=True)
                if not _is_credential_query_parameter(name)
            ],
            doseq=True,
        )
        return urlunsplit((parsed.scheme, safe_netloc, parsed.path, safe_query, ""))
    except ValueError:
        return "<redacted>"


def _validate_capture_round(captures: list[CaptureEntry], registered_urls: tuple[str, ...]) -> dict[str, CaptureEntry]:
    if not captures or not registered_urls or len(set(registered_urls)) != len(registered_urls):
        msg = "captures must contain one entry for every registered source URL"
        raise ToolError(msg)

    registered = set(registered_urls)
    by_url: dict[str, CaptureEntry] = {}
    for entry in captures:
        if not isinstance(entry, dict):
            msg = "captures must contain URL entries"
            raise ToolError(msg)
        url = entry.get("url")
        if not isinstance(url, str) or url not in registered or url in by_url:
            msg = "captures must contain each registered source URL exactly once"
            raise ToolError(msg)
        by_url[url] = entry

    if by_url.keys() != registered:
        msg = "captures must contain each registered source URL exactly once"
        raise ToolError(msg)
    return by_url


def _capture_to_ingest_item(
    url: str,
    entry: CaptureEntry,
    metadata: dict[str, Any] | None,
) -> IngestDocument | IngestAcquisitionFailure:
    has_captured = "captured" in entry
    has_failed = "failed" in entry
    if has_captured == has_failed:
        msg = "each capture entry must contain exactly one outcome"
        raise ToolError(msg)
    if has_failed:
        return _failed_capture_to_ingest_failure(url, entry.get("failed"))
    return _captured_capture_to_ingest_document(url, entry.get("captured"), metadata)


def _failed_capture_to_ingest_failure(url: str, failed: object) -> IngestAcquisitionFailure:
    if not isinstance(failed, dict):
        msg = "failed capture entry is invalid"
        raise ToolError(msg)
    status = failed.get("status")
    if not isinstance(status, str) or status not in _CAPTURE_FAILURE_STATUSES:
        msg = "failed capture status is not supported"
        raise ToolError(msg)
    if "message" in failed and not isinstance(failed["message"], str):
        msg = "failed capture entry is invalid"
        raise ToolError(msg)
    return IngestAcquisitionFailure(
        uri=url,
        failure=KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="browser_capture_failed",
            retryable=False,
            message=f"Browser capture failed with status {status}",
        ),
    )


def _optional_capture_text(captured: dict[str, Any], field_name: str) -> str | None:
    value = captured.get(field_name)
    if value is not None and not isinstance(value, str):
        msg = "captured provenance is invalid"
        raise ToolError(msg)
    return value


def _captured_capture_to_ingest_document(
    url: str,
    captured: object,
    metadata: dict[str, Any] | None,
) -> IngestDocument:
    if not isinstance(captured, dict):
        msg = "captured entry is invalid"
        raise ToolError(msg)
    text = captured.get("text")
    if not isinstance(text, str):
        msg = "captured entry must include text"
        raise ToolError(msg)
    try:
        text_size = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        msg = "captured text is invalid"
        raise ToolError(msg) from None
    if text_size > MAX_RESPONSE_BYTES:
        msg = "captured text exceeds the maximum size"
        raise ToolError(msg)

    title = _optional_capture_text(captured, "title")
    canonical_url = _optional_capture_text(captured, "canonical_url")
    provenance: dict[str, str] = {
        "canonical_url": _redact_capture_url(canonical_url or url),
        "title": title or url,
    }
    for field_name in ("fetched_at", "content_hash"):
        field_value = _optional_capture_text(captured, field_name)
        if field_value is not None:
            provenance[field_name] = field_value

    document_metadata = {} if metadata is None else dict(metadata)
    document_metadata.update(provenance)
    return IngestDocument(title=title or url, text=text, uri=url, metadata=document_metadata)


def _prepare_capture_round(
    captures: list[CaptureEntry],
    registered_urls: tuple[str, ...],
    *,
    metadata: dict[str, Any] | None = None,
) -> tuple[tuple[IngestDocument, ...], tuple[IngestAcquisitionFailure, ...]]:
    by_url = _validate_capture_round(captures, registered_urls)
    documents: list[IngestDocument] = []
    failures: list[IngestAcquisitionFailure] = []
    for url in registered_urls:
        item = _capture_to_ingest_item(url, by_url[url], metadata)
        if isinstance(item, IngestDocument):
            documents.append(item)
        else:
            failures.append(item)
    return tuple(documents), tuple(failures)


def select_content_fetcher(method: str) -> ContentFetcher:
    """Return the content fetcher implementation for a persisted fetch method."""
    normalized = method.strip().lower()
    if normalized == "browser":
        return _BrowserContentFetcher()  # type: ignore[return-value]
    return HttpxContentFetcher()


def _serialize_search_entities(value: object) -> list[SearchEntity]:
    """Normalize result entities to a list of {name, type} objects."""
    if not isinstance(value, list):
        return []

    entities: list[SearchEntity] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name")
            entity_type = item.get("type")
        else:
            name = getattr(item, "name", None)
            entity_type = getattr(item, "type", None)
        if isinstance(name, str) and isinstance(entity_type, str):
            entities.append({"name": name, "type": entity_type})
    return entities


def _serialize_graph_context(value: object) -> str:
    """Normalize graph expansion text for MCP search results."""
    return value if isinstance(value, str) else ""


def _serialize_related_sources(value: object) -> list[RelatedSource]:
    """Normalize related_sources to {name, relationship, entity} objects."""
    if not isinstance(value, list):
        return []

    related_sources: list[RelatedSource] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name")
            relationship = item.get("relationship")
            entity = item.get("entity")
        else:
            name = getattr(item, "name", None)
            relationship = getattr(item, "relationship", None)
            entity = getattr(item, "entity", None)
        if isinstance(name, str) and isinstance(relationship, str) and isinstance(entity, str):
            related_sources.append({"name": name, "relationship": relationship, "entity": entity})
    return related_sources


def _serialize_source(value: object) -> SearchSource:
    """Normalize source metadata to a {name, url} object."""
    name = getattr(value, "name", None)
    raw_url = getattr(value, "url", None)
    url = raw_url.strip() if isinstance(raw_url, str) and raw_url.strip() else None

    if url is None:
        config = getattr(value, "config", None)
        config_url = config.get("url") if isinstance(config, dict) else None
        if isinstance(config_url, str) and config_url.strip():
            url = config_url.strip()
        elif isinstance(config, dict):
            config_urls = config.get("urls")
            if isinstance(config_urls, list):
                url = next((item.strip() for item in config_urls if isinstance(item, str) and item.strip()), None)
            elif isinstance(config_urls, str):
                url = next((item.strip() for item in config_urls.split(",") if item.strip()), None)

    return {
        "name": name if isinstance(name, str) else "",
        "url": url or "",
    }


def _normalize_optional_scope(scope: str | None) -> str | None:
    """Normalize null-like MCP client encodings for optional scope filters."""
    if scope is None:
        return None
    normalized = scope.strip()
    if normalized.lower() in _NULL_LIKE_SCOPE_VALUES:
        return None
    return normalized


def _normalize_scope_list(scopes: object) -> list[str] | None:
    """Normalize MCP search scope filters before vector retrieval."""
    if scopes is None:
        return None
    if not isinstance(scopes, list):
        msg = "scopes must be a list of strings"
        raise ToolError(msg)

    normalized_scopes: list[str] = []
    for scope in scopes:
        if not isinstance(scope, str):
            msg = "scopes must be a list of strings"
            raise ToolError(msg)
        normalized = scope.strip()
        if normalized.lower() in _NULL_LIKE_SCOPE_VALUES:
            continue
        normalized_scopes.append(normalized)
    return normalized_scopes or None


def _normalize_batch_limit(limit: int) -> int:
    """Validate and bound mutable enrichment batch claims."""
    if isinstance(limit, bool) or not isinstance(limit, int):
        msg = "limit must be an integer"
        raise ToolError(msg)
    if limit < 1:
        msg = "limit must be at least 1"
        raise ToolError(msg)
    return min(limit, _MAX_ENRICHMENT_BATCH_SIZE)


def _normalize_read_limit(limit: int) -> int:
    """Validate and bound read-only list limits exposed through MCP tools."""
    if isinstance(limit, bool) or not isinstance(limit, int):
        msg = "limit must be an integer"
        raise ToolError(msg)
    if limit < 1:
        msg = "limit must be at least 1"
        raise ToolError(msg)
    return min(limit, _MAX_ENRICHMENT_BATCH_SIZE)


def _normalize_enrichment_items(value: object, *, field_name: str) -> list[dict[str, Any]]:
    """Validate MCP enrichment payload fields that must be lists of objects."""
    if value is None:
        return []
    if not isinstance(value, list):
        msg = f"{field_name} must be a list of objects"
        raise ToolError(msg)
    for item in value:
        if not isinstance(item, dict):
            msg = f"{field_name} must be a list of objects"
            raise ToolError(msg)
    return value
