"""Smoke tests for SourceFetcher protocol — task #1885.

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py
  serve/knowledge/src/owlbear_knowledge/protocols/__init__.py

AC coverage (smoke — one test per AC line):
  AC1 — FetchedDocument(BoundaryModel) with required title/text/uri + optional external_id/metadata
  AC2 — FetchError(BoundaryModel) with required uri/error
  AC3 — FetchResult(BoundaryModel) with documents/errors tuple fields (empty defaults)
  AC4 — @runtime_checkable SourceFetcher(Protocol) with fetch_source(source, *, cancel) signature
  AC5 — fetch_source docstring: Guarantees/Non-guarantees/Side effects/Raises sections
  AC6 — All 4 names in protocols/__init__.py AND in __all__
  AC7 — Module imports only from allowed sources (.common, .sources, cancellation, stdlib, pydantic)
"""

from __future__ import annotations

import inspect

from owlbear_knowledge.protocols.fetcher import (  # greenfield — ImportError expected
    FetchedDocument,
    FetchError,
    FetchResult,
    SourceFetcher,
)
from owlbear_knowledge.protocols.sources import (
    ConfiguredSourceRecord,
    FetchTransport,
    FileGlobConfig,
    SourceKind,
    SourceState,
)
from owlbear_knowledge.cancellation import CancelSignal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source() -> ConfiguredSourceRecord:
    return ConfiguredSourceRecord(
        id="src-1",
        name="test-source",
        state=SourceState.ACTIVE,
        kind=SourceKind.FILE_GLOB,
        fetch_method=FetchTransport.FILESYSTEM,
        config=FileGlobConfig(patterns=("**/*.txt",)),
    )


# ---------------------------------------------------------------------------
# AC1 — FetchedDocument construction and field contract
# ---------------------------------------------------------------------------


class TestFromAC_FetchedDocumentModel:
    def test_fetched_document_required_fields_and_optional_defaults(self) -> None:
        """AC1: FetchedDocument(BoundaryModel) with required title/text/uri and optional defaults."""
        doc = FetchedDocument(title="My Doc", text="Some content", uri="file:///a.txt")
        assert doc.title == "My Doc"
        assert doc.text == "Some content"
        assert doc.uri == "file:///a.txt"
        assert doc.external_id is None
        assert doc.metadata == {}


# ---------------------------------------------------------------------------
# AC2 — FetchError construction
# ---------------------------------------------------------------------------


class TestFromAC_FetchErrorModel:
    def test_fetch_error_required_fields(self) -> None:
        """AC2: FetchError(BoundaryModel) with required uri and error fields."""
        err = FetchError(uri="file:///missing.txt", error="File not found")
        assert err.uri == "file:///missing.txt"
        assert err.error == "File not found"


# ---------------------------------------------------------------------------
# AC3 — FetchResult construction with empty tuple defaults
# ---------------------------------------------------------------------------


class TestFromAC_FetchResultModel:
    def test_fetch_result_empty_defaults(self) -> None:
        """AC3: FetchResult(BoundaryModel) with documents and errors defaulting to empty tuples."""
        result = FetchResult()
        assert result.documents == ()
        assert result.errors == ()


# ---------------------------------------------------------------------------
# AC4 — SourceFetcher runtime_checkable protocol
# ---------------------------------------------------------------------------


class TestFromAC_SourceFetcherProtocol:
    def test_source_fetcher_is_runtime_checkable(self) -> None:
        """AC4: @runtime_checkable SourceFetcher satisfied by duck-typed class with fetch_source."""

        class _FakeFetcher:
            async def fetch_source(
                self,
                _source: ConfiguredSourceRecord,
                *,
                _cancel: CancelSignal | None = None,
            ) -> FetchResult:
                return FetchResult()

        assert isinstance(_FakeFetcher(), SourceFetcher)


# ---------------------------------------------------------------------------
# AC5 — fetch_source docstring contract
# ---------------------------------------------------------------------------


class TestFromAC_SourceFetcherDocstring:
    def test_fetch_source_docstring_contains_required_sections(self) -> None:
        """AC5: fetch_source docstring contains Guarantees, Non-guarantees, Side effects, Raises."""
        doc = SourceFetcher.fetch_source.__doc__
        assert doc is not None, "fetch_source must have a docstring"
        for section in ("Guarantees", "Non-guarantees", "Side effects", "Raises"):
            assert section in doc, f"fetch_source docstring missing section: {section!r}"


# ---------------------------------------------------------------------------
# AC6 — Re-exports in protocols/__init__.py + __all__
# ---------------------------------------------------------------------------


class TestFromAC_ProtocolsInitReexport:
    def test_all_public_names_in_protocols_namespace_and_all(self) -> None:
        """AC6: FetchedDocument/FetchError/FetchResult/SourceFetcher in protocols namespace and __all__."""
        import owlbear_knowledge.protocols as proto

        for name in ("FetchedDocument", "FetchError", "FetchResult", "SourceFetcher"):
            assert hasattr(proto, name), f"{name!r} not found in owlbear_knowledge.protocols"
            assert name in proto.__all__, f"{name!r} not listed in owlbear_knowledge.protocols.__all__"


# ---------------------------------------------------------------------------
# AC7 — Module import constraints
# ---------------------------------------------------------------------------


class TestFromAC_FetcherModuleImports:
    def test_fetcher_module_imports_only_from_allowed_sources(self) -> None:
        """AC7: fetcher.py imports only .common, .sources, cancellation, stdlib, pydantic."""
        import owlbear_knowledge.protocols.fetcher as fetcher_mod

        source = inspect.getsource(fetcher_mod)

        forbidden = [
            "from owlbear_knowledge.protocols.content",
            "from owlbear_knowledge.protocols.graph",
            "from owlbear_knowledge.protocols.enrichment",
            "from owlbear_knowledge.protocols.ingest",
            "from owlbear_knowledge.protocols.query",
            "from owlbear_knowledge.protocols.registry",
            "import owlbear_knowledge.protocols.content",
            "import owlbear_knowledge.protocols.graph",
            "import owlbear_knowledge.protocols.enrichment",
            "import owlbear_knowledge.protocols.ingest",
        ]
        for pattern in forbidden:
            assert pattern not in source, (
                f"fetcher.py contains forbidden import: {pattern!r}"
            )
