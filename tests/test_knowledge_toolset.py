"""Tests for KnowledgeToolset — mock knowledge components.

Covers query_knowledge, ingest_document, list_knowledge_sources,
tool registration, protocol-typed constructor, and _safe_path guard.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.tools.knowledge import KnowledgeToolset

# ---------------------------------------------------------------------------
# Fixtures — mocked knowledge components
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Provide a temporary workspace directory."""
    return tmp_path


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Mock satisfying VectorStoreProtocol."""
    store = MagicMock()
    store.search_similar = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_graph_store() -> MagicMock:
    """Mock satisfying GraphStore interface."""
    store = MagicMock()
    store.list_documents = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_embedding_provider() -> MagicMock:
    """Mock satisfying EmbeddingProvider protocol."""
    provider = MagicMock()
    provider.embed = MagicMock(return_value=[[0.1, 0.2, 0.3]])
    return provider


@pytest.fixture
def mock_ingest_pipeline() -> MagicMock:
    """Mock satisfying IngestPipeline interface."""
    pipeline = MagicMock()
    pipeline.ingest = AsyncMock()
    pipeline.ingest_text = AsyncMock()
    return pipeline


@pytest.fixture
def toolset(
    workspace_root: Path,
    mock_vector_store: MagicMock,
    mock_graph_store: MagicMock,
    mock_embedding_provider: MagicMock,
    mock_ingest_pipeline: MagicMock,
) -> KnowledgeToolset:
    """Create a KnowledgeToolset with all mocked dependencies."""
    return KnowledgeToolset(
        workspace_root=workspace_root,
        vector_store=mock_vector_store,
        graph_store=mock_graph_store,
        embedding_provider=mock_embedding_provider,
        ingest_pipeline=mock_ingest_pipeline,
    )


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Verify toolset registers the expected tools."""

    def test_registers_three_tools(self, toolset: KnowledgeToolset) -> None:
        """Toolset must expose exactly 3 tools."""
        assert len(toolset.tools) == 3

    def test_tool_names(self, toolset: KnowledgeToolset) -> None:
        """Registered tools must have the expected names."""
        names = set(toolset.tools.keys())
        assert names == {"query_knowledge", "ingest_document", "list_knowledge_sources"}


# ---------------------------------------------------------------------------
# Constructor — protocol types
# ---------------------------------------------------------------------------


class TestConstructor:
    """Verify constructor accepts protocol-typed dependencies."""

    def test_accepts_protocol_types(
        self,
        workspace_root: Path,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_ingest_pipeline: MagicMock,
    ) -> None:
        """Constructor should not require concrete classes — MagicMocks suffice."""
        ts = KnowledgeToolset(
            workspace_root=workspace_root,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            ingest_pipeline=mock_ingest_pipeline,
        )
        assert ts is not None


# ---------------------------------------------------------------------------
# query_knowledge
# ---------------------------------------------------------------------------


