"""RED-phase tests for KB data loader — scope, enabled, and initial manifest (#176).

Covers AC lines from #176 NOT already tested by test_kb_loader.py (#431):
  - AC1  (scope/enabled schema): manifest schema accepts optional scope (default "global")
           and optional enabled (default true); entries expose these fields after parsing
  - AC6  (scope passthrough): scope from manifest entry is forwarded as scope= kwarg
           to IngestPipeline.ingest(); different sources use their own scopes
  - AC1  (enabled=false skip): sources with enabled=false are not registered and not ingested
  - AC11 (initial sources.yaml): data/knowledge/general/sources.yaml exists and contains
           globs for docs/research/*.md, skills/*/SKILL.md, instructions/*.md

All tests must FAIL until loader.py is extended to support scope/enabled fields.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.ingest import IngestResult
from owlbear_knowledge.loader import LoadSummary, load_manifest_file, main, parse_manifest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent


def _ok() -> IngestResult:
    return IngestResult(document_id="x", chunk_count=1, entity_count=0, edge_count=0, status="ok")


def _write_manifest(tmp: Path, content: str) -> Path:
    p = tmp / "sources.yaml"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# AC1 — Manifest schema: scope field (default "global")
# ---------------------------------------------------------------------------


class TestFromAC_ScopeField:
    """scope is an optional manifest field; absent → 'global'."""

    def test_parse_manifest_exposes_scope_attribute(self) -> None:
        """ManifestEntry must have a scope attribute after parsing."""
        yaml = """\
sources:
  - name: "Docs"
    type: file_glob
    config:
      glob: "*.md"
    scope: project
"""
        entries = parse_manifest(yaml)
        assert len(entries) == 1
        entry = entries[0]
        assert hasattr(entry, "scope"), "ManifestEntry must expose a 'scope' attribute"
        assert entry.scope == "project"

    def test_scope_defaults_to_global_when_omitted(self) -> None:
        """When scope is not in the YAML, the entry's scope defaults to 'global'."""
        yaml = """\
sources:
  - name: "Docs"
    type: file_glob
    config:
      glob: "*.md"
"""
        entries = parse_manifest(yaml)
        assert entries[0].scope == "global"

    def test_explicit_global_scope_preserved(self) -> None:
        """Explicit scope: global is preserved as 'global'."""
        yaml = """\
sources:
  - name: "Docs"
    type: file_glob
    config:
      glob: "*.md"
    scope: global
"""
        entries = parse_manifest(yaml)
        assert entries[0].scope == "global"

    def test_custom_scope_value_preserved(self) -> None:
        """Arbitrary scope values (e.g. 'knowledge') are preserved as-is."""
        yaml = """\
sources:
  - name: "Skills"
    type: file_glob
    config:
      glob: "**/*.md"
    scope: knowledge
"""
        entries = parse_manifest(yaml)
        assert entries[0].scope == "knowledge"

    def test_multiple_sources_with_different_scopes(self) -> None:
        """Each source entry keeps its own scope."""
        yaml = """\
sources:
  - name: "A"
    type: file_glob
    config:
      glob: "*.md"
    scope: alpha
  - name: "B"
    type: file_glob
    config:
      glob: "*.txt"
    scope: beta
"""
        entries = parse_manifest(yaml)
        assert entries[0].scope == "alpha"
        assert entries[1].scope == "beta"


# ---------------------------------------------------------------------------
# AC1 — Manifest schema: enabled field (default true)
# ---------------------------------------------------------------------------


class TestFromAC_EnabledField:
    """enabled is an optional manifest field; absent → True."""

    def test_parse_manifest_exposes_enabled_attribute(self) -> None:
        """ManifestEntry must have an enabled attribute after parsing."""
        yaml = """\
sources:
  - name: "Docs"
    type: file_glob
    config:
      glob: "*.md"
    enabled: true
"""
        entries = parse_manifest(yaml)
        assert len(entries) == 1
        assert hasattr(entries[0], "enabled"), "ManifestEntry must expose an 'enabled' attribute"
        assert entries[0].enabled is True

    def test_enabled_defaults_to_true_when_omitted(self) -> None:
        """When enabled is absent from YAML, entry.enabled is True."""
        yaml = """\
sources:
  - name: "Docs"
    type: file_glob
    config:
      glob: "*.md"
"""
        entries = parse_manifest(yaml)
        assert entries[0].enabled is True

    def test_enabled_false_parsed_correctly(self) -> None:
        """enabled: false is parsed as the boolean False."""
        yaml = """\
sources:
  - name: "Disabled"
    type: file_glob
    config:
      glob: "*.md"
    enabled: false
"""
        entries = parse_manifest(yaml)
        assert entries[0].enabled is False


