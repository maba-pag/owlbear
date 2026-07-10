"""Tests for the Semble CLI launcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from owlbear_tools import semble


def test_uses_current_tool_and_returns_its_exit_code() -> None:
    """Consumer projects resolve Semble lazily through OwlBear's shared command."""
    completed_process = MagicMock(returncode=7)

    with patch.object(semble.subprocess, "run", return_value=completed_process) as run:
        exit_code = semble.main(["search", "task lifecycle", "."])

    assert exit_code == 7
    run.assert_called_once_with(
        ["uv", "tool", "run", "--from", "semble", "semble", "search", "task lifecycle", "."],
        check=False,
    )
