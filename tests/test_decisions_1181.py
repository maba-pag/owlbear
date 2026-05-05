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

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban.decisions import create_dr, resolve_pending_drs

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


def _write_dr(
    pending_dir: Path,
    filename: str,
    response: str,
    task_id: int = 42,
) -> Path:
    """Write a minimal 5-field DR file into pending_dir."""
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: approach-selection\n"
        "created: '2026-04-30'\n"
        f"response: {response}\n"
        "---\n\n## Body\nTest.\n"
    )
    path = pending_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def _mock_engine() -> MagicMock:
    """Return a lenient MagicMock suitable for use as a DecisionEngine."""
    return MagicMock()


# ---------------------------------------------------------------------------
# AC2, AC4, AC5, AC6, AC7 — create_dr
# ---------------------------------------------------------------------------


class TestFromAC_CreateDr:
    """Smoke tests for create_dr() — AC lines 2, 4, 5, 6, 7."""

    def test_ac2_returns_path_inside_pending_dir(self, tmp_path: Path) -> None:
        """AC2 smoke: create_dr returns a Path located in decisions_dir/pending/."""
        decisions_dir, _, _ = _make_dirs(tmp_path)
        engine = _mock_engine()

        result = create_dr(
            decisions_dir,
            engine,
            task_id=1,
            agent="builder",
            request_type="approach-selection",
            body="## Context\nSome body.",
        )

        assert isinstance(result, Path), (
            f"create_dr must return a Path; got {type(result)!r}"
        )
        assert result.exists(), "Returned path must exist on disk"
        assert result.parent == decisions_dir / "pending", (
            f"File must be written inside decisions_dir/pending/; got parent {result.parent}"
        )

    def test_ac4_frontmatter_has_exactly_five_fields(self, tmp_path: Path) -> None:
        """AC4 smoke: created file frontmatter contains exactly the 5 required fields."""
        from ruamel.yaml import YAML

        decisions_dir, _, _ = _make_dirs(tmp_path)
        engine = _mock_engine()

        result = create_dr(
            decisions_dir,
            engine,
            task_id=10,
            agent="reviewer",
            request_type="information-request",
            body="",
        )

        text = result.read_text(encoding="utf-8")
        lines = text.splitlines()
        close_idx = next(i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---")
        fm = YAML(typ="safe").load("\n".join(lines[1:close_idx])) or {}

        expected = {"task_id", "agent", "request_type", "created", "response"}
        assert set(fm.keys()) == expected, (
            f"Frontmatter must have exactly {sorted(expected)}; got {sorted(fm.keys())}"
        )
        assert str(fm["created"]).count("-") == 2, (
            f"'created' must be YYYY-MM-DD; got {fm['created']!r}"
        )
        assert fm["response"] == "pending", (
            f"'response' must default to 'pending'; got {fm['response']!r}"
        )

    def test_ac5_slug_derived_from_request_type(self, tmp_path: Path) -> None:
        """AC5 smoke: filename slug comes from the request_type argument."""
        decisions_dir, _, _ = _make_dirs(tmp_path)
        engine = _mock_engine()

        result = create_dr(
            decisions_dir,
            engine,
            task_id=7,
            agent="builder",
            request_type="approach-selection",
            body="",
        )

        assert "approach-selection" in result.stem, (
            f"Slug must be derived from request_type 'approach-selection'; got stem {result.stem!r}"
        )

    def test_ac6_collision_produces_dash_2_suffix(self, tmp_path: Path) -> None:
        """AC6 smoke: a second create_dr with the same args produces a -2 suffix filename."""
        decisions_dir, _, _ = _make_dirs(tmp_path)
        engine = _mock_engine()

        first = create_dr(
            decisions_dir,
            engine,
            task_id=5,
            agent="builder",
            request_type="approach-selection",
            body="First",
        )
        second = create_dr(
            decisions_dir,
            engine,
            task_id=5,
            agent="builder",
            request_type="approach-selection",
            body="Second",
        )

        assert first.exists(), "First file must still exist after collision"
        assert second.exists(), "Second file must be created despite collision"
        assert first != second, "Collision must produce a distinct path"
        assert second.stem.endswith("-2"), (
            f"First collision must produce -2 suffix; got stem {second.stem!r}"
        )

    def test_ac7_file_deleted_and_exception_reraises_on_engine_failure(
        self, tmp_path: Path
    ) -> None:
        """AC7 smoke: if engine.edit_task raises, the DR file is deleted and exception re-raised."""
        decisions_dir, _, _ = _make_dirs(tmp_path)
        engine = _mock_engine()
        engine.edit_task.side_effect = RuntimeError("engine down")

        with pytest.raises(RuntimeError, match="engine down"):
            create_dr(
                decisions_dir,
                engine,
                task_id=99,
                agent="builder",
                request_type="approach-selection",
                body="Rollback test",
            )

        orphans = list((decisions_dir / "pending").glob("*.md"))
        assert orphans == [], (
            f"Rollback must remove the DR file; orphaned files: {[p.name for p in orphans]}"
        )


# ---------------------------------------------------------------------------
# AC3, AC8, AC9, AC10 — resolve_pending_drs
# ---------------------------------------------------------------------------


class TestFromAC_ResolvePendingDrs:
    """Tests for resolve_pending_drs() — AC lines 3 (dual form), 8 (td:2), 9, 10."""

    # --- AC3: dual call-form (engine-only) — PRIMARY GAP not in #1180/#1195 ---

    def test_ac3_engine_only_form_resolves_from_kanban_dir(
        self, tmp_path: Path
    ) -> None:
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

        assert isinstance(result, list), (
            f"resolve_pending_drs must return a list; got {type(result)!r}"
        )
        assert len(result) == 1, (
            f"Engine-only form must process DRs from engine._kanban_dir/decisions/; got {result}"
        )
        assert not dr_file.exists(), "Resolved DR must be removed from pending/"
        assert (resolved_dir / "42-approach-selection.md").exists(), (
            "Resolved DR must appear in decisions_dir/resolved/"
        )

    # --- AC8 (td:2): resolve logic — happy, edge, error, boundary ---

    def test_ac8_happy_approved_appends_unblocks_and_moves(
        self, tmp_path: Path
    ) -> None:
        """AC8 happy: approved DR → append_body called, unblock called, file in resolved/."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        _write_dr(
            pending_dir, "42-approach-selection.md", response="approved", task_id=42
        )
        engine = _mock_engine()

        result = resolve_pending_drs(decisions_dir, engine)

        # append_body must have been called for task 42
        append_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0
            and c.args[0] == 42
            and c.kwargs.get("append_body") is not None
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
        assert (resolved_dir / "42-approach-selection.md").exists(), (
            "Approved DR must be moved to resolved/"
        )
        assert not (pending_dir / "42-approach-selection.md").exists(), (
            "Approved DR must be removed from pending/"
        )
        assert len(result) == 1, f"One DR moved; got {result}"

    def test_ac8_edge_needs_info_appends_and_moves_without_unblock(
        self, tmp_path: Path
    ) -> None:
        """AC8 edge: needs-info DR → append_body called, file moved, NO unblock."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        _write_dr(
            pending_dir, "55-approach-selection.md", response="needs-info", task_id=55
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        # append_body must be called
        append_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0
            and c.args[0] == 55
            and c.kwargs.get("append_body") is not None
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
            f"needs-info must NOT call engine.edit_task(55, blocked=False) — "
            f"found unexpected unblock: {unblock_calls}"
        )

        # file must still move to resolved/
        assert (resolved_dir / "55-approach-selection.md").exists(), (
            "needs-info DR must be moved to resolved/ even though task stays blocked"
        )

    def test_ac8_error_engine_raises_during_unblock_file_stays_pending(
        self, tmp_path: Path
    ) -> None:
        """AC8 error: if engine raises during unblock, DR file stays in pending/ (not half-moved)."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        dr_file = _write_dr(
            pending_dir, "77-approach-selection.md", response="approved", task_id=77
        )
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
        assert dr_file.exists(), (
            "DR file must stay in pending/ when engine.edit_task raises during unblock"
        )
        assert not (resolved_dir / "77-approach-selection.md").exists(), (
            "DR file must NOT appear in resolved/ when unblock failed"
        )

    def test_ac8_boundary_rejected_full_flow_matches_approved(
        self, tmp_path: Path
    ) -> None:
        """AC8 boundary: rejected DR follows the same full flow as approved (append+unblock+move)."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        _write_dr(
            pending_dir, "88-approach-selection.md", response="rejected", task_id=88
        )
        engine = _mock_engine()

        result = resolve_pending_drs(decisions_dir, engine)

        unblock_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0 and c.args[0] == 88 and c.kwargs.get("blocked") is False
        ]
        assert unblock_calls, (
            "rejected DR must trigger unblock via engine.edit_task(88, blocked=False)"
        )
        assert (resolved_dir / "88-approach-selection.md").exists(), (
            "rejected DR must be moved to resolved/"
        )
        assert len(result) == 1, f"One DR moved; got {result}"

    # --- AC9: per-file exception isolation ---

    def test_ac9_exception_from_one_dr_does_not_stall_others(
        self, tmp_path: Path
    ) -> None:
        """AC9 smoke: exception from processing one DR does not prevent others from being resolved."""
        decisions_dir, pending_dir, _ = _make_dirs(tmp_path)
        resolved_dir = decisions_dir / "resolved"

        # File A: task 10 — engine.edit_task will raise for this task ID
        _write_dr(
            pending_dir, "10-approach-selection.md", response="approved", task_id=10
        )
        # File B: task 20 — must be processed successfully
        _write_dr(
            pending_dir, "20-approach-selection.md", response="approved", task_id=20
        )

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
        dr_file = _write_dr(
            pending_dir, "42-approach-selection.md", response="bogus-status"
        )
        engine = _mock_engine()

        with caplog.at_level(logging.WARNING):
            resolve_pending_drs(decisions_dir, engine)

        warning_texts = [
            r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING
        ]
        assert any(
            "bogus-status" in t or "unknown" in t.lower() for t in warning_texts
        ), (
            f"Expected warning mentioning the unknown response value; got: {warning_texts}"
        )
        assert dr_file.exists(), (
            "File with unknown response must remain in pending/ (not moved)"
        )
        assert not engine.edit_task.called, (
            "engine.edit_task must NOT be called for unknown response values"
        )

    # --- AC8 atomicity: move failure after mutation must not produce duplicate summary ---

    def test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry(
        self, tmp_path: Path
    ) -> None:
        """AC8 atomicity: if _move_with_collision_suffix fails after _append_summary and unblock,
        retrying resolve_pending_drs must NOT produce a second append_body call.

        Failure mode (current defect): the DR stays in pending after state mutation, so a retry
        will call _append_summary again — producing a duplicate summary in the task body.
        A correct implementation either rolls back the mutation or guards against re-processing.
        """
        decisions_dir, pending_dir, _resolved_dir = _make_dirs(tmp_path)
        _write_dr(
            pending_dir, "99-approach-selection.md", response="approved", task_id=99
        )
        engine = _mock_engine()

        target = "owlbear_kanban.decisions._move_with_collision_suffix"
        with patch(target, side_effect=OSError("disk full")):
            resolve_pending_drs(decisions_dir, engine)

        # DR must still be in pending after the failed move
        assert (pending_dir / "99-approach-selection.md").exists(), (
            "DR must remain in pending/ when _move_with_collision_suffix raises"
        )

        # Count append_body calls after the first (failed) attempt
        append_calls_first = [
            c
            for c in engine.edit_task.call_args_list
            if c.kwargs.get("append_body") is not None
        ]

        # Retry: run resolve again with move still failing
        with patch(target, side_effect=OSError("disk full")):
            resolve_pending_drs(decisions_dir, engine)

        append_calls_total = [
            c
            for c in engine.edit_task.call_args_list
            if c.kwargs.get("append_body") is not None
        ]

        assert len(append_calls_total) == len(append_calls_first), (
            "Retrying resolve after a move failure must NOT produce a duplicate append_body call; "
            f"after first attempt: {len(append_calls_first)} call(s), "
            f"after retry: {len(append_calls_total)} call(s) — duplicate detected"
        )

    # --- AC5: rejected path appends summary (retry gap fill) ---

    def test_ac5_rejected_path_appends_summary_to_task(
        self, tmp_path: Path
    ) -> None:
        """AC5 boundary: rejected DR must append_body to task before unblock and move."""
        decisions_dir, pending_dir, _resolved_dir = _make_dirs(tmp_path)
        _write_dr(
            pending_dir, "88-approach-selection.md", response="rejected", task_id=88
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        append_calls = [
            c
            for c in engine.edit_task.call_args_list
            if len(c.args) > 0
            and c.args[0] == 88
            and c.kwargs.get("append_body") is not None
        ]
        assert append_calls, (
            f"rejected DR must trigger engine.edit_task(88, append_body=...) — "
            f"actual calls: {engine.edit_task.call_args_list}"
        )
        # Summary must mention the response value
        summary_text = append_calls[0].kwargs["append_body"]
        assert "rejected" in summary_text, (
            f"append_body summary must contain 'rejected'; got: {summary_text!r}"
        )

    # --- AC6: pending removal for needs-info and rejected (retry gap fill) ---

    def test_ac6_needs_info_file_removed_from_pending_after_resolve(
        self, tmp_path: Path
    ) -> None:
        """AC6: after resolve_pending_drs(), needs-info DR must not remain in pending/."""
        decisions_dir, pending_dir, _resolved_dir = _make_dirs(tmp_path)
        dr_file = _write_dr(
            pending_dir, "55-approach-selection.md", response="needs-info", task_id=55
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        assert not dr_file.exists(), (
            "needs-info DR must be removed from pending/ after resolve_pending_drs() runs"
        )

    def test_ac6_rejected_file_removed_from_pending_after_resolve(
        self, tmp_path: Path
    ) -> None:
        """AC6: after resolve_pending_drs(), rejected DR must not remain in pending/."""
        decisions_dir, pending_dir, _resolved_dir = _make_dirs(tmp_path)
        dr_file = _write_dr(
            pending_dir, "88-approach-selection.md", response="rejected", task_id=88
        )
        engine = _mock_engine()

        resolve_pending_drs(decisions_dir, engine)

        assert not dr_file.exists(), (
            "rejected DR must be removed from pending/ after resolve_pending_drs() runs"
        )
