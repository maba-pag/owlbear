from __future__ import annotations

import subprocess
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_kanban import JobRecord, ProofCheckoutDiagnosticCode, ProofCheckoutManager
from owlbear_kanban.runtime_query import RuntimeQuery


class _History:
    pass


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init")
    _git(repository, "config", "user.name", "Proof Test")
    _git(repository, "config", "user.email", "proof@example.test")
    tracked = repository / "tracked.txt"
    tracked.write_text("proof\n", encoding="utf-8")
    _git(repository, "add", "tracked.txt")
    _git(repository, "commit", "-m", "proof")
    authority = repository / ".owlbear/changes/proof-change"
    authority.mkdir(parents=True)
    (authority / "plan.yaml").write_text("mode: verification-only\n", encoding="utf-8")
    return repository, _git(repository, "rev-parse", "HEAD")


def _job(kind: str = "accept", job_id: int = 27) -> JobRecord:
    return JobRecord.model_validate(
        {
            "schema_version": 1,
            "job_id": job_id,
            "kind": kind,
            "priority": 1,
            "created_at": "2026-07-24T00:00:00Z",
            "updated_at": "2026-07-24T00:00:00Z",
            "change_id": "proof-change",
            "delivery_digest": "a" * 64,
            "target_node_id": "DN-004",
            "packet_id": "DN-004-PK-001" if kind == "build" else None,
        }
    )


def test_materialize_uses_exact_commit_read_only_checkout_and_manifest(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "scratch" / "proof")

    result = manager.materialize(
        _job(), commit, environment={"TOOLCHAIN": "uv"}, replacements=("temporary repository",)
    )

    assert result.diagnostic is None
    assert result.checkout is not None
    checkout = result.checkout
    assert checkout.root == tmp_path / "scratch" / "proof" / "27"
    assert _git(checkout.checkout, "rev-parse", "HEAD") == commit
    assert (checkout.authority / "plan.yaml").read_text(encoding="utf-8") == "mode: verification-only\n"
    assert len(checkout.authority_digest) == 64
    assert "job_id: 27" in checkout.manifest.read_text(encoding="utf-8")
    assert "authority_digest:" in checkout.manifest.read_text(encoding="utf-8")
    assert checkout.authority_digest in checkout.manifest.read_text(encoding="utf-8").replace("\n", "")
    assert "TOOLCHAIN: uv" in checkout.manifest.read_text(encoding="utf-8")
    assert "temporary repository" in checkout.manifest.read_text(encoding="utf-8")
    with pytest.raises(PermissionError):
        (checkout.checkout / "tracked.txt").write_text("changed\n", encoding="utf-8")


def test_materialize_resolves_symbolic_commit_to_canonical_manifest_sha(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "scratch" / "proof")

    result = manager.materialize(_job(), "HEAD")

    assert result.diagnostic is None
    assert result.checkout is not None
    assert result.checkout.commit == commit
    assert f"commit: {commit}" in result.checkout.manifest.read_text(encoding="utf-8")


def test_validate_rejects_revision_mismatch_and_tracked_mutation(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "scratch" / "proof")
    result = manager.materialize(_job(), commit)
    assert result.checkout is not None

    mismatch = manager.validate(27, "HEAD")
    assert mismatch is not None
    assert mismatch.code is ProofCheckoutDiagnosticCode.COMMIT_MISMATCH

    tracked = result.checkout.checkout / "tracked.txt"
    tracked.chmod(stat.S_IMODE(tracked.stat().st_mode) | stat.S_IWUSR)
    tracked.write_text("changed\n", encoding="utf-8")

    mutation = manager.validate(27, commit)
    assert mutation is not None
    assert mutation.code is ProofCheckoutDiagnosticCode.TRACKED_MUTATION

    other = repository / "other.txt"
    other.write_text("other\n", encoding="utf-8")
    _git(repository, "add", "other.txt")
    _git(repository, "commit", "-m", "other")
    mismatch = manager.validate(27, _git(repository, "rev-parse", "HEAD"))
    assert mismatch is not None
    assert mismatch.code is ProofCheckoutDiagnosticCode.COMMIT_MISMATCH


def test_validate_rejects_authority_sidecar_mutation(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "scratch" / "proof")
    result = manager.materialize(_job(), commit)
    assert result.checkout is not None

    plan = result.checkout.authority / "plan.yaml"
    plan.chmod(stat.S_IMODE(plan.stat().st_mode) | stat.S_IWUSR)
    plan.write_text("mode: build\n", encoding="utf-8")

    mutation = manager.validate(27, commit)
    assert mutation is not None
    assert mutation.code is ProofCheckoutDiagnosticCode.AUTHORITY_MUTATION


