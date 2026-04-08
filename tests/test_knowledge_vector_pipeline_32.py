"""Contract tests for vector store + embedding pipeline extraction (#32).

Complements the detailed unit tests shipped in task #151:
  packages/knowledge/tests/test_qdrant_vector_store.py
  packages/knowledge/tests/test_embedding_provider.py

AC lines covered here:
  AC1 — QdrantVectorStore implements VectorStoreProtocol (isinstance)
  AC2 — __init__ accepts :memory:, filesystem path, and HTTP/HTTPS URL
  AC3 — BgeM3EmbeddingProvider implements EmbeddingProvider (isinstance)
  AC4 — configurable idle_timeout; idle unload fires after timeout
  AC5 — Zero PydanticAI / daemon imports in qdrant.py and embeddings.py
  AC6 — qdrant-client>=1.9.0 in qdrant; FlagEmbedding>=1.2.0 in embedding
  AC7 — protocol.py defines VectorStoreProtocol, HybridEmbedding,
         SparseVector, and Embedding alias
"""

from __future__ import annotations

import ast
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Module-level guards
# ---------------------------------------------------------------------------

try:
    import qdrant_client as _qdrant_client  # noqa: F401

    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False

_KNOWLEDGE_SRC = (
    Path(__file__).parent.parent
    / "serve"
    / "knowledge"
    / "src"
    / "owlbear_knowledge"
)
_PYPROJECT = (
    Path(__file__).parent.parent / "serve" / "knowledge" / "pyproject.toml"
)

