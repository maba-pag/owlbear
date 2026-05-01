"""Failing tests for #1180: Test decisions.py create_dr + resolve_pending_drs.

AC coverage:
  ac1-frontmatter  — create_dr writes pending file with 5-field YAML frontmatter
  ac1-body         — create_dr places markdown body after frontmatter delimiter
  ac2-collision    — create_dr O_EXCL collision retries with counter suffix (-2.md)
  ac3-block        — create_dr blocks the task via engine.edit_task
  ac4-rollback     — create_dr deletes file if engine.edit_task raises (rollback)
  ac5-skip-pending — resolve_pending_drs skips response=pending files
  ac6-approved     — approved DRs → body appended, task unblocked, file in resolved/
  ac6-rejected     — rejected DRs → body appended, task unblocked, file in resolved/
  ac7-needs-info-move  — needs-info DRs → file in resolved/, task stays blocked
  ac7-needs-info-body  — needs-info DRs → DR summary appended to task body
  ac8-unknown      — unknown response value → warning logged, file not moved
  ac9-fail-safe    — per-file exception caught; remaining files still processed
  ac10-unknown-keys — reader ignores unknown frontmatter keys (forward-compatible)

All tests FAIL (RED phase) — owlbear_kanban.decisions module does not exist yet.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.decisions import create_dr, resolve_pending_drs

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_decisions_dir(tmp_path: Path) -> Path:
    """Create a decisions directory with pending/ and resolved/ subdirectories."""
    decisions_dir = tmp_path / "decisions"
    (decisions_dir / "pending").mkdir(parents=True)
    (decisions_dir / "resolved").mkdir(parents=True)
    return decisions_dir


def _write_dr(
    pending_dir: Path,
    filename: str,
    response: str,
    task_id: int = 42,
    **extra: object,
) -> Path:
    """Write a minimal DR file into *pending_dir* with given frontmatter values."""
    extra_lines = ""
    for k, v in extra.items():
        if isinstance(v, int):
            extra_lines += f"{k}: {v}\n"
        else:
            extra_lines += f"{k}: '{v}'\n"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: approach-selection\n"
        "created: '2026-04-30'\n"
        f"response: {response}\n"
        f"{extra_lines}"
        "---\n\n## Question\nTest body.\n"
    )
    path = pending_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def _parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a DR file."""
    from ruamel.yaml import YAML

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    close_idx = next(i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---")
    frontmatter_text = "\n".join(lines[1:close_idx])
    return YAML(typ="safe").load(frontmatter_text) or {}


def _mock_engine() -> MagicMock:
    """Return a MagicMock with spec=KanbanEngine."""
    return MagicMock(spec=KanbanEngine)


# ---------------------------------------------------------------------------
# AC1-AC4: create_dr
# ---------------------------------------------------------------------------


class TestFromAC_CreateDr:
    """Tests for create_dr() mapped to AC lines 1-4."""

    def test_creates_pending_file_with_five_field_frontmatter(self, tmp_path: Path) -> None:
        """AC1 happy: file written in pending/ with exactly the 5 required frontmatter fields."""
        decisions_dir = _make_decisions_dir(tmp_path)
        engine = _mock_engine()

        result_path = create_dr(
            decisions_dir,
            engine,
            task_id=42,
            agent="builder",
            request_type="approach-selection",
            body="## Context\nNeed a decision.",
        )

        assert result_path.exists(), "DR file must exist after create_dr"
        assert result_path.parent == decisions_dir / "pending", "File must be written in pending/"
        fm = _parse_frontmatter(result_path)
        assert fm["task_id"] == 42
        assert fm["agent"] == "builder"
        assert fm["request_type"] == "approach-selection"
        assert re.match(r"\d{4}-\d{2}-\d{2}$", str(fm["created"])), (
            f"created field must be in YYYY-MM-DD format; got {fm.get('created')!r}"
        )
        assert fm["response"] == "pending"

    def test_pending_file_body_appears_after_frontmatter(self, tmp_path: Path) -> None:
        """AC1 boundary: markdown body appears after the closing --- delimiter."""
        decisions_dir = _make_decisions_dir(tmp_path)
        engine = _mock_engine()
        body_text = "## Question\nWhich approach is correct?"

        result_path = create_dr(
            decisions_dir,
            engine,
            task_id=7,
            agent="reviewer",
            request_type="information-request",
            body=body_text,
        )

        content = result_path.read_text(encoding="utf-8")
        # Body must appear after the second --- delimiter
        parts = content.split("---", 2)
        assert len(parts) >= 3, "File must contain at least two --- delimiters"
        assert body_text in parts[2], "Body must appear after the closing frontmatter delimiter"

    def test_collision_retries_with_counter_suffix(self, tmp_path: Path) -> None:
        """AC2 edge: when slug file already exists, create_dr uses a counter suffix (-2.md)."""
        decisions_dir = _make_decisions_dir(tmp_path)
        engine = _mock_engine()

        first_path = create_dr(
            decisions_dir,
            engine,
            task_id=10,
            agent="builder",
            request_type="approach-selection",
            body="First DR",
        )
        assert first_path.exists()

        # Second call with same parameters must create a distinct file
        second_path = create_dr(
            decisions_dir,
            engine,
            task_id=10,
            agent="builder",
            request_type="approach-selection",
            body="Second DR",
        )

        assert second_path.exists(), "Second DR file must be created"
        assert second_path != first_path, "Collision must produce a different path"
        assert first_path.exists(), "Original file must not be overwritten"
        assert "approach-selection" in first_path.stem, (
            f"Slug must be derived from request_type 'approach-selection'; got stem {first_path.stem!r}"
        )
        assert second_path.stem.endswith("-2"), (
            f"Counter suffix must be '-2', got stem {second_path.stem!r}"
        )

    def test_blocks_task_via_edit_task(self, tmp_path: Path) -> None:
        """AC3 smoke: create_dr calls engine.edit_task(blocked=True, block_reason='DR pending')."""
        decisions_dir = _make_decisions_dir(tmp_path)
        engine = _mock_engine()

        create_dr(
            decisions_dir,
            engine,
            task_id=99,
            agent="builder",
            request_type="approach-selection",
            body="",
        )

        blocking_calls = [
            c
            for c in engine.edit_task.call_args_list
            if c.kwargs.get("blocked") is True
            and c.kwargs.get("block_reason") == "DR pending"
        ]
        assert blocking_calls, (
            "create_dr must call engine.edit_task(blocked=True, block_reason='DR pending'); "
            f"actual calls: {engine.edit_task.call_args_list}"
        )

    def test_file_deleted_if_engine_blocking_fails(self, tmp_path: Path) -> None:
        """AC4 error: DR file is deleted (rolled back) when engine.edit_task raises."""
        decisions_dir = _make_decisions_dir(tmp_path)
        engine = _mock_engine()
        engine.edit_task.side_effect = RuntimeError("engine unavailable")

        with pytest.raises(RuntimeError):
            create_dr(
                decisions_dir,
                engine,
                task_id=55,
                agent="builder",
                request_type="approach-selection",
                body="",
            )

        leftover = list((decisions_dir / "pending").iterdir())
        assert leftover == [], (
            f"Rollback failed — orphaned DR file(s) remain in pending/: "
            f"{[p.name for p in leftover]}"
        )

    def test_frontmatter_key_set_is_exactly_five_fields(self, tmp_path: Path) -> None:
        """AC1 boundary: pending file contains EXACTLY the 5-field schema — no more, no fewer."""
        decisions_dir = _make_decisions_dir(tmp_path)
        engine = _mock_engine()

        result_path = create_dr(
            decisions_dir,
            engine,
            task_id=42,
            agent="builder",
            request_type="approach-selection",
            body="## Context",
        )

        fm = _parse_frontmatter(result_path)
        expected_keys = {"task_id", "agent", "request_type", "created", "response"}
        assert set(fm.keys()) == expected_keys, (
            f"Frontmatter must have exactly {expected_keys!r}; "
            f"got {set(fm.keys())!r}"
        )

    def test_exclusive_create_uses_o_excl_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC2 boundary: create_dr uses O_CREAT|O_EXCL for atomic file creation (not exists-then-write)."""
        import os as os_mod

        real_open = os_mod.open
        observed_flags: list[int] = []

        def spy_open(path: object, flags: int, mode: int = 0o777) -> int:
            observed_flags.append(flags)
            return real_open(path, flags, mode)  # type: ignore[arg-type]

        monkeypatch.setattr("owlbear_kanban.decisions.os.open", spy_open)

        decisions_dir = _make_decisions_dir(tmp_path)
        engine = _mock_engine()

        create_dr(
            decisions_dir,
            engine,
            task_id=42,
            agent="builder",
            request_type="approach-selection",
            body="",
        )

        assert observed_flags, "os.open must be called at least once by create_dr"
        flags = observed_flags[0]
        assert flags & os_mod.O_CREAT, "O_CREAT must be set in os.open call"
        assert flags & os_mod.O_EXCL, (
            "O_EXCL must be set — atomic exclusive-create required (not exists-then-write)"
        )


# ---------------------------------------------------------------------------
# AC5-AC9: resolve_pending_drs
# ---------------------------------------------------------------------------


class TestFromAC_ResolvePendingDrs:
    """Tests for resolve_pending_drs() mapped to AC lines 5-9."""

    def test_skips_files_with_pending_response(self, tmp_path: Path) -> None:
        """AC5 smoke: files with response=pending are left untouched in pending/."""
        decisions_dir = _make_decisions_dir(tmp_path)
        dr_file = _write_dr(
            decisions_dir / "pending",
            "42-question.md",
            response="pending",
            task_id=42,
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        assert dr_file.exists(), "Pending DR must not be moved or deleted"
        assert not (decisions_dir / "resolved" / "42-question.md").exists()
        assert not engine.edit_task.called, (
            "engine.edit_task must not be called for response=pending DRs"
        )

    @pytest.mark.parametrize("response", ["approved", "rejected"])
    def test_approved_or_rejected_unblocks_and_moves_to_resolved(
        self, tmp_path: Path, response: str
    ) -> None:
        """AC6 happy: approved/rejected → body appended, task unblocked, file in resolved/."""
        decisions_dir = _make_decisions_dir(tmp_path)
        _write_dr(
            decisions_dir / "pending",
            "42-question.md",
            response=response,
            task_id=42,
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        # File must move to resolved/
        assert (decisions_dir / "resolved" / "42-question.md").exists(), (
            f"DR file must be in resolved/ after response={response!r}"
        )
        assert not (decisions_dir / "pending" / "42-question.md").exists(), (
            "DR file must be removed from pending/"
        )
        # Task must be unblocked
        unblock_calls = [
            c for c in engine.edit_task.call_args_list if c.kwargs.get("blocked") is False
        ]
        assert unblock_calls, (
            f"engine.edit_task(blocked=False) must be called for response={response!r}; "
            f"actual calls: {engine.edit_task.call_args_list}"
        )

    @pytest.mark.parametrize("response", ["approved", "rejected"])
    def test_approved_or_rejected_appends_dr_summary(
        self, tmp_path: Path, response: str
    ) -> None:
        """AC6 edge: approved/rejected → DR summary appended to task body before unblock."""
        decisions_dir = _make_decisions_dir(tmp_path)
        _write_dr(
            decisions_dir / "pending",
            "42-question.md",
            response=response,
            task_id=42,
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        append_calls = [
            c for c in engine.edit_task.call_args_list if c.kwargs.get("append_body") is not None
        ]
        assert append_calls, (
            f"engine.edit_task must be called with append_body for response={response!r}; "
            f"actual calls: {engine.edit_task.call_args_list}"
        )
        payload = append_calls[0].kwargs["append_body"]
        assert isinstance(payload, str), (
            f"append_body payload must be a string; got {type(payload)!r}"
        )
        assert len(payload.strip()) > 0, (
            f"append_body payload must be non-empty; got {payload!r}"
        )
        assert response in payload, (
            f"append_body payload must contain the response value {response!r}; got {payload!r}"
        )

    def test_needs_info_moves_file_but_keeps_task_blocked(self, tmp_path: Path) -> None:
        """AC7 happy: needs-info → file in resolved/, task NOT unblocked."""
        decisions_dir = _make_decisions_dir(tmp_path)
        _write_dr(
            decisions_dir / "pending",
            "42-question.md",
            response="needs-info",
            task_id=42,
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        # File must move to resolved/
        assert (decisions_dir / "resolved" / "42-question.md").exists(), (
            "DR file must be in resolved/ after needs-info"
        )
        assert not (decisions_dir / "pending" / "42-question.md").exists()
        # Task must NOT be unblocked
        unblock_calls = [
            c for c in engine.edit_task.call_args_list if c.kwargs.get("blocked") is False
        ]
        assert not unblock_calls, (
            "needs-info must NOT call engine.edit_task(blocked=False); "
            f"found unexpected unblock calls: {unblock_calls}"
        )

    def test_needs_info_appends_summary_to_task_body(self, tmp_path: Path) -> None:
        """AC7 edge: needs-info → DR summary appended to task body via engine."""
        decisions_dir = _make_decisions_dir(tmp_path)
        _write_dr(
            decisions_dir / "pending",
            "99-clarify.md",
            response="needs-info",
            task_id=99,
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        append_calls = [
            c for c in engine.edit_task.call_args_list if c.kwargs.get("append_body") is not None
        ]
        assert append_calls, (
            "engine.edit_task must be called with append_body for needs-info; "
            f"actual calls: {engine.edit_task.call_args_list}"
        )

    def test_needs_info_append_body_payload_is_meaningful(self, tmp_path: Path) -> None:
        """AC7 boundary: needs-info append_body payload is a real summary, not a stub string."""
        decisions_dir = _make_decisions_dir(tmp_path)
        _write_dr(
            decisions_dir / "pending",
            "77-clarify.md",
            response="needs-info",
            task_id=77,
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        append_calls = [
            c for c in engine.edit_task.call_args_list if c.kwargs.get("append_body") is not None
        ]
        assert append_calls, "engine.edit_task(append_body=...) must be called for needs-info"
        payload: str = append_calls[0].kwargs["append_body"]
        assert "needs-info" in payload, (
            f"append_body must include the response value 'needs-info'; got {payload!r}"
        )
        is_structured = "Decision Request" in payload or len(payload.strip().splitlines()) > 1
        assert is_structured, (
            f"append_body must contain a structured summary (not a one-word stub); got {payload!r}"
        )

    def test_unknown_response_logs_warning_and_skips(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC8 smoke: unknown response value → warning logged, file remains in pending/."""
        decisions_dir = _make_decisions_dir(tmp_path)
        dr_file = _write_dr(
            decisions_dir / "pending",
            "42-question.md",
            response="wibble",
            task_id=42,
        )
        engine = _mock_engine()

        with caplog.at_level(logging.WARNING):
            resolve_pending_drs(decisions_dir, engine)

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert any(
            "wibble" in r.message or "unknown" in r.message.lower()
            for r in warning_records
        ), (
            f"Expected warning about unknown response value 'wibble'; "
            f"log records: {[(r.levelname, r.message) for r in warning_records]}"
        )
        # File must remain untouched in pending/
        assert dr_file.exists(), "File with unknown response must remain in pending/"
        assert not (decisions_dir / "resolved" / "42-question.md").exists()

    def test_unknown_response_does_not_mutate_task_state(
        self, tmp_path: Path
    ) -> None:
        """AC8 edge: unknown response must NOT call engine.edit_task (task state untouched)."""
        decisions_dir = _make_decisions_dir(tmp_path)
        _write_dr(
            decisions_dir / "pending",
            "42-unknown.md",
            response="invalid-status",
            task_id=42,
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        assert not engine.edit_task.called, (
            "engine.edit_task must NOT be called for unknown response values; "
            f"actual calls: {engine.edit_task.call_args_list}"
        )

    def test_per_file_exception_does_not_stall_other_files(self, tmp_path: Path) -> None:
        """AC9 error: exception from one DR is caught; remaining DRs are still processed."""
        decisions_dir = _make_decisions_dir(tmp_path)
        # File A: task 10 — engine.edit_task raises for this task
        _write_dr(
            decisions_dir / "pending",
            "10-will-fail.md",
            response="approved",
            task_id=10,
        )
        # File B: task 20 — must be processed successfully
        _write_dr(
            decisions_dir / "pending",
            "20-will-succeed.md",
            response="approved",
            task_id=20,
        )
        engine = _mock_engine()

        def _edit_side_effect(*args: object, **kwargs: object) -> MagicMock:
            tid = args[0] if args else kwargs.get("task_id")
            if str(tid) == "10":
                msg = "engine failure for task 10"
                raise RuntimeError(msg)
            return MagicMock()

        engine.edit_task.side_effect = _edit_side_effect

        # Must not raise even though task 10 fails
        resolve_pending_drs(decisions_dir, engine)

        # File B must be moved to resolved/ — fail-safe preserved processing
        assert (decisions_dir / "resolved" / "20-will-succeed.md").exists(), (
            "File B must be processed even when File A raises an exception"
        )


# ---------------------------------------------------------------------------
# AC10: DR reader — forward-compatibility with unknown frontmatter keys
# ---------------------------------------------------------------------------


class TestFromAC_DrReader:
    """Tests for DR file parsing — AC line 10 (forward-compatibility)."""

    def test_reader_ignores_unknown_frontmatter_keys(self, tmp_path: Path) -> None:
        """AC10 smoke: DR files with extra frontmatter keys are parsed without error."""
        decisions_dir = _make_decisions_dir(tmp_path)
        _write_dr(
            decisions_dir / "pending",
            "42-future-compat.md",
            response="approved",
            task_id=42,
            # Extra keys not in the 5-field spec — forward-compat with old scribe DR files
            urgency="blocking",
            decision_type="approach-selection",
            impact_tier=2,
        )
        engine = _mock_engine()

        # resolve_pending_drs must process the file without raising on extra keys
        resolve_pending_drs(decisions_dir, engine)

        # File must be processed (moved to resolved/) — proves reader didn't choke on extra keys
        assert (decisions_dir / "resolved" / "42-future-compat.md").exists(), (
            "DR file with extra frontmatter keys must be processed without error"
        )
