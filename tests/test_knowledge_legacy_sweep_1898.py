"""Failing tests for task #1898: Knowledge final legacy file sweep (Phase C).

All tests in this file drive the RED phase — they must fail until the builder
deletes the 13 legacy files, migrates three types, and rewrites __init__.py.
"""

from __future__ import annotations

import ast
import pathlib
import re

KNOWLEDGE_PKG = pathlib.Path("serve/knowledge/src/owlbear_knowledge")
MCP_KNOWLEDGE_PKG = pathlib.Path("serve/mcp-knowledge/src/owlbear_mcp_knowledge")
TESTS_ROOT = pathlib.Path("tests")

_LEGACY_MODULES = [
    "source_store",
    "document_store",
    "graph_store",
    "graph_builder",
    "status_store",
    "ingest",
    "query_service",
    "retrieval",
    "refresh",
    "protocol",
    "models",
    "schema",
    "extractor",
]


# ---------------------------------------------------------------------------
# AC1 — 13 legacy files deleted
# ---------------------------------------------------------------------------


class TestFromAC_LegacyFileDeletion:
    """AC1: All 13 legacy implementation files must not exist on disk."""

    def test_all_legacy_files_absent(self) -> None:
        still_present = [m for m in _LEGACY_MODULES if (KNOWLEDGE_PKG / f"{m}.py").exists()]
        assert still_present == [], f"Legacy files still present: {still_present}"

    def test_source_store_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "source_store.py").exists()

    def test_document_store_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "document_store.py").exists()

    def test_graph_store_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "graph_store.py").exists()

    def test_graph_builder_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "graph_builder.py").exists()

    def test_status_store_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "status_store.py").exists()

    def test_ingest_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "ingest.py").exists()

    def test_query_service_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "query_service.py").exists()

    def test_retrieval_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "retrieval.py").exists()

    def test_refresh_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "refresh.py").exists()

    def test_protocol_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "protocol.py").exists()

    def test_models_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "models.py").exists()

    def test_schema_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "schema.py").exists()

    def test_extractor_absent(self) -> None:
        assert not (KNOWLEDGE_PKG / "extractor.py").exists()


# ---------------------------------------------------------------------------
# AC2 — compute_content_hash inlined in stores/content.py
# ---------------------------------------------------------------------------


class TestFromAC_ComputeContentHash:
    """AC2: compute_content_hash must live in stores/content.py, not status_store."""

    def test_compute_content_hash_defined_in_stores_content_module(self) -> None:
        """compute_content_hash must be defined locally in stores.content, not imported."""
        import inspect

        from owlbear_knowledge.stores import content as _content_mod  # type: ignore[attr-defined]

        fn = getattr(_content_mod, "compute_content_hash", None)
        assert fn is not None, "compute_content_hash not found in stores.content"
        assert inspect.getmodule(fn) is _content_mod, (
            f"compute_content_hash is defined in {inspect.getmodule(fn)}, "
            "expected owlbear_knowledge.stores.content"
        )

    def test_stores_content_does_not_import_from_status_store(self) -> None:
        source = (KNOWLEDGE_PKG / "stores" / "content.py").read_text()
        assert "status_store" not in source, (
            "stores/content.py still imports from status_store"
        )

    def test_stores_content_defines_compute_content_hash(self) -> None:
        """compute_content_hash must be defined (not just imported) in stores/content.py."""
        source = (KNOWLEDGE_PKG / "stores" / "content.py").read_text()
        assert "def compute_content_hash" in source, (
            "compute_content_hash is not defined in stores/content.py"
        )


# ---------------------------------------------------------------------------
# AC3 — HybridEmbedding and SparseVector moved to embeddings.py
# ---------------------------------------------------------------------------


