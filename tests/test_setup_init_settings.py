"""Integration tests for seeded VS Code settings written by setup/init.py."""

from __future__ import annotations

import importlib.util
import json
import os
import types
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest
from owlbear_delivery import DeliveryStartupConfig

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
    tmp_path: Path,
    init_module: types.ModuleType,
    run_init_without_test_surface: Callable[..., None],
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)

    settings_path = target_dir / ".vscode" / "settings.json"
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    owlbear_rel_path = Path(os.path.relpath(_REPO_ROOT, target_dir)).as_posix()

    assert "chat.hookFilesLocations" not in data
    assert data["chat.agentHost.copilot.toolSearch.enabled"] is True
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


def test_settings_template_escapes_windows_paths(tmp_path: Path, init_module: types.ModuleType) -> None:
    settings_path = tmp_path / "settings.json"

    init_module._write_settings(
        _REPO_ROOT / "seed/.vscode/settings.json",
        settings_path,
        {
            "owlbear_rel_path": "../owlbear",
            "owlbear_abs_path": r"C:\Dev\owlbear",
            "target_abs_path": r"C:\Dev\project",
        },
    )

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["github.copilot.chat.additionalReadAccessPaths"] == [r"C:\Dev\owlbear"]


def test_init_creates_delivery_policy_without_runtime_selection_artifacts(
    tmp_path: Path,
    init_module: types.ModuleType,
    run_init_without_test_surface: Callable[..., None],
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with patch("subprocess.run") as package_install:
        run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)

    config = DeliveryStartupConfig.model_validate_json((target_dir / ".owlbear/delivery/config.json").read_bytes())
    assert config.target_branch
    for retired_path in (
        ".owlbear/target",
        ".owlbear/worktrees",
        ".owlbear/adapters",
        ".owlbear/target-cutover-request.json",
        ".owlbear/target-cutover.json",
        ".owlbear/delivery/runtime",
        ".owlbear/delivery/worktrees",
    ):
        assert not (target_dir / retired_path).exists()
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
    assert delivery_config.schema_version == 2
    assert delivery_config.remote == "origin"
    assert delivery_config.target_branch == "main"
    assert delivery_config.github_repository == "example/project"
    assert "/.owlbear/delivery/config.json" not in (target_dir / ".gitignore").read_text(encoding="utf-8")
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
    run_init_without_test_surface: Callable[..., None],
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)

    settings_path = target_dir / ".vscode/settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["example.userSetting"] = "preserved"
    settings["chat.tools.terminal.autoApprove"]["example-command"] = False
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    delivery_config_path = target_dir / ".owlbear/delivery/config.json"
    delivery_config = json.loads(delivery_config_path.read_text(encoding="utf-8"))
    delivery_config["target_branch"] = "release"
    delivery_config_path.write_text(json.dumps(delivery_config), encoding="utf-8")
    gitignore_path = target_dir / ".gitignore"
    gitignore_path.write_text(
        gitignore_path.read_text(encoding="utf-8")
        + "\n# Host-local Delivery worktrees and mutable capacity ledger\n"
        + "/.owlbear/worktrees/\n"
        + "/.owlbear/target/target-runtime/capacity.json\n"
        + "/.owlbear/target/target-runtime/integration-verification/\n"
        + ".owlbear/target/**/.storage.lock\n"
        + ".owlbear/target-cutover.pending\n"
        + "# Brief drafts (transient template directory)\n"
        + ".owlbear/briefs/draft-new/\n",
        encoding="utf-8",
    )

    records = {
        ".owlbear/target/changes/example/authority.json": b'{"authority":"preserved"}\n',
        ".owlbear/target/changes/example/target-runtime/state.json": b'{"runtime":"preserved"}\n',
    }
    for relative_path, content in records.items():
        path = target_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)
    first_rerun = {path.relative_to(target_dir): path.read_bytes() for path in target_dir.rglob("*") if path.is_file()}
    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)
    second_rerun = {path.relative_to(target_dir): path.read_bytes() for path in target_dir.rglob("*") if path.is_file()}

    merged_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert merged_settings["example.userSetting"] == "preserved"
    assert merged_settings["chat.tools.terminal.autoApprove"]["example-command"] is False
    assert json.loads(delivery_config_path.read_text(encoding="utf-8"))["target_branch"] == "release"
    assert all((target_dir / path).read_bytes() == content for path, content in records.items())
    gitignore = gitignore_path.read_text(encoding="utf-8")
    for retired in (".owlbear/briefs/draft-new/",):
        assert retired not in gitignore
    for preserved_legacy_rule in (
        "/.owlbear/worktrees/",
        "/.owlbear/target/target-runtime/capacity.json",
        "/.owlbear/target/target-runtime/integration-verification/",
        ".owlbear/target/**/.storage.lock",
        ".owlbear/target-cutover.pending",
    ):
        assert preserved_legacy_rule in gitignore
    assert "/.owlbear/delivery/runtime/" in gitignore
    assert "/.owlbear/delivery/worktrees/" in gitignore
    assert second_rerun == first_rerun


