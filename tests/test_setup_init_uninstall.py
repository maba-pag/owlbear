"""Tests for the conservative setup/init.py uninstall mode."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_INIT_PATH = _REPO_ROOT / "setup" / "init.py"


def _load_init_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("owlbear_setup_init_uninstall", _INIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _initialize(
    module: types.ModuleType,
    target_dir: Path,
    *,
    owlbear_dir: Path = _REPO_ROOT,
    refresh_configs: bool = False,
) -> None:
    module.init(
        target_dir,
        owlbear_dir,
        interactive=False,
        refresh_configs=refresh_configs,
        github_repository="example/project",
    )


def _copy_owlbear_seed(tmp_path: Path) -> Path:
    owlbear_dir = tmp_path / "owlbear"
    shutil.copytree(_REPO_ROOT / "seed", owlbear_dir / "seed")
    return owlbear_dir


def test_uninstall_removes_unchanged_seed_surfaces_and_preserves_user_state(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    custom_settings = {"user.setting": True}
    vscode_dir = target_dir / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "settings.json").write_text(json.dumps(custom_settings), encoding="utf-8")
    custom_mcp = {"servers": {"local-server": {"command": "local"}}, "userRoot": True}
    (vscode_dir / "mcp.json").write_text(json.dumps(custom_mcp), encoding="utf-8")

    custom_root_gitignore = "consumer-rule/\n"
    (target_dir / ".gitignore").write_text(custom_root_gitignore, encoding="utf-8")
    custom_nested_gitignore = "consumer-cache/\n"
    nested_gitignore = target_dir / ".owlbear" / ".gitignore"
    nested_gitignore.parent.mkdir(parents=True)
    nested_gitignore.write_text(custom_nested_gitignore, encoding="utf-8")

    custom_instructions = "# Consumer instructions\n"
    instructions = target_dir / ".github" / "copilot-instructions.md"
    instructions.parent.mkdir()
    instructions.write_text(custom_instructions, encoding="utf-8")
    custom_editorconfig = "root = false\n"
    (target_dir / ".editorconfig").write_text(custom_editorconfig, encoding="utf-8")

    custom_hook = target_dir / ".owlbear" / "hooks" / "deny-writes.py"
    custom_hook.parent.mkdir(parents=True, exist_ok=True)
    custom_hook.write_text("# consumer hook\n", encoding="utf-8")

    _initialize(module, target_dir)
    delivery_config = target_dir / ".owlbear" / "delivery" / "config.json"
    delivery_config_before = delivery_config.read_bytes()

    assert module.uninstall(target_dir, _REPO_ROOT, confirm=False).completed is True

    assert json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8")) == custom_settings
    assert json.loads((vscode_dir / "mcp.json").read_text(encoding="utf-8")) == custom_mcp
    assert (target_dir / ".gitignore").read_text(encoding="utf-8") == custom_root_gitignore
    assert nested_gitignore.read_text(encoding="utf-8") == custom_nested_gitignore
    assert instructions.read_text(encoding="utf-8") == custom_instructions
    assert (target_dir / ".editorconfig").read_text(encoding="utf-8") == custom_editorconfig
    assert custom_hook.read_text(encoding="utf-8") == "# consumer hook\n"
    assert delivery_config.read_bytes() == delivery_config_before

    assert not (target_dir / ".gitattributes").exists()
    assert not (target_dir / ".markdownlint.json").exists()
    assert not (target_dir / ".markdownlint-cli2.jsonc").exists()
    assert not (target_dir / ".markdownlintignore").exists()
    assert not (target_dir / ".yamllint.yml").exists()
    assert not (target_dir / ".owlbear" / "install-manifest.json").exists()
    assert not (target_dir / ".owlbear" / "hooks" / "allow-stances-only.py").exists()
    assert not (target_dir / ".owlbear" / "scripts" / "test-root.py").exists()
    assert not (target_dir / ".owlbear" / "knowledge" / ".gitkeep").exists()
    assert not (target_dir / "store" / "knowledge" / ".gitkeep").exists()


def test_cli_uninstall_does_not_require_delivery_identity(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir)

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(_INIT_PATH), "--uninstall", "--yes"],
        cwd=target_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "uninstalled" in result.stdout
    assert (target_dir / ".owlbear" / "delivery" / "config.json").exists()


def test_cli_uninstall_requires_explicit_confirmation_without_a_tty(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir)

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(_INIT_PATH), "--uninstall"],
        cwd=target_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--yes" in result.stderr or "--yes" in result.stdout
    assert (target_dir / ".owlbear" / "hooks" / "deny-writes.py").exists()


def test_cli_uninstall_dry_run_preserves_files(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir)

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(_INIT_PATH), "--uninstall", "--dry-run"],
        cwd=target_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "dry-run" in result.stdout
    assert "would remove" in result.stdout
    assert (target_dir / ".owlbear" / "hooks" / "deny-writes.py").exists()


def test_uninstall_dry_run_returns_actions_without_an_out_parameter(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir)

    result = module.uninstall(target_dir, _REPO_ROOT, confirm=False, dry_run=True)

    assert result.completed is True
    assert result.actions
    assert (target_dir / ".owlbear" / "hooks" / "deny-writes.py").exists()


def test_uninstall_preserves_preexisting_setting_equal_to_seed(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    settings_path = target_dir / ".vscode" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text('{"accessibility.chat.showCheckmarks": true}', encoding="utf-8")

    _initialize(module, target_dir)
    result = module.uninstall(target_dir, _REPO_ROOT, confirm=False)

    assert result.completed is True
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "accessibility.chat.showCheckmarks": True,
    }


def test_uninstall_preserves_jsonc_comments_when_settings_changed(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir)
    settings_path = target_dir / ".vscode" / "settings.json"
    customized = "// Keep this project note.\n" + settings_path.read_text(encoding="utf-8")
    settings_path.write_text(customized, encoding="utf-8")

    module.uninstall(target_dir, _REPO_ROOT, confirm=False)

    assert settings_path.read_text(encoding="utf-8") == customized


def test_uninstall_does_not_follow_parent_symlink_outside_target(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir)

    outside_hooks = tmp_path / "outside" / "hooks"
    outside_hooks.mkdir(parents=True)
    outside_hook = outside_hooks / "deny-writes.py"
    outside_hook.write_bytes((target_dir / ".owlbear/hooks/deny-writes.py").read_bytes())
    shutil.rmtree(target_dir / ".owlbear/hooks")
    (target_dir / ".owlbear/hooks").symlink_to(outside_hooks, target_is_directory=True)

    result = module.uninstall(target_dir, _REPO_ROOT, confirm=False)

    assert outside_hook.exists()
    assert any("outside target" in action for action in result.actions)


def test_uninstall_rejects_targets_nested_in_owlbear_checkout() -> None:
    module = _load_init_module()

    with pytest.raises(RuntimeError, match="descendants"):
        module.uninstall(_REPO_ROOT / "seed", _REPO_ROOT, confirm=False)


def test_uninstall_uses_install_digest_after_seed_drift(tmp_path: Path) -> None:
    module = _load_init_module()
    owlbear_dir = _copy_owlbear_seed(tmp_path)
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir, owlbear_dir=owlbear_dir)

    drifted_seed = owlbear_dir / "seed/.owlbear/hooks/deny-writes.py"
    drifted_seed.write_text("# newer seed\n", encoding="utf-8")
    result = module.uninstall(target_dir, owlbear_dir, confirm=False)

    assert result.completed is True
    assert not (target_dir / ".owlbear/hooks/deny-writes.py").exists()


def test_uninstall_removes_receipt_file_when_seed_surface_is_retired(tmp_path: Path) -> None:
    module = _load_init_module()
    owlbear_dir = _copy_owlbear_seed(tmp_path)
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir, owlbear_dir=owlbear_dir)

    retired_seed = owlbear_dir / "seed/.owlbear/hooks/allow-stances-only.py"
    installed_file = target_dir / ".owlbear/hooks/allow-stances-only.py"
    retired_seed.unlink()

    module.uninstall(target_dir, owlbear_dir, confirm=False)

    assert not installed_file.exists()


def test_uninstall_keeps_preexisting_empty_vscode_directory(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    (target_dir / ".vscode").mkdir(parents=True)
    _initialize(module, target_dir)

    module.uninstall(target_dir, _REPO_ROOT, confirm=False)

    assert (target_dir / ".vscode").is_dir()


def test_uninstall_failure_retains_completed_actions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir)
    remove_file = module._remove_manifest_file  # noqa: SLF001
    calls = 0

    def fail_on_second_call(dest: Path, record: dict | None, options: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            failure_message = "simulated uninstall failure"
            raise RuntimeError(failure_message)
        remove_file(dest, record, options)

    monkeypatch.setattr(module, "_remove_manifest_file", fail_on_second_call)

    with pytest.raises(module.UninstallError) as error:
        module.uninstall(target_dir, _REPO_ROOT, confirm=False)

    assert error.value.actions


def test_refresh_configs_are_preserved_on_uninstall_when_preexisting(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    editorconfig = target_dir / ".editorconfig"
    editorconfig.write_text("root = false\n", encoding="utf-8")

    _initialize(module, target_dir, refresh_configs=True)
    module.uninstall(target_dir, _REPO_ROOT, confirm=False)

    assert editorconfig.exists()


def test_cli_rejects_uninstall_only_flags_in_other_modes(tmp_path: Path) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    yes_result = subprocess.run(  # noqa: S603
        [sys.executable, str(_INIT_PATH), "--yes"],
        cwd=target_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    replace_result = subprocess.run(  # noqa: S603
        [sys.executable, str(_INIT_PATH), "--uninstall", "--replace-hooks", "--yes"],
        cwd=target_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert yes_result.returncode != 0
    assert "--yes requires --uninstall" in yes_result.stderr
    assert replace_result.returncode != 0
    assert "--replace-hooks cannot be combined" in replace_result.stderr


def test_uninstall_preserves_non_mergeable_settings_values(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    settings_path = target_dir / ".vscode" / "settings.json"
    settings_path.parent.mkdir()
    seed_settings = json.loads((_REPO_ROOT / "seed/.vscode/settings.json").read_text(encoding="utf-8"))
    existing_settings = {
        "files.watcherExclude": {
            **seed_settings["files.watcherExclude"],
            "consumer-only": True,
        },
        "python.analysis.fixAll": [*seed_settings["python.analysis.fixAll"], "source.consumerOnly"],
    }
    settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

    _initialize(module, target_dir)
    assert module.uninstall(target_dir, _REPO_ROOT, confirm=False).completed is True

    assert json.loads(settings_path.read_text(encoding="utf-8")) == existing_settings


def test_uninstall_preserves_empty_mergeable_settings_values(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir)
    settings_path = target_dir / ".vscode" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["files.exclude"] = {}
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    assert module.uninstall(target_dir, _REPO_ROOT, confirm=False).completed is True

    remaining_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert remaining_settings["files.exclude"] == {}


def test_uninstall_preserves_retired_lines_in_nested_gitignore(tmp_path: Path) -> None:
    module = _load_init_module()
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _initialize(module, target_dir)
    nested_gitignore = target_dir / ".owlbear" / ".gitignore"
    nested_gitignore.write_text(
        nested_gitignore.read_text(encoding="utf-8")
        + "\n# Host-local Delivery worktrees and mutable capacity ledger\n",
        encoding="utf-8",
    )

    assert module.uninstall(target_dir, _REPO_ROOT, confirm=False).completed is True

    assert "# Host-local Delivery worktrees and mutable capacity ledger" in nested_gitignore.read_text(encoding="utf-8")


def test_uninstall_refuses_the_owlbear_checkout() -> None:
    module = _load_init_module()

    with pytest.raises(RuntimeError, match="OwlBear checkout itself"):
        module.uninstall(_REPO_ROOT, _REPO_ROOT, confirm=False)
