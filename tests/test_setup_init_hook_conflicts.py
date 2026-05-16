"""Tests for setup/init.py hook conflict handling."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import types

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_INIT_PATH = _REPO_ROOT / "setup" / "init.py"


def _load_init_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("owlbear_setup_init", _INIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def init_module() -> types.ModuleType:
    return _load_init_module()


def _make_seed_hook(owlbear_dir: Path, content: str) -> Path:
    hook_path = owlbear_dir / "seed" / ".owlbear" / "hooks" / "deny-writes.py"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(content, encoding="utf-8")
    return hook_path


def _make_existing_hook(target_dir: Path, content: str) -> Path:
    hook_path = target_dir / ".owlbear" / "hooks" / "deny-writes.py"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(content, encoding="utf-8")
    return hook_path


def test_noninteractive_conflict_skips_without_replace_flag(tmp_path: Path, init_module: types.ModuleType) -> None:
    owlbear_dir = tmp_path / "owlbear"
    target_dir = tmp_path / "project"
    _make_seed_hook(owlbear_dir, "seed-version")
    existing = _make_existing_hook(target_dir, "local-version")

    with pytest.warns(UserWarning, match="Existing hook file differs"):
        init_module.init(target_dir, owlbear_dir, interactive=False)

    assert existing.read_text(encoding="utf-8") == "local-version"


def test_replace_hooks_flag_overwrites_existing_hook(tmp_path: Path, init_module: types.ModuleType) -> None:
    owlbear_dir = tmp_path / "owlbear"
    target_dir = tmp_path / "project"
    _make_seed_hook(owlbear_dir, "seed-version")
    existing = _make_existing_hook(target_dir, "local-version")

    init_module.init(target_dir, owlbear_dir, interactive=False, replace_hooks=True)

    assert existing.read_text(encoding="utf-8") == "seed-version"


def test_interactive_replace_overwrites_existing_hook(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owlbear_dir = tmp_path / "owlbear"
    target_dir = tmp_path / "project"
    _make_seed_hook(owlbear_dir, "seed-version")
    existing = _make_existing_hook(target_dir, "local-version")
    monkeypatch.setattr("builtins.input", lambda _prompt: "replace")

    init_module.init(target_dir, owlbear_dir, interactive=True)

    assert existing.read_text(encoding="utf-8") == "seed-version"


def test_interactive_skip_keeps_existing_hook(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owlbear_dir = tmp_path / "owlbear"
    target_dir = tmp_path / "project"
    _make_seed_hook(owlbear_dir, "seed-version")
    existing = _make_existing_hook(target_dir, "local-version")
    monkeypatch.setattr("builtins.input", lambda _prompt: "skip")

    init_module.init(target_dir, owlbear_dir, interactive=True)

    assert existing.read_text(encoding="utf-8") == "local-version"


def test_interactive_cancel_raises(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owlbear_dir = tmp_path / "owlbear"
    target_dir = tmp_path / "project"
    _make_seed_hook(owlbear_dir, "seed-version")
    existing = _make_existing_hook(target_dir, "local-version")
    monkeypatch.setattr("builtins.input", lambda _prompt: "cancel")

    with pytest.raises(RuntimeError, match="Hook seeding cancelled"):
        init_module.init(target_dir, owlbear_dir, interactive=True)

    assert existing.read_text(encoding="utf-8") == "local-version"
