"""Text chunker — stub, not yet implemented (#15)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Chunk(BaseModel):
    """A single text chunk produced by TextChunker."""

    model_config = ConfigDict(frozen=True)

    text: str
    index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextChunker:
    """Stub — raises NotImplementedError until extracted from v1."""

    def __init__(
        self,
        *,
        target_tokens: int = 512,
        overlap_tokens: int = 50,
        separators: list[str] | None = None,
    ) -> None:
        _msg = "TextChunker not yet extracted from v1"
        raise NotImplementedError(_msg)

    def chunk(
        self,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        raise NotImplementedError
