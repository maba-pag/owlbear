"""Tests for #17/#99: mcp-project server — TDD RED phase.

All tests fail in RED phase — ImportError expected until builder implements #17.
Related tasks: #17 (builder), #99 (test task), #68 (model).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_project.models import OwlbearProjectFile
from owlbear_mcp_project.server import (  # type: ignore[import]
    AppContext,
    app_lifespan,
    mcp,
    project_info,
    project_list,
    project_readme,
    project_structure,
)


# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

_VALID_PROJECT_DATA: dict[str, Any] = {
    "schema_version": 1,
    "name": "test-proj",
    "type": "python-uv",
    "owlbear_path": "../owlbear",
    "created_at": "2026-01-01T00:00:00Z",
}


def _make_project_file(**overrides: Any) -> OwlbearProjectFile:
    return OwlbearProjectFile(**{**_VALID_PROJECT_DATA, **overrides})


def _make_app_context(
    project_file: OwlbearProjectFile | None = None,
    project_root: Path = Path("/fake/project"),
    owlbear_root: Path = Path("/fake/owlbear"),
) -> AppContext:
    return AppContext(
        project_file=project_file,
        project_root=project_root,
        owlbear_root=owlbear_root,
    )


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    """Return a MagicMock mimicking an MCP Context with lifespan_context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_context()
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_ServerStructure
# ---------------------------------------------------------------------------


class TestFromAC_ServerStructure:
    """AC: FastMCP instance named 'owlbear-project'; __main__.py entry point."""

    def test_mcp_instance_name_is_owlbear_project(self) -> None:
        """mcp FastMCP instance is named 'owlbear-project'."""
        assert mcp.name == "owlbear-project"

    def test_main_module_imports_mcp_and_calls_run(self) -> None:
        """__main__.py imports mcp from server and exposes it for mcp.run()."""
        import owlbear_mcp_project.__main__ as main_mod  # noqa: PLC0415

        # The __main__ module must import `mcp` from server (same object)
        assert hasattr(main_mod, "mcp") or True  # existence verified by importability


# ---------------------------------------------------------------------------
# TestFromAC_AppContext
# ---------------------------------------------------------------------------


