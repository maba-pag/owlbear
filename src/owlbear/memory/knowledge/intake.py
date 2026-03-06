"""Knowledge intake — file, URL, and text content readers."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

import anyio
import httpx
from pydantic import BaseModel, ConfigDict, Field

from owlbear.core.retry import TRANSIENT_RETRY

if TYPE_CHECKING:
    from pathlib import Path


class IntakeResult(BaseModel):
    """Result of reading content from a file, URL, or raw text."""

    model_config = ConfigDict(frozen=True)

    content: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.datetime.now(datetime.UTC).isoformat()


async def read_file(path: str | Path) -> IntakeResult:
    """Read a text file from disk and return an IntakeResult.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    p = anyio.Path(path)
    content = await p.read_text(encoding="utf-8")
    return IntakeResult(
        content=content,
        source=str(p),
        metadata={"source_type": "file", "fetched_at": _now_iso()},
    )


@TRANSIENT_RETRY
async def read_url(url: str) -> IntakeResult:
    """Fetch content from a URL via httpx and return an IntakeResult.

    Retries transient HTTP errors (429, 502, 503, 504) and connection
    failures up to 3 attempts with exponential backoff.

    Raises:
        httpx.HTTPStatusError: If the response status is permanently non-2xx.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=5)) as client:
        response = await client.get(url)
        response.raise_for_status()
    return IntakeResult(
        content=response.text,
        source=url,
        metadata={"source_type": "url", "fetched_at": _now_iso()},
    )


def read_text(text: str, source: str = "inline") -> IntakeResult:
    """Wrap raw text into an IntakeResult.

    Args:
        text: The raw text content.
        source: Identifier for the text origin (default: ``'inline'``).
    """
    return IntakeResult(
        content=text,
        source=source,
        metadata={"source_type": "text", "fetched_at": _now_iso()},
    )