class TestQueryKnowledge:
    """Test query_knowledge tool."""

    def test_returns_formatted_results(
        self,
        toolset: KnowledgeToolset,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """query_knowledge should format results as numbered list with title, score, content."""
        from owlbear.memory.knowledge.models import Document

        mock_embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
        mock_vector_store.search_similar.return_value = [
            ("doc-abc", 0.95),
            ("doc-xyz", 0.82),
        ]
        mock_graph_store.get_document.side_effect = lambda doc_id: {
            "doc-abc": Document(
                id="doc-abc", title="Design Doc",
                content="Design content here", scope="global",
            ),
            "doc-xyz": Document(
                id="doc-xyz", title="API Ref",
                content="API reference content", scope="global",
            ),
        }[doc_id]

        result = toolset._query_knowledge("test query", top_k=5)

        assert isinstance(result, str)
        assert "1. [Design Doc] (score: 0.95)" in result
        assert "Design content here" in result
        assert "2. [API Ref] (score: 0.82)" in result
        assert "API reference content" in result
        mock_embedding_provider.embed.assert_called_once_with(["test query"])
        mock_vector_store.search_similar.assert_called_once_with(
            [0.1, 0.2, 0.3], top_k=5, embedding_type="document"
        )

    def test_empty_results_returns_no_results_message(
        self,
        toolset: KnowledgeToolset,
        mock_vector_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """query_knowledge with no search hits returns 'No results found'."""
        mock_embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
        mock_vector_store.search_similar.return_value = []

        result = toolset._query_knowledge("empty query")

        assert result == "No results found"

    def test_query_knowledge_missing_document(
        self,
        toolset: KnowledgeToolset,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """query_knowledge skips results where graph_store.get_document() returns None."""
        mock_embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
        mock_vector_store.search_similar.return_value = [
            ("doc-gone", 0.90),
        ]
        mock_graph_store.get_document.return_value = None

        result = toolset._query_knowledge("orphan query")

        assert result == "No results found"
        mock_graph_store.get_document.assert_called_once_with("doc-gone")


# ---------------------------------------------------------------------------
# ingest_document
# ---------------------------------------------------------------------------


class TestIngestDocument:
    """Test ingest_document tool."""

    @pytest.mark.anyio
    async def test_ingest_document_text(
        self,
        toolset: KnowledgeToolset,
        mock_ingest_pipeline: MagicMock,
    ) -> None:
        """ingest_document with doc_type='text' calls IngestPipeline.ingest_text()."""
        from owlbear.memory.knowledge import IngestResult

        mock_ingest_pipeline.ingest_text.return_value = IngestResult(
            document_id="doc-123",
            chunk_count=3,
            entity_count=2,
            edge_count=1,
            status="completed",
        )

        result = await toolset._ingest_document(source="Some text content", doc_type="text")

        assert isinstance(result, str)
        assert "doc-123" in result
        mock_ingest_pipeline.ingest_text.assert_called_once_with(
            "Some text content", scope="global"
        )

    @pytest.mark.anyio
    async def test_file_source_validates_path(
        self,
        toolset: KnowledgeToolset,
        workspace_root: Path,
        mock_ingest_pipeline: MagicMock,
    ) -> None:
        """ingest_document with doc_type='file' validates path against workspace sandbox."""
        from owlbear.memory.knowledge import IngestResult

        # Create a test file in the workspace
        test_file = workspace_root / "test.txt"
        test_file.write_text("hello world", encoding="utf-8")

        mock_ingest_pipeline.ingest.return_value = IngestResult(
            document_id="doc-456",
            chunk_count=1,
            entity_count=0,
            edge_count=0,
            status="completed",
        )

        result = await toolset._ingest_document(source="test.txt", doc_type="file")

        assert isinstance(result, str)
        assert "doc-456" in result
        # Pipeline should receive the resolved Path
        call_args = mock_ingest_pipeline.ingest.call_args
        assert call_args is not None
        passed_source = call_args[0][0]
        assert Path(passed_source) == test_file

    @pytest.mark.anyio
    async def test_file_source_blocks_traversal(
        self,
        toolset: KnowledgeToolset,
    ) -> None:
        """ingest_document with doc_type='file' rejects paths outside workspace."""
        with pytest.raises(PermissionError, match="Path outside workspace"):
            await toolset._ingest_document(source="../../etc/passwd", doc_type="file")

    @pytest.mark.anyio
    async def test_ingest_document_url(
        self,
        toolset: KnowledgeToolset,
        mock_ingest_pipeline: MagicMock,
    ) -> None:
        """ingest_document with doc_type='url' delegates to ingest_pipeline.ingest()."""
        from owlbear.memory.knowledge import IngestResult

        mock_ingest_pipeline.ingest.return_value = IngestResult(
            document_id="doc-url-789",
            chunk_count=5,
            entity_count=3,
            edge_count=2,
            status="completed",
        )

        result = await toolset._ingest_document(
            source="https://example.com/doc", doc_type="url"
        )

        assert isinstance(result, str)
        assert "doc-url-789" in result
        mock_ingest_pipeline.ingest.assert_called_once_with(
            "https://example.com/doc", scope="global"
        )

    @pytest.mark.anyio
    async def test_invalid_doc_type_raises(
        self,
        toolset: KnowledgeToolset,
    ) -> None:
        """ingest_document with unknown doc_type raises ValueError."""
        with pytest.raises(ValueError, match="doc_type"):
            await toolset._ingest_document(source="data", doc_type="binary")


# ---------------------------------------------------------------------------
# list_knowledge_sources
# ---------------------------------------------------------------------------


class TestListKnowledgeSources:
    """Test list_knowledge_sources tool."""

    def test_returns_formatted_list(
        self,
        toolset: KnowledgeToolset,
        mock_graph_store: MagicMock,
    ) -> None:
        """list_knowledge_sources formats documents with scope."""
        from owlbear.memory.knowledge.models import Document

        mock_graph_store.list_documents.return_value = [
            Document(id="doc-1", title="Design Doc", content="...", scope="global"),
            Document(id="doc-2", title="API Reference", content="...", scope="project"),
        ]

        result = toolset._list_knowledge_sources()

        assert isinstance(result, str)
        assert "doc-1" in result
        assert "Design Doc" in result
        assert "(scope: global)" in result
        assert "doc-2" in result
        assert "API Reference" in result
        assert "(scope: project)" in result

    def test_empty_store_returns_no_documents_message(
        self,
        toolset: KnowledgeToolset,
        mock_graph_store: MagicMock,
    ) -> None:
        """list_knowledge_sources with no documents returns 'No documents ingested.'."""
        mock_graph_store.list_documents.return_value = []

        result = toolset._list_knowledge_sources()

        assert result == "No documents ingested."


# ---------------------------------------------------------------------------
# _safe_path
# ---------------------------------------------------------------------------


class TestSafePath:
    """Test _safe_path sandbox guard."""

    def test_blocks_traversal_outside_workspace(
        self,
        toolset: KnowledgeToolset,
    ) -> None:
        """_safe_path rejects paths that escape the workspace root."""
        with pytest.raises(PermissionError, match="Path outside workspace"):
            toolset._safe_path("../../etc/passwd")

    def test_allows_path_inside_workspace(
        self,
        toolset: KnowledgeToolset,
        workspace_root: Path,
    ) -> None:
        """_safe_path accepts and resolves paths within the workspace."""
        resolved = toolset._safe_path("subdir/file.txt")
        assert resolved == workspace_root / "subdir" / "file.txt"

    def test_blocks_null_byte_path(
        self,
        toolset: KnowledgeToolset,
    ) -> None:
        """_safe_path rejects paths containing null bytes."""
        with pytest.raises(PermissionError, match="Path outside workspace"):
            toolset._safe_path("file\x00.txt")


# ---------------------------------------------------------------------------
# Project scope filtering
# ---------------------------------------------------------------------------


class TestProjectScope:
    """Test that project_scope parameter controls query scoping."""

    def test_no_project_scope_passes_no_scopes(
        self,
        toolset: KnowledgeToolset,
        mock_vector_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Without project_scope, search_similar receives no scopes kwarg."""
        mock_embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
        mock_vector_store.search_similar.return_value = []

        toolset._query_knowledge("test query")

        mock_vector_store.search_similar.assert_called_once_with(
            [0.1, 0.2, 0.3], top_k=5, embedding_type="document",
        )

    def test_project_scope_passes_scopes_to_search(
        self,
        workspace_root: Path,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_ingest_pipeline: MagicMock,
    ) -> None:
        """With project_scope set, search_similar receives scopes=['global', 'project:{id}']."""
        ts = KnowledgeToolset(
            workspace_root=workspace_root,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            ingest_pipeline=mock_ingest_pipeline,
            project_scope="proj-abc",
        )
        mock_embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
        mock_vector_store.search_similar.return_value = []

        ts._query_knowledge("scoped query")

        mock_vector_store.search_similar.assert_called_once_with(
            [0.1, 0.2, 0.3],
            top_k=5,
            embedding_type="document",
            scopes=["global", "project:proj-abc"],
        )

    def test_project_scope_none_by_default(
        self,
        toolset: KnowledgeToolset,
    ) -> None:
        """Default project_scope is None."""
        assert toolset._scopes is None

    def test_project_scope_stored_as_scopes_list(
        self,
        workspace_root: Path,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_ingest_pipeline: MagicMock,
    ) -> None:
        """project_scope is converted to a scopes list on the instance."""
        ts = KnowledgeToolset(
            workspace_root=workspace_root,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            ingest_pipeline=mock_ingest_pipeline,
            project_scope="proj-xyz",
        )
        assert ts._scopes == ["global", "project:proj-xyz"]