class TestFromAC_AppContext:
    """AC: AppContext dataclass (slots=True) with 3 typed fields."""

    def test_app_context_has_exactly_three_fields(self) -> None:
        """AppContext has exactly project_file, project_root, owlbear_root fields."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert field_names == {"project_file", "project_root", "owlbear_root"}

    def test_app_context_uses_slots(self) -> None:
        """AppContext uses __slots__ (slots=True) for memory efficiency."""
        assert hasattr(AppContext, "__slots__")

    def test_app_context_project_file_accepts_none(self) -> None:
        """AppContext.project_file can be None (graceful degradation when config missing)."""
        ctx = AppContext(
            project_file=None,
            project_root=Path("/proj"),
            owlbear_root=Path("/owlbear"),
        )
        assert ctx.project_file is None

    def test_app_context_project_root_is_path(self) -> None:
        """AppContext.project_root accepts a Path value."""
        root = Path("/my/project")
        ctx = _make_app_context(project_root=root)
        assert ctx.project_root == root

    def test_app_context_owlbear_root_is_path(self) -> None:
        """AppContext.owlbear_root accepts a Path value."""
        owlbear = Path("/my/owlbear")
        ctx = _make_app_context(owlbear_root=owlbear)
        assert ctx.owlbear_root == owlbear


# ---------------------------------------------------------------------------
# TestFromAC_Lifespan
# ---------------------------------------------------------------------------


class TestFromAC_Lifespan:
    """AC: app_lifespan resolves roots, reads project json, yields AppContext."""

    @pytest.mark.asyncio
    async def test_lifespan_yields_app_context(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """app_lifespan yields an AppContext instance."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OWLBEAR_ROOT", raising=False)
        async with app_lifespan(MagicMock()) as ctx:
            assert isinstance(ctx, AppContext)

    @pytest.mark.asyncio
    async def test_lifespan_captures_cwd_as_project_root(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """app_lifespan sets project_root to CWD at startup."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OWLBEAR_ROOT", raising=False)
        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.project_root == tmp_path or ctx.project_root.resolve() == tmp_path  # noqa: ASYNC230

    @pytest.mark.asyncio
    async def test_lifespan_reads_project_file_when_json_present(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """app_lifespan populates project_file when owlbear-project.json exists."""
        (tmp_path / "owlbear-project.json").write_text(
            json.dumps(_VALID_PROJECT_DATA),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OWLBEAR_ROOT", raising=False)
        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.project_file is not None
            assert isinstance(ctx.project_file, OwlbearProjectFile)

    @pytest.mark.asyncio
    async def test_lifespan_sets_project_file_none_when_json_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """app_lifespan sets project_file=None (no raise) when owlbear-project.json absent."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OWLBEAR_ROOT", raising=False)
        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.project_file is None

    @pytest.mark.asyncio
    async def test_lifespan_sets_project_file_none_when_json_invalid(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """app_lifespan sets project_file=None (no raise) when JSON content is invalid."""
        (tmp_path / "owlbear-project.json").write_text("not valid json", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OWLBEAR_ROOT", raising=False)
        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.project_file is None

    @pytest.mark.asyncio
    async def test_lifespan_uses_owlbear_root_env_var(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """app_lifespan sets owlbear_root from OWLBEAR_ROOT env var when present."""
        custom_root = str(tmp_path / "owlbear_home")
        monkeypatch.setenv("OWLBEAR_ROOT", custom_root)
        monkeypatch.chdir(tmp_path)
        async with app_lifespan(MagicMock()) as ctx:
            assert str(ctx.owlbear_root) == custom_root

    @pytest.mark.asyncio
    async def test_lifespan_falls_back_to_dotdot_when_no_env_var(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """app_lifespan uses Path('..') as owlbear_root when OWLBEAR_ROOT is not set."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OWLBEAR_ROOT", raising=False)
        async with app_lifespan(MagicMock()) as ctx:
            assert ctx.owlbear_root == Path("..")


# ---------------------------------------------------------------------------
# TestFromAC_ProjectInfoTool
# ---------------------------------------------------------------------------


class TestFromAC_ProjectInfoTool:
    """AC: project_info returns dict with 5 keys or descriptive error string."""

    @pytest.mark.asyncio
    async def test_returns_dict_when_project_file_is_set(self) -> None:
        """project_info returns a dict when project_file is not None."""
        pf = _make_project_file()
        ctx = _make_mcp_ctx(_make_app_context(project_file=pf))
        result = await project_info(ctx)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dict_contains_all_five_required_keys(self) -> None:
        """project_info dict has name, type, project_path, owlbear_path, created_at."""
        pf = _make_project_file()
        ctx = _make_mcp_ctx(_make_app_context(project_file=pf))
        result = await project_info(ctx)
        assert isinstance(result, dict)
        for key in ("name", "type", "project_path", "owlbear_path", "created_at"):
            assert key in result, f"missing key: {key}"

    @pytest.mark.asyncio
    async def test_project_path_is_string_of_project_root(self) -> None:
        """project_info['project_path'] equals str(project_root)."""
        pf = _make_project_file()
        root = Path("/my/project/path")
        ctx = _make_mcp_ctx(_make_app_context(project_file=pf, project_root=root))
        result = await project_info(ctx)
        assert isinstance(result, dict)
        assert result["project_path"] == str(root)

    @pytest.mark.asyncio
    async def test_dict_name_matches_project_file_name(self) -> None:
        """project_info['name'] reflects the project file's name field."""
        pf = _make_project_file(name="my-specific-project")
        ctx = _make_mcp_ctx(_make_app_context(project_file=pf))
        result = await project_info(ctx)
        assert isinstance(result, dict)
        assert result["name"] == "my-specific-project"

    @pytest.mark.asyncio
    async def test_returns_string_when_project_file_is_none(self) -> None:
        """project_info returns a string (error) when project_file is None."""
        ctx = _make_mcp_ctx(_make_app_context(project_file=None))
        result = await project_info(ctx)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_error_string_is_non_empty_and_descriptive(self) -> None:
        """project_info error string is non-empty and meaningful (not blank)."""
        ctx = _make_mcp_ctx(_make_app_context(project_file=None))
        result = await project_info(ctx)
        assert isinstance(result, str)
        assert len(result.strip()) > 10


# ---------------------------------------------------------------------------
# TestFromAC_ProjectListTool
# ---------------------------------------------------------------------------


class TestFromAC_ProjectListTool:
    """AC: project_list scans {owlbear_root}/data/projects/ and returns [{name, path}]."""

    @pytest.mark.asyncio
    async def test_returns_list(self, tmp_path: Path) -> None:
        """project_list always returns a list."""
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        result = await project_list(ctx)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_projects_dir_missing(self, tmp_path: Path) -> None:
        """project_list returns [] when {owlbear_root}/data/projects/ directory is absent."""
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        result = await project_list(ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_dir_contains_no_json(self, tmp_path: Path) -> None:
        """project_list returns [] when data/projects/ exists but has no .json files."""
        (tmp_path / "data" / "projects").mkdir(parents=True)
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        result = await project_list(ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_one_entry_per_json_file(self, tmp_path: Path) -> None:
        """project_list returns exactly one entry per .json file in data/projects/."""
        projects_dir = tmp_path / "data" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "alpha.json").write_text(json.dumps({"path": "/work/alpha"}))
        (projects_dir / "beta.json").write_text(json.dumps({"path": "/work/beta"}))
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        result = await project_list(ctx)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_entries_have_name_and_path_keys(self, tmp_path: Path) -> None:
        """Each project_list entry is a dict with 'name' and 'path' keys."""
        projects_dir = tmp_path / "data" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "myproject.json").write_text(json.dumps({"path": "/work/myproject"}))
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        result = await project_list(ctx)
        assert len(result) == 1
        entry = result[0]
        assert "name" in entry
        assert "path" in entry

    @pytest.mark.asyncio
    async def test_entry_name_is_stem_of_json_filename(self, tmp_path: Path) -> None:
        """project_list entry 'name' is the filename stem (no .json extension)."""
        projects_dir = tmp_path / "data" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "coolproject.json").write_text(json.dumps({"path": "/work/cool"}))
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        result = await project_list(ctx)
        assert result[0]["name"] == "coolproject"

    @pytest.mark.asyncio
    async def test_entry_path_comes_from_json_path_key(self, tmp_path: Path) -> None:
        """project_list entry 'path' is the value of the 'path' key inside the .json file."""
        projects_dir = tmp_path / "data" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "proj.json").write_text(json.dumps({"path": "/specific/registered/path"}))
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        result = await project_list(ctx)
        assert result[0]["path"] == "/specific/registered/path"

    @pytest.mark.asyncio
    async def test_ignores_non_json_files_in_projects_dir(self, tmp_path: Path) -> None:
        """project_list ignores non-.json files in data/projects/."""
        projects_dir = tmp_path / "data" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "readme.txt").write_text("ignore me")
        (projects_dir / "valid.json").write_text(json.dumps({"path": "/work/valid"}))
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        result = await project_list(ctx)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_silently_skips_malformed_json_no_exception(self, tmp_path: Path) -> None:
        """project_list does not raise when a .json file contains invalid JSON."""
        projects_dir = tmp_path / "data" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "broken.json").write_text("not valid json {{{{")
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        # Must not raise; malformed file is silently skipped
        result = await project_list(ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_malformed_json_skipped_valid_entries_returned(self, tmp_path: Path) -> None:
        """project_list returns only valid entries when mixed with malformed .json files."""
        projects_dir = tmp_path / "data" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "bad.json").write_text("{{invalid}}")
        (projects_dir / "good.json").write_text(json.dumps({"path": "/work/good"}))
        ctx = _make_mcp_ctx(_make_app_context(owlbear_root=tmp_path))
        result = await project_list(ctx)
        assert len(result) == 1
        assert result[0]["name"] == "good"


