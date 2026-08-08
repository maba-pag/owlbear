"""Behavioral tests for project utility commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.megalinter import MegaLinterImage, load_megalinter_image
from owlbear_tools.project import integration_target, megalint_clean


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


def test_integration_target_prints_current_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"schema_version": 1, "integration_target": "dev"}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["integration-target"])

    integration_target()

    assert capsys.readouterr().out == "dev\n"


def test_integration_target_atomically_changes_idle_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"schema_version": 1, "integration_target": "dev"}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["integration-target", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result):
        integration_target()

    assert json.loads(config.read_text(encoding="utf-8"))["integration_target"] == "release"
    assert "dev -> release" in capsys.readouterr().out


def test_integration_target_rejects_unfinished_delivery_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"schema_version": 1, "integration_target": "dev"}\n', encoding="utf-8")
    frontier = tmp_path / ".owlbear/target/delivery/changes/example/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text('{"bindings": [], "integration_completion": null}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["integration-target", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        integration_target()

    assert json.loads(config.read_text(encoding="utf-8"))["integration_target"] == "dev"


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
