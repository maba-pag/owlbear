"""Behavioral tests for lint command wrappers."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from owlbear_tools.lint import lint


def test_lint_uses_staged_files_when_no_paths_are_given() -> None:
    with (
        patch.object(sys, "argv", ["lint"]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    call.assert_called_once_with(["pre-commit", "run"])


def test_lint_passes_explicit_paths_to_pre_commit() -> None:
    paths = ["share/skills/h-mcp-memory/SKILL.md", "share/instructions/pipeline-agents.instructions.md"]
    with (
        patch.object(sys, "argv", ["lint", *paths]),
        patch("owlbear_tools.lint.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        lint()

    call.assert_called_once_with(["pre-commit", "run", "--files", *paths])
