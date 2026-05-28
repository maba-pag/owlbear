"""Content intake: read files, URLs, or plain text into IntakeResult."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from owlbear_knowledge._paths import sandbox_path
from owlbear_knowledge.fetcher import HttpxContentFetcher

if TYPE_CHECKING:
    from pathlib import Path


class IntakeResult(BaseModel):
    """Result of a content intake operation."""

    model_config = ConfigDict(frozen=True)

    content: str
    source: str
    metadata: dict[str, Any]


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


async def read_url(url: str) -> IntakeResult:
    """Fetch a URL asynchronously and return content as IntakeResult.

    Args:
        url: The URL to fetch (must be http or https).

    Returns:
        IntakeResult with the response body and URL metadata.

    Raises:
        httpx.HTTPStatusError: On non-2xx HTTP responses.
    """
    content = await HttpxContentFetcher().fetch(url)
    return IntakeResult(
        content=content,
        source=url,
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
