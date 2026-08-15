"""Behavioral tests for Delivery target-branch configuration."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.delivery_config import target_branch


def _git_result(command: list[str], *, cwd: Path | None = None) -> int:  # noqa: ARG001
    return 0 if command[:2] == ["git", "check-ref-format"] or "show-ref" in command else 1


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

    with patch("owlbear_tools.delivery_config._run", side_effect=_git_result):
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
    frontier.write_text('{"bindings": []}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.delivery_config._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"


def test_target_branch_accepts_acceptance_completed_delivery_work(
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
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text('{"bindings": [], "change_completion": {"completion_id": "receipt"}}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.delivery_config._run", side_effect=_git_result):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "release"
    assert "dev -> release" in capsys.readouterr().out


def test_target_branch_accepts_abandoned_delivery_work(
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
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text('{"bindings": [], "change_abandonment": {"abandonment_id": "receipt"}}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.delivery_config._run", side_effect=_git_result):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "release"
    assert "dev -> release" in capsys.readouterr().out


def test_target_branch_accepts_legacy_integration_completed_delivery_work(
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
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text(
        json.dumps(
            {
                "bindings": [],
                "integration_result_id": "a" * 64,
                "integration_completion": {"completion_id": "a" * 64},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.delivery_config._run", side_effect=_git_result):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "release"
    assert "dev -> release" in capsys.readouterr().out


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

    with patch("owlbear_tools.delivery_config._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
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

    with patch("owlbear_tools.delivery_config._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
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

    with patch("owlbear_tools.delivery_config._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"
