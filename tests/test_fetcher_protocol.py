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


class TestFetchedDocumentModel:
    def test_fetched_document_required_fields_and_optional_defaults(self) -> None:
        """AC1: FetchedDocument(BoundaryModel) with required title/text/uri and optional defaults."""
        doc = FetchedDocument(title="My Doc", text="Some content", uri="file:///a.txt")
        assert doc.title == "My Doc"
        assert doc.text == "Some content"
        assert doc.uri == "file:///a.txt"
        assert doc.external_id is None
        assert doc.metadata == {}

    def test_fetched_document_is_boundary_model_subclass(self) -> None:
        """AC1: FetchedDocument must inherit BoundaryModel (boundary contract cannot regress)."""
        from owlbear_knowledge.protocols.common import BoundaryModel

        assert issubclass(FetchedDocument, BoundaryModel), "FetchedDocument must inherit BoundaryModel"

    def test_fetched_document_required_fields_are_required(self) -> None:
        """AC1: title, text, uri must remain required — cannot silently gain defaults."""
        for field_name in ("title", "text", "uri"):
            assert FetchedDocument.model_fields[field_name].is_required(), (
                f"FetchedDocument.{field_name} must be required (no default allowed)"
            )


# ---------------------------------------------------------------------------
# AC2 — FetchError construction
# ---------------------------------------------------------------------------


class TestFetchErrorModel:
    def test_fetch_error_required_fields(self) -> None:
        """AC2: FetchError(BoundaryModel) with required uri and error fields."""
        err = FetchError(uri="file:///missing.txt", error="File not found")
        assert err.uri == "file:///missing.txt"
        assert err.error == "File not found"

    def test_fetch_error_is_boundary_model_subclass(self) -> None:
        """AC2: FetchError must inherit BoundaryModel (boundary contract cannot regress)."""
        from owlbear_knowledge.protocols.common import BoundaryModel

        assert issubclass(FetchError, BoundaryModel), "FetchError must inherit BoundaryModel"

    def test_fetch_error_required_fields_are_required(self) -> None:
        """AC2: uri, error must remain required — cannot silently gain defaults."""
        for field_name in ("uri", "error"):
            assert FetchError.model_fields[field_name].is_required(), (
                f"FetchError.{field_name} must be required (no default allowed)"
            )


# ---------------------------------------------------------------------------
# AC3 — FetchResult construction with empty tuple defaults
# ---------------------------------------------------------------------------


class TestFetchResultModel:
    def test_fetch_result_empty_defaults(self) -> None:
        """AC3: FetchResult(BoundaryModel) with documents and errors defaulting to empty tuples."""
        result = FetchResult()
        assert result.documents == ()
        assert result.errors == ()

    def test_fetch_result_is_boundary_model_subclass(self) -> None:
        """AC3: FetchResult must inherit BoundaryModel (boundary contract cannot regress)."""
        from owlbear_knowledge.protocols.common import BoundaryModel

        assert issubclass(FetchResult, BoundaryModel), "FetchResult must inherit BoundaryModel"

    def test_fetch_result_fields_have_defaults(self) -> None:
        """AC3: documents and errors must have default_factory (remain optional, not required)."""
        for field_name in ("documents", "errors"):
            assert not FetchResult.model_fields[field_name].is_required(), (
                f"FetchResult.{field_name} must have a default (default_factory=tuple)"
            )


# ---------------------------------------------------------------------------
# AC4 — SourceFetcher runtime_checkable protocol
# ---------------------------------------------------------------------------


