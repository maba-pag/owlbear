"""Failing tests for task #1578: Repair manifest loader for pilot knowledge corpus.

TDD RED phase — all tests fail until the builder makes four targeted repairs:
  1. Pass scope=entry.scope to KnowledgeSource() in load_manifest_file (loader.py L170)
  2. Pass source_id=source.id to pipeline.ingest() in load_manifest_file (loader.py L198)
  3. Replace stale glob paths in store/knowledge/general/sources.yaml
  4. Use QdrantVectorStore(location=qdrant_path) in main() (loader.py L260)

Covers:
  AC-1: load_manifest_file creates source row with correct scope + ingest receives source_id
  AC-2: sources.yaml glob paths resolve against current repo layout
  AC-3: search result source field is non-null with name after source_id is linked
  AC-4: CLI main() constructs QdrantVectorStore with persistent location from env var
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.extractor import EntityExtractor
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.loader import LoadSummary, load_manifest_file, main, parse_manifest

from owlbear_knowledge.query_service import KnowledgeQueryService
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """In-memory SQLite connection with schema initialised; thread-safe for asyncio.to_thread."""
    c = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(c)
    return c


@pytest.fixture()
def mock_vs() -> MagicMock:
    """Mock vector store — avoids Qdrant dependency in unit tests."""
    vs = MagicMock()
    vs.store_embedding = MagicMock()
    vs.search_similar = MagicMock(return_value=[])
    return vs


@pytest.fixture()
def mock_emb() -> MagicMock:
    """Mock embedder — returns stub embeddings without loading a model."""
    emb = MagicMock()
    emb.embed = MagicMock(return_value=[[0.1] * 10])
    return emb


@pytest.fixture()
def real_pipeline(
    conn: sqlite3.Connection, mock_vs: MagicMock, mock_emb: MagicMock
) -> dict:
    """Real pipeline components wired with mock vector/embedding."""
    graph_store = GraphStore(conn)
    source_store = KnowledgeSourceStore(conn)
    doc_store = DocumentStore(conn, graph_store, mock_vs, mock_emb)
    chunker = TextChunker()
    extractor = EntityExtractor()
    pipeline = IngestPipeline(doc_store, extractor, chunker)
    return {
        "conn": conn,
        "graph_store": graph_store,
        "source_store": source_store,
        "doc_store": doc_store,
        "pipeline": pipeline,
    }


def _write_single_source_manifest(
    path: Path, *, name: str = "Test Source", glob: str = "*.md", scope: str = "my-scope"
) -> None:
    """Write a minimal single-source file_glob manifest to *path*."""
    path.write_text(
        f'sources:\n'
        f'  - name: "{name}"\n'
        f'    type: file_glob\n'
        f'    config:\n'
        f'      glob: "{glob}"\n'
        f'    scope: "{scope}"\n'
    )


def _stub_ingest_result() -> MagicMock:
    """Return a mock IngestResult with status='ok'."""
    r = MagicMock()
    r.status = "ok"
    return r


# ---------------------------------------------------------------------------
# TestFromAC_ManifestLoaderSourceId  (AC-1)
# ---------------------------------------------------------------------------


class TestFromAC_ManifestLoaderSourceId:
    """AC-1: load_manifest_file must create source row with scope and pass source_id to ingest."""

    @pytest.mark.asyncio
    async def test_source_row_created_with_scope_from_manifest(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """KnowledgeSource row must carry the scope declared in the manifest entry.

        Fails because load_manifest_file creates KnowledgeSource without scope=entry.scope,
        so the DB row gets the default scope='global' even when the manifest says 'my-scope'.
        """
        (tmp_path / "doc.md").write_text("# Title\n\nContent paragraph for chunking.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, scope="my-scope")

        source_store = KnowledgeSourceStore(conn)
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_stub_ingest_result())

        await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        sources = source_store.list_all()
        assert len(sources) == 1, "Exactly one source should have been created"
        assert sources[0].scope == "my-scope", (
            f"Source scope must be 'my-scope' (from manifest), got {sources[0].scope!r}; "
            "loader must pass scope=entry.scope to KnowledgeSource()"
        )

    @pytest.mark.asyncio
    async def test_source_row_scope_not_overridden_to_global(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """Non-global scope must not silently revert to 'global'.

        Fails because the KnowledgeSource default is scope='global' and the
        loader does not override it with the manifest entry's scope.
        """
        (tmp_path / "doc.md").write_text("Some document content here.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, scope="pilot")

        source_store = KnowledgeSourceStore(conn)
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_stub_ingest_result())

        await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        sources = source_store.list_all()
        assert sources, "No source was created"
        assert sources[0].scope != "global", (
            "scope must not be 'global' when manifest declares a different scope; "
            "loader must forward entry.scope to KnowledgeSource()"
        )

    @pytest.mark.asyncio
    async def test_ingest_receives_source_id_kwarg(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """pipeline.ingest() must be called with source_id= equal to the created source's id.

        Fails because load_manifest_file calls pipeline.ingest(intake, scope=entry.scope)
        with no source_id argument, so the kwarg is absent (defaults to None in IngestPipeline).
        """
        (tmp_path / "a.md").write_text("Document A content.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, glob="*.md")

        source_store = KnowledgeSourceStore(conn)
        captured_kwargs: list[dict] = []

        async def capture_ingest(_intake: IntakeResult, **kwargs: object) -> MagicMock:
            captured_kwargs.append(dict(kwargs))
            return _stub_ingest_result()

        mock_pipeline = MagicMock()
        mock_pipeline.ingest = capture_ingest

        await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        assert captured_kwargs, "pipeline.ingest() was never called"
        call_kwargs = captured_kwargs[0]
        assert "source_id" in call_kwargs, (
            "pipeline.ingest() must receive source_id= keyword argument; "
            "currently load_manifest_file omits it entirely"
        )
        assert call_kwargs["source_id"] is not None, (
            "source_id passed to pipeline.ingest() must not be None"
        )

    @pytest.mark.asyncio
    async def test_ingest_source_id_matches_created_source_row(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """The source_id passed to ingest must equal the KnowledgeSource.id in the DB.

        Fails because source_id is never passed to ingest, so any captured value
        would be None while the real source row has a non-None id.
        """
        (tmp_path / "doc.md").write_text("Test content.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, name="My Source")

        source_store = KnowledgeSourceStore(conn)
        captured_source_ids: list[str | None] = []

        async def capture_ingest(_intake: IntakeResult, **kwargs: object) -> MagicMock:
            captured_source_ids.append(kwargs.get("source_id"))  # type: ignore[arg-type]
            return _stub_ingest_result()

        mock_pipeline = MagicMock()
        mock_pipeline.ingest = capture_ingest

        await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        sources = source_store.list_all()
        assert sources, "Source row must be created"
        created_source_id = sources[0].id

        assert captured_source_ids, "pipeline.ingest() was never called"
        assert captured_source_ids[0] == created_source_id, (
            f"source_id passed to ingest ({captured_source_ids[0]!r}) must equal "
            f"the created KnowledgeSource.id ({created_source_id!r})"
        )

    @pytest.mark.asyncio
    async def test_document_source_id_not_null_in_db(
        self, real_pipeline: dict, tmp_path: Path
    ) -> None:
        """Document row's source_id column must not be NULL after load_manifest_file.

        Fails because pipeline.ingest() is called without source_id= so
        DocumentStore.insert_document() receives source_id=None, which writes NULL.
        """
        (tmp_path / "content.md").write_text(
            "# Knowledge Base Entry\n\n"
            "This is a pilot document that should be linked to its source record "
            "via the source_id foreign key on the documents table.\n"
        )
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest)

        conn: sqlite3.Connection = real_pipeline["conn"]
        source_store: KnowledgeSourceStore = real_pipeline["source_store"]
        pipeline: IngestPipeline = real_pipeline["pipeline"]

        await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=pipeline,
        )

        row = conn.execute("SELECT source_id FROM documents").fetchone()
        assert row is not None, "No document row was created in the DB"
        assert row[0] is not None, (
            "documents.source_id must not be NULL — load_manifest_file must pass "
            "source_id=source.id to pipeline.ingest()"
        )

    @pytest.mark.asyncio
    async def test_document_source_id_references_existing_source_row(
        self, real_pipeline: dict, tmp_path: Path
    ) -> None:
        """documents.source_id must be a valid FK reference to knowledge_sources.id.

        Fails because source_id is NULL in the document, so no FK match exists.
        """
        (tmp_path / "article.md").write_text(
            "# Article Title\n\nEnough content for at least one chunk to be produced.\n"
        )
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, name="Pilot Source")

        conn: sqlite3.Connection = real_pipeline["conn"]
        source_store: KnowledgeSourceStore = real_pipeline["source_store"]
        pipeline: IngestPipeline = real_pipeline["pipeline"]

        await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=pipeline,
        )

        doc_row = conn.execute("SELECT source_id FROM documents").fetchone()
        assert doc_row is not None, "No document created"
        doc_source_id = doc_row[0]

        assert doc_source_id is not None, "document.source_id is NULL; expected FK reference"
        source_row = conn.execute(
            "SELECT id FROM knowledge_sources WHERE id = ?", (doc_source_id,)
        ).fetchone()
        assert source_row is not None, (
            f"document.source_id={doc_source_id!r} does not reference any "
            "knowledge_sources row — linkage is broken"
        )

    @pytest.mark.asyncio
    async def test_all_files_in_glob_receive_same_source_id(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """Every file matched by the glob must pass the same source_id to ingest.

        Fails because source_id is never passed to ingest (all calls get None).
        """
        (tmp_path / "a.md").write_text("File A content.")
        (tmp_path / "b.md").write_text("File B content.")
        (tmp_path / "c.md").write_text("File C content.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, glob="*.md")

        source_store = KnowledgeSourceStore(conn)
        per_call_source_ids: list[str | None] = []

        async def capture_ingest(_intake: IntakeResult, **kwargs: object) -> MagicMock:
            per_call_source_ids.append(kwargs.get("source_id"))  # type: ignore[arg-type]
            return _stub_ingest_result()

        mock_pipeline = MagicMock()
        mock_pipeline.ingest = capture_ingest

        await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        assert len(per_call_source_ids) == 3, (
            f"Expected 3 ingest calls (one per file), got {len(per_call_source_ids)}"
        )
        # Every call must have received a non-None, consistent source_id.
        assert all(sid is not None for sid in per_call_source_ids), (
            f"All ingest calls must receive source_id; got: {per_call_source_ids}"
        )
        assert len(set(per_call_source_ids)) == 1, (
            "All files from the same manifest source must share the same source_id; "
            f"got distinct values: {set(per_call_source_ids)}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ManifestGlobPaths  (AC-2)
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
_SOURCES_YAML = _WORKSPACE_ROOT / "store" / "knowledge" / "general" / "sources.yaml"


def _parse_sources_yaml() -> list[dict]:
    """Parse sources.yaml and return list of source dicts with {name, glob} keys."""
    from owlbear_knowledge.loader import parse_manifest  # noqa: PLC0415

    text = _SOURCES_YAML.read_text(encoding="utf-8")
    entries = parse_manifest(text)
    return [{"name": e.name, "glob": e.config.get("glob", "")} for e in entries]


class TestFromAC_ManifestGlobPaths:
    """AC-2: sources.yaml glob paths must resolve against the current repo layout."""

    def test_research_glob_resolves_to_at_least_one_file(self) -> None:
        """The 'Research docs' glob must match at least one file in the workspace.

        Fails because the current glob 'docs/research/*.md' points to a path
        that does not exist; correct path is '.owlbear/research/*.md'.
        """
        sources = _parse_sources_yaml()
        research = next((s for s in sources if "research" in s["name"].lower()), None)
        assert research is not None, "No 'Research docs' source found in sources.yaml"

        matched = list(_WORKSPACE_ROOT.glob(research["glob"]))
        assert matched, (
            f"Glob {research['glob']!r} matched no files under {_WORKSPACE_ROOT}; "
            "update sources.yaml to use the correct path (e.g. '.owlbear/research/*.md')"
        )

    def test_skills_glob_resolves_to_at_least_one_file(self) -> None:
        """The 'Skills' glob must match at least one SKILL.md file.

        Fails because the current glob 'skills/*/SKILL.md' does not exist;
        correct path is 'share/skills/*/SKILL.md'.
        """
        sources = _parse_sources_yaml()
        skills = next((s for s in sources if "skill" in s["name"].lower()), None)
        assert skills is not None, "No 'Skills' source found in sources.yaml"

        matched = list(_WORKSPACE_ROOT.glob(skills["glob"]))
        assert matched, (
            f"Glob {skills['glob']!r} matched no files under {_WORKSPACE_ROOT}; "
            "update sources.yaml to use the correct path (e.g. 'share/skills/*/SKILL.md')"
        )

    def test_instructions_glob_resolves_to_at_least_one_file(self) -> None:
        """The 'Instructions' glob must match at least one .md file.

        Fails because the current glob 'instructions/*.md' does not exist;
        correct path is 'share/instructions/*.md'.
        """
        sources = _parse_sources_yaml()
        instructions = next((s for s in sources if "instruction" in s["name"].lower()), None)
        assert instructions is not None, "No 'Instructions' source found in sources.yaml"

        matched = list(_WORKSPACE_ROOT.glob(instructions["glob"]))
        assert matched, (
            f"Glob {instructions['glob']!r} matched no files under {_WORKSPACE_ROOT}; "
            "update sources.yaml to use the correct path (e.g. 'share/instructions/*.md')"
        )

    def test_stale_glob_docs_research_not_in_sources_yaml(self) -> None:
        """The stale path 'docs/research' must not appear in any glob in sources.yaml.

        Fails because the current sources.yaml still contains 'docs/research/*.md'.
        """
        text = _SOURCES_YAML.read_text(encoding="utf-8")
        assert "docs/research" not in text, (
            "sources.yaml still contains the stale path 'docs/research'; "
            "replace with '.owlbear/research/*.md'"
        )

    def test_stale_glob_bare_skills_not_in_sources_yaml(self) -> None:
        """The stale path 'skills/*/SKILL.md' (without 'share/' prefix) must not appear.

        Fails because the current sources.yaml uses 'skills/*/SKILL.md'.
        """
        text = _SOURCES_YAML.read_text(encoding="utf-8")
        # Must not contain the bare 'skills/' path (not preceded by 'share/')
        lines = [ln.strip() for ln in text.splitlines() if "glob" in ln]
        for line in lines:
            assert not (
                "skills/" in line and "share/skills/" not in line
            ), (
                f"Found stale glob line {line!r}; expected 'share/skills/*/SKILL.md', "
                "not 'skills/*/SKILL.md'"
            )

    def test_stale_glob_bare_instructions_not_in_sources_yaml(self) -> None:
        """The stale 'instructions/*.md' path (without 'share/') must not appear.

        Fails because the current sources.yaml uses 'instructions/*.md'.
        """
        text = _SOURCES_YAML.read_text(encoding="utf-8")
        lines = [ln.strip() for ln in text.splitlines() if "glob" in ln]
        for line in lines:
            assert not (
                "instructions/" in line and "share/instructions/" not in line
            ), (
                f"Found stale glob line {line!r}; expected 'share/instructions/*.md', "
                "not 'instructions/*.md'"
            )


# ---------------------------------------------------------------------------
# TestFromAC_SearchSourceMetadata  (AC-3)
# ---------------------------------------------------------------------------


class TestFromAC_SearchSourceMetadata:
    """AC-3: search result 'source' field must be non-null with name after loader fix."""

    @pytest.mark.asyncio
    async def test_loader_ingested_doc_query_returns_source_name(
        self, real_pipeline: dict, tmp_path: Path
    ) -> None:
        """After load_manifest_file, querying the document must return source.name.

        Full integration chain:
          load_manifest_file → IngestPipeline.ingest() → document in DB
          → KnowledgeQueryService.query() → StructuredSearchResult.source.name

        Fails because load_manifest_file omits source_id= from pipeline.ingest(),
        so the document has source_id=NULL → query_service sets source=None
        → result.source is None → name check fails.
        """
        content_file = tmp_path / "pilot.md"
        content_file.write_text(
            "# Pilot Document\n\n"
            "This file is part of the pilot knowledge corpus. "
            "It contains enough text that the chunker produces at least one chunk, "
            "allowing the query service to find it via the mocked vector search.\n"
        )
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, name="Pilot Source", scope="pilot")

        conn: sqlite3.Connection = real_pipeline["conn"]
        graph_store: GraphStore = real_pipeline["graph_store"]
        source_store: KnowledgeSourceStore = real_pipeline["source_store"]
        pipeline: IngestPipeline = real_pipeline["pipeline"]
        mock_emb: MagicMock = real_pipeline["doc_store"]._embedder  # type: ignore[attr-defined]

        await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=pipeline,
        )

        # Retrieve the first chunk_id from the DB to feed to the mock vector search.
        chunk_row = conn.execute("SELECT id FROM chunks LIMIT 1").fetchone()
        assert chunk_row is not None, "No chunks were created after load_manifest_file"
        chunk_id = chunk_row[0]

        # Wire a mock vector store for the query service that returns our chunk.
        query_mock_vs = MagicMock()
        query_mock_vs.search_similar = MagicMock(return_value=[(chunk_id, 0.95)])
        mock_emb.embed = MagicMock(return_value=[[0.1] * 10])

        qs = KnowledgeQueryService(
            vector_store=query_mock_vs,
            graph_store=graph_store,
            embedding_provider=mock_emb,
            source_store=source_store,
            similarity_threshold=0.0,
        )

        results = await qs.query("pilot document", top_k=1)
        assert results, "Query returned no results"

        result = results[0]
        assert result.source is not None, (
            "StructuredSearchResult.source must not be None when document has source_id set; "
            "currently documents.source_id=NULL because load_manifest_file omits source_id="
        )
        assert result.source.name == "Pilot Source", (  # type: ignore[union-attr]
            f"result.source.name must be 'Pilot Source', got {getattr(result.source, 'name', None)!r}; "
            "source_id linkage is broken"
        )

    @pytest.mark.asyncio
    async def test_document_with_null_source_id_gives_empty_source_name(
        self, real_pipeline: dict, tmp_path: Path
    ) -> None:
        """Regression: documents with source_id=NULL yield source.name='' in search results.

        This is the CURRENT (broken) behaviour that AC-3 is fixing. The test
        demonstrates the breakage: after the buggy load_manifest_file, searching
        returns a result whose source.name is empty (because source_id=NULL →
        source_store.get(None) is skipped → source=None → _serialize_source(None)
        returns name='').

        Fails as a contract test: asserts name != '' to prove linkage works, but
        currently name='' because source_id is NULL on the document.
        """
        (tmp_path / "doc.md").write_text(
            "# Linked Document\n\nText to produce a chunk for searching.\n"
        )
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, name="Corpus Source", scope="corpus")

        conn: sqlite3.Connection = real_pipeline["conn"]
        graph_store: GraphStore = real_pipeline["graph_store"]
        source_store: KnowledgeSourceStore = real_pipeline["source_store"]
        pipeline: IngestPipeline = real_pipeline["pipeline"]
        mock_emb: MagicMock = real_pipeline["doc_store"]._embedder  # type: ignore[attr-defined]

        await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=pipeline,
        )

        chunk_row = conn.execute("SELECT id FROM chunks LIMIT 1").fetchone()
        assert chunk_row is not None, "No chunks created"
        chunk_id = chunk_row[0]

        query_vs = MagicMock()
        query_vs.search_similar = MagicMock(return_value=[(chunk_id, 0.9)])
        mock_emb.embed = MagicMock(return_value=[[0.2] * 10])

        qs = KnowledgeQueryService(
            vector_store=query_vs,
            graph_store=graph_store,
            embedding_provider=mock_emb,
            source_store=source_store,
            similarity_threshold=0.0,
        )

        results = await qs.query("corpus source", top_k=1)
        assert results, "Query returned no results"

        result = results[0]
        # After the fix, source.name must be "Corpus Source", not "".
        source_name = getattr(result.source, "name", None) if result.source else ""
        assert source_name == "Corpus Source", (
            f"result.source.name must equal the source row name 'Corpus Source', "
            f"got {source_name!r}; document.source_id is NULL because "
            "load_manifest_file does not forward source_id= to pipeline.ingest()"
        )


# ---------------------------------------------------------------------------
# TestFromAC_LoaderCliVectorPath  (AC-4)
# ---------------------------------------------------------------------------


class TestFromAC_LoaderCliVectorPath:
    """AC-4: main() must use QdrantVectorStore(location=...) with env var or default."""

    def test_main_uses_owlbear_qdrant_path_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """QdrantVectorStore must be called with location= from OWLBEAR_QDRANT_PATH.

        Fails because main() calls QdrantVectorStore() without any location= argument,
        defaulting to ':memory:' instead of the configured persistent path.
        """
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("sources:\n")  # No sources — returns immediately.

        qdrant_path = str(tmp_path / "my_vectors")
        monkeypatch.setenv("OWLBEAR_QDRANT_PATH", qdrant_path)
        monkeypatch.setenv("OWLBEAR_KB_PATH", str(tmp_path / "local.db"))

        with patch("owlbear_knowledge.qdrant.QdrantVectorStore") as mock_qdrant:
            main(["--manifest", str(manifest), "--root", str(tmp_path)])

        mock_qdrant.assert_called_once()
        call_kwargs = mock_qdrant.call_args
        actual_location = call_kwargs.kwargs.get("location") or (
            call_kwargs.args[0] if call_kwargs.args else None
        )
        assert actual_location == qdrant_path, (
            f"QdrantVectorStore must be called with location={qdrant_path!r}; "
            f"got location={actual_location!r}; main() uses QdrantVectorStore() without location="
        )

    def test_main_uses_default_qdrant_path_when_no_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without OWLBEAR_QDRANT_PATH, main() must use '.owlbear/knowledge/vectors'.

        Fails because main() calls QdrantVectorStore() with no arguments, which
        defaults the client to ':memory:' — not the persistent path.
        """
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("sources:\n")

        monkeypatch.delenv("OWLBEAR_QDRANT_PATH", raising=False)
        monkeypatch.setenv("OWLBEAR_KB_PATH", str(tmp_path / "local.db"))

        expected_default = ".owlbear/knowledge/vectors"

        with patch("owlbear_knowledge.qdrant.QdrantVectorStore") as mock_qdrant:
            main(["--manifest", str(manifest), "--root", str(tmp_path)])

        mock_qdrant.assert_called_once()
        call_kwargs = mock_qdrant.call_args
        actual_location = call_kwargs.kwargs.get("location") or (
            call_kwargs.args[0] if call_kwargs.args else None
        )
        assert actual_location == expected_default, (
            f"QdrantVectorStore must be called with location='{expected_default}'; "
            f"got location={actual_location!r}"
        )

    def test_main_qdrant_location_matches_mcp_server_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The default Qdrant path in main() must match _DEFAULT_QDRANT_PATH in server.py.

        Fails because main() does not pass location= to QdrantVectorStore() at all,
        while server.py uses os.environ.get('OWLBEAR_QDRANT_PATH', '.owlbear/knowledge/vectors').
        """
        from owlbear_mcp_knowledge import server as _mcp_server  # noqa: PLC0415
        server_default = _mcp_server._DEFAULT_QDRANT_PATH

        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("sources:\n")

        monkeypatch.delenv("OWLBEAR_QDRANT_PATH", raising=False)
        monkeypatch.setenv("OWLBEAR_KB_PATH", str(tmp_path / "local.db"))

        with patch("owlbear_knowledge.qdrant.QdrantVectorStore") as mock_qdrant:
            main(["--manifest", str(manifest), "--root", str(tmp_path)])

        call_kwargs = mock_qdrant.call_args
        actual_location = call_kwargs.kwargs.get("location") or (
            call_kwargs.args[0] if call_kwargs.args else None
        )
        assert actual_location == server_default, (
            f"loader main() default Qdrant path must match server.py _DEFAULT_QDRANT_PATH "
            f"({server_default!r}); got {actual_location!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ParseManifestBranches  (coverage expansion — parse_manifest paths)
# ---------------------------------------------------------------------------


class TestFromAC_ParseManifestBranches:
    """Coverage for parse_manifest branches not exercised by the primary AC tests."""

    def test_null_sources_field_returns_empty_list(self) -> None:
        """parse_manifest('sources:\\n') with a null sources field returns []."""
        result = parse_manifest("sources:\n")
        assert result == []

    def test_inline_empty_sequence_normalised_to_empty_list(self) -> None:
        """parse_manifest('sources: []') normalises via regex and returns []."""
        result = parse_manifest("sources: []\n")
        assert result == []

    def test_invalid_type_enum_raises_yaml_validation_error(self) -> None:
        """An unknown 'type' value in the manifest raises YAMLValidationError."""
        import strictyaml as sy  # noqa: PLC0415

        yaml_text = (
            "sources:\n"
            "  - name: Bad Source\n"
            "    type: totally_wrong\n"
            "    config:\n"
            "      glob: '*.md'\n"
        )
        with pytest.raises(sy.YAMLValidationError):
            parse_manifest(yaml_text)

    def test_disabled_entry_parsed_with_enabled_false(self) -> None:
        """An entry with 'enabled: false' produces ManifestEntry.enabled=False."""
        entries = parse_manifest(
            "sources:\n"
            "  - name: Disabled Source\n"
            "    type: file_glob\n"
            "    config:\n"
            "      glob: '*.md'\n"
            "    enabled: false\n"
        )
        assert len(entries) == 1
        assert entries[0].enabled is False

    def test_entry_without_scope_defaults_to_global(self) -> None:
        """An entry without a 'scope' key defaults to ManifestEntry.scope='global'."""
        entries = parse_manifest(
            "sources:\n"
            "  - name: No Scope\n"
            "    type: file_glob\n"
            "    config:\n"
            "      glob: '*.md'\n"
        )
        assert len(entries) == 1
        assert entries[0].scope == "global"

    def test_non_yaml_error_wrapped_as_yaml_validation_error(self) -> None:
        """A non-YAMLValidationError from sy.load is caught and re-raised as YAMLValidationError."""
        import strictyaml as sy  # noqa: PLC0415

        with (
            patch("strictyaml.load", side_effect=RuntimeError("unexpected boom")),
            pytest.raises(sy.YAMLValidationError),
        ):
            parse_manifest("sources:\n")


# ---------------------------------------------------------------------------
# TestFromAC_LoaderBranchCoverage  (coverage expansion — load_manifest_file paths)
# ---------------------------------------------------------------------------


class TestFromAC_LoaderBranchCoverage:
    """Coverage for load_manifest_file branches not hit by the primary AC tests."""

    @pytest.mark.asyncio
    async def test_disabled_source_entry_not_ingested(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A source entry with enabled=false must not call pipeline.ingest()."""
        (tmp_path / "doc.md").write_text("Some content.")
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(
            "sources:\n"
            "  - name: Disabled\n"
            "    type: file_glob\n"
            "    config:\n"
            '      glob: "*.md"\n'
            "    enabled: false\n"
        )
        source_store = KnowledgeSourceStore(conn)
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_stub_ingest_result())

        summary = await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        mock_pipeline.ingest.assert_not_called()
        assert summary.ingested == 0

    @pytest.mark.asyncio
    async def test_glob_matching_no_files_skips_ingest(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """When a glob matches no files, no ingest call is made and counters stay zero."""
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, glob="*.nonexistent_extension")
        source_store = KnowledgeSourceStore(conn)
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_stub_ingest_result())

        summary = await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        mock_pipeline.ingest.assert_not_called()
        assert summary.ingested == 0
        assert summary.failed == 0

    @pytest.mark.asyncio
    async def test_skipped_status_increments_summary_skipped(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """result.status == 'skipped' increments summary.skipped, not summary.ingested."""
        (tmp_path / "doc.md").write_text("Content.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, glob="*.md")

        source_store = KnowledgeSourceStore(conn)
        skipped_result = MagicMock()
        skipped_result.status = "skipped"
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=skipped_result)

        summary = await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        assert summary.skipped == 1
        assert summary.ingested == 0
        assert summary.failed == 0

    @pytest.mark.asyncio
    async def test_failed_status_increments_summary_failed(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """result.status == 'failed' increments summary.failed (not ingested or skipped)."""
        (tmp_path / "doc.md").write_text("Content.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, glob="*.md")

        source_store = KnowledgeSourceStore(conn)
        failed_result = MagicMock()
        failed_result.status = "failed"
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=failed_result)

        summary = await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        assert summary.failed == 1
        assert summary.ingested == 0
        assert summary.skipped == 0

    @pytest.mark.asyncio
    async def test_ingest_exception_increments_failed(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """An exception raised by pipeline.ingest() increments summary.failed."""
        (tmp_path / "doc.md").write_text("Content.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, glob="*.md")

        source_store = KnowledgeSourceStore(conn)
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(side_effect=RuntimeError("ingest error"))

        summary = await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        assert summary.failed == 1
        assert summary.ingested == 0

    @pytest.mark.asyncio
    async def test_all_files_failed_sets_all_source_ok_false(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """When every file in a source fails, summary.all_source_ok becomes False."""
        (tmp_path / "a.md").write_text("File A.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, glob="*.md")

        source_store = KnowledgeSourceStore(conn)
        failed_result = MagicMock()
        failed_result.status = "failed"
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=failed_result)

        summary = await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        assert summary.all_source_ok is False

    @pytest.mark.asyncio
    async def test_partial_failure_preserves_all_source_ok_true(
        self, conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """When only some files fail (not all), all_source_ok remains True."""
        (tmp_path / "ok.md").write_text("OK content.")
        (tmp_path / "fail.md").write_text("Fail content.")
        manifest = tmp_path / "manifest.yaml"
        _write_single_source_manifest(manifest, glob="*.md")

        source_store = KnowledgeSourceStore(conn)
        ok_result = _stub_ingest_result()
        failed_result = MagicMock()
        failed_result.status = "failed"
        call_count = 0

        async def alternate_ingest(_intake: object, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return ok_result if call_count % 2 == 1 else failed_result

        mock_pipeline = MagicMock()
        mock_pipeline.ingest = alternate_ingest

        summary = await load_manifest_file(
            manifest_path=manifest,
            workspace_root=tmp_path,
            source_store=source_store,
            pipeline=mock_pipeline,
        )

        assert summary.all_source_ok is True


# ---------------------------------------------------------------------------
# TestFromAC_MainCliExitCode  (coverage expansion — main() return value paths)
# ---------------------------------------------------------------------------


class TestFromAC_MainCliExitCode:
    """Coverage for main() return-code paths (0 and 1)."""

    def test_main_returns_one_when_all_source_ok_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() returns exit code 1 when summary.all_source_ok is False."""
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("sources:\n")
        monkeypatch.setenv("OWLBEAR_KB_PATH", str(tmp_path / "local.db"))
        monkeypatch.delenv("OWLBEAR_QDRANT_PATH", raising=False)

        async def _fake_load(*_args: object, **_kwargs: object) -> LoadSummary:
            return LoadSummary(all_source_ok=False)

        with (
            patch("owlbear_knowledge.loader.load_manifest_file", side_effect=_fake_load),
            patch("owlbear_knowledge.qdrant.QdrantVectorStore"),
            patch("owlbear_knowledge.embeddings.BgeM3EmbeddingProvider"),
        ):
            result = main(["--manifest", str(manifest)])

        assert result == 1

    def test_main_returns_zero_when_all_source_ok_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() returns exit code 0 when summary.all_source_ok is True."""
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("sources:\n")
        monkeypatch.setenv("OWLBEAR_KB_PATH", str(tmp_path / "local.db"))
        monkeypatch.delenv("OWLBEAR_QDRANT_PATH", raising=False)

        async def _fake_load(*_args: object, **_kwargs: object) -> LoadSummary:
            return LoadSummary(all_source_ok=True)

        with (
            patch("owlbear_knowledge.loader.load_manifest_file", side_effect=_fake_load),
            patch("owlbear_knowledge.qdrant.QdrantVectorStore"),
            patch("owlbear_knowledge.embeddings.BgeM3EmbeddingProvider"),
        ):
            result = main(["--manifest", str(manifest)])

        assert result == 0
