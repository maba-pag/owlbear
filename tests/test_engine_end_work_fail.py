"""Tests for AgentView.end_work fail outcome + MCP model alignment (task #1125).

Tests:
  AC1 — AgentView.end_work(outcome="fail") succeeds: note appended, status unchanged, claim released
  AC2 — AgentView.end_work(outcome="fail") on unclaimed task raises ERR_NOT_CLAIMED
  AC3 — AgentView.end_work(outcome="fail") rejects move_to / block_reason / archival fields
  AC4 — EndWorkParams(outcome="fail") validates successfully (Literal includes "fail")
  AC5 — h-mcp-kanban SKILL.md outcome table includes release row
  AC6 — AgentView.end_work(outcome="fail") CAS stale-recovery branch proof
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ConcurrencyError, ValidationError

# ---------------------------------------------------------------------------
# Board helpers (mirrored from test_engine_end_work_1077.py)
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
next_id: 1
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: {tags}
parent: {parent}
depends_on: {depends_on}
blocked: {blocked}
block_reason: {block_reason}
claimed_at: {claimed_at}
archival_reason: {archival_reason}
archival_refs: {archival_refs}
---
{body}
"""

_LIVE_CLAIM_TS = '"2026-04-25T08:00:00+00:00"'  # non-null, within 1h claim_timeout


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(  # noqa: PLR0913
    kanban_dir: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "in-progress",
    priority: str = "needed",
    tags: str = "[]",
    blocked: str = "false",
    block_reason: str = "null",
    depends_on: str = "[]",
    body: str = "Initial body.",
    parent: str = "null",
    archival_reason: str = "null",
    archival_refs: str = "[]",
    claimed_at: str = "null",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        tags=tags,
        blocked=blocked,
        block_reason=block_reason,
        depends_on=depends_on,
        body=body,
        parent=parent,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
        claimed_at=claimed_at,
    )
    dest = kanban_dir / "tasks" / f"{task_id}-task.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return dest


def _make_view(base_dir: Path) -> tuple[AgentView, Path]:
    kanban_dir = _make_board(base_dir)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine), kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_FailOutcome — AC1, AC2, AC3
# ---------------------------------------------------------------------------


