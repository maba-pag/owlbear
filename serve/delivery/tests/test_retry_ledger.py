"""Focused D03-B durable retry ledger checks."""

# ruff: noqa: SLF001 - CAS assertions intentionally exercise the ledger's transaction boundary.

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_delivery.recovery import (
    RetryEpisodeKey,
    RetryFailureClass,
    RetryLedger,
    RetryLedgerConflictError,
    RetryLedgerCorruptError,
    RetryLedgerSummary,
    RetryStopCode,
)

_START = datetime(2026, 8, 4, tzinfo=UTC)
_HEAD = "a" * 40
_TARGET = "b" * 40


def _engine_key(change_id: str = "change-a", action: str = "build") -> RetryEpisodeKey:
    return RetryEpisodeKey.engine(change_id, action, _HEAD, _TARGET, "final-1")


def test_semantic_identity_aliases_and_restart_persistence(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key()
    same_key = _engine_key()

    assert key.identity == same_key.identity
    reservation = ledger.reserve(
        key,
        failure_class=RetryFailureClass.MECHANICAL,
        now=_START,
        attempt_id="operation-original",
        operation_alias="session-original",
    )
    episode = ledger.record_failure(reservation, failure_code="builder-failed", now=_START)
    episode = ledger.record_alias(key, alias_kind="commit", value=_HEAD, now=_START)

    restarted = RetryLedger(tmp_path, "change-a").read()
    restored = restarted.episodes[0]
    assert restored.episode_id == key.identity
    assert restored.attempt_ids == ("operation-original",)
    assert {alias.value for alias in episode.aliases} == {"session-original", _HEAD}
    assert {alias.value for alias in restored.aliases} == {"session-original", _HEAD}
    assert restored.next_eligible_at == (_START + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")


def test_duplicate_reservation_is_idempotent_and_mechanical_budget_is_bounded(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key()

    original = ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START,
        attempt_id="attempt-1",
        operation_alias="operation-1",
    )
    assert ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START,
        attempt_id="attempt-1",
        operation_alias="operation-1-replayed",
    ).replayed
    first_failure = ledger.record_failure(original, failure_code="repair-1", now=_START)
    assert first_failure.repair_attempts == 0
    assert ledger.record_failure(original, failure_code="different-prose", now=_START).outcome_ids == (
        first_failure.outcome_ids
    )
    with pytest.raises(RetryLedgerConflictError, match="original retry attempt"):
        ledger.reserve(
            key,
            failure_class="mechanical",
            now=_START,
            attempt_id="attempt-original-again",
            original=True,
        )

    early = ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START + timedelta(milliseconds=500),
        attempt_id="attempt-2",
    )
    assert not early.allowed
    assert early.reason_code == RetryStopCode.BACKOFF.value

    repair_one = ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START + timedelta(seconds=1),
        attempt_id="attempt-2",
    )
    ledger.record_failure(repair_one, failure_code="repair-2", now=_START + timedelta(seconds=1))
    repair_two = ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START + timedelta(seconds=3),
        attempt_id="attempt-3",
    )
    ledger.record_failure(repair_two, failure_code="repair-3", now=_START + timedelta(seconds=3))

    exhausted = ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START + timedelta(seconds=10),
        attempt_id="attempt-4",
    )
    assert not exhausted.allowed
    assert exhausted.reason_code == RetryStopCode.EXHAUSTED.value
    assert exhausted.attempts == 3
    assert ledger.episode(key).repair_attempts == 2


