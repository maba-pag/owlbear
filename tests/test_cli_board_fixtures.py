"""RED tests for cli_board_fixtures helpers (task #936).

Tests define the contract for ``tests/cli_board_fixtures.py``:

- AC #1: ``board_task()``, ``board_move()``, and ``board_payloads()`` helpers
  return paired kanban-md list/log JSON from shared semantic inputs.
- AC #2: Tests cover assignee-precedence and latest-move-age fixtures, including
  ``created`` fallback and wrong-destination-ignore cases.
- AC #3: Scope stays under ``tests/`` only — no conftest.py, src/, or #926 scope.
- AC #4: All tests fail before paired implementation task (#939) lands.
  ImportError from a missing ``cli_board_fixtures`` module is acceptable RED.
- AC #5: Does NOT modify existing tests in ``tests/test_cli_board.py``.
"""

from __future__ import annotations

import datetime
import json

# ---------------------------------------------------------------------------
# AC #1 — board_task() helper contract
# ---------------------------------------------------------------------------


class TestFromAC_BoardTaskHelper:
    """AC #1: board_task() returns a dict matching kanban-md list --json task shape."""

    def test_board_task_has_id_field(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task()
        assert "id" in t

    def test_board_task_has_title_field(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task()
        assert "title" in t

    def test_board_task_has_status_field(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task()
        assert "status" in t

    def test_board_task_has_tags_field(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task()
        assert "tags" in t

    def test_board_task_has_created_field(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task()
        assert "created" in t

    def test_board_task_id_kwarg_is_reflected(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task(task_id=99)
        assert t["id"] == 99

    def test_board_task_title_kwarg_is_reflected(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task(title="Specific title")
        assert t["title"] == "Specific title"

    def test_board_task_status_kwarg_is_reflected(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task(status="review")
        assert t["status"] == "review"

    def test_board_task_tags_kwarg_is_reflected(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task(tags=["cli", "phase-14"])
        assert t["tags"] == ["cli", "phase-14"]

    def test_board_task_created_kwarg_is_reflected(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        ts = "2026-02-15T10:00:00+01:00"
        t = board_task(created=ts)
        assert t["created"] == ts

    def test_board_task_assignee_kwarg_present_when_given(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task(assignee="alice")
        assert t.get("assignee") == "alice"

    def test_board_task_claimed_by_kwarg_present_when_given(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task(claimed_by="bot-worker")
        assert t.get("claimed_by") == "bot-worker"

    def test_board_task_no_assignee_key_when_omitted(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task()
        assert "assignee" not in t

    def test_board_task_no_claimed_by_key_when_omitted(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task()
        assert "claimed_by" not in t

    def test_board_task_default_tags_is_empty_list(self) -> None:
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task()
        assert t["tags"] == []


# ---------------------------------------------------------------------------
# AC #1 — board_move() helper contract
# ---------------------------------------------------------------------------


class TestFromAC_BoardMoveHelper:
    """AC #1: board_move() returns a dict matching kanban-md log --action move --json shape."""

    def test_board_move_has_timestamp_field(self) -> None:
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        m = board_move(task_id=1, from_status="todo", to_status="in-progress")
        assert "timestamp" in m

    def test_board_move_has_action_field(self) -> None:
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        m = board_move(task_id=1, from_status="todo", to_status="in-progress")
        assert "action" in m

    def test_board_move_has_task_id_field(self) -> None:
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        m = board_move(task_id=1, from_status="todo", to_status="in-progress")
        assert "task_id" in m

    def test_board_move_has_detail_field(self) -> None:
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        m = board_move(task_id=1, from_status="todo", to_status="in-progress")
        assert "detail" in m

    def test_board_move_action_value_is_move(self) -> None:
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        m = board_move(task_id=1, from_status="todo", to_status="in-progress")
        assert m["action"] == "move"

    def test_board_move_task_id_kwarg_reflected(self) -> None:
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        m = board_move(task_id=42, from_status="todo", to_status="in-progress")
        assert m["task_id"] == 42

    def test_board_move_detail_contains_to_status(self) -> None:
        """Detail must encode the destination status so the board command can parse it."""
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        m = board_move(task_id=1, from_status="todo", to_status="review")
        assert "review" in m["detail"]

    def test_board_move_detail_contains_from_status(self) -> None:
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        m = board_move(task_id=1, from_status="backlog", to_status="in-progress")
        assert "backlog" in m["detail"]

    def test_board_move_timestamp_kwarg_reflected(self) -> None:
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        ts = "2026-03-01T09:00:00+01:00"
        m = board_move(task_id=1, from_status="todo", to_status="in-progress", timestamp=ts)
        assert m["timestamp"] == ts


# ---------------------------------------------------------------------------
# AC #1 — board_payloads() helper contract
# ---------------------------------------------------------------------------


class TestFromAC_BoardPayloadsHelper:
    """AC #1: board_payloads() returns paired list_json and log_json strings."""

    def test_board_payloads_returns_two_element_sequence(self) -> None:
        from cli_board_fixtures import (  # type: ignore[import-not-found]
            board_move,
            board_payloads,
            board_task,
        )

        task = board_task(task_id=1, status="in-progress")
        move = board_move(task_id=1, from_status="todo", to_status="in-progress")
        result = board_payloads(tasks=[task], moves=[move])
        assert len(result) == 2

    def test_board_payloads_list_json_is_valid_json_string(self) -> None:
        from cli_board_fixtures import board_payloads, board_task  # type: ignore[import-not-found]

        task = board_task(task_id=1, status="in-progress")
        list_json, _ = board_payloads(tasks=[task], moves=[])
        assert isinstance(list_json, str)
        parsed = json.loads(list_json)
        assert isinstance(parsed, list)

    def test_board_payloads_log_json_is_valid_json_string(self) -> None:
        from cli_board_fixtures import (  # type: ignore[import-not-found]
            board_move,
            board_payloads,
            board_task,
        )

        task = board_task(task_id=1, status="in-progress")
        move = board_move(task_id=1, from_status="todo", to_status="in-progress")
        _, log_json = board_payloads(tasks=[task], moves=[move])
        assert isinstance(log_json, str)
        parsed = json.loads(log_json)
        assert isinstance(parsed, list)

    def test_board_payloads_list_json_contains_task_data(self) -> None:
        from cli_board_fixtures import board_payloads, board_task  # type: ignore[import-not-found]

        task = board_task(task_id=77, title="Fixture task", status="review")
        list_json, _ = board_payloads(tasks=[task], moves=[])
        parsed = json.loads(list_json)
        assert any(t["id"] == 77 for t in parsed)

    def test_board_payloads_log_json_contains_move_data(self) -> None:
        from cli_board_fixtures import (  # type: ignore[import-not-found]
            board_move,
            board_payloads,
            board_task,
        )

        task = board_task(task_id=1, status="in-progress")
        move = board_move(task_id=1, from_status="todo", to_status="in-progress")
        _, log_json = board_payloads(tasks=[task], moves=[move])
        parsed = json.loads(log_json)
        assert len(parsed) == 1

    def test_board_payloads_empty_tasks_produces_empty_list_json(self) -> None:
        from cli_board_fixtures import board_payloads  # type: ignore[import-not-found]

        list_json, _ = board_payloads(tasks=[], moves=[])
        assert json.loads(list_json) == []

    def test_board_payloads_empty_moves_produces_empty_log_json(self) -> None:
        from cli_board_fixtures import board_payloads, board_task  # type: ignore[import-not-found]

        task = board_task(task_id=1, status="in-progress")
        _, log_json = board_payloads(tasks=[task], moves=[])
        assert json.loads(log_json) == []

    def test_board_payloads_multiple_tasks_all_appear_in_list_json(self) -> None:
        from cli_board_fixtures import board_payloads, board_task  # type: ignore[import-not-found]

        tasks = [board_task(task_id=i, status="todo") for i in range(1, 4)]
        list_json, _ = board_payloads(tasks=tasks, moves=[])
        parsed = json.loads(list_json)
        ids = [t["id"] for t in parsed]
        assert 1 in ids
        assert 2 in ids
        assert 3 in ids

    def test_board_payloads_multiple_moves_all_appear_in_log_json(self) -> None:
        from cli_board_fixtures import (  # type: ignore[import-not-found]
            board_move,
            board_payloads,
            board_task,
        )

        task = board_task(task_id=5, status="in-progress")
        moves = [
            board_move(task_id=5, from_status="backlog", to_status="todo"),
            board_move(task_id=5, from_status="todo", to_status="in-progress"),
        ]
        _, log_json = board_payloads(tasks=[task], moves=moves)
        parsed = json.loads(log_json)
        assert len(parsed) == 2


# ---------------------------------------------------------------------------
# AC #2 — Assignee-precedence fixture cases
# ---------------------------------------------------------------------------


class TestFromAC_AssigneePrecedenceFixtures:
    """AC #2: assignee-precedence fixtures that exercise all three display paths."""

    def test_board_task_both_assignee_and_claimed_by_encoded(self) -> None:
        """Fixture for CLI test: assignee takes priority over claimed_by when both present."""
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task(assignee="alice", claimed_by="bot-worker")
        assert t.get("assignee") == "alice"
        assert t.get("claimed_by") == "bot-worker"

    def test_board_task_claimed_by_only_has_no_assignee_key(self) -> None:
        """Fixture for CLI test: claimed_by shown when no assignee field present."""
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task(claimed_by="bot-worker")
        assert "assignee" not in t
        assert t.get("claimed_by") == "bot-worker"

    def test_board_task_neither_field_produces_no_assignee_or_claimed_by_keys(self) -> None:
        """Fixture for CLI test: neither field present → board shows placeholder."""
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        t = board_task()
        assert "assignee" not in t
        assert "claimed_by" not in t

    def test_board_payloads_preserves_assignee_in_list_json(self) -> None:
        """board_payloads round-trips assignee field through JSON serialization."""
        from cli_board_fixtures import board_payloads, board_task  # type: ignore[import-not-found]

        task = board_task(task_id=20, assignee="carol")
        list_json, _ = board_payloads(tasks=[task], moves=[])
        parsed = json.loads(list_json)
        assert parsed[0].get("assignee") == "carol"

    def test_board_payloads_preserves_claimed_by_in_list_json(self) -> None:
        """board_payloads round-trips claimed_by field through JSON serialization."""
        from cli_board_fixtures import board_payloads, board_task  # type: ignore[import-not-found]

        task = board_task(task_id=21, claimed_by="builder-agent")
        list_json, _ = board_payloads(tasks=[task], moves=[])
        parsed = json.loads(list_json)
        assert parsed[0].get("claimed_by") == "builder-agent"


# ---------------------------------------------------------------------------
# AC #2 — Latest-move-age fixture cases (including created fallback and
#          wrong-destination-ignore)
# ---------------------------------------------------------------------------


class TestFromAC_MoveAgeFixtures:
    """AC #2: age-fixture cases — latest-move, created-fallback, wrong-destination-ignore."""

    def test_move_to_matching_status_encoded_in_log_json(self) -> None:
        """A move whose destination matches task status appears in log JSON."""
        from cli_board_fixtures import (  # type: ignore[import-not-found]
            board_move,
            board_payloads,
            board_task,
        )

        today = datetime.datetime.now(tz=datetime.UTC).date()
        move_date = today - datetime.timedelta(days=12)
        created_date = today - datetime.timedelta(days=41)
        task = board_task(
            task_id=30,
            status="in-progress",
            created=f"{created_date.isoformat()}T10:00:00+01:00",
        )
        move = board_move(
            task_id=30,
            from_status="todo",
            to_status="in-progress",
            timestamp=f"{move_date.isoformat()}T10:00:00+01:00",
        )
        list_json, log_json = board_payloads(tasks=[task], moves=[move])
        task_data = json.loads(list_json)
        log_data = json.loads(log_json)
        # Task is at "in-progress"
        assert task_data[0]["status"] == "in-progress"
        # Move destination matches "in-progress" so CLI will pick it up
        assert "in-progress" in log_data[0]["detail"]

    def test_created_fallback_fixture_has_empty_log_json(self) -> None:
        """When no moves are provided, log JSON is empty → CLI falls back to created."""
        from cli_board_fixtures import board_payloads, board_task  # type: ignore[import-not-found]

        today = datetime.datetime.now(tz=datetime.UTC).date()
        created_date = today - datetime.timedelta(days=27)
        task = board_task(
            task_id=31,
            status="in-progress",
            created=f"{created_date.isoformat()}T10:00:00+01:00",
        )
        list_json, log_json = board_payloads(tasks=[task], moves=[])
        assert json.loads(log_json) == []
        task_data = json.loads(list_json)
        # created timestamp is preserved for the CLI fallback to read
        assert task_data[0]["created"] == f"{created_date.isoformat()}T10:00:00+01:00"

    def test_wrong_destination_move_detail_does_not_match_task_status(self) -> None:
        """A move to a different destination is encoded but its detail doesn't match task status."""
        from cli_board_fixtures import (  # type: ignore[import-not-found]
            board_move,
            board_payloads,
            board_task,
        )

        today = datetime.datetime.now(tz=datetime.UTC).date()
        wrong_move_date = today - datetime.timedelta(days=16)
        created_date = today - datetime.timedelta(days=29)
        task = board_task(
            task_id=32,
            status="review",
            created=f"{created_date.isoformat()}T10:00:00+01:00",
        )
        # Move goes to "in-progress", NOT the task's current status "review"
        wrong_move = board_move(
            task_id=32,
            from_status="todo",
            to_status="in-progress",
            timestamp=f"{wrong_move_date.isoformat()}T10:00:00+01:00",
        )
        list_json, log_json = board_payloads(tasks=[task], moves=[wrong_move])
        task_data = json.loads(list_json)
        log_data = json.loads(log_json)
        # Task status is "review"
        assert task_data[0]["status"] == "review"
        # Move destination is "in-progress" — will not match "review" in CLI
        assert "in-progress" in log_data[0]["detail"]
        assert "review" not in log_data[0]["detail"]

    def test_latest_move_fixture_all_moves_encoded_in_log_json(self) -> None:
        """Multiple moves are all encoded in log JSON so CLI can pick the latest."""
        from cli_board_fixtures import (  # type: ignore[import-not-found]
            board_move,
            board_payloads,
            board_task,
        )

        today = datetime.datetime.now(tz=datetime.UTC).date()
        early_date = today - datetime.timedelta(days=21)
        late_date = today - datetime.timedelta(days=11)
        task = board_task(task_id=33, status="in-progress")
        move_early = board_move(
            task_id=33,
            from_status="backlog",
            to_status="in-progress",
            timestamp=f"{early_date.isoformat()}T10:00:00+01:00",
        )
        move_late = board_move(
            task_id=33,
            from_status="todo",
            to_status="in-progress",
            timestamp=f"{late_date.isoformat()}T10:00:00+01:00",
        )
        _, log_json = board_payloads(tasks=[task], moves=[move_early, move_late])
        log_data = json.loads(log_json)
        # Both moves appear; CLI picks the latest (by timestamp)
        assert len(log_data) == 2

    def test_wrong_destination_ignored_created_timestamp_preserved(self) -> None:
        """created timestamp in list JSON is intact when wrong-destination move in log."""
        from cli_board_fixtures import (  # type: ignore[import-not-found]
            board_move,
            board_payloads,
            board_task,
        )

        today = datetime.datetime.now(tz=datetime.UTC).date()
        created_date = today - datetime.timedelta(days=29)
        wrong_move_date = today - datetime.timedelta(days=16)
        task = board_task(
            task_id=34,
            status="review",
            created=f"{created_date.isoformat()}T10:00:00+01:00",
        )
        wrong_move = board_move(
            task_id=34,
            from_status="todo",
            to_status="in-progress",
            timestamp=f"{wrong_move_date.isoformat()}T10:00:00+01:00",
        )
        list_json, _ = board_payloads(tasks=[task], moves=[wrong_move])
        task_data = json.loads(list_json)
        # created is still present for CLI fallback to read after ignoring wrong-destination move
        assert task_data[0]["created"] == f"{created_date.isoformat()}T10:00:00+01:00"
