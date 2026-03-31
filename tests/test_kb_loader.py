"""RED-phase tests for KB data loader script and sources manifest (#431).

Covers all AC lines from #431:
  - AC1: Manifest parsing — valid YAML accepted; malformed YAML raises YAMLValidationError
  - AC2: Schema enforces required fields (name, type, config); unknown type values rejected
  - AC3: File glob resolution — glob expands to expected files using tmp_path
  - AC4: Empty glob returns 0 files, logged at WARNING level
  - AC5: Source registration — KnowledgeSourceStore.create() called once per entry
          with correct KnowledgeSource fields including created_at/updated_at as ISO strings
  - AC6: Ingest flow — IngestPipeline.ingest() called for each resolved file with IntakeResult
  - AC7: Delta skipping — status=skipped files counted as skipped
  - AC8: Per-file failure isolation — one failure does not stop remaining files
  - AC9: CLI --manifest flag parsed, --root defaults to cwd, missing --manifest exits non-zero
  - AC10: Exit codes — 0 on all-ok/some-skipped, non-zero when all files in any source fail

All tests must FAIL until owlbear_knowledge/loader.py is implemented.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import strictyaml

from owlbear_knowledge.ingest import IngestResult
from owlbear_knowledge.loader import LoadSummary, load_manifest_file, parse_manifest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_YAML = """\
sources:
  - name: "Test docs"
    type: file_glob
    config:
      glob: "*.md"
"""

_TWO_SOURCE_YAML = """\
sources:
  - name: "First"
    type: file_glob
    config:
      glob: "*.md"
  - name: "Second"
    type: file_glob
    config:
      glob: "*.txt"
"""


def _make_ok_result() -> IngestResult:
    return IngestResult(
        document_id="abc", chunk_count=2, entity_count=1, edge_count=0, status="ok"
    )


def _make_skipped_result() -> IngestResult:
    return IngestResult(
        document_id="abc", chunk_count=0, entity_count=0, edge_count=0, status="skipped"
    )


def _make_failed_result() -> IngestResult:
    return IngestResult(
        document_id="abc", chunk_count=0, entity_count=0, edge_count=0, status="failed"
    )


def _write_manifest(path: Path, content: str) -> Path:
    p = path / "sources.yaml"
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# AC1, AC2 — Manifest parsing and schema validation
# ---------------------------------------------------------------------------


class TestFromAC_ManifestParsing:
    """Tests for manifest YAML parsing and strictyaml schema validation."""

    def test_valid_yaml_single_source_returns_one_entry(self) -> None:
        """Valid YAML with one source returns a list of length 1."""
        entries = parse_manifest(_VALID_YAML)
        assert len(entries) == 1

    def test_valid_entry_exposes_name_type_config(self) -> None:
        """Parsed entry exposes name, type, and config dict."""
        entries = parse_manifest(_VALID_YAML)
        entry = entries[0]
        assert entry.name == "Test docs"
        assert entry.type == "file_glob"
        assert isinstance(entry.config, dict)
        assert "glob" in entry.config

    def test_valid_yaml_multiple_sources_all_returned(self) -> None:
        """Multiple manifest entries are all returned in order."""
        entries = parse_manifest(_TWO_SOURCE_YAML)
        assert len(entries) == 2
        assert entries[0].name == "First"
        assert entries[1].name == "Second"

    def test_malformed_yaml_raises_yaml_validation_error(self) -> None:
        """Completely invalid YAML raises strictyaml.YAMLValidationError."""
        with pytest.raises(strictyaml.YAMLValidationError):
            parse_manifest("sources: ][not valid yaml")

    def test_missing_name_field_raises_yaml_validation_error(self) -> None:
        """An entry without 'name' raises strictyaml.YAMLValidationError."""
        yaml = """\
sources:
  - type: file_glob
    config:
      glob: "*.md"
"""
        with pytest.raises(strictyaml.YAMLValidationError):
            parse_manifest(yaml)

    def test_missing_type_field_raises_yaml_validation_error(self) -> None:
        """An entry without 'type' raises strictyaml.YAMLValidationError."""
        yaml = """\
sources:
  - name: "Test"
    config:
      glob: "*.md"
"""
        with pytest.raises(strictyaml.YAMLValidationError):
            parse_manifest(yaml)

    def test_missing_config_field_raises_yaml_validation_error(self) -> None:
        """An entry without 'config' raises strictyaml.YAMLValidationError."""
        yaml = """\
sources:
  - name: "Test"
    type: file_glob
