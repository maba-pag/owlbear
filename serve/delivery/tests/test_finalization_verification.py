from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from owlbear_delivery.finalization_verification import (
    FinalizationVerificationStatus,
    FinalizationVerificationStore,
    FinalizationVerifier,
)
from owlbear_delivery.integration_verification import IntegrationVerificationProfile, IntegrationVerificationStep


def _git(repository: Path, *arguments: str, check: bool = True) -> str:
    result = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Finalization Test")
    _git(repository, "config", "user.email", "finalization@example.com")
    (repository / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repository, "add", "tracked.txt")
    _git(repository, "commit", "-m", "initial")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repository, _git(repository, "rev-parse", "HEAD")


def _profile(script: str) -> IntegrationVerificationProfile:
    return IntegrationVerificationProfile(
        schema_version=1,
        pass_environment=("FINALIZATION_TEST_ENV",),
        steps=(
            IntegrationVerificationStep(
                step_id="proof",
                argv=(sys.executable, "-c", script),
                cwd=".",
                timeout_seconds=5,
            ),
        ),
    )


def _run(
    repository: Path,
    head: str,
    profile: IntegrationVerificationProfile,
) -> tuple[FinalizationVerifier, object]:
    store = FinalizationVerificationStore(repository / ".runtime")
    verifier = FinalizationVerifier(repository, store)
    receipt = verifier.run(
        change_id="finalization-change",
        worktree=repository,
        branch="main",
        exact_head=head,
        target_ref="refs/remotes/origin/main",
        target_head=head,
        profile_digest="a" * 64,
        profile=profile,
    )
    return verifier, receipt


def test_finalization_verifier_runs_exact_profile_and_replays_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository, head = _repository(tmp_path)
    monkeypatch.setenv("FINALIZATION_TEST_ENV", "visible")

    _verifier, receipt = _run(
        repository,
        head,
        _profile("import os; print(os.environ.get('FINALIZATION_TEST_ENV', 'missing'))"),
    )

    assert receipt.status == FinalizationVerificationStatus.PASSED
    assert receipt.clean is True
    assert receipt.observed_head == head
    assert receipt.steps[0].status.value == "passed"
    assert receipt.steps[0].stdout == "visible\n"

    replay = _run(
        repository,
        head,
        _profile("import os; print(os.environ.get('FINALIZATION_TEST_ENV', 'missing'))"),
    )[1]
    assert replay == receipt


def test_finalization_verifier_rejects_dirty_worktree(tmp_path: Path) -> None:
    repository, head = _repository(tmp_path)
    (repository / "untracked.txt").write_text("dirty\n", encoding="utf-8")

    _verifier, receipt = _run(repository, head, _profile("print('should not run')"))

    assert receipt.status == FinalizationVerificationStatus.WORKTREE_CHANGED
    assert receipt.clean is False
    assert receipt.steps[0].step_id == "preflight"


def test_finalization_verifier_records_worktree_mutation(tmp_path: Path) -> None:
    repository, head = _repository(tmp_path)

    _verifier, receipt = _run(
        repository,
        head,
        _profile("from pathlib import Path; Path('generated.txt').write_text('changed')"),
    )

    assert receipt.status == FinalizationVerificationStatus.WORKTREE_CHANGED
    assert receipt.clean is False
    assert "changed tracked or untracked" in receipt.diagnostics[-1]


def test_finalization_verifier_rejects_target_move_during_proof(tmp_path: Path, monkeypatch) -> None:
    repository, head = _repository(tmp_path)
    store = FinalizationVerificationStore(repository / ".runtime")
    verifier = FinalizationVerifier(repository, store)
    calls = 0

    def resolve_target(_target_ref: str) -> str:
        nonlocal calls
        calls += 1
        return head if calls == 1 else "f" * 40

    monkeypatch.setattr(verifier, "_resolve_target_head", resolve_target)  # noqa: SLF001

    receipt = verifier.run(
        change_id="finalization-change",
        worktree=repository,
        branch="main",
        exact_head=head,
        target_ref="refs/remotes/origin/main",
        target_head=head,
        profile_digest="a" * 64,
        profile=_profile("pass"),
    )

    assert receipt.status == FinalizationVerificationStatus.TARGET_CHANGED
    assert receipt.clean is True
    assert "target changed during finalization proof" in receipt.diagnostics[-1]


def test_finalization_verifier_rejects_missing_cached_target(tmp_path: Path) -> None:
    repository, head = _repository(tmp_path)
    _git(repository, "update-ref", "-d", "refs/remotes/origin/main")
    store = FinalizationVerificationStore(repository / ".runtime")
    verifier = FinalizationVerifier(repository, store)

    receipt = verifier.run(
        change_id="finalization-change",
        worktree=repository,
        branch="main",
        exact_head=head,
        target_ref="refs/remotes/origin/main",
        target_head=head,
        profile_digest="a" * 64,
        profile=_profile("pass"),
    )

    assert receipt.status == FinalizationVerificationStatus.TARGET_CHANGED
    assert receipt.steps[0].step_id == "preflight"
    assert "changed before finalization proof" in receipt.diagnostics[0]


def test_finalization_verification_replay_preserves_observation_and_scope(tmp_path: Path) -> None:
    repository, head = _repository(tmp_path)
    store = FinalizationVerificationStore(repository / ".runtime")
    verifier = FinalizationVerifier(repository, store)
    observed_at = datetime(2026, 8, 11, 13, tzinfo=UTC)

    first = verifier.run(
        change_id="finalization-change",
        worktree=repository,
        branch="main",
        exact_head=head,
        target_ref="refs/remotes/origin/main",
        target_head=head,
        profile_digest="a" * 64,
        profile=_profile("pass"),
        target_observed_at=observed_at,
    )
    replay = verifier.run(
        change_id="finalization-change",
        worktree=repository,
        branch="main",
        exact_head=head,
        target_ref="refs/remotes/origin/main",
        target_head=head,
        profile_digest="a" * 64,
        profile=_profile("pass"),
        target_observed_at=datetime(2026, 8, 12, 13, tzinfo=UTC),
    )

    assert replay == first
    assert replay.target_observed_at == observed_at
    assert replay.proof_scope.value == "change-head-profile"
