"""Tests for owlbear.memory.knowledge.chunker — TextChunker + Chunk model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.chunker import Chunk, TextChunker

# -- Chunk model --------------------------------------------------------------


class TestChunkModel:
    """Chunk is a frozen Pydantic model with text, index, metadata."""

    def test_construction(self) -> None:
        c = Chunk(text="hello world", index=0, metadata={"doc_id": "d1"})
        assert c.text == "hello world"
        assert c.index == 0
        assert c.metadata == {"doc_id": "d1"}

    def test_frozen(self) -> None:
        c = Chunk(text="hello", index=0, metadata={})
        with pytest.raises(ValidationError):
            c.text = "bye"  # type: ignore[misc]

    def test_default_metadata_empty(self) -> None:
        c = Chunk(text="hello", index=0)
        assert c.metadata == {}


# -- Empty / whitespace input -------------------------------------------------


class TestEmptyInput:
    """Empty or whitespace-only text returns empty list."""

    @pytest.mark.parametrize("text", ["", "   ", "\n", "\t\n  "])
    def test_empty_or_whitespace_returns_empty(self, text: str) -> None:
        chunker = TextChunker()
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert result == []


# -- Single chunk for short text ----------------------------------------------


class TestShortText:
    """Text shorter than target_tokens returns a single chunk."""

    def test_single_chunk_returned(self) -> None:
        chunker = TextChunker(target_tokens=100)
        text = "This is a short sentence."
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert len(result) == 1
        assert result[0].text == text
        assert result[0].index == 0

    def test_single_chunk_metadata(self) -> None:
        chunker = TextChunker(target_tokens=100)
        text = "Short text."
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        meta = result[0].metadata
        assert meta["doc_id"] == "d1"
        assert meta["start_char"] == 0
        assert meta["end_char"] == len(text)


# -- chunk() returns list[Chunk] with correct fields --------------------------


class TestChunkReturnType:
    """chunk() returns list[Chunk] with text, index, metadata."""

    def test_returns_list_of_chunks(self) -> None:
        chunker = TextChunker(target_tokens=5)
        text = "one two three four five six seven eight nine ten"
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert isinstance(result, list)
        assert all(isinstance(c, Chunk) for c in result)

    def test_indices_are_sequential(self) -> None:
        chunker = TextChunker(target_tokens=5, overlap_tokens=0)
        text = "one two three four five six seven eight nine ten"
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert [c.index for c in result] == list(range(len(result)))


# -- Separator hierarchy ------------------------------------------------------


class TestSeparatorHierarchy:
    """Chunker respects separator hierarchy: \\n## > \\n### > \\n\\n > \\n > space."""

    def test_splits_on_heading2_first(self) -> None:
        text = "Section one content.\n## Section Two\nMore content here."
        chunker = TextChunker(target_tokens=5, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        # Should split at \n## boundary — first chunk ends before \n##
        assert any("Section one content." in c.text for c in result)
        assert any("Section Two" in c.text for c in result)

    def test_splits_on_heading3_when_no_h2(self) -> None:
        text = "Intro paragraph.\n### Subsection\nDetails follow."
        chunker = TextChunker(target_tokens=4, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert any("Intro paragraph." in c.text for c in result)
        assert any("Subsection" in c.text for c in result)

    def test_splits_on_double_newline_when_no_headings(self) -> None:
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunker = TextChunker(target_tokens=3, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert len(result) >= 2

    def test_splits_on_newline_when_no_double(self) -> None:
        text = "line one\nline two\nline three\nline four\nline five"
        chunker = TextChunker(target_tokens=3, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert len(result) >= 2

    def test_splits_on_space_as_last_resort(self) -> None:
        text = "word1 word2 word3 word4 word5 word6 word7 word8"
        chunker = TextChunker(target_tokens=3, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert len(result) >= 2
        for c in result:
            assert len(c.text.split()) <= 3


# -- Hard maximum: no chunk exceeds target_tokens + overlap_tokens -------------


class TestHardMaximum:
    """No chunk exceeds target_tokens + overlap_tokens."""

    def test_no_chunk_exceeds_limit(self) -> None:
        # Build text with 100 words
        text = " ".join(f"word{i}" for i in range(100))
        chunker = TextChunker(target_tokens=20, overlap_tokens=5)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        hard_max = 20 + 5
        for c in result:
            assert len(c.text.split()) <= hard_max, (
                f"Chunk {c.index} has {len(c.text.split())} tokens, max={hard_max}"
            )

    def test_no_exceed_with_headings(self) -> None:
        sections = [f"\n## Section {i}\n" + " ".join(f"w{j}" for j in range(30)) for i in range(5)]
        text = "".join(sections)
        chunker = TextChunker(target_tokens=15, overlap_tokens=3)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        hard_max = 15 + 3
        for c in result:
            assert len(c.text.split()) <= hard_max


# -- Overlap tokens at chunk boundaries ---------------------------------------


class TestOverlap:
    """Overlap tokens appear at chunk boundaries."""

    def test_overlap_from_previous_chunk(self) -> None:
        # 10 words: "w0 w1 w2 w3 w4 w5 w6 w7 w8 w9"
        text = " ".join(f"w{i}" for i in range(10))
        chunker = TextChunker(target_tokens=5, overlap_tokens=2)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert len(result) >= 2
        # Last 2 tokens of chunk 0 should appear at start of chunk 1
        first_tokens = result[0].text.split()
        second_tokens = result[1].text.split()
        overlap = first_tokens[-2:]
        assert second_tokens[:2] == overlap

    def test_no_overlap_on_first_chunk(self) -> None:
        text = " ".join(f"w{i}" for i in range(10))
        chunker = TextChunker(target_tokens=5, overlap_tokens=2)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        # First chunk starts from the beginning of text
        assert result[0].text.startswith("w0")

    def test_zero_overlap(self) -> None:
        text = " ".join(f"w{i}" for i in range(10))
        chunker = TextChunker(target_tokens=5, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        # With zero overlap, no token duplication across chunks
        all_tokens = []
        for c in result:
            all_tokens.extend(c.text.split())
        assert len(all_tokens) == 10


# -- Source tracking metadata --------------------------------------------------


class TestSourceMetadata:
    """Source tracking metadata (doc_id, start_char, end_char) preserved."""

    def test_doc_id_preserved(self) -> None:
        text = " ".join(f"w{i}" for i in range(20))
        chunker = TextChunker(target_tokens=5, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "abc"})
        for c in result:
            assert c.metadata["doc_id"] == "abc"

    def test_start_end_char_present(self) -> None:
        text = " ".join(f"w{i}" for i in range(20))
        chunker = TextChunker(target_tokens=5, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        for c in result:
            assert "start_char" in c.metadata
            assert "end_char" in c.metadata
            assert isinstance(c.metadata["start_char"], int)
            assert isinstance(c.metadata["end_char"], int)

    def test_char_offsets_cover_source_text(self) -> None:
        text = " ".join(f"w{i}" for i in range(20))
        chunker = TextChunker(target_tokens=5, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        # First chunk starts at 0
        assert result[0].metadata["start_char"] == 0
        # Last chunk ends at len(text)
        assert result[-1].metadata["end_char"] == len(text)

    def test_extra_metadata_preserved(self) -> None:
        text = " ".join(f"w{i}" for i in range(20))
        chunker = TextChunker(target_tokens=5, overlap_tokens=0)
        result = chunker.chunk(text, metadata={"doc_id": "d1", "source": "test"})
        for c in result:
            assert c.metadata["source"] == "test"


# -- Configurable target_tokens and overlap_tokens ----------------------------


class TestConfigurable:
    """TextChunker accepts custom target_tokens and overlap_tokens."""

    def test_custom_target_tokens(self) -> None:
        chunker = TextChunker(target_tokens=3)
        text = "one two three four five six"
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        # Should produce multiple chunks with small target
        assert len(result) >= 2

    def test_custom_overlap_tokens(self) -> None:
        chunker = TextChunker(target_tokens=5, overlap_tokens=1)
        text = " ".join(f"w{i}" for i in range(15))
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        # Verify overlap is exactly 1 token
        if len(result) >= 2:
            first_tokens = result[0].text.split()
            second_tokens = result[1].text.split()
            assert second_tokens[0] == first_tokens[-1]

    def test_custom_separators(self) -> None:
        chunker = TextChunker(target_tokens=5, overlap_tokens=0, separators=["|||"])
        text = "alpha bravo charlie|||delta echo foxtrot|||golf hotel india"
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert len(result) >= 2

    def test_defaults(self) -> None:
        chunker = TextChunker()
        assert chunker.target_tokens == 512
        assert chunker.overlap_tokens == 50
        assert chunker.separators == ["\n## ", "\n### ", "\n\n", "\n", " "]


# -- Edge cases for coverage --------------------------------------------------


class TestEdgeCases:
    """Cover remaining branches: force-split after overlap, fallback char offset."""

    def test_force_split_after_overlap_exceeds_hard_max(self) -> None:
        """When overlap pushes a chunk past hard_max, force-split kicks in."""
        # 30 words, target=6, overlap=5 → overlap can push chunks past hard_max=11
        text = " ".join(f"w{i}" for i in range(30))
        chunker = TextChunker(target_tokens=6, overlap_tokens=5)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        hard_max = 6 + 5
        for c in result:
            assert len(c.text.split()) <= hard_max

    def test_single_separator_no_match_falls_through(self) -> None:
        """When no separator matches, falls through to word-level split."""
        chunker = TextChunker(target_tokens=3, overlap_tokens=0, separators=["---"])
        text = "alpha bravo charlie delta echo foxtrot"
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert len(result) >= 2
        for c in result:
            assert len(c.text.split()) <= 3

    def test_metadata_none_defaults_to_empty(self) -> None:
        """Passing no metadata still works — start_char/end_char added."""
        chunker = TextChunker(target_tokens=100)
        result = chunker.chunk("hello world")
        assert len(result) == 1
        assert "start_char" in result[0].metadata
        assert "end_char" in result[0].metadata

    def test_overlap_with_structural_separators(self) -> None:
        """Overlap works correctly with markdown heading separators."""
        text = (
            "Intro words here.\n## Section A\nContent A one two three four.\n"
            "## Section B\nContent B one two three four."
        )
        chunker = TextChunker(target_tokens=6, overlap_tokens=2)
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert len(result) >= 2
        hard_max = 6 + 2
        for c in result:
            assert len(c.text.split()) <= hard_max

    def test_very_long_single_word_force_splits(self) -> None:
        """A single long line with no separator except space is force-split."""
        text = " ".join(f"longword{i}" for i in range(50))
        chunker = TextChunker(target_tokens=10, overlap_tokens=0, separators=[])
        result = chunker.chunk(text, metadata={"doc_id": "d1"})
        assert len(result) == 5
        for c in result:
            assert len(c.text.split()) <= 10
