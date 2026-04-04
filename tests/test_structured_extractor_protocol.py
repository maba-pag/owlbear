"""RED-phase tests for StructuredExtractor @runtime_checkable protocol (task #203 / #33).

Covers AC line from #203:
  - StructuredExtractor protocol is @runtime_checkable and validates duck-type conformance

All tests must FAIL until #33 adds StructuredExtractor to owlbear_knowledge/protocol.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock

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
