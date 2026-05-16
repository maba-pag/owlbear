"""Integration tests for seeded VS Code settings written by setup/init.py."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import types

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_INIT_PATH = _REPO_ROOT / "setup" / "init.py"


def _load_init_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("owlbear_setup_init_settings", _INIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def init_module() -> types.ModuleType:
    return _load_init_module()


def test_init_writes_settings_without_hook_locations_and_with_local_hints(
    tmp_path: Path, init_module: types.ModuleType
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    init_module.init(target_dir, _REPO_ROOT, interactive=False)

    settings_path = target_dir / ".vscode" / "settings.json"
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    owlbear_rel_path = Path(os.path.relpath(_REPO_ROOT, target_dir)).as_posix()

    assert "chat.hookFilesLocations" not in data
    assert data["chat.agentFilesLocations"] == {
        f"{owlbear_rel_path}/share/agents": True,
        ".owlbear/agents": True,
    }
    assert data["chat.agentSkillsLocations"] == {
        f"{owlbear_rel_path}/share/skills": True,
        ".owlbear/skills": True,
    }
    assert data["chat.instructionsFilesLocations"] == {
        f"{owlbear_rel_path}/share/instructions": True,
        ".owlbear/instructions": True,
    }
    assert data["chat.promptFilesLocations"] == {
        f"{owlbear_rel_path}/share/prompts": True,
        ".owlbear/prompts": True,
    }
    assert data["github.copilot.chat.additionalReadAccessPaths"] == [
        str(_REPO_ROOT.resolve()),
    ]
