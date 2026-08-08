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


def test_consumer_help_hides_development_commands(tmp_path: object, monkeypatch: object, capsys: object) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["help"])

    help_main()

    output = capsys.readouterr().out
    assert "uv run lint [" in output
    assert "uv run lint-full" not in output
    assert "uv run megalint" not in output
    assert "uv run deps-sync" not in output
