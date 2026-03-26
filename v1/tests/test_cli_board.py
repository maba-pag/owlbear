"""RED tests for bearclaw board command (task #909).

Tests define the contract for ``bearclaw board``:

- AC #1: ``board`` appears in root ``--help`` output.
- AC #2: Rich table with status sections (kanban/config.yml order) and columns
  ID, Title, Assignee, Age, Tags.
- AC #3: Assignee display priority: ``assignee`` > ``claimed_by`` > ``--``.
- AC #4: Age from latest ``kanban-md log --action move --json`` entry whose
  destination matches the current status; fallback to ``created`` when no match.
- AC #5: Empty task list exits 0 and prints a message containing "No tasks".
- AC #6: CliRunner + mocked ``subprocess.run`` only — no live kanban binary.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from cli_board_fixtures import board_move, board_task
from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task(  # noqa: PLR0913
    task_id: int = 1,
    title: str = "A task",
    status: str = "in-progress",
    tags: list[str] | None = None,
    assignee: str | None = None,
    claimed_by: str | None = None,
    created: str = "2026-01-01T10:00:00+01:00",
) -> dict[str, object]:
    """Build a fake ``kanban-md list --json`` task entry."""
    t: dict[str, object] = {
        "id": task_id,
        "title": title,
        "status": status,
        "tags": tags or [],
        "created": created,
    }
    if assignee is not None:
        t["assignee"] = assignee
    if claimed_by is not None:
        t["claimed_by"] = claimed_by
    return t


def _move(
    task_id: int,
    from_status: str,
    to_status: str,
    timestamp: str = "2026-03-15T10:00:00+01:00",
) -> dict[str, object]:
    """Build a fake ``kanban-md log --action move --json`` entry."""
    return {
        "timestamp": timestamp,
        "action": "move",
        "task_id": task_id,
        "detail": f"{from_status} -> {to_status}",
    }


def _subproc(
    tasks: list[dict[str, object]],
    log_entries: list[dict[str, object]],
):
    """Return a side_effect callable for ``subprocess.run``.

    Dispatches on the presence of ``"list"`` or ``"log"`` in the arg list so
    the board command receives the right JSON payload for each call.
    """

    def _run(args: list[str], **_kwargs: object) -> MagicMock:
        proc = MagicMock()
        proc.returncode = 0
        if "list" in args:
            proc.stdout = json.dumps(tasks)
        elif "log" in args:
            proc.stdout = json.dumps(log_entries)
        else:
            proc.stdout = "[]"
        return proc

    return _run


# ---------------------------------------------------------------------------
# AC #1 — Registration
# ---------------------------------------------------------------------------


class TestFromAC_BoardRegistration:
    """AC #1: Root ``--help`` output lists ``board`` as a top-level command."""

    def test_board_in_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "board" in result.output

    def test_board_help_exits_zero(self) -> None:
        result = runner.invoke(app, ["board", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# AC #2 — Table rendering
# ---------------------------------------------------------------------------


class TestFromAC_BoardRendering:
    """AC #2: Rich table with status sections (config order) and all five columns."""

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_id_column_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([board_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "ID" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_title_column_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([board_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "Title" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_assignee_column_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([board_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "Assignee" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_age_column_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([board_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "Age" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_tags_column_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([board_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "Tags" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_status_as_section_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([board_task(status="in-progress")], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "in-progress" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_task_title(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([board_task(title="My important task")], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "My important task" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_task_id(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([board_task(task_id=42)], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "42" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_task_tags(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([board_task(tags=["cli", "phase-1"])], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "cli" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_status_order_follows_config_yml(self, mock_run: MagicMock) -> None:
        """``todo`` appears before ``in-progress`` per kanban/config.yml order."""
        tasks = [
            board_task(task_id=1, status="in-progress", title="In progress task"),
            board_task(task_id=2, status="todo", title="Todo task"),
        ]
        mock_run.side_effect = _subproc(tasks, [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        todo_pos = result.output.find("todo")
        in_progress_pos = result.output.find("in-progress")
        assert todo_pos != -1
        assert in_progress_pos != -1
        assert todo_pos < in_progress_pos

    @patch("bearclaw.commands.board.subprocess.run")
    def test_tasks_appear_under_their_own_status_section(self, mock_run: MagicMock) -> None:
        tasks = [
            board_task(task_id=10, status="review", title="Review task"),
            board_task(task_id=20, status="todo", title="Todo task"),
        ]
        mock_run.side_effect = _subproc(tasks, [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "review" in result.output
        assert "todo" in result.output
        assert "Review task" in result.output
        assert "Todo task" in result.output


# ---------------------------------------------------------------------------
# AC #3 — Assignee display
# ---------------------------------------------------------------------------


class TestFromAC_AssigneeDisplay:
    """AC #3: ``assignee`` > ``claimed_by`` > ``--``."""

    @patch("bearclaw.commands.board.subprocess.run")
    def test_assignee_shown_over_claimed_by(self, mock_run: MagicMock) -> None:
        """``assignee`` takes priority over ``claimed_by`` when both are present."""
        mock_run.side_effect = _subproc(
            [board_task(assignee="alice", claimed_by="bot-worker")],
            [],
        )
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "alice" in result.output
        assert "bot-worker" not in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_claimed_by_shown_when_no_assignee(self, mock_run: MagicMock) -> None:
        """``claimed_by`` is the display value when ``assignee`` is absent."""
        mock_run.side_effect = _subproc([board_task(claimed_by="builder-agent")], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "builder-agent" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_dash_shown_when_neither_assignee_nor_claimed_by(self, mock_run: MagicMock) -> None:
        """``--`` is the placeholder when neither assignee nor claimed_by is set."""
        mock_run.side_effect = _subproc([board_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "--" in result.output


# ---------------------------------------------------------------------------
# AC #4 — Age in status
# ---------------------------------------------------------------------------


class TestFromAC_AgeInStatus:
    """AC #4: Age from latest matching move entry; fallback to ``created``."""

    @patch("bearclaw.commands.board.subprocess.run")
    def test_age_uses_latest_move_into_current_status(self, mock_run: MagicMock) -> None:
        """When a matching move log entry exists, the move timestamp defines the age."""
        import datetime

        today = datetime.datetime.now(tz=datetime.UTC).date()
        move_date = today - datetime.timedelta(days=12)
        created_date = today - datetime.timedelta(days=41)
        task = board_task(
            task_id=151,
            title="Alpha task",
            status="in-progress",
            created=f"{created_date.isoformat()}T10:00:00+01:00",
        )
        log = [
            board_move(
                task_id=151,
                from_status="todo",
                to_status="in-progress",
                timestamp=f"{move_date.isoformat()}T10:00:00+01:00",
            )
        ]
        mock_run.side_effect = _subproc([task], log)
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        # Age derived from move (12 days) must appear; created (41 days) must not.
        assert "12" in result.output
        assert "41" not in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_age_falls_back_to_created_when_no_matching_move(self, mock_run: MagicMock) -> None:
        """When no matching move exists, age is derived from the ``created`` timestamp."""
        import datetime

        today = datetime.datetime.now(tz=datetime.UTC).date()
        created_date = today - datetime.timedelta(days=27)
        task = board_task(
            task_id=152,
            title="Beta task",
            status="in-progress",
            created=f"{created_date.isoformat()}T10:00:00+01:00",
        )
        log: list[dict[str, object]] = []
        mock_run.side_effect = _subproc([task], log)
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        # Created-derived age (27 days) must appear.
        assert "27" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_age_uses_latest_move_not_earliest(self, mock_run: MagicMock) -> None:
        """When multiple matching moves exist, the latest one defines the age."""
        import datetime

        today = datetime.datetime.now(tz=datetime.UTC).date()
        early_date = today - datetime.timedelta(days=21)
        late_date = today - datetime.timedelta(days=11)
        task = board_task(task_id=153, title="Gamma task", status="in-progress")
        log = [
            board_move(
                task_id=153,
                from_status="backlog",
                to_status="in-progress",
                timestamp=f"{early_date.isoformat()}T10:00:00+01:00",
            ),
            board_move(
                task_id=153,
                from_status="todo",
                to_status="in-progress",
                timestamp=f"{late_date.isoformat()}T10:00:00+01:00",
            ),
        ]
        mock_run.side_effect = _subproc([task], log)
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        # Latest move: 11 days; earliest: 21 days.
        assert "11" in result.output
        assert "21" not in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_age_ignores_moves_to_different_status(self, mock_run: MagicMock) -> None:
        """Move entries targeting a different destination do not affect age calculation."""
        import datetime

        today = datetime.datetime.now(tz=datetime.UTC).date()
        created_date = today - datetime.timedelta(days=29)
        wrong_move_date = today - datetime.timedelta(days=16)
        task = board_task(
            task_id=154,
            title="Delta task",
            status="review",
            created=f"{created_date.isoformat()}T10:00:00+01:00",
        )
        log = [
            # Move to "in-progress", NOT current status "review" — must be ignored.
            board_move(
                task_id=154,
                from_status="todo",
                to_status="in-progress",
                timestamp=f"{wrong_move_date.isoformat()}T10:00:00+01:00",
            ),
        ]
        mock_run.side_effect = _subproc([task], log)
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        # No matching move for "review" → falls back to created (29 days).
        assert "29" in result.output
        assert "16" not in result.output


# ---------------------------------------------------------------------------
# AC #5 — Empty board
# ---------------------------------------------------------------------------


class TestFromAC_EmptyBoard:
    """AC #5: Empty task list exits 0 and prints a message containing "No tasks"."""

    @patch("bearclaw.commands.board.subprocess.run")
    def test_empty_board_exits_zero(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0

    @patch("bearclaw.commands.board.subprocess.run")
    def test_empty_board_prints_no_tasks_message(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([], [])
        result = runner.invoke(app, ["board"])
        assert "No tasks" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_empty_board_output_is_not_blank(self, mock_run: MagicMock) -> None:
        """Output must be non-empty and contain the no-tasks message, not a blank table."""
        mock_run.side_effect = _subproc([], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert result.output.strip() != ""


# ---------------------------------------------------------------------------
# Failure-path helpers (#924)
# ---------------------------------------------------------------------------


def _subproc_fail_list(returncode: int = 1, stdout: str = ""):
    """Return a side_effect that makes the task-list call fail.

    If ``returncode`` is non-zero, the call simulates a command failure.
    If ``returncode`` is 0 and ``stdout`` is invalid JSON, it simulates a JSON
    parse failure.  Any subsequent log call returns an empty JSON array so only
    the list-stage error is observable.
    """
    from conftest import make_completed_process  # type: ignore[import-untyped]

    def _run(args: list[str], **_kwargs: object) -> object:
        if "list" in args:
            return make_completed_process(returncode=returncode, stdout=stdout)
        return make_completed_process(returncode=0, stdout="[]")

    return _run


def _subproc_fail_log(
    tasks: list[dict[str, object]],
    returncode: int = 1,
    stdout: str = "",
):
    """Return a side_effect that lets task-list succeed but makes the log call fail.

    If ``returncode`` is non-zero, the call simulates a command failure on the
    move-log stage.  If ``returncode`` is 0 and ``stdout`` is invalid JSON, it
    simulates a JSON parse failure on the move-log stage.
    """
    from conftest import make_completed_process  # type: ignore[import-untyped]

    def _run(args: list[str], **_kwargs: object) -> object:
        if "list" in args:
            return make_completed_process(returncode=0, stdout=json.dumps(tasks))
        return make_completed_process(returncode=returncode, stdout=stdout)

    return _run


# ---------------------------------------------------------------------------
# AC for #924 — Failure paths
# ---------------------------------------------------------------------------


class TestFromAC_BoardFailurePaths:
    """AC #1-3 (#924): Failure-path contract for the board command.

    Five failure classes are covered:

    - Missing binary (FileNotFoundError on spawn)
    - Non-zero task-list exit
    - Non-zero move-log exit
    - Invalid task-list JSON
    - Invalid move-log JSON

    All tests assert: exit_code == 1, an ``Error:`` prefix in output,
    ``kanban-md`` mentioned by name, a stage-specific message (task-list vs
    move-log), and correct error-type classification (command failure carries
    no ``JSON`` mention; parse failure does).

    Tests patch only ``bearclaw.commands.board.subprocess.run``.
    """

    @patch("bearclaw.commands.board.subprocess.run")
    def test_missing_binary_exits_1_with_error_referencing_kanban_md(
        self, mock_run: MagicMock
    ) -> None:
        """Spawn failure → exit 1, Error: prefix in output, kanban-md named, no JSON mention."""
        from conftest import make_missing_binary_error  # type: ignore[import-untyped]

        mock_run.side_effect = make_missing_binary_error()
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "kanban-md" in result.output
        assert "json" not in result.output.lower()

    @patch("bearclaw.commands.board.subprocess.run")
    def test_tasklist_nonzero_exit_exits_1_with_stage_specific_command_error(
        self, mock_run: MagicMock
    ) -> None:
        """Non-zero list exit → exit 1, Error:, kanban-md, task-list stage mention, no JSON."""
        mock_run.side_effect = _subproc_fail_list(returncode=1)
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "kanban-md" in result.output
        assert "task" in result.output.lower()
        assert "json" not in result.output.lower()

    @patch("bearclaw.commands.board.subprocess.run")
    def test_movelog_nonzero_exit_exits_1_with_stage_specific_command_error(
        self, mock_run: MagicMock
    ) -> None:
        """Non-zero log exit → exit 1, Error:, kanban-md, log stage mention, no JSON."""
        mock_run.side_effect = _subproc_fail_log([_task()], returncode=1)
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "kanban-md" in result.output
        assert "log" in result.output.lower()
        assert "json" not in result.output.lower()

    @patch("bearclaw.commands.board.subprocess.run")
    def test_tasklist_invalid_json_exits_1_with_json_parse_error(self, mock_run: MagicMock) -> None:
        """Invalid list JSON → exit 1, Error:, kanban-md, JSON mention, task-list mention."""
        mock_run.side_effect = _subproc_fail_list(returncode=0, stdout="not valid json {{{")
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "kanban-md" in result.output
        assert "json" in result.output.lower()
        assert "task" in result.output.lower()

    @patch("bearclaw.commands.board.subprocess.run")
    def test_movelog_invalid_json_exits_1_with_json_parse_error(self, mock_run: MagicMock) -> None:
        """Invalid log JSON → exit 1, Error:, kanban-md, JSON mention, log mention."""
        mock_run.side_effect = _subproc_fail_log(
            [_task()], returncode=0, stdout="not valid json {{{"
        )
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "kanban-md" in result.output
        assert "json" in result.output.lower()
        assert "log" in result.output.lower()


# ---------------------------------------------------------------------------
# Builder-discovered tests
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-added tests covering AC2 subprocess call-count requirements.

    AC2: invoke kanban-md list --json exactly once AND kanban-md log --action
    move --json exactly once; when no tasks are returned the log call must be
    skipped entirely.
    """

    @patch("bearclaw.commands.board.subprocess.run")
    def test_subprocess_called_exactly_twice_when_tasks_present(self, mock_run: MagicMock) -> None:
        """With tasks: subprocess.run is invoked exactly twice — once for list, once for log."""
        mock_run.side_effect = _subproc([_task()], [])
        runner.invoke(app, ["board"])
        assert mock_run.call_count == 2
        first_args = mock_run.call_args_list[0][0][0]
        second_args = mock_run.call_args_list[1][0][0]
        assert "list" in first_args
        assert "--json" in first_args
        assert "log" in second_args
        assert "--action" in second_args
        assert "move" in second_args

    @patch("bearclaw.commands.board.subprocess.run")
    def test_subprocess_called_exactly_once_when_no_tasks(self, mock_run: MagicMock) -> None:
        """Empty board: only list --json is called; log subprocess call is skipped."""
        mock_run.side_effect = _subproc([], [])
        runner.invoke(app, ["board"])
        assert mock_run.call_count == 1
        first_args = mock_run.call_args_list[0][0][0]
        assert "list" in first_args
        assert "--json" in first_args


# ---------------------------------------------------------------------------
# Helpers for AC #925 — age-threshold styling
# ---------------------------------------------------------------------------
import contextlib  # noqa: E402
import datetime as _dt  # noqa: E402
import pathlib  # noqa: E402
import tempfile  # noqa: E402


def _now_minus_hours(hours: float) -> str:
    """Return an ISO-8601 UTC timestamp *hours* before the current moment."""
    return (_dt.datetime.now(tz=_dt.UTC) - _dt.timedelta(hours=hours)).isoformat()


def _age_subproc(hours_ago: float):
    """Subprocess side-effect: task entered in-progress *hours_ago* hours ago."""
    task = _task(task_id=1, title="Threshold task", status="in-progress")
    log = [
        _move(
            task_id=1,
            from_status="todo",
            to_status="in-progress",
            timestamp=_now_minus_hours(hours_ago),
        )
    ]
    return _subproc([task], log)


# Env that forces Rich to emit ANSI sequences through a non-TTY CliRunner.
_ANSI_ENV = {"FORCE_COLOR": "1", "TTY_COMPATIBLE": "1", "TTY_INTERACTIVE": "0"}

# Minimal valid config with three testable threshold tiers.
_THRESHOLD_CONFIG_YAML = """\
statuses:
  - name: in-progress
tui:
  age_thresholds:
    - after: 0s
      color: "242"
    - after: 1h
      color: "34"
    - after: 24h
      color: "226"
"""


@contextlib.contextmanager
def _with_config(content: str | None):  # type: ignore[return]
    """Patch _KANBAN_CONFIG to a temp file holding *content*.

    If *content* is ``None`` the path points to a non-existent file so that
    reading it raises ``FileNotFoundError``.
    """
    with tempfile.TemporaryDirectory() as td:
        if content is None:
            cfg = pathlib.Path(td) / "absent" / "config.yml"
        else:
            cfg = pathlib.Path(td) / "config.yml"
            cfg.write_text(content, encoding="utf-8")
        with patch("bearclaw.commands.board._KANBAN_CONFIG", cfg):
            yield


# ---------------------------------------------------------------------------
# AC #3 and #4 — threshold styling contract (task #925)
# ---------------------------------------------------------------------------


class TestFromAC_AgeThresholdStyling:
    """AC #3/#4 (task #925): Age cell ANSI styling driven by tui.age_thresholds config.

    All tests assert that specific ANSI color sequences appear in board output
    when the task age crosses a configured threshold.  Every test FAILS on
    current HEAD until ``#921`` lands because ``board.py`` does not yet apply
    Age cell styling.
    """

    @patch("bearclaw.commands.board.subprocess.run")
    def test_age_above_1h_threshold_emits_34_tier_ansi_color(self, mock_run: MagicMock) -> None:
        """Age 3 h crosses the 1 h threshold → 38;5;34 ANSI sequence in Age cell."""
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;34" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_age_above_24h_threshold_emits_226_tier_ansi_color(self, mock_run: MagicMock) -> None:
        """Age 36 h crosses the 24 h threshold → 38;5;226 ANSI sequence in Age cell."""
        mock_run.side_effect = _age_subproc(36.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;226" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_base_zero_second_tier_color_242_applied_for_fresh_task(
        self, mock_run: MagicMock
    ) -> None:
        """Age 30 min is above 0 s, below 1 h → base tier color 242 → 38;5;242 in output."""
        mock_run.side_effect = _age_subproc(0.5)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;242" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_numeric_color_string_becomes_38_5_n_ansi_not_raw_config_string(
        self, mock_run: MagicMock
    ) -> None:
        """Config color "34" maps to 38;5;34 ANSI (Rich color(34)), not a literal "34" token."""
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        # Must normalise "34" → color(34) → 38;5;34 escape, not embed the raw string "34".
        assert "38;5;34" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_threshold_boundary_same_displayed_age_text_different_ansi(
        self, mock_run: MagicMock
    ) -> None:
        """AC #3: 30 min and 3 h both render '0d' Age text but receive different tier colors.

        Raw age duration drives threshold selection, not the rounded display text.
        The 30-min task stays in the base tier (color 242); the 3-h task enters
        the 1 h tier (color 34).  This test verifies the contrast.
        """
        with _with_config(_THRESHOLD_CONFIG_YAML):
            mock_run.side_effect = _age_subproc(0.5)
            result_below = runner.invoke(app, ["board"], env=_ANSI_ENV)
            mock_run.side_effect = _age_subproc(3.0)
            result_above = runner.invoke(app, ["board"], env=_ANSI_ENV)

        # Both fall within the current calendar day so the display text is identical.
        assert "0d" in result_below.output
        assert "0d" in result_above.output
        # Base-tier task must NOT show the 1 h tier color.
        assert "38;5;34" not in result_below.output
        # 1 h tier task MUST show color 34 — FAILS on current HEAD.
        assert "38;5;34" in result_above.output


# ---------------------------------------------------------------------------
# AC #5 — fallback contract (task #925)
# ---------------------------------------------------------------------------


class TestFromAC_AgeThresholdFallback:
    """AC #5 (task #925): missing or invalid threshold config must not break the board.

    Each test verifies the fallback contract: exit 0 + plain Age text.
    Contrast tests also establish the positive baseline (valid config → ANSI)
    so that the test fails on current HEAD (no styling exists yet) while
    simultaneously documenting that the fallback produces no unexpected ANSI.
    """

    @patch("bearclaw.commands.board.subprocess.run")
    def test_missing_config_file_exits_zero_with_plain_age_text(self, mock_run: MagicMock) -> None:
        """Missing kanban/config.yml → board exits 0 with plain Age, no crash.

        Currently FAILS because ``_read_status_order`` raises ``FileNotFoundError``
        when the path does not exist.
        """
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(None):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "0d" in result.output
        assert "38;5;34" not in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_malformed_yaml_config_exits_zero_with_plain_age_text(
        self, mock_run: MagicMock
    ) -> None:
        """Malformed YAML in config → board exits 0 with plain Age, no crash.

        Currently FAILS because ``yaml.safe_load`` raises ``YAMLError`` which
        propagates unhandled from ``_read_status_order``.
        """
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config("{ invalid yaml :"):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "0d" in result.output
        assert "38;5;34" not in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_tui_section_absent_plain_age_contrast_valid_config_has_ansi(
        self, mock_run: MagicMock
    ) -> None:
        """Absent tui section → plain Age; valid config → styled Age (RED: baseline fails)."""
        # Baseline: valid thresholds emit styled output (FAILS on current HEAD).
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result_valid = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert "38;5;34" in result_valid.output  # RED trigger ✓

        # Fallback: absent tui section → no threshold ANSI, board still exits 0.
        _no_tui = "statuses:\n  - name: in-progress\n"
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_no_tui):
            result_fallback = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result_fallback.exit_code == 0
        assert "38;5;34" not in result_fallback.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_age_thresholds_not_a_list_plain_age_contrast_valid_config_has_ansi(
        self, mock_run: MagicMock
    ) -> None:
        """Non-list age_thresholds → plain Age fallback; valid config → styled Age."""
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result_valid = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert "38;5;34" in result_valid.output  # RED trigger ✓

        _bad = "statuses:\n  - name: in-progress\ntui:\n  age_thresholds: not_a_list\n"
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_bad):
            result_fallback = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result_fallback.exit_code == 0
        assert "38;5;34" not in result_fallback.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_threshold_invalid_duration_plain_age_contrast_valid_config_has_ansi(
        self, mock_run: MagicMock
    ) -> None:
        """Invalid threshold duration → plain Age fallback; valid config → styled Age."""
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result_valid = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert "38;5;34" in result_valid.output  # RED trigger ✓

        _bad = (
            "statuses:\n  - name: in-progress\n"
            'tui:\n  age_thresholds:\n    - after: not_a_duration\n      color: "34"\n'
        )
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_bad):
            result_fallback = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result_fallback.exit_code == 0
        assert "38;5;34" not in result_fallback.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_threshold_invalid_color_value_plain_age_contrast_valid_config_has_ansi(
        self, mock_run: MagicMock
    ) -> None:
        """Invalid threshold color value → plain Age fallback; valid config → styled Age."""
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result_valid = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert "38;5;34" in result_valid.output  # RED trigger ✓

        _bad = (
            "statuses:\n  - name: in-progress\n"
            "tui:\n  age_thresholds:\n"
            '    - after: 1h\n      color: "absolutelynotavalidrichcolor"\n'
        )
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_bad):
            result_fallback = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result_fallback.exit_code == 0
        assert "38;5;34" not in result_fallback.output


# ---------------------------------------------------------------------------
# Helpers for #921 — multi-status threshold config
# ---------------------------------------------------------------------------

# Config that includes todo, in-progress, and review in status order alongside
# age thresholds — used in order/grouping invariant tests so that both "todo"
# and "in-progress" appear in the config-ordered sections.
_MULTI_STATUS_THRESHOLD_CONFIG_YAML = """\
statuses:
  - name: todo
  - name: in-progress
  - name: review
tui:
  age_thresholds:
    - after: 0s
      color: "242"
    - after: 1h
      color: "34"
    - after: 24h
      color: "226"
"""


# ---------------------------------------------------------------------------
# AC #3 — Age cell scope invariants (task #921)
# ---------------------------------------------------------------------------


class TestFromAC_921_AgeThresholdCellScope:
    """AC #3 (#921): Age-threshold ANSI styling confined to the Age cell only.

    Title, ID, Assignee, and Tags cells must not receive the threshold color.
    Status order, task grouping, and displayed age text must be unchanged from
    the #910 baseline.

    Every test includes an ANSI assertion as a RED trigger: it fails on current
    HEAD because board.py does not apply any threshold styling yet.  Once the
    implementation lands, the ANSI assertion passes AND the invariant assertion
    must also hold, constraining the builder to cell-level styling only.
    """

    @patch("bearclaw.commands.board.subprocess.run")
    def test_threshold_color_not_directly_preceding_title_text(self, mock_run: MagicMock) -> None:
        """Threshold ANSI opener must not immediately precede the title text.

        If the style were applied to the Title cell the output would contain
        the ANSI opener (``38;5;34m``) directly before the title string.  This
        test fails on HEAD (no ANSI present yet) and constrains styling to the
        Age cell.
        """
        unique_title = "SENTINEL_TITLE_NOT_STYLED_ABC"
        task = _task(task_id=1, title=unique_title, status="in-progress")
        log = [_move(1, "todo", "in-progress", timestamp=_now_minus_hours(3.0))]
        mock_run.side_effect = _subproc([task], log)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;34" in result.output  # Age IS styled — RED trigger
        assert unique_title in result.output  # title still renders
        assert f"38;5;34m{unique_title}" not in result.output  # title NOT styled

    @patch("bearclaw.commands.board.subprocess.run")
    def test_threshold_color_not_directly_preceding_id_text(self, mock_run: MagicMock) -> None:
        """Threshold ANSI opener must not immediately precede the task ID text.

        Fails on HEAD (no ANSI); once styling lands, asserts ID cell is not
        wrapped with the threshold color.
        """
        task = _task(task_id=88877, title="ID cell scope check", status="in-progress")
        log = [_move(88877, "todo", "in-progress", timestamp=_now_minus_hours(3.0))]
        mock_run.side_effect = _subproc([task], log)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;34" in result.output  # Age IS styled — RED trigger
        assert "88877" in result.output  # ID still renders
        assert "38;5;34m88877" not in result.output  # ID NOT wrapped with threshold color

    @patch("bearclaw.commands.board.subprocess.run")
    def test_tags_column_data_intact_when_threshold_fires(self, mock_run: MagicMock) -> None:
        """Tags column must render its data unchanged when threshold styling fires.

        Fails on HEAD (no ANSI); also asserts that the unique tag text is not
        directly wrapped with the threshold ANSI opener.
        """
        unique_tag = "unique-tag-xyz-sentinel"
        task = _task(
            task_id=1,
            title="Tagged task",
            status="in-progress",
            tags=["phase-99", unique_tag],
        )
        log = [_move(1, "todo", "in-progress", timestamp=_now_minus_hours(3.0))]
        mock_run.side_effect = _subproc([task], log)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;34" in result.output  # Age IS styled — RED trigger
        assert unique_tag in result.output  # tag text still renders
        assert f"38;5;34m{unique_tag}" not in result.output  # tag NOT wrapped

    @patch("bearclaw.commands.board.subprocess.run")
    def test_threshold_color_not_applied_to_assignee_cell(self, mock_run: MagicMock) -> None:
        """Threshold ANSI opener must not immediately precede the assignee text.

        If the style were applied to the Assignee cell the output would contain
        the ANSI opener (``38;5;34m``) directly before the assignee string.
        This test constrains styling to the Age cell only and guards against
        a regression to row-level or multi-cell styling.
        """
        unique_assignee = "SENTINEL_ASSIGNEE_NOT_STYLED_XYZ"
        task = _task(
            task_id=1,
            title="Assignee scope check",
            status="in-progress",
            assignee=unique_assignee,
        )
        log = [_move(1, "todo", "in-progress", timestamp=_now_minus_hours(3.0))]
        mock_run.side_effect = _subproc([task], log)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;34" in result.output  # Age IS styled — regression guard active
        assert unique_assignee in result.output  # assignee still renders
        assert f"38;5;34m{unique_assignee}" not in result.output  # assignee NOT styled

    @patch("bearclaw.commands.board.subprocess.run")
    def test_status_order_preserved_while_threshold_styling_applied(
        self, mock_run: MagicMock
    ) -> None:
        """``todo`` section appears before ``in-progress`` when threshold config is active.

        Uses a config with both statuses listed in the canonical order.  The
        ANSI assertion is the RED trigger — fails on HEAD because no styling
        exists yet.  Once styling lands, status ordering must remain unaffected.
        """
        tasks = [
            _task(task_id=1, status="in-progress", title="In-prog task"),
            _task(task_id=2, status="todo", title="Todo task"),
        ]
        log = [_move(1, "todo", "in-progress", timestamp=_now_minus_hours(3.0))]
        mock_run.side_effect = _subproc(tasks, log)
        with _with_config(_MULTI_STATUS_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;34" in result.output  # Age IS styled — RED trigger
        todo_pos = result.output.find("todo")
        in_progress_pos = result.output.find("in-progress")
        assert todo_pos != -1
        assert in_progress_pos != -1
        assert todo_pos < in_progress_pos  # config-defined order preserved

    @patch("bearclaw.commands.board.subprocess.run")
    def test_task_grouping_preserved_while_threshold_styling_applied(
        self, mock_run: MagicMock
    ) -> None:
        """Each task must appear under its own status section when threshold config is active.

        Fails on HEAD because the ANSI assertion (RED trigger) fires first.
        Once styling lands, section grouping must be unaffected: each task
        title appears after its own section header in the output.
        """
        tasks = [
            _task(task_id=10, status="review", title="Review section task"),
            _task(task_id=20, status="todo", title="Todo section task"),
        ]
        log = [_move(10, "in-progress", "review", timestamp=_now_minus_hours(27.0))]
        mock_run.side_effect = _subproc(tasks, log)
        with _with_config(_MULTI_STATUS_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;226" in result.output  # 27 h → 24 h tier — RED trigger
        review_pos = result.output.find("review")
        todo_pos = result.output.find("todo")
        review_task_pos = result.output.find("Review section task")
        todo_task_pos = result.output.find("Todo section task")
        assert review_pos != -1
        assert todo_pos != -1
        assert review_task_pos > review_pos  # task title after its own section header
        assert todo_task_pos > todo_pos  # task title after its own section header

    @patch("bearclaw.commands.board.subprocess.run")
    def test_age_text_value_unchanged_after_stripping_ansi_sequences(
        self, mock_run: MagicMock
    ) -> None:
        """Stripping ANSI sequences from styled output must leave plain age text intact.

        Uses a task created exactly two days ago so the displayed age is always
        ``2d`` regardless of the time of day the test runs.  Verifies that
        styling is purely additive markup that does not alter the visible label.
        The ANSI assertion is the RED trigger.
        """
        import datetime as _dt2
        import re

        two_days_ago = (_dt2.datetime.now(tz=_dt2.UTC) - _dt2.timedelta(days=2)).date()
        task = _task(
            task_id=1,
            title="Age text task",
            status="in-progress",
            created=f"{two_days_ago.isoformat()}T00:00:00+00:00",
        )
        log: list[dict[str, object]] = []  # no move entry — fallback to created date
        mock_run.side_effect = _subproc([task], log)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result.exit_code == 0
        assert "38;5;226" in result.output  # 2 d → 24 h tier — RED trigger
        stripped = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "2d" in stripped  # age text preserved after ANSI removal


# ---------------------------------------------------------------------------
# AC #4 — fallback for malformed mapping entries (task #921)
# ---------------------------------------------------------------------------


class TestFromAC_921_FallbackMappingValidation:
    """AC #4 (#921): Malformed threshold mapping entries → plain Age fallback.

    Covers the "not a list of {after,color} mappings" sub-case of AC4 that
    ``TestFromAC_AgeThresholdFallback`` does not test explicitly: entries with
    a missing ``after`` key, a missing ``color`` key, and a list of scalars
    instead of mapping objects.

    Contrast pattern mirrors the existing fallback tests: the first invoke with
    valid config asserts ANSI styling works (RED trigger — fails on HEAD);
    the second invoke with the malformed config verifies the fallback.
    """

    @patch("bearclaw.commands.board.subprocess.run")
    def test_threshold_entry_missing_after_key_falls_back_to_plain_age(
        self, mock_run: MagicMock
    ) -> None:
        """Entry ``{color: "34"}`` with no ``after`` key → plain Age, exit 0."""
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result_valid = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert "38;5;34" in result_valid.output  # RED trigger ✓

        _bad = 'statuses:\n  - name: in-progress\ntui:\n  age_thresholds:\n    - color: "34"\n'
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_bad):
            result_fallback = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result_fallback.exit_code == 0
        assert "Threshold task" in result_fallback.output  # row rendered
        assert "38;5;34" not in result_fallback.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_threshold_entry_missing_color_key_falls_back_to_plain_age(
        self, mock_run: MagicMock
    ) -> None:
        """Entry ``{after: 1h}`` with no ``color`` key → plain Age, exit 0."""
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result_valid = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert "38;5;34" in result_valid.output  # RED trigger ✓

        _bad = "statuses:\n  - name: in-progress\ntui:\n  age_thresholds:\n    - after: 1h\n"
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_bad):
            result_fallback = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result_fallback.exit_code == 0
        assert "Threshold task" in result_fallback.output  # row rendered
        assert "38;5;34" not in result_fallback.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_threshold_list_of_scalars_falls_back_to_plain_age(self, mock_run: MagicMock) -> None:
        """``age_thresholds`` is a list of scalars (not mappings) → plain Age, exit 0."""
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_THRESHOLD_CONFIG_YAML):
            result_valid = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert "38;5;34" in result_valid.output  # RED trigger ✓

        _bad = "statuses:\n  - name: in-progress\ntui:\n  age_thresholds:\n    - 1h\n    - 24h\n"
        mock_run.side_effect = _age_subproc(3.0)
        with _with_config(_bad):
            result_fallback = runner.invoke(app, ["board"], env=_ANSI_ENV)
        assert result_fallback.exit_code == 0
        assert "Threshold task" in result_fallback.output  # row rendered
        assert "38;5;34" not in result_fallback.output