_DENSE_DIM = 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flag_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Inject a lightweight FlagEmbedding mock for the life of the test."""
    dense_mock = MagicMock()
    dense_mock.tolist.return_value = [0.1] * _DENSE_DIM

    fake_model = MagicMock()
    fake_model.encode.return_value = {"dense_vecs": [dense_mock]}

    fake_module = MagicMock()
    fake_module.BGEM3FlagModel.return_value = fake_model

    monkeypatch.setitem(sys.modules, "FlagEmbedding", fake_module)
    return fake_model


# ===========================================================================
# AC7 — protocol.py defines all four required types
# ===========================================================================


class TestFromAC_ProtocolDefinitions:
    """All four protocol types are importable from owlbear_knowledge.protocol."""

    def test_vector_store_protocol_importable(self) -> None:
        """VectorStoreProtocol is importable from owlbear_knowledge.protocol."""
        from owlbear_knowledge.protocol import VectorStoreProtocol  # noqa: PLC0415

        assert VectorStoreProtocol is not None

    def test_hybrid_embedding_importable(self) -> None:
        """HybridEmbedding is importable from owlbear_knowledge.protocol."""
        from owlbear_knowledge.protocol import HybridEmbedding  # noqa: PLC0415

        assert HybridEmbedding is not None

    def test_sparse_vector_importable(self) -> None:
        """SparseVector is importable from owlbear_knowledge.protocol."""
        from owlbear_knowledge.protocol import SparseVector  # noqa: PLC0415

        assert SparseVector is not None

    def test_embedding_alias_importable(self) -> None:
        """Embedding type alias is importable from owlbear_knowledge.protocol."""
        from owlbear_knowledge.protocol import Embedding  # noqa: PLC0415

        assert Embedding is not None

    def test_vector_store_protocol_is_runtime_checkable(self) -> None:
        """A class with the correct methods satisfies VectorStoreProtocol at runtime."""
        from owlbear_knowledge.protocol import VectorStoreProtocol  # noqa: PLC0415

        class _Stub:
            def store_embedding(self, entity_or_doc_id, embedding, embedding_type, scope="global") -> None: ...  # noqa: ANN001
            def get_embedding(self, entity_or_doc_id) -> list[float] | None: ...  # noqa: ANN001
            def search_similar(self, query_embedding, top_k=5, embedding_type=None, *, scopes=None, recency_weight=0.0, decay_rate=0.001) -> list[tuple[str, float]]: ...  # noqa: ANN001, PLR0913
            def delete_embedding(self, entity_or_doc_id) -> bool: ...  # noqa: ANN001

        assert isinstance(_Stub(), VectorStoreProtocol)


# ===========================================================================
# AC1 — QdrantVectorStore implements VectorStoreProtocol
# ===========================================================================


@pytest.mark.skipif(not _QDRANT_AVAILABLE, reason="qdrant-client not installed")
class TestFromAC_QdrantProtocolConformance:
    """QdrantVectorStore is a runtime-conformant VectorStoreProtocol."""

    def test_isinstance_vector_store_protocol(self) -> None:
        """isinstance(QdrantVectorStore(":memory:"), VectorStoreProtocol) is True."""
        from owlbear_knowledge.protocol import VectorStoreProtocol  # noqa: PLC0415
        from owlbear_knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415

        store = QdrantVectorStore(":memory:")
        assert isinstance(store, VectorStoreProtocol)

    def test_has_all_four_protocol_methods(self) -> None:
        """QdrantVectorStore exposes all four methods of VectorStoreProtocol."""
        from owlbear_knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415

        for method in ("store_embedding", "get_embedding", "search_similar", "delete_embedding"):
            assert callable(getattr(QdrantVectorStore, method, None)), (
                f"missing method: {method}"
            )


# ===========================================================================
# AC2 — __init__ accepts :memory:, filesystem path, and HTTP/HTTPS URL
# ===========================================================================


@pytest.mark.skipif(not _QDRANT_AVAILABLE, reason="qdrant-client not installed")
class TestFromAC_QdrantInitModes:
    """QdrantVectorStore constructor accepts all three location signatures."""

    def test_memory_mode_constructs_without_error(self) -> None:
        """:memory: mode creates an in-memory store without raising."""
        from owlbear_knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415

        store = QdrantVectorStore(":memory:")
        assert store is not None

    def test_http_url_routes_to_location_kwarg(self) -> None:
        """http:// URL passes QdrantClient the 'location' kwarg, not 'path'."""
        from owlbear_knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415

        with patch("owlbear_knowledge.qdrant.QdrantClient") as mock_client:
            QdrantVectorStore("http://localhost:6333")
            kwargs = mock_client.call_args.kwargs
            assert kwargs.get("location") == "http://localhost:6333"
            assert "path" not in kwargs

    def test_https_url_routes_to_location_kwarg(self) -> None:
        """https:// URL passes QdrantClient the 'location' kwarg, not 'path'."""
        from owlbear_knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415

        with patch("owlbear_knowledge.qdrant.QdrantClient") as mock_client:
            QdrantVectorStore("https://cloud.qdrant.io:443")
            kwargs = mock_client.call_args.kwargs
            assert kwargs.get("location") == "https://cloud.qdrant.io:443"
            assert "path" not in kwargs

    def test_filesystem_path_routes_to_path_kwarg(self, tmp_path: Path) -> None:
        """A filesystem path passes QdrantClient the 'path' kwarg, not 'location'."""
        from owlbear_knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415

        db_path = str(tmp_path / "qdrant_db")
        with patch("owlbear_knowledge.qdrant.QdrantClient") as mock_client:
            QdrantVectorStore(db_path)
            kwargs = mock_client.call_args.kwargs
            assert kwargs.get("path") == db_path
            assert "location" not in kwargs

    def test_filesystem_path_store_retrieve_roundtrip(self, tmp_path: Path) -> None:
        """Filesystem path: embedding stored and retrieved from an on-disk collection."""
        from owlbear_knowledge.qdrant import DENSE_DIM, QdrantVectorStore  # noqa: PLC0415

        db_path = str(tmp_path / "qdrant_db")
        vec = [0.5] * DENSE_DIM
        store = QdrantVectorStore(db_path)
        store.store_embedding("doc-fs", vec, "document")
        result = store.get_embedding("doc-fs")
        assert result is not None
        assert len(result) == DENSE_DIM

    def test_search_with_hybrid_query_extracts_dense_component(self) -> None:
        """search_similar accepts a HybridEmbedding query; only the dense part is used."""
        from owlbear_knowledge.protocol import HybridEmbedding, SparseVector  # noqa: PLC0415
        from owlbear_knowledge.qdrant import DENSE_DIM, QdrantVectorStore  # noqa: PLC0415

        store = QdrantVectorStore(":memory:")
        dense = [0.3] * DENSE_DIM
        store.store_embedding("ent1", dense, "entity")
        query = HybridEmbedding(
            dense=dense,
            sparse=SparseVector(indices=[0, 1], values=[0.5, 0.5]),
        )
        results = store.search_similar(query, top_k=1)
        assert len(results) == 1
        assert results[0][0] == "ent1"


# ===========================================================================
# AC3 — BgeM3EmbeddingProvider implements EmbeddingProvider
# ===========================================================================


class TestFromAC_BgeM3ProtocolConformance:
    """BgeM3EmbeddingProvider is a runtime-conformant EmbeddingProvider."""

    def test_isinstance_embedding_provider(self) -> None:
        """isinstance(BgeM3EmbeddingProvider(), EmbeddingProvider) is True."""
        from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider, EmbeddingProvider  # noqa: PLC0415

        provider = BgeM3EmbeddingProvider()
        assert isinstance(provider, EmbeddingProvider)

    def test_embedding_provider_protocol_is_runtime_checkable(self) -> None:
        """Any object with embed(list[str])->list[list[float]] satisfies EmbeddingProvider."""
        from owlbear_knowledge.embeddings import EmbeddingProvider  # noqa: PLC0415

        class _Stub:
            def embed(self, texts: list[str]) -> list[list[float]]:
                return [[0.0]] * len(texts)

        assert isinstance(_Stub(), EmbeddingProvider)

    def test_bge_m3_embed_method_is_callable(self) -> None:
        """BgeM3EmbeddingProvider.embed is a callable method."""
        from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider  # noqa: PLC0415

        assert callable(BgeM3EmbeddingProvider.embed)


# ===========================================================================
# AC4 — lazy loading + configurable idle_timeout
# ===========================================================================