"""
        with pytest.raises(strictyaml.YAMLValidationError):
            parse_manifest(yaml)

    def test_unknown_type_value_raises_yaml_validation_error(self) -> None:
        """A type value not in (file_glob, url_list, crawl) raises YAMLValidationError."""
        yaml = """\
sources:
  - name: "Test"
    type: database_dump
    config:
      glob: "*.md"
"""
        with pytest.raises(strictyaml.YAMLValidationError):
            parse_manifest(yaml)

    def test_empty_sources_list_returns_empty_list(self) -> None:
        """A manifest with an empty sources list returns []."""
        entries = parse_manifest("sources: []\n")
        assert entries == []


# ---------------------------------------------------------------------------
# AC3, AC4 — File glob resolution
# ---------------------------------------------------------------------------


class TestFromAC_GlobResolution:
    """Tests for file glob expansion against the filesystem."""

    @pytest.mark.asyncio
    async def test_glob_expands_to_matching_files(self, tmp_path: Path) -> None:
        """*.md glob resolves to exactly the .md files in tmp_path."""
        (tmp_path / "a.md").write_text("hello")
        (tmp_path / "b.md").write_text("world")
        (tmp_path / "c.txt").write_text("not this")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'Docs'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        summary = await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert summary.ingested == 2

    @pytest.mark.asyncio
    async def test_glob_does_not_ingest_non_matching_files(self, tmp_path: Path) -> None:
        """Files not matching the glob pattern are not ingested."""
        (tmp_path / "a.md").write_text("hello")
        (tmp_path / "b.txt").write_text("no match")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'Docs'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert mock_pipeline.ingest.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_glob_returns_zero_ingested(self, tmp_path: Path) -> None:
        """A glob matching no files results in ingested=0."""
        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'NoMatch'\n    type: file_glob\n    config:\n      glob: '*.xyz'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        summary = await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert summary.ingested == 0
        assert mock_pipeline.ingest.call_count == 0

    @pytest.mark.asyncio
    async def test_empty_glob_logs_at_warning_level(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An empty glob match emits at least one WARNING-level log."""
        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'NoMatch'\n    type: file_glob\n    config:\n      glob: '*.xyz'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        with caplog.at_level(logging.WARNING, logger="owlbear_knowledge.loader"):
            await load_manifest_file(
                manifest_path=manifest_file,
                workspace_root=tmp_path,
                source_store=mock_source_store,
                pipeline=mock_pipeline,
            )

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) >= 1


# ---------------------------------------------------------------------------
# AC5 — Source registration
# ---------------------------------------------------------------------------


class TestFromAC_SourceRegistration:
    """Tests for KnowledgeSourceStore.create() call contract."""

    @pytest.mark.asyncio
    async def test_create_called_once_per_manifest_entry(self, tmp_path: Path) -> None:
        """source_store.create() is called exactly once per source entry."""
        manifest_file = _write_manifest(tmp_path, _TWO_SOURCE_YAML)
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert mock_source_store.create.call_count == 2

    @pytest.mark.asyncio
    async def test_knowledge_source_name_matches_manifest(self, tmp_path: Path) -> None:
        """The KnowledgeSource passed to create() has the name from the manifest."""
        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'My Source'\n    type: file_glob\n    config:\n      glob: '*.xyz'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        source = mock_source_store.create.call_args[0][0]
        assert source.name == "My Source"

    @pytest.mark.asyncio
    async def test_knowledge_source_type_matches_manifest(self, tmp_path: Path) -> None:
        """The KnowledgeSource source_type matches the manifest 'type' field."""
        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'S'\n    type: file_glob\n    config:\n      glob: '*.xyz'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        source = mock_source_store.create.call_args[0][0]
        assert str(source.source_type) == "file_glob"

    @pytest.mark.asyncio
    async def test_knowledge_source_created_at_is_iso_string(self, tmp_path: Path) -> None:
        """created_at on the registered KnowledgeSource is a valid ISO 8601 timestamp string."""
        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'T'\n    type: file_glob\n    config:\n      glob: '*.xyz'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        source = mock_source_store.create.call_args[0][0]
        assert isinstance(source.created_at, str)
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", source.created_at)

    @pytest.mark.asyncio
    async def test_knowledge_source_updated_at_is_iso_string(self, tmp_path: Path) -> None:
        """updated_at on the registered KnowledgeSource is a valid ISO 8601 timestamp string."""
        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'T'\n    type: file_glob\n    config:\n      glob: '*.xyz'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        source = mock_source_store.create.call_args[0][0]
        assert isinstance(source.updated_at, str)
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", source.updated_at)


