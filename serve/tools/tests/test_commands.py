"""Behavioral tests for the command registry help output."""

from __future__ import annotations

import io
import sys

import pytest

from owlbear_tools.commands import command_footer, help_main


class _TerminalBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


_QUALITY_TREE = (
    "  quality-full",
    "    format-full",
    "      format-python",
    "      format-whitespace",
    "      format-eof",
    "    lint-full",
    "      lint",
    "        lint-python",
    "        lint-markdown",
    "        lint-yaml",
    "        lint-shell",
    "        lint-actions",
    "        lint-editorconfig",
    "        lint-cockpit",
    "          lint-cockpit-code",
    "          lint-cockpit-style",
    "          lint-cockpit-html",
    "      megalint",
    "    typecheck-cockpit",
    "    todo",
)


def _assert_rows_in_order(output: str, rows: tuple[str, ...]) -> None:
    lines = output.splitlines()
    positions = [next(index for index, line in enumerate(lines) if line.startswith(row)) for row in rows]
    assert positions == sorted(positions)


def test_default_help_renders_the_quality_tree(monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(sys, "argv", ["help"])

    help_main()

    output = capsys.readouterr().out
    assert "Workspace:" in output
    assert "Quality:" in output
    assert "Tests:" in output
    _assert_rows_in_order(output, _QUALITY_TREE)
    assert "Setup:" not in output
    assert "Maintenance:" not in output
    assert "Internal:" not in output


def test_quality_help_renders_the_command_tree(monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(sys, "argv", ["help", "quality"])

    help_main()

    output = capsys.readouterr().out
    assert "Quality:" in output
    assert "Includes:" not in output
    _assert_rows_in_order(output, _QUALITY_TREE)
    assert "  Available options:" in output
    assert "ˢ staged files only (-s)" in output
    assert "✚ disable safe fixes (-n)" in output
    assert "⚠ unsafe fixes (-u)" in output


def test_internal_help_renders_indexes_aggregate(monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(sys, "argv", ["help", "internal"])

    help_main()

    output = capsys.readouterr().out
    assert "indexes" in output
    assert "Includes:" not in output
    assert "  indexes [PATH]" in output
    assert "    doc-index [PATH]" in output
    assert "    py-index [PATH]" in output
    assert "    ts-index [PATH]" in output


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
    assert "  lint [OPTIONS]" not in output
    assert any(line.startswith("  lint ") for line in output.splitlines())
    assert "lint-full" not in output
    assert "quality-full" not in output
    assert "megalint" not in output
    assert "Tests:" not in output
    assert "Topics: s." in output
    assert "maintenance (m)" not in output
    assert "internal (i)" not in output


def test_help_styles_semantic_anchors_and_capability_symbols(monkeypatch: object) -> None:
    output = _TerminalBuffer()
    monkeypatch.setattr(sys, "argv", ["help", "quality"])
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    help_main()

    rendered = output.getvalue()
    assert "\033[1m\033[35m\N{INFORMATION SOURCE} OwlBear commands\033[0m" in rendered
    assert "\033[1m\033[32mQuality:\033[0m" in rendered
    assert "\033[32mlint" in rendered
    assert "\033[32mˢ\033[0m" in rendered
    assert "\033[31m✚\033[0m" in rendered
    assert "\033[33m⚠\033[0m" in rendered


def test_help_aligns_capabilities_without_iconless_rows(monkeypatch: object, capsys: object) -> None:
    terminal_size = type("TerminalSize", (), {"columns": 80})()
    monkeypatch.setattr(sys, "argv", ["help", "quality"])
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr("owlbear_tools.commands.shutil.get_terminal_size", lambda **_kwargs: terminal_size)

    help_main()

    lines = capsys.readouterr().out.splitlines()
    options_index = next(index for index, line in enumerate(lines) if line.startswith("  Available options:"))
    tree_lines = lines[:options_index]
    capability_lines = [line for line in tree_lines if any(symbol in line for symbol in ("ˢ", "✚", "⚠"))]
    assert {line.find("ˢ") for line in capability_lines if "ˢ" in line} == {60}
    assert {line.find("✚") for line in capability_lines if "✚" in line} == {62}
    assert {line.find("⚠") for line in capability_lines if "⚠" in line} == {64}
    assert len(next(line for line in lines if line.startswith("    todo"))) > 60
    assert lines[options_index : options_index + 4] == [
        "  Available options:",
        "    ˢ staged files only (-s)",
        "    ✚ disable safe fixes (-n)",
        "    ⚠ unsafe fixes (-u)",
    ]
    assert all(len(line) <= 80 for line in lines)


def test_help_keeps_options_legend_on_one_line_when_it_fits(monkeypatch: object, capsys: object) -> None:
    terminal_size = type("TerminalSize", (), {"columns": 120})()
    monkeypatch.setattr(sys, "argv", ["help", "quality"])
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr("owlbear_tools.commands.shutil.get_terminal_size", lambda **_kwargs: terminal_size)

    help_main()

    lines = capsys.readouterr().out.splitlines()
    assert "  Available options:  ˢ staged files only (-s)  ✚ disable safe fixes (-n)  ⚠ unsafe fixes (-u)" in lines
    assert all(len(line) <= 120 for line in lines)


def test_help_and_footer_stay_plain_when_color_is_disabled(monkeypatch: object) -> None:
    output = _TerminalBuffer()
    monkeypatch.setattr(sys, "argv", ["help", "quality"])
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setenv("NO_COLOR", "1")

    help_main()

    assert "\033[" not in output.getvalue()
    assert "ˢ" in output.getvalue()
    assert command_footer(output) == "\N{INFORMATION SOURCE} More commands and options: uv run help"


def test_help_preserves_tree_on_narrow_terminals(monkeypatch: object) -> None:
    output = _TerminalBuffer()
    terminal_size = type("TerminalSize", (), {"columns": 80})()

    def get_terminal_size(fallback: tuple[int, int] = (80, 24)) -> object:
        assert fallback in {(80, 24), (120, 24)}
        return terminal_size

    monkeypatch.setattr(sys, "argv", ["help", "quality"])
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr("owlbear_tools.commands.shutil.get_terminal_size", get_terminal_size)

    help_main()

    assert "        lint" in output.getvalue()
    assert "    lint-full" in output.getvalue()
    assert "      lint" in output.getvalue()
    assert "        lint-python" in output.getvalue()
