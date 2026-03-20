"""Recursive separator-based text chunker for knowledge ingestion."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_DEFAULT_SEPARATORS: list[str] = ["\n## ", "\n### ", "\n\n", "\n", " "]


def _token_count(text: str) -> int:
    """Count tokens using a simple word-split heuristic (KISS — no tiktoken)."""
    return len(text.split())


# -- Models -------------------------------------------------------------------


class Chunk(BaseModel):
    """A single text chunk produced by :class:`TextChunker`."""

    model_config = ConfigDict(frozen=True)

    text: str
    index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


# -- Chunker ------------------------------------------------------------------


class TextChunker:
    """Recursive separator-based text chunker with overlap.

    Splits *text* by trying each separator in order (largest structural
    boundary first, falling back to smaller ones).  Merges the resulting
    pieces into chunks that stay within *target_tokens*.  An optional
    *overlap_tokens* value causes the last N tokens of each chunk to be
    prepended to the next chunk so that context is preserved across
    boundaries.

    Token counting uses ``len(text.split())`` — a word-count heuristic
    that avoids a tiktoken dependency.
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

    # -- public API -----------------------------------------------------------

    def chunk(self, text: str, *, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split *text* into chunks respecting the separator hierarchy.

        Parameters
        ----------
        text:
            The source text to chunk.
        metadata:
            Arbitrary metadata propagated to every :class:`Chunk`.  The
            keys ``start_char`` and ``end_char`` are added automatically.

        Returns:
        -------
        list[Chunk]
            An empty list when *text* is empty or whitespace-only.
        """
        if not text or not text.strip():
            return []

        metadata = dict(metadata) if metadata else {}

        # Step 1: recursively split text into small pieces using separator hierarchy
        pieces = self._recursive_split(text, separator_idx=0)

        # Step 2: merge pieces into target-sized chunks
        raw_chunks = self._merge_pieces(pieces)

        # Step 3: apply overlap
        overlapped = self._apply_overlap(raw_chunks)

        # Step 4: build Chunk objects with metadata and char offsets
        return self._build_chunks(overlapped, text, metadata)

    # -- internals ------------------------------------------------------------

    def _recursive_split(self, text: str, separator_idx: int) -> list[str]:
        """Recursively split *text* using separators starting at *separator_idx*."""
        # Base case: no more separators — split on whitespace (word level)
        if separator_idx >= len(self.separators):
            return [text] if text else []

        sep = self.separators[separator_idx]

        if sep not in text:
            # This separator doesn't appear — try the next one
            return self._recursive_split(text, separator_idx + 1)

        parts = text.split(sep)
        result: list[str] = []
        for i, part in enumerate(parts):
            # Re-attach the separator to the beginning of each part after the first
            # so the structural marker is preserved in the chunk text.
            piece = (sep + part) if i > 0 else part
            if not piece:
                continue
            if _token_count(piece) <= self.target_tokens:
                result.append(piece)
            else:
                # Piece is still too large — recurse with next separator
                result.extend(self._recursive_split(piece, separator_idx + 1))
        return result

    def _merge_pieces(self, pieces: list[str]) -> list[str]:
        """Greedily merge *pieces* so each chunk stays ≤ target_tokens."""
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

        # Hard-cap: if any chunk still exceeds target, force-split on words
        result: list[str] = []
        hard_max = self.target_tokens
        for chunk_text in chunks:
            if _token_count(chunk_text) <= hard_max:
                result.append(chunk_text)
            else:
                result.extend(self._force_split(chunk_text, hard_max))

        return result

    def _force_split(self, text: str, max_tokens: int) -> list[str]:
        """Split *text* into pieces of at most *max_tokens* words."""
        words = text.split()
        pieces: list[str] = []
        for i in range(0, len(words), max_tokens):
            piece = " ".join(words[i : i + max_tokens])
            if piece:
                pieces.append(piece)
        return pieces

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """Prepend the last *overlap_tokens* of the previous chunk to each subsequent chunk."""
        if self.overlap_tokens <= 0 or len(chunks) <= 1:
            return chunks

        result: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tokens = chunks[i - 1].split()
            overlap = prev_tokens[-self.overlap_tokens :]
            overlap_text = " ".join(overlap)
            result.append(overlap_text + " " + chunks[i])

        # Hard-cap after overlap: enforce target + overlap maximum
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
        original: str,
        base_metadata: dict[str, Any],
    ) -> list[Chunk]:
        """Wrap raw text pieces into :class:`Chunk` objects with char offsets."""
        chunks: list[Chunk] = []
        search_start = 0

        for idx, text in enumerate(texts):
            # Find the non-overlap core text position in the original
            # For char offsets, strip the overlap prefix on chunks after the first
            if idx == 0:
                core_text = text
            else:
                # The overlap portion may not appear verbatim in original
                # at this position — so we look for the non-overlap words
                words = text.split()
                core_words = words[self.overlap_tokens :] if self.overlap_tokens > 0 else words
                core_text = " ".join(core_words) if core_words else text

            # Find start_char in original for this chunk's core text
            start_char = self._find_start_char(original, core_text, search_start)

            # Last chunk ends at the end of original text
            end_char = len(original) if idx == len(texts) - 1 else start_char + len(core_text)

            if idx == 0:
                start_char = 0

            meta = {**base_metadata, "start_char": start_char, "end_char": end_char}
            chunks.append(Chunk(text=text, index=idx, metadata=meta))

            # Advance search_start past the current chunk for next iteration
            search_start = start_char + 1

        return chunks

    @staticmethod
    def _find_start_char(original: str, core_text: str, search_from: int) -> int:
        """Find the character offset of *core_text* in *original*."""
        # Try exact match first
        pos = original.find(core_text, search_from)
        if pos >= 0:
            return pos

        # Fallback: find first word of core_text
        parts = core_text.split(maxsplit=1)
        first_word = parts[0] if parts else ""
        if first_word:
            pos = original.find(first_word, search_from)
            if pos >= 0:
                return pos

        return search_from