def test_init_migrates_exact_schema_one_delivery_policy(
    tmp_path: Path,
    init_module: types.ModuleType,
    run_init_without_test_surface: Callable[..., None],
) -> None:
    target_dir = tmp_path / "project"
    config_path = target_dir / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('{"schema_version":1,"integration_target":"release"}\n', encoding="utf-8")

    run_init_without_test_surface(
        init_module.init,
        target_dir,
        _REPO_ROOT,
        interactive=False,
        remote="upstream",
        github_repository="example/project",
    )

    config = DeliveryStartupConfig.model_validate_json(config_path.read_bytes())
    assert config.model_dump() == {
        "schema_version": 2,
        "remote": "upstream",
        "target_branch": "release",
        "github_repository": "example/project",
    }


def test_init_requires_exact_github_identity_when_remote_cannot_supply_it(
    tmp_path: Path,
    init_module: types.ModuleType,
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with pytest.raises(RuntimeError, match="GitHub repository must be provided"):
        init_module.init(target_dir, _REPO_ROOT, interactive=False)

    assert not (target_dir / ".owlbear/delivery/config.json").exists()


def test_init_uses_requested_target_branch_without_local_ref(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    run_init_without_test_surface: Callable[..., None],
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    monkeypatch.setattr(init_module, "_valid_branch_name", lambda _target, branch: branch == "release")

    run_init_without_test_surface(
        init_module.init,
        target_dir,
        _REPO_ROOT,
        interactive=False,
        target_branch="release",
    )

    config = json.loads((target_dir / ".owlbear/delivery/config.json").read_text(encoding="utf-8"))
    assert config["target_branch"] == "release"


def test_init_interactive_target_defaults_to_checked_out_branch(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    run_init_without_test_surface: Callable[..., None],
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    monkeypatch.setattr(init_module, "_current_branch", lambda _target: "develop")
    monkeypatch.setattr(init_module, "_valid_branch_name", lambda _target, branch: branch == "develop")
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=True)

    config = json.loads((target_dir / ".owlbear/delivery/config.json").read_text(encoding="utf-8"))
    assert config["target_branch"] == "develop"


def test_init_scaffolds_and_preserves_detected_verification_profile(
    tmp_path: Path,
    init_module: types.ModuleType,
) -> None:
    target_dir = tmp_path / "project"
    (target_dir / "tests").mkdir(parents=True)
    (target_dir / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
    (target_dir / "package.json").write_text('{"scripts":{"test":"vitest run"}}\n', encoding="utf-8")
    (target_dir / "package-lock.json").write_text("{}\n", encoding="utf-8")

    init_module.init(
        target_dir,
        _REPO_ROOT,
        interactive=False,
        github_repository="example/project",
    )

    profile_path = target_dir / ".owlbear/delivery/verification.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert [step["step_id"] for step in profile["steps"]] == [
        "python-tests",
        "node-install",
        "node-tests",
    ]
    assert profile["steps"][0]["argv"] == ["uv", "run", "--locked", "pytest"]
    profile["steps"][0]["timeout_seconds"] = 42
    profile_path.write_text(json.dumps(profile), encoding="utf-8")

    init_module.init(
        target_dir,
        _REPO_ROOT,
        interactive=False,
        github_repository="example/project",
    )

    preserved = json.loads(profile_path.read_text(encoding="utf-8"))
    assert preserved["steps"][0]["timeout_seconds"] == 42
