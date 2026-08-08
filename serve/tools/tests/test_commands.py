"""Behavioral tests for the command registry help output."""

from __future__ import annotations

import sys

from owlbear_tools.commands import help_main


def test_help_always_lists_setup_and_maintenance_commands(monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(sys, "argv", ["help"])

    help_main()

    output = capsys.readouterr().out
    assert "Setup:" in output
    assert "uv run setup-project" in output
    assert "uv run integration-target" in output
    assert "Maintenance:" in output
    assert "uv run megalint-clean" in output


def test_help_topic_limits_output_to_selected_group(monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(sys, "argv", ["help", "setup"])

    help_main()

    output = capsys.readouterr().out
    assert "Setup:" in output
    assert "Everyday:" not in output
    assert "Maintenance:" not in output
