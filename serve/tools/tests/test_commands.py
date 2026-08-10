"""Behavioral tests for the command registry help output."""

from __future__ import annotations

import io
import sys

import pytest

from owlbear_tools.commands import command_footer, help_main


class _TerminalBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_default_help_focuses_on_workspace_quality_and_tests(monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(sys, "argv", ["help"])

    help_main()

    output = capsys.readouterr().out
    assert "Workspace:" in output
    assert "Quality:" in output
    assert "Tests:" in output
    assert "Setup:" not in output
    assert "Maintenance:" not in output
    assert "Internal:" not in output
    assert "uv run help setup" in output
    assert "uv run help maintenance" in output
    assert "uv run help internal" in output


def test_help_topic_limits_output_to_selected_group(monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(sys, "argv", ["help", "setup"])

    help_main()

    output = capsys.readouterr().out
    assert "Setup:" in output
    assert "Workspace:" not in output
    assert "Quality:" not in output
    assert "Maintenance:" not in output


@pytest.mark.parametrize(("topic", "heading"), [("s", "Setup:"), ("m", "Maintenance:"), ("i", "Internal:")])
def test_help_accepts_topic_shorthands(topic: str, heading: str, monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(sys, "argv", ["help", topic])

    help_main()

    assert heading in capsys.readouterr().out


def test_consumer_help_hides_development_commands(tmp_path: object, monkeypatch: object, capsys: object) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["help"])

    help_main()

    output = capsys.readouterr().out
    assert "uv run lint [" in output
    assert "uv run lint-full" not in output
    assert "Tests:" not in output
    assert "uv run megalint" not in output
    assert "uv run deps-sync" not in output
    assert "uv run help setup" in output
    assert "uv run help maintenance" not in output


def test_help_styles_semantic_anchors_for_terminal_output(monkeypatch: object) -> None:
    output = _TerminalBuffer()
    monkeypatch.setattr(sys, "argv", ["help"])
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    help_main()

    rendered = output.getvalue()
    assert "\033[1m\033[35m\N{INFORMATION SOURCE} OwlBear commands\033[0m" in rendered
    assert "\033[1m\033[36mWorkspace:\033[0m" in rendered
    assert "\033[1m\033[32mQuality:\033[0m" in rendered
    assert "\033[1m\033[35mTests:\033[0m" in rendered
    assert "\033[32muv run lint" in rendered
    assert "lint --all plus frontend and MegaLinter checks" in rendered
    footer = command_footer(output)
    assert "\033[1m\033[35m\N{INFORMATION SOURCE}\033[0m" in footer
    assert "\033[1m\033[32muv run help\033[0m" in footer


def test_help_and_footer_stay_plain_when_color_is_disabled(monkeypatch: object) -> None:
    output = _TerminalBuffer()
    monkeypatch.setattr(sys, "argv", ["help"])
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setenv("NO_COLOR", "1")

    help_main()

    assert "\033[" not in output.getvalue()
    assert command_footer(output) == "\N{INFORMATION SOURCE} More commands and options: uv run help"


def test_help_stacks_descriptions_on_narrow_terminals(monkeypatch: object) -> None:
    output = _TerminalBuffer()
    terminal_size = type("TerminalSize", (), {"columns": 80})()

    def get_terminal_size(fallback: tuple[int, int] = (80, 24)) -> object:
        assert fallback in {(80, 24), (120, 24)}
        return terminal_size

    monkeypatch.setattr(sys, "argv", ["help", "lint"])
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setattr("owlbear_tools.commands.shutil.get_terminal_size", get_terminal_size)

    help_main()

    assert "uv run lint [OPTIONS] [FILE ...]\033[0m\n      Staged or explicit files" in output.getvalue()
