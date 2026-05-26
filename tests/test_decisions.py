from __future__ import annotations

# --- merged from tests/test_decisions_1180.py ---
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


import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.decisions import resolve_pending_drs

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
        assert not engine.edit_task.called, "engine.edit_task must not be called for response=pending DRs"

    @pytest.mark.parametrize("response", ["approved", "rejected"])
    def test_approved_or_rejected_unblocks_and_moves_to_resolved(self, tmp_path: Path, response: str) -> None:
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
        assert not (decisions_dir / "pending" / "42-question.md").exists(), "DR file must be removed from pending/"
        # Task must be unblocked
        unblock_calls = [c for c in engine.edit_task.call_args_list if c.kwargs.get("blocked") is False]
        assert unblock_calls, (
            f"engine.edit_task(blocked=False) must be called for response={response!r}; "
            f"actual calls: {engine.edit_task.call_args_list}"
        )

    @pytest.mark.parametrize("response", ["approved", "rejected"])
    def test_approved_or_rejected_appends_dr_summary(self, tmp_path: Path, response: str) -> None:
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

        append_calls = [c for c in engine.edit_task.call_args_list if c.kwargs.get("append_body") is not None]
        assert append_calls, (
            f"engine.edit_task must be called with append_body for response={response!r}; "
            f"actual calls: {engine.edit_task.call_args_list}"
        )
        payload = append_calls[0].kwargs["append_body"]
        assert isinstance(payload, str), f"append_body payload must be a string; got {type(payload)!r}"
        assert len(payload.strip()) > 0, f"append_body payload must be non-empty; got {payload!r}"
        assert response in payload, f"append_body payload must contain the response value {response!r}; got {payload!r}"

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
        assert (decisions_dir / "resolved" / "42-question.md").exists(), "DR file must be in resolved/ after needs-info"
        assert not (decisions_dir / "pending" / "42-question.md").exists()
        # Task must NOT be unblocked
        unblock_calls = [c for c in engine.edit_task.call_args_list if c.kwargs.get("blocked") is False]
        assert not unblock_calls, (
            f"needs-info must NOT call engine.edit_task(blocked=False); found unexpected unblock calls: {unblock_calls}"
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

        append_calls = [c for c in engine.edit_task.call_args_list if c.kwargs.get("append_body") is not None]
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

        append_calls = [c for c in engine.edit_task.call_args_list if c.kwargs.get("append_body") is not None]
        assert append_calls, "engine.edit_task(append_body=...) must be called for needs-info"
        payload: str = append_calls[0].kwargs["append_body"]
        assert "needs-info" in payload, f"append_body must include the response value 'needs-info'; got {payload!r}"
        is_structured = "Decision Request" in payload or len(payload.strip().splitlines()) > 1
        assert is_structured, f"append_body must contain a structured summary (not a one-word stub); got {payload!r}"

    def test_unknown_response_logs_warning_and_skips(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
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
        assert any("wibble" in r.message or "unknown" in r.message.lower() for r in warning_records), (
            f"Expected warning about unknown response value 'wibble'; "
            f"log records: {[(r.levelname, r.message) for r in warning_records]}"
        )
        # File must remain untouched in pending/
        assert dr_file.exists(), "File with unknown response must remain in pending/"
        assert not (decisions_dir / "resolved" / "42-question.md").exists()

    def test_unknown_response_does_not_mutate_task_state(self, tmp_path: Path) -> None:
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


# --- merged from tests/test_decisions_1181.py ---
"""Failing tests for #1181: decisions.py module — P1-02 AC coverage.

AC coverage:
  ac2-create-dr     — create_dr(decisions_dir, engine, *, task_id, agent, request_type, body) → Path
  ac3-dual-form     — resolve_pending_drs dual call-form: resolve_pending_drs(engine) (engine-only)
  ac4-frontmatter   — 5-field frontmatter (task_id, agent, request_type, created YYYY-MM-DD, response)
  ac5-slug          — slug generated from request_type field
  ac6-atomic        — atomic O_EXCL creation with -2, -3, … collision suffix retry
  ac7-rollback      — file deleted if engine.edit_task(blocked=True) raises; exception re-raised
  ac8-resolve-happy — approved DR: append_body + unblock + move to resolved/  (td:2 happy)
  ac8-resolve-edge  — needs-info DR: append_body + move, NO unblock               (td:2 edge)
  ac8-resolve-error — unblock call raises → pending file stays in pending/         (td:2 error)
  ac8-resolve-bound — rejected DR: same full flow as approved                      (td:2 boundary)
  ac9-error-isolate — per-file exception does not stall remaining DRs in the loop
  ac10-unknown      — unknown response value → warning logged, file not moved

All tests FAIL (RED phase) when decisions.py does not exist; implementation already present
from pre-built work, so tests serve as the authoritative contract spec for #1181.
"""


import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban.decisions import resolve_pending_drs

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (decisions_dir, pending_dir, resolved_dir) — all directories created."""
    decisions_dir = tmp_path / "decisions"
    pending_dir = decisions_dir / "pending"
    resolved_dir = decisions_dir / "resolved"
    pending_dir.mkdir(parents=True)
    resolved_dir.mkdir(parents=True)
    return decisions_dir, pending_dir, resolved_dir


# ---------------------------------------------------------------------------
# AC3, AC8, AC9, AC10 — resolve_pending_drs
# ---------------------------------------------------------------------------


class TestFromAC_ResolvePendingDrs_1181:
    """Tests for resolve_pending_drs() — AC lines 3 (dual form), 8 (td:2), 9, 10."""

    # --- AC3: dual call-form (engine-only) — PRIMARY GAP not in #1180/#1195 ---

    def test_ac3_engine_only_form_resolves_from_kanban_dir(self, tmp_path: Path) -> None:
        """AC3 smoke: resolve_pending_drs(engine) infers decisions_dir from engine._kanban_dir."""
        kanban_dir = tmp_path / "kanban"
        decisions_dir = kanban_dir / "decisions"
        pending_dir = decisions_dir / "pending"
        resolved_dir = decisions_dir / "resolved"
        pending_dir.mkdir(parents=True)
        resolved_dir.mkdir(parents=True)

        dr_file = pending_dir / "42-approach-selection.md"
        dr_file.write_text(
            "---\n"
            "task_id: 42\n"
            "agent: builder\n"
            "request_type: approach-selection\n"
            "created: '2026-04-30'\n"
            "response: approved\n"
            "---\n\n## Body\nDecision needed.\n",
            encoding="utf-8",
        )

        engine = _mock_engine()
        engine._kanban_dir = kanban_dir

        result = resolve_pending_drs(engine)  # single-argument (engine-only) form

        assert isinstance(result, list), f"resolve_pending_drs must return a list; got {type(result)!r}"
        assert len(result) == 1, f"Engine-only form must process DRs from engine._kanban_dir/decisions/; got {result}"
        assert not dr_file.exists(), "Resolved DR must be removed from pending/"
        assert (resolved_dir / "42-approach-selection.md").exists(), (
            "Resolved DR must appear in decisions_dir/resolved/"
        )

    # --- AC8 (td:2): resolve logic — happy, edge, error, boundary ---

    def test_ac8_happy_approved_appends_unblocks_and_moves(self, tmp_path: Path) -> None:
        """AC8 happy: approved DR → append_body called, unblock called, file in resolved/."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        _write_dr(pending_dir, "42-approach-selection.md", response="approved", task_id=42)
        engine = _mock_engine()

        result = resolve_pending_drs(decisions_dir, engine)

        # append_body must have been called for task 42
        append_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0 and c.args[0] == 42 and c.kwargs.get("append_body") is not None
        ]
        assert append_calls, (
            f"approved DR must trigger engine.edit_task(42, append_body=...) — "
            f"actual calls: {engine.edit_task.call_args_list}"
        )

        # unblock must have been called for task 42
        unblock_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0 and c.args[0] == 42 and c.kwargs.get("blocked") is False
        ]
        assert unblock_calls, (
            f"approved DR must trigger engine.edit_task(42, blocked=False) — "
            f"actual calls: {engine.edit_task.call_args_list}"
        )

        # file must move to resolved/
        assert (resolved_dir / "42-approach-selection.md").exists(), "Approved DR must be moved to resolved/"
        assert not (pending_dir / "42-approach-selection.md").exists(), "Approved DR must be removed from pending/"
        assert len(result) == 1, f"One DR moved; got {result}"

    def test_ac8_edge_needs_info_appends_and_moves_without_unblock(self, tmp_path: Path) -> None:
        """AC8 edge: needs-info DR → append_body called, file moved, NO unblock."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        _write_dr(pending_dir, "55-approach-selection.md", response="needs-info", task_id=55)
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        # append_body must be called
        append_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0 and c.args[0] == 55 and c.kwargs.get("append_body") is not None
        ]
        assert append_calls, (
            f"needs-info DR must trigger engine.edit_task(55, append_body=...) — "
            f"actual calls: {engine.edit_task.call_args_list}"
        )

        # unblock must NOT be called
        unblock_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0 and c.args[0] == 55 and c.kwargs.get("blocked") is False
        ]
        assert not unblock_calls, (
            f"needs-info must NOT call engine.edit_task(55, blocked=False) — found unexpected unblock: {unblock_calls}"
        )

        # file must still move to resolved/
        assert (resolved_dir / "55-approach-selection.md").exists(), (
            "needs-info DR must be moved to resolved/ even though task stays blocked"
        )

    def test_ac8_error_engine_raises_during_unblock_file_stays_pending(self, tmp_path: Path) -> None:
        """AC8 error: if engine raises during unblock, DR file stays in pending/ (not half-moved)."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        dr_file = _write_dr(pending_dir, "77-approach-selection.md", response="approved", task_id=77)
        engine = _mock_engine()

        def _fail_on_unblock(*_args: object, **kwargs: object) -> MagicMock:
            if kwargs.get("blocked") is False:
                msg = "unblock failed"
                raise RuntimeError(msg)
            return MagicMock()

        engine.edit_task.side_effect = _fail_on_unblock

        # Must not propagate the exception — per-file isolation catches it
        resolve_pending_drs(decisions_dir, engine)

        # DR must remain in pending/ — it was never successfully moved
        assert dr_file.exists(), "DR file must stay in pending/ when engine.edit_task raises during unblock"
        assert not (resolved_dir / "77-approach-selection.md").exists(), (
            "DR file must NOT appear in resolved/ when unblock failed"
        )

    def test_ac8_boundary_rejected_full_flow_matches_approved(self, tmp_path: Path) -> None:
        """AC8 boundary: rejected DR follows the same full flow as approved (append+unblock+move)."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        _write_dr(pending_dir, "88-approach-selection.md", response="rejected", task_id=88)
        engine = _mock_engine()

        result = resolve_pending_drs(decisions_dir, engine)

        unblock_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0 and c.args[0] == 88 and c.kwargs.get("blocked") is False
        ]
        assert unblock_calls, "rejected DR must trigger unblock via engine.edit_task(88, blocked=False)"
        assert (resolved_dir / "88-approach-selection.md").exists(), "rejected DR must be moved to resolved/"
        assert len(result) == 1, f"One DR moved; got {result}"

    # --- AC9: per-file exception isolation ---

    def test_ac9_exception_from_one_dr_does_not_stall_others(self, tmp_path: Path) -> None:
        """AC9 smoke: exception from processing one DR does not prevent others from being resolved."""
        decisions_dir, pending_dir, _ = _make_dirs(tmp_path)
        resolved_dir = decisions_dir / "resolved"

        # File A: task 10 — engine.edit_task will raise for this task ID
        _write_dr(pending_dir, "10-approach-selection.md", response="approved", task_id=10)
        # File B: task 20 — must be processed successfully
        _write_dr(pending_dir, "20-approach-selection.md", response="approved", task_id=20)

        engine = _mock_engine()

        def _raise_for_task_10(*_args: object, **kwargs: object) -> MagicMock:
            task_id = _args[0] if _args else kwargs.get("task_id")
            if str(task_id) == "10":
                msg = "injected failure for task 10"
                raise RuntimeError(msg)
            return MagicMock()

        engine.edit_task.side_effect = _raise_for_task_10

        # Must not raise
        resolve_pending_drs(decisions_dir, engine)

        assert (resolved_dir / "20-approach-selection.md").exists(), (
            "File B must be processed even though File A raised an exception"
        )

    # --- AC10: unknown response → warning, skip ---

    def test_ac10_unknown_response_logs_warning_and_leaves_file_in_pending(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC10 smoke: unknown response value → warning logged, file stays in pending/."""
        decisions_dir, pending_dir, _ = _make_dirs(tmp_path)
        dr_file = _write_dr(pending_dir, "42-approach-selection.md", response="bogus-status")
        engine = _mock_engine()

        with caplog.at_level(logging.WARNING):
            resolve_pending_drs(decisions_dir, engine)

        warning_texts = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("bogus-status" in t or "unknown" in t.lower() for t in warning_texts), (
            f"Expected warning mentioning the unknown response value; got: {warning_texts}"
        )
        assert dr_file.exists(), "File with unknown response must remain in pending/ (not moved)"
        assert not engine.edit_task.called, "engine.edit_task must NOT be called for unknown response values"

    # --- AC8 atomicity: move failure after mutation must not produce duplicate summary ---

    def test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry(self, tmp_path: Path) -> None:
        """AC8 atomicity: if _move_with_collision_suffix fails after _append_summary and unblock,
        retrying resolve_pending_drs must NOT produce a second append_body call.

        Failure mode (current defect): the DR stays in pending after state mutation, so a retry
        will call _append_summary again — producing a duplicate summary in the task body.
        A correct implementation either rolls back the mutation or guards against re-processing.
        """
        decisions_dir, pending_dir, _resolved_dir = _make_dirs(tmp_path)
        _write_dr(pending_dir, "99-approach-selection.md", response="approved", task_id=99)
        engine = _mock_engine()

        target = "owlbear_kanban.decisions._move_with_collision_suffix"
        with patch(target, side_effect=OSError("disk full")):
            resolve_pending_drs(decisions_dir, engine)

        # DR must still be in pending after the failed move
        assert (pending_dir / "99-approach-selection.md").exists(), (
            "DR must remain in pending/ when _move_with_collision_suffix raises"
        )

        # Count append_body calls after the first (failed) attempt
        append_calls_first = [c for c in engine.edit_task.call_args_list if c.kwargs.get("append_body") is not None]

        # Retry: run resolve again with move still failing
        with patch(target, side_effect=OSError("disk full")):
            resolve_pending_drs(decisions_dir, engine)

        append_calls_total = [c for c in engine.edit_task.call_args_list if c.kwargs.get("append_body") is not None]

        assert len(append_calls_total) == len(append_calls_first), (
            "Retrying resolve after a move failure must NOT produce a duplicate append_body call; "
            f"after first attempt: {len(append_calls_first)} call(s), "
            f"after retry: {len(append_calls_total)} call(s) — duplicate detected"
        )

    # --- AC5: rejected path appends summary (retry gap fill) ---

    def test_ac5_rejected_path_appends_summary_to_task(self, tmp_path: Path) -> None:
        """AC5 boundary: rejected DR must append_body to task before unblock and move."""
        decisions_dir, pending_dir, _resolved_dir = _make_dirs(tmp_path)
        _write_dr(pending_dir, "88-approach-selection.md", response="rejected", task_id=88)
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        append_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0 and c.args[0] == 88 and c.kwargs.get("append_body") is not None
        ]
        assert append_calls, (
            f"rejected DR must trigger engine.edit_task(88, append_body=...) — "
            f"actual calls: {engine.edit_task.call_args_list}"
        )
        # Summary must mention the response value
        summary_text = append_calls[0].kwargs["append_body"]
        assert "rejected" in summary_text, f"append_body summary must contain 'rejected'; got: {summary_text!r}"

    # --- AC6: pending removal for needs-info and rejected (retry gap fill) ---

    def test_ac6_needs_info_file_removed_from_pending_after_resolve(self, tmp_path: Path) -> None:
        """AC6: after resolve_pending_drs(), needs-info DR must not remain in pending/."""
        decisions_dir, pending_dir, _resolved_dir = _make_dirs(tmp_path)
        dr_file = _write_dr(pending_dir, "55-approach-selection.md", response="needs-info", task_id=55)
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        assert not dr_file.exists(), "needs-info DR must be removed from pending/ after resolve_pending_drs() runs"

    def test_ac6_rejected_file_removed_from_pending_after_resolve(self, tmp_path: Path) -> None:
        """AC6: after resolve_pending_drs(), rejected DR must not remain in pending/."""
        decisions_dir, pending_dir, _resolved_dir = _make_dirs(tmp_path)
        dr_file = _write_dr(pending_dir, "88-approach-selection.md", response="rejected", task_id=88)
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        assert not dr_file.exists(), "rejected DR must be removed from pending/ after resolve_pending_drs() runs"


