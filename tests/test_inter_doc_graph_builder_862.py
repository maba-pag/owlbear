"""RED-phase tests for #862: Inter-doc prompt integration with corporate type guidance.

AC coverage:
  AC1: LLMExtractor accepts optional system_prompt constructor parameter so
       INTER_DOC_PROMPT can be wired in as the system prompt for inter-doc extraction
  AC2: _build_inter_prompt() includes entity types and descriptions alongside entity names
  AC3: Corporate-type guidance (GOVERNS: policy/standard → procedure;
       SUPERSEDES_VERSION: same entity across versions) added to INTER_DOC_PROMPT
  AC4: Existing inter-doc tests still pass (builder's concern); new tests in this file
       cover corporate type guidance

All tests FAIL until #862 implements the changes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.inter_doc_graph_builder import INTER_DOC_PROMPT, InterDocGraphBuilder
from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT, LLMExtractor
from owlbear_knowledge.models import Edge, Entity, EntityType
from owlbear_knowledge.protocol import StructuredExtractor, VectorStoreProtocol


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(
    name: str,
    doc_id: str,
    etype: EntityType = EntityType.POLICY,
    description: str = "test description",
) -> Entity:
    return Entity(
        name=name,
        entity_type=etype,
        scope="global",
        document_id=doc_id,
        description=description,
    )


def _async_extractor(edges: list[Edge] | None = None) -> MagicMock:
    mock = MagicMock(spec=StructuredExtractor)
    mock.extract = AsyncMock(return_value=ExtractionResult(edges=edges or []))
    return mock


def _vector_store() -> MagicMock:
    mock = MagicMock(spec=VectorStoreProtocol)
    mock.get_embedding.return_value = [0.1] * 1024
    mock.search_similar.return_value = []
    return mock


def _graph_store() -> MagicMock:
    mock = MagicMock(spec=GraphStore)
    mock.list_edges.return_value = []
    mock.get_document.return_value = None
    return mock


# ---------------------------------------------------------------------------
# TestFromAC_InterDocPromptIntegration
# ---------------------------------------------------------------------------


class TestFromAC_InterDocPromptIntegration:
    # -- AC1: LLMExtractor accepts optional system_prompt parameter --------

    def test_llm_extractor_accepts_system_prompt_kwarg(self) -> None:
        """LLMExtractor(system_prompt=...) must not raise TypeError."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI"):
            extractor = LLMExtractor(model="m", api_key="k", system_prompt="custom system")
        assert extractor is not None

    def test_llm_extractor_default_system_prompt_is_llm_extraction_prompt(self) -> None:
        """LLMExtractor() without system_prompt stores LLM_EXTRACTION_PROMPT as default."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI"):
            extractor = LLMExtractor(model="m", api_key="k")
        assert extractor._system_prompt == LLM_EXTRACTION_PROMPT

    @pytest.mark.asyncio
    async def test_llm_extractor_custom_system_prompt_sent_as_system_message(self) -> None:
        """extract() sends the custom system_prompt as the system role message."""
        custom_prompt = "inter-doc corporate system prompt"
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.parsed = ExtractionResult()
            mock_client.chat.completions.parse = AsyncMock(return_value=mock_resp)

            extractor = LLMExtractor(model="m", api_key="k", system_prompt=custom_prompt)
            await extractor.extract("user content")

        call_kw = mock_client.chat.completions.parse.call_args.kwargs
        system_msg = next(m for m in call_kw["messages"] if m["role"] == "system")
        assert system_msg["content"] == custom_prompt

    # -- AC2: _build_inter_prompt includes entity types and descriptions ---

    @pytest.mark.asyncio
    async def test_build_inter_prompt_includes_entity_type_in_extractor_call(self) -> None:
        """Entity type values appear in the prompt passed to extractor.extract()."""
        # Same canonical name "risk policy" forces canonical-name blocking to pair them.
        entity_a = _entity("Risk Policy", "doc1", EntityType.POLICY, "governs risk control")
        entity_b = _entity("Risk Policy", "doc2", EntityType.PROCEDURE, "risk assessment steps")
        extractor = _async_extractor()
        builder = InterDocGraphBuilder(
            extractor=extractor, vector_store=_vector_store(), graph_store=_graph_store()
        )
        await builder.build([entity_a, entity_b], scope="test")

        extractor.extract.assert_called_once()
        prompt: str = extractor.extract.call_args.args[0]
        assert EntityType.POLICY.value in prompt
        assert EntityType.PROCEDURE.value in prompt

    @pytest.mark.asyncio
    async def test_build_inter_prompt_includes_entity_description_in_extractor_call(self) -> None:
        """Entity descriptions appear verbatim in the prompt passed to extractor.extract()."""
        entity_a = _entity("Data Standard", "doc1", EntityType.POLICY, "governs data retention")
        entity_b = _entity("Data Standard", "doc2", EntityType.STANDARD, "ISO 27001 baseline")
        extractor = _async_extractor()
        builder = InterDocGraphBuilder(
            extractor=extractor, vector_store=_vector_store(), graph_store=_graph_store()
        )
        await builder.build([entity_a, entity_b], scope="test")

        extractor.extract.assert_called_once()
        prompt: str = extractor.extract.call_args.args[0]
        assert "governs data retention" in prompt
        assert "ISO 27001 baseline" in prompt

    @pytest.mark.asyncio
    async def test_build_inter_prompt_includes_types_for_both_entities_in_pair(self) -> None:
        """Both entities in a candidate pair have their entity_type included in the prompt."""
        entity_a = _entity("Compliance Control", "doc1", EntityType.REQUIREMENT, "req desc")
        entity_b = _entity("Compliance Control", "doc2", EntityType.CONCEPT, "concept desc")
        extractor = _async_extractor()
        builder = InterDocGraphBuilder(
            extractor=extractor, vector_store=_vector_store(), graph_store=_graph_store()
        )
        await builder.build([entity_a, entity_b], scope="test")

        prompt: str = extractor.extract.call_args.args[0]
        assert EntityType.REQUIREMENT.value in prompt
        assert EntityType.CONCEPT.value in prompt

    @pytest.mark.asyncio
    async def test_build_inter_prompt_empty_description_does_not_omit_entity_type(self) -> None:
        """Entity with description='' still emits its entity_type in the prompt."""
        entity_a = _entity("Asset Framework", "doc1", EntityType.STANDARD, description="")
        entity_b = _entity("Asset Framework", "doc2", EntityType.SOLUTION, description="")
        extractor = _async_extractor()
        builder = InterDocGraphBuilder(
            extractor=extractor, vector_store=_vector_store(), graph_store=_graph_store()
        )
        await builder.build([entity_a, entity_b], scope="test")

        extractor.extract.assert_called_once()
        prompt: str = extractor.extract.call_args.args[0]
        assert EntityType.STANDARD.value in prompt
        assert EntityType.SOLUTION.value in prompt

    # -- AC3: INTER_DOC_PROMPT contains corporate-type guidance prose ------

    def test_inter_doc_prompt_has_governs_guidance_prose(self) -> None:
        """INTER_DOC_PROMPT must contain literal 'governs' guidance text.

        Checking the raw (un-formatted) template so the assertion is not satisfied
        by the {relation_types} placeholder injection alone.
        """
        assert "governs" in INTER_DOC_PROMPT.lower(), (
            "INTER_DOC_PROMPT must contain governs guidance prose, "
            "not just rely on {relation_types} placeholder"
        )

    def test_inter_doc_prompt_governs_guidance_references_policy_or_standard(self) -> None:
        """INTER_DOC_PROMPT governs guidance must reference policy or standard entity types."""
        prompt_lower = INTER_DOC_PROMPT.lower()
        assert "policy" in prompt_lower or "standard" in prompt_lower, (
            "INTER_DOC_PROMPT governs guidance must mention policy or standard context"
        )

    def test_inter_doc_prompt_has_supersedes_version_guidance_prose(self) -> None:
        """INTER_DOC_PROMPT must contain literal supersedes_version guidance text."""
        prompt_lower = INTER_DOC_PROMPT.lower()
        assert "supersedes_version" in prompt_lower or "supersedes" in prompt_lower, (
            "INTER_DOC_PROMPT must contain supersedes_version guidance prose"
        )

    def test_inter_doc_prompt_supersedes_version_guidance_references_versions(self) -> None:
        """INTER_DOC_PROMPT supersedes_version guidance must mention document versioning context."""
        assert "version" in INTER_DOC_PROMPT.lower(), (
            "INTER_DOC_PROMPT supersedes_version guidance must mention versioned entities "
            "(e.g., 'same entity across versions' or 'prior version')"
        )
