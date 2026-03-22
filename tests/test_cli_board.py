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
        mock_run.side_effect = _subproc([_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "ID" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_title_column_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "Title" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_assignee_column_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "Assignee" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_age_column_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "Age" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_tags_column_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([_task()], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "Tags" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_status_as_section_header(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([_task(status="in-progress")], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "in-progress" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_task_title(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([_task(title="My important task")], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "My important task" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_task_id(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([_task(task_id=42)], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "42" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_renders_task_tags(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = _subproc([_task(tags=["cli", "phase-1"])], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "cli" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_status_order_follows_config_yml(self, mock_run: MagicMock) -> None:
        """``todo`` appears before ``in-progress`` per kanban/config.yml order."""
        tasks = [
            _task(task_id=1, status="in-progress", title="In progress task"),
            _task(task_id=2, status="todo", title="Todo task"),
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
            _task(task_id=10, status="review", title="Review task"),
            _task(task_id=20, status="todo", title="Todo task"),
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
        mock_run.side_effect = _subproc([_task(assignee="alice", claimed_by="bot-worker")], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "alice" in result.output
        assert "bot-worker" not in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_claimed_by_shown_when_no_assignee(self, mock_run: MagicMock) -> None:
        """``claimed_by`` is the display value when ``assignee`` is absent."""
        mock_run.side_effect = _subproc([_task(claimed_by="builder-agent")], [])
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 0
        assert "builder-agent" in result.output

    @patch("bearclaw.commands.board.subprocess.run")
    def test_dash_shown_when_neither_assignee_nor_claimed_by(self, mock_run: MagicMock) -> None:
        """``--`` is the placeholder when neither assignee nor claimed_by is set."""
        mock_run.side_effect = _subproc([_task()], [])
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
        task = _task(
            task_id=151,
            title="Alpha task",
            status="in-progress",
            created=f"{created_date.isoformat()}T10:00:00+01:00",
        )
        log = [
            _move(
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
        task = _task(
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
        task = _task(task_id=153, title="Gamma task", status="in-progress")
        log = [
            _move(
                task_id=153,
                from_status="backlog",
                to_status="in-progress",
                timestamp=f"{early_date.isoformat()}T10:00:00+01:00",
            ),
            _move(
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
        task = _task(
            task_id=154,
            title="Delta task",
            status="review",
            created=f"{created_date.isoformat()}T10:00:00+01:00",
        )
        log = [
            # Move to "in-progress", NOT current status "review" — must be ignored.
            _move(
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

    def _run(args: list[str], **_kwargs: object) -> MagicMock:
        proc = MagicMock()
        if "list" in args:
            proc.returncode = returncode
            proc.stdout = stdout
        else:
            proc.returncode = 0
            proc.stdout = "[]"
        return proc

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

    def _run(args: list[str], **_kwargs: object) -> MagicMock:
        proc = MagicMock()
        if "list" in args:
            proc.returncode = 0
            proc.stdout = json.dumps(tasks)
        else:
            proc.returncode = returncode
            proc.stdout = stdout
        return proc

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
        mock_run.side_effect = FileNotFoundError(
            "No such file or directory: 'kanban/kanban-md.exe'"
        )
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
    def test_subprocess_called_exactly_twice_when_tasks_present(
        self, mock_run: MagicMock
    ) -> None:
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