class TestFromAC_EmbeddingsMigration:
    """AC3: HybridEmbedding and SparseVector must be defined in embeddings.py."""

    def test_hybrid_embedding_importable_from_embeddings(self) -> None:
        from owlbear_knowledge.embeddings import HybridEmbedding  # type: ignore[attr-defined]

        assert HybridEmbedding is not None

    def test_sparse_vector_importable_from_embeddings(self) -> None:
        from owlbear_knowledge.embeddings import SparseVector  # type: ignore[attr-defined]

        assert SparseVector is not None

    def test_hybrid_embedding_is_concrete_class_not_type_alias(self) -> None:
        from owlbear_knowledge.embeddings import HybridEmbedding  # type: ignore[attr-defined]

        obj = HybridEmbedding(dense=[0.1, 0.2])
        assert obj.dense == [0.1, 0.2]

    def test_sparse_vector_is_concrete_class(self) -> None:
        from owlbear_knowledge.embeddings import SparseVector  # type: ignore[attr-defined]

        sv = SparseVector(indices=[0, 1], values=[0.5, 0.3])
        assert sv.indices == [0, 1]

    def test_qdrant_does_not_import_from_protocol(self) -> None:
        source = (KNOWLEDGE_PKG / "qdrant.py").read_text()
        assert "from owlbear_knowledge.protocol import" not in source, (
            "qdrant.py still imports from protocol.py"
        )

    def test_qdrant_imports_hybrid_embedding_from_embeddings(self) -> None:
        source = (KNOWLEDGE_PKG / "qdrant.py").read_text()
        has_absolute = "from owlbear_knowledge.embeddings import" in source
        has_relative = "from .embeddings import" in source
        assert has_absolute or has_relative, (
            "qdrant.py does not import HybridEmbedding from embeddings"
        )

    def test_embeddings_module_source_has_no_protocol_import(self) -> None:
        """embeddings.py source must not reference protocol.py at all (no TYPE_CHECKING block)."""
        source = (KNOWLEDGE_PKG / "embeddings.py").read_text()
        assert "from owlbear_knowledge.protocol import" not in source, (
            "embeddings.py still references protocol.py"
        )


# ---------------------------------------------------------------------------
# AC4 — ContentFetcher protocol moved to fetcher.py; _helpers.py updated
# ---------------------------------------------------------------------------


class TestFromAC_ContentFetcherMigration:
    """AC4: ContentFetcher must live in fetcher.py; _helpers.py imports from there."""

    def test_content_fetcher_importable_from_fetcher(self) -> None:
        from owlbear_knowledge.fetcher import ContentFetcher  # type: ignore[attr-defined]

        assert ContentFetcher is not None

    def test_content_fetcher_is_protocol_with_fetch_method(self) -> None:
        from owlbear_knowledge.fetcher import ContentFetcher  # type: ignore[attr-defined]

        assert hasattr(ContentFetcher, "fetch"), (
            "ContentFetcher in fetcher.py must declare async fetch(url) method"
        )

    def test_content_fetcher_is_runtime_checkable(self) -> None:
        from owlbear_knowledge.fetcher import ContentFetcher  # type: ignore[attr-defined]

        class _MinimalFetcher:
            async def fetch(self, url: str) -> str:  # noqa: ARG002
                return ""

        assert isinstance(_MinimalFetcher(), ContentFetcher)

    def test_helpers_does_not_import_content_fetcher_from_protocol(self) -> None:
        source = (MCP_KNOWLEDGE_PKG / "_helpers.py").read_text()
        # Must NOT import ContentFetcher from owlbear_knowledge.protocol
        assert "from owlbear_knowledge.protocol import" not in source, (
            "_helpers.py still imports from owlbear_knowledge.protocol"
        )

    def test_helpers_imports_content_fetcher_from_fetcher(self) -> None:
        source = (MCP_KNOWLEDGE_PKG / "_helpers.py").read_text()
        # ContentFetcher type annotation must come from owlbear_knowledge.fetcher specifically.
        # Use \b word boundary so HttpxContentFetcher does not produce a false match.
        has_fetcher_import = bool(
            re.search(r"from owlbear_knowledge\.fetcher import[^\n]*\bContentFetcher\b", source)
        )
        assert has_fetcher_import, (
            "_helpers.py does not import ContentFetcher from owlbear_knowledge.fetcher"
        )


# ---------------------------------------------------------------------------
# AC5 — AppContext lacks source_store and refresh_orchestrator (regression guard)
# Note: prerequisite #1911 already removed these fields. Tests are guards.
# ---------------------------------------------------------------------------


class TestFromAC_AppContextFields:
    """AC5: AppContext must not declare source_store or refresh_orchestrator fields."""

    def test_app_context_no_source_store_field(self) -> None:
        source = (MCP_KNOWLEDGE_PKG / "server.py").read_text()
        m = re.search(r"class AppContext[^:]*:(.*?)(?=\nclass |\Z)", source, re.DOTALL)
        assert m is not None, "AppContext class not found in server.py"
        class_body = m.group(1)
        # source_store_v2 is valid; bare source_store: is not
        assert not re.search(r"^\s+source_store\s*:", class_body, re.MULTILINE), (
            "AppContext still declares a source_store field"
        )

    def test_app_context_no_refresh_orchestrator_field(self) -> None:
        source = (MCP_KNOWLEDGE_PKG / "server.py").read_text()
        m = re.search(r"class AppContext[^:]*:(.*?)(?=\nclass |\Z)", source, re.DOTALL)
        assert m is not None, "AppContext class not found in server.py"
        class_body = m.group(1)
        assert not re.search(r"^\s+refresh_orchestrator\s*:", class_body, re.MULTILINE), (
            "AppContext still declares a refresh_orchestrator field"
        )