# ---------------------------------------------------------------------------
# AC6, AC7, AC8 — Ingest flow, delta skipping, failure isolation
# ---------------------------------------------------------------------------


class TestFromAC_IngestFlow:
    """Tests for IngestPipeline.ingest() orchestration and per-file accounting."""

    @pytest.mark.asyncio
    async def test_ingest_called_once_per_resolved_file(self, tmp_path: Path) -> None:
        """ingest() is called exactly once per file matched by the glob."""
        (tmp_path / "a.md").write_text("one")
        (tmp_path / "b.md").write_text("two")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'Docs'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert mock_pipeline.ingest.call_count == 2

    @pytest.mark.asyncio
    async def test_ingest_receives_intake_result_not_raw_text(self, tmp_path: Path) -> None:
        """ingest() receives an IntakeResult object, not a raw string or Path."""
        from owlbear_knowledge.intake import IntakeResult

        (tmp_path / "doc.md").write_text("content here")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'D'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        intake_arg = mock_pipeline.ingest.call_args[0][0]
        assert isinstance(intake_arg, IntakeResult)

    @pytest.mark.asyncio
    async def test_intake_result_content_matches_file_content(self, tmp_path: Path) -> None:
        """The IntakeResult passed to ingest() contains the actual file content."""
        (tmp_path / "doc.md").write_text("unique marker 12345")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'D'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_ok_result())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        intake_arg = mock_pipeline.ingest.call_args[0][0]
        assert "unique marker 12345" in intake_arg.content

    @pytest.mark.asyncio
    async def test_skipped_status_counted_as_skipped_not_ingested(
        self, tmp_path: Path
    ) -> None:
        """When ingest() returns status=skipped, summary.skipped increments, not ingested."""
        (tmp_path / "doc.md").write_text("unchanged content")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'D'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_make_skipped_result())
        mock_source_store = MagicMock()

        summary = await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert summary.skipped == 1
        assert summary.ingested == 0

    @pytest.mark.asyncio
    async def test_per_file_failure_does_not_abort_remaining_files(
        self, tmp_path: Path
    ) -> None:
        """If the first file fails, the loader still attempts the remaining files."""
        (tmp_path / "a.md").write_text("first")
        (tmp_path / "b.md").write_text("second")
        (tmp_path / "c.md").write_text("third")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'D'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(
            side_effect=[_make_failed_result(), _make_ok_result(), _make_ok_result()]
        )
        mock_source_store = MagicMock()

        summary = await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert mock_pipeline.ingest.call_count == 3
        assert summary.failed == 1
        assert summary.ingested == 2

    @pytest.mark.asyncio
    async def test_summary_tracks_ingested_skipped_failed_counts(
        self, tmp_path: Path
    ) -> None:
        """LoadSummary correctly tracks ingested, skipped, and failed counters."""
        (tmp_path / "a.md").write_text("ok")
        (tmp_path / "b.md").write_text("skip")
        (tmp_path / "c.md").write_text("fail")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'D'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(
            side_effect=[_make_ok_result(), _make_skipped_result(), _make_failed_result()]
        )
        mock_source_store = MagicMock()

        summary = await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert summary.ingested == 1
        assert summary.skipped == 1
        assert summary.failed == 1

    @pytest.mark.asyncio
    async def test_ingest_exception_does_not_abort_remaining_files(
        self, tmp_path: Path
    ) -> None:
        """If ingest() raises an exception on one file, remaining files are still processed
        and summary.failed is incremented (covers exception handler at loader.py:193-196)."""
        (tmp_path / "a.md").write_text("first")
        (tmp_path / "b.md").write_text("second")
        (tmp_path / "c.md").write_text("third")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'D'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(
            side_effect=[RuntimeError("unexpected failure"), _make_ok_result(), _make_ok_result()]
        )
        mock_source_store = MagicMock()

        summary = await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert mock_pipeline.ingest.call_count == 3
        assert summary.failed == 1
        assert summary.ingested == 2

    @pytest.mark.asyncio
    async def test_all_source_ok_false_when_all_files_in_source_fail(
        self, tmp_path: Path
    ) -> None:
        """When every file in a source fails, all_source_ok is set to False via the
        source_failed == source_total condition (loader.py:199) — tested without CLI mock."""
        (tmp_path / "a.md").write_text("fail1")
        (tmp_path / "b.md").write_text("fail2")

        manifest_file = _write_manifest(
            tmp_path,
            "sources:\n  - name: 'D'\n    type: file_glob\n    config:\n      glob: '*.md'\n",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(
            side_effect=[_make_failed_result(), _make_failed_result()]
        )
        mock_source_store = MagicMock()

        summary = await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert summary.all_source_ok is False
        assert summary.failed == 2


# ---------------------------------------------------------------------------
# AC9, AC10 — CLI entry point and exit codes
# ---------------------------------------------------------------------------


class TestFromAC_CLI:
    """Tests for the CLI main() function and exit code contract."""

    def test_missing_manifest_flag_raises_system_exit_nonzero(self) -> None:
        """main([]) without --manifest causes SystemExit with non-zero code."""
        from owlbear_knowledge.loader import main

        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code != 0

    def test_manifest_flag_accepted_exits_zero_on_success(
        self, tmp_path: Path
    ) -> None:
        """--manifest flag is parsed and main() returns 0 on a successful run."""
        from unittest.mock import AsyncMock, patch

        from owlbear_knowledge.loader import main

        manifest_file = tmp_path / "sources.yaml"
        manifest_file.write_text("sources: []\n")

        mock_summary = MagicMock(spec=LoadSummary)
        mock_summary.all_source_ok = True

        with patch(
            "owlbear_knowledge.loader.load_manifest_file",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ):
            exit_code = main(["--manifest", str(manifest_file), "--root", str(tmp_path)])

        assert exit_code == 0

    def test_root_defaults_to_cwd_when_omitted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When --root is not supplied, workspace_root defaults to the current directory."""
        from unittest.mock import AsyncMock, patch

        from owlbear_knowledge.loader import main

        manifest_file = tmp_path / "sources.yaml"
        manifest_file.write_text("sources: []\n")
        monkeypatch.chdir(tmp_path)

        mock_summary = MagicMock(spec=LoadSummary)
        mock_summary.all_source_ok = True

        with patch(
            "owlbear_knowledge.loader.load_manifest_file",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ) as mock_load:
            main(["--manifest", str(manifest_file)])

        _, kwargs = mock_load.call_args
        workspace_root = kwargs.get("workspace_root") or mock_load.call_args.args[1]
        assert Path(workspace_root).resolve() == tmp_path.resolve()

    def test_exit_code_zero_on_all_ok(
        self, tmp_path: Path
    ) -> None:
        """Exit code 0 when all files ingested successfully."""
        from unittest.mock import AsyncMock, patch

        from owlbear_knowledge.loader import main

        manifest_file = tmp_path / "sources.yaml"
        manifest_file.write_text("sources: []\n")

        mock_summary = MagicMock(spec=LoadSummary)
        mock_summary.all_source_ok = True

        with patch(
            "owlbear_knowledge.loader.load_manifest_file",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ):
            exit_code = main(["--manifest", str(manifest_file), "--root", str(tmp_path)])

        assert exit_code == 0

    def test_exit_code_zero_when_some_files_are_skipped(
        self, tmp_path: Path
    ) -> None:
        """Exit code 0 when some files were delta-skipped (unchanged content)."""
        from unittest.mock import AsyncMock, patch

        from owlbear_knowledge.loader import main

        manifest_file = tmp_path / "sources.yaml"
        manifest_file.write_text("sources: []\n")

        mock_summary = MagicMock(spec=LoadSummary)
        mock_summary.ingested = 1
        mock_summary.skipped = 5
        mock_summary.failed = 0
        mock_summary.all_source_ok = True

        with patch(
            "owlbear_knowledge.loader.load_manifest_file",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ):
            exit_code = main(["--manifest", str(manifest_file), "--root", str(tmp_path)])

        assert exit_code == 0

    def test_exit_code_nonzero_when_all_files_in_any_source_fail(
        self, tmp_path: Path
    ) -> None:
        """Exit code non-zero when every file in at least one source failed to ingest."""
        from unittest.mock import AsyncMock, patch

        from owlbear_knowledge.loader import main

        manifest_file = tmp_path / "sources.yaml"
        manifest_file.write_text("sources: []\n")

        mock_summary = MagicMock(spec=LoadSummary)
        mock_summary.ingested = 0
        mock_summary.skipped = 0
        mock_summary.failed = 3
        mock_summary.all_source_ok = False

        with patch(
            "owlbear_knowledge.loader.load_manifest_file",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ):
            exit_code = main(["--manifest", str(manifest_file), "--root", str(tmp_path)])

        assert exit_code != 0

