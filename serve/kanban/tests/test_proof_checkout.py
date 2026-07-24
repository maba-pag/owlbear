from __future__ import annotations

import subprocess
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
    assert "job_id: 27" in checkout.manifest.read_text(encoding="utf-8")
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
