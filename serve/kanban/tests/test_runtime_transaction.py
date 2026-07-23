from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from owlbear_kanban.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionManifestError,
    TransactionParticipant,
    TransactionPathError,
)


@pytest.mark.parametrize("stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_recovery_completes_lifecycle_job_and_activity_participants(tmp_path: Path, stage: str) -> None:
    change_root = tmp_path / "change"
    work_root = tmp_path / "work"
    transaction = RuntimeTransaction(
        change_root,
        "lifecycle",
        (
            TransactionParticipant(work_root, Path("jobs/shape.yaml"), b"shape"),
            TransactionParticipant(work_root, Path("activity/shape.jsonl"), b'{"event":"started"}\n'),
        ),
    )

    def interrupt(current_stage: str) -> None:
        if current_stage == stage:
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="interrupted"):
        transaction.commit(failure=interrupt)

    RuntimeTransaction.recover_all(change_root, roots=(change_root, work_root))

    assert (work_root / "jobs/shape.yaml").read_bytes() == b"shape"
    assert (work_root / "activity/shape.jsonl").read_bytes() == b'{"event":"started"}\n'
    assert not list((change_root / ".runtime-transactions").glob("*.yaml"))


def test_transaction_rejects_conflicts_and_escaped_destinations_without_mutation(tmp_path: Path) -> None:
    root = tmp_path / "work"
    destination = root / "jobs/shape.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"committed")
    conflicting = RuntimeTransaction(
        tmp_path / "change",
        "conflict",
        (TransactionParticipant(root, Path("jobs/shape.yaml"), b"replacement"),),
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
    destination = work_root / "jobs/shape.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"expected")
    transaction = RuntimeTransaction(
        manifest_root,
        "replacement",
        (ReplacementTransactionParticipant(work_root, Path("jobs/shape.yaml"), b"expected", b"replacement"),),
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


def test_replacement_participant_rejects_conflicts_and_invalid_recovery_manifests(tmp_path: Path) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    destination = work_root / "jobs/shape.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"different")
    transaction = RuntimeTransaction(
        manifest_root,
        "replacement",
        (ReplacementTransactionParticipant(work_root, Path("jobs/shape.yaml"), b"expected", b"replacement"),),
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
    destination = work_root / "jobs/shape.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"expected")
    transaction = RuntimeTransaction(
        manifest_root,
        "replacement",
        (ReplacementTransactionParticipant(work_root, Path("jobs/shape.yaml"), b"expected", b"replacement"),),
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
    assert not (tmp_path / "outside/jobs/shape.yaml").exists()


def test_concurrent_processes_publish_one_immutable_participant_set(tmp_path: Path) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    command = (
        "from pathlib import Path\n"
        "from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionParticipant\n"
        f"RuntimeTransaction(Path({str(manifest_root)!r}), 'shared', "
        f"(TransactionParticipant(Path({str(work_root)!r}), Path('jobs/shape.yaml'), b'shape'),)).commit()\n"
    )
    processes = [subprocess.Popen([sys.executable, "-c", command]) for _ in range(2)]
    for process in processes:
        process.wait()

    assert [process.returncode for process in processes] == [0, 0]
    assert (work_root / "jobs/shape.yaml").read_bytes() == b"shape"
    assert not list((manifest_root / ".runtime-transactions").glob("*.yaml"))