# ---------------------------------------------------------------------------
# AC1 (enabled=false) — Disabled sources must be skipped
# ---------------------------------------------------------------------------


class TestFromAC_DisabledSourceSkip:
    """Sources with enabled=false must not be registered or ingested."""

    @pytest.mark.asyncio
    async def test_disabled_source_not_registered_in_source_store(
        self, tmp_path: Path
    ) -> None:
        """source_store.create() is NOT called for entries with enabled=false."""
        (tmp_path / "doc.md").write_text("content")
        manifest_file = _write_manifest(
            tmp_path,
            """\
sources:
  - name: "Off"
    type: file_glob
    config:
      glob: "*.md"
    enabled: false
""",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ok())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        mock_source_store.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_disabled_source_not_ingested(self, tmp_path: Path) -> None:
        """pipeline.ingest() is NOT called for entries with enabled=false."""
        (tmp_path / "doc.md").write_text("content")
        manifest_file = _write_manifest(
            tmp_path,
            """\
sources:
  - name: "Off"
    type: file_glob
    config:
      glob: "*.md"
    enabled: false
""",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ok())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        mock_pipeline.ingest.assert_not_called()

    @pytest.mark.asyncio
    async def test_mix_enabled_disabled_only_enabled_processed(
        self, tmp_path: Path
    ) -> None:
        """With one enabled and one disabled source, only the enabled one is processed."""
        (tmp_path / "a.md").write_text("enabled content")
        manifest_file = _write_manifest(
            tmp_path,
            """\
sources:
  - name: "Active"
    type: file_glob
    config:
      glob: "*.md"
    enabled: true
  - name: "Inactive"
    type: file_glob
    config:
      glob: "*.md"
    enabled: false
""",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ok())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        # Only one source was enabled; create() called once, ingest called once
        assert mock_source_store.create.call_count == 1
        assert mock_pipeline.ingest.call_count == 1


# ---------------------------------------------------------------------------
# AC6 — scope from manifest forwarded to IngestPipeline.ingest()
# ---------------------------------------------------------------------------


class TestFromAC_ScopePassthrough:
    """Scope from the manifest entry must be forwarded to pipeline.ingest()."""

    @pytest.mark.asyncio
    async def test_ingest_called_with_scope_from_manifest(self, tmp_path: Path) -> None:
        """pipeline.ingest() receives scope= keyword arg matching the manifest entry scope."""
        (tmp_path / "doc.md").write_text("content")
        manifest_file = _write_manifest(
            tmp_path,
            """\
sources:
  - name: "Research"
    type: file_glob
    config:
      glob: "*.md"
    scope: research
""",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ok())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        _, kwargs = mock_pipeline.ingest.call_args
        assert kwargs.get("scope") == "research", (
            "ingest() must be called with scope='research'"
        )

    @pytest.mark.asyncio
    async def test_default_scope_global_passed_to_ingest_when_omitted(
        self, tmp_path: Path
    ) -> None:
        """When scope is absent from manifest, ingest() receives scope='global'."""
        (tmp_path / "doc.md").write_text("content")
        manifest_file = _write_manifest(
            tmp_path,
            """\
sources:
  - name: "Docs"
    type: file_glob
    config:
      glob: "*.md"
""",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ok())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        _, kwargs = mock_pipeline.ingest.call_args
        assert kwargs.get("scope") == "global"

    @pytest.mark.asyncio
    async def test_multiple_sources_each_use_own_scope(self, tmp_path: Path) -> None:
        """Two sources with different scopes pass their respective scopes to ingest()."""
        (tmp_path / "a.md").write_text("alpha doc")
        (tmp_path / "b.txt").write_text("beta doc")
        manifest_file = _write_manifest(
            tmp_path,
            """\
sources:
  - name: "Alpha"
    type: file_glob
    config:
      glob: "*.md"
    scope: alpha
  - name: "Beta"
    type: file_glob
    config:
      glob: "*.txt"
    scope: beta
""",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ok())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert mock_pipeline.ingest.call_count == 2
        scopes_used = [
            c.kwargs.get("scope") for c in mock_pipeline.ingest.call_args_list
        ]
        assert "alpha" in scopes_used
        assert "beta" in scopes_used

    @pytest.mark.asyncio
    async def test_scope_passed_to_each_file_in_same_source(self, tmp_path: Path) -> None:
        """All files from one source use that source's scope, even with multiple files."""
        (tmp_path / "a.md").write_text("one")
        (tmp_path / "b.md").write_text("two")
        manifest_file = _write_manifest(
            tmp_path,
            """\
sources:
  - name: "Docs"
    type: file_glob
    config:
      glob: "*.md"
    scope: docs
""",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ok())
        mock_source_store = MagicMock()

        await load_manifest_file(
            manifest_path=manifest_file,
            workspace_root=tmp_path,
            source_store=mock_source_store,
            pipeline=mock_pipeline,
        )

        assert mock_pipeline.ingest.call_count == 2
        for c in mock_pipeline.ingest.call_args_list:
            assert c.kwargs.get("scope") == "docs", (
                "Every ingest() call must use scope='docs'"
            )


