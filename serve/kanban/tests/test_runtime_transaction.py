from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from owlbear_kanban.runtime_transaction import (
    RuntimeTransaction,
    TransactionConflictError,
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
