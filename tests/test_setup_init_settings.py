"""Integration tests for seeded VS Code settings written by setup/init.py."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import types
from unittest.mock import patch

import pytest
from owlbear_delivery import DeliveryStartupConfig, TargetCutoverRequest, authorize_target_mutation

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


def test_init_creates_only_empty_target_control_plane_stores(
    tmp_path: Path,
    init_module: types.ModuleType,
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with patch("subprocess.run") as package_install:
        init_module.init(target_dir, _REPO_ROOT, interactive=False)

    assert (target_dir / ".owlbear/target/changes").is_dir()
    request_path = target_dir / ".owlbear/target-cutover-request.json"
    request = TargetCutoverRequest.model_validate_json(request_path.read_bytes())
    assert request.receipt_path == ".owlbear/target-cutover.json"
    activation = authorize_target_mutation(target_dir, request)
    assert activation.authorities == ()
    assert not (target_dir / ".owlbear/changes").exists()
    assert not (target_dir / ".owlbear/kanban").exists()
    assert not (target_dir / "openspec").exists()
    settings = json.loads((target_dir / ".vscode/settings.json").read_text(encoding="utf-8"))
    shared_locations = {
        "chat.agentFilesLocations": _REPO_ROOT / "share/agents",
        "chat.agentSkillsLocations": _REPO_ROOT / "share/skills",
        "chat.instructionsFilesLocations": _REPO_ROOT / "share/instructions",
        "chat.promptFilesLocations": _REPO_ROOT / "share/prompts",
    }
    for setting, source in shared_locations.items():
        configured = {
            (target_dir / path).resolve()
            for path, enabled in settings[setting].items()
            if enabled and not path.startswith(".owlbear/")
        }
        assert configured == {source.resolve()}
        assert any(source.rglob("*"))
    installed_hooks = {path.name for path in (target_dir / ".owlbear/hooks").glob("*.py")}
    seed_hooks = {path.name for path in (_REPO_ROOT / "seed/.owlbear/hooks").glob("*.py")}
    assert installed_hooks == seed_hooks
    mcp = json.loads((target_dir / ".vscode/mcp.json").read_text(encoding="utf-8"))
    assert set(mcp["servers"]) == {
        "owlbear-delivery",
        "owlbear-knowledge",
        "owlbear-memory",
        "owlbear-browser",
        "markitdown",
    }
    delivery_config_path = target_dir / ".owlbear/delivery/config.json"
    assert "env" not in mcp["servers"]["owlbear-delivery"]
    delivery_config = DeliveryStartupConfig.model_validate_json(delivery_config_path.read_bytes())
    assert delivery_config.schema_version == 1
    assert delivery_config.integration_target == "main"
    assert (_REPO_ROOT / "serve/cockpit/dist/index.html").is_file()
    assert (_REPO_ROOT / "serve/cockpit/dist/assets").is_dir()
    installed_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in target_dir.rglob("*")
        if path.is_file() and path.suffix in {"", ".json", ".jsonc", ".md", ".yml", ".yaml"}
    )
    assert "openspec" not in installed_text.lower()
    assert ".owlbear/kanban/tasks" not in installed_text
    assert ".owlbear/kanban/decisions" not in installed_text
    package_install.assert_not_called()


def test_init_rerun_preserves_user_settings_and_target_records(
    tmp_path: Path,
    init_module: types.ModuleType,
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    init_module.init(target_dir, _REPO_ROOT, interactive=False)

    settings_path = target_dir / ".vscode/settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["example.userSetting"] = "preserved"
    settings["chat.tools.terminal.autoApprove"]["example-command"] = False
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    delivery_config_path = target_dir / ".owlbear/delivery/config.json"
    delivery_config = json.loads(delivery_config_path.read_text(encoding="utf-8"))
    delivery_config["integration_target"] = "release"
    delivery_config_path.write_text(json.dumps(delivery_config), encoding="utf-8")

    records = {
        ".owlbear/target/changes/example/authority.json": b'{"authority":"preserved"}\n',
        ".owlbear/target/changes/example/target-runtime/state.json": b'{"runtime":"preserved"}\n',
    }
    for relative_path, content in records.items():
        path = target_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    init_module.init(target_dir, _REPO_ROOT, interactive=False)
    first_rerun = {path.relative_to(target_dir): path.read_bytes() for path in target_dir.rglob("*") if path.is_file()}
    init_module.init(target_dir, _REPO_ROOT, interactive=False)
    second_rerun = {path.relative_to(target_dir): path.read_bytes() for path in target_dir.rglob("*") if path.is_file()}

    merged_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert merged_settings["example.userSetting"] == "preserved"
    assert merged_settings["chat.tools.terminal.autoApprove"]["example-command"] is False
    assert json.loads(delivery_config_path.read_text(encoding="utf-8"))["integration_target"] == "release"
    assert all((target_dir / path).read_bytes() == content for path, content in records.items())
    assert second_rerun == first_rerun


def test_init_uses_requested_existing_integration_target(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    monkeypatch.setattr(init_module, "_branch_exists", lambda _target, branch: branch == "release")

    init_module.init(
        target_dir,
        _REPO_ROOT,
        interactive=False,
        integration_target="release",
    )

    config = json.loads((target_dir / ".owlbear/delivery/config.json").read_text(encoding="utf-8"))
    assert config["integration_target"] == "release"


def test_init_interactive_target_defaults_to_checked_out_branch(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    monkeypatch.setattr(init_module, "_current_branch", lambda _target: "develop")
    monkeypatch.setattr(init_module, "_branch_exists", lambda _target, branch: branch == "develop")
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    init_module.init(target_dir, _REPO_ROOT, interactive=True)

    config = json.loads((target_dir / ".owlbear/delivery/config.json").read_text(encoding="utf-8"))
    assert config["integration_target"] == "develop"


def test_init_preserves_pre_cutover_store_without_creating_target(
    tmp_path: Path,
    init_module: types.ModuleType,
) -> None:
    target_dir = tmp_path / "project"
    legacy_record = target_dir / ".owlbear/kanban/jobs/000001.yaml"
    legacy_record.parent.mkdir(parents=True)
    legacy_record.write_text("job: preserved\n", encoding="utf-8")

    init_module.init(target_dir, _REPO_ROOT, interactive=False)

    assert legacy_record.read_text(encoding="utf-8") == "job: preserved\n"
    assert not (target_dir / ".owlbear/target").exists()
    assert not (target_dir / ".owlbear/target-cutover.json").exists()