# --- merged from tests/test_decisions_1195.py ---
"""Failing tests for #1195: resolve_pending_drs collision protection in resolved/.

AC coverage:
  ac1-happy    — move to resolved/ succeeds without overwrite when basename conflicts
  ac1-edge     — moved path is distinct from pre-existing resolved file
  ac1-boundary — collision-protected path appears in returned list
  ac2          — original resolved file content preserved byte-for-byte after collision
  ac3-happy    — first conflict yields -2.md suffix
  ac3-edge     — two pre-existing conflicts yield -3.md (next-free allocation)
  ac3-boundary — three pre-existing conflicts yield -4.md
  ac4          — collision detection does not overwrite (O_EXCL or equivalent)
  ac5-approved — approved resolution path applies collision protection
  ac5-rejected — rejected resolution path applies collision protection
  ac5-needs-info — needs-info resolution path applies collision protection

All tests FAIL (RED phase) — resolve_pending_drs currently uses path.replace() which
silently overwrites pre-existing resolved/ files; collision protection not yet implemented.
"""


from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.decisions import resolve_pending_drs

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SENTINEL = "ORIGINAL CONTENT MUST NOT CHANGE"


def _write_resolved(resolved_dir: Path, filename: str, content: str = _SENTINEL) -> Path:
    """Write a pre-existing file in resolved/ to simulate a collision."""
    path = resolved_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# AC1 (td:2): Move to resolved/ succeeds without overwrite when basename conflicts
