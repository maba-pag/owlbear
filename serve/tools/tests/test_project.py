"""Behavioral tests for project setup and diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.project import doctor


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
        patch("owlbear_tools.delivery_config._remote_target_exists", return_value=True),
        patch("owlbear_tools.delivery_config._remote_github_repository", return_value="example/project"),
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
