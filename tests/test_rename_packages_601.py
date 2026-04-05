"""Tests for task #601: Rename packages/ to serve/.

Contract-level tests verifying post-rename state of:
- Directory structure: serve/ with all 7 sub-packages, packages/ gone
- pyproject.toml: workspace members, ruff src paths, per-file-ignores, testpaths
- .gitignore: dist pattern updated to serve/
- .pre-commit-config.yaml: bandit -r path updated to serve/
- Runtime: uv sync succeeds, all 7 namespaces importable, MCP server modules resolve

AC coverage:
  AC1a: serve/ directory exists
  AC1b: serve/ contains all 7 sub-packages
  AC1c: serve/ contains exactly the 7 expected sub-packages (boundary)
  AC1d: packages/ directory has been removed
  AC2a: pyproject.toml workspace members = ["serve/*"]
  AC2b: pyproject.toml workspace members no longer contains "packages/*"
  AC3a: pyproject.toml ruff src contains all 7 serve/*/src entries
  AC3b: pyproject.toml ruff src contains no packages/ entries
  AC4a: pyproject.toml ruff per-file-ignores has serve/*/examples/**/*.py key
  AC4b: pyproject.toml ruff per-file-ignores has serve/*/tests/**/*.py key
  AC4c: pyproject.toml ruff per-file-ignores has no packages/ keys
  AC5a: pyproject.toml pytest testpaths contains "serve"
  AC5b: pyproject.toml pytest testpaths does not contain "packages"
  AC6:  uv sync exits 0 after rename (preconditioned on serve/ existing)
  AC7:  all 7 namespace packages importable via uv run python
  AC8:  MCP server modules still resolve after rename
  AC9a: .gitignore contains serve/*/dist/ pattern
  AC9b: .gitignore does not contain packages/*/dist/ pattern
  AC10a: .pre-commit-config.yaml bandit args reference serve/
  AC10b: .pre-commit-config.yaml bandit args do not reference packages/
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent
PYPROJECT = WORKSPACE_ROOT / "pyproject.toml"
GITIGNORE = WORKSPACE_ROOT / ".gitignore"
PRE_COMMIT = WORKSPACE_ROOT / ".pre-commit-config.yaml"

SERVE_DIR = WORKSPACE_ROOT / "serve"
PACKAGES_DIR = WORKSPACE_ROOT / "packages"

EXPECTED_SUBPACKAGES = frozenset({
    "orchestrator",
    "knowledge",
    "mcp-kanban",
    "mcp-knowledge",
    "mcp-memory",
    "mcp-project",
    "voice",
})


class TestFromAC_RenamePackagesToServe:
    # ------------------------------------------------------------------ AC1 --

    def test_serve_directory_exists(self):
        assert SERVE_DIR.is_dir(), f"serve/ directory must exist at {SERVE_DIR}"

    def test_serve_has_all_7_subpackages(self):
        assert SERVE_DIR.is_dir(), "serve/ must exist (AC1 precondition)"
        existing = {d.name for d in SERVE_DIR.iterdir() if d.is_dir()}
        missing = EXPECTED_SUBPACKAGES - existing
        assert not missing, f"Missing sub-packages in serve/: {sorted(missing)}"

    def test_serve_has_exactly_7_subpackages(self):
        # boundary: no extras were added or missed during git mv
        assert SERVE_DIR.is_dir(), "serve/ must exist (AC1 precondition)"
        found = {d.name for d in SERVE_DIR.iterdir() if d.is_dir()}
        assert found == EXPECTED_SUBPACKAGES, (
            f"Expected exactly {sorted(EXPECTED_SUBPACKAGES)}, got {sorted(found)}"
        )

    def test_packages_directory_removed(self):
        assert not PACKAGES_DIR.exists(), (
            f"packages/ must not exist after rename — still found at {PACKAGES_DIR}"
        )

    # ------------------------------------------------------------------ AC2 --

    def test_workspace_members_updated_to_serve(self):
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        members = config["tool"]["uv"]["workspace"]["members"]
        assert members == ["serve/*"], f"Expected members=['serve/*'], got {members}"

    def test_workspace_members_no_longer_packages(self):
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        members = config["tool"]["uv"]["workspace"]["members"]
        assert "packages/*" not in members, (
            f"Old packages/* still in workspace members: {members}"
        )

    # ------------------------------------------------------------------ AC3 --

    def test_ruff_src_paths_contain_all_7_serve_entries(self):
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        src_paths = set(config["tool"]["ruff"]["src"])
        expected = {f"serve/{pkg}/src" for pkg in EXPECTED_SUBPACKAGES}
        missing = expected - src_paths
        assert not missing, f"Missing serve/ src entries in ruff config: {sorted(missing)}"

    def test_ruff_src_paths_no_packages_entries(self):
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        src_paths = config["tool"]["ruff"]["src"]
        stale = [p for p in src_paths if p.startswith("packages/")]
        assert not stale, f"Old packages/ paths still in ruff src: {stale}"

    # ------------------------------------------------------------------ AC4 --

    def test_ruff_per_file_ignores_examples_key_updated(self):
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        ignores = config["tool"]["ruff"]["lint"]["per-file-ignores"]
        assert "serve/*/examples/**/*.py" in ignores, (
            "Key 'serve/*/examples/**/*.py' not found in ruff per-file-ignores"
        )

    def test_ruff_per_file_ignores_tests_key_updated(self):
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        ignores = config["tool"]["ruff"]["lint"]["per-file-ignores"]
        assert "serve/*/tests/**/*.py" in ignores, (
            "Key 'serve/*/tests/**/*.py' not found in ruff per-file-ignores"
        )

    def test_ruff_per_file_ignores_no_packages_keys(self):
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        ignores = config["tool"]["ruff"]["lint"]["per-file-ignores"]
        stale_keys = [k for k in ignores if k.startswith("packages/")]
        assert not stale_keys, (
            f"Old packages/ keys still in ruff per-file-ignores: {stale_keys}"
        )

    # ------------------------------------------------------------------ AC5 --

    def test_pytest_testpaths_contains_serve(self):
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        testpaths = config["tool"]["pytest"]["ini_options"]["testpaths"]
        assert "serve" in testpaths, (
            f"'serve' not in pytest testpaths: {testpaths}"
        )

    def test_pytest_testpaths_no_packages_entry(self):
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        testpaths = config["tool"]["pytest"]["ini_options"]["testpaths"]
        assert "packages" not in testpaths, (
            f"Old 'packages' entry still in pytest testpaths: {testpaths}"
        )

    # ------------------------------------------------------------------ AC6 --

    def test_uv_sync_succeeds_after_rename(self):
        # preconditions: rename must be complete before uv sync is meaningful
        assert SERVE_DIR.is_dir(), "serve/ must exist — rename not yet done"
        assert not PACKAGES_DIR.exists(), "packages/ must be gone after rename"
        result = subprocess.run(
            ["uv", "sync"],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
        )
        assert result.returncode == 0, (
            f"uv sync failed after rename\n"
            f"stdout: {result.stdout.decode()}\n"
            f"stderr: {result.stderr.decode()}"
        )

    # ------------------------------------------------------------------ AC7 --

    def test_all_7_namespace_packages_importable(self):
        assert SERVE_DIR.is_dir(), "serve/ must exist — rename not yet done"
        import_cmd = (
            "import owlbear; "
            "import owlbear_knowledge; "
            "import owlbear_mcp_kanban; "
            "import owlbear_mcp_knowledge; "
            "import owlbear_mcp_memory; "
            "import owlbear_mcp_project; "
            "import owlbear_voice"
        )
        result = subprocess.run(
            ["uv", "run", "python", "-c", import_cmd],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
        )
        assert result.returncode == 0, (
            f"Namespace import check failed\n"
            f"stdout: {result.stdout.decode()}\n"
            f"stderr: {result.stderr.decode()}"
        )

    # ------------------------------------------------------------------ AC8 --

    def test_mcp_server_modules_still_resolve(self):
        assert SERVE_DIR.is_dir(), "serve/ must exist — rename not yet done"
        servers = [
            "owlbear_mcp_kanban.server",
            "owlbear_mcp_knowledge.server",
            "owlbear_mcp_memory.server",
            "owlbear_mcp_project.server",
        ]
        import_cmd = "; ".join(f"import {s}" for s in servers)
        result = subprocess.run(
            ["uv", "run", "python", "-c", import_cmd],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
        )
        assert result.returncode == 0, (
            f"MCP server module imports failed after rename\n"
            f"stdout: {result.stdout.decode()}\n"
            f"stderr: {result.stderr.decode()}"
        )

    # ------------------------------------------------------------------ AC9 --

    def test_gitignore_has_serve_dist_pattern(self):
        content = GITIGNORE.read_text(encoding="utf-8")
        assert "serve/*/dist/" in content, (
            "Pattern 'serve/*/dist/' not found in .gitignore"
        )

    def test_gitignore_no_packages_dist_pattern(self):
        content = GITIGNORE.read_text(encoding="utf-8")
        assert "packages/*/dist/" not in content, (
            "Old pattern 'packages/*/dist/' still present in .gitignore"
        )

    # ----------------------------------------------------------------- AC10 --

    def test_precommit_bandit_references_serve(self):
        content = PRE_COMMIT.read_text(encoding="utf-8")
        assert "serve/" in content, (
            "bandit path 'serve/' not found in .pre-commit-config.yaml"
        )

    def test_precommit_bandit_no_packages_reference(self):
        content = PRE_COMMIT.read_text(encoding="utf-8")
        assert "packages/" not in content, (
            "Old bandit path 'packages/' still in .pre-commit-config.yaml"
        )
