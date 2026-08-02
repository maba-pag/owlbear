"""Behavioral coverage for target semantic authority admission."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban.target_admission import (
    TargetAdmissionCandidate,
    TargetAdmissionConflictError,
    TargetAdmissionRequest,
    TargetAdmissionValidationError,
    TargetAuthorityRegistry,
    TargetChallengeEntry,
)
from owlbear_kanban.target_authority import Outcome, PlanScopeKind, TargetAuthority, TaskPlanScope
from owlbear_kanban.target_runtime import StartTargetJobRequest, TargetRuntime


def _authority(*, title: str = "Target change") -> TargetAuthority:
    return TargetAuthority(
        change_id="target-change",
        title=title,
        outcomes=(
            Outcome(
                outcome_id="OUT-001",
                title="First outcome",
                promise="Deliver the first result",
                acceptance=("First result is visible",),
            ),
            Outcome(
                outcome_id="OUT-002",
                title="Second outcome",
                promise="Deliver the dependent result",
                acceptance=("Second result is visible",),
                dependency_ids=("OUT-001",),
            ),
        ),
        task_plan_scopes=(
            TaskPlanScope(scope_id="PLAN-001", kind=PlanScopeKind.OUTCOME, target_id="OUT-001"),
            TaskPlanScope(scope_id="PLAN-002", kind=PlanScopeKind.OUTCOME, target_id="OUT-002"),
        ),
    )


def _candidate(authority: TargetAuthority | None = None) -> TargetAdmissionCandidate:
    selected = authority or _authority()
    identities = (
        selected.change_id,
        *(item.outcome_id for item in selected.outcomes),
        *(item.scope_id for item in selected.task_plan_scopes),
    )
    return TargetAdmissionCandidate(
        authority=selected,
        challenge=tuple(
            TargetChallengeEntry(subject_id=identity, disposition="pass", evidence=f"evidence for {identity}")
            for identity in identities
        ),
        baseline=("uv run pytest -q",),
        known_limits=("No optional migration",),
        prepared_at="2026-08-04T00:00:00+00:00",
    )


def _request(registry: TargetAuthorityRegistry, candidate: TargetAdmissionCandidate) -> TargetAdmissionRequest:
    assessment = registry.validate(candidate)
    return TargetAdmissionRequest(
        candidate=candidate,
        approved_digest=assessment.authority_digest,
        approved_by="user",
        approved_at="2026-08-04T00:01:00+00:00",
    )


def test_admission_atomically_publishes_dependency_frontier_and_replays(tmp_path: Path) -> None:
    registry = TargetAuthorityRegistry(tmp_path / "target")
    candidate = _candidate()
    request = _request(registry, candidate)

    result = registry.admit(request)
    replay = registry.admit(request)

    assert result.replayed is False
    assert replay.model_copy(update={"replayed": False}) == result
    assert replay.replayed is True
    assert [item.predecessor_job_ids for item in result.runtime_state.jobs] == [(), (1,)]
    assert registry.list_authorities() == (candidate.authority,)
    assert registry.show_authority("target-change") == candidate.authority


def test_admission_replay_preserves_advanced_runtime_state(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    registry = TargetAuthorityRegistry(target_root)
    candidate = _candidate()
    request = _request(registry, candidate)
    registry.admit(request)
    runtime = TargetRuntime(candidate.authority, target_root / "changes/target-change")
    active = runtime.start_job(
        StartTargetJobRequest(
            job_id=1,
            attempt_id="attempt-one",
            claim_id="claim-one",
            owner_id="owner-one",
            reviewer_id="reviewer-one",
            process_id="123",
            started_at="2026-08-04T00:02:00+00:00",
            lease_expires_at="2026-08-04T01:02:00+00:00",
        )
    )

    replay = registry.admit(request)

    assert replay.replayed is True
    assert replay.runtime_state.jobs[0] == active.job
    assert replay.runtime_state.attempts == (active.attempt,)
    assert runtime.show_job(1) == active.job


def test_validation_rejects_incomplete_challenge_and_stale_approval(tmp_path: Path) -> None:
    registry = TargetAuthorityRegistry(tmp_path / "target")
    candidate = _candidate()
    incomplete = candidate.model_copy(update={"challenge": candidate.challenge[:-1]})

    with pytest.raises(TargetAdmissionValidationError, match="challenge coverage differs"):
        registry.validate(incomplete)

    stale = _request(registry, candidate).model_copy(update={"approved_digest": "b" * 64})
    with pytest.raises(TargetAdmissionValidationError, match="approval does not name"):
        registry.admit(stale)
    assert registry.list_authorities() == ()


def test_revision_archives_prior_authority_and_replaces_inactive_frontier(tmp_path: Path) -> None:
    registry = TargetAuthorityRegistry(tmp_path / "target")
    first = _candidate()
    initial = registry.admit(_request(registry, first))
    changed = _candidate(_authority(title="Changed target"))

    revised = registry.admit(_request(registry, changed))

    revision_root = tmp_path / "target/changes/target-change/revisions" / initial.receipt.authority_digest
    assert revised.authority == changed.authority
    assert registry.show_authority("target-change") == changed.authority
    assert (revision_root / "authority.json").is_file()
    assert (revision_root / "state.json").is_file()
    assert (revision_root / "admission.json").is_file()


def test_active_job_blocks_authority_revision(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    registry = TargetAuthorityRegistry(target_root)
    first = _candidate()
    registry.admit(_request(registry, first))
    runtime = TargetRuntime(first.authority, target_root / "changes/target-change")
    runtime.start_job(
        StartTargetJobRequest(
            job_id=1,
            attempt_id="attempt-one",
            claim_id="claim-one",
            owner_id="owner-one",
            reviewer_id="reviewer-one",
            process_id="123",
            started_at="2026-08-04T00:02:00+00:00",
            lease_expires_at="2026-08-04T01:02:00+00:00",
        )
    )
    changed = _candidate(_authority(title="Changed target"))

    with pytest.raises(TargetAdmissionConflictError, match="active target work blocks"):
        registry.admit(_request(registry, changed))


def test_validation_rejects_missing_or_duplicate_outcome_scope(tmp_path: Path) -> None:
    registry = TargetAuthorityRegistry(tmp_path / "target")
    authority = _authority()
    missing = authority.model_copy(update={"task_plan_scopes": authority.task_plan_scopes[:1]})
    duplicate = authority.model_copy(
        update={
            "task_plan_scopes": (
                *authority.task_plan_scopes,
                TaskPlanScope(scope_id="PLAN-003", kind=PlanScopeKind.OUTCOME, target_id="OUT-002"),
            )
        }
    )

    with pytest.raises(TargetAdmissionValidationError, match="active outcome plan scopes differ"):
        registry.validate(_candidate(missing))
    with pytest.raises(TargetAdmissionValidationError, match="exactly one task plan scope"):
        registry.validate(_candidate(duplicate))
