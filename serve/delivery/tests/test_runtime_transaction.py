from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from owlbear_delivery.runtime_transaction import (
    MoveTransactionParticipant,
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionManifestError,
    TransactionParticipant,
    TransactionPathError,
)
from owlbear_delivery.storage_io import locked_roots


def test_locked_roots_rejects_symlink_roots_and_lock_files(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    symlink_root = tmp_path / "symlink-root"
    symlink_root.symlink_to(root, target_is_directory=True)

    with pytest.raises(ValueError, match="must not be a symlink"), locked_roots((symlink_root,)):
        pass

    (root / ".storage.lock").symlink_to(tmp_path / "outside")
    with pytest.raises(OSError), locked_roots((root,)):
        pass


@pytest.mark.parametrize("stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_recovery_completes_lifecycle_job_and_activity_participants(tmp_path: Path, stage: str) -> None:
    change_root = tmp_path / "change"
    work_root = tmp_path / "work"
    transaction = RuntimeTransaction(
        change_root,
        "lifecycle",
        (
            TransactionParticipant(work_root, Path("jobs/plan.yaml"), b"plan"),
            TransactionParticipant(work_root, Path("activity/plan.jsonl"), b'{"event":"started"}\n'),
        ),
    )

    def interrupt(current_stage: str) -> None:
        if current_stage == stage:
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="interrupted"):
        transaction.commit(failure=interrupt)

    RuntimeTransaction.recover_all(change_root, roots=(change_root, work_root))

    assert (work_root / "jobs/plan.yaml").read_bytes() == b"plan"
    assert (work_root / "activity/plan.jsonl").read_bytes() == b'{"event":"started"}\n'
    assert not list((change_root / ".runtime-transactions").glob("*.yaml"))


@pytest.mark.parametrize(
    "interruption",
    ["before-publication", "after-first-publication", "before-manifest-cleanup", "during-replay"],
)
def test_recovery_converges_graph_job_receipt_activity_and_invalidation_participants(
    tmp_path: Path,
    interruption: str,
) -> None:
    change_root = tmp_path / "change"
    work_root = tmp_path / "work"
    active_job = work_root / "jobs/1.yaml"
    archived_job = work_root / "archive/1.yaml"
    prior_receipt = change_root / "receipts/prior.yaml"
    prior_activity = work_root / "activity/prior.jsonl"
    active_job.parent.mkdir(parents=True)
    prior_receipt.parent.mkdir(parents=True)
    prior_activity.parent.mkdir(parents=True)
    active_job.write_bytes(b"active-job")
    prior_receipt.write_bytes(b"prior-receipt")
    prior_activity.write_bytes(b"prior-activity\n")
    transaction = RuntimeTransaction(
        change_root,
        "complete-publication",
        (
            MoveTransactionParticipant(
                work_root,
                Path("jobs/1.yaml"),
                Path("archive/1.yaml"),
                b"active-job",
                b"archived-job",
            ),
            TransactionParticipant(change_root, Path("delivery/graph.yaml"), b"graph"),
            TransactionParticipant(change_root, Path("receipts/current.yaml"), b"receipt"),
            TransactionParticipant(work_root, Path("activity/current.jsonl"), b"activity\n"),
            TransactionParticipant(work_root, Path("invalidations/current.yaml"), b"invalidation"),
        ),
    )

    def interrupt(stage: str) -> None:
        if stage == interruption:
            message = "interrupted"
            raise RuntimeError(message)

    if interruption == "during-replay":
        with pytest.raises(RuntimeError, match="interrupted"):
            transaction.commit(
                failure=lambda stage: (
                    (_ for _ in ()).throw(RuntimeError("interrupted")) if stage == "before-publication" else None
                )
            )
        with pytest.raises(RuntimeError, match="interrupted"):
            transaction.commit(
                failure=lambda stage: (
                    (_ for _ in ()).throw(RuntimeError("interrupted")) if stage == "after-first-publication" else None
                )
            )
    else:
        with pytest.raises(RuntimeError, match="interrupted"):
            transaction.commit(failure=interrupt)

    assert active_job.exists() is not archived_job.exists()

    roots = (change_root, work_root)
    RuntimeTransaction.recover_all(change_root, roots=roots)
    RuntimeTransaction.recover_all(change_root, roots=roots)

    assert not active_job.exists()
    assert archived_job.read_bytes() == b"archived-job"
    assert (change_root / "delivery/graph.yaml").read_bytes() == b"graph"
    assert (change_root / "receipts/current.yaml").read_bytes() == b"receipt"
    assert (work_root / "activity/current.jsonl").read_bytes() == b"activity\n"
    assert (work_root / "invalidations/current.yaml").read_bytes() == b"invalidation"
    assert prior_receipt.read_bytes() == b"prior-receipt"
    assert prior_activity.read_bytes() == b"prior-activity\n"
    assert not list((change_root / ".runtime-transactions").glob("*.yaml"))


def test_transaction_rejects_conflicts_and_escaped_destinations_without_mutation(tmp_path: Path) -> None:
    root = tmp_path / "work"
    destination = root / "jobs/plan.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"committed")
    conflicting = RuntimeTransaction(
        tmp_path / "change",
        "conflict",
        (TransactionParticipant(root, Path("jobs/plan.yaml"), b"replacement"),),
    )
    escaped = RuntimeTransaction(
        tmp_path / "change",
        "escaped",
        (TransactionParticipant(root, Path("../outside.yaml"), b"unsafe"),),
    )

    with pytest.raises(TransactionConflictError):
        conflicting.commit()
    with pytest.raises(TransactionPathError):
        escaped.commit()

    assert destination.read_bytes() == b"committed"
    assert not (tmp_path / "outside.yaml").exists()


@pytest.mark.parametrize("stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_replacement_participant_recovers_and_replays(tmp_path: Path, stage: str) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    destination = work_root / "jobs/plan.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"expected")
    transaction = RuntimeTransaction(
        manifest_root,
        "replacement",
        (ReplacementTransactionParticipant(work_root, Path("jobs/plan.yaml"), b"expected", b"replacement"),),
    )

    def interrupt(current_stage: str) -> None:
        if current_stage == stage:
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="interrupted"):
        transaction.commit(failure=interrupt)

    RuntimeTransaction.recover_all(manifest_root, roots=(manifest_root, work_root))
    RuntimeTransaction.recover_all(manifest_root, roots=(manifest_root, work_root))

    assert destination.read_bytes() == b"replacement"
    assert not list((manifest_root / ".runtime-transactions").glob("*.yaml"))


