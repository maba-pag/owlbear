from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from owlbear_delivery import AtomicIntegrationPreparation, DeliveryIntegrationCandidate
from owlbear_delivery.integration_verification import (
    INTEGRATION_VERIFICATION_PROFILE_PATH,
    IntegrationVerificationStatus,
    IntegrationVerificationStore,
    IntegrationVerifier,
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _profile(argv: tuple[str, ...], *, timeout_seconds: int = 30) -> bytes:
    content = {
        "schema_version": 1,
        "pass_environment": ["PATH", "HOME", "TMPDIR"],
        "steps": [
            {
                "step_id": "project-tests",
                "argv": list(argv),
                "cwd": ".",
                "timeout_seconds": timeout_seconds,
            }
        ],
    }
    return (json.dumps(content, indent=2) + "\n").encode()


def _repository(
    tmp_path: Path,
    argv: tuple[str, ...],
    *,
    timeout_seconds: int = 30,
) -> tuple[Path, str, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Verification Test")
    _git(repository, "config", "user.email", "verification@example.invalid")
    profile_path = repository / INTEGRATION_VERIFICATION_PROFILE_PATH
    profile_path.parent.mkdir(parents=True)
    profile_path.write_bytes(_profile(argv, timeout_seconds=timeout_seconds))
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    target_head = _git(repository, "rev-parse", "HEAD")
    _git(repository, "switch", "-c", "change-a")
    (repository / "product.txt").write_text("candidate\n", encoding="utf-8")
    _git(repository, "commit", "-am", "candidate")
    candidate_commit = _git(repository, "rev-parse", "HEAD")
    _git(repository, "update-ref", "refs/owlbear/integration-candidates/change-a", candidate_commit)
    return repository, target_head, candidate_commit


def _candidate(target_head: str, candidate_commit: str) -> DeliveryIntegrationCandidate:
    return DeliveryIntegrationCandidate(
        candidate_id="1" * 64,
        completion_id="2" * 64,
        change_id="change-a",
        package_id="3" * 64,
        authority_digest="4" * 64,
        runtime_digest="5" * 64,
        result_history_digest="6" * 64,
        reviewed_change_head=candidate_commit,
        integration_target="main",
        target_head=target_head,
        completion_path=".owlbear/completed/change-a",
        package_tree=candidate_commit,
    )


def _preparation(target_head: str, candidate_commit: str) -> AtomicIntegrationPreparation:
    return AtomicIntegrationPreparation(
        change_id="change-a",
        candidate_commit=candidate_commit,
        candidate_ref="refs/owlbear/integration-candidates/change-a",
        change_head=candidate_commit,
        integration_target="main",
        target_head=target_head,
    )


def _verifier(tmp_path: Path, repository: Path) -> IntegrationVerifier:
    target_root = tmp_path / "target"
    target_root.mkdir()
    return IntegrationVerifier(
        repository,
        tmp_path / "verification-worktrees",
        IntegrationVerificationStore(target_root),
    )


def test_verification_persists_exact_receipt_and_replays_without_execution(tmp_path: Path) -> None:
    marker = tmp_path / "executions.txt"
    script = (
        f"from pathlib import Path; p=Path({str(marker)!r}); p.write_text((p.read_text() if p.exists() else '')+'x')"
    )
    repository, target_head, candidate_commit = _repository(tmp_path, (sys.executable, "-c", script))
    verifier = _verifier(tmp_path, repository)
    candidate = _candidate(target_head, candidate_commit)
    preparation = _preparation(target_head, candidate_commit)

    first = verifier.verify(candidate, preparation)
    replayed = verifier.verify(candidate, preparation)

    assert first.status == IntegrationVerificationStatus.PASSED
    assert replayed == first
    assert marker.read_text(encoding="utf-8") == "x"
    assert not (tmp_path / "verification-worktrees" / first.request_id).exists()
    assert (tmp_path / "target/claims/integration-verification/requests" / f"{first.request_id}.json").is_file()
    assert (tmp_path / "target/claims/integration-verification/receipts" / f"{first.request_id}.json").is_file()


def test_concurrent_verification_executes_one_exact_request_once(tmp_path: Path) -> None:
    marker = tmp_path / "executions.txt"
    script = (
        "import time; from pathlib import Path; "
        f"p=Path({str(marker)!r}); time.sleep(0.1); p.write_text((p.read_text() if p.exists() else '')+'x')"
    )
    repository, target_head, candidate_commit = _repository(tmp_path, (sys.executable, "-c", script))
    verifier = _verifier(tmp_path, repository)
    candidate = _candidate(target_head, candidate_commit)
    preparation = _preparation(target_head, candidate_commit)

    with ThreadPoolExecutor(max_workers=2) as executor:
        receipts = tuple(executor.map(lambda _index: verifier.verify(candidate, preparation), range(2)))

    assert receipts[0] == receipts[1]
    assert receipts[0].status == IntegrationVerificationStatus.PASSED
    assert marker.read_text(encoding="utf-8") == "x"


def test_verification_rejects_candidate_profile_change_without_execution(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-run.txt"
    script = f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')"
    repository, target_head, _candidate_commit = _repository(tmp_path, (sys.executable, "-c", script))
    profile_path = repository / INTEGRATION_VERIFICATION_PROFILE_PATH
    profile_path.write_bytes(_profile((sys.executable, "-c", "raise SystemExit(0)")))
    _git(repository, "add", INTEGRATION_VERIFICATION_PROFILE_PATH)
    _git(repository, "commit", "-m", "rewrite verification authority")
    candidate_commit = _git(repository, "rev-parse", "HEAD")
    _git(repository, "update-ref", "refs/owlbear/integration-candidates/change-a", candidate_commit)

    receipt = _verifier(tmp_path, repository).verify(
        _candidate(target_head, candidate_commit),
        _preparation(target_head, candidate_commit),
    )

    assert receipt.status == IntegrationVerificationStatus.PROFILE_CHANGED
    assert not marker.exists()


def test_verification_failure_keeps_bounded_process_evidence(tmp_path: Path) -> None:
    script = "import sys; print('x' * 20000); print('y' * 20000, file=sys.stderr); raise SystemExit(3)"
    repository, target_head, candidate_commit = _repository(tmp_path, (sys.executable, "-c", script))

    receipt = _verifier(tmp_path, repository).verify(
        _candidate(target_head, candidate_commit),
        _preparation(target_head, candidate_commit),
    )

    assert receipt.status == IntegrationVerificationStatus.FAILED
    assert receipt.steps[0].exit_code == 3
    assert len(receipt.steps[0].stdout) <= 8_192
    assert len(receipt.steps[0].stderr) <= 8_192
    assert "output truncated" in receipt.steps[0].stdout


def test_verification_timeout_kills_the_entire_process_group(tmp_path: Path) -> None:
    marker = tmp_path / "grandchild-survived.txt"
    grandchild = f"import time; from pathlib import Path; time.sleep(2); Path({str(marker)!r}).write_text('ran')"
    parent = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(10)"
    repository, target_head, candidate_commit = _repository(
        tmp_path,
        (sys.executable, "-c", parent),
        timeout_seconds=1,
    )
    started_at = time.monotonic()

    receipt = _verifier(tmp_path, repository).verify(
        _candidate(target_head, candidate_commit),
        _preparation(target_head, candidate_commit),
    )

    elapsed = time.monotonic() - started_at
    time.sleep(1.25)
    assert receipt.status == IntegrationVerificationStatus.TIMED_OUT
    assert elapsed < 1.75
    assert not marker.exists()
