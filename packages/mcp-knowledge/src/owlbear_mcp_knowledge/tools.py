"""MCP tool functions for the owlbear-mcp-knowledge package."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol


class QueryService(Protocol):
    """Protocol for services that provide knowledge search context."""

    def query_for_context(
        self,
        prompt: str,
        *,
        max_tokens: int = 2000,
        top_k: int = 5,
    ) -> str | None:
        """Return a formatted context string for a prompt, or None."""


@dataclass(slots=True)
class AppContext:
    """Runtime context passed to MCP tools."""

    query_service: QueryService | None


async def search_knowledge(ctx: AppContext, query: str, limit: int = 5) -> str:
    """Search knowledge context for *query* and return formatted text.

    Args:
        ctx: MCP app context containing the query service.
        query: Natural-language search query.
        limit: Maximum number of results to request.

    Returns:
        A formatted context string from the query service, or a user-facing
        fallback message when the service is unavailable or no results exist.
    """
    query_service = ctx.query_service
    if query_service is None:
        return "Knowledge service not available."

    result = await asyncio.to_thread(
        query_service.query_for_context,
        query,
        top_k=limit,
    )
    if result is None:
        return "No relevant knowledge found for your query."
    return result
