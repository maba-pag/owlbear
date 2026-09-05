"""Content intake: read files, URLs, or plain text into IntakeResult."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from owlbear_knowledge._paths import sandbox_path
from owlbear_knowledge.fetcher import HttpxContentFetcher, failure_for_fetch_exception
from owlbear_knowledge.protocols.failures import KnowledgeFailure, KnowledgeFailureStage, KnowledgeOperationError
from owlbear_web_content import extract_content, normalize

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_knowledge.fetcher import HttpResponseFetcher


_HTML_MEDIA_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_TEXT_MEDIA_TYPES = frozenset({"text/plain", "text/markdown", "text/x-markdown"})


class IntakeResult(BaseModel):
    """Result of a content intake operation."""

    model_config = ConfigDict(frozen=True)

    content: str
    source: str
    metadata: dict[str, Any]
    media_type: str | None = None


async def read_file(path: Path, *, workspace_root: Path) -> IntakeResult:
    """Read a file asynchronously after sandbox validation.

    Args:
        path: Path to the file (relative or absolute).
        workspace_root: The root directory files must reside within.

    Returns:
        IntakeResult with the file content and file metadata.

    Raises:
        PermissionError: If *path* escapes *workspace_root*.
        FileNotFoundError: If the file does not exist.
    """
    resolved = sandbox_path(workspace_root, path)
    text = await asyncio.to_thread(resolved.read_text, encoding="utf-8")
    return IntakeResult(
        content=text,
        source=str(resolved),
        metadata={
            "source_type": "file",
            "fetched_at": datetime.now(tz=UTC).isoformat(),
        },
    )


async def read_url(url: str, *, fetcher: HttpResponseFetcher | None = None) -> IntakeResult:
    """Fetch a URL asynchronously and return content as IntakeResult.

    Args:
        url: The URL to fetch (must be http or https).
        fetcher: Optional response-aware HTTP fetcher. Defaults to ``HttpxContentFetcher``.

    Returns:
        IntakeResult with normalized response content, media type, and URL metadata.

    Raises:
        KnowledgeOperationError: If acquisition or extraction fails.
    """
    response_fetcher = fetcher if fetcher is not None else HttpxContentFetcher()
    try:
        response = await response_fetcher.fetch_response(url)
    except KnowledgeOperationError:
        raise
    except Exception as exc:
        raise KnowledgeOperationError(failure_for_fetch_exception(exc)) from exc
    media_type = response.media_type.split(";", 1)[0].strip().lower()
    if media_type not in _HTML_MEDIA_TYPES and media_type not in _TEXT_MEDIA_TYPES:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.EXTRACTION,
            code="unsupported_media_type",
            retryable=False,
            message="Response media type is unsupported",
        )
        raise KnowledgeOperationError(failure)

    try:
        if media_type in _HTML_MEDIA_TYPES:
            content = normalize(extract_content(response.content, url=url))
        elif media_type in _TEXT_MEDIA_TYPES:
            content = normalize(response.content)
    except KnowledgeOperationError:
        raise
    except Exception as exc:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.EXTRACTION,
            code="extraction_failed",
            retryable=False,
            message="Response extraction failed",
        )
        raise KnowledgeOperationError(failure) from exc
    if not content:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.EXTRACTION,
            code="content_boundary_missing",
            retryable=False,
            message="Response contains no meaningful content",
        )
        raise KnowledgeOperationError(failure)

    return IntakeResult(
        content=content,
        source=url,
        media_type=media_type,
        metadata={
            "source_type": "url",
            "fetched_at": datetime.now(tz=UTC).isoformat(),
        },
    )


def read_text(text: str, source: str = "inline") -> IntakeResult:
    """Synchronous intake for plain text strings.

    Args:
        text: Raw text content to wrap.
        source: Source identifier. Defaults to 'inline'.

    Returns:
        IntakeResult with source_type='text' and fetched_at timestamp.
    """
    return IntakeResult(
        content=text,
        source=source,
        metadata={
            "source_type": "text",
            "fetched_at": datetime.now(tz=UTC).isoformat(),
        },
    )