class TestFromAC_BgeM3IdleTimeout:
    """BgeM3EmbeddingProvider: configurable idle_timeout; idle unload fires."""

    def test_default_idle_timeout_is_600s(self) -> None:
        """Default idle_timeout is 600.0 seconds."""
        from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider  # noqa: PLC0415

        assert BgeM3EmbeddingProvider().idle_timeout == 600.0

    def test_idle_timeout_is_configurable(self) -> None:
        """idle_timeout set via constructor is stored on the instance."""
        from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider  # noqa: PLC0415

        assert BgeM3EmbeddingProvider(idle_timeout=120.0).idle_timeout == 120.0
        assert BgeM3EmbeddingProvider(idle_timeout=0.0).idle_timeout == 0.0

    def test_idle_timeout_zero_no_timer_after_embed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """idle_timeout=0 means no auto-unload timer is ever scheduled."""
        from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider  # noqa: PLC0415

        _make_flag_mock(monkeypatch)
        provider = BgeM3EmbeddingProvider(idle_timeout=0)
        provider.embed(["hello"])
        assert provider._timer is None  # noqa: SLF001

    def test_idle_unload_fires_and_clears_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After idle_timeout seconds, the model reference is cleared to None."""
        from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider  # noqa: PLC0415

        _make_flag_mock(monkeypatch)
        provider = BgeM3EmbeddingProvider(idle_timeout=0.05)  # 50 ms
        provider.embed(["trigger load"])
        assert provider._model is not None  # noqa: SLF001
        time.sleep(0.2)  # wait for the 50 ms timer to fire
        assert provider._model is None  # noqa: SLF001


# ===========================================================================
# AC5 — Zero PydanticAI / daemon imports in qdrant.py and embeddings.py
# ===========================================================================


class TestFromAC_NoPydanticAiImports:
    """qdrant.py and embeddings.py contain no pydantic_ai or daemon imports."""

    @staticmethod
    def _collect_import_modules(filepath: Path) -> list[str]:
        """Return every imported module name from a Python source file."""
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        return names

    def test_qdrant_no_pydantic_ai_import(self) -> None:
        """qdrant.py contains no 'pydantic_ai' import."""
        imports = self._collect_import_modules(_KNOWLEDGE_SRC / "qdrant.py")
        violators = [n for n in imports if "pydantic_ai" in n]
        assert not violators, f"Found pydantic_ai imports in qdrant.py: {violators}"

    def test_embeddings_no_pydantic_ai_import(self) -> None:
        """embeddings.py contains no 'pydantic_ai' import."""
        imports = self._collect_import_modules(_KNOWLEDGE_SRC / "embeddings.py")
        violators = [n for n in imports if "pydantic_ai" in n]
        assert not violators, f"Found pydantic_ai imports in embeddings.py: {violators}"

    def test_qdrant_no_daemon_import(self) -> None:
        """qdrant.py contains no 'daemon' module import."""
        imports = self._collect_import_modules(_KNOWLEDGE_SRC / "qdrant.py")
        violators = [n for n in imports if "daemon" in n.lower()]
        assert not violators, f"Found daemon imports in qdrant.py: {violators}"

    def test_embeddings_no_daemon_import(self) -> None:
        """embeddings.py contains no 'daemon' module import."""
        imports = self._collect_import_modules(_KNOWLEDGE_SRC / "embeddings.py")
        violators = [n for n in imports if "daemon" in n.lower()]
        assert not violators, f"Found daemon imports in embeddings.py: {violators}"


# ===========================================================================
# AC6 — Optional dependency version specs in pyproject.toml
# ===========================================================================


class TestFromAC_OptionalDependencies:
    """pyproject.toml declares qdrant-client>=1.9.0 and FlagEmbedding>=1.2.0."""

    @staticmethod
    def _optional_deps() -> dict[str, list[str]]:
        import tomllib  # noqa: PLC0415

        with _PYPROJECT.open("rb") as f:
            data = tomllib.load(f)
        return data["project"]["optional-dependencies"]

    def test_qdrant_optional_dep_group_exists(self) -> None:
        """[project.optional-dependencies] has a 'qdrant' key."""
        assert "qdrant" in self._optional_deps()

    def test_qdrant_client_min_version(self) -> None:
        """qdrant-client>=1.9.0 is listed under the 'qdrant' optional-dep group."""
        deps = self._optional_deps().get("qdrant", [])
        assert any("qdrant-client>=1.9.0" in dep for dep in deps), (
            f"Expected 'qdrant-client>=1.9.0' in {deps}"
        )

    def test_embedding_optional_dep_group_exists(self) -> None:
        """[project.optional-dependencies] has an 'embedding' key."""
        assert "embedding" in self._optional_deps()

    def test_flag_embedding_min_version(self) -> None:
        """FlagEmbedding>=1.2.0 is listed under the 'embedding' optional-dep group."""
        deps = self._optional_deps().get("embedding", [])
        assert any("FlagEmbedding>=1.2.0" in dep for dep in deps), (
            f"Expected 'FlagEmbedding>=1.2.0' in {deps}"
        )
