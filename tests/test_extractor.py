"""RED-phase tests for EntityExtractor DI constructor (task #203 / #33).

Covers all AC lines from #203 for tests/test_extractor.py:
  - empty/whitespace input returns empty ExtractionResult without calling extractor
  - non-empty input delegates to injected StructuredExtractor and returns its result
  - optional metadata dict is prefixed to the prompt string sent to the extractor

All tests must FAIL until #33 implements the DI-based EntityExtractor.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.protocol import StructuredExtractor  # noqa: F401 — RED: not in protocol.py yet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entity(name: str = "test") -> Entity:
    return Entity(name=name, entity_type=EntityType.CONCEPT, scope="global")


def _make_mock_extractor(result: ExtractionResult | None = None) -> MagicMock:
    """Return a MagicMock satisfying StructuredExtractor with a fixed return value."""
    mock = MagicMock(spec=StructuredExtractor)
    mock.extract.return_value = result if result is not None else ExtractionResult()
    return mock


# ---------------------------------------------------------------------------
# TestFromAC_EntityExtractor
# ---------------------------------------------------------------------------


class TestFromAC_EntityExtractor:
    """AC: EntityExtractor with injected StructuredExtractor (task #203/#33)."""

    # --- empty / whitespace guard ---

    @pytest.mark.asyncio
    async def test_empty_string_returns_empty_without_calling_extractor(self) -> None:
        """Empty string returns ExtractionResult() and never calls the injected extractor."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        result = await extractor.extract("")
        assert result == ExtractionResult()
        mock_ext.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_empty_without_calling_extractor(self) -> None:
        """Whitespace-only input returns ExtractionResult() without invoking the extractor."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        result = await extractor.extract("   \t\n  ")
        assert result == ExtractionResult()
        mock_ext.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_newlines_only_returns_empty_without_calling_extractor(self) -> None:
        """Newline-only input is treated as whitespace and returns empty result."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        result = await extractor.extract("\n\n\n")
        assert result == ExtractionResult()
        mock_ext.extract.assert_not_called()

    # --- delegation to injected extractor ---

    @pytest.mark.asyncio
    async def test_nonempty_input_delegates_to_injected_extractor(self) -> None:
        """Non-empty input causes exactly one call to the injected extractor."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        await extractor.extract("pytest is a testing framework")
        mock_ext.extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_exact_result_from_injected_extractor(self) -> None:
        """The ExtractionResult returned is the value produced by the injected extractor."""
        entity = _make_entity("TDD")
        edge = Edge(
            source_id=entity.id,
            target_id="dummy-id",
            relation=RelationType.RELATED_TO,
        )
        expected = ExtractionResult(entities=[entity], edges=[edge])
        mock_ext = _make_mock_extractor(result=expected)
        extractor = EntityExtractor(extractor=mock_ext)
        result = await extractor.extract("TDD is related to testing")
        assert result is expected

    @pytest.mark.asyncio
    async def test_extractor_called_with_single_string_argument(self) -> None:
        """The injected extractor.extract() is called with a single string argument (the prompt)."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        await extractor.extract("hello world")
        mock_ext.extract.assert_called_once()
        call_args = mock_ext.extract.call_args
        assert len(call_args[0]) == 1
        assert isinstance(call_args[0][0], str)

    # --- metadata prefix ---

    @pytest.mark.asyncio
    async def test_metadata_keys_and_values_appear_in_prompt(self) -> None:
        """Each key and value from the metadata dict is included in the prompt."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        metadata = {"scope": "project", "doc_id": "abc123"}
        await extractor.extract("some text", metadata=metadata)
        prompt = mock_ext.extract.call_args[0][0]
        assert "scope" in prompt
        assert "project" in prompt
        assert "doc_id" in prompt
        assert "abc123" in prompt

    @pytest.mark.asyncio
    async def test_metadata_prefix_appears_before_main_text(self) -> None:
        """The metadata prefix occurs earlier in the prompt than the main text."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        text = "the_actual_content_marker_zxq"
        metadata = {"key": "unique_meta_sentinel"}
        await extractor.extract(text, metadata=metadata)
        prompt = mock_ext.extract.call_args[0][0]
        assert prompt.index("unique_meta_sentinel") < prompt.index(text)

    @pytest.mark.asyncio
    async def test_no_metadata_includes_original_text_in_prompt(self) -> None:
        """Without metadata, the prompt contains the original text."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        text = "plain text without metadata"
        await extractor.extract(text)
        prompt = mock_ext.extract.call_args[0][0]
        assert text in prompt

    @pytest.mark.asyncio
    async def test_none_metadata_does_not_raise(self) -> None:
        """metadata=None is accepted and does not error."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        result = await extractor.extract("some text", metadata=None)
        assert isinstance(result, ExtractionResult)

    @pytest.mark.asyncio
    async def test_empty_metadata_dict_does_not_raise(self) -> None:
        """metadata={} is accepted and does not error."""
        mock_ext = _make_mock_extractor()
        extractor = EntityExtractor(extractor=mock_ext)
        result = await extractor.extract("some text", metadata={})
        assert isinstance(result, ExtractionResult)


# ---------------------------------------------------------------------------
# TestFromAC_PromptConstants
# ---------------------------------------------------------------------------


class TestFromAC_PromptConstants:
    """AC: Prompt constants preserved as module-level string constants (task #33 retry)."""

    def test_extraction_prompt_exists_as_module_level_string(self) -> None:
        """EXTRACTION_PROMPT is a non-empty module-level string in owlbear_knowledge.extractor."""
        import owlbear_knowledge.extractor as extractor_mod

        assert hasattr(extractor_mod, "EXTRACTION_PROMPT"), "EXTRACTION_PROMPT missing from extractor module"
        assert isinstance(extractor_mod.EXTRACTION_PROMPT, str)
        assert len(extractor_mod.EXTRACTION_PROMPT) > 0

    def test_graph_builder_prompt_exists_as_module_level_string(self) -> None:
        """GRAPH_BUILDER_PROMPT is a non-empty module-level string in owlbear_knowledge.graph_builder."""
        import owlbear_knowledge.graph_builder as graph_builder_mod

        assert hasattr(graph_builder_mod, "GRAPH_BUILDER_PROMPT"), "GRAPH_BUILDER_PROMPT missing from graph_builder module"
        assert isinstance(graph_builder_mod.GRAPH_BUILDER_PROMPT, str)
        assert len(graph_builder_mod.GRAPH_BUILDER_PROMPT) > 0

    def test_inter_doc_prompt_exists_as_module_level_string(self) -> None:
        """INTER_DOC_PROMPT is a non-empty module-level string in owlbear_knowledge.inter_doc_graph_builder."""
        import owlbear_knowledge.inter_doc_graph_builder as inter_doc_mod

        assert hasattr(inter_doc_mod, "INTER_DOC_PROMPT"), "INTER_DOC_PROMPT missing from inter_doc_graph_builder module"
        assert isinstance(inter_doc_mod.INTER_DOC_PROMPT, str)
        assert len(inter_doc_mod.INTER_DOC_PROMPT) > 0