# ---------------------------------------------------------------------------


class TestFromAC_ResolvePendingDrsCollision:
    """Collision-protection tests for resolve_pending_drs(), AC1-AC5."""

    # AC1 — happy path: approved DR with a basename conflict in resolved/
    def test_ac1_happy_approved_move_succeeds_without_overwrite(self, tmp_path: Path) -> None:
        """AC1 happy: approved DR moves even when resolved/ already has a file with the same name."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "42-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved")
        # Pre-existing conflict in resolved/
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        # The DR must be resolved (something must have been moved)
        assert len(result) == 1, f"Expected 1 moved file, got {len(result)}: {result}"
        # The pre-existing resolved file must NOT have been overwritten
        existing_content = (resolved_dir / filename).read_text(encoding="utf-8")
        assert existing_content == _SENTINEL, (
            f"Pre-existing resolved file must be preserved byte-for-byte; got: {existing_content!r}"
        )

    # AC1 — edge: the moved path is distinct from the pre-existing resolved file
    def test_ac1_edge_moved_path_is_distinct_when_conflict_exists(self, tmp_path: Path) -> None:
        """AC1 edge: the path returned for the moved file differs from the original basename."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "99-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=99)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert len(result) == 1
        moved_path = result[0]
        # The moved path must NOT be the exact same name as the pre-existing file
        assert moved_path.name != filename, f"Collision must produce a distinct filename; got {moved_path.name!r}"

    # AC1 — boundary: the collision-protected path appears in the returned list
    def test_ac1_boundary_collision_protected_path_in_returned_list(self, tmp_path: Path) -> None:
        """AC1 boundary: resolve_pending_drs returns the new (suffixed) path, not the original."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "55-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=55)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert result, "Result list must not be empty when a DR is resolved"
        moved_path = result[0]
        assert moved_path.exists(), f"Returned path must exist on disk: {moved_path}"
        assert moved_path.parent == resolved_dir, "Moved path must be inside resolved/"
        assert moved_path.name != filename, (
            "Collision-protected path must differ from pre-existing filename; "
            f"got {moved_path.name!r} which matches the conflict"
        )

    # ---------------------------------------------------------------------------
    # AC2 (td:1): Original resolved file content preserved byte-for-byte
    # ---------------------------------------------------------------------------

    def test_ac2_original_resolved_content_preserved_byte_for_byte(self, tmp_path: Path) -> None:
        """AC2: The pre-existing resolved file retains its exact bytes after a collision."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "10-approach-selection.md"
        original_bytes = b"PRECIOUS ORIGINAL CONTENT\xc3\xa9"  # non-ASCII to catch encoding bugs
        (resolved_dir / filename).write_bytes(original_bytes)
        _write_dr(pending_dir, filename, response="approved", task_id=10)

        resolve_pending_drs(decisions_dir, engine)

        actual_bytes = (resolved_dir / filename).read_bytes()
        assert actual_bytes == original_bytes, (
            "Pre-existing resolved file must be preserved byte-for-byte after collision move; "
            f"expected {original_bytes!r}, got {actual_bytes!r}"
        )

    # ---------------------------------------------------------------------------
    # AC3 (td:2): Counter suffix; next-free allocation
    # ---------------------------------------------------------------------------

    def test_ac3_happy_first_collision_uses_dash_2_suffix(self, tmp_path: Path) -> None:
        """AC3 happy: when resolved/ already has the base name, the moved file gets -2.md."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "7-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=7)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert len(result) == 1
        moved = result[0]
        assert moved.name == "7-approach-selection-2.md", (
            f"First collision must produce '-2.md' suffix; got {moved.name!r}"
        )

    def test_ac3_edge_two_preexisting_conflicts_yield_dash_3_suffix(self, tmp_path: Path) -> None:
        """AC3 edge: when resolved/ has both base and -2 variant, next-free is -3.md."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "20-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=20)
        _write_resolved(resolved_dir, "20-approach-selection.md")
        _write_resolved(resolved_dir, "20-approach-selection-2.md")

        result = resolve_pending_drs(decisions_dir, engine)

        assert len(result) == 1
        moved = result[0]
        assert moved.name == "20-approach-selection-3.md", (
            f"With base and -2 taken, next free must be '-3.md'; got {moved.name!r}"
        )

    def test_ac3_boundary_three_preexisting_conflicts_yield_dash_4_suffix(self, tmp_path: Path) -> None:
        """AC3 boundary: three pre-existing variants → next-free counter lands at -4.md."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "33-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=33)
        _write_resolved(resolved_dir, "33-approach-selection.md")
        _write_resolved(resolved_dir, "33-approach-selection-2.md")
        _write_resolved(resolved_dir, "33-approach-selection-3.md")

        result = resolve_pending_drs(decisions_dir, engine)

        assert len(result) == 1
        moved = result[0]
        assert moved.name == "33-approach-selection-4.md", (
            f"Three pre-existing variants → next free must be '-4.md'; got {moved.name!r}"
        )

    # ---------------------------------------------------------------------------
    # AC4 (td:1): Non-overwriting mechanism (O_EXCL or equivalent)
    # ---------------------------------------------------------------------------

    def test_ac4_mechanism_does_not_overwrite_resolved_file(self, tmp_path: Path) -> None:
        """AC4: The collision mechanism must not overwrite the pre-existing resolved file."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "77-approach-selection.md"
        existing_content = "DO NOT TOUCH ME"
        _write_resolved(resolved_dir, filename, content=existing_content)
        _write_dr(pending_dir, filename, response="needs-info", task_id=77)

        resolve_pending_drs(decisions_dir, engine)

        # The original file must be untouched
        after_content = (resolved_dir / filename).read_text(encoding="utf-8")
        assert after_content == existing_content, (
            f"Non-overwriting mechanism must preserve the existing resolved file; "
            f"expected {existing_content!r}, got {after_content!r}"
        )
        # And a suffixed copy must now exist
        suffixed = resolved_dir / "77-approach-selection-2.md"
        assert suffixed.exists(), "A collision-suffixed file must have been created in resolved/"

    # ---------------------------------------------------------------------------
    # AC5 (td:1): Both resolution paths apply collision protection
    # ---------------------------------------------------------------------------

    def test_ac5_approved_path_applies_collision_protection(self, tmp_path: Path) -> None:
        """AC5 approved: the approved branch applies the same collision-protection logic."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "100-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=100)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert result, "Approved DR must be moved to resolved/"
        moved = result[0]
        assert moved.name != filename, "Approved branch must not overwrite pre-existing resolved file"
        # Verify original untouched
        assert (resolved_dir / filename).read_text(encoding="utf-8") == _SENTINEL

    def test_ac5_rejected_path_applies_collision_protection(self, tmp_path: Path) -> None:
        """AC5 rejected: the rejected branch applies the same collision-protection logic."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "200-approach-selection.md"
        _write_dr(pending_dir, filename, response="rejected", task_id=200)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert result, "Rejected DR must be moved to resolved/"
        moved = result[0]
        assert moved.name != filename, "Rejected branch must not overwrite pre-existing resolved file"
        assert (resolved_dir / filename).read_text(encoding="utf-8") == _SENTINEL

    def test_ac5_needs_info_path_applies_collision_protection(self, tmp_path: Path) -> None:
        """AC5 needs-info: the needs-info branch applies the same collision-protection logic."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "300-approach-selection.md"
        _write_dr(pending_dir, filename, response="needs-info", task_id=300)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert result, "Needs-info DR must be moved to resolved/"
        moved = result[0]
        assert moved.name != filename, "Needs-info branch must not overwrite pre-existing resolved file"
        assert (resolved_dir / filename).read_text(encoding="utf-8") == _SENTINEL

    # ---------------------------------------------------------------------------
    # Retry gaps: collision-path source-removal and mechanism proof (reviewer Required Follow-up)
    # ---------------------------------------------------------------------------

    def test_ac1_collision_case_pending_source_file_removed_after_move(self, tmp_path: Path) -> None:
        """AC1 retry gap: pending source file must be deleted after a collision-protected move."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "11-approach-selection.md"
        pending_file = _write_dr(pending_dir, filename, response="approved", task_id=11)
        _write_resolved(resolved_dir, filename)  # force collision path

        resolve_pending_drs(decisions_dir, engine)

        assert not pending_file.exists(), (
            "Pending source file must be removed from pending/ after collision-protected move; "
            f"{pending_file} still exists"
        )

    def test_ac4_collision_helper_uses_o_excl_exclusive_create_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC4 mechanism retry gap: collision helper uses O_CREAT|O_EXCL, not exists-then-write."""
        import os as os_mod

        real_open = os_mod.open
        observed_flags: list[int] = []

        def spy_open(path: object, flags: int, mode: int = 0o777) -> int:
            observed_flags.append(flags)
            return real_open(path, flags, mode)  # type: ignore[arg-type]

        monkeypatch.setattr("owlbear_kanban.decisions.os.open", spy_open)

        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "22-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=22)
        _write_resolved(resolved_dir, filename)  # force collision so helper is invoked

        resolve_pending_drs(decisions_dir, engine)

        assert observed_flags, "os.open must be called by the collision helper during resolution"
        o_creat = os_mod.O_CREAT
        o_excl = os_mod.O_EXCL
        matching = [f for f in observed_flags if (f & o_creat) and (f & o_excl)]
        assert matching, (
            "Collision helper must use O_CREAT|O_EXCL for atomic exclusive-create; no matching os.open call found"
        )
