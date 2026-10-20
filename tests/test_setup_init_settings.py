"""Integration tests for seeded VS Code settings written by setup/init.py."""

# ruff: noqa: SLF001

from __future__ import annotations

import importlib.util
import json
import os
import runpy
import subprocess
import sys
import types
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_INIT_PATH = _REPO_ROOT / "setup" / "init.py"


def test_init_refuses_windows_before_changing_the_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    with (
        patch.object(sys, "platform", "win32"),
        patch.object(sys, "argv", [str(_INIT_PATH)]),
        pytest.raises(SystemExit) as exit_info,
    ):
        runpy.run_path(str(_INIT_PATH), run_name="__main__")

    assert exit_info.value.code == 1
    assert "Windows is unsupported" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


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


def test_init_writes_paths_through_the_runtime_alias(tmp_path: Path, init_module: types.ModuleType) -> None:
    version = tmp_path / ".owlbear/versions/v1.0"
    version.mkdir(parents=True)
    alias = tmp_path / ".owlbear/runtime"
    alias.symlink_to(version, target_is_directory=True)
    target_dir = tmp_path / "Projects/app"
    target_dir.mkdir(parents=True)

    paths = init_module._build_replacements(alias, target_dir)

    assert (paths["owlbear_rel_path"], paths["owlbear_abs_path"]) == ("../../.owlbear/runtime", str(alias))


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
    assert "owlbear-memory" in mcp["servers"]


def test_init_creates_project_surfaces_without_runtime_selection_artifacts(
    tmp_path: Path,
    init_module: types.ModuleType,
    run_init_without_test_surface: Callable[..., None],
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with patch("subprocess.run") as package_install:
        run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)

    for retired_path in (
        ".owlbear/target",
        ".owlbear/worktrees",
        ".owlbear/adapters",
        ".owlbear/target-cutover-request.json",
        ".owlbear/target-cutover.json",
        ".owlbear/delivery",
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
        "owlbear-knowledge",
        "owlbear-memory",
        "owlbear-browser",
        "markitdown",
    }
    browser_env = mcp["servers"]["owlbear-browser"]["env"]
    assert browser_env["BROWSER_ALLOWED_DOMAINS"] == "*"
    assert "BROWSER_MODE" not in browser_env
    assert "PLAYWRIGHT_USER_DATA_DIR" not in browser_env
    for server_name in (
        "owlbear-knowledge",
        "owlbear-memory",
        "owlbear-browser",
    ):
        server = mcp["servers"][server_name]
        assert server["command"] == "uv"
        assert server["args"][:2] == ["--project", owlbear_rel_path]
    assert not (target_dir / ".gitignore").exists()
    assert not (target_dir / ".owlbear/.gitignore").exists()
    installed_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in target_dir.rglob("*")
        if path.is_file() and path.suffix in {"", ".json", ".jsonc", ".md", ".yml", ".yaml"}
    )
    assert "openspec" not in installed_text.lower()
    assert ".owlbear/kanban/tasks" not in installed_text
    assert ".owlbear/kanban/decisions" not in installed_text
    assert all(call.args[0][0] == "git" for call in package_install.call_args_list)


def test_init_rerun_preserves_user_settings(
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

    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)
    first_rerun = {path.relative_to(target_dir): path.read_bytes() for path in target_dir.rglob("*") if path.is_file()}
    run_init_without_test_surface(init_module.init, target_dir, _REPO_ROOT, interactive=False)
    second_rerun = {path.relative_to(target_dir): path.read_bytes() for path in target_dir.rglob("*") if path.is_file()}

    merged_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert merged_settings["example.userSetting"] == "preserved"
    assert merged_settings["chat.tools.terminal.autoApprove"]["example-command"] is False
    assert second_rerun == first_rerun


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", *arguments],  # noqa: S607
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _git_project(tmp_path: Path) -> Path:
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    _git(target_dir, "init", "-q")
    return target_dir


def test_cli_setup_without_consent_writes_nothing(tmp_path: Path) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    refused = subprocess.run(  # noqa: S603
        [sys.executable, str(_INIT_PATH)], cwd=target_dir, capture_output=True, text=True, check=False
    )
    dry_run = subprocess.run(  # noqa: S603
        [sys.executable, str(_INIT_PATH), "--dry-run"], cwd=target_dir, capture_output=True, text=True, check=False
    )

    assert refused.returncode == 1
    assert "--yes" in refused.stderr
    assert dry_run.returncode == 0, dry_run.stderr
    assert "create: .vscode/settings.json" in dry_run.stdout
    assert list(target_dir.iterdir()) == []


def test_interactive_decline_writes_nothing(
    tmp_path: Path,
    init_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = _git_project(tmp_path)
    exclude = target_dir / ".git/info/exclude"
    exclude_before = exclude.read_bytes()
    prompts: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "n")

    assert init_module.init(target_dir, _REPO_ROOT, interactive=True) is False

    assert prompts == [f"Write the OwlBear agent workspace into {target_dir.resolve()}? [y/N] "]
    assert [path.name for path in target_dir.iterdir()] == [".git"]
    assert exclude.read_bytes() == exclude_before


