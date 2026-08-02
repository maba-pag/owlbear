"""Exact-commit proof checkouts for target review."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

from owlbear_kanban import ProofCheckoutDiagnosticCode, ProofCheckoutManager, TargetJob


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "test@example.com")
    _git(repository, "config", "user.name", "Test")
    (repository / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repository, "add", "tracked.txt")
    _git(repository, "commit", "-q", "-m", "initial")
    authority = repository / ".owlbear/target/changes/change-one"
    authority.mkdir(parents=True)
    (authority / "authority.json").write_text('{"change_id":"change-one"}\n', encoding="utf-8")
    return repository, _git(repository, "rev-parse", "HEAD")


def _job(job_id: int = 27) -> TargetJob:
    return TargetJob(
        job_id=job_id,
        kind="assembly",
        change_id="change-one",
        authority_digest="a" * 64,
        work_item_id="change-one",
        plan_scope_id="PLAN-001",
        created_at="2026-08-02T00:00:00Z",
    )


def test_materialize_uses_exact_commit_and_immutable_target_authority(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "proof")

    result = manager.materialize(_job(), "HEAD", environment={"TOOLCHAIN": "uv"}, replacements=("remote service",))

    assert result.diagnostic is None
    assert result.checkout is not None
    assert result.checkout.commit == commit
    assert result.checkout.target == "change-one"
    assert (result.checkout.authority / "authority.json").read_text(encoding="utf-8")
    assert not (result.checkout.authority / "target-runtime").exists()
    assert stat.S_IMODE((result.checkout.authority / "authority.json").stat().st_mode) & 0o222 == 0
    assert manager.validate(27, commit) is None


def test_validate_rejects_candidate_and_authority_mutation(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "proof")
    result = manager.materialize(_job(), commit)
    assert result.checkout is not None

    assert manager.validate(27, "HEAD").code is ProofCheckoutDiagnosticCode.COMMIT_MISMATCH
    tracked = result.checkout.checkout / "tracked.txt"
    tracked.chmod(stat.S_IMODE(tracked.stat().st_mode) | stat.S_IWUSR)
    tracked.write_text("changed\n", encoding="utf-8")
    assert manager.validate(27, commit).code is ProofCheckoutDiagnosticCode.TRACKED_MUTATION

    _git(result.checkout.checkout, "restore", "tracked.txt")
    authority = result.checkout.authority / "authority.json"
    authority.chmod(stat.S_IMODE(authority.stat().st_mode) | stat.S_IWUSR)
    authority.write_text("{}\n", encoding="utf-8")
    assert manager.validate(27, commit).code is ProofCheckoutDiagnosticCode.AUTHORITY_MUTATION


def test_snapshot_restores_same_target_claim_and_authority(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "proof")
    job = _job()
    result = manager.materialize(job, commit, replacements=("remote service",))
    assert result.checkout is not None
    snapshot = manager.snapshot(job.job_id)
    assert snapshot is not None

    manager.cleanup(job.job_id)

    assert manager.restore(job, snapshot)
    restored = manager.existing(job.job_id)
    assert restored is not None
    assert restored.commit == commit
    assert restored.authority_digest == snapshot.authority_digest


def test_materialize_rejects_missing_commit_or_authority(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "proof")

    missing_commit = manager.materialize(_job(), "f" * 40)
    assert missing_commit.diagnostic is not None
    assert missing_commit.diagnostic.code is ProofCheckoutDiagnosticCode.COMMIT_MISSING

    (repository / ".owlbear/target/changes/change-one/authority.json").unlink()
    missing_authority = manager.materialize(_job(job_id=28), commit)
    assert missing_authority.diagnostic is not None
    assert missing_authority.diagnostic.code is ProofCheckoutDiagnosticCode.SETUP_FAILED
