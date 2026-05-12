"""Tests for the test-root discovery utility."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_tools.test_root import find_test_root


@pytest.fixture()
def frontend_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a mock project with a frontend package."""
    monkeypatch.chdir(tmp_path)

    # Create a frontend package with vitest
    frontend = tmp_path / "web" / "src" / "__tests__"
    frontend.mkdir(parents=True)
    (frontend / "App.test.tsx").write_text("test('renders', () => {})")

    pkg = tmp_path / "web" / "package.json"
    pkg.write_text(
        json.dumps(
            {
                "name": "my-frontend",
                "scripts": {"test": "vitest run"},
                "devDependencies": {"vitest": "^3.0.0"},
            }
        )
    )

    # Create a Python test at root
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_foo.py").write_text("def test_foo(): pass")

    return tmp_path


class TestFindTestRoot:
    """Unit tests for find_test_root()."""

    pytestmark = pytest.mark.usefixtures("frontend_project")

    def test_frontend_tsx_resolves_to_vitest(self) -> None:
        result = find_test_root("web/src/__tests__/App.test.tsx")
        assert result["toolchain"] == "vitest"
        assert result["cwd"] == "web"
        assert result["cmd"] == "npm test"

    def test_python_test_resolves_to_pytest(self) -> None:
        result = find_test_root("tests/test_foo.py")
        assert result["toolchain"] == "pytest"
        assert result["cwd"] == "."
        assert result["cmd"] == "uv run pytest"

    def test_nonexistent_path_falls_back_to_pytest(self) -> None:
        result = find_test_root("nonexistent/test_bar.py")
        assert result["toolchain"] == "pytest"
        assert result["cwd"] == "."

    def test_returns_original_test_path(self) -> None:
        path = "web/src/__tests__/App.test.tsx"
        result = find_test_root(path)
        assert result["test_path"] == path


class TestCLIEntryPoint:
    """Integration tests for the `test-root` CLI."""

    def test_entry_point_is_resolvable(self) -> None:
        eps = importlib.metadata.entry_points(group="console_scripts")
        names = [ep.name for ep in eps]
        assert "test-root" in names

    def test_single_path_returns_object(self, frontend_project: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "owlbear_tools.test_root", "tests/test_foo.py"],
            capture_output=True,
            text=True,
            cwd=frontend_project,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["toolchain"] == "pytest"

    def test_multiple_paths_returns_array(self, frontend_project: Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "owlbear_tools.test_root",
                "tests/test_foo.py",
                "web/src/__tests__/App.test.tsx",
            ],
            capture_output=True,
            text=True,
            cwd=frontend_project,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["toolchain"] == "pytest"
        assert data[1]["toolchain"] == "vitest"

    def test_no_args_prints_usage(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "owlbear_tools.test_root"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Usage" in result.stderr