def test_install_in_git_repository_shows_nothing_new_and_keeps_gitignore(
    tmp_path: Path,
    init_module: types.ModuleType,
) -> None:
    target_dir = _git_project(tmp_path)
    gitignore = target_dir / ".gitignore"
    gitignore.write_text("consumer-rule/\n", encoding="utf-8")
    _git(target_dir, "add", ".gitignore")
    _git(target_dir, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "base", "--no-gpg-sign")

    assert init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True) is True
    for runtime_file in (".owlbear/scratch/note.txt", ".owlbear/knowledge/kb.db"):
        (target_dir / runtime_file).parent.mkdir(parents=True, exist_ok=True)
        (target_dir / runtime_file).write_text("x\n", encoding="utf-8")

    assert _git(target_dir, "status", "--porcelain", "--untracked-files=all") == ""
    assert gitignore.read_text(encoding="utf-8") == "consumer-rule/\n"
    assert (target_dir / ".vscode/mcp.json").is_file()


def test_tracked_settings_are_listed_as_tracked(
    tmp_path: Path,
    init_module: types.ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target_dir = _git_project(tmp_path)
    settings_path = target_dir / ".vscode/settings.json"
    settings_path.parent.mkdir()
    settings_path.write_text('{"user.setting": true}\n', encoding="utf-8")
    _git(target_dir, "add", ".vscode/settings.json")

    init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True)

    output = capsys.readouterr().out.splitlines()
    assert "  merge into existing: .vscode/settings.json (tracked: your change will show as modified)" in output
    assert "  create: .vscode/mcp.json" in output
    changed = {line[3:] for line in _git(target_dir, "status", "--porcelain", "--untracked-files=all").splitlines()}
    assert changed == {".vscode/settings.json"}


def test_rerun_keeps_one_exclude_block(tmp_path: Path, init_module: types.ModuleType) -> None:
    target_dir = _git_project(tmp_path)
    exclude = target_dir / ".git/info/exclude"

    init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True)
    first = exclude.read_text(encoding="utf-8")
    init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True)
    second = exclude.read_text(encoding="utf-8")

    manifest = json.loads((target_dir / ".owlbear/install-manifest.json").read_text(encoding="utf-8"))
    begin, end = init_module._workspace_git.markers("")
    block = second.split(f"{begin}\n")[1].split(f"{end}\n")[0]
    assert second == first
    assert second.count(begin) == 1
    assert block.splitlines() == manifest["git_exclude"]
    assert "/.owlbear/" in manifest["git_exclude"]


def test_a_later_user_file_beside_the_workspace_files_stays_visible(
    tmp_path: Path, init_module: types.ModuleType
) -> None:
    target_dir = _git_project(tmp_path)
    init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True)
    (target_dir / ".vscode/extensions.json").write_text("{}\n", encoding="utf-8")

    assert _git(target_dir, "status", "--porcelain", "--untracked-files=all") == "?? .vscode/extensions.json\n"


def test_two_installs_in_one_repository_keep_their_own_blocks_and_literal_paths(
    tmp_path: Path, init_module: types.ModuleType
) -> None:
    repository = _git_project(tmp_path)
    for name in ("a", "[demo]"):
        (repository / "apps" / name).mkdir(parents=True)
        init_module.init(repository / "apps" / name, _REPO_ROOT, interactive=False, yes=True)

    exclude = (repository / ".git/info/exclude").read_text(encoding="utf-8")
    assert _git(repository, "status", "--porcelain", "--untracked-files=all") == ""
    assert exclude.count(" — begin") == 2
    assert "/apps/\\[demo\\]/.owlbear/" in exclude


def test_a_rerun_keeps_lines_the_owner_added_to_the_block(tmp_path: Path, init_module: types.ModuleType) -> None:
    target_dir = _git_project(tmp_path)
    exclude = target_dir / ".git/info/exclude"
    init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True)
    end = init_module._workspace_git.markers("")[1]
    exclude.write_text(exclude.read_text(encoding="utf-8").replace(end, f"/private-notes/\n{end}"), encoding="utf-8")

    init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True)

    assert "/private-notes/\n" in exclude.read_text(encoding="utf-8")


def test_install_outside_git_says_nothing_is_hidden(
    tmp_path: Path,
    init_module: types.ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True)

    assert "Not a Git repository" in capsys.readouterr().out
    manifest = json.loads((target_dir / ".owlbear/install-manifest.json").read_text(encoding="utf-8"))
    assert "git_exclude" not in manifest


def test_init_does_not_scaffold_retired_verification_profile(
    tmp_path: Path,
    init_module: types.ModuleType,
) -> None:
    target_dir = tmp_path / "project"
    (target_dir / "tests").mkdir(parents=True)
    (target_dir / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
    (target_dir / "package.json").write_text('{"scripts":{"test":"vitest run"}}\n', encoding="utf-8")
    (target_dir / "package-lock.json").write_text("{}\n", encoding="utf-8")

    init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True)

    profile_path = target_dir / ".owlbear/delivery/verification.json"
    assert not profile_path.exists()

    init_module.init(target_dir, _REPO_ROOT, interactive=False, yes=True)

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
        "gpt-6-luna": "max",
        "gpt-6-sol": "high",
        "claude-opus-5.5": "medium",
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
                "gpt-6-luna": {"custom": "preserve"},
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
    assert profile_data[1]["settings"]["gpt-6-luna"] == {
        "custom": "preserve",
        "reasoningEffort": "max",
    }
    assert profile_data[1]["settings"]["gpt-6-sol"] == {"reasoningEffort": "high"}
    assert profile_data[1]["settings"]["claude-opus-5.5"] == {"reasoningEffort": "medium"}


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
