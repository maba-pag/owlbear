"""Integration tests for seeded VS Code settings written by setup/init.py."""

# ruff: noqa: SLF001

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


def _write_workspace_profile_association(
    user_data_root: Path,
    target_dir: Path,
    profile_id: str,
) -> None:
    storage_path = user_data_root / "User" / "globalStorage" / "storage.json"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(
        json.dumps(
            {
                "profileAssociations": {
                    "workspaces": {target_dir.resolve().as_uri(): profile_id},
                },
            }
        ),
        encoding="utf-8",
    )


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


def test_init_warns_when_existing_mcp_json_is_malformed(tmp_path: Path, init_module: types.ModuleType) -> None:
    mcp_path = tmp_path / ".vscode" / "mcp.json"
    mcp_path.parent.mkdir()
    mcp_path.write_text("{not valid json\n", encoding="utf-8")

    with pytest.warns(UserWarning, match=r"Could not parse existing .*mcp\.json"):
        init_module._write_mcp(
            _REPO_ROOT / "seed/.vscode/mcp.json",
            mcp_path,
            {
                "owlbear_rel_path": "../owlbear",
                "owlbear_abs_path": str(_REPO_ROOT),
                "target_abs_path": str(tmp_path),
            },
        )

    mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
    assert "owlbear-delivery" in mcp["servers"]


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
    owlbear_rel_path = Path(os.path.relpath(_REPO_ROOT, target_dir)).as_posix()
    assert set(mcp["servers"]) == {
        "owlbear-delivery",
        "owlbear-knowledge",
        "owlbear-memory",
        "owlbear-browser",
        "markitdown",
    }
    assert mcp["servers"]["owlbear-browser"]["env"] == {"BROWSER_ALLOWED_DOMAINS": "*"}
    for server_name in (
        "owlbear-delivery",
        "owlbear-knowledge",
        "owlbear-memory",
        "owlbear-browser",
    ):
        server = mcp["servers"][server_name]
        assert server["command"] == "uv"
        assert server["args"][:2] == ["--project", owlbear_rel_path]
    delivery_config_path = target_dir / ".owlbear/delivery/config.json"
    assert "env" not in mcp["servers"]["owlbear-delivery"]
    delivery_config = DeliveryStartupConfig.model_validate_json(delivery_config_path.read_bytes())
    assert delivery_config.schema_version == 2
    assert delivery_config.remote == "origin"
    assert delivery_config.target_branch == "main"
    assert delivery_config.github_repository == "example/project"
    gitignore = (target_dir / ".gitignore").read_text(encoding="utf-8")
    assert "/.owlbear/delivery/config.json" not in gitignore
    assert "/.owlbear/delivery/runtime/" not in gitignore
    assert "delivery/runtime/" in (target_dir / ".owlbear/.gitignore").read_text(encoding="utf-8")
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
    nested_gitignore_path = target_dir / ".owlbear/.gitignore"
    nested_gitignore_path.write_text(
        nested_gitignore_path.read_text(encoding="utf-8") + "\ncustom-consumer-rule/\n",
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
    for retired in (
        "/.owlbear/delivery/runtime/",
        "/.owlbear/delivery/worktrees/",
        "/.owlbear/worktrees/",
        "/.owlbear/target/target-runtime/capacity.json",
        "/.owlbear/target/target-runtime/integration-verification/",
        ".owlbear/target/**/.storage.lock",
        ".owlbear/briefs/draft-new/",
    ):
        assert retired not in gitignore
    assert ".owlbear/target-cutover.pending" in gitignore
    nested_gitignore = nested_gitignore_path.read_text(encoding="utf-8")
    assert "delivery/runtime/" in nested_gitignore
    assert "custom-consumer-rule/" in nested_gitignore
    assert second_rerun == first_rerun


def test_init_rerun_preserves_legacy_managed_coverage_rule(
    tmp_path: Path,
    init_module: types.ModuleType,
    run_init_without_test_surface: Callable[..., None],
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)

    gitignore_path = target_dir / ".gitignore"
    current = gitignore_path.read_text(encoding="utf-8")
    prefix, marker, managed = current.partition(init_module._OWLBEAR_GITIGNORE_MARKER)
    assert marker
    legacy_prefix = "\n".join(line for line in prefix.splitlines() if line != ".coverage.*").rstrip()
    legacy_managed = managed.rstrip() + "\n.coverage.*\n"
    gitignore_path.write_text(f"{legacy_prefix}\n\n{marker}{legacy_managed}", encoding="utf-8")

    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)

    assert ".coverage.*" in gitignore_path.read_text(encoding="utf-8").splitlines()


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
    monkeypatch.setattr(init_module, "_configure_copilot_profile", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=True)

    config = json.loads((target_dir / ".owlbear/delivery/config.json").read_text(encoding="utf-8"))
    assert config["target_branch"] == "develop"


