"""Behavioral checks for the non-blocking lint-changed hook warnings."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).parent.parent
_HOOK_PATH = _REPO_ROOT / ".owlbear/hooks/lint-changed.py"


def _load_hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lint_changed_hook", _HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True, text=True)  # noqa: S603, S607


def _repository(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "--quiet")
    source = tmp_path / "src/module.py"
    source.parent.mkdir()
    source.write_text("\n".join(f"before_{line} = {line}" for line in range(120)) + "\n", encoding="utf-8")
    _git(tmp_path, "add", "src/module.py")
    _git(tmp_path, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--quiet", "-m", "base")
    return source


def test_extracts_apply_patch_paths() -> None:
    hook = _load_hook()
    patch = """*** Begin Patch
*** Update File: /repo/src/module.py
*** Add File: /repo/tests/test_module.py
*** End Patch"""

    assert hook._extract_paths("apply_patch", {"input": patch}) == [  # noqa: SLF001
        "/repo/src/module.py",
        "/repo/tests/test_module.py",
    ]


def test_targeted_edit_has_no_minimum_change_warning(tmp_path: Path, monkeypatch) -> None:
    hook = _load_hook()
    source = _repository(tmp_path)
    lines = source.read_text(encoding="utf-8").splitlines()
    lines[0] = "after_0 = 0"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert hook._minimum_change_warnings([str(source)], tmp_path) == []  # noqa: SLF001


def test_warns_for_new_test_and_large_replacement(tmp_path: Path, monkeypatch) -> None:
    hook = _load_hook()
    source = _repository(tmp_path)
    source.write_text("\n".join(f"after_{line} = {line}" for line in range(120)) + "\n", encoding="utf-8")
    test_file = tmp_path / "tests/test_module.py"
    test_file.parent.mkdir()
    test_file.write_text("\n".join(f"assert {line} == {line}" for line in range(300)) + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    warnings = hook._minimum_change_warnings([str(source), str(test_file)], tmp_path)  # noqa: SLF001

    assert any("large replacement" in warning for warning in warnings)
    assert any("new test file" in warning for warning in warnings)
    assert any("test-heavy edit" in warning for warning in warnings)
