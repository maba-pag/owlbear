"""Behavioral tests for project utility commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.megalinter import MegaLinterImage, load_megalinter_image
from owlbear_tools.project import deps_status, deps_sync, doctor, megalint_clean, target_branch


def _git_result(command: list[str], *, cwd: Path | None = None) -> int:  # noqa: ARG001
    return 0 if command[:2] == ["git", "check-ref-format"] or "show-ref" in command else 1


def test_megalinter_image_loads_from_workspace_config(tmp_path: Path) -> None:
    config = tmp_path / ".mega-linter.yml"
    config.write_text(
        "OWLBEAR_MEGALINTER_IMAGE: registry.example/main:v-current\n",
        encoding="utf-8",
    )

    image = load_megalinter_image(config)

    assert image.repository == "registry.example/main"
    assert image.tag == "v-current"


def test_target_branch_prints_current_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch"])

    target_branch()

    assert capsys.readouterr().out == "dev\n"


def test_target_branch_atomically_changes_idle_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "release"
    assert "dev -> release" in capsys.readouterr().out


def test_target_branch_rejects_unfinished_delivery_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text('{"bindings": [], "integration_completion": null}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"


def test_target_branch_rejects_idle_change_coordination_without_frontier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    coordination = tmp_path / ".owlbear/delivery/runtime/claims/changes/example.json"
    coordination.parent.mkdir(parents=True)
    coordination.write_text('{"writer": null}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"


@pytest.mark.parametrize(
    "unfinished_path",
    [
        ".owlbear/delivery/runtime/changes/example/contract.json",
        ".owlbear/delivery/packages/example/manifest.json",
    ],
)
def test_target_branch_rejects_partial_change_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unfinished_path: str,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    authority = tmp_path / unfinished_path
    authority.parent.mkdir(parents=True)
    authority.write_text("{}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"


@pytest.mark.parametrize("legacy_root", [".owlbear/target", ".owlbear/worktrees"])
def test_target_branch_rejects_unmigrated_delivery_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    legacy_root: str,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    state = tmp_path / legacy_root / "state"
    state.parent.mkdir(parents=True)
    state.write_text("unmigrated\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"


def test_doctor_accepts_canonical_workspace_without_cutover_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    mcp = tmp_path / ".vscode/mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["doctor", str(tmp_path)])

    with (
        patch("owlbear_tools.project.shutil.which", return_value="/usr/bin/tool"),
        patch("owlbear_tools.project._remote_target_exists", return_value=True),
        patch("owlbear_tools.project._remote_github_repository", return_value="example/project"),
        pytest.raises(SystemExit, match="0"),
    ):
        doctor()

    output = capsys.readouterr().out
    assert "target-cutover" not in output


def test_doctor_reports_only_unsupported_config_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"schema_version":1,"integration_target":"dev"}\n', encoding="utf-8")
    mcp = tmp_path / ".vscode/mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["doctor", str(tmp_path)])

    with (
        patch("owlbear_tools.project.shutil.which", return_value="/usr/bin/tool"),
        pytest.raises(SystemExit, match="1"),
    ):
        doctor()

    output = capsys.readouterr().out
    assert "FAIL  unsupported Delivery config schema: 1" in output
    assert "None/None" not in output


def test_doctor_rejects_unmigrated_delivery_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    legacy = tmp_path / ".owlbear/target/runtime.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("{}\n", encoding="utf-8")
    mcp = tmp_path / ".vscode/mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["doctor", str(tmp_path)])

    with (
        patch("owlbear_tools.project.shutil.which", return_value="/usr/bin/tool"),
        patch("owlbear_tools.project._remote_target_exists", return_value=True),
        patch("owlbear_tools.project._remote_github_repository", return_value="example/project"),
        pytest.raises(SystemExit, match="1"),
    ):
        doctor()

    assert "FAIL  unmigrated Delivery state: .owlbear/target" in capsys.readouterr().out


def test_deps_status_distinguishes_available_updates_from_sync(tmp_path, monkeypatch, capsys) -> None:
    web = tmp_path / "serve/cockpit/web"
    web.mkdir(parents=True)
    (web / "package-lock.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with patch("owlbear_tools.project._run", side_effect=[0, 1, 1]), pytest.raises(SystemExit, match="0"):
        deps_status()

    output = capsys.readouterr().out
    assert "Dependency status is informational" in output
    assert "Wanted is the newest version allowed by package.json" in output
    assert "does not update locks or manifest ranges" in output


def test_deps_sync_explains_that_it_reproduces_existing_locks(tmp_path, monkeypatch, capsys) -> None:
    web = tmp_path / "serve/cockpit/web"
    web.mkdir(parents=True)
    (web / "package-lock.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with patch("owlbear_tools.project._run", return_value=0), pytest.raises(SystemExit, match="0"):
        deps_sync()

    output = capsys.readouterr().out
    assert "versions and manifest ranges will not be updated" in output
    assert "remaining deps-status entries require a lock or manifest update" in output


def test_megalint_clean_preserves_current_and_removes_only_obsolete_images(
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    image = MegaLinterImage(reference="registry.example/megalinter-main:v-current")
    listing = f"{image.repository}\t{image.tag}\tcurrent\t1GB\n{image.repository}\tv-old\tobsolete\t900MB\n"
    monkeypatch.setattr(sys, "argv", ["megalint-clean", "--yes"])
    completed = type("Result", (), {"returncode": 0, "stdout": listing, "stderr": ""})()

    with (
        patch("owlbear_tools.project.load_megalinter_image", return_value=image),
        patch("owlbear_tools.project.subprocess.run", return_value=completed),
        patch("owlbear_tools.project._run", return_value=0) as remove,
        pytest.raises(SystemExit, match="0"),
    ):
        megalint_clean()

    remove.assert_called_once_with(["docker", "image", "rm", "obsolete"])
    assert "v-old" in capsys.readouterr().out


def test_pds_sync_replaces_assets_only_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from owlbear_tools.project import pds_sync

    web = tmp_path / "serve/cockpit/web"
    target = web / "public/porsche-design-system"
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def populate(_command: list[str], *, cwd: Path, env: dict[str, str], check: bool) -> object:  # noqa: ARG001
        output = Path(env["PDS_OUTPUT_DIR"])
        (output / "components").mkdir()
        (output / "components/new.js").write_text("new", encoding="utf-8")
        return type("Result", (), {"returncode": 0})()

    with patch("owlbear_tools.project.subprocess.run", side_effect=populate), pytest.raises(SystemExit, match="0"):
        pds_sync()

    assert not (target / "old.txt").exists()
    assert (target / "components/new.js").read_text(encoding="utf-8") == "new"


def test_pds_sync_preserves_assets_when_download_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from owlbear_tools.project import pds_sync

    web = tmp_path / "serve/cockpit/web"
    target = web / "public/porsche-design-system"
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    failed = type("Result", (), {"returncode": 1})()

    with patch("owlbear_tools.project.subprocess.run", return_value=failed), pytest.raises(SystemExit, match="1"):
        pds_sync()

    assert (target / "old.txt").read_text(encoding="utf-8") == "old"