def test_init_does_not_scaffold_retired_verification_profile(
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
    assert not profile_path.exists()

    init_module.init(
        target_dir,
        _REPO_ROOT,
        interactive=False,
        github_repository="example/project",
    )

    assert not profile_path.exists()


def test_copilot_profile_resolves_workspace_association(
    tmp_path: Path,
    init_module: types.ModuleType,
) -> None:
    target_dir = tmp_path / "project"
    user_data_root = tmp_path / "Code"
    profile_dir = user_data_root / "User" / "profiles" / "named-profile"
    target_dir.mkdir()
    profile_dir.mkdir(parents=True)
    _write_workspace_profile_association(user_data_root, target_dir, "named-profile")

    target = init_module._find_associated_copilot_profile([user_data_root], target_dir)

    assert target is not None
    assert target.associated is True
    assert target.profile_id == "named-profile"
    assert target.settings_path == profile_dir / "chatLanguageModels.json"


def test_copilot_profile_falls_back_to_one_default_user_data_root(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = tmp_path / "project"
    user_data_root = tmp_path / "Code"
    target_dir.mkdir()
    (user_data_root / "User").mkdir(parents=True)
    monkeypatch.setattr(init_module, "_running_macos_vscode_user_data_roots", list)

    target = init_module._select_default_copilot_profile([user_data_root], target_dir)

    assert target.associated is False
    assert target.profile_id is None
    assert target.settings_path == user_data_root / "User" / "chatLanguageModels.json"


def test_copilot_profile_creation_and_reasoning_settings(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = tmp_path / "project"
    user_data_root = tmp_path / "Code"
    profile_dir = user_data_root / "User" / "profiles" / "named-profile"
    target_dir.mkdir()
    profile_dir.mkdir(parents=True)
    _write_workspace_profile_association(user_data_root, target_dir, "named-profile")
    monkeypatch.setattr(init_module.sys, "platform", "darwin")
    monkeypatch.setattr(init_module, "_macos_vscode_user_data_roots", lambda: [user_data_root])
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    init_module._configure_copilot_profile(target_dir, interactive=True)

    profile_data = json.loads((profile_dir / "chatLanguageModels.json").read_text(encoding="utf-8"))
    copilot_settings = profile_data[0]["settings"]
    assert {
        model_id: copilot_settings[model_id]["reasoningEffort"] for model_id in init_module._COPILOT_REASONING_SETTINGS
    } == {
        "gpt-5.6-luna": "max",
        "gpt-5.6-sol": "high",
        "claude-opus-5": "medium",
    }


def test_copilot_profile_preserves_unrelated_entries(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = tmp_path / "project"
    user_data_root = tmp_path / "Code"
    profile_dir = user_data_root / "User" / "profiles" / "named-profile"
    profile_path = profile_dir / "chatLanguageModels.json"
    target_dir.mkdir()
    profile_dir.mkdir(parents=True)
    _write_workspace_profile_association(user_data_root, target_dir, "named-profile")
    original_data = [
        {"name": "Other provider", "vendor": "other", "settings": {"keep": True}},
        {
            "name": "GitHub Copilot Chat",
            "vendor": "copilot",
            "settings": {
                "unrelated-model": {"reasoningEffort": "low", "custom": "preserve"},
                "gpt-5.6-luna": {"custom": "preserve"},
            },
        },
    ]
    profile_path.write_text(json.dumps(original_data, indent=4) + "\n", encoding="utf-8")
    monkeypatch.setattr(init_module.sys, "platform", "darwin")
    monkeypatch.setattr(init_module, "_macos_vscode_user_data_roots", lambda: [user_data_root])
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")

    init_module._configure_copilot_profile(target_dir, interactive=True)

    profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile_data[0] == original_data[0]
    assert profile_data[1]["settings"]["unrelated-model"] == original_data[1]["settings"]["unrelated-model"]
    assert profile_data[1]["settings"]["gpt-5.6-luna"] == {
        "custom": "preserve",
        "reasoningEffort": "max",
    }
    assert profile_data[1]["settings"]["gpt-5.6-sol"] == {"reasoningEffort": "high"}
    assert profile_data[1]["settings"]["claude-opus-5"] == {"reasoningEffort": "medium"}


def test_copilot_profile_decline_preserves_file(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = tmp_path / "project"
    user_data_root = tmp_path / "Code"
    profile_dir = user_data_root / "User" / "profiles" / "named-profile"
    profile_path = profile_dir / "chatLanguageModels.json"
    target_dir.mkdir()
    profile_dir.mkdir(parents=True)
    _write_workspace_profile_association(user_data_root, target_dir, "named-profile")
    original_text = '[{"vendor": "copilot", "settings": {}}]\n'
    profile_path.write_text(original_text, encoding="utf-8")
    monkeypatch.setattr(init_module.sys, "platform", "darwin")
    monkeypatch.setattr(init_module, "_macos_vscode_user_data_roots", lambda: [user_data_root])
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    init_module._configure_copilot_profile(target_dir, interactive=True)

    assert profile_path.read_text(encoding="utf-8") == original_text


def test_copilot_profile_malformed_json_is_left_unchanged(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = tmp_path / "project"
    user_data_root = tmp_path / "Code"
    profile_dir = user_data_root / "User" / "profiles" / "named-profile"
    profile_path = profile_dir / "chatLanguageModels.json"
    target_dir.mkdir()
    profile_dir.mkdir(parents=True)
    _write_workspace_profile_association(user_data_root, target_dir, "named-profile")
    malformed_text = "{not valid json\n"
    profile_path.write_text(malformed_text, encoding="utf-8")
    monkeypatch.setattr(init_module.sys, "platform", "darwin")
    monkeypatch.setattr(init_module, "_macos_vscode_user_data_roots", lambda: [user_data_root])

    with pytest.warns(UserWarning, match="Could not inspect"):
        init_module._configure_copilot_profile(target_dir, interactive=True)

    assert profile_path.read_text(encoding="utf-8") == malformed_text


def test_copilot_profile_rejects_ambiguous_associations(
    tmp_path: Path,
    init_module: types.ModuleType,
) -> None:
    target_dir = tmp_path / "project"
    roots = [tmp_path / "Code", tmp_path / "Code - Insiders"]
    target_dir.mkdir()
    for root in roots:
        (root / "User" / "profiles" / "named-profile").mkdir(parents=True)
        _write_workspace_profile_association(root, target_dir, "named-profile")

    with pytest.raises(RuntimeError, match="Multiple VS Code profile associations"):
        init_module._find_associated_copilot_profile(roots, target_dir)


def test_copilot_profile_skips_noninteractive_and_non_macos(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    monkeypatch.setattr(
        init_module, "_macos_vscode_user_data_roots", lambda: pytest.fail("discovery should be skipped")
    )

    monkeypatch.setattr(init_module.sys, "platform", "darwin")
    with pytest.warns(UserWarning, match="non-interactive"):
        init_module._configure_copilot_profile(target_dir, interactive=False)

    monkeypatch.setattr(init_module.sys, "platform", "linux")
    init_module._configure_copilot_profile(target_dir, interactive=True)
