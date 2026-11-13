"""Public runner discovery through the registered command and module entry point."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_tools.test_root import find_test_root


@pytest.fixture
def frontend_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    frontend = tmp_path / "web/src/__tests__"
    frontend.mkdir(parents=True)
    (frontend / "App.test.tsx").write_text("test('renders', () => {})")
    (tmp_path / "web/package.json").write_text(
        json.dumps({"scripts": {"test": "vitest run"}, "devDependencies": {"vitest": "^3.0.0"}})
    )
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "npm --prefix web test --"}}))
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_foo.py").write_text("def test_foo(): pass")
    return tmp_path


@pytest.mark.usefixtures("frontend_project")
def test_registered_command_resolves_python_despite_root_npm_proxy(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    entry = next(ep for ep in importlib.metadata.entry_points(group="console_scripts") if ep.name == "test-root")
    monkeypatch.setattr(sys, "argv", ["test-root", "tests/test_foo.py"])

    entry.load()()

    assert json.loads(capsys.readouterr().out) == {
        "test_path": "tests/test_foo.py",
        "cwd": ".",
        "toolchain": "pytest",
        "cmd": "uv run pytest",
    }


def test_multiple_paths_return_their_own_runners(frontend_project: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "owlbear_tools.test_root", "tests/test_foo.py", "web/src/__tests__/App.test.tsx"],
        capture_output=True,
        text=True,
        cwd=frontend_project,
        check=False,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == [
        {"test_path": "tests/test_foo.py", "cwd": ".", "toolchain": "pytest", "cmd": "uv run pytest"},
        {"test_path": "web/src/__tests__/App.test.tsx", "cwd": "web", "toolchain": "vitest", "cmd": "npm test"},
    ]


@pytest.mark.usefixtures("frontend_project")
def test_nonexistent_path_falls_back_to_pytest() -> None:
    result = find_test_root("nonexistent/test_bar.py")
    assert result["toolchain"] == "pytest"
    assert result["cwd"] == "."


def test_no_args_prints_usage() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "owlbear_tools.test_root"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Usage" in result.stderr