# ---------------------------------------------------------------------------
# AC11 — Initial sources.yaml exists with correct glob patterns
# ---------------------------------------------------------------------------


class TestFromAC_InitialSourcesYaml:
    """data/knowledge/general/sources.yaml must exist and contain required globs."""

    _MANIFEST_PATH = PROJECT_ROOT / "store" / "knowledge" / "general" / "sources.yaml"

    def test_initial_sources_yaml_exists(self) -> None:
        """data/knowledge/general/sources.yaml must exist in the repository."""
        assert self._MANIFEST_PATH.exists(), (
            f"Expected initial sources manifest at {self._MANIFEST_PATH}"
        )

    def test_initial_sources_yaml_is_valid(self) -> None:
        """The initial sources.yaml must be parseable by parse_manifest without error."""
        content = self._MANIFEST_PATH.read_text(encoding="utf-8")
        entries = parse_manifest(content)
        assert isinstance(entries, list)

    def test_initial_manifest_includes_docs_research_glob(self) -> None:
        """sources.yaml must include a source with glob matching docs/research/*.md."""
        content = self._MANIFEST_PATH.read_text(encoding="utf-8")
        entries = parse_manifest(content)
        globs = [e.config.get("glob", "") for e in entries]
        assert any("docs/research" in g for g in globs), (
            f"No glob for docs/research/*.md found in {globs}"
        )

    def test_initial_manifest_includes_skills_glob(self) -> None:
        """sources.yaml must include a source with glob matching skills/*/SKILL.md."""
        content = self._MANIFEST_PATH.read_text(encoding="utf-8")
        entries = parse_manifest(content)
        globs = [e.config.get("glob", "") for e in entries]
        assert any("skills" in g and "SKILL" in g for g in globs), (
            f"No glob for skills/*/SKILL.md found in {globs}"
        )

    def test_initial_manifest_includes_instructions_glob(self) -> None:
        """sources.yaml must include a source with glob matching instructions/*.md."""
        content = self._MANIFEST_PATH.read_text(encoding="utf-8")
        entries = parse_manifest(content)
        globs = [e.config.get("glob", "") for e in entries]
        assert any("instructions" in g for g in globs), (
            f"No glob for instructions/*.md found in {globs}"
        )


# ---------------------------------------------------------------------------
# AC9 — Module invocation path: python -m owlbear_knowledge.loader
# Reviewer finding: CLI tests were LAX (called main() directly).
# These tests verify the module-as-script entrypoint is functional.
# ---------------------------------------------------------------------------


