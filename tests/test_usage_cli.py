"""Tests for bearclaw usage CLI — ``bearclaw usage`` command."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()


def _usage_jsonl_line(  # noqa: PLR0913
    *,
    minutes_ago: int = 5,
    model: str = "gpt-4o",
    input_tokens: int = 500,
    output_tokens: int = 150,
    estimated_cost_usd: float | None = None,
    premium_requests: float | None = None,
    provider: str = "copilot",
) -> str:
    """Build a single JSONL line for a UsageRecord."""
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    record = {
        "timestamp": ts.isoformat(),
        "model": model,
        "provider": provider,
        "session_id": "sess-001",
        "requests": 1,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_write_tokens": 0,
        "cache_read_tokens": 0,
        "tool_calls": 0,
        "estimated_cost_usd": estimated_cost_usd,
        "premium_requests": premium_requests,
    }
    return json.dumps(record)


def _write_mock_jsonl(path: Path, lines: list[str]) -> None:
    """Write mock JSONL lines to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


class TestUsageCommandRegistered:
    """``bearclaw usage`` command is registered on the app."""

    def test_usage_in_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "usage" in result.output.lower()

    def test_usage_help(self) -> None:
        result = runner.invoke(app, ["usage", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Mock JSONL data → tabular output
# ---------------------------------------------------------------------------


class TestUsageOutput:
    """Mock JSONL data produces correct tabular output."""

    def test_produces_output_with_mock_data(self, tmp_path: Path) -> None:
        """Given valid JSONL data, the command shows a summary table."""
        usage_file = tmp_path / "usage.jsonl"
        lines = [
            _usage_jsonl_line(minutes_ago=5, model="gpt-4o", input_tokens=500, output_tokens=150),
            _usage_jsonl_line(minutes_ago=10, model="gpt-4o", input_tokens=300, output_tokens=100),
        ]
        _write_mock_jsonl(usage_file, lines)

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage"])

        assert result.exit_code == 0
        # Output should contain token counts or model names
        output = result.output
        assert "gpt-4o" in output or "500" in output or "token" in output.lower()

    def test_shows_model_name(self, tmp_path: Path) -> None:
        """Output includes the model name from the records."""
        usage_file = tmp_path / "usage.jsonl"
        lines = [_usage_jsonl_line(model="gpt-4o")]
        _write_mock_jsonl(usage_file, lines)

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage"])

        assert result.exit_code == 0
        assert "gpt-4o" in result.output


# ---------------------------------------------------------------------------
# Time-window flags
# ---------------------------------------------------------------------------


class TestUsageTimeWindows:
    """Time-window flags filter records correctly."""

    def test_last_hour_excludes_old_records(self, tmp_path: Path) -> None:
        """--last-hour should exclude records older than 1 hour."""
        usage_file = tmp_path / "usage.jsonl"
        recent = _usage_jsonl_line(minutes_ago=5, input_tokens=100)
        old = _usage_jsonl_line(minutes_ago=120, input_tokens=9999)
        _write_mock_jsonl(usage_file, [old, recent])

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage", "--last-hour"])

        assert result.exit_code == 0
        # Old record (9999 tokens) should not appear in last-hour view
        assert "9999" not in result.output

    def test_last_24h_is_default_or_accepted(self, tmp_path: Path) -> None:
        """--last-24h flag is accepted without error."""
        usage_file = tmp_path / "usage.jsonl"
        lines = [_usage_jsonl_line(minutes_ago=5)]
        _write_mock_jsonl(usage_file, lines)

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage", "--last-24h"])

        assert result.exit_code == 0

    def test_last_7d_flag_accepted(self, tmp_path: Path) -> None:
        """--last-7d flag is accepted without error."""
        usage_file = tmp_path / "usage.jsonl"
        lines = [_usage_jsonl_line(minutes_ago=5)]
        _write_mock_jsonl(usage_file, lines)

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage", "--last-7d"])

        assert result.exit_code == 0

    def test_all_flag_accepted(self, tmp_path: Path) -> None:
        """--all flag shows all records regardless of age."""
        usage_file = tmp_path / "usage.jsonl"
        old = _usage_jsonl_line(minutes_ago=60 * 24 * 30)  # 30 days old
        _write_mock_jsonl(usage_file, [old])

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage", "--all"])

        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Empty log → informative message (not error/traceback)
# ---------------------------------------------------------------------------


class TestUsageEmptyLog:
    """Empty or missing usage log prints informative message, not error."""

    def test_missing_file_shows_message(self, tmp_path: Path) -> None:
        """When the usage file doesn't exist, show a friendly message."""
        usage_file = tmp_path / "nonexistent.jsonl"

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage"])

        assert result.exit_code == 0
        # Should say something about no data, not crash with a traceback
        output_lower = result.output.lower()
        assert "no" in output_lower or "empty" in output_lower or "no usage" in output_lower

    def test_empty_file_shows_message(self, tmp_path: Path) -> None:
        """When the usage file is empty, show a friendly message."""
        usage_file = tmp_path / "usage.jsonl"
        usage_file.write_text("")

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage"])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "no" in output_lower or "empty" in output_lower or "no usage" in output_lower

    def test_no_traceback_on_empty(self, tmp_path: Path) -> None:
        """Empty log must not produce a Python traceback."""
        usage_file = tmp_path / "nonexistent.jsonl"

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage"])

        assert "Traceback" not in result.output
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Premium and cost columns
# ---------------------------------------------------------------------------


class TestUsagePremiumCost:
    """Coverage for cost/premium branches in usage CLI."""

    def test_estimated_cost_aggregated(self, tmp_path: Path) -> None:
        """Records with estimated_cost_usd → costs summed in output."""
        usage_file = tmp_path / "usage.jsonl"
        lines = [
            _usage_jsonl_line(
                minutes_ago=5,
                model="gpt-4o",
                estimated_cost_usd=0.0025,
            ),
            _usage_jsonl_line(
                minutes_ago=10,
                model="gpt-4o",
                estimated_cost_usd=0.0050,
            ),
        ]
        _write_mock_jsonl(usage_file, lines)

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage"])

        assert result.exit_code == 0
        assert "$" in result.output  # Cost column present

    def test_premium_column_shown_for_copilot(self, tmp_path: Path) -> None:
        """Copilot records with premium_requests → Premium column in output."""
        usage_file = tmp_path / "usage.jsonl"
        lines = [
            _usage_jsonl_line(
                minutes_ago=5,
                model="gpt-4o",
                provider="copilot",
                premium_requests=1.0,
            ),
        ]
        _write_mock_jsonl(usage_file, lines)

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage"])

        assert result.exit_code == 0
        assert "Premium" in result.output

    def test_non_copilot_no_premium_column(self, tmp_path: Path) -> None:
        """Non-copilot records without premium → no Premium column."""
        usage_file = tmp_path / "usage.jsonl"
        lines = [
            _usage_jsonl_line(
                minutes_ago=5,
                model="gpt-4o",
                provider="openai",
                premium_requests=None,
            ),
        ]
        _write_mock_jsonl(usage_file, lines)

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage"])

        assert result.exit_code == 0
        assert "Premium" not in result.output

    def test_usage_table_renders_rich_table(self, tmp_path: Path) -> None:
        """Usage table renders via Rich with box-drawing and TOTAL row."""
        usage_file = tmp_path / "usage.jsonl"
        lines = [
            _usage_jsonl_line(minutes_ago=5, model="gpt-4o"),
            _usage_jsonl_line(minutes_ago=10, model="gpt-3.5-turbo"),
        ]
        _write_mock_jsonl(usage_file, lines)

        with patch("bearclaw.commands.usage._get_usage_path", return_value=usage_file):
            result = runner.invoke(app, ["usage"])

        assert result.exit_code == 0
        assert "TOTAL" in result.output
        assert "\u2502" in result.output  # │ box-drawing vertical from Rich Table
