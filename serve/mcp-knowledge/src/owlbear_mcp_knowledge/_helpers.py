"""Utility functions: normalization, serialization, validation, extraction."""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.fetcher import HttpxContentFetcher
from owlbear_knowledge.models import Edge, EntityType, RelationType

from ._types import (
    _MAX_ENRICHMENT_BATCH_SIZE,
    RelatedSource,
    SearchEntity,
    SearchSource,
    _BrowserContentFetcher,
)

if TYPE_CHECKING:
    from owlbear_knowledge.protocol import ContentFetcher

if False:  # TYPE_CHECKING
    pass

_SANITIZED_ERROR_MAX_LEN = 120
_ERROR_CLASS_OR_HTTP_RE = re.compile(r"(?<![/\\])[A-Z][a-zA-Z]*(?:Error|Exception)|HTTP \d{3}")
_NULL_LIKE_SCOPE_VALUES = {"", "none", "null"}


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


def _extract_relation(edge: dict[str, Any]) -> str:
    """Read edge relation from documented aliases and validate it."""
    relation = edge.get("relation")
    if not isinstance(relation, str) or not relation.strip():
        relationship = edge.get("relationship")
        if isinstance(relationship, str) and relationship.strip():
            relation = relationship
    if not isinstance(relation, str) or not relation.strip():
        msg = "edge relation is required (use 'relation' or 'relationship')"
        raise ToolError(msg)
    relation_value = relation.strip().lower()
    try:
        return RelationType(relation_value).value
    except ValueError as exc:
        valid = ", ".join(item.value for item in RelationType)
        msg = f"unsupported edge relation {relation_value!r}; valid values: {valid}"
        raise ToolError(msg) from exc


def _extract_entity_type(entity: dict[str, Any]) -> str:
    """Read entity type from documented aliases and return a readable graph value."""
    entity_type = entity.get("entity_type")
    if not isinstance(entity_type, str) or not entity_type.strip():
        type_alias = entity.get("type")
        entity_type = type_alias if isinstance(type_alias, str) else ""
    if not isinstance(entity_type, str) or not entity_type.strip():
        return EntityType.CONCEPT.value

    entity_type_value = entity_type.strip().lower()
    try:
        return EntityType(entity_type_value).value
    except ValueError as exc:
        valid = ", ".join(item.value for item in EntityType)
        msg = f"unsupported entity_type {entity_type_value!r}; valid values: {valid}"
        raise ToolError(msg) from exc


def _stable_edge_id(*parts: str) -> str:
    """Return a deterministic edge row ID for idempotent retries."""
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def select_content_fetcher(method: str) -> ContentFetcher:
    """Return the content fetcher implementation for a persisted fetch method."""
    normalized = method.strip().lower()
    if normalized == "browser":
        return _BrowserContentFetcher()  # type: ignore[return-value]
    return HttpxContentFetcher()


def _extract_section_path(metadata: str | None) -> str | None:
    """Extract section_path from serialized chunk metadata."""
    if not metadata:
        return None
    try:
        parsed = json.loads(metadata)
    except (TypeError, ValueError):
        return None
    section_path = parsed.get("section_path")
    return section_path if isinstance(section_path, str) else None


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


def _normalize_optional_read_limit(limit: int | None) -> int | None:
    """Validate read limits that explicitly support None as unlimited."""
    if limit is None:
        return None
    return _normalize_read_limit(limit)


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


def _validate_enrichment_edge_payload(payload: dict[str, Any]) -> Edge:
    """Return a domain-validated Edge for an enrichment payload."""
    try:
        return Edge(**payload)
    except ValueError as exc:
        msg = "invalid edge payload"
        raise ToolError(msg) from exc
