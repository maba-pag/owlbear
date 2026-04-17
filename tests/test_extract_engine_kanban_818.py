"""RED tests — Engine extraction to serve/kanban/ + workspace config (task #818).

Verifies the target state of Phase 2 extraction:
- serve/kanban/pyproject.toml exists with correct deps (ruamel.yaml, pydantic, pyyaml; no MCP)
- Engine files present at serve/kanban/src/owlbear_kanban/ (6 files + __init__.py)
- Engine files removed from serve/mcp-kanban/src/owlbear_mcp_kanban/ (moved, not copied)
- Root pyproject.toml coverage and ruff src paths updated
- serve/mcp-kanban/pyproject.toml depends on owlbear-kanban workspace package

All tests FAIL in the RED phase before serve/kanban/ is extracted.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SERVE_DIR = _REPO_ROOT / "serve"
_KANBAN_DIR = _SERVE_DIR / "kanban"
_KANBAN_PYPROJECT = _KANBAN_DIR / "pyproject.toml"
_KANBAN_SRC = _KANBAN_DIR / "src" / "owlbear_kanban"
_MCP_KANBAN_SRC = _SERVE_DIR / "mcp-kanban" / "src" / "owlbear_mcp_kanban"
_MCP_KANBAN_PYPROJECT = _SERVE_DIR / "mcp-kanban" / "pyproject.toml"
_ROOT_PYPROJECT = _REPO_ROOT / "pyproject.toml"


class TestFromAC_KanbanPackageToml:
    """AC1: serve/kanban/pyproject.toml exists with correct deps (ruamel.yaml, pydantic, pyyaml; no MCP)."""

    def test_pyproject_toml_exists(self) -> None:
        """serve/kanban/pyproject.toml must exist after package extraction."""
        assert _KANBAN_PYPROJECT.exists(), (
            f"serve/kanban/pyproject.toml not found at {_KANBAN_PYPROJECT} — package not yet extracted"
        )

    def test_package_name(self) -> None:
        """serve/kanban/pyproject.toml project.name must be 'owlbear-kanban'."""
        data = tomllib.loads(_KANBAN_PYPROJECT.read_text(encoding="utf-8"))
        name = data.get("project", {}).get("name", "")
        assert name == "owlbear-kanban", f"Expected name 'owlbear-kanban', got {name!r}"

    def test_ruamel_yaml_dep(self) -> None:
        """ruamel.yaml must be in serve/kanban/pyproject.toml dependencies (config_loader.py uses it)."""
        data = tomllib.loads(_KANBAN_PYPROJECT.read_text(encoding="utf-8"))
        deps = data.get("project", {}).get("dependencies", [])
        assert any("ruamel.yaml" in d for d in deps), f"ruamel.yaml not found in serve/kanban deps: {deps}"

    def test_pydantic_dep(self) -> None:
        """pydantic must be in serve/kanban/pyproject.toml dependencies (models.py requires it)."""
        data = tomllib.loads(_KANBAN_PYPROJECT.read_text(encoding="utf-8"))
        deps = data.get("project", {}).get("dependencies", [])
        assert any("pydantic" in d for d in deps), f"pydantic not found in serve/kanban deps: {deps}"

    def test_no_mcp_dep(self) -> None:
        """serve/kanban/pyproject.toml must NOT depend on mcp or fastmcp (engine is transport-free)."""
        data = tomllib.loads(_KANBAN_PYPROJECT.read_text(encoding="utf-8"))
        deps = data.get("project", {}).get("dependencies", [])
        mcp_deps = [d for d in deps if d.lower().startswith("mcp") or "fastmcp" in d.lower()]
        assert not mcp_deps, f"Engine package must not depend on MCP transport packages: {mcp_deps}"


class TestFromAC_EngineFilesExtracted:
    """AC2: Engine files present at serve/kanban/src/owlbear_kanban/ and removed from mcp-kanban."""

    def test_engine_src_dir_exists(self) -> None:
        """serve/kanban/src/owlbear_kanban/ directory must exist after extraction."""
        assert _KANBAN_SRC.exists(), f"serve/kanban/src/owlbear_kanban/ not found at {_KANBAN_SRC}"

    def test_engine_py_at_new_location(self) -> None:
        """engine.py must exist at serve/kanban/src/owlbear_kanban/engine.py."""
        assert (_KANBAN_SRC / "engine.py").exists()

    def test_models_py_at_new_location(self) -> None:
        """models.py must exist at serve/kanban/src/owlbear_kanban/models.py (renamed from engine_models.py)."""
        assert (_KANBAN_SRC / "models.py").exists()

    def test_task_io_at_new_location(self) -> None:
        """task_io.py must exist at serve/kanban/src/owlbear_kanban/task_io.py."""
        assert (_KANBAN_SRC / "task_io.py").exists()

    def test_config_loader_at_new_location(self) -> None:
        """config_loader.py must exist at serve/kanban/src/owlbear_kanban/config_loader.py."""
        assert (_KANBAN_SRC / "config_loader.py").exists()

    def test_activity_log_at_new_location(self) -> None:
        """activity_log.py must exist at serve/kanban/src/owlbear_kanban/activity_log.py."""
        assert (_KANBAN_SRC / "activity_log.py").exists()

    def test_agent_names_at_new_location(self) -> None:
        """agent_names.py must exist at serve/kanban/src/owlbear_kanban/agent_names.py."""
        assert (_KANBAN_SRC / "agent_names.py").exists()

    def test_init_py_at_new_location(self) -> None:
        """__init__.py must exist at serve/kanban/src/owlbear_kanban/__init__.py."""
        assert (_KANBAN_SRC / "__init__.py").exists()

    def test_engine_py_removed_from_mcp_kanban(self) -> None:
        """engine.py must NOT remain in mcp-kanban — it was moved to serve/kanban/."""
        assert not (_MCP_KANBAN_SRC / "engine.py").exists(), (
            "engine.py still present in mcp-kanban — must be moved to serve/kanban/ (not copied)"
        )

    def test_engine_models_removed_from_mcp_kanban(self) -> None:
        """engine_models.py must NOT remain in mcp-kanban — renamed to models.py and moved."""
        assert not (_MCP_KANBAN_SRC / "engine_models.py").exists(), (
            "engine_models.py still in mcp-kanban — must be moved and renamed to models.py in serve/kanban/"
        )

    def test_task_io_removed_from_mcp_kanban(self) -> None:
        """task_io.py must NOT remain in mcp-kanban — it was moved to serve/kanban/."""
        assert not (_MCP_KANBAN_SRC / "task_io.py").exists(), (
            "task_io.py still in mcp-kanban — must be moved to serve/kanban/"
        )

    def test_config_loader_removed_from_mcp_kanban(self) -> None:
        """config_loader.py must NOT remain in mcp-kanban — it was moved to serve/kanban/."""
        assert not (_MCP_KANBAN_SRC / "config_loader.py").exists(), (
            "config_loader.py still in mcp-kanban — must be moved to serve/kanban/"
        )

    def test_activity_log_removed_from_mcp_kanban(self) -> None:
        """activity_log.py must NOT remain in mcp-kanban — it was moved to serve/kanban/."""
        assert not (_MCP_KANBAN_SRC / "activity_log.py").exists(), (
            "activity_log.py still in mcp-kanban — must be moved to serve/kanban/"
        )

    def test_agent_names_removed_from_mcp_kanban(self) -> None:
        """agent_names.py must NOT remain in mcp-kanban — it was moved to serve/kanban/."""
        assert not (_MCP_KANBAN_SRC / "agent_names.py").exists(), (
            "agent_names.py still in mcp-kanban — must be moved to serve/kanban/"
        )


class TestFromAC_RootConfigUpdated:
    """AC4: Root pyproject.toml coverage paths and ruff src paths include serve/kanban/."""

    def test_coverage_source_pkgs_includes_owlbear_kanban(self) -> None:
        """Root pyproject.toml [tool.coverage.run] source_pkgs must include 'owlbear_kanban'."""
        data = tomllib.loads(_ROOT_PYPROJECT.read_text(encoding="utf-8"))
        source_pkgs = data.get("tool", {}).get("coverage", {}).get("run", {}).get("source_pkgs", [])
        assert "owlbear_kanban" in source_pkgs, (
            f"'owlbear_kanban' not in [tool.coverage.run] source_pkgs: {source_pkgs}"
        )

    def test_ruff_src_includes_kanban(self) -> None:
        """Root pyproject.toml [tool.ruff] src must include 'serve/kanban/src'."""
        data = tomllib.loads(_ROOT_PYPROJECT.read_text(encoding="utf-8"))
        ruff_src = data.get("tool", {}).get("ruff", {}).get("src", [])
        assert "serve/kanban/src" in ruff_src, f"'serve/kanban/src' not in [tool.ruff] src: {ruff_src}"


class TestFromAC_McpKanbanWorkspaceDep:
    """Implicit AC (from research): serve/mcp-kanban/pyproject.toml depends on owlbear-kanban workspace package."""

    def test_owlbear_kanban_in_mcp_deps(self) -> None:
        """serve/mcp-kanban/pyproject.toml must list owlbear-kanban as a dependency."""
        data = tomllib.loads(_MCP_KANBAN_PYPROJECT.read_text(encoding="utf-8"))
        deps = data.get("project", {}).get("dependencies", [])
        assert any("owlbear-kanban" in d for d in deps), f"owlbear-kanban not found in mcp-kanban dependencies: {deps}"

    def test_owlbear_kanban_workspace_source(self) -> None:
        """serve/mcp-kanban/pyproject.toml must declare owlbear-kanban as workspace = true in [tool.uv.sources]."""
        data = tomllib.loads(_MCP_KANBAN_PYPROJECT.read_text(encoding="utf-8"))
        sources = data.get("tool", {}).get("uv", {}).get("sources", {})
        assert "owlbear-kanban" in sources, f"owlbear-kanban not in mcp-kanban [tool.uv.sources]: {sources}"
        assert sources["owlbear-kanban"].get("workspace") is True, (
            f"owlbear-kanban source must be workspace=true, got: {sources.get('owlbear-kanban')}"
        )

    def test_ruamel_yaml_not_direct_dep_of_mcp_kanban(self) -> None:
        """ruamel.yaml must NOT be a direct dep of mcp-kanban — it moves with the engine package."""
        data = tomllib.loads(_MCP_KANBAN_PYPROJECT.read_text(encoding="utf-8"))
        deps = data.get("project", {}).get("dependencies", [])
        ruamel_direct = [d for d in deps if "ruamel.yaml" in d]
        assert not ruamel_direct, (
            f"ruamel.yaml should not be a direct dep of mcp-kanban after extraction "
            f"(obtained transitively through owlbear-kanban): {ruamel_direct}"
        )