def test_generated_attempt_id_remains_unique_after_fixed_clock_reset(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key()
    first = ledger.reserve(key, failure_class="mechanical", now=_START)
    ledger.record_accepted_progress(first, now=_START)
    second = ledger.reserve(key, failure_class="mechanical", now=_START)

    assert second.attempt_id is not None
    assert second.attempt_id != first.attempt_id
    assert ledger.episode(key).attempt_ids == (first.attempt_id, second.attempt_id)


def test_transient_budget_and_cas_reject_stale_summary(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key(action="sync-target")
    _, previous = ledger._read_with_bytes()

    first = ledger.reserve(key, failure_class="transient", now=_START, attempt_id="transient-1")
    ledger.record_failure(first, failure_code="read-failed", now=_START)
    second = ledger.reserve(
        key,
        failure_class="transient",
        now=_START + timedelta(seconds=1),
        attempt_id="transient-2",
    )
    ledger.record_failure(second, failure_code="read-failed", now=_START + timedelta(seconds=1))
    third = ledger.reserve(
        key,
        failure_class="transient",
        now=_START + timedelta(seconds=3),
        attempt_id="transient-3",
    )
    episode = ledger.record_failure(third, failure_code="read-failed", now=_START + timedelta(seconds=3))
    assert episode.total_attempts == 3
    assert episode.stop_code is RetryStopCode.EXHAUSTED

    stale = RetryLedgerSummary.empty("change-a").model_copy(update={"version": 1})
    with pytest.raises(RetryLedgerConflictError):
        ledger._commit_summary(previous, stale)


def test_acceptance_wait_allows_explicit_observation_without_reset(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key(action="observe-acceptance")
    at = _START

    for index in range(3):
        reservation = ledger.reserve(
            key,
            failure_class="acceptance",
            now=at,
            attempt_id=f"observation-{index}",
        )
        episode = ledger.record_failure(reservation, failure_code="unchanged", now=at)
        at = at + timedelta(seconds=1 if index == 0 else 2)

    assert episode.stop_code is RetryStopCode.ACCEPTANCE_WAIT
    assert episode.observation_attempts == 3
    assert episode.total_attempts == 3

    automatic = ledger.reserve(
        key,
        failure_class="acceptance",
        now=at + timedelta(days=1),
        attempt_id="observation-automatic-4",
    )
    assert not automatic.allowed
    assert automatic.reason_code == RetryStopCode.ACCEPTANCE_WAIT.value

    explicit = ledger.reserve(
        key,
        failure_class="acceptance",
        now=at + timedelta(days=1),
        attempt_id="observation-explicit",
        automatic=False,
    )
    assert explicit.allowed
    updated = ledger.record_success(explicit, now=at + timedelta(days=1))
    assert updated.total_attempts == 3
    assert updated.explicit_observations == 1
    assert updated.reset_count == 0
    assert updated.stop_code is RetryStopCode.ACCEPTANCE_WAIT


def test_unresolved_reservation_is_contained_until_an_outcome(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key()
    first = ledger.reserve(key, failure_class="mechanical", now=_START, attempt_id="in-flight")

    blocked = ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START + timedelta(seconds=10),
        attempt_id="replacement",
    )
    assert not blocked.allowed
    assert blocked.reason_code == RetryStopCode.CONTAINMENT.value
    assert ledger.episode(key).last_status == "contained"

    ledger.record_failure(first, failure_code="known-result", now=_START + timedelta(seconds=10))
    retry = ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START + timedelta(seconds=11),
        attempt_id="replacement",
    )
    assert retry.allowed


def test_verified_release_preserves_budget_for_worker_episode(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = RetryEpisodeKey.worker(
        "change-a",
        "builder-claim",
        _HEAD,
        contract_digest="c" * 64,
        outcome_id="OUT-001",
        task_lineage="TASK-001",
        procedure_class="builder",
        original_candidate="candidate-1",
    )
    original = ledger.reserve(key, failure_class="mechanical", now=_START, attempt_id="worker-1")
    ledger.record_failure(original, failure_code="builder-failed", now=_START)
    repair = ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START + timedelta(seconds=1),
        attempt_id="worker-2",
    )

    released = ledger.record_recovery_release_for_outcome("OUT-001", now=_START + timedelta(seconds=1))

    assert len(released) == 1
    assert released[0].total_attempts == 2
    assert released[0].repair_attempts == 1
    assert released[0].reset_count == 0
    assert released[0].last_status == "succeeded"
    next_repair = ledger.reserve(
        key,
        failure_class="mechanical",
        now=_START + timedelta(seconds=1),
        attempt_id="worker-3",
    )
    assert next_repair.allowed
    assert repair.attempt_id == "worker-2"


def test_reset_requires_accepted_progress_and_is_change_episode_scoped(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    affected = _engine_key(action="build")
    unrelated = _engine_key(action="check")
    first = ledger.reserve(affected, failure_class="mechanical", now=_START, attempt_id="affected-1")
    ledger.record_failure(first, failure_code="builder-failed", now=_START)
    other = ledger.reserve(unrelated, failure_class="mechanical", now=_START, attempt_id="unrelated-1")
    ledger.record_failure(other, failure_code="check-failed", now=_START)

    with pytest.raises(ValueError, match="accepted progress"):
        ledger.reset(affected, accepted_progress=False, now=_START)

    reset = ledger.reset(affected, accepted_progress=True, now=_START + timedelta(seconds=1))
    assert reset.total_attempts == 0
    assert reset.reset_count == 1
    assert reset.attempt_ids == ("affected-1",)
    assert ledger.episode(unrelated).total_attempts == 1
    next_attempt = ledger.reserve(
        affected,
        failure_class="mechanical",
        now=_START + timedelta(seconds=1),
        attempt_id="affected-2",
    )
    assert next_attempt.allowed


def test_corrupt_summary_fails_closed(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    ledger.summary_path.parent.mkdir(parents=True)
    ledger.summary_path.write_bytes(b"not-json")

    with pytest.raises(RetryLedgerCorruptError):
        ledger.read()


@pytest.mark.parametrize("count", [1, 2, 3, 7])
def test_legacy_failures_are_not_a_fresh_allowance(tmp_path: Path, count: int) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key()
    ledger.import_legacy_failures(key, count, now=_START)
    restarted = RetryLedger(tmp_path, "change-a")
    restarted.import_legacy_failures(key, count, now=_START + timedelta(days=1))
    episode = restarted.episode(key)
    assert episode.total_attempts == count
    assert episode.repair_attempts == count - 1
    assert not restarted.reserve(key, failure_class="mechanical", now=_START).allowed
    attempt = restarted.reserve(key, failure_class="mechanical", now=_START + timedelta(seconds=2))
    assert attempt.allowed is (count < 3)
    if attempt.allowed:
        assert attempt.attempts == count + 1


def test_legacy_failures_join_an_existing_unreset_ledger_once(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key()
    first = ledger.reserve(key, failure_class="mechanical", now=_START)
    ledger.record_failure(first, failure_code="failed", now=_START)
    imported = ledger.import_legacy_failures(key, 2, now=_START)
    assert imported.total_attempts == 3
    assert imported.legacy_failures == 2
    assert imported.stop_code is RetryStopCode.EXHAUSTED
    assert ledger.import_legacy_failures(key, 2, now=_START + timedelta(days=1)) == imported


def test_recovery_release_preserves_failed_backoff_and_fractional_clock(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key()
    at = _START + timedelta(microseconds=750000)
    original = ledger.reserve(key, failure_class="mechanical", now=at)
    failed = ledger.record_failure(original, failure_code="failed", now=at)
    assert ledger.record_recovery_release(original, now=at) == failed
    assert not ledger.reserve(key, failure_class="mechanical", now=at - timedelta(seconds=1)).allowed
    assert not ledger.reserve(key, failure_class="mechanical", now=at + timedelta(milliseconds=999)).allowed
    assert ledger.reserve(key, failure_class="mechanical", now=at + timedelta(seconds=1)).allowed


def test_old_accepted_result_cannot_reset_successor_episode(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = _engine_key()
    first = ledger.reserve(key, failure_class="mechanical", now=_START)
    ledger.record_accepted_progress(first, now=_START)
    second = ledger.reserve(key, failure_class="mechanical", now=_START)
    ledger.record_failure(second, failure_code="new-failure", now=_START)
    before = ledger.read()
    ledger.record_accepted_progress(first, now=_START)
    assert ledger.read() == before
    assert ledger.episode(key).repair_attempts == 0


def test_repair_commit_and_task_alias_keep_original_failed_episode(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    key = RetryEpisodeKey.worker(
        "change-a",
        "builder-claim",
        _HEAD,
        contract_digest="c" * 64,
        outcome_id="OUT-001",
        task_lineage="TASK-001",
        procedure_class="builder",
        original_candidate="original",
    )
    first = ledger.reserve(key, failure_class="mechanical", now=_START)
    ledger.record_failure(first, failure_code="first-code", now=_START)
    ledger.record_alias(key, alias_kind="task", value="renamed", now=_START)
    renamed = key.model_copy(update={"exact_head": "d" * 40, "task_lineage": "renamed", "original_candidate": "new"})
    second = ledger.reserve(renamed, failure_class="mechanical", now=_START + timedelta(seconds=1))
    assert second.episode_id == first.episode_id
    assert second.attempts == 2
    assert ledger.episode(renamed).key == key


def test_accepted_other_task_does_not_reset_failed_task_episode(tmp_path: Path) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    first_key = RetryEpisodeKey.worker(
        "change-a",
        "builder-claim",
        _HEAD,
        contract_digest="c" * 64,
        outcome_id="OUT-001",
        task_lineage="TASK-001",
        procedure_class="builder",
        original_candidate="candidate",
    )
    first = ledger.reserve(first_key, failure_class="mechanical", now=_START)
    ledger.record_failure(first, failure_code="failed-check", now=_START)
    other_key = first_key.model_copy(update={"task_lineage": "TASK-002"})
    other = ledger.reserve(other_key, failure_class="mechanical", now=_START)
    ledger.record_accepted_progress(other, now=_START)
    assert ledger.episode(first_key).total_attempts == 1
    assert ledger.episode(first_key).reset_count == 0
    assert ledger.episode(other_key).total_attempts == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [("exact_head", "d" * 40), ("target_head", "e" * 40), ("finalization_id", "final-2")],
)
def test_engine_contexts_do_not_share_exhausted_budget(tmp_path: Path, field: str, value: str) -> None:
    ledger = RetryLedger(tmp_path, "change-a")
    first_key = _engine_key(action="finalize")
    for index, seconds in enumerate((0, 1, 3)):
        now = _START + timedelta(seconds=seconds)
        attempt = ledger.reserve(first_key, failure_class="mechanical", now=now, attempt_id=f"old-{index}")
        ledger.record_failure(attempt, failure_code="failed-check", now=now)
    assert ledger.episode(first_key).stop_code is RetryStopCode.EXHAUSTED
    other_key = first_key.model_copy(update={field: value})
    other = ledger.reserve(
        other_key, failure_class="mechanical", now=_START + timedelta(seconds=10), attempt_id="new-context"
    )
    assert other.allowed
    assert other.attempts == 1
    assert other.episode_id != first_key.identity
    assert ledger.episode(first_key).stop_code is RetryStopCode.EXHAUSTED
    assert not ledger.reserve(first_key, failure_class="mechanical", now=_START + timedelta(days=1)).allowed
