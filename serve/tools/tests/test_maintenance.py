"""Behavioral tests for dependency and asset maintenance commands."""

from __future__ import annotations

import sys
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.maintenance import deps_status, deps_sync, pds_sync


def test_deps_status_distinguishes_available_updates_from_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    web = tmp_path / "serve/cockpit/web"
    web.mkdir(parents=True)
    (web / "package-lock.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("owlbear_tools.maintenance._require_development", lambda _prog: None)

    with patch("owlbear_tools.maintenance._run", side_effect=[0, 0, 1]), pytest.raises(SystemExit, match="0"):
        deps_status()

    output = capsys.readouterr().out
    assert "Dependency status is informational" in output
    assert "Wanted is the newest version allowed by package.json" in output
    assert "does not update locks or manifest ranges" in output


def test_deps_status_surfaces_uv_tree_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("owlbear_tools.maintenance._require_development", lambda _prog: None)

    with patch("owlbear_tools.maintenance._run", side_effect=[0, 1]), pytest.raises(SystemExit, match="1"):
        deps_status()


def test_deps_status_preserves_missing_tool_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("owlbear_tools.maintenance._require_development", lambda _prog: None)

    with patch("owlbear_tools.maintenance._run", side_effect=[0, 2]), pytest.raises(SystemExit, match="2"):
        deps_status()


def test_deps_sync_explains_that_it_reproduces_existing_locks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    web = tmp_path / "serve/cockpit/web"
    web.mkdir(parents=True)
    (web / "package-lock.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("owlbear_tools.maintenance._require_development", lambda _prog: None)

    with patch("owlbear_tools.maintenance._run", return_value=0), pytest.raises(SystemExit, match="0"):
        deps_sync()

    output = capsys.readouterr().out
    assert "versions and manifest ranges will not be updated" in output
    assert "remaining deps-status entries require a lock or manifest update" in output


def test_pds_sync_replaces_assets_only_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    web = tmp_path / "serve/cockpit/web"
    target = web / "public/porsche-design-system"
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("owlbear_tools.maintenance._require_development", lambda _prog: None)

    def populate(_command: list[str], *, cwd: Path, env: dict[str, str], check: bool) -> object:  # noqa: ARG001
        output = Path(env["PDS_OUTPUT_DIR"])
        (output / "components").mkdir()
        (output / "components/new.js").write_text("new", encoding="utf-8")
        return type("Result", (), {"returncode": 0})()

    with patch("owlbear_tools.maintenance.subprocess.run", side_effect=populate), pytest.raises(SystemExit, match="0"):
        pds_sync()

    assert not (target / "old.txt").exists()
    assert (target / "components/new.js").read_text(encoding="utf-8") == "new"


def test_pds_sync_preserves_assets_when_download_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    web = tmp_path / "serve/cockpit/web"
    target = web / "public/porsche-design-system"
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("owlbear_tools.maintenance._require_development", lambda _prog: None)
    failed = type("Result", (), {"returncode": 1})()

    with patch("owlbear_tools.maintenance.subprocess.run", return_value=failed), pytest.raises(SystemExit, match="1"):
        pds_sync()

    assert (target / "old.txt").read_text(encoding="utf-8") == "old"


def test_pds_sync_creates_missing_public_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    web = tmp_path / "serve/cockpit/web"
    web.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("owlbear_tools.maintenance._require_development", lambda _prog: None)

    def populate(_command: list[str], *, cwd: Path, env: dict[str, str], check: bool) -> object:  # noqa: ARG001
        output = Path(env["PDS_OUTPUT_DIR"])
        (output / "components").mkdir()
        (output / "components/new.js").write_text("new", encoding="utf-8")
        return type("Result", (), {"returncode": 0})()

    with patch("owlbear_tools.maintenance.subprocess.run", side_effect=populate), pytest.raises(SystemExit, match="0"):
        pds_sync()

    assert (web / "public/porsche-design-system/components/new.js").read_text(encoding="utf-8") == "new"
    assert stat.S_IMODE((web / "public/porsche-design-system").stat().st_mode) == 0o755


def test_deps_status_help_is_available_outside_development_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["deps-status", "--help"])

    with pytest.raises(SystemExit, match="0"):
        deps_status()


def test_pds_sync_reports_missing_npm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    web = tmp_path / "serve/cockpit/web"
    web.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("owlbear_tools.maintenance._require_development", lambda _prog: None)

    with (
        patch("owlbear_tools.maintenance.subprocess.run", side_effect=FileNotFoundError("npm")),
        pytest.raises(SystemExit, match="2"),
    ):
        pds_sync()

    assert "Error: unable to run npm" in capsys.readouterr().err
