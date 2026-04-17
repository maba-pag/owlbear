"""RED-phase tests for LLMExtractor using openai SDK (task #875).

Covers AC lines:
  - LLMExtractor class in llm_extractor.py satisfying StructuredExtractor protocol
  - Uses AsyncOpenAI with response_format for structured JSON output
  - Constructor takes model, api_key, base_url — works with any OpenAI-compatible endpoint
  - Graceful degradation: try/except → empty ExtractionResult() on LLM failure
  - openai>=1.50 added as optional dep group llm in serve/knowledge/pyproject.toml
  - full extras group includes llm
  - Existing LLM_EXTRACTION_PROMPT constant reused as system prompt

All tests must FAIL until #875 implements LLMExtractor.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT, LLMExtractor  # RED: LLMExtractor not implemented yet
from owlbear_knowledge.models import Entity, EntityType
from owlbear_knowledge.protocol import StructuredExtractor

_PYPROJECT_PATH = Path(__file__).parent.parent / "serve" / "knowledge" / "pyproject.toml"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_parse_response(result: ExtractionResult) -> MagicMock:
    """Build a mock parse() response with a given parsed result."""
    choice = MagicMock()
    choice.message.parsed = result
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def mock_openai(mock_entity: Entity):
    """Patch AsyncOpenAI and yield (MockAOI, mock_parse) with a single-entity success result."""
    success_result = ExtractionResult(entities=[mock_entity])
    mock_parse = AsyncMock(return_value=_make_parse_response(success_result))

    with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
        client = MagicMock()
        # Support both client.chat.completions.parse and client.beta.chat.completions.parse
        client.chat.completions.parse = mock_parse
        client.beta.chat.completions.parse = mock_parse
        mock_aoi.return_value = client
        yield mock_aoi, mock_parse


@pytest.fixture
def mock_entity() -> Entity:
    return Entity(name="TestEntity", entity_type=EntityType.CONCEPT, scope="global")


# ---------------------------------------------------------------------------
# TestFromAC_LLMExtractor
# ---------------------------------------------------------------------------


class TestFromAC_LLMExtractor:
    """AC: LLMExtractor using openai SDK (task #875)."""

    # --- Happy path ---

    @pytest.mark.asyncio
    async def test_extract_returns_extraction_result_type(self, mock_openai) -> None:  # noqa: ARG002
        """extract() always returns an ExtractionResult instance."""
        extractor = LLMExtractor(model="gpt-4o", api_key="sk-test", base_url="http://localhost")
        result = await extractor.extract("Python is a programming language")
        assert isinstance(result, ExtractionResult)

    @pytest.mark.asyncio
    async def test_extract_returns_entities_from_llm_response(self, mock_openai) -> None:  # noqa: ARG002
        """extract() returns entities from the parsed LLM response."""
        extractor = LLMExtractor(model="gpt-4o", api_key="sk-test", base_url="http://localhost")
        result = await extractor.extract("Python is a programming language")
        assert len(result.entities) > 0

    def test_satisfies_structured_extractor_protocol(self) -> None:
        """LLMExtractor satisfies the @runtime_checkable StructuredExtractor Protocol."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            mock_aoi.return_value = MagicMock()
            extractor = LLMExtractor(model="gpt-4o", api_key="sk-test")
        assert isinstance(extractor, StructuredExtractor)

    # --- Edge cases ---

    def test_constructor_accepts_model_api_key_base_url(self) -> None:
        """Constructor accepts model, api_key, and base_url keyword args without raising."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            mock_aoi.return_value = MagicMock()
            extractor = LLMExtractor(
                model="gpt-4o-mini",
                api_key="sk-abc123",
                base_url="https://api.openai.com/v1",
            )
        assert extractor is not None

    def test_base_url_forwarded_to_async_openai_constructor(self) -> None:
        """base_url is forwarded to the AsyncOpenAI constructor call."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            mock_aoi.return_value = MagicMock()
            LLMExtractor(
                model="gpt-4o",
                api_key="sk-test",
                base_url="https://custom.llm-endpoint.io/v1",
            )
        assert mock_aoi.call_args.kwargs.get("base_url") == "https://custom.llm-endpoint.io/v1"

    @pytest.mark.asyncio
    async def test_llm_extraction_prompt_used_as_system_message(self, mock_openai) -> None:
        """LLM_EXTRACTION_PROMPT is sent as the system message in the parse call."""
        _, mock_parse = mock_openai
        extractor = LLMExtractor(model="gpt-4o", api_key="sk-test", base_url="http://localhost")
        await extractor.extract("some text to extract from")
        messages = mock_parse.call_args.kwargs["messages"]
        system_contents = [m.get("content", "") for m in messages if m.get("role") == "system"]
        assert any(LLM_EXTRACTION_PROMPT in content for content in system_contents)

    @pytest.mark.asyncio
    async def test_response_format_is_extraction_result_class(self, mock_openai) -> None:
        """response_format=ExtractionResult is passed to the underlying parse call."""
        _, mock_parse = mock_openai
        extractor = LLMExtractor(model="gpt-4o", api_key="sk-test", base_url="http://localhost")
        await extractor.extract("some text to extract from")
        assert mock_parse.call_args.kwargs.get("response_format") is ExtractionResult

    # --- Error paths ---

    @pytest.mark.asyncio
    async def test_llm_runtime_exception_returns_empty_extraction_result(self) -> None:
        """RuntimeError from parse() is caught; extract() returns empty ExtractionResult."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            client = MagicMock()
            client.chat.completions.parse = AsyncMock(side_effect=RuntimeError("API timeout"))
            client.beta.chat.completions.parse = AsyncMock(side_effect=RuntimeError("API timeout"))
            mock_aoi.return_value = client
            extractor = LLMExtractor(model="gpt-4o", api_key="sk-test", base_url="http://localhost")
            result = await extractor.extract("some text")
        assert result == ExtractionResult()

    @pytest.mark.asyncio
    async def test_parsed_none_returns_empty_extraction_result(self) -> None:
        """When parsed=None (LLM refusal), extract() returns empty ExtractionResult."""
        none_response = _make_parse_response(ExtractionResult())
        none_response.choices[0].message.parsed = None

        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            client = MagicMock()
            client.chat.completions.parse = AsyncMock(return_value=none_response)
            client.beta.chat.completions.parse = AsyncMock(return_value=none_response)
            mock_aoi.return_value = client
            extractor = LLMExtractor(model="gpt-4o", api_key="sk-test", base_url="http://localhost")
            result = await extractor.extract("some text")
        assert result == ExtractionResult()

    @pytest.mark.asyncio
    async def test_connection_error_returns_empty_extraction_result(self) -> None:
        """ConnectionError (network failure) from parse() is caught; returns empty ExtractionResult."""
        with patch("owlbear_knowledge.llm_extractor.AsyncOpenAI") as mock_aoi:
            client = MagicMock()
            client.chat.completions.parse = AsyncMock(side_effect=ConnectionError("host unreachable"))
            client.beta.chat.completions.parse = AsyncMock(side_effect=ConnectionError("host unreachable"))
            mock_aoi.return_value = client
            extractor = LLMExtractor(model="gpt-4o", api_key="sk-test", base_url="http://localhost")
            result = await extractor.extract("some text")
        assert result == ExtractionResult()

    # --- Boundary conditions (pyproject.toml structure) ---

    def test_pyproject_toml_has_llm_optional_dep_group(self) -> None:
        """serve/knowledge/pyproject.toml defines an optional-dependency group named 'llm'."""
        with _PYPROJECT_PATH.open("rb") as f:
            config = tomllib.load(f)
        optional_deps = config.get("project", {}).get("optional-dependencies", {})
        assert "llm" in optional_deps, "optional-dependencies must contain a 'llm' group"

    def test_pyproject_toml_llm_group_requires_openai_gte_1_50(self) -> None:
        """The llm optional-dep group specifies openai>=1.50."""
        with _PYPROJECT_PATH.open("rb") as f:
            config = tomllib.load(f)
        llm_deps: list[str] = config.get("project", {}).get("optional-dependencies", {}).get("llm", [])
        assert any("openai" in dep and "1.50" in dep for dep in llm_deps), (
            f"llm group must include 'openai>=1.50', got: {llm_deps}"
        )

    def test_pyproject_toml_full_group_includes_openai(self) -> None:
        """The full optional-dep group includes openai (bringing in the llm dependency)."""
        with _PYPROJECT_PATH.open("rb") as f:
            config = tomllib.load(f)
        full_deps: list[str] = config.get("project", {}).get("optional-dependencies", {}).get("full", [])
        assert any("openai" in dep for dep in full_deps), f"full extras group must include openai, got: {full_deps}"
