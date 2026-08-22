"""Unit tests for memory Git failure formatting."""

from __future__ import annotations

import subprocess

from owlbear_memory_mcp.git import format_git_failure


def test_format_git_failure_prefers_stderr_and_includes_command_status() -> None:
    error = subprocess.CalledProcessError(
        17,
        ["git", "commit", "-m", "memory batch"],
        output="stdout detail",
        stderr="stderr detail",
    )

    detail = format_git_failure(error)

    assert "git commit -m 'memory batch' exited with status 17" in detail
    assert "stderr detail" in detail
    assert "stdout detail" not in detail


def test_format_git_failure_falls_back_to_stdout() -> None:
    error = subprocess.CalledProcessError(
        1,
        ["git", "commit"],
        output="stdout detail",
        stderr="",
    )

    detail = format_git_failure(error)

    assert "stdout detail" in detail


def test_format_git_failure_tail_is_bounded_and_marked() -> None:
    output = "header\n" + ("x" * 5_000) + "\nfinal failure detail"
    error = subprocess.CalledProcessError(1, ["git", "commit"], stderr=output)

    detail = format_git_failure(error)
    captured = detail.split("<<<\n", maxsplit=1)[1].removesuffix("\n>>>")

    assert len(captured) <= 4_096
    assert "[truncated; showing final command output]" in captured
    assert captured.endswith("final failure detail")


def test_format_git_failure_reports_command_without_output() -> None:
    error = subprocess.CalledProcessError(128, ["git", "rev-parse", "--show-toplevel"])

    assert format_git_failure(error) == "git rev-parse --show-toplevel exited with status 128"
