"""RED-phase tests for AgentView.move_task and AgentView.start_work (task #1075).

Covers Brief B paper-integration.md §1.6, §1.7, §3.1, §3.4:
  - start_work: ERR_ALREADY_CLAIMED detail includes claimed_at timestamp (D18+D36)
  - start_work: expired-claim lazy-release uses write_task_if_unchanged CAS (D18+D36)
  - start_work: fresh claim uses write_task_if_unchanged CAS (D18+D36)
  - start_work: on ERR_STALE retry, if re-read finds live claim → ERR_ALREADY_CLAIMED (D18+D36)

NOT TESTABLE AS RED (already implemented — behaviours verified to pass):
  D11     → start_work sets claimed_at = now(): engine.claim_task already sets claimed_at;
            SingleTaskResponse.claimed and .claimed_at already populate correctly.
  D11     → no claimed_by in response: write_task pops claimed_by (never persisted);
            TaskSummary._coerce_claimed() strips claimed_by from projections.
  D14     → updated advanced on move_task success: engine.move_task already sets
            record.updated = datetime.now(tz=UTC).isoformat() on every write path.
  D14     → updated advanced on start_work success: engine.claim_task already sets
            record.updated = effective_now.isoformat() alongside claimed_at.
  D46     → AgentView.move_task has no expected_updated param: current signature
            is move_task(task_id, status, *, archival_reason, archival_refs) — no
            expected_updated. D46 regression guard not needed as failing test.

AC coverage:
  D18+D36 CAS-1 → TestFromAC_StartWork_1075.test_already_claimed_error_includes_claimed_at
  D18+D36 CAS-2 → TestFromAC_StartWork_1075.test_expired_claim_release_uses_cas_primitive
  D18+D36 CAS-3 → TestFromAC_StartWork_1075.test_fresh_claim_uses_cas_primitive
  D18+D36 CAS-4 → TestFromAC_StartWork_1075.test_expired_claim_cas_stale_retry_raises_already_claimed
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine, storage
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ConcurrencyError, ValidationError

# ---------------------------------------------------------------------------
# Minimal board + task helpers (mirrors test_engine_move_claim.py conventions)
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: builder
  in-progress: builder
  review: reviewer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
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


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(  # noqa: PLR0913
    kanban_dir: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    priority: str = "needed",
    tags: str = "[]",
    blocked: str = "false",
    block_reason: str = "null",
    depends_on: str = "[]",
    body: str = "Body.",
    subdir: str = "tasks",
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
    dest_dir = kanban_dir / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_view(
    base_dir: Path, config_yaml: str = _BASE_CONFIG
) -> tuple[AgentView, Path]:
    kanban_dir = _make_board(base_dir, config_yaml)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine), kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_StartWork_1075
#
# All four tests cover D18+D36: expired-claim lazy-release and fresh-claim
# write must both use storage.write_task_if_unchanged (CAS).  Current
# engine.claim_task uses plain write_task (no CAS), so:
#
#   CAS-1: The live-claim error message does not include claimed_at — FAILS.
#   CAS-2: write_task_if_unchanged is never called during expired-claim path — FAILS.
#   CAS-3: write_task_if_unchanged is never called during fresh-claim path — FAILS.
#   CAS-4: ERR_STALE injection has no effect (code never calls the CAS
#           primitive), so start_work returns success instead of raising
#           ERR_ALREADY_CLAIMED after the simulated retry — FAILS.
# ---------------------------------------------------------------------------


class TestFromAC_StartWork_1075:
    """D18+D36 CAS contract tests for AgentView.start_work."""

    def test_already_claimed_error_includes_claimed_at(
        self, tmp_path: Path
    ) -> None:
        """D18+D36: ConcurrencyError(ERR_ALREADY_CLAIMED) must include claimed_at in message.

        Brief §1.7: ``ConcurrencyError(code="ERR_ALREADY_CLAIMED", detail="claimed_at={ts}")``.
        The error message must contain the live claim timestamp so callers can
        compute retry delay.  Current AgentView.start_work raises the error
        with a generic "already claimed by another agent" message that omits
        the timestamp.
        """
        view, kanban_dir = _make_view(tmp_path)
        live_ts = "2099-12-31T23:59:59+00:00"
        _write_task(kanban_dir, task_id=1, status="todo", claimed_at=f'"{live_ts}"')
        with pytest.raises(ConcurrencyError) as exc_info:
            view.start_work(1)
        assert exc_info.value.code == "ERR_ALREADY_CLAIMED"
        # D18+D36 brief contract: error detail must include the live claimed_at value.
        assert live_ts in exc_info.value.user_message, (
            f"ERR_ALREADY_CLAIMED message must contain claimed_at timestamp; "
            f"got: {exc_info.value.user_message!r}"
        )

    def test_expired_claim_release_uses_cas_primitive(
        self, tmp_path: Path
    ) -> None:
        """D18+D36: start_work on expired-claim task must route the release write
        through storage.write_task_if_unchanged (CAS), not plain write_task.

        Brief §1.7: "lazy-release first per D18+D36 by routing the release through
        storage.write_task_if_unchanged(cleared_task, expected_updated=current.updated, ...)".
        Current engine.claim_task uses plain write_task for the release — the CAS
        primitive is never called.
        """
        view, kanban_dir = _make_view(tmp_path)
        stale = "2026-01-01T00:00:00+00:00"  # well over 1h ago — expired
        _write_task(kanban_dir, task_id=1, status="todo", claimed_at=f'"{stale}"')

        mock_cas: MagicMock = MagicMock(wraps=storage.write_task_if_unchanged)
        with patch("owlbear_kanban.storage.write_task_if_unchanged", mock_cas):
            view.start_work(1)

        assert mock_cas.called, (
            "storage.write_task_if_unchanged must be called during expired-claim "
            "lazy-release (D18+D36); engine.claim_task currently uses plain write_task"
        )

    def test_fresh_claim_uses_cas_primitive(
        self, tmp_path: Path
    ) -> None:
        """D18+D36: start_work on an unclaimed task must route the claim write
        through storage.write_task_if_unchanged (CAS).

        Brief §1.7: "otherwise proceed to claim via the same CAS primitive."
        An unclaimed task also uses CAS for the claim write to prevent two
        agents from simultaneously overwriting each other's claim tokens.
        Current engine.claim_task uses plain write_task — CAS is never called.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")  # no claim

        mock_cas: MagicMock = MagicMock(wraps=storage.write_task_if_unchanged)
        with patch("owlbear_kanban.storage.write_task_if_unchanged", mock_cas):
            view.start_work(1)

        assert mock_cas.called, (
            "storage.write_task_if_unchanged must be called for the claim write "
            "even on a fresh (unclaimed) task (D18+D36 — 'same CAS primitive'); "
            "engine.claim_task currently uses plain write_task"
        )

    def test_expired_claim_cas_stale_retry_raises_already_claimed(
        self, tmp_path: Path
    ) -> None:
        """D18+D36: when the CAS write for expired-claim release raises ERR_STALE
        (concurrent agent beat us), start_work retries from the top; if the re-read
        finds a live claim, it raises ConcurrencyError(ERR_ALREADY_CLAIMED).

        Brief §1.7: "on ERR_STALE (another writer beat us to it), re-read and
        re-evaluate from the top."

        Simulation: on the first write_task_if_unchanged call we inject a
        concurrent live claim into the file then raise ConcurrencyError(ERR_STALE).
        The CAS-aware implementation retries, reads the live claim, and raises
        ERR_ALREADY_CLAIMED.  Without CAS, write_task_if_unchanged is never
        called, no injection occurs, and start_work returns success — causing this
        test to fail with "DID NOT RAISE ConcurrencyError".
        """
        view, kanban_dir = _make_view(tmp_path)
        stale = "2026-01-01T00:00:00+00:00"  # expired claim
        _write_task(kanban_dir, task_id=1, status="todo", claimed_at=f'"{stale}"')

        call_count = 0

        def inject_then_stale(task: object, expected_updated: str, kdir: Path) -> Path:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Simulate: another agent claims the task before our CAS write.
                current_path = next((kdir / "tasks").glob("1-*.md"))
                from owlbear_kanban.storage import read_task, write_task  # noqa: PLC0415

                live_record = read_task(current_path)
                live_record.claimed_at = "2099-12-31T00:00:00+00:00"
                live_record.updated = "2099-12-31T00:00:00+00:00"
                write_task(live_record, kdir)
                raise ConcurrencyError(
                    code="ERR_STALE",
                    user_message="simulated concurrent modification",
                )
            # Allow subsequent calls through (second attempt after retry).
            return storage.write_task_if_unchanged(task, expected_updated, kdir)

        with (
            patch("owlbear_kanban.storage.write_task_if_unchanged", side_effect=inject_then_stale),
            pytest.raises(ConcurrencyError) as exc_info,
        ):
            view.start_work(1)

        assert exc_info.value.code == "ERR_ALREADY_CLAIMED", (
            f"Expected ERR_ALREADY_CLAIMED after ERR_STALE retry sees live claim; "
            f"got {exc_info.value.code!r}"
        )

    def test_expired_claim_release_before_claim_two_cas_writes(
        self, tmp_path: Path
    ) -> None:
        """D18+D36: expired-claim path must issue TWO CAS writes in sequence:
        (1) release write — task with claimed_at=None, then (2) claim write —
        task with claimed_at=<now>.

        Brief §1.7: "lazy-release first per D18+D36 by routing the release through
        storage.write_task_if_unchanged(cleared_task, expected_updated=current.updated, ...);
        ... otherwise proceed to claim via the same CAS primitive."

        The current engine.claim_task performs a single CAS write that sets
        claimed_at to the new timestamp directly (no prior release step), so:
          - cas_call_claimed_ats has only 1 entry → assertion len >= 2 fails.
        Even if len were to pass, the first entry would have claimed_at != None.
        """
        view, kanban_dir = _make_view(tmp_path)
        stale = "2026-01-01T00:00:00+00:00"  # well over 1h ago — expired
        _write_task(kanban_dir, task_id=1, status="todo", claimed_at=f'"{stale}"')

        real_cas = storage.write_task_if_unchanged
        cas_call_claimed_ats: list[str | None] = []

        def capture(task: object, expected_updated: str, kdir: Path) -> Path:
            cas_call_claimed_ats.append(getattr(task, "claimed_at", None))
            return real_cas(task, expected_updated, kdir)

        with patch("owlbear_kanban.storage.write_task_if_unchanged", side_effect=capture):
            view.start_work(1)

        assert len(cas_call_claimed_ats) >= 2, (
            f"Expected ≥2 CAS writes (release then claim) for expired-claim path; "
            f"got {len(cas_call_claimed_ats)} write(s) with claimed_at values: "
            f"{cas_call_claimed_ats!r}. "
            f"Brief §1.7 requires a release step (claimed_at=None) before the claim write."
        )
        assert cas_call_claimed_ats[0] is None, (
            f"First CAS write must be the release step with claimed_at=None; "
            f"got claimed_at={cas_call_claimed_ats[0]!r}. "
            f"Current implementation skips the release step and claims directly."
        )
        assert cas_call_claimed_ats[1] is not None, (
            f"Second CAS write must be the claim step with claimed_at=<new timestamp>; "
            f"got claimed_at={cas_call_claimed_ats[1]!r}"
        )

    def test_stale_retry_success_produces_fresh_timestamps(
        self, tmp_path: Path
    ) -> None:
        """D14: on stale-retry-success, claimed_at and updated must be fresher
        than the pre-attempt snapshot (effective_now refreshed inside retry loop).

        Brief §3.2: updated is advanced on every successful write.
        Regression guard: if effective_now were captured once before the retry loop
        (old bug), successful retries after ERR_STALE could reuse a stale timestamp
        and set updated/claimed_at to a value that lags the re-read snapshot.
        Fix at engine.py:1136 refreshes effective_now inside the loop.

        Failure mode: CAS-raise-stale logic is absent (write_task_if_unchanged never
        called) → second call never fires → call_count stays 1 → assertion fails.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")

        # Read the initial snapshot so we have a definite lower bound for freshness.
        task_path = next((kanban_dir / "tasks").glob("1-*.md"))
        snapshot = storage.read_task(task_path)
        snapshot_updated_str = snapshot.updated  # "2026-01-01T10:00:00+00:00"

        call_count = 0
        real_cas = storage.write_task_if_unchanged

        def stale_on_first(task: object, expected_updated: str, kdir: Path) -> Path:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConcurrencyError(
                    code="ERR_STALE",
                    user_message="simulated stale — retry should refresh timestamps",
                )
            return real_cas(task, expected_updated, kdir)

        with patch("owlbear_kanban.storage.write_task_if_unchanged", side_effect=stale_on_first):
            result = view.start_work(1)

        from datetime import datetime  # noqa: PLC0415

        snapshot_dt = datetime.fromisoformat(snapshot_updated_str)
        result_claimed_at = datetime.fromisoformat(result.claimed_at)
        result_updated = datetime.fromisoformat(result.updated)

        assert result_claimed_at > snapshot_dt, (
            f"D14: after stale-retry-success, claimed_at={result.claimed_at!r} must be "
            f"fresher than pre-attempt snapshot.updated={snapshot_updated_str!r}"
        )
        assert result_updated > snapshot_dt, (
            f"D14: after stale-retry-success, updated={result.updated!r} must be "
            f"fresher than pre-attempt snapshot.updated={snapshot_updated_str!r}"
        )
        assert call_count == 2, (  # noqa: PLR2004
            f"Expected exactly 2 CAS calls (first stale, second success); got {call_count}"
        )

    def test_stale_retry_success_timestamps_fresher_than_concurrent_update(
        self, tmp_path: Path
    ) -> None:
        """D14 (mutation-resistant): stale-retry claimed_at/updated must be fresher
        than the concurrent update written during ERR_STALE.

        Mechanism (architect AC refinement — prescribes HOW, not just WHAT):
          T1 < T_concurrent < T3
          - datetime.now mocked: first loop iteration → T1, retry iteration → T3
          - ERR_STALE callback writes the task file with updated=T_concurrent
            (simulates a concurrent edit that beat our CAS)
          - Engine re-reads: task.updated=T_concurrent, effective_now=T3 (refreshed)
          - Assertions: result.claimed_at >= T3 AND result.updated >= T3

        Mutation guard: if effective_now were captured once before the loop
        (reverting engine.py:1136), both iterations use T1.  T1 < T_concurrent so
        the second CAS succeeds but result.updated = T1 < T3 → assertion fails.

        NOTE: regression guard — PASSES because engine.py:1136 fix is already in place.
        """
        import datetime as _dt  # noqa: PLC0415

        t1 = _dt.datetime(2026, 1, 1, 10, 0, 1, tzinfo=_dt.UTC)
        t_concurrent = _dt.datetime(2026, 1, 1, 10, 0, 2, tzinfo=_dt.UTC)
        t3 = _dt.datetime(2026, 1, 1, 10, 0, 3, tzinfo=_dt.UTC)

        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")

        scheduled: list[_dt.datetime] = [t1, t3]

        class _MockDatetime(_dt.datetime):
            @classmethod
            def now(cls, tz: object = None) -> _dt.datetime:  # type: ignore[override]
                if scheduled:
                    return scheduled.pop(0)
                return _dt.datetime.now(tz=tz)  # type: ignore[arg-type]

        real_cas = storage.write_task_if_unchanged
        cas_call_count = 0

        def stale_then_succeed(task: object, expected_updated: str, kdir: Path) -> Path:
            nonlocal cas_call_count
            cas_call_count += 1
            if cas_call_count == 1:
                # Concurrent update: write t_concurrent to disk, then raise ERR_STALE.
                task_path = next((kdir / "tasks").glob("1-*.md"))
                from owlbear_kanban.storage import read_task as _read, write_task as _write  # noqa: PLC0415

                concurrent_record = _read(task_path)
                concurrent_record.updated = t_concurrent.isoformat()
                _write(concurrent_record, kdir)
                raise ConcurrencyError(
                    code="ERR_STALE",
                    user_message="simulated concurrent edit",
                )
            return real_cas(task, expected_updated, kdir)

        with (
            patch("owlbear_kanban.engine.datetime", _MockDatetime),
            patch("owlbear_kanban.storage.write_task_if_unchanged", side_effect=stale_then_succeed),
        ):
            result = view.start_work(1)

        result_claimed_at = _dt.datetime.fromisoformat(result.claimed_at)
        result_updated = _dt.datetime.fromisoformat(result.updated)

        assert result_claimed_at >= t3, (
            f"D14: stale-retry-success claimed_at={result.claimed_at!r} must be "
            f">= t3={t3.isoformat()!r}; mutation guard: reverting engine.py:1136 "
            f"gives effective_now=t1={t1.isoformat()!r} < t3"
        )
        assert result_updated >= t3, (
            f"D14: stale-retry-success updated={result.updated!r} must be "
            f">= t3={t3.isoformat()!r}; mutation guard: reverting engine.py:1136 "
            f"gives effective_now=t1={t1.isoformat()!r} < t3"
        )
        assert cas_call_count == 2, (  # noqa: PLR2004
            f"Expected 2 CAS calls (stale then succeed); got {cas_call_count}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_MoveTask_D37_1075
#
# D37 full matrix: _validate_move_archival must reject self-references and
# archival cycles, matching the edit_task path at engine.py:2443-2456.
# Current _validate_move_archival lacks both checks (no task_id param, no
# _has_archival_cycle call), so both tests fail.
# ---------------------------------------------------------------------------


class TestFromAC_MoveTask_D37_1075:
    """D37 archival-matrix self-ref and cycle tests for AgentView.move_task."""

    def test_move_task_archival_rejects_self_reference(
        self, tmp_path: Path
    ) -> None:
        """D37: move_task('archived') must raise ERR_ARCHIVAL_REF_SELF when
        archival_refs includes the task's own id.

        Brief §1.6 D37 matrix (same as edit_task): self-references are always
        forbidden.  The edit_task path enforces this at engine.py:2443-2445.
        Current _validate_move_archival omits the check (no task_id param) so
        the call completes without raising.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="done")

        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                archival_reason="deprecated",
                archival_refs=[1],  # self-reference
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_SELF", (
            f"move_task must reject self-referencing archival_refs with "
            f"ERR_ARCHIVAL_REF_SELF; got {exc_info.value.code!r}"
        )

    def test_move_task_archival_rejects_cycle(
        self, tmp_path: Path
    ) -> None:
        """D37: move_task('archived') must raise ERR_ARCHIVAL_REF_CYCLE when
        archival_refs would introduce a transitive cycle.

        Setup: task 2 already references task 1 (archival_refs=[1]).
        Archiving task 1 with archival_refs=[2] creates the cycle 1→2→1.
        The edit_task path catches this at engine.py:2454-2456 via the existing
        _has_archival_cycle helper.  Current _validate_move_archival never calls
        that helper, so no error is raised.
        """
        view, kanban_dir = _make_view(tmp_path)
        # task 2 already archived and references task 1
        _write_task(
            kanban_dir,
            task_id=2,
            status="todo",
            archival_refs="[1]",
        )
        # task 1 (the one being moved) references task 2 → creates cycle 1→2→1
        _write_task(kanban_dir, task_id=1, status="done")

        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                archival_reason="deprecated",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_CYCLE", (
            f"move_task must reject cycles in archival_refs with "
            f"ERR_ARCHIVAL_REF_CYCLE; got {exc_info.value.code!r}"
        )