class TestFromAC_FailOutcome:
    """AgentView.end_work(outcome='fail') — AC1, AC2, AC3."""

    # --- AC1: success path ---------------------------------------------------

    def test_fail_outcome_returns_response(self, tmp_path: Path) -> None:
        """AC1: fail outcome returns a response without raising.

        FAIL reason: AgentView.end_work valid_outcomes excludes 'fail' — raises
        ERR_INVALID_OUTCOME before delegating to engine.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        # Must not raise
        result = view.end_work(1, outcome="fail", note="Stopping here — need rethink.")
        assert result is not None

    def test_fail_outcome_status_unchanged(self, tmp_path: Path) -> None:
        """AC1: fail outcome keeps status at 'in-progress' (no advancement).

        FAIL reason: AgentView.end_work currently raises ERR_INVALID_OUTCOME for
        'fail', so status is never changed/preserved.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(1, outcome="fail", note="Fail — retry needed.")

        assert result.task.status == "in-progress", (
            f"Expected status 'in-progress' after fail; got {result.task.status!r}"
        )

    def test_fail_outcome_releases_claim(self, tmp_path: Path) -> None:
        """AC1: fail outcome releases the claim (claimed_at becomes null).

        FAIL reason: AgentView.end_work raises ERR_INVALID_OUTCOME for 'fail'
        before the claim-release path is reached.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(1, outcome="fail", note="Fail — releasing.")

        assert result.task.claimed_at is None, f"Expected claim released after fail; got {result.task.claimed_at!r}"

    def test_fail_outcome_note_appended(self, tmp_path: Path) -> None:
        """AC1: fail outcome appends the note to task body.

        FAIL reason: AgentView.end_work raises ERR_INVALID_OUTCOME for 'fail'
        before the note-append path is reached.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            status="in-progress",
            body="Original body.",
            claimed_at=_LIVE_CLAIM_TS,
        )

        note_text = "Fail — approach needs rethink."
        result = view.end_work(1, outcome="fail", note=note_text)

        assert note_text in result.task.body, f"Expected note to be appended to body; body={result.task.body!r}"

    def test_fail_outcome_note_has_timestamp(self, tmp_path: Path) -> None:
        """AC1: appended note includes an ISO 8601 datetime prefix.

        FAIL reason: AgentView.end_work raises ERR_INVALID_OUTCOME for 'fail'
        before the note-append path is reached.
        """
        import re

        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(1, outcome="fail", note="Fail note.")

        # ISO 8601 datetime pattern: YYYY-MM-DDTHH:MM (time component present)
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", result.task.body), (
            f"Expected ISO 8601 datetime in appended note; body={result.task.body!r}"
        )

    # --- AC2: claimed requirement ---------------------------------------------

    def test_fail_outcome_unclaimed_raises_not_claimed(self, tmp_path: Path) -> None:
        """AC2: fail outcome on unclaimed task raises ERR_NOT_CLAIMED.

        FAIL reason: AgentView.end_work raises ERR_INVALID_OUTCOME for 'fail'
        before the claimed-check, so the wrong error code is returned.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at="null")

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="fail", note="Should fail with not-claimed.")

        assert exc_info.value.code == "ERR_NOT_CLAIMED", f"Expected ERR_NOT_CLAIMED; got {exc_info.value.code!r}"

    # --- AC3: forbidden parameters -------------------------------------------

    def test_fail_outcome_move_to_raises_forbidden(self, tmp_path: Path) -> None:
        """AC3: fail + move_to raises ERR_MOVE_TO_FORBIDDEN_ON_FAIL.

        FAIL reason: AgentView.end_work raises ERR_INVALID_OUTCOME for 'fail'
        before parameter validation, so the correct error code is never raised.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="fail", note="Fail.", move_to="review")

        assert exc_info.value.code == "ERR_MOVE_TO_FORBIDDEN_ON_FAIL", (
            f"Expected ERR_MOVE_TO_FORBIDDEN_ON_FAIL; got {exc_info.value.code!r}"
        )

    def test_fail_outcome_block_reason_raises_forbidden(self, tmp_path: Path) -> None:
        """AC3: fail + block_reason raises ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK.

        FAIL reason: AgentView.end_work raises ERR_INVALID_OUTCOME for 'fail'
        before parameter validation.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="fail", note="Fail.", block_reason="Blocked reason")

        assert exc_info.value.code == "ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK", (
            f"Expected ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK; got {exc_info.value.code!r}"
        )

    def test_fail_outcome_archival_reason_raises_forbidden(self, tmp_path: Path) -> None:
        """AC3: fail + archival_reason raises ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_FAIL.

        FAIL reason: AgentView.end_work raises ERR_INVALID_OUTCOME for 'fail'
        before parameter validation.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="fail", note="Fail.", archival_reason="completed")

        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_FAIL", (
            f"Expected ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_FAIL; got {exc_info.value.code!r}"
        )

    def test_fail_outcome_archival_refs_raises_forbidden(self, tmp_path: Path) -> None:
        """AC3: fail + archival_refs raises ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_FAIL.

        FAIL reason: AgentView.end_work raises ERR_INVALID_OUTCOME for 'fail'
        before parameter validation.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="fail", note="Fail.", archival_refs=[99])

        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_FAIL", (
            f"Expected ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_FAIL; got {exc_info.value.code!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkParamsFail — AC4
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkParamsFail:
    """EndWorkParams.outcome Literal includes 'fail' — AC4."""

    def test_end_work_params_accepts_fail(self) -> None:
        """AC4: EndWorkParams(outcome='fail') validates without error.

        FAIL reason: EndWorkParams Literal is currently ['success','reject','release','block']
        — 'fail' is absent, so Pydantic raises a ValidationError.
        """
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1, outcome="fail")
        assert p.outcome == "fail"


# ---------------------------------------------------------------------------
# TestFromAC_SkillDocReleaseRow — AC5
# ---------------------------------------------------------------------------


class TestFromAC_SkillDocReleaseRow:
    """h-mcp-kanban SKILL.md outcome table includes 'release' row — AC5."""

    _SKILL_PATH = Path(__file__).parent.parent / "share" / "skills" / "h-mcp-kanban" / "SKILL.md"

    def test_skill_doc_outcome_table_has_release_row(self) -> None:
        """AC5: outcome table in SKILL.md contains a 'release' row.

        FAIL reason: The current outcome table in h-mcp-kanban/SKILL.md has
        success, fail, block, reject rows — 'release' row is absent.
        """
        content = self._SKILL_PATH.read_text(encoding="utf-8")
        # Match a markdown table row starting with | `release` or | release
        assert "| `release`" in content or "| release " in content, (
            "Outcome table in h-mcp-kanban/SKILL.md is missing the 'release' row"
        )

    def test_skill_doc_release_row_describes_behavior(self) -> None:
        """AC5: release row describes behavior (idempotent on unclaimed / release claim).

        FAIL reason: The 'release' row does not yet exist, so its content cannot
        match the expected behavior description.
        """
        content = self._SKILL_PATH.read_text(encoding="utf-8")
        # The row must contain at least one of these behavioral keywords
        has_release_row = "| `release`" in content or "| release " in content
        assert has_release_row, "No 'release' row found — cannot verify behavior"

        # Find the release row and check for behavioral keywords
        for line in content.splitlines():
            if (
                "release" in line.lower()
                and line.strip().startswith("|")
                and ("idempotent" in line.lower() or "release claim" in line.lower() or "unclaimed" in line.lower())
            ):
                return  # found matching row
        pytest.fail("release row in outcome table does not describe idempotent/unclaimed behavior")

    def test_skill_doc_release_row_exact_behavior_text(self) -> None:
        """AC5: release row behavior cell exactly equals the corrected AC5 text.

        Corrected (retry cycle 7): prior text 'without note' contradicted live
        release_task behavior which appends notes when provided (engine.py:1296).
        Required text (AC5 final, cycle 8 — no trailing period):
          'Release claim, no status change (note appended if provided; no-op when unclaimed)'

        Uses exact cell extraction (==) rather than substring containment (in)
        to prevent false-green on trailing punctuation drift (cycle 8 fix).

        FAIL reason: handbook release row in share/skills/h-mcp-kanban/SKILL.md
        has a trailing period — builder must remove it so the cell text exactly
        matches the AC5 string without trailing punctuation.
        """
        expected = "Release claim, no status change (note appended if provided; no-op when unclaimed)"
        content = self._SKILL_PATH.read_text(encoding="utf-8")
        release_cell: str | None = None
        for line in content.splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = line.strip().split("|")
            # cells[0]='', cells[1]=outcome col, cells[2]=behavior col, cells[3]=''
            if len(cells) >= 3 and cells[1].strip() in ("`release`", "release"):
                release_cell = cells[2].strip()
                break
        assert release_cell is not None, "No '| release |' or '| `release` |' row found in outcome table"
        assert release_cell == expected, (
            f"Release row behavior cell mismatch.\n  Expected: {expected!r}\n  Got:      {release_cell!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_FailOutcomeCASRecovery — AC6
# ---------------------------------------------------------------------------


class TestFromAC_FailOutcomeCASRecovery:
    """AgentView.end_work(outcome='fail') CAS stale-recovery branch — AC6."""

    def test_fail_outcome_stale_unclaimed_raises_not_claimed(self, tmp_path: Path) -> None:
        """AC6(a): ERR_STALE + concurrent release → ValidationError(ERR_NOT_CLAIMED).

        Simulation: patch write_task_if_unchanged to release the claim (write
        claimed_at=None to disk) then raise ConcurrencyError(ERR_STALE).
        AgentView re-reads the task, finds claimed_at is None, and maps the
        stale error to ERR_NOT_CLAIMED.

        Test pattern mirrors test_engine_move_claim_1075.py CAS injection.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        def stale_then_unclaim(_task: object, _expected_updated: str, kdir: Path) -> Path:
            # Simulate: concurrent agent releases the claim before our CAS write.
            task_path = next((kdir / "tasks").glob("1-*.md"))
            from owlbear_kanban.storage import read_task as _read, write_task as _write  # noqa: PLC0415

            record = _read(task_path)
            record.claimed_at = None  # release the claim in the file
            _write(record, kdir)
            raise ConcurrencyError(
                code="ERR_STALE",
                user_message="simulated concurrent release",
            )

        with (
            patch(
                "owlbear_kanban.storage.write_task_if_unchanged",
                side_effect=stale_then_unclaim,
            ),
            pytest.raises(ValidationError) as exc_info,
        ):
            view.end_work(1, outcome="fail", note="Fail note.")

        assert exc_info.value.code == "ERR_NOT_CLAIMED", (
            f"Expected ERR_NOT_CLAIMED when stale write finds unclaimed task; got {exc_info.value.code!r}"
        )

    def test_fail_outcome_stale_still_claimed_raises_stale(self, tmp_path: Path) -> None:
        """AC6(b): ERR_STALE + task still claimed → ConcurrencyError(ERR_STALE).

        Simulation: patch write_task_if_unchanged to raise ConcurrencyError(ERR_STALE)
        without releasing the claim. AgentView re-reads the task, finds claimed_at
        is still set, and propagates ERR_STALE with retry guidance.

        Test pattern mirrors test_engine_move_claim_1075.py CAS injection.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        def stale_keep_claimed(_task: object, _expected_updated: str, _kdir: Path) -> Path:
            # Simulate: concurrent modification without releasing the claim.
            raise ConcurrencyError(
                code="ERR_STALE",
                user_message="simulated concurrent modification",
            )

        with (
            patch(
                "owlbear_kanban.storage.write_task_if_unchanged",
                side_effect=stale_keep_claimed,
            ),
            pytest.raises(ConcurrencyError) as exc_info,
        ):
            view.end_work(1, outcome="fail", note="Fail note.")

        assert exc_info.value.code == "ERR_STALE", (
            f"Expected ERR_STALE when stale write finds still-claimed task; got {exc_info.value.code!r}"
        )
        assert "changed concurrently; reload and retry" in exc_info.value.user_message, (
            f"Expected retry-guidance in user_message; got {exc_info.value.user_message!r}"
        )