class TestFromAC_ModuleInvocation:
    """The loader module must have a __main__ guard so it is invokable via python -m."""

    def test_loader_module_has_main_guard(self) -> None:
        """loader.py must contain an `if __name__ == '__main__'` guard.

        Without this guard, `python -m owlbear_knowledge.loader` silently exits 0
        with no output — AC9 is violated.
        """
        import inspect

        import owlbear_knowledge.loader as loader_mod

        source = inspect.getsource(loader_mod)
        assert "if __name__ == '__main__'" in source, (
            "loader.py must have an `if __name__ == '__main__': sys.exit(main())` guard "
            "so that `python -m owlbear_knowledge.loader` invokes main()"
        )

    def test_module_invocation_without_manifest_exits_nonzero(self) -> None:
        """Running the module via runpy without --manifest must exit non-zero.

        Simulates: python -m owlbear_knowledge.loader  (no args)
        Expected:  SystemExit with code != 0 (argparse error for missing --manifest)
        Without the __main__ guard, no SystemExit is raised at all.
        """
        import runpy

        with patch.object(sys, "argv", ["owlbear_knowledge.loader"]), pytest.raises(SystemExit) as exc_info:
            runpy.run_module("owlbear_knowledge.loader", run_name="__main__")
        assert exc_info.value.code != 0, (
            "python -m owlbear_knowledge.loader without --manifest must exit non-zero; "
            "got code 0 (likely missing __main__ guard)"
        )

    def test_module_invocation_with_valid_manifest_exits_zero(
        self, tmp_path: Path
    ) -> None:
        """Running the module via runpy with --manifest must exit 0 on success.

        Simulates: python -m owlbear_knowledge.loader --manifest <path>
        Expected:  SystemExit(0)
        Without the __main__ guard, no SystemExit is raised at all.
        """
        import runpy

        manifest = tmp_path / "sources.yaml"
        manifest.write_text("sources: []\n")

        mock_load = AsyncMock(return_value=LoadSummary())
        with (
            patch("owlbear_knowledge.loader.load_manifest_file", mock_load),
            patch.object(sys, "argv", ["owlbear_knowledge.loader", "--manifest", str(manifest)]),
            pytest.raises(SystemExit) as exc_info,
        ):
            runpy.run_module("owlbear_knowledge.loader", run_name="__main__")
        assert exc_info.value.code == 0, (
            "python -m owlbear_knowledge.loader --manifest <path> must exit 0 on success"
        )


# ---------------------------------------------------------------------------
# AC9/AC10 — main() must instantiate real dependencies (not pass None)
# Reviewer finding: main() passes source_store=None and pipeline=None,
# causing AttributeError at runtime for any non-empty manifest.
# ---------------------------------------------------------------------------


class TestFromAC_MainInstantiation:
    """main() must pass real KnowledgeSourceStore and IngestPipeline instances."""

    def test_main_does_not_pass_none_source_store(self, tmp_path: Path) -> None:
        """main() must not pass None as source_store to load_manifest_file.

        Current broken behaviour: main() calls load_manifest_file(..., source_store=None)
        which would raise AttributeError on any non-empty manifest in production.
        """
        manifest = tmp_path / "sources.yaml"
        manifest.write_text("sources: []\n")

        mock_load = AsyncMock(return_value=LoadSummary())
        with patch("owlbear_knowledge.loader.load_manifest_file", mock_load):
            main(["--manifest", str(manifest), "--root", str(tmp_path)])

        mock_load.assert_called_once()
        call_kwargs = mock_load.call_args.kwargs
        source_store = call_kwargs.get("source_store")
        assert source_store is not None, (
            "main() must not pass None as source_store; "
            "it must instantiate a real KnowledgeSourceStore before calling load_manifest_file"
        )

    def test_main_does_not_pass_none_pipeline(self, tmp_path: Path) -> None:
        """main() must not pass None as pipeline to load_manifest_file.

        Current broken behaviour: main() calls load_manifest_file(..., pipeline=None)
        which would raise AttributeError on any non-empty manifest in production.
        """
        manifest = tmp_path / "sources.yaml"
        manifest.write_text("sources: []\n")

        mock_load = AsyncMock(return_value=LoadSummary())
        with patch("owlbear_knowledge.loader.load_manifest_file", mock_load):
            main(["--manifest", str(manifest), "--root", str(tmp_path)])

        mock_load.assert_called_once()
        call_kwargs = mock_load.call_args.kwargs
        pipeline = call_kwargs.get("pipeline")
        assert pipeline is not None, (
            "main() must not pass None as pipeline; "
            "it must instantiate a real IngestPipeline before calling load_manifest_file"
        )