@pytest.mark.parametrize(
    ("job", "commit", "proof_root", "expected"),
    [
        (_job(kind="build"), "a" * 40, "proof", ProofCheckoutDiagnosticCode.PATH_UNSAFE),
        (_job(), "f" * 40, "proof", ProofCheckoutDiagnosticCode.COMMIT_MISSING),
    ],
)
def test_materialize_rejects_ineligible_or_missing_commit_without_checkout(
    tmp_path: Path, job: JobRecord, commit: str, proof_root: str, expected: ProofCheckoutDiagnosticCode
) -> None:
    repository, _head = _repository(tmp_path)
    root = tmp_path / "scratch" / proof_root

    result = ProofCheckoutManager(repository, root).materialize(job, commit)

    assert result.checkout is None
    assert result.diagnostic is not None
    assert result.diagnostic.code is expected
    assert not root.exists()


def test_materialize_rejects_symlinked_or_unusable_proof_root(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    symlink = tmp_path / "scratch" / "proof"
    symlink.parent.mkdir()
    symlink.symlink_to(outside, target_is_directory=True)

    unsafe = ProofCheckoutManager(repository, symlink).materialize(_job(), commit)
    assert unsafe.diagnostic is not None
    assert unsafe.diagnostic.code is ProofCheckoutDiagnosticCode.PATH_UNSAFE
    assert not (outside / "27").exists()

    unusable = tmp_path / "unusable"
    unusable.write_text("not a directory", encoding="utf-8")
    failed = ProofCheckoutManager(repository, unusable).materialize(_job(), commit)
    assert failed.diagnostic is not None
    assert failed.diagnostic.code is ProofCheckoutDiagnosticCode.SETUP_FAILED


def test_materialize_preserves_existing_same_job_root(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    proof_root = tmp_path / "scratch" / "proof"
    existing = proof_root / "27"
    existing.mkdir(parents=True)
    marker = existing / "concurrent-owner"
    marker.write_text("active\n", encoding="utf-8")

    result = ProofCheckoutManager(repository, proof_root).materialize(_job(), commit)

    assert result.checkout is None
    assert result.diagnostic is not None
    assert result.diagnostic.code is ProofCheckoutDiagnosticCode.SETUP_FAILED
    assert marker.read_text(encoding="utf-8") == "active\n"


def test_cleanup_is_idempotent_and_health_reports_leftover_checkout(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "scratch" / "proof")
    result = manager.materialize(_job(), commit)
    assert result.checkout is not None
    assert manager.health_paths() == ("27",)

    query = RuntimeQuery(
        SimpleNamespace(source_dir=tmp_path / "change"),
        tmp_path / "work",
        _History(),
        manager,
    )
    findings = query.work_health(limit=10).findings

    assert findings[0].code == "ERR_WORK_PROOF_CHECKOUT_ORPHAN"
    manager.cleanup(27)
    manager.cleanup(27)
    assert not result.checkout.root.exists()
    assert manager.health_paths() == ()


def test_snapshot_restores_exact_checkout_manifest_after_cleanup(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "scratch" / "proof")
    job = _job()
    created = manager.materialize(
        job,
        commit,
        environment={"TOOLCHAIN": "uv"},
        replacements=("temporary repository",),
    )
    assert created.checkout is not None
    manifest_before = created.checkout.manifest.read_bytes()
    snapshot = manager.snapshot(job.job_id)
    assert snapshot is not None

    manager.cleanup(job.job_id)
    restored = manager.restore(job, snapshot)

    assert restored
    current = manager.existing(job.job_id)
    assert current is not None
    assert current.commit == commit
    assert current.manifest.read_bytes() == manifest_before


def test_snapshot_restore_rejects_changed_live_authority(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    manager = ProofCheckoutManager(repository, tmp_path / "scratch" / "proof")
    job = _job()
    created = manager.materialize(job, commit)
    assert created.checkout is not None
    snapshot = manager.snapshot(job.job_id)
    assert snapshot is not None
    manager.cleanup(job.job_id)
    (repository / ".owlbear/changes/proof-change/plan.yaml").write_text("mode: build\n", encoding="utf-8")

    assert not manager.restore(job, snapshot)
    assert manager.existing(job.job_id) is None