# ---------------------------------------------------------------------------
# AC6 — __init__.py exports only from protocols/ and stores/
# ---------------------------------------------------------------------------


class TestFromAC_InitExports:
    """AC6: __init__.py must only import from protocols/ and stores/ subpackages."""

    def test_init_does_not_import_any_legacy_module(self) -> None:
        source = (KNOWLEDGE_PKG / "__init__.py").read_text()
        for module in _LEGACY_MODULES:
            absolute_ref = f"from owlbear_knowledge.{module}"
            relative_ref = f"from .{module}"
            assert absolute_ref not in source, f"__init__.py still imports from {module}"
            assert relative_ref not in source, f"__init__.py still has relative import of {module}"

    def test_init_all_imports_from_protocols_or_stores(self) -> None:
        source = (KNOWLEDGE_PKG / "__init__.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module is None:
                continue
            mod = node.module
            if not mod.startswith("owlbear_knowledge."):
                # relative or standard-lib import handled separately
                continue
            suffix = mod[len("owlbear_knowledge."):]
            assert suffix.startswith(("protocols", "stores")), (
                f"__init__.py has import from non-protocols/stores module: {mod}"
            )



# ---------------------------------------------------------------------------
# AC7 — Dead test files deleted (regression guard — already done)
# ---------------------------------------------------------------------------


class TestFromAC_DeadTestFiles:
    """AC7: test_search_provenance.py and test_mcp_knowledge_lifespan_1888.py must be gone."""

    def test_test_search_provenance_absent(self) -> None:
        assert not (TESTS_ROOT / "test_search_provenance.py").exists(), (
            "test_search_provenance.py still exists"
        )

    def test_test_mcp_knowledge_lifespan_1888_absent(self) -> None:
        assert not (TESTS_ROOT / "test_mcp_knowledge_lifespan_1888.py").exists(), (
            "test_mcp_knowledge_lifespan_1888.py still exists"
        )


# ---------------------------------------------------------------------------
# AC8 — grep for stale imports returns zero hits
# ---------------------------------------------------------------------------


def _find_stale_legacy_imports(root: pathlib.Path) -> list[str]:
    """Return list of '<file>: references <module>' for any stale import found."""
    hits: list[str] = []
    for py_file in sorted(root.rglob("*.py")):
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for module in _LEGACY_MODULES:
            pattern = f"owlbear_knowledge.{module}"
            if pattern in text:
                hits.append(f"{py_file}: references owlbear_knowledge.{module}")
    return hits


class TestFromAC_StaleSweep:
    """AC8: No surviving file in serve/ or tests/ imports from deleted modules."""

    def test_no_stale_imports_in_serve(self) -> None:
        hits = _find_stale_legacy_imports(pathlib.Path("serve"))
        assert hits == [], "Stale legacy imports found in serve/:\n" + "\n".join(hits)

    def test_no_stale_imports_in_tests(self) -> None:
        hits = _find_stale_legacy_imports(pathlib.Path("tests"))
        assert hits == [], "Stale legacy imports found in tests/:\n" + "\n".join(hits)

    def test_stores_content_no_status_store_reference(self) -> None:
        """Boundary: the specific stores/content.py → status_store link must be severed."""
        source = (KNOWLEDGE_PKG / "stores" / "content.py").read_text()
        assert "owlbear_knowledge.status_store" not in source
        assert "from .status_store" not in source

    def test_qdrant_no_protocol_reference(self) -> None:
        """Boundary: qdrant.py must not reference owlbear_knowledge.protocol."""
        source = (KNOWLEDGE_PKG / "qdrant.py").read_text()
        assert "owlbear_knowledge.protocol" not in source


# ---------------------------------------------------------------------------
# AC9 — Full test suite passes (import-topology proxy)
# ---------------------------------------------------------------------------


class TestFromAC_PackageIntegrity:
    """AC9 proxy: package import must not load any deleted legacy module."""

    def test_package_import_does_not_load_legacy_modules(self) -> None:
        """After import, sys.modules must not contain any deleted legacy module."""
        import importlib
        import sys

        # Evict any cached knowledge modules
        stale_keys = [k for k in sys.modules if "owlbear_knowledge" in k]
        for k in stale_keys:
            del sys.modules[k]

        importlib.import_module("owlbear_knowledge")

        for module in _LEGACY_MODULES:
            fq = f"owlbear_knowledge.{module}"
            assert fq not in sys.modules, (
                f"Importing owlbear_knowledge loaded deleted module: {fq}"
            )

    def test_protocols_subpackage_importable(self) -> None:
        from owlbear_knowledge import protocols  # noqa: F401

    def test_stores_subpackage_importable(self) -> None:
        from owlbear_knowledge import stores  # noqa: F401
