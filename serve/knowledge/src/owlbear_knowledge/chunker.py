"""Recursive separator-based text chunker for knowledge ingestion."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_DEFAULT_SEPARATORS: list[str] = ["\n## ", "\n### ", "\n\n", "\n", " "]


def _token_count(text: str) -> int:
    """Count tokens using a simple word-split heuristic."""
    return len(text.split())


class Chunk(BaseModel):
    """A single text chunk produced by :class:`TextChunker`."""

    model_config = ConfigDict(frozen=True)

    text: str
    index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextChunker:
    """Recursive separator-based text chunker with overlap.

    Splits *text* by trying each separator in order (largest structural
    boundary first, falling back to smaller ones). Merges the resulting
    pieces into chunks that stay within *target_tokens*. An optional
    *overlap_tokens* value causes the last N tokens of each chunk to be
    prepended to the next chunk so that context is preserved across
    boundaries.
    """

    def __init__(
        self,
        *,
        target_tokens: int = 512,
        overlap_tokens: int = 50,
        separators: list[str] | None = None,
    ) -> None:
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.separators = list(separators) if separators is not None else list(_DEFAULT_SEPARATORS)

    def chunk(self, text: str, *, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split *text* into chunks respecting the separator hierarchy."""
        if not text or not text.strip():
            return []

        metadata = dict(metadata) if metadata else {}
        pieces = self._recursive_split(text, separator_idx=0)
        raw_chunks = self._merge_pieces(pieces)
        overlapped = self._apply_overlap(raw_chunks)
        return self._build_chunks(overlapped, metadata)

    def _recursive_split(self, text: str, separator_idx: int) -> list[str]:
        if separator_idx >= len(self.separators):
            return [text] if text else []

        sep = self.separators[separator_idx]
        if sep not in text:
            return self._recursive_split(text, separator_idx + 1)

        parts = text.split(sep)
        result: list[str] = []
        for i, part in enumerate(parts):
            piece = (sep + part) if i > 0 else part
            if not piece:
                continue
            if _token_count(piece) <= self.target_tokens:
                result.append(piece)
            else:
                result.extend(self._recursive_split(piece, separator_idx + 1))
        return result

    def _merge_pieces(self, pieces: list[str]) -> list[str]:
        if not pieces:
            return []

        chunks: list[str] = []
        current = pieces[0]
        for piece in pieces[1:]:
            merged = current + piece
            if _token_count(merged) <= self.target_tokens:
                current = merged
            else:
                chunks.append(current)
                current = piece
        if current:
            chunks.append(current)

        result: list[str] = []
        for chunk_text in chunks:
            if _token_count(chunk_text) <= self.target_tokens:
                result.append(chunk_text)
            else:
                result.extend(self._force_split(chunk_text, self.target_tokens))
        return result

    def _force_split(self, text: str, max_tokens: int) -> list[str]:
        words = text.split()
        pieces: list[str] = []
        for i in range(0, len(words), max_tokens):
            piece = " ".join(words[i : i + max_tokens])
            if piece:
                pieces.append(piece)
        return pieces

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        if self.overlap_tokens <= 0 or len(chunks) <= 1:
            return chunks

        result: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tokens = chunks[i - 1].split()
            overlap = prev_tokens[-self.overlap_tokens :]
            result.append(" ".join(overlap) + " " + chunks[i])

        hard_max = self.target_tokens + self.overlap_tokens
        final: list[str] = []
        for chunk_text in result:
            if _token_count(chunk_text) <= hard_max:
                final.append(chunk_text)
            else:
                final.extend(self._force_split(chunk_text, hard_max))
        return final

    def _build_chunks(
        self,
        texts: list[str],
        base_metadata: dict[str, Any],
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        for idx, text in enumerate(texts):
            meta = {**base_metadata, "chunk_index": idx}
            chunks.append(Chunk(text=text, index=idx, metadata=meta))
        return chunks
