"""RED-phase tests for owlbear_orchestrator.analysis._cli (task #466, RED for #180).

Tests main(argv=None) -> int and indirectly __main__.py.
Approach: mock analyze() and formatters; call main(argv) directly. No subprocess.

All tests fail on current HEAD: _cli.py does not exist yet.
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from owlbear_orchestrator.analysis._cli import main  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Patch namespace — resolved once _cli.py is built
# ---------------------------------------------------------------------------

_CLI = "owlbear_orchestrator.analysis._cli"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_proposal() -> MagicMock:
    """Create a minimal mock AnalysisProposal for format-selection tests."""
    p = MagicMock()
    p.model_dump.return_value = {
        "target_agent": "builder",
        "category": "performance",
        "pattern": "slow_agent",
        "rationale": "p50=120s",
        "evidence": {},
        "suggested_action": "reduce context size",
    }
    return p


def _call_arg(mock_obj: MagicMock, name: str, pos: int) -> Any:
    """Return a call argument by keyword name or positional index (whichever was used)."""
    c = mock_obj.call_args
    if name in c.kwargs:
        return c.kwargs[name]
    return c.args[pos] if len(c.args) > pos else None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_AnalysisCLI:
    """Tests derived from task #466 AC — RED phase for task #180."""

    # AC: test_main_returns_int
    def test_main_returns_int(self) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]):
            result = main([])
        assert isinstance(result, int)

    # AC: test_exit_code_0_success
    def test_exit_code_0_success(self) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]):
            code = main([])
        assert code == 0

    # AC: test_default_format_json — no --format flag → JSON on stdout
    def test_default_format_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]):
            main([])
        out = capsys.readouterr().out.strip()
        parsed = json.loads(out)  # must be valid JSON
        assert isinstance(parsed, list)

    # AC: test_format_json_flag — explicit --format json calls format_json
    def test_format_json_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]), patch(f"{_CLI}.format_json", return_value="[]") as mock_fmt:
            main(["--format", "json"])
        mock_fmt.assert_called_once()
        assert "[]" in capsys.readouterr().out

    # AC: test_format_markdown_flag — --format markdown calls format_markdown
    def test_format_markdown_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]), patch(f"{_CLI}.format_markdown", return_value="No analysis proposals.") as mock_fmt:
            main(["--format", "markdown"])
        mock_fmt.assert_called_once()
        assert "No analysis proposals." in capsys.readouterr().out

    # AC: test_window_hours — --window 24 passes timedelta(hours=24) to analyze()
    def test_window_hours(self) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]) as mock_analyze:
            main(["--window", "24"])
        window = _call_arg(mock_analyze, "window", 1)
        assert window == timedelta(hours=24)

    # AC: test_window_default_all — no --window passes timedelta(days=36500) to analyze()
    def test_window_default_all(self) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]) as mock_analyze:
            main([])
        window = _call_arg(mock_analyze, "window", 1)
        assert window is not None
        assert window == timedelta(days=36500)

    # AC: test_audit_dir_flag — --audit-dir custom/ passes Path("custom/") to analyze()
    def test_audit_dir_flag(self) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]) as mock_analyze:
            main(["--audit-dir", "custom/"])
        audit_dir = _call_arg(mock_analyze, "audit_dir", 0)
        assert audit_dir == Path("custom/")

    # AC: test_audit_dir_default — no --audit-dir passes Path("data/audit/") to analyze()
    def test_audit_dir_default(self) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]) as mock_analyze:
            main([])
        audit_dir = _call_arg(mock_analyze, "audit_dir", 0)
        assert audit_dir == Path("store/audit/")

    # AC: test_exit_code_1_on_error — analyze() raises → main() returns 1
    def test_exit_code_1_on_error(self) -> None:
        with patch(f"{_CLI}.analyze", side_effect=RuntimeError("boom")):
            code = main([])
        assert code == 1

    # AC: test_error_message_stderr — error written to stderr, not stdout
    def test_error_message_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(f"{_CLI}.analyze", side_effect=RuntimeError("something broke")):
            main([])
        captured = capsys.readouterr()
        assert len(captured.err) > 0, "error output expected on stderr"
        assert "something broke" not in captured.out, "error must NOT appear on stdout"

    # AC: test_no_proposals_json — empty list → JSON output is "[]"
    def test_no_proposals_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]):
            main([])
        out = capsys.readouterr().out.strip()
        assert out == "[]"

    # AC: test_no_proposals_markdown — empty list → markdown output is "No analysis proposals."
    def test_no_proposals_markdown(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(f"{_CLI}.analyze", return_value=[]):
            main(["--format", "markdown"])
        out = capsys.readouterr().out.strip()
        assert out == "No analysis proposals."

    # AC: test_main_argv_injection — main(argv) uses argv, not sys.argv
    def test_main_argv_injection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Poisoning sys.argv with --format markdown must not affect main([]) output."""
        monkeypatch.setattr(sys, "argv", ["owlbear-analyze", "--format", "markdown"])
        with (
            patch(f"{_CLI}.analyze", return_value=[]),
            patch(f"{_CLI}.format_json", return_value="[]") as mock_json,
            patch(f"{_CLI}.format_markdown", return_value="No analysis proposals.") as mock_md,
        ):
            main([])  # explicit empty argv → JSON default, NOT markdown from sys.argv
        mock_json.assert_called_once()
        mock_md.assert_not_called()