class TestSourceFetcherProtocol:
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

    def test_source_fetcher_fetch_source_signature(self) -> None:
        """AC4: SourceFetcher.fetch_source must be async with source/cancel params and FetchResult return."""
        sig = inspect.signature(SourceFetcher.fetch_source)
        params = sig.parameters

        assert inspect.iscoroutinefunction(SourceFetcher.fetch_source), "fetch_source must be declared async"

        # 'source' positional param — annotated ConfiguredSourceRecord
        assert "source" in params, "missing 'source' parameter on fetch_source"
        assert params["source"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD, (
            f"'source' must be POSITIONAL_OR_KEYWORD, got {params['source'].kind!r}"
        )
        assert "ConfiguredSourceRecord" in str(params["source"].annotation), (
            f"'source' annotation must reference ConfiguredSourceRecord, got {params['source'].annotation!r}"
        )

        # 'cancel' keyword-only param — annotated CancelSignal | None, default None
        assert "cancel" in params, "missing 'cancel' keyword parameter on fetch_source"
        cancel_param = params["cancel"]
        assert cancel_param.kind == inspect.Parameter.KEYWORD_ONLY, "'cancel' must be keyword-only (after *)"
        assert cancel_param.default is None, "'cancel' default must be None"
        assert "CancelSignal" in str(cancel_param.annotation), (
            f"'cancel' annotation must reference CancelSignal, got {cancel_param.annotation!r}"
        )

        # Return annotation — FetchResult
        assert "FetchResult" in str(sig.return_annotation), (
            f"fetch_source return annotation must be FetchResult, got {sig.return_annotation!r}"
        )


# ---------------------------------------------------------------------------
# AC5 — fetch_source docstring contract
# ---------------------------------------------------------------------------


class TestSourceFetcherDocstring:
    def test_fetch_source_docstring_contains_required_sections(self) -> None:
        """AC5: fetch_source docstring contains Guarantees, Non-guarantees, Side effects, Raises."""
        doc = SourceFetcher.fetch_source.__doc__
        assert doc is not None, "fetch_source must have a docstring"
        for section in ("Guarantees", "Non-guarantees", "Side effects", "Raises"):
            assert section in doc, f"fetch_source docstring missing section: {section!r}"

    def test_fetch_source_docstring_semantics(self) -> None:
        """AC5: fetch_source docstring must encode the required semantic guarantees, not just headings."""
        doc = SourceFetcher.fetch_source.__doc__ or ""
        doc_lower = doc.lower()

        # Guarantees: partial documents on cancel
        assert "partial" in doc_lower, "Guarantees must mention partial documents on cancellation"
        assert "cancel" in doc_lower, "Guarantees must reference cancellation behaviour"

        # Guarantees: per-item failures in errors tuple, never raised
        assert "errors" in doc_lower, "Guarantees must mention errors tuple for per-item failures"
        assert "never" in doc_lower, "Guarantees must state item-level failures are never raised"

        # Non-guarantees: ordering
        assert "order" in doc_lower, "Non-guarantees must state result ordering is not guaranteed"

        # Non-guarantees: batch strategy
        assert "batch" in doc_lower, "Non-guarantees must mention batch strategy"

        # Side effects: transport I/O
        assert "transport" in doc_lower, "Side effects must mention transport I/O"

        # Raises: Never — check inside the Raises section specifically
        raises_idx = doc.find("Raises")
        assert raises_idx != -1, "docstring must have a Raises section"
        raises_section = doc[raises_idx:]
        assert "never" in raises_section.lower(), "Raises section must state 'Never' (no exceptions propagated)"


# ---------------------------------------------------------------------------
# AC6 — Re-exports in protocols/__init__.py + __all__
# ---------------------------------------------------------------------------


class TestProtocolsInitReexport:
    def test_all_public_names_in_protocols_namespace_and_all(self) -> None:
        """AC6: FetchedDocument/FetchError/FetchResult/SourceFetcher in protocols namespace and __all__."""
        import owlbear_knowledge.protocols as proto

        for name in ("FetchedDocument", "FetchError", "FetchResult", "SourceFetcher"):
            assert hasattr(proto, name), f"{name!r} not found in owlbear_knowledge.protocols"
            assert name in proto.__all__, f"{name!r} not listed in owlbear_knowledge.protocols.__all__"


# ---------------------------------------------------------------------------
# AC7 — Module import constraints
# ---------------------------------------------------------------------------


class TestFetcherModuleImports:
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
            assert pattern not in source, f"fetcher.py contains forbidden import: {pattern!r}"

    def test_fetcher_module_imports_only_from_allowlist(self) -> None:
        """AC7: Every import in fetcher.py must come from stdlib roots, pydantic, or the 3 knowledge paths."""
        import ast
        import owlbear_knowledge.protocols.fetcher as fetcher_mod

        source = inspect.getsource(fetcher_mod)
        tree = ast.parse(source)

        # Exact knowledge module paths allowed
        allowed_knowledge_modules = {
            "owlbear_knowledge.protocols.common",
            "owlbear_knowledge.protocols.sources",
            "owlbear_knowledge.cancellation",
        }
        # Allowed top-level package roots (stdlib + pydantic)
        allowed_roots = {"__future__", "typing", "pydantic"}

        def _is_allowed(module_name: str) -> bool:
            root = module_name.split(".", maxsplit=1)[0]
            if root in allowed_roots:
                return True
            if "owlbear_knowledge" in module_name:
                return module_name in allowed_knowledge_modules
            return False

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert _is_allowed(module), (
                    f"fetcher.py has disallowed import: 'from {module} import ...'. "
                    f"Allowed roots: {sorted(allowed_roots)}, "
                    f"knowledge paths: {sorted(allowed_knowledge_modules)}"
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert _is_allowed(alias.name), (
                        f"fetcher.py has disallowed import: 'import {alias.name}'. "
                        f"Allowed roots: {sorted(allowed_roots)}, "
                        f"knowledge paths: {sorted(allowed_knowledge_modules)}"
                    )
