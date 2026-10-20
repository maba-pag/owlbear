"""Behavioral tests for project setup and diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.project import doctor


def test_doctor_accepts_workspace_with_mcp_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    mcp = tmp_path / ".vscode/mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["doctor", str(tmp_path)])

    with (
        patch("owlbear_tools.project.shutil.which", return_value="/usr/bin/tool"),
        pytest.raises(SystemExit, match="0"),
    ):
        doctor()

    output = capsys.readouterr().out
    assert "PASS  .vscode/mcp.json" in output
    assert "FAIL" not in output


def test_doctor_reports_missing_mcp_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    monkeypatch.setattr(sys, "argv", ["doctor", str(tmp_path)])

    with (
        patch("owlbear_tools.project.shutil.which", return_value="/usr/bin/tool"),
        pytest.raises(SystemExit, match="1"),
    ):
        doctor()

    output = capsys.readouterr().out
    assert "FAIL  missing .vscode/mcp.json" in output
