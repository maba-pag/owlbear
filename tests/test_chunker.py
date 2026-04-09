"""Tests for TextChunker edge cases — covers uncovered paths in chunker.py.

Targets: _recursive_split recursion, _force_split, _merge_pieces overflow,
_apply_overlap hard-max enforcement, and empty-piece handling.
"""

from __future__ import annotations

from owlbear_knowledge.chunker import TextChunker


class TestChunkerEdgeCases:
    def test_empty_piece_after_split_is_skipped(self) -> None:
        """Text starting with separator produces empty first part that is skipped."""
        # Text starts with separator → split produces ["", "rest"] → piece="" → continue
        chunker = TextChunker(target_tokens=50, overlap_tokens=0, separators=["\n\n"])
        text = "\n\nhello world"
        chunks = chunker.chunk(text)
        texts = [c.text for c in chunks]
        assert len(texts) == 1
        assert all(t.strip() for t in texts), f"Got empty chunk(s): {texts}"

    def test_recursive_split_into_next_separator(self) -> None:
        """When a piece exceeds target_tokens, recursion falls to next separator."""
        # separator[0] = "||", separator[1] = " "
        # The first split produces a piece > 3 tokens, which must recurse to " "
        chunker = TextChunker(target_tokens=3, overlap_tokens=0, separators=["||", " "])
        text = "a b c d||e f"
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2, f"Expected >=2 chunks, got {len(chunks)}"

    def test_empty_pieces_returns_empty(self) -> None:
        """Whitespace-only text returns no chunks."""
        chunker = TextChunker(target_tokens=10, overlap_tokens=0)
        assert chunker.chunk("   ") == []
        assert chunker.chunk("") == []

    def test_force_split_on_oversized_merged_chunk(self) -> None:
        """When _merge_pieces produces a chunk > target, _force_split breaks it by words."""
        # Single separator, each piece is within target, but merge can't merge and
        # a single piece exceeds target because no sub-separator exists
        chunker = TextChunker(target_tokens=2, overlap_tokens=0, separators=["\n\n"])
        text = "word1 word2 word3 word4 word5"
        chunks = chunker.chunk(text)
        # Force split should break into pieces <=2 tokens each
        for c in chunks:
            word_count = len(c.text.split())
            assert word_count <= 2, f"Chunk '{c.text}' has {word_count} words, expected <=2"

    def test_force_split_produces_correct_pieces(self) -> None:
        """_force_split divides text at word boundaries by max_tokens."""
        chunker = TextChunker(target_tokens=3, overlap_tokens=0, separators=[])
        # No separators match → all text goes through as one piece → force split
        text = "one two three four five six"
        chunks = chunker.chunk(text)
        assert len(chunks) == 2  # [one two three, four five six]
        assert chunks[0].text == "one two three"
        assert chunks[1].text == "four five six"

    def test_overlap_hard_max_triggers_force_split(self) -> None:
        """When overlap pushes a chunk beyond hard_max, it is force-split."""
        # target=3, overlap=2 → hard_max=5
        # Create chunks where overlap pushes beyond 5 words
        chunker = TextChunker(target_tokens=3, overlap_tokens=2, separators=["\n\n"])
        text = "a b c\n\nd e f\n\ng h i"
        chunks = chunker.chunk(text)
        hard_max = 5
        for c in chunks:
            word_count = len(c.text.split())
            assert word_count <= hard_max, f"Chunk '{c.text}' has {word_count} words, exceeds hard_max={hard_max}"

    def test_separator_exhaustion_returns_text_as_is(self) -> None:
        """When no separator matches, text is returned as-is (base case)."""
        chunker = TextChunker(target_tokens=100, overlap_tokens=0, separators=["###"])
        text = "no separators here at all"
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_chunk_metadata_propagated(self) -> None:
        """Base metadata is merged into each chunk's metadata dict."""
        chunker = TextChunker(target_tokens=5, overlap_tokens=0, separators=[" "])
        text = "hello world foo bar baz qux"
        chunks = chunker.chunk(text, metadata={"source": "test"})
        assert all(c.metadata["source"] == "test" for c in chunks)

    def test_chunk_index_is_sequential(self) -> None:
        """Chunk index starts at 0 and increments sequentially."""
        chunker = TextChunker(target_tokens=3, overlap_tokens=0, separators=["\n\n"])
        text = "a b c\n\nd e f\n\ng h i"
        chunks = chunker.chunk(text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i
