"""RED-phase tests for StructuredExtractor @runtime_checkable protocol (task #203 / #33).

Covers AC line from #203:
  - StructuredExtractor protocol is @runtime_checkable and validates duck-type conformance

All tests must FAIL until #33 adds StructuredExtractor to owlbear_knowledge/protocol.py.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.protocol import StructuredExtractor  # RED: not in protocol.py yet


# ---------------------------------------------------------------------------
# Duck-type fixtures
# ---------------------------------------------------------------------------


class _ConformingExtractor:
    """Fully conforming duck-type: has extract(prompt: str) -> ExtractionResult."""

    def extract(self, prompt: str) -> ExtractionResult:  # noqa: ARG002
        return ExtractionResult()


class _MissingExtractMethod:
    """Does not implement extract() — missing method entirely."""

    def unrelated_method(self) -> None: ...


class _WrongMethodName:
    """Has a method but not named 'extract'."""

    def run(self, prompt: str) -> ExtractionResult:  # noqa: ARG002
        return ExtractionResult()


# ---------------------------------------------------------------------------
# TestFromAC_StructuredExtractorProtocol
# ---------------------------------------------------------------------------


class TestFromAC_StructuredExtractorProtocol:
    """AC: StructuredExtractor is @runtime_checkable with duck-type conformance (task #203/#33)."""

    def test_protocol_is_importable_from_protocol_module(self) -> None:
        """StructuredExtractor is importable from owlbear_knowledge.protocol."""
        assert StructuredExtractor is not None

    def test_protocol_is_runtime_checkable_no_type_error(self) -> None:
        """isinstance() against StructuredExtractor must not raise TypeError."""
        obj = _ConformingExtractor()
        # Protocols without @runtime_checkable raise TypeError on isinstance()
        try:
            result = isinstance(obj, StructuredExtractor)
        except TypeError as exc:
            pytest.fail(f"isinstance() raised TypeError — protocol is not @runtime_checkable: {exc}")
        assert isinstance(result, bool)

    def test_conforming_object_passes_isinstance(self) -> None:
        """Object with extract(prompt) method satisfies StructuredExtractor at runtime."""
        obj = _ConformingExtractor()
        assert isinstance(obj, StructuredExtractor)

    def test_object_missing_extract_fails_isinstance(self) -> None:
        """Object without extract() method does not satisfy StructuredExtractor."""
        obj = _MissingExtractMethod()
        assert not isinstance(obj, StructuredExtractor)

    def test_object_with_wrong_method_name_fails_isinstance(self) -> None:
        """Object with 'run' instead of 'extract' does not satisfy StructuredExtractor."""
        obj = _WrongMethodName()
        assert not isinstance(obj, StructuredExtractor)

    def test_plain_object_fails_isinstance(self) -> None:
        """A bare object() with no methods does not satisfy StructuredExtractor."""
        assert not isinstance(object(), StructuredExtractor)

    def test_protocol_has_extract_attribute(self) -> None:
        """StructuredExtractor exposes 'extract' as a protocol method."""
        assert hasattr(StructuredExtractor, "extract")

    def test_mock_with_spec_satisfies_protocol(self) -> None:
        """MagicMock(spec=StructuredExtractor) passes isinstance check."""
        mock = MagicMock(spec=StructuredExtractor)
        assert isinstance(mock, StructuredExtractor)


# ---------------------------------------------------------------------------
# TestFromAC_AsyncStructuredExtractorProtocol
# ---------------------------------------------------------------------------


class TestFromAC_AsyncStructuredExtractorProtocol:
    """AC1: StructuredExtractor.extract() must be declared async (task #697/#687)."""

    def test_extract_is_coroutine_function(self) -> None:
        """StructuredExtractor.extract() must be an async coroutine function."""
        assert inspect.iscoroutinefunction(StructuredExtractor.extract), (
            "StructuredExtractor.extract() is not async — protocol must declare 'async def extract'"
        )

    def test_extract_not_a_plain_synchronous_method(self) -> None:
        """extract() must NOT be a plain sync function — the protocol contract requires async."""
        is_plain_sync = inspect.isfunction(StructuredExtractor.extract) and not inspect.iscoroutinefunction(
            StructuredExtractor.extract
        )
        assert not is_plain_sync, "StructuredExtractor.extract() is a plain sync function — must be declared async"

    def test_asyncmock_spec_exposes_async_extract_when_protocol_is_async(self) -> None:
        """AsyncMock(spec=StructuredExtractor) must produce an AsyncMock for the extract attribute.

        When the protocol declares extract() as async, AutoSpec / AsyncMock auto-promotes
        the attribute mock to an AsyncMock. FAIL now (extract is sync), PASS after #687.
        """
        mock = AsyncMock(spec=StructuredExtractor)
        assert inspect.iscoroutinefunction(mock.extract), (
            "AsyncMock with StructuredExtractor spec did not make extract() async — "
            "StructuredExtractor.extract() must be declared async"
        )