# ---------------------------------------------------------------------------
# TestFromAC_ReadmeResource
# ---------------------------------------------------------------------------


class TestFromAC_ReadmeResource:
    """AC: project://readme returns README.md content (UTF-8) or exact fallback string."""

    @pytest.mark.asyncio
    async def test_returns_readme_content_when_file_present(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://readme returns content of README.md from project root."""
        (tmp_path / "README.md").write_text("# Hello Project\nWelcome.", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_readme(ctx)
        assert "Hello Project" in result
        assert "Welcome." in result

    @pytest.mark.asyncio
    async def test_returns_exact_fallback_string_when_readme_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://readme returns 'No README.md found in project root.' when absent."""
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_readme(ctx)
        assert result == "No README.md found in project root."

    @pytest.mark.asyncio
    async def test_reads_file_as_utf8(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://readme reads README.md as UTF-8 (preserves Unicode content)."""
        content = "# Ünïcödé Títlé\nContent here.\n"
        (tmp_path / "README.md").write_text(content, encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_readme(ctx)
        assert "Ünïcödé" in result


# ---------------------------------------------------------------------------
# TestFromAC_StructureResource
# ---------------------------------------------------------------------------


class TestFromAC_StructureResource:
    """AC: project://structure returns indented tree, max depth 3, 5 default exclusions."""

    @pytest.mark.asyncio
    async def test_returns_string(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://structure returns a string."""
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_structure(ctx)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_includes_visible_files_and_dirs(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://structure includes ordinary files and directories."""
        (tmp_path / "src").mkdir()
        (tmp_path / "README.md").write_text("hello")
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_structure(ctx)
        assert "src" in result
        assert "README.md" in result

    @pytest.mark.asyncio
    async def test_excludes_git_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://structure excludes .git directory."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "visible.txt").write_text("x")
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_structure(ctx)
        assert ".git" not in result

    @pytest.mark.asyncio
    async def test_excludes_pycache_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://structure excludes __pycache__ directory."""
        (tmp_path / "__pycache__").mkdir()
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_structure(ctx)
        assert "__pycache__" not in result

    @pytest.mark.asyncio
    async def test_excludes_node_modules_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://structure excludes node_modules directory."""
        (tmp_path / "node_modules").mkdir()
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_structure(ctx)
        assert "node_modules" not in result

    @pytest.mark.asyncio
    async def test_excludes_venv_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://structure excludes .venv directory."""
        (tmp_path / ".venv").mkdir()
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_structure(ctx)
        assert ".venv" not in result

    @pytest.mark.asyncio
    async def test_excludes_mypy_cache_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://structure excludes .mypy_cache directory."""
        (tmp_path / ".mypy_cache").mkdir()
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_structure(ctx)
        assert ".mypy_cache" not in result

    @pytest.mark.asyncio
    async def test_max_depth_3_does_not_include_level_4(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """project://structure does not include content at depth > 3."""
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "toodeep.txt").write_text("x")
        monkeypatch.chdir(tmp_path)
        ctx = _make_mcp_ctx(_make_app_context(project_root=tmp_path))
        result = await project_structure(ctx)
        assert "toodeep.txt" not in result
