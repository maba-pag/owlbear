from __future__ import annotations

# --- merged from tests/test_decisions_1180.py ---
"""Failing tests for #1180: Test decisions.py request creation + resolve_pending_drs.

AC coverage:
    ac1-frontmatter  — request creation writes pending file with 5-field YAML frontmatter
    ac1-body         — request creation places markdown body after frontmatter delimiter
    ac2-collision    — request creation O_EXCL collision retries with counter suffix (-2.md)
    ac3-block        — request creation blocks the task via engine.edit_task
    ac4-rollback     — request creation deletes file if engine.edit_task raises (rollback)
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
    ac2-create-path   — request creation helper(decisions_dir, engine, *, task_id, agent, request_type, body) → Path
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