def test_abort_restores_exact_prepublication_state_for_mixed_participants(tmp_path: Path) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    immutable = work_root / "evidence/existing.yaml"
    replacement = work_root / "jobs/1.yaml"
    move_source = work_root / "jobs/2.yaml"
    move_destination = work_root / "archive/2.yaml"
    immutable.parent.mkdir(parents=True)
    replacement.parent.mkdir(parents=True)
    immutable.write_bytes(b"existing")
    replacement.write_bytes(b"before")
    move_source.write_bytes(b"active")
    transaction = RuntimeTransaction(
        manifest_root,
        "abort-mixed",
        (
            TransactionParticipant(work_root, Path("evidence/existing.yaml"), b"existing"),
            ReplacementTransactionParticipant(work_root, Path("jobs/1.yaml"), b"before", b"after"),
            MoveTransactionParticipant(
                work_root,
                Path("jobs/2.yaml"),
                Path("archive/2.yaml"),
                b"active",
                b"archived",
            ),
        ),
    )

    def interrupt(stage: str) -> None:
        if stage == "before-manifest-cleanup":
            message = "handled failure"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="handled failure"):
        transaction.commit(failure=interrupt)
    transaction.abort()

    assert immutable.read_bytes() == b"existing"
    assert replacement.read_bytes() == b"before"
    assert move_source.read_bytes() == b"active"
    assert not move_destination.exists()
    assert not list((manifest_root / ".runtime-transactions").glob("*.yaml"))


def test_replacement_participant_rejects_conflicts_and_invalid_recovery_manifests(tmp_path: Path) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    destination = work_root / "jobs/plan.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"different")
    transaction = RuntimeTransaction(
        manifest_root,
        "replacement",
        (ReplacementTransactionParticipant(work_root, Path("jobs/plan.yaml"), b"expected", b"replacement"),),
    )

    with pytest.raises(TransactionConflictError):
        transaction.commit()
    assert destination.read_bytes() == b"different"

    manifest_directory = manifest_root / ".runtime-transactions"
    manifest_directory.mkdir(parents=True, exist_ok=True)
    (manifest_directory / "malformed.yaml").write_text("schema_version: 2\nparticipants: [bad]\n", encoding="utf-8")

    with pytest.raises(TransactionManifestError):
        RuntimeTransaction.recover_all(manifest_root, roots=(manifest_root, work_root))
    assert destination.read_bytes() == b"different"


@pytest.mark.parametrize("alteration", ["digest", "unsafe-root"])
def test_replacement_recovery_rejects_altered_or_unsafe_manifests(tmp_path: Path, alteration: str) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    destination = work_root / "jobs/plan.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"expected")
    transaction = RuntimeTransaction(
        manifest_root,
        "replacement",
        (ReplacementTransactionParticipant(work_root, Path("jobs/plan.yaml"), b"expected", b"replacement"),),
    )

    def interrupt(current_stage: str) -> None:
        if current_stage == "before-publication":
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="interrupted"):
        transaction.commit(failure=interrupt)

    manifest_path = manifest_root / ".runtime-transactions/replacement.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    participant = manifest["participants"][0]
    if alteration == "digest":
        participant["replacement_sha256"] = "0" * 64
    else:
        participant["root"] = str(tmp_path / "outside")
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    expected_error = TransactionManifestError if alteration == "digest" else TransactionPathError
    with pytest.raises(expected_error):
        RuntimeTransaction.recover_all(manifest_root, roots=(manifest_root, work_root))

    assert destination.read_bytes() == b"expected"
    assert not (tmp_path / "outside/jobs/plan.yaml").exists()


def test_concurrent_processes_publish_one_immutable_participant_set(tmp_path: Path) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    command = (
        "from pathlib import Path\n"
        "from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionParticipant\n"
        f"RuntimeTransaction(Path({str(manifest_root)!r}), 'shared', "
        f"(TransactionParticipant(Path({str(work_root)!r}), Path('jobs/plan.yaml'), b'plan'),)).commit()\n"
    )
    processes = [subprocess.Popen([sys.executable, "-c", command]) for _ in range(2)]
    for process in processes:
        process.wait()

    assert [process.returncode for process in processes] == [0, 0]
    assert (work_root / "jobs/plan.yaml").read_bytes() == b"plan"
    assert not list((manifest_root / ".runtime-transactions").glob("*.yaml"))
