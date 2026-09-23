from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from owlbear_delivery.change_workspace import (
    AdoptExternalHead,
    CapacityLedger,
    ChangeCoordination,
    ChangeDesignPackageSnapshotReceipt,
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeFinalizationAttempt,
    ChangeWorkspaceManager,
    ChangeWorktreeAttentionCode,
    ChangeWorktreeAttentionError,
    ChangeWriter,
    CoordinationConflictError,
    PortfolioCoordinator,
    PreservationFenceError,
    PreservationPathProvenance,
    PreservationProvenanceEvidence,
    PreservationRejectedError,
    PromoteExternalHead,
    PublicationBaselineUnavailableError,
    PublicationLease,
    RecoverOutOfBandHead,
    SyncChangeWithTarget,
    UnavailablePreservationProvenanceProvider,
    WriterIdentity,
    WorktreePreservationReceipt,
)
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RecoveryEvidence,
    RecoveryEvidenceReference,
    RecoveryIntent,
    RecoveryInvocation,
    RecoveryInvocationRequest,
    RecoveryReceipt,
    digest,
    journal_path,
)
from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionParticipant, write_contained


def _coordination(root: Path, change_id: str) -> ChangeCoordination:
    return ChangeCoordination(
        change_id=change_id,
        branch=f"owlbear/change/{change_id}",
        worktree_path=root / "worktrees" / change_id,
        integration_target="main",
        target_head="a" * 40,
        last_reviewed_commit="a" * 40,
    )


def _identity(change_id: str) -> WriterIdentity:
    return WriterIdentity(
        attempt_id=f"attempt-{change_id}",
        claim_id=f"claim-{change_id}",
        actor_id="builder",
        process_id=f"process-{change_id}",
        claimed_at="2026-08-02T00:01:00Z",
    )


def test_portfolio_coordinates_independent_changes_but_rejects_second_writer(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state")
    coordinator.register(_coordination(tmp_path, "change-a"))
    coordinator.register(_coordination(tmp_path, "change-b"))
    first = coordinator.acquire(
        "change-a",
        ChangeWriter(**_identity("change-a").model_dump(), job_id=1, kind="build"),
    )
    second = coordinator.acquire(
        "change-b",
        ChangeWriter(**_identity("change-b").model_dump(), job_id=2, kind="build"),
    )

    assert first.writer is not None
    assert second.writer is not None
    with pytest.raises(CoordinationConflictError, match="active writer"):
        coordinator.acquire(
            "change-a",
            ChangeWriter(**_identity("change-a").model_dump(), job_id=3, kind="build"),
        )


@pytest.mark.parametrize("damage", ["missing", "malformed", "identity"])
def test_runtime_custody_guard_rejects_unreadable_coordination(tmp_path: Path, damage: str) -> None:
    coordinator = PortfolioCoordinator(tmp_path)
    path = tmp_path / "coordination/changes/change-a.json"
    coordinator.register(_coordination(tmp_path, "change-a"))
    if damage == "missing":
        path.unlink()
    else:
        path.write_text(
            "{" if damage == "malformed" else _coordination(tmp_path, "change-b").model_dump_json(), encoding="utf-8"
        )
    before = path.read_bytes() if path.exists() else None
    for operation in (coordinator.show, coordinator.prepare_runtime_custody_guard):
        with pytest.raises(CoordinationConflictError) as failure:
            operation("change-a")
        assert failure.value.code == "ERR_TARGET_COORDINATION_CONFLICT"
    assert (path.read_bytes() if path.exists() else None) == before


@pytest.mark.parametrize("damage", ["missing-attempt", "wrong-writer", "finished-attempt"])
def test_finalizer_requires_exact_unfinished_attempt(tmp_path: Path, damage: str) -> None:
    coordinator = PortfolioCoordinator(tmp_path)
    original = coordinator.register(_coordination(tmp_path, "change-a"))
    writer = ChangeWriter(**_identity("change-a").model_dump(), job_id=1, kind="finalize")
    attempt = ChangeFinalizationAttempt(
        writer=writer, contract_digest="a" * 64, frontier_digest="b" * 64, exact_head="a" * 40, target_head="b" * 40
    )
    invalid = {
        "missing-attempt": None,
        "wrong-writer": attempt.model_copy(
            update={"writer": writer.model_copy(update={"claim_id": "different-claim"})}
        ),
        "finished-attempt": attempt.model_copy(update={"finished_at": "2026-08-02T00:02:00Z"}),
    }[damage]
    with pytest.raises(ValidationError):
        ChangeCoordination.model_validate(original.model_dump() | {"writer": writer, "finalization_attempt": invalid})
    with pytest.raises(CoordinationConflictError, match="exact unfinished attempt"):
        coordinator.acquire("change-a", writer, finalization_attempt=invalid)
    assert coordinator.show("change-a") == original


def test_publication_reservation_excludes_writers_and_boundary_updates(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state")
    coordinator.register(_coordination(tmp_path, "publish-change"))
    now = datetime.now(UTC)

    with coordinator.publication_lock("publish-change") as lock:
        reserved = coordinator.reserve_publication(
            "publish-change",
            PublicationLease(
                operation_id="operation-1",
                owner_id="owner-1",
                expires_at=(now + timedelta(minutes=10)).isoformat(),
            ),
            lock,
            now=now.isoformat(),
        )

    assert reserved.publication_lease is not None
    assert reserved.publication_lease.operation_id == "operation-1"
    with pytest.raises(CoordinationConflictError, match="active writer"):
        coordinator.acquire(
            "publish-change",
            ChangeWriter(**_identity("publish-change").model_dump(), job_id=1, kind="build"),
        )
    with pytest.raises(CoordinationConflictError, match="reserved publication boundary"):
        coordinator.update(reserved.model_copy(update={"target_head": "b" * 40}))
    with coordinator.publication_lock("publish-change") as lock:
        with pytest.raises(CoordinationConflictError, match="does not own"):
            coordinator.release_publication("publish-change", "operation-1", "owner-2", lock)
        released = coordinator.release_publication("publish-change", "operation-1", "owner-1", lock)

    assert released.publication_lease is None
    with pytest.raises(ValueError, match="active publication lock"):
        coordinator.release_publication("publish-change", "operation-1", "owner-1", lock)


def test_publication_locks_allow_independent_changes_concurrently(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state")
    coordinator.register(_coordination(tmp_path, "change-a"))
    coordinator.register(_coordination(tmp_path, "change-b"))

    with (
        coordinator.publication_lock("change-a", blocking=False),
        coordinator.publication_lock("change-b", blocking=False),
    ):
        pass


def test_publication_lease_rejects_concurrent_owner_and_allows_expired_takeover(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state")
    coordinator.register(_coordination(tmp_path, "lease-change"))
    with coordinator.publication_lock("lease-change") as lock:
        coordinator.reserve_publication(
            "lease-change",
            PublicationLease(
                operation_id="operation-1",
                owner_id="owner-1",
                expires_at="2026-08-02T00:10:00Z",
            ),
            lock,
            now="2026-08-02T00:00:00Z",
        )
        with pytest.raises(CoordinationConflictError, match="active ownership"):
            coordinator.reserve_publication(
                "lease-change",
                PublicationLease(
                    operation_id="operation-1",
                    owner_id="owner-2",
                    expires_at="2026-08-02T00:15:00Z",
                ),
                lock,
                now="2026-08-02T00:05:00Z",
            )
        recovered = coordinator.reserve_publication(
            "lease-change",
            PublicationLease(
                operation_id="operation-2",
                owner_id="owner-2",
                expires_at="2026-08-02T00:21:00Z",
            ),
            lock,
            now="2026-08-02T00:11:00Z",
        )

    assert recovered.publication_lease is not None
    assert recovered.publication_lease.operation_id == "operation-2"
    assert recovered.publication_lease.owner_id == "owner-2"
    with (
        coordinator.publication_lock("lease-change") as lock,
        pytest.raises(CoordinationConflictError, match="does not own"),
    ):
        coordinator.release_publication("lease-change", "operation-1", "owner-1", lock)


def test_writer_acquisition_recovers_expired_publication_lease(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state")
    coordinator.register(_coordination(tmp_path, "expired-change"))
    with coordinator.publication_lock("expired-change") as lock:
        coordinator.reserve_publication(
            "expired-change",
            PublicationLease(
                operation_id="operation-expired",
                owner_id="owner-expired",
                expires_at="2020-08-02T00:10:00Z",
            ),
            lock,
            now="2020-08-02T00:00:00Z",
        )

    acquired = coordinator.acquire(
        "expired-change",
        ChangeWriter(**_identity("expired-change").model_dump(), job_id=1, kind="build"),
    )

    assert acquired.writer is not None
    assert acquired.publication_lease is None


def test_retired_scalar_publication_reservation_loads_as_abandoned(tmp_path: Path) -> None:
    payload = _coordination(tmp_path, "retired-change").model_dump(mode="json")
    payload["publication_operation_id"] = "operation-retired"
    payload["publication_expires_at"] = "2099-08-02T00:10:00Z"
    payload.pop("publication_base_head")

    coordination = ChangeCoordination.model_validate_json(json.dumps(payload))

    assert coordination.publication_lease is None
    assert coordination.publication_base_head is None


def test_publication_lease_duration_is_bounded(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state")
    coordinator.register(_coordination(tmp_path, "bounded-change"))

    with (
        coordinator.publication_lock("bounded-change") as lock,
        pytest.raises(ValueError, match="maximum duration"),
    ):
        coordinator.reserve_publication(
            "bounded-change",
            PublicationLease(
                operation_id="operation-bounded",
                owner_id="owner-bounded",
                expires_at="2026-08-02T00:10:01Z",
            ),
            lock,
            now="2026-08-02T00:00:00Z",
        )


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_ref_exists(repository: Path, reference: str) -> bool:
    return (
        subprocess.run(  # noqa: S603
            ("git", "-C", str(repository), "rev-parse", "--verify", reference),  # noqa: S607
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _repository(tmp_path: Path, *, target: str = "release") -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Test User")
    _git(repository, "config", "user.email", "test@example.com")
    (repository / "shared.txt").write_text("base\n", encoding="utf-8")
    _git(repository, "add", "shared.txt")
    _git(repository, "commit", "-m", "initial")
    initial = _git(repository, "rev-parse", "HEAD")
    _git(repository, "branch", target, initial)
    _git(repository, "update-ref", f"refs/remotes/origin/{target}", initial)
    return repository, initial


def _manager(
    tmp_path: Path,
    repository: Path,
    *,
    target: str = "release",
    remote: str = "origin",
    provenance_provider: object | None = None,
):
    coordinator = PortfolioCoordinator(tmp_path / "state")
    manager = ChangeWorkspaceManager(
        repository,
        tmp_path / "worktrees",
        coordinator,
        target,
        remote=remote,
        preservation_provenance_provider=provenance_provider or _TestPreservationProvenanceProvider(),
    )
    return coordinator, manager


class _TestPreservationProvenanceProvider:
    def __init__(
        self,
        *,
        disposition: str = "disposable",
        stale_task_digest: bool = False,
        stale_head: bool = False,
        verification_available: bool = True,
    ):
        self.disposition = disposition
        self.stale_task_digest = stale_task_digest
        self.stale_head = stale_head
        self.verification_available = verification_available

    def classify(self, **kwargs):
        intent = kwargs["intent"]
        worktree = kwargs["worktree_path"]

        def before_state(path: str) -> tuple[str, str | None, int | None]:
            candidate = worktree / PurePosixPath(path)
            try:
                metadata = candidate.lstat()
            except FileNotFoundError:
                return "absent", None, None
            if stat.S_ISLNK(metadata.st_mode):
                content = os.fsencode(os.readlink(candidate))
                return "symlink", hashlib.sha256(content).hexdigest(), 0o777
            content = candidate.read_bytes()
            return "regular", hashlib.sha256(content).hexdigest(), stat.S_IMODE(metadata.st_mode)

        def path_provenance(path: str) -> PreservationPathProvenance:
            kind, before_digest, before_mode = before_state(path)
            return PreservationPathProvenance(
                path=path,
                disposition=self.disposition,
                producer_id="test-owner",
                before_kind=kind,
                before_digest=before_digest,
                before_mode=before_mode,
            )

        return PreservationProvenanceEvidence(
            evidence_id="test-owner-evidence",
            change_id=kwargs["change_id"],
            recovery_id=kwargs["recovery_id"],
            worktree_path=worktree,
            workspace_fingerprint=intent.workspace_fingerprint,
            exact_head=("0" * 40 if self.stale_head else kwargs["exact_head"]),
            index_digest=kwargs["index_digest"],
            task_id=intent.admitted_task_id,
            task_digest=(
                ("0" * 64 if self.stale_task_digest else intent.admitted_task_digest)
                if intent.admitted_task_digest is not None
                else None
            ),
            paths=tuple(
                path_provenance(path)
                for path in kwargs["paths"]
            ),
        )

    def verify(self, **kwargs):
        if not self.verification_available:
            return None
        return kwargs["evidence"]


@pytest.mark.parametrize(
    "arguments",
    [
        ("status", "--porcelain=v1", "-z"),
        ("diff", "--cached", "--quiet", "--"),
        ("rev-parse", "--path-format=absolute", "--git-path", "index"),
        ("ls-files", "--sparse", "--stage", "-z"),
        ("ls-tree", "-z", "HEAD", "--", "shared.txt"),
        ("cat-file", "blob", "HEAD:shared.txt"),
    ],
)
def test_preservation_git_inspections_have_bounded_timeout(tmp_path: Path, arguments: tuple[str, ...]) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    with patch("owlbear_delivery.change_workspace.subprocess.run") as run:
        manager._preservation_git(*arguments, cwd=repository)  # noqa: SLF001
    assert run.call_args.kwargs["timeout"] == 10
    assert run.call_args.kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
    assert run.call_args.args[0][3:] == ("--no-optional-locks", *arguments)


@pytest.mark.parametrize(
    ("arguments", "timeout"),
    [
        (("status", "--porcelain"), 10),
        (("-C", ".", "--no-optional-locks", "status", "--porcelain"), 10),
        (("--no-optional-locks", "-C", ".", "worktree", "list"), 10),
        (("--no-optional-locks", "branch", "--show-current"), 10),
        (("--no-optional-locks", "commit", "-m", "message"), None),
    ],
)
def test_git_inspection_timeout_handles_supported_global_options(tmp_path: Path, arguments, timeout) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    with patch("owlbear_delivery.change_workspace.subprocess.run") as run:
        manager._run_git(*arguments)  # noqa: SLF001
    assert run.call_args.kwargs["timeout"] == timeout
    assert run.call_args.args[0][3:] == arguments


def test_nonterminal_recovery_same_size_replacement_is_not_the_captured_preimage(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    path = worktree / "changed.bin"
    path.write_bytes(b"same-size")

    before = ChangeWorkspaceManager._read_worktree_state(worktree, "changed.bin")  # noqa: SLF001
    replacement = worktree / "replacement.bin"
    replacement.write_bytes(b"same-size")
    replacement.replace(path)
    after = ChangeWorkspaceManager._read_worktree_state(worktree, "changed.bin")  # noqa: SLF001

    assert before.content == after.content
    assert before.mode == after.mode
    assert not ChangeWorkspaceManager._same_state(before, after)  # noqa: SLF001


@pytest.mark.parametrize("kind", ["regular", "symlink", "index"])
def test_nonterminal_recovery_reads_without_noatime(tmp_path: Path, monkeypatch, kind: str) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("portable-read")
    path = coordination.worktree_path / "shared.txt"
    if kind == "index":
        index = manager._resolve_managed_index(coordination.worktree_path)  # noqa: SLF001
        path = index.path
    elif kind == "symlink":
        path = coordination.worktree_path / "read-link"
        path.symlink_to("shared.txt")
    metadata = path.lstat()
    os.utime(path, ns=(1, metadata.st_mtime_ns), follow_symlinks=False)
    monkeypatch.delattr(os, "O_NOATIME", raising=False)

    if kind == "index":
        assert manager._read_managed_index(index) == path.read_bytes()  # noqa: SLF001
    else:
        first = manager._read_worktree_state(coordination.worktree_path, path.name)  # noqa: SLF001
        second = manager._read_worktree_state(coordination.worktree_path, path.name)  # noqa: SLF001
        assert manager._same_state(first, second)  # noqa: SLF001


def test_nonterminal_recovery_reader_atime_does_not_invalidate_preimage(tmp_path: Path) -> None:
    path = tmp_path / "changed.bin"
    path.write_bytes(b"preserved")
    metadata = path.stat()
    os.utime(path, ns=(1, metadata.st_mtime_ns))
    before = ChangeWorkspaceManager._read_worktree_state(tmp_path, path.name)  # noqa: SLF001

    assert path.read_bytes() == b"preserved"
    after = ChangeWorkspaceManager._read_worktree_state(tmp_path, path.name)  # noqa: SLF001

    assert ChangeWorkspaceManager._same_state(before, after)  # noqa: SLF001


def test_nonterminal_recovery_rejects_ignored_inventory_before_private_capture() -> None:
    with pytest.raises(PreservationRejectedError, match="ignored"):
        ChangeWorkspaceManager._preservation_status_paths(b"!! .venv/\0")  # noqa: SLF001


def test_recovery_workspace_retains_stronger_custody_guard_with_ignored_inventory(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("ignored-recovery")
    (coordination.worktree_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (coordination.worktree_path / "ignored.txt").write_text("do not touch\n", encoding="utf-8")
    coordinator.acquire(
        coordination.change_id,
        ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build"),
    )

    captured = manager.capture_recovery_workspace(coordination.change_id, ())

    assert captured[-1] == "active-custody"


def test_recovery_workspace_normalizes_active_custody_for_ordinary_untracked_content(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("untracked-recovery")
    worktree = coordination.worktree_path
    (worktree / "added.bin").write_bytes(b"ordinary untracked\n")
    coordinator.acquire(
        coordination.change_id,
        ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build"),
    )

    with patch.object(manager, "_read_worktree_state", wraps=manager._read_worktree_state) as read_state:
        captured = manager.capture_recovery_workspace(
            coordination.change_id,
            (),
            expected_paths=("added.bin",),
            expected_scope_details=(("added.bin",), {"added.bin": "file"}),
        )

    assert captured[3:] == (("added.bin",), "workspace-dirty")
    assert read_state.call_count == 1


def test_recovery_workspace_rejects_intermediate_symlink_before_git_fingerprint(tmp_path: Path) -> None:
    _coordinator, manager, coordination, _intent = _preservation_workspace(tmp_path, nested=True)
    worktree = coordination.worktree_path
    external = tmp_path / "external"
    external.mkdir()
    (external / "file.txt").write_bytes(b"outside\n")
    nested = worktree / "nested" / "deeper"
    shutil.rmtree(nested)
    nested.symlink_to(external, target_is_directory=True)
    expected_paths = ("nested/deeper", "nested/deeper/file.txt")

    with (
        patch.object(manager, "_read_worktree_state", side_effect=AssertionError("dirty content was read")),
        patch.object(manager, "_run_git", wraps=manager._run_git) as run_git,  # noqa: SLF001
        pytest.raises(DeliveryWorkerExclusionRequiredError),
    ):
        manager.capture_recovery_workspace(
            coordination.change_id,
            (),
            expected_paths=expected_paths,
            expected_scope_details=(("nested",), {"nested": "directory"}),
        )

    assert not any(call.args[:1] == ("diff",) for call in run_git.call_args_list)


def test_recovery_workspace_rejects_noncanonical_admitted_path_before_git_fingerprint(tmp_path: Path) -> None:
    _coordinator, manager, coordination, _intent = _preservation_workspace(tmp_path)
    path = coordination.worktree_path / "file with space.py"
    path.write_bytes(b"unsupported admission\n")

    with (
        patch.object(manager, "_read_worktree_state", side_effect=AssertionError("dirty content was read")),
        patch.object(manager, "_run_git", wraps=manager._run_git) as run_git,  # noqa: SLF001
        pytest.raises(DeliveryWorkerExclusionRequiredError),
    ):
        manager.capture_recovery_workspace(
            coordination.change_id,
            (),
            expected_paths=("file with space.py",),
            expected_scope_details=(("file with space.py",), {"file with space.py": "file"}),
        )

    assert not any(call.args[:1] == ("diff",) for call in run_git.call_args_list)


@pytest.mark.parametrize("kind", ["nested", "deletion", "symlink-leaf"])
def test_recovery_workspace_reads_supported_nested_path_states(tmp_path: Path, kind: str) -> None:
    _coordinator, manager, coordination, _intent = _preservation_workspace(tmp_path, nested=True)
    worktree = coordination.worktree_path
    path = worktree / "nested" / "deeper" / "file.txt"
    if kind == "nested":
        path.write_bytes(b"nested change\n")
        relative = "nested/deeper/file.txt"
    elif kind == "deletion":
        path.unlink()
        relative = "nested/deeper/file.txt"
    else:
        external = tmp_path / "symlink-target.txt"
        external.write_bytes(b"outside\n")
        (path.parent / "link").symlink_to(external)
        relative = "nested/deeper/link"

    captured = manager.capture_recovery_workspace(
        coordination.change_id,
        (),
        expected_paths=(relative,),
        expected_scope_details=(("nested",), {"nested": "directory"}),
    )

    assert captured[3] == (relative,)
    state = manager._read_worktree_state(worktree, relative)  # noqa: SLF001
    assert state.kind == {"nested": "regular", "deletion": "absent", "symlink-leaf": "symlink"}[kind]


def test_recovery_workspace_reader_fences_ancestor_substitution(tmp_path: Path) -> None:
    _coordinator, _manager, coordination, _intent = _preservation_workspace(tmp_path, nested=True)
    worktree = coordination.worktree_path
    original_open = os.open
    swapped = False

    def open_and_replace(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        if dir_fd is not None and path == "deeper" and not swapped:
            nested = worktree / "nested" / "deeper"
            retained = worktree / "nested" / "retained-deeper"
            nested.rename(retained)
            nested.mkdir()
            swapped = True
        return descriptor

    with (
        patch("owlbear_delivery.change_workspace.os.open", side_effect=open_and_replace),
        pytest.raises(PreservationFenceError, match="ancestor"),
    ):
        ChangeWorkspaceManager._read_worktree_state(worktree, "nested/deeper/file.txt")  # noqa: SLF001

    assert swapped


def test_recovery_workspace_reader_closes_parent_on_missing_intermediate(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    (worktree / "nested").mkdir(parents=True)
    opened: list[int] = []
    closed: list[int] = []
    original_open = os.open
    original_close = os.close

    def tracking_open(path, flags, mode=0o777, *, dir_fd=None):
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        opened.append(descriptor)
        return descriptor

    def tracking_close(descriptor):
        closed.append(descriptor)
        return original_close(descriptor)

    with (
        patch("owlbear_delivery.change_workspace.os.open", side_effect=tracking_open),
        patch("owlbear_delivery.change_workspace.os.close", side_effect=tracking_close),
    ):
        result = ChangeWorkspaceManager._open_worktree_read_parent(  # noqa: SLF001
            worktree,
            ("nested", "missing"),
            "nested/missing/file.txt",
        )

    assert result is None
    assert set(opened) == set(closed)


def test_recovery_workspace_reader_closes_successor_on_identity_mismatch(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    (worktree / "nested").mkdir(parents=True)
    opened: list[int] = []
    closed: list[int] = []
    fstat_calls = 0
    original_open = os.open
    original_close = os.close
    original_fstat = os.fstat

    def tracking_open(path, flags, mode=0o777, *, dir_fd=None):
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        opened.append(descriptor)
        return descriptor

    def tracking_close(descriptor):
        closed.append(descriptor)
        return original_close(descriptor)

    def mismatching_fstat(descriptor):
        nonlocal fstat_calls
        fstat_calls += 1
        metadata = original_fstat(descriptor)
        if fstat_calls == 2:
            values = list(metadata)
            values[1] += 1
            return os.stat_result(values)
        return metadata

    with (
        patch("owlbear_delivery.change_workspace.os.open", side_effect=tracking_open),
        patch("owlbear_delivery.change_workspace.os.close", side_effect=tracking_close),
        patch("owlbear_delivery.change_workspace.os.fstat", side_effect=mismatching_fstat),
        pytest.raises(PreservationFenceError, match="ancestor"),
    ):
        ChangeWorkspaceManager._open_worktree_read_parent(  # noqa: SLF001
            worktree,
            ("nested",),
            "nested/file.txt",
        )

    assert fstat_calls == 2
    assert set(opened) == set(closed)


def test_finalization_repair_release_reuses_completed_recovery_custody(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state")
    coordination = _coordination(tmp_path, "repair-release")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="finalize")
    attempt = ChangeFinalizationAttempt(
        writer=writer,
        contract_digest="b" * 64,
        frontier_digest="c" * 64,
        exact_head="a" * 40,
        target_head="b" * 40,
        finished_at="2026-08-02T00:02:00Z",
    )
    coordinator.register(coordination.model_copy(update={"finalization_attempt": attempt}))

    participant = coordinator.prepare_finalization_repair_release(
        coordination.change_id,
        writer.attempt_id,
        "2026-08-02T00:03:00Z",
    )

    assert isinstance(participant, TransactionParticipant)
    assert participant.content == coordinator.coordination_bytes(coordination.change_id)


def _preservation_workspace(
    tmp_path: Path,
    *,
    nested: bool = False,
    provenance_provider: object | None = None,
):
    repository, initial = _repository(tmp_path, target="release")
    if nested:
        (repository / "nested" / "deeper").mkdir(parents=True)
        (repository / "nested" / "deeper" / "file.txt").write_bytes(b"nested baseline\n")
        _git(repository, "add", "nested")
        _git(repository, "commit", "-m", "nested baseline")
        initial = _git(repository, "rev-parse", "HEAD")
        _git(repository, "branch", "-f", "release", initial)
        _git(repository, "update-ref", "refs/remotes/origin/release", initial)
    coordinator, manager = _manager(tmp_path, repository, provenance_provider=provenance_provider)
    coordination = manager.ensure("preserve-change")
    frontier_path = manager.runtime_root / "changes" / coordination.change_id / "frontier.json"
    frontier = b'{"frontier":"preservation"}\n'
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier_path.write_bytes(frontier)
    request = RecoveryInvocationRequest(
        change_id=coordination.change_id,
        owner_id="owner-preservation",
        attempt_id="attempt-preservation",
        outcome_id="OUT-001",
        kind="claim",
        contract_digest="a" * 64,
        exact_head=initial,
        target_head=manager.observed_target_head(),
        branch=coordination.branch,
        worktree=str(coordination.worktree_path),
        repository=str(manager.repository),
        runtime_root=str(manager.runtime_root),
        integration_target=coordination.integration_target,
    )
    invocation = RecoveryInvocation(
        request=request,
        host_instance="test-host",
        host_generation="test-generation",
        invocation_id="invocation-preservation",
    )
    intent = RecoveryIntent(
        invocation=invocation,
        frontier_digest=digest(frontier),
        coordination_digest=digest(coordinator.coordination_bytes(coordination.change_id)),
        exact_head=initial,
        target_head=request.target_head,
        workspace_fingerprint="b" * 64,
        owner_record="owner record",
        kind="clean-claim",
        maintained_surfaces=("src",),
        last_write_provenance=("test-owner",),
        admitted_task_id="TASK-PRESERVATION",
        admitted_task_digest="c" * 64,
        admitted_task_scope=(
            "added.bin",
            "nested/deeper/file.txt",
            "nested/deeper/new.txt",
            "preserved-link",
            "shared.txt",
        ),
        admitted_paths=(
            "added.bin",
            "nested/deeper/file.txt",
            "nested/deeper/new.txt",
            "preserved-link",
            "shared.txt",
        ),
    )
    evidence = RecoveryEvidence(
        reference=RecoveryEvidenceReference(reference="opaque-preservation"),
        recovery_id=intent.recovery_id,
        invocation=invocation,
        status="closed",
    )
    receipt = RecoveryReceipt(
        recovery_id=intent.recovery_id,
        evidence=evidence,
        owner_effect="no-workspace-effect",
        finished_at="2026-08-02T00:04:00Z",
    )
    recovery_root = manager.runtime_root / journal_path(coordination.change_id, intent.recovery_id, "intent").parent
    recovery_root.mkdir(parents=True, exist_ok=True)
    (manager.runtime_root / journal_path(coordination.change_id, intent.recovery_id, "intent")).write_bytes(
        intent.model_dump_json().encode()
    )
    (manager.runtime_root / journal_path(coordination.change_id, intent.recovery_id, "evidence")).write_bytes(
        evidence.model_dump_json().encode()
    )
    (manager.runtime_root / journal_path(coordination.change_id, intent.recovery_id, "receipt")).write_bytes(
        receipt.model_dump_json().encode()
    )
    coordinator.record_verified_exclusion(intent.recovery_id)
    return coordinator, manager, coordination, intent


def test_preservation_captures_linked_index_and_restores_raw_worktree_state(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    index = manager._resolve_managed_index(coordination.worktree_path)  # noqa: SLF001
    assert index.path != manager.repository / ".git" / "index"
    index_bytes = manager._read_managed_index(index)  # noqa: SLF001
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty preservation\n")
    (coordination.worktree_path / "shared.txt").chmod(0o755)
    (coordination.worktree_path / "preserved-link").symlink_to("shared.txt")

    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    assert tuple(entry.path for entry in preservation.paths) == ("preserved-link", "shared.txt")
    assert manager.verify_preservation(coordination.change_id, preservation.preservation_id) == preservation
    private_root = (
        manager.runtime_root
        / "changes"
        / coordination.change_id
        / "recovery-receipts"
        / intent.recovery_id
        / "preservation"
    )
    assert (private_root / "manifest.json").exists()
    assert (private_root.stat().st_mode & 0o077) == 0

    restored = manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert restored == preservation
    assert (coordination.worktree_path / "shared.txt").read_bytes() == b"base\n"
    assert (coordination.worktree_path / "shared.txt").stat().st_mode & 0o777 == 0o644
    assert not (coordination.worktree_path / "preserved-link").is_symlink()
    assert manager._read_managed_index(index) == index_bytes  # noqa: SLF001
    assert manager.restore_preservation(coordination.change_id, preservation.preservation_id) == preservation
    _git(coordination.worktree_path, "update-index", "--chmod=+x", "shared.txt")
    with pytest.raises(PreservationFenceError, match="index"):
        manager.restore_preservation(coordination.change_id, preservation.preservation_id)


def test_preservation_rejects_foreign_dirty_path_before_private_capture(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    (worktree / "shared.txt").write_bytes(b"dirty preservation\n")
    (worktree / "foreign.txt").write_bytes(b"unknown bytes\n")

    with (
        patch.object(manager, "_read_managed_index", side_effect=AssertionError("raw index was read")),
        pytest.raises(PreservationRejectedError, match="admitted task path authority"),
    ):
        manager.capture_preservation(coordination.change_id, intent.recovery_id)

    private_root = manager.runtime_root / "changes" / intent.invocation.request.change_id / "recovery-receipts"
    assert not (private_root / intent.recovery_id / "preservation").exists()


@pytest.mark.parametrize(
    ("provider", "message"),
    [
        (_TestPreservationProvenanceProvider(stale_task_digest=True), "stale"),
        (_TestPreservationProvenanceProvider(stale_head=True), "stale"),
        (_TestPreservationProvenanceProvider(disposition="foreign"), "foreign"),
        (_TestPreservationProvenanceProvider(disposition="ambiguous"), "foreign"),
        (_TestPreservationProvenanceProvider(disposition="private"), "foreign"),
    ],
)
def test_preservation_requires_trusted_exact_path_provenance_before_copying(
    tmp_path: Path,
    provider: _TestPreservationProvenanceProvider,
    message: str,
) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(
        tmp_path, provenance_provider=provider
    )
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty preservation\n")

    with (
        patch.object(manager, "_read_worktree_state", side_effect=AssertionError("raw path was read")),
        pytest.raises(PreservationRejectedError, match=message),
    ):
        manager.capture_preservation(coordination.change_id, intent.recovery_id)

    private_root = manager.runtime_root / "changes" / coordination.change_id / "recovery-receipts"
    assert not (private_root / intent.recovery_id / "preservation").exists()


def test_preservation_default_owner_boundary_is_unavailable(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(
        tmp_path,
        provenance_provider=UnavailablePreservationProvenanceProvider(),
    )
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty preservation\n")

    with pytest.raises(PreservationRejectedError, match="trusted path provenance"):
        manager.capture_preservation(coordination.change_id, intent.recovery_id)


def test_preservation_restores_only_proven_disposable_paths(tmp_path: Path) -> None:
    provider = _TestPreservationProvenanceProvider(disposition="useful")
    _coordinator, manager, coordination, intent = _preservation_workspace(
        tmp_path, provenance_provider=provider
    )
    (coordination.worktree_path / "shared.txt").write_bytes(b"useful code\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)

    assert preservation.provenance is not None
    assert preservation.provenance.paths[0].disposition == "useful"
    manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert (coordination.worktree_path / "shared.txt").read_bytes() == b"useful code\n"
    with pytest.raises(PreservationRejectedError, match="disposable"):
        manager.restore_preservation(
            coordination.change_id,
            preservation.preservation_id,
            paths=("shared.txt",),
        )


def test_preservation_requires_owner_before_state_to_match_captured_bytes(tmp_path: Path) -> None:
    class MismatchedStateProvider(_TestPreservationProvenanceProvider):
        def classify(self, **kwargs):
            evidence = super().classify(**kwargs)
            item = evidence.paths[0].model_copy(update={"before_digest": "f" * 64})
            return evidence.model_copy(update={"paths": (item, *evidence.paths[1:])})

    _coordinator, manager, coordination, intent = _preservation_workspace(
        tmp_path,
        provenance_provider=MismatchedStateProvider(),
    )
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty preservation\n")

    with pytest.raises(PreservationFenceError, match="trusted path provenance"):
        manager.capture_preservation(coordination.change_id, intent.recovery_id)
    preservation_root = (
        manager.runtime_root
        / "changes"
        / coordination.change_id
        / "recovery-receipts"
        / intent.recovery_id
        / "preservation"
    )
    assert not preservation_root.exists()


def test_preservation_owner_evidence_binds_recovery_and_workspace(tmp_path: Path) -> None:
    class WrongRecoveryBindingProvider(_TestPreservationProvenanceProvider):
        def classify(self, **kwargs):
            evidence = super().classify(**kwargs)
            return evidence.model_copy(update={"recovery_id": "0" * 64})

    _coordinator, manager, coordination, intent = _preservation_workspace(
        tmp_path,
        provenance_provider=WrongRecoveryBindingProvider(),
    )
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty preservation\n")

    with pytest.raises(PreservationRejectedError, match="path provenance"):
        manager.capture_preservation(coordination.change_id, intent.recovery_id)


def test_restore_requires_independent_provenance_reverification_before_objects(tmp_path: Path) -> None:
    provider = _TestPreservationProvenanceProvider()
    _coordinator, manager, coordination, intent = _preservation_workspace(
        tmp_path, provenance_provider=provider
    )
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    provider.verification_available = False

    with (
        patch.object(manager, "_read_private_preservation_object", side_effect=AssertionError("object was read")),
        pytest.raises(PreservationRejectedError, match="reverified"),
    ):
        manager.restore_preservation(coordination.change_id, preservation.preservation_id)


def test_private_path_policy_remains_conservative_for_dirty_paths() -> None:
    with pytest.raises(PreservationRejectedError, match="private"):
        ChangeWorkspaceManager._validate_private_paths(
            ("custom-tokens.css", "components/password-component.tsx")
        )
    with pytest.raises(PreservationRejectedError, match="private"):
        ChangeWorkspaceManager._validate_private_paths(("config/password",))
    with pytest.raises(PreservationRejectedError, match="private"):
        ChangeWorkspaceManager._validate_private_paths(("config/private.txt",))


def _raw_index_for_test(path: str, *, extension: bytes = b"") -> bytes:
    encoded_path = path.encode()
    entry = bytearray(62)
    entry[24:28] = (0o100644).to_bytes(4, "big")
    entry[40:60] = b"\x01" * 20
    entry[60:62] = len(encoded_path).to_bytes(2, "big")
    entry.extend(encoded_path)
    entry.append(0)
    entry.extend(b"\0" * ((-len(entry)) % 8))
    content = b"DIRC" + (2).to_bytes(4, "big") + (1).to_bytes(4, "big") + entry + extension
    return content + hashlib.sha1(content, usedforsecurity=False).digest()


@pytest.mark.parametrize("path", ["custom-tokens.css", "components/password-component.tsx"])
def test_raw_index_privacy_uses_structural_paths(path: str) -> None:
    expected_entries = ((path, 0o100644, 0, "01" * 20),)
    head_entries = ((path, 0o100644, "01" * 20),)
    names = ChangeWorkspaceManager._validate_index_extensions(
        _raw_index_for_test(path),
        expected_entries=expected_entries,
        head_entries=head_entries,
    )
    ChangeWorkspaceManager._validate_index_path_names(names)


def test_raw_index_qualification_binds_exact_git_and_head_entries() -> None:
    content = _raw_index_for_test("ordinary.txt")
    index_entries = (("ordinary.txt", 0o100644, 0, "01" * 20),)
    head_entries = (("ordinary.txt", 0o100644, "01" * 20),)
    ChangeWorkspaceManager._validate_index_extensions(
        content,
        expected_entries=index_entries,
        head_entries=head_entries,
    )
    with pytest.raises(PreservationRejectedError, match="Git inventory"):
        ChangeWorkspaceManager._validate_index_extensions(
            content,
            expected_entries=(("ordinary.txt", 0o100644, 0, "02" * 20),),
            head_entries=head_entries,
        )
    with pytest.raises(PreservationRejectedError, match="reviewed HEAD"):
        ChangeWorkspaceManager._validate_index_extensions(
            content,
            expected_entries=index_entries,
            head_entries=(("ordinary.txt", 0o100644, "02" * 20),),
        )


def test_raw_index_cache_tree_extension_is_fully_parsed() -> None:
    tree = b"\0" + b"1 0\n" + b"\x02" * 20
    extension = b"TREE" + len(tree).to_bytes(4, "big") + tree
    index_entries = (("ordinary.txt", 0o100644, 0, "01" * 20),)
    head_entries = (("ordinary.txt", 0o100644, "01" * 20),)
    names = ChangeWorkspaceManager._validate_index_extensions(
        _raw_index_for_test("ordinary.txt", extension=extension),
        expected_entries=index_entries,
        head_entries=head_entries,
    )
    ChangeWorkspaceManager._validate_index_path_names(names)
    private_tree = b"config/password\0" + b"1 0\n" + b"\x02" * 20
    private_extension = b"TREE" + len(private_tree).to_bytes(4, "big") + private_tree
    with pytest.raises(PreservationRejectedError, match="private"):
        ChangeWorkspaceManager._validate_index_path_names(
            ChangeWorkspaceManager._validate_index_extensions(
                _raw_index_for_test("ordinary.txt", extension=private_extension),
                expected_entries=index_entries,
                head_entries=head_entries,
            )
        )


def test_raw_index_rejects_nonzero_padding_and_bad_checksum() -> None:
    content = bytearray(_raw_index_for_test("ordinary.txt"))
    entry_start = 12
    path_end = entry_start + 62 + len(b"ordinary.txt") + 1
    content[path_end] = 1
    content[-20:] = hashlib.sha1(content[:-20], usedforsecurity=False).digest()
    with pytest.raises(PreservationRejectedError, match="padding"):
        ChangeWorkspaceManager._validate_index_extensions(bytes(content))

    invalid_checksum = bytearray(_raw_index_for_test("ordinary.txt"))
    invalid_checksum[-1] ^= 1
    with pytest.raises(PreservationRejectedError, match="checksum"):
        ChangeWorkspaceManager._validate_index_extensions(bytes(invalid_checksum))


def test_raw_index_rejects_extended_entry_flags_before_path_parsing() -> None:
    content = bytearray(_raw_index_for_test("ordinary.txt"))
    content[12 + 60 : 12 + 62] = (0x4000).to_bytes(2, "big")
    content[-20:] = hashlib.sha1(content[:-20], usedforsecurity=False).digest()

    with pytest.raises(PreservationRejectedError, match="extended"):
        ChangeWorkspaceManager._validate_index_extensions(bytes(content))


def test_raw_index_private_and_unknown_extensions_remain_contained() -> None:
    index_entries = (("password", 0o100644, 0, "01" * 20),)
    head_entries = (("password", 0o100644, "01" * 20),)
    with pytest.raises(PreservationRejectedError, match="private"):
        ChangeWorkspaceManager._validate_index_path_names(
            ChangeWorkspaceManager._validate_index_extensions(
                _raw_index_for_test("password"),
                expected_entries=index_entries,
                head_entries=head_entries,
            )
        )
    with pytest.raises(PreservationRejectedError, match="containment"):
        ChangeWorkspaceManager._validate_index_extensions(
            _raw_index_for_test("ordinary.txt", extension=b"UNKN" + (3).to_bytes(4, "big") + b"raw")
        )
    with pytest.raises(PreservationRejectedError, match="containment"):
        ChangeWorkspaceManager._validate_index_extensions(
            _raw_index_for_test("ordinary.txt", extension=b"EOIE" + (0).to_bytes(4, "big"))
        )


def test_raw_index_scans_all_bytes_for_high_confidence_credentials() -> None:
    with pytest.raises(PreservationRejectedError, match="private"):
        ChangeWorkspaceManager._validate_index_extensions(
            _raw_index_for_test("ordinary.txt", extension=b"UNKN" + (13).to_bytes(4, "big") + b"github_pat_abc")
        )


def test_legacy_preservation_receipt_loads_but_cannot_authorize_restore(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    (coordination.worktree_path / "shared.txt").write_bytes(b"legacy preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    manifest_path = (
        manager.runtime_root
        / "changes"
        / coordination.change_id
        / "recovery-receipts"
        / intent.recovery_id
        / "preservation"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_bytes())
    legacy_receipt = manifest["receipt"]
    legacy_receipt.pop("provenance")
    for entry in legacy_receipt["paths"]:
        entry.pop("provenance")
    legacy_receipt["receipt_id"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in legacy_receipt.items() if key != "receipt_id"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    loaded = WorktreePreservationReceipt.model_validate(legacy_receipt)
    assert loaded.provenance is None
    manifest["receipt"] = legacy_receipt
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    assert manager.verify_preservation(coordination.change_id, preservation.preservation_id).provenance is None

    with pytest.raises(PreservationRejectedError, match="path provenance"):
        manager.restore_preservation(coordination.change_id, preservation.preservation_id)


def test_legacy_provenance_shape_remains_inspectable_but_lacks_authority() -> None:
    legacy = PreservationProvenanceEvidence(
        evidence_id="legacy-owner-evidence",
        exact_head="a" * 40,
        index_digest="b" * 64,
        task_id="legacy-task",
        task_digest="c" * 64,
        paths=(
            PreservationPathProvenance(
                path="shared.txt",
                disposition="disposable",
                producer_id="legacy-owner",
            ),
        ),
    )

    assert legacy.change_id is None
    assert legacy.paths[0].before_kind is None


def test_preservation_status_paths_include_both_rename_names() -> None:
    status = b"R  renamed.txt\0original.txt\0"

    assert ChangeWorkspaceManager._preservation_status_paths(status) == ("original.txt", "renamed.txt")


def test_recovery_workspace_metadata_does_not_read_dirty_content(tmp_path: Path) -> None:
    _coordinator, manager, coordination, _intent = _preservation_workspace(tmp_path)
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty preservation\n")

    with (
        patch.object(manager, "_read_worktree_state", side_effect=AssertionError("dirty content was read")),
        patch.object(manager, "_run_git", wraps=manager._run_git) as run_git,
    ):
        _coordination, _head, _status, paths, _reason = manager.capture_recovery_workspace_metadata(
            coordination.change_id, ()
        )

    assert paths == ("shared.txt",)
    assert not any(call.args[:1] == ("diff",) for call in run_git.call_args_list)


def test_recovery_workspace_fingerprint_includes_admitted_untracked_bytes(tmp_path: Path) -> None:
    _coordinator, manager, coordination, _intent = _preservation_workspace(tmp_path)
    path = coordination.worktree_path / "added.bin"
    path.write_bytes(b"first\n")
    first = manager.capture_recovery_workspace(coordination.change_id, (), expected_paths=("added.bin",))
    path.write_bytes(b"second\n")
    second = manager.capture_recovery_workspace(coordination.change_id, (), expected_paths=("added.bin",))

    assert first[3] == second[3] == ("added.bin",)
    assert first[2] != second[2]


def test_recovery_workspace_rejects_ignored_inventory_before_admission_fingerprint(tmp_path: Path) -> None:
    _coordinator, manager, coordination, _intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    exclude = Path(_git(worktree, "rev-parse", "--git-path", "info/exclude"))
    if not exclude.is_absolute():
        exclude = worktree / exclude
    exclude.write_text("ignored-recovery.txt\n", encoding="utf-8")
    (worktree / "ignored-recovery.txt").write_text("do not read\n", encoding="utf-8")
    tracked = worktree / "shared.txt"
    tracked.write_text("first\n", encoding="utf-8")

    with (
        patch.object(manager, "_read_worktree_state", side_effect=AssertionError("dirty content was read")),
        pytest.raises(DeliveryWorkerExclusionRequiredError),
    ):
        manager.capture_recovery_workspace(coordination.change_id, (), expected_paths=("shared.txt",))


def test_recovery_workspace_rejects_path_drift_before_content_read(tmp_path: Path) -> None:
    _coordinator, manager, coordination, _intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    (worktree / "shared.txt").write_bytes(b"dirty preservation\n")
    (worktree / "foreign.txt").write_bytes(b"foreign\n")

    with (
        patch.object(manager, "_read_worktree_state", side_effect=AssertionError("dirty content was read")),
        pytest.raises(DeliveryWorkerExclusionRequiredError),
    ):
        manager.capture_recovery_workspace(
            coordination.change_id,
            (),
            expected_paths=("shared.txt",),
        )


def test_old_provenance_dirty_recovery_cannot_upgrade_to_admitted_preservation(tmp_path: Path) -> None:
    coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    old_bytes = (
        intent.model_dump_json(
            exclude={
                "admitted_task_id",
                "admitted_task_digest",
                "admitted_task_scope",
                "admitted_paths",
            }
        )
        + "\n"
    ).encode()
    old_intent = RecoveryIntent.model_validate_json(old_bytes)
    # Old authority may still recapture cleanly, but it cannot authorize dirty raw custody.
    assert old_intent.authority_matches(intent)
    evidence_path = manager.runtime_root / journal_path(coordination.change_id, intent.recovery_id, "evidence")
    receipt_path = manager.runtime_root / journal_path(coordination.change_id, intent.recovery_id, "receipt")
    evidence = RecoveryEvidence.model_validate_json(evidence_path.read_bytes())
    receipt = RecoveryReceipt.model_validate_json(receipt_path.read_bytes())
    old_evidence = evidence.model_copy(update={"recovery_id": old_intent.recovery_id})
    old_receipt = receipt.model_copy(update={"recovery_id": old_intent.recovery_id, "evidence": old_evidence})
    old_intent_path = manager.runtime_root / journal_path(coordination.change_id, old_intent.recovery_id, "intent")
    old_intent_path.parent.mkdir(parents=True, exist_ok=True)
    old_intent_path.write_bytes(old_bytes)
    (manager.runtime_root / journal_path(coordination.change_id, old_intent.recovery_id, "evidence")).write_bytes(
        old_evidence.model_dump_json().encode()
    )
    (manager.runtime_root / journal_path(coordination.change_id, old_intent.recovery_id, "receipt")).write_bytes(
        old_receipt.model_dump_json().encode()
    )
    coordinator.record_verified_exclusion(old_intent.recovery_id)
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty legacy preservation\n")

    with pytest.raises(PreservationRejectedError, match="admitted Builder task"):
        manager.capture_preservation(coordination.change_id, old_intent.recovery_id)

    private_root = (
        manager.runtime_root
        / "changes"
        / coordination.change_id
        / "recovery-receipts"
        / old_intent.recovery_id
        / "preservation"
    )
    assert not private_root.exists()


def test_replay_rejects_existing_preservation_without_admission_authority(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    old_intent = RecoveryIntent.model_validate_json(
        intent.model_dump_json(
            exclude={
                "admitted_task_id",
                "admitted_task_digest",
                "admitted_task_scope",
                "admitted_paths",
            }
        )
    )

    with (
        patch.object(manager, "_require_preservation_authority", return_value=(old_intent, object())),
        patch.object(manager, "_read_private_preservation_object", side_effect=AssertionError("read before admission")),
        pytest.raises(PreservationRejectedError, match="admitted Builder task authority"),
    ):
        manager.restore_preservation(coordination.change_id, preservation.preservation_id)


@pytest.mark.parametrize("root_drift", ["replacement", "mode"])
def test_nonterminal_recovery_restores_nested_directory_without_losing_root_fence(
    tmp_path: Path, root_drift: str
) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path, nested=True)
    worktree = coordination.worktree_path
    shutil.rmtree(worktree / "nested")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    assert tuple(entry.path for entry in preservation.paths) == ("nested/deeper/file.txt",)
    index = manager._resolve_managed_index(worktree)  # noqa: SLF001
    index_bytes = manager._read_managed_index(index)  # noqa: SLF001

    manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert (worktree / "nested" / "deeper" / "file.txt").read_bytes() == b"nested baseline\n"
    assert worktree.stat().st_nlink != preservation.worktree_links
    assert manager.restore_preservation(coordination.change_id, preservation.preservation_id) == preservation
    assert manager._read_managed_index(index) == index_bytes  # noqa: SLF001

    if root_drift == "replacement":
        retained = worktree.with_name("retained-original")
        worktree.rename(retained)
        shutil.copytree(retained, worktree)
    else:
        worktree.chmod(worktree.stat().st_mode ^ 0o010)
    with pytest.raises(PreservationFenceError, match="root descriptor"):
        manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert (worktree / "nested" / "deeper" / "file.txt").read_bytes() == b"nested baseline\n"
    assert manager._read_managed_index(index) == index_bytes  # noqa: SLF001


def test_nonterminal_recovery_absent_nested_replay_does_not_recreate_parents(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    untracked = worktree / "nested" / "deeper" / "new.txt"
    untracked.parent.mkdir(parents=True)
    untracked.write_bytes(b"untracked\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)

    manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert not untracked.exists()
    shutil.rmtree(worktree / "nested")
    manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert not (worktree / "nested").exists()


@pytest.mark.parametrize("kind", ["worktree-file", "index"])
def test_nonterminal_recovery_still_rejects_file_and_index_hardlinks(tmp_path: Path, kind: str) -> None:
    _coordinator, manager, coordination, _intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    path = (
        manager._resolve_managed_index(worktree).path  # noqa: SLF001
        if kind == "index"
        else worktree / "shared.txt"
    )
    os.link(path, tmp_path / "retained-hardlink")
    if kind == "index":
        reader, arguments = manager._resolve_managed_index, (worktree,)  # noqa: SLF001
    else:
        reader, arguments = manager._read_worktree_state, (worktree, "shared.txt")  # noqa: SLF001
    with pytest.raises(PreservationRejectedError, match=r"linked|single regular"):
        reader(*arguments)


@pytest.mark.parametrize("orphan_manifest", ["missing", "malformed"])
def test_nonterminal_recovery_receipt_lookup_contains_incomplete_sibling(tmp_path: Path, orphan_manifest: str) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty bytes\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    incomplete = manager.runtime_root / Path(preservation.storage_ref).parent.parent / ("0" * 64) / "preservation"
    incomplete.mkdir(parents=True)
    assert intent.recovery_id > "0" * 64
    if orphan_manifest == "malformed":
        (incomplete / "manifest.json").write_bytes(b"{")
        with pytest.raises(PreservationRejectedError, match="manifest is malformed"):
            manager.verify_preservation(coordination.change_id, preservation.preservation_id)
    else:
        (incomplete / "unfinished.raw").write_bytes(b"retained incomplete object")
        assert manager.verify_preservation(coordination.change_id, preservation.preservation_id) == preservation
        manager.restore_preservation(coordination.change_id, preservation.preservation_id)
        assert (coordination.worktree_path / "shared.txt").read_bytes() == b"base\n"
        assert (incomplete / "unfinished.raw").read_bytes() == b"retained incomplete object"


@pytest.mark.parametrize("error_type", [subprocess.CalledProcessError, subprocess.TimeoutExpired])
def test_nonterminal_recovery_git_failure_retains_failure_journal(tmp_path: Path, error_type) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty bytes\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    error = error_type(1, "git") if error_type is subprocess.CalledProcessError else error_type("git", 10)
    with (
        pytest.raises(error_type) as raised,
        manager._restoration_attempt(preservation, ("shared.txt",)),  # noqa: SLF001
        patch("owlbear_delivery.change_workspace.subprocess.run", side_effect=error),
    ):
        manager._preservation_git("status", "--porcelain", cwd=coordination.worktree_path)  # noqa: SLF001
    assert raised.value is error
    _assert_restoration_failure(manager, preservation)
    assert not tuple((manager.runtime_root / preservation.storage_ref).glob("restoration/*/result.json"))
    assert (coordination.worktree_path / "shared.txt").read_bytes() == b"dirty bytes\n"


@pytest.mark.parametrize("failure", ["intent", "path-result", "result", "restore"])
@pytest.mark.parametrize("drift", ["none", "path", "new-path", "index"])
def test_nonterminal_recovery_restoration_journal_replays_interruption(
    tmp_path: Path, monkeypatch, failure: str, drift: str
) -> None:
    coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    (worktree / "shared.txt").write_bytes(b"dirty preservation\n")
    (worktree / "added.bin").write_bytes(b"\x00new binary")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    index = manager._resolve_managed_index(worktree)  # noqa: SLF001
    index_bytes = manager._read_managed_index(index)  # noqa: SLF001
    coordination_bytes = coordinator.coordination_bytes(coordination.change_id)
    restore = manager._write_worktree_state  # noqa: SLF001

    def fail_record(receipt, operation_id, name, payload):
        if (
            (failure == "intent" and name == "intent.json")
            or (failure == "path-result" and name.startswith("paths/") and name.endswith("/result.json"))
            or (failure == "result" and name == "result.json")
        ):
            msg = "injected receipt interruption"
            raise OSError(msg)
        return ChangeWorkspaceManager._write_restoration_record(  # noqa: SLF001
            manager, receipt, operation_id, name, payload
        )

    def fail_restore(*args, **kwargs):
        restore(*args, **kwargs)
        msg = "injected post-restore interruption"
        raise OSError(msg)

    with monkeypatch.context() as faults:
        faults.setattr(manager, "_write_restoration_record", fail_record)
        if failure == "restore":
            faults.setattr(manager, "_write_worktree_state", fail_restore)
        with pytest.raises(OSError, match="injected"):
            manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert coordinator.coordination_bytes(coordination.change_id) == coordination_bytes
    assert manager._read_managed_index(index) == index_bytes  # noqa: SLF001
    assert manager.verify_preservation(coordination.change_id, preservation.preservation_id) == preservation
    if failure == "intent":
        assert (worktree / "added.bin").read_bytes() == b"\x00new binary"
        assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"
    else:
        _assert_restoration_failure(manager, preservation)

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(intent.recovery_id)
    if drift != "none":
        if drift == "path":
            (worktree / "shared.txt").write_bytes(b"foreign newer edit\n")
        elif drift == "new-path":
            (worktree / "foreign.txt").write_bytes(b"unrelated new file\n")
        else:
            index_bytes = index_bytes[:-1] + bytes([index_bytes[-1] ^ 1])
            index.path.write_bytes(index_bytes)
        before_shared = (worktree / "shared.txt").read_bytes()
        before_added = (worktree / "added.bin").read_bytes() if (worktree / "added.bin").exists() else None
        with pytest.raises(PreservationFenceError, match=r"identity|inventory|index"):
            restarted.restore_preservation(coordination.change_id, preservation.preservation_id)
        assert (worktree / "shared.txt").read_bytes() == before_shared
        assert ((worktree / "added.bin").read_bytes() if (worktree / "added.bin").exists() else None) == before_added
    else:
        _assert_restoration_replay(restarted, preservation)
    assert restarted._read_managed_index(index) == index_bytes  # noqa: SLF001


def _assert_restoration_replay(manager, preservation):
    assert manager.restore_preservation(preservation.change_id, preservation.preservation_id) == preservation
    assert (preservation.worktree_path / "shared.txt").read_bytes() == b"base\n"
    assert not (preservation.worktree_path / "added.bin").exists()
    journal_root = manager.runtime_root / preservation.storage_ref / "restoration"
    results = tuple(journal_root.glob("*/result.json"))
    assert len(results) == 1
    result = json.loads(results[0].read_bytes())
    assert result["preservation_receipt_id"] == preservation.receipt_id
    assert result["paths"] == ["added.bin", "shared.txt"]
    assert len(tuple(journal_root.glob("*/paths/*/intent.json"))) == 2
    assert len(tuple(journal_root.glob("*/paths/*/result.json"))) == 2
    assert all(path.stat().st_mode & 0o077 == 0 for path in journal_root.rglob("*.json"))
    records = {path: path.read_bytes() for path in journal_root.rglob("*.json")}
    manager.restore_preservation(preservation.change_id, preservation.preservation_id)
    assert {path: path.read_bytes() for path in journal_root.rglob("*.json")} == records


def _assert_restoration_failure(manager, preservation):
    failures = tuple((manager.runtime_root / preservation.storage_ref).glob("restoration/*/failure.json"))
    assert len(failures) == 1
    assert json.loads(failures[0].read_bytes())["code"] == "restoration-interrupted"


def _restoration_staging_path(preservation, path: str) -> Path:
    operation_id = _restoration_operation_id(preservation)
    temporary = f".owlbear-preserve-{operation_id}-{hashlib.sha256(path.encode()).hexdigest()[:16]}"
    return preservation.worktree_path / Path(path).parent / temporary


def _restoration_operation_id(preservation) -> str:
    selected = tuple(entry.path for entry in preservation.paths)
    return digest(
        json.dumps(
            {"preservation_receipt_id": preservation.receipt_id, "paths": selected},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )


def _kill_during_restoration_before_replace(tmp_path: Path, preservation, repository: Path) -> None:
    script = (
        "import os, signal, sys\n"
        "from pathlib import Path\n"
        "from owlbear_delivery.change_workspace import ChangeWorkspaceManager, PortfolioCoordinator\n"
        "class TestPreservationProvenanceProvider:\n"
        "    def verify(self, **kwargs):\n"
        "        return kwargs['evidence']\n"
        "root = Path(sys.argv[1])\n"
        "repository = Path(sys.argv[2])\n"
        "coordinator = PortfolioCoordinator(root / 'state')\n"
        "coordinator.record_verified_exclusion(sys.argv[5])\n"
        "manager = ChangeWorkspaceManager(\n"
        "    repository, root / 'worktrees', coordinator, 'release', remote='origin',\n"
        "    preservation_provenance_provider=TestPreservationProvenanceProvider(),\n"
        ")\n"
        "os.replace = lambda *args, **kwargs: os.kill(os.getpid(), signal.SIGKILL)\n"
        "manager.restore_preservation(sys.argv[3], sys.argv[4])\n"
    )
    result = subprocess.run(  # noqa: S603 - the child is a controlled test process.
        (
            sys.executable,
            "-c",
            script,
            str(tmp_path),
            str(repository),
            preservation.change_id,
            preservation.preservation_id,
            preservation.recovery_id,
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == -signal.SIGKILL, result.stderr


def _kill_during_restoration_intent_link(tmp_path: Path, preservation, repository: Path) -> None:
    script = (
        "import os, signal, sys\n"
        "from pathlib import Path\n"
        "from owlbear_delivery.change_workspace import ChangeWorkspaceManager, PortfolioCoordinator\n"
        "class TestPreservationProvenanceProvider:\n"
        "    def verify(self, **kwargs):\n"
        "        return kwargs['evidence']\n"
        "root = Path(sys.argv[1])\n"
        "repository = Path(sys.argv[2])\n"
        "coordinator = PortfolioCoordinator(root / 'state')\n"
        "coordinator.record_verified_exclusion(sys.argv[5])\n"
        "manager = ChangeWorkspaceManager(\n"
        "    repository, root / 'worktrees', coordinator, 'release', remote='origin',\n"
        "    preservation_provenance_provider=TestPreservationProvenanceProvider(),\n"
        ")\n"
        "os.link = lambda *args, **kwargs: os.kill(os.getpid(), signal.SIGKILL)\n"
        "manager.restore_preservation(sys.argv[3], sys.argv[4])\n"
    )
    result = subprocess.run(  # noqa: S603 - the child is a controlled test process.
        (
            sys.executable,
            "-c",
            script,
            str(tmp_path),
            str(repository),
            preservation.change_id,
            preservation.preservation_id,
            preservation.recovery_id,
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == -signal.SIGKILL, result.stderr


def _kill_after_restoration_replace_before_private_unlink(
    tmp_path: Path, preservation, repository: Path
) -> None:
    script = (
        "import os, signal, sys\n"
        "from pathlib import Path\n"
        "from owlbear_delivery.change_workspace import ChangeWorkspaceManager, PortfolioCoordinator\n"
        "class TestPreservationProvenanceProvider:\n"
        "    def verify(self, **kwargs):\n"
        "        return kwargs['evidence']\n"
        "root = Path(sys.argv[1])\n"
        "repository = Path(sys.argv[2])\n"
        "coordinator = PortfolioCoordinator(root / 'state')\n"
        "coordinator.record_verified_exclusion(sys.argv[5])\n"
        "manager = ChangeWorkspaceManager(\n"
        "    repository, root / 'worktrees', coordinator, 'release', remote='origin',\n"
        "    preservation_provenance_provider=TestPreservationProvenanceProvider(),\n"
        ")\n"
        "def kill_before_private_unlink(*args, **kwargs):\n"
        "    os.kill(os.getpid(), signal.SIGKILL)\n"
        "manager._remove_private_staging = kill_before_private_unlink\n"
        "manager.restore_preservation(sys.argv[3], sys.argv[4])\n"
    )
    result = subprocess.run(  # noqa: S603 - the child is a controlled test process.
        (
            sys.executable,
            "-c",
            script,
            str(tmp_path),
            str(repository),
            preservation.change_id,
            preservation.preservation_id,
            preservation.recovery_id,
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == -signal.SIGKILL, result.stderr


def _kill_during_private_staging_write(tmp_path: Path, preservation, repository: Path) -> None:
    ready = tmp_path / "private-stage-write-ready"
    script = (
        "import os, signal, sys, time\n"
        "from pathlib import Path\n"
        "from owlbear_delivery.change_workspace import ChangeWorkspaceManager, PortfolioCoordinator\n"
        "class TestPreservationProvenanceProvider:\n"
        "    def verify(self, **kwargs):\n"
        "        return kwargs['evidence']\n"
        "root = Path(sys.argv[1])\n"
        "repository = Path(sys.argv[2])\n"
        "ready = Path(sys.argv[6])\n"
        "real_fdopen = os.fdopen\n"
        "def fdopen(fd, *args, **kwargs):\n"
        "    handle = real_fdopen(fd, *args, **kwargs)\n"
        "    try:\n"
        "        name = os.readlink('/proc/self/fd/' + str(fd))\n"
        "    except OSError:\n"
        "        name = ''\n"
        "    if not Path(name).name.startswith('stage-'):\n"
        "        return handle\n"
        "    class PartialWrite:\n"
        "        def __init__(self, wrapped):\n"
        "            self.wrapped = wrapped\n"
        "        def __enter__(self):\n"
        "            return self\n"
        "        def __exit__(self, *exc):\n"
        "            return self.wrapped.__exit__(*exc)\n"
        "        def write(self, content):\n"
        "            count = self.wrapped.write(content[:2])\n"
        "            self.wrapped.flush()\n"
        "            ready.write_text(str(count))\n"
        "            while True:\n"
        "                time.sleep(1)\n"
        "        def flush(self):\n"
        "            return self.wrapped.flush()\n"
        "    return PartialWrite(handle)\n"
        "os.fdopen = fdopen\n"
        "coordinator = PortfolioCoordinator(root / 'state')\n"
        "coordinator.record_verified_exclusion(sys.argv[5])\n"
        "manager = ChangeWorkspaceManager(\n"
        "    repository, root / 'worktrees', coordinator, 'release', remote='origin',\n"
        "    preservation_provenance_provider=TestPreservationProvenanceProvider(),\n"
        ")\n"
        "manager.restore_preservation(sys.argv[3], sys.argv[4])\n"
    )
    process = subprocess.Popen(  # noqa: S603 - the child is a controlled test process.
        (
            sys.executable,
            "-c",
            script,
            str(tmp_path),
            str(repository),
            preservation.change_id,
            preservation.preservation_id,
            preservation.recovery_id,
            str(ready),
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for _ in range(100):
        if ready.exists():
            break
        time.sleep(0.01)
    if not ready.exists():
        os.kill(process.pid, signal.SIGKILL)
        _stdout, stderr = process.communicate()
        pytest.fail(f"private staging child did not reach partial-write gate: {stderr}")
    os.kill(process.pid, signal.SIGKILL)
    _stdout, stderr = process.communicate()
    assert process.returncode == -signal.SIGKILL, stderr


def test_nonterminal_recovery_replays_after_operation_intent_publication_death(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    worktree.joinpath("shared.txt").write_bytes(b"dirty preservation\n")
    index = manager._resolve_managed_index(worktree)  # noqa: SLF001
    index_bytes = manager._read_managed_index(index)  # noqa: SLF001
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)

    _kill_during_restoration_intent_link(tmp_path, preservation, manager.repository)
    operation_dir = (
        manager.runtime_root / preservation.storage_ref / "restoration" / _restoration_operation_id(preservation)
    )
    orphaned = tuple(operation_dir.glob(".tmp-*"))
    assert len(orphaned) == 1
    orphan_metadata = orphaned[0].lstat()
    orphan_bytes = orphaned[0].read_bytes()
    orphan_identity = (orphan_metadata.st_dev, orphan_metadata.st_ino)
    assert stat.S_ISREG(orphan_metadata.st_mode)
    assert orphan_metadata.st_nlink == 1
    assert orphan_metadata.st_size <= 64 * 1024 * 1024
    assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"
    assert manager._read_managed_index(index) == index_bytes  # noqa: SLF001

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(preservation.recovery_id)
    exposed = _restoration_staging_path(preservation, "shared.txt")
    exposed.write_bytes(b"foreign worktree artifact\n")
    with pytest.raises(PreservationFenceError, match="worktree exposure"):
        restarted.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"
    assert restarted._read_managed_index(index) == index_bytes  # noqa: SLF001
    exposed.unlink()
    assert restarted.restore_preservation(coordination.change_id, preservation.preservation_id) == preservation
    assert (worktree / "shared.txt").read_bytes() == b"base\n"
    assert restarted._read_managed_index(index) == index_bytes  # noqa: SLF001
    assert orphaned[0].read_bytes() == orphan_bytes
    replayed_orphan_metadata = orphaned[0].lstat()
    assert (replayed_orphan_metadata.st_dev, replayed_orphan_metadata.st_ino) == orphan_identity


@pytest.mark.parametrize("artifact", ["symlink", "hardlink", "permissions", "oversize", "too-many"])
def test_nonterminal_recovery_rejects_untrusted_incomplete_operation_artifacts(
    tmp_path: Path, artifact: str
) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    worktree.joinpath("shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    operation_dir = (
        manager.runtime_root / preservation.storage_ref / "restoration" / _restoration_operation_id(preservation)
    )
    operation_dir.mkdir(parents=True)
    artifact_path = operation_dir / f".tmp-{'a' * 24}"
    if artifact == "symlink":
        target = tmp_path / "foreign-source"
        target.write_bytes(b"foreign\n")
        artifact_path.symlink_to(target)
    elif artifact == "hardlink":
        target = tmp_path / "foreign-source"
        target.write_bytes(b"foreign\n")
        target.chmod(0o600)
        os.link(target, artifact_path)
    elif artifact == "permissions":
        artifact_path.write_bytes(b"foreign\n")
        artifact_path.chmod(0o640)
    elif artifact == "oversize":
        with artifact_path.open("wb") as handle:
            handle.truncate(64 * 1024 * 1024 + 1)
        artifact_path.chmod(0o600)
    else:
        for index in range(257):
            (operation_dir / f".tmp-{index:024x}").touch(mode=0o600)
    artifact_metadata = artifact_path.lstat() if artifact != "too-many" else None

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(preservation.recovery_id)
    with pytest.raises(PreservationFenceError, match="intent is missing with artifacts"):
        restarted.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"
    if artifact == "too-many":
        assert len(tuple(operation_dir.iterdir())) == 257
    else:
        assert artifact_metadata is not None
        current_metadata = artifact_path.lstat()
        assert (current_metadata.st_dev, current_metadata.st_ino) == (
            artifact_metadata.st_dev,
            artifact_metadata.st_ino,
        )


def test_nonterminal_recovery_replays_operation_owned_staging_after_subprocess_death(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    worktree.joinpath("shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)

    _kill_during_restoration_before_replace(tmp_path, preservation, manager.repository)
    staging = _restoration_staging_path(preservation, "shared.txt")
    assert staging.read_bytes() == b"base\n"
    assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(preservation.recovery_id)
    assert restarted.restore_preservation(coordination.change_id, preservation.preservation_id) == preservation
    assert (worktree / "shared.txt").read_bytes() == b"base\n"
    assert not staging.exists()


def test_nonterminal_recovery_cleans_private_source_after_replace_death(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    worktree.joinpath("shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)

    _kill_during_restoration_before_replace(tmp_path, preservation, manager.repository)
    _kill_after_restoration_replace_before_private_unlink(tmp_path, preservation, manager.repository)
    target = worktree / "shared.txt"
    assert target.stat().st_nlink == 2

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(preservation.recovery_id)
    assert restarted.restore_preservation(coordination.change_id, preservation.preservation_id) == preservation
    assert target.read_bytes() == b"base\n"
    assert target.stat().st_nlink == 1


def test_nonterminal_recovery_replays_after_partial_private_staging_write_death(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    worktree.joinpath("shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)

    _kill_during_private_staging_write(tmp_path, preservation, manager.repository)
    staging = _restoration_staging_path(preservation, "shared.txt")
    assert not staging.exists()
    assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(preservation.recovery_id)
    assert restarted.restore_preservation(coordination.change_id, preservation.preservation_id) == preservation
    assert (worktree / "shared.txt").read_bytes() == b"base\n"
    assert not staging.exists()


def test_nonterminal_recovery_retains_staging_evidence_when_private_source_disappears(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    worktree.joinpath("shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)

    _kill_during_restoration_before_replace(tmp_path, preservation, manager.repository)
    staging = _restoration_staging_path(preservation, "shared.txt")
    staging_record = next(
        (manager.runtime_root / preservation.storage_ref / "restoration").glob("*/paths/*/staging.json")
    )
    staging_payload = json.loads(staging_record.read_bytes())
    (staging_record.parent / staging_payload["source"]).unlink()
    staging.unlink()

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(preservation.recovery_id)
    with pytest.raises(PreservationFenceError, match="staging source is missing"):
        restarted.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert staging_record.exists()
    assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"


@pytest.mark.parametrize("orphan", ["empty", "artifact"])
def test_nonterminal_recovery_handles_empty_operation_directory_without_authorizing_artifacts(
    tmp_path: Path, orphan: str
) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    worktree.joinpath("shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    selected = tuple(entry.path for entry in preservation.paths)
    operation_id = digest(
        json.dumps(
            {"preservation_receipt_id": preservation.receipt_id, "paths": selected},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    operation_dir = manager.runtime_root / preservation.storage_ref / "restoration" / operation_id
    operation_dir.mkdir(parents=True)
    if orphan == "artifact":
        (operation_dir / "orphan").write_bytes(b"unowned")

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(preservation.recovery_id)
    if orphan == "artifact":
        with pytest.raises(PreservationFenceError, match="intent is missing with artifacts"):
            restarted.restore_preservation(coordination.change_id, preservation.preservation_id)
        assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"
    else:
        assert restarted.restore_preservation(coordination.change_id, preservation.preservation_id) == preservation
        assert (worktree / "shared.txt").read_bytes() == b"base\n"


@pytest.mark.parametrize("mutation", ["bytes", "same-bytes", "same-bytes-foreign", "type", "index"])
def test_nonterminal_recovery_rejects_changed_operation_owned_staging_or_index(
    tmp_path: Path, mutation: str
) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    worktree.joinpath("shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    _kill_during_restoration_before_replace(tmp_path, preservation, manager.repository)
    staging = _restoration_staging_path(preservation, "shared.txt")
    index = manager._resolve_managed_index(worktree)  # noqa: SLF001
    original_index = manager._read_managed_index(index)  # noqa: SLF001
    if mutation == "bytes":
        staging.write_bytes(b"foreign staging bytes\n")
    elif mutation == "same-bytes":
        staging.write_bytes(b"base\n")
    elif mutation == "same-bytes-foreign":
        staging.unlink()
        staging.write_bytes(b"base\n")
    elif mutation == "type":
        staging.unlink()
        staging.mkdir()
    else:
        index.path.write_bytes(original_index[:-1] + bytes([original_index[-1] ^ 1]))

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(preservation.recovery_id)
    with pytest.raises(PreservationFenceError, match=r"staging|index"):
        restarted.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"


def test_nonterminal_recovery_rejects_foreign_collision_at_owned_staging_name(tmp_path: Path) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    worktree.joinpath("shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    staging = _restoration_staging_path(preservation, "shared.txt")
    staging.write_bytes(b"foreign collision\n")

    restarted_coordinator, restarted = _manager(tmp_path, manager.repository)
    restarted_coordinator.record_verified_exclusion(preservation.recovery_id)
    with pytest.raises(PreservationFenceError, match="inventory"):
        restarted.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert staging.read_bytes() == b"foreign collision\n"
    assert (worktree / "shared.txt").read_bytes() == b"dirty preservation\n"


@pytest.mark.parametrize("failure", ["before-object", "after-object", "before-manifest", "after-manifest"])
def test_nonterminal_recovery_capture_failure_keeps_bytes_and_replays(tmp_path: Path, failure: str) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    (worktree / "shared.txt").write_bytes(b"preserved raw bytes\n")
    index = manager._resolve_managed_index(worktree)  # noqa: SLF001
    index_bytes = manager._read_managed_index(index)  # noqa: SLF001
    refs = _git(manager.repository, "show-ref")

    def interrupted_write(root_fd, path, content, **kwargs):
        selected = path.name == "manifest.json" if "manifest" in failure else path.suffix == ".raw"
        msg = "injected preservation interruption"
        if selected and failure.startswith("before"):
            raise OSError(msg)
        write_contained(root_fd, path, content, **kwargs)
        if selected and failure.startswith("after"):
            raise OSError(msg)

    with (
        patch("owlbear_delivery.change_workspace.write_contained", side_effect=interrupted_write),
        pytest.raises(OSError, match="injected"),
    ):
        manager.capture_preservation(coordination.change_id, intent.recovery_id)
    assert (worktree / "shared.txt").read_bytes() == b"preserved raw bytes\n"
    assert manager._read_managed_index(index) == index_bytes  # noqa: SLF001
    assert _git(manager.repository, "show-ref") == refs
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    assert manager.verify_preservation(coordination.change_id, preservation.preservation_id) == preservation
    manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert (worktree / "shared.txt").read_bytes() == b"base\n"
    assert manager._read_managed_index(index) == index_bytes  # noqa: SLF001


def test_nonterminal_recovery_restore_fsync_failure_cannot_publish_success(tmp_path: Path, monkeypatch) -> None:
    _coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    worktree = coordination.worktree_path
    (worktree / "shared.txt").write_bytes(b"dirty bytes\n")
    preservation = manager.capture_preservation(coordination.change_id, intent.recovery_id)
    parent_inode = worktree.stat().st_ino
    real_fsync = os.fsync

    def fail_parent_sync(descriptor):
        if os.fstat(descriptor).st_ino == parent_inode:
            msg = "injected worktree directory fsync failure"
            raise OSError(msg)
        real_fsync(descriptor)

    with monkeypatch.context() as faults:
        faults.setattr(os, "fsync", fail_parent_sync)
        with pytest.raises(OSError, match="fsync"):
            manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    journal_root = manager.runtime_root / preservation.storage_ref / "restoration"
    assert not tuple(journal_root.glob("*/result.json"))
    assert not tuple(journal_root.glob("*/paths/*/result.json"))
    assert tuple(journal_root.glob("*/failure.json"))
    manager.restore_preservation(coordination.change_id, preservation.preservation_id)
    assert (worktree / "shared.txt").read_bytes() == b"base\n"
    assert len(tuple(journal_root.glob("*/result.json"))) == 1


@pytest.mark.parametrize("operation", ["ensure", "recover", "validate_recovery"])
def test_malformed_coordination_is_not_treated_as_missing_authority(tmp_path: Path, operation: str) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("change-a")
    path = tmp_path / "state/coordination/changes/change-a.json"
    path.write_bytes(b"{")
    shutil.rmtree(coordination.worktree_path)
    with pytest.raises(CoordinationConflictError, match="unreadable or invalid"):
        getattr(manager, operation)("change-a", recovery_reviewed_head=initial)
    assert path.read_bytes() == b"{"
    assert not coordination.worktree_path.exists()
    assert _git(repository, "rev-parse", "HEAD") == initial


def _workspace_bytes(repository: Path, state_root: Path) -> tuple[str, str, tuple[tuple[str, bytes], ...]]:
    state_files = tuple(
        sorted(
            (str(path.relative_to(state_root)), path.read_bytes()) for path in state_root.rglob("*") if path.is_file()
        )
    )
    return (
        _git(repository, "show-ref"),
        _git(repository, "worktree", "list", "--porcelain"),
        state_files,
    )


def test_snapshot_design_package_commits_managed_change_worktree_only(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("snapshot-change")
    package_files = {
        "authority.json": b'{"authority":true}\n',
        "design.md": b"# Design\n",
        "intent.md": b"# Intent\n",
        "manifest.json": b'{"manifest":true}\n',
    }
    before_status = _git(repository, "status", "--porcelain")

    receipt = manager.snapshot_design_package(
        coordination.change_id,
        "a" * 64,
        package_files,
        "snapshot-operation",
    )
    replayed = manager.snapshot_design_package(
        coordination.change_id,
        "a" * 64,
        package_files,
        "snapshot-operation",
    )

    assert isinstance(receipt, ChangeDesignPackageSnapshotReceipt)
    assert replayed == receipt
    assert receipt.previous_head == initial
    assert receipt.snapshot_head != initial
    assert coordinator.show(coordination.change_id).last_reviewed_commit == receipt.snapshot_head
    assert manager.source_head(coordination.change_id) == receipt.snapshot_head
    assert _git(repository, "rev-parse", "HEAD") == initial
    assert _git(repository, "status", "--porcelain") == before_status
    relative_paths = tuple(f".owlbear/delivery/packages/{coordination.change_id}/{name}" for name in package_files)
    assert (
        tuple(
            _git(
                coordination.worktree_path,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                receipt.snapshot_head,
            ).splitlines()
        )
        == relative_paths
    )
    for name, relative_path in zip(package_files, relative_paths, strict=True):
        assert _git(
            coordination.worktree_path, "show", f"{receipt.snapshot_head}:{relative_path}"
        ).encode() == package_files[name].rstrip(b"\n")


def test_snapshot_design_package_revises_with_receipt_fence_and_replays(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("snapshot-revision")
    original_files = {
        "authority.json": b'{"authority":"old"}\n',
        "design.md": b"# Old design\n",
        "intent.md": b"# Old intent\n",
        "manifest.json": b'{"manifest":"old"}\n',
    }
    revised_files = {
        "authority.json": b'{"authority":"new"}\n',
        "design.md": b"# New design\n",
        "intent.md": b"# New intent\n",
        "manifest.json": b'{"manifest":"new"}\n',
    }

    original = manager.snapshot_design_package(
        coordination.change_id,
        "a" * 64,
        original_files,
        "snapshot-revision-old",
    )
    revised = manager.snapshot_design_package(
        coordination.change_id,
        "b" * 64,
        revised_files,
        "snapshot-revision-new",
        expected_existing_receipt_id=original.receipt_id,
    )
    replayed = manager.snapshot_design_package(
        coordination.change_id,
        "b" * 64,
        revised_files,
        "snapshot-revision-new",
        expected_existing_receipt_id=original.receipt_id,
    )

    assert revised == replayed
    assert revised.package_id == "b" * 64
    assert revised.previous_head == original.snapshot_head
    assert revised.snapshot_head != original.snapshot_head
    assert (
        _git(
            coordination.worktree_path,
            "merge-base",
            "--is-ancestor",
            original.snapshot_head,
            revised.snapshot_head,
        )
        == ""
    )
    assert coordinator.show(coordination.change_id).design_package_snapshot == revised

    with pytest.raises(CoordinationConflictError, match="differs from the expected receipt"):
        manager.snapshot_design_package(
            coordination.change_id,
            "c" * 64,
            revised_files,
            "snapshot-revision-stale",
            expected_existing_receipt_id=original.receipt_id,
        )


def test_snapshot_design_package_revises_after_commit_before_receipt(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("snapshot-revision-replay")
    original_files = {
        "authority.json": b'{"authority":"old"}\n',
        "design.md": b"# Old design\n",
        "intent.md": b"# Old intent\n",
        "manifest.json": b'{"manifest":"old"}\n',
    }
    revised_files = {
        "authority.json": b'{"authority":"new"}\n',
        "design.md": b"# New design\n",
        "intent.md": b"# New intent\n",
        "manifest.json": b'{"manifest":"new"}\n',
    }
    original = manager.snapshot_design_package(
        coordination.change_id,
        "a" * 64,
        original_files,
        "snapshot-revision-replay-old",
    )
    original_update = coordinator.update
    update_count = 0
    failure_message = "simulated replacement receipt failure"

    def fail_replacement_receipt(updated: ChangeCoordination, *, lock=None) -> ChangeCoordination:
        nonlocal update_count
        update_count += 1
        if update_count == 1:
            return original_update(updated, lock=lock)
        raise RuntimeError(failure_message)

    with (
        patch.object(coordinator, "update", side_effect=fail_replacement_receipt),
        pytest.raises(RuntimeError, match=failure_message),
    ):
        manager.snapshot_design_package(
            coordination.change_id,
            "b" * 64,
            revised_files,
            "snapshot-revision-replay-new",
            expected_existing_receipt_id=original.receipt_id,
        )

    interrupted = coordinator.show(coordination.change_id)
    assert interrupted.design_package_snapshot == original
    assert interrupted.design_package_snapshot_intent is not None
    recovered = manager.snapshot_design_package(
        coordination.change_id,
        "b" * 64,
        revised_files,
        "snapshot-revision-replay-new",
        expected_existing_receipt_id=original.receipt_id,
    )

    assert recovered.package_id == "b" * 64
    assert coordinator.show(coordination.change_id).design_package_snapshot == recovered
    assert coordinator.show(coordination.change_id).design_package_snapshot_intent is None


def test_snapshot_design_package_replays_after_commit_before_receipt(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("snapshot-replay")
    package_files = {
        "authority.json": b'{"authority":true}\n',
        "design.md": b"# Design\n",
        "intent.md": b"# Intent\n",
        "manifest.json": b'{"manifest":true}\n',
    }
    original_update = coordinator.update
    update_count = 0
    failure_message = "simulated receipt failure"

    def fail_receipt_update(updated: ChangeCoordination, *, lock=None) -> ChangeCoordination:
        nonlocal update_count
        update_count += 1
        if update_count == 2:
            raise RuntimeError(failure_message)
        return original_update(updated, lock=lock)

    with (
        patch.object(coordinator, "update", side_effect=fail_receipt_update),
        pytest.raises(RuntimeError, match=failure_message),
    ):
        manager.snapshot_design_package(
            coordination.change_id,
            "a" * 64,
            package_files,
            "snapshot-replay-operation",
        )

    interrupted = coordinator.show(coordination.change_id)
    assert interrupted.design_package_snapshot_intent is not None
    assert interrupted.design_package_snapshot is None
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") != initial
    assert _git(coordination.worktree_path, "status", "--porcelain") == ""

    receipt = manager.snapshot_design_package(
        coordination.change_id,
        "a" * 64,
        package_files,
        "snapshot-replay-operation",
    )

    assert receipt.snapshot_head == _git(coordination.worktree_path, "rev-parse", "HEAD")
    assert coordinator.show(coordination.change_id).design_package_snapshot == receipt
    assert coordinator.show(coordination.change_id).design_package_snapshot_intent is None
    assert receipt.previous_head == initial


def test_list_retained_worktrees_is_sorted_and_batches_git_reads(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    first = manager.ensure("change-b")
    second = manager.ensure("change-a")
    _git(repository, "update-ref", "refs/heads/owlbear/change/nested-only/s1", initial)
    before_coordination = tuple(
        sorted((path.name, path.read_bytes()) for path in (tmp_path / "state/coordination/changes").iterdir())
    )
    before_worktrees = _git(repository, "worktree", "list", "--porcelain")
    original_run_git = manager._run_git  # noqa: SLF001

    with patch.object(manager, "_run_git", wraps=original_run_git) as run_git:
        retained = manager.list_retained()

    assert [item.change_id for item in retained] == ["change-a", "change-b"]
    assert all(item.coordination_registered and item.git_registered and item.worktree_present for item in retained)
    assert retained[0].worktree_path == second.worktree_path.resolve()
    assert retained[1].worktree_path == first.worktree_path.resolve()
    assert retained[0].branch_head == initial
    assert retained[0].worktree_head == initial
    assert retained[0].worktree_branch == "owlbear/change/change-a"
    assert all("/s1" not in item.branch for item in retained)
    assert [call.args[:3] for call in run_git.call_args_list] == [
        ("--no-optional-locks", "worktree", "list"),
        ("--no-optional-locks", "for-each-ref", "--format=%(refname)%00%(objectname)"),
        ("--no-optional-locks", "status", "--porcelain=v1"),
        ("--no-optional-locks", "status", "--porcelain=v1"),
    ]
    assert before_worktrees == _git(repository, "worktree", "list", "--porcelain")
    assert before_coordination == tuple(
        sorted((path.name, path.read_bytes()) for path in (tmp_path / "state/coordination/changes").iterdir())
    )


@pytest.mark.parametrize("remote", ["origin", "upstream"])
def test_ensure_bases_new_changes_on_remote_tracking_target(tmp_path: Path, remote: str) -> None:
    repository, initial = _repository(tmp_path)
    if remote != "origin":
        _git(repository, "update-ref", f"refs/remotes/{remote}/release", initial)
    (repository / "shared.txt").write_text("local-only\n", encoding="utf-8")
    _git(repository, "add", "shared.txt")
    _git(repository, "commit", "-m", "advance local target")
    _git(repository, "update-ref", "refs/heads/release", "HEAD")
    local_target_head = _git(repository, "rev-parse", "refs/heads/release")
    _coordinator, manager = _manager(tmp_path, repository, remote=remote)

    coordination = manager.ensure(f"remote-target-{remote}")

    assert local_target_head != initial
    assert coordination.target_head == initial
    assert coordination.publication_base_head == initial
    assert _git(repository, "rev-parse", coordination.branch) == initial


def test_refresh_target_does_not_advance_publication_baseline(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("refresh-baseline")
    (repository / "target.txt").write_text("target\n", encoding="utf-8")
    _git(repository, "add", "target.txt")
    _git(repository, "commit", "-m", "advance target")
    advanced_target = _git(repository, "rev-parse", "HEAD")
    _git(repository, "update-ref", "refs/remotes/origin/release", advanced_target)

    refreshed = manager.refresh_integration_target(coordination.change_id)

    assert refreshed.target_head == advanced_target
    assert refreshed.publication_base_head == initial


def test_legacy_publication_baseline_recovers_once_and_replays(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("legacy-baseline")
    (coordination.worktree_path / "workflow.txt").write_text("change\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "workflow.txt")
    _git(coordination.worktree_path, "commit", "-m", "reviewed Change")
    reviewed_head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (tmp_path / "state/coordination/changes/legacy-baseline.json").write_text(json.dumps(payload), encoding="utf-8")
    coordinator.update(
        coordination.model_copy(update={"last_reviewed_commit": reviewed_head, "publication_base_head": None})
    )

    receipt = manager.recover_publication_baseline(
        coordination.change_id,
        reviewed_head,
        initial,
        "recover-baseline",
    )
    replayed = manager.recover_publication_baseline(
        coordination.change_id,
        reviewed_head,
        initial,
        "recover-baseline",
    )

    assert replayed == receipt
    recovered = coordinator.show(coordination.change_id)
    assert recovered.publication_base_head == initial
    assert recovered.publication_baseline_recovery == receipt
    with pytest.raises(CoordinationConflictError, match="different authority"):
        manager.recover_publication_baseline(coordination.change_id, reviewed_head, initial, "other-operation")


@pytest.mark.parametrize("custody", ["writer", "publication lease"])
def test_publication_baseline_recovery_requires_idle_change(tmp_path: Path, custody: str) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"busy-{custody.replace(' ', '-')}")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (tmp_path / f"state/coordination/changes/{coordination.change_id}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    if custody == "writer":
        coordinator.acquire(
            coordination.change_id,
            ChangeWriter(
                **_identity(coordination.change_id).model_dump(),
                job_id=1,
                kind="build",
            ),
        )
    else:
        with coordinator.publication_lock(coordination.change_id) as lock:
            coordinator.reserve_publication(
                coordination.change_id,
                PublicationLease(
                    operation_id="busy-lease",
                    owner_id="busy-owner",
                    expires_at="2026-08-02T00:10:00Z",
                ),
                lock,
                now="2026-08-02T00:00:00Z",
            )

    with pytest.raises(CoordinationConflictError, match="idle Change"):
        manager.recover_publication_baseline(coordination.change_id, initial, initial, "recover-busy")


@pytest.mark.parametrize("baseline_kind", ["missing", "non-ancestor"])
def test_publication_baseline_recovery_rejects_unusable_baseline(tmp_path: Path, baseline_kind: str) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"invalid-{baseline_kind}")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (tmp_path / f"state/coordination/changes/{coordination.change_id}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    baseline = "f" * 40
    if baseline_kind == "non-ancestor":
        baseline = _git(repository, "commit-tree", f"{initial}^{{tree}}", "-m", "unrelated baseline")

    with pytest.raises(PublicationBaselineUnavailableError):
        manager.recover_publication_baseline(coordination.change_id, initial, baseline, f"recover-{baseline_kind}")

    recovered = coordinator.show(coordination.change_id)
    assert recovered.publication_base_head is None
    assert recovered.publication_baseline_recovery is None


def test_generic_update_cannot_replace_or_erase_known_publication_baseline(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("immutable-baseline")

    with pytest.raises(CoordinationConflictError, match="explicit recovery"):
        coordinator.update(coordination.model_copy(update={"publication_base_head": None}))
    with pytest.raises(CoordinationConflictError, match="explicit recovery"):
        coordinator.update(coordination.model_copy(update={"publication_base_head": "b" * 40}))

    assert coordinator.show(coordination.change_id).publication_base_head == initial


def test_legacy_publication_summary_fails_closed_without_baseline(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("unknown-baseline")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (repository / "target.txt").write_text("target\n", encoding="utf-8")
    _git(repository, "add", "target.txt")
    _git(repository, "commit", "-m", "advance target")
    target_head = _git(repository, "rev-parse", "HEAD")
    payload["target_head"] = target_head
    (tmp_path / "state/coordination/changes/unknown-baseline.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PublicationBaselineUnavailableError, match="explicitly known baseline"):
        manager.repository_automation_paths(coordination.change_id, initial)


def test_repository_automation_paths_reports_changed_workflow_and_action_files(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    (repository / ".github/workflows").mkdir(parents=True)
    (repository / ".github/workflows/old.yml").write_text("name: old\n", encoding="utf-8")
    (repository / "action.yml").write_text("name: root\n", encoding="utf-8")
    (repository / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "seed automation")
    baseline = _git(repository, "rev-parse", "HEAD")
    _git(repository, "branch", "-f", "release", baseline)
    _git(repository, "update-ref", "refs/remotes/origin/release", baseline)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("automation-paths")

    worktree = coordination.worktree_path
    _git(worktree, "mv", ".github/workflows/old.yml", ".github/workflows/new.yml")
    _git(worktree, "rm", "action.yml")
    (worktree / ".github/workflows/created.yaml").write_text("name: created\n", encoding="utf-8")
    (worktree / "nested").mkdir()
    (worktree / "nested/action.yaml").write_text("name: nested\n", encoding="utf-8")
    (worktree / "ignored.txt").write_text("changed\n", encoding="utf-8")
    _git(worktree, "add", ".")
    _git(worktree, "commit", "-m", "change automation")
    exact_head = _git(worktree, "rev-parse", "HEAD")

    assert manager.repository_automation_paths(coordination.change_id, exact_head) == (
        ".github/workflows/created.yaml",
        ".github/workflows/new.yml",
        ".github/workflows/old.yml",
        "action.yml",
        "nested/action.yaml",
    )


def test_list_retained_worktrees_returns_empty_without_coordination_store(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator = PortfolioCoordinator(tmp_path / "state")
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "release")
    assert coordinator.list_registered() == ()
    assert manager.list_retained() == ()


def test_cleanup_removes_exact_worktree_keeps_branch_and_replays_receipt(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("cleanup-change")

    receipt = manager.cleanup(coordination.change_id)

    assert receipt.change_id == coordination.change_id
    assert receipt.branch_head == initial
    assert receipt.worktree_path == coordination.worktree_path.resolve()
    assert not coordination.worktree_path.exists()
    assert _git_ref_exists(repository, coordination.branch)
    assert _git(repository, "rev-parse", coordination.branch) == initial
    assert coordinator.show(coordination.change_id).worktree_cleanup == receipt
    assert manager.cleanup(coordination.change_id) == receipt
    assert manager.list_retained() == ()


def test_cleanup_refuses_dirty_worktree_without_discarding_content(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("dirty-cleanup")
    dirty_file = coordination.worktree_path / "uncommitted.txt"
    dirty_file.write_text("preserve me\n", encoding="utf-8")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.cleanup(coordination.change_id)

    assert ChangeWorktreeAttentionCode.WORKTREE_DIRTY in raised.value.attention
    assert dirty_file.read_text(encoding="utf-8") == "preserve me\n"
    assert coordination.worktree_path.exists()
    assert coordinator.show(coordination.change_id).worktree_cleanup is None


def test_restart_refuses_dirty_worktree_before_creating_attempt_ref(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("dirty-restart")
    writer = ChangeWriter(
        **_identity(coordination.change_id).model_dump(),
        job_id=1,
        kind="build",
    )
    coordinator.acquire(coordination.change_id, writer)
    dirty_file = coordination.worktree_path / "uncommitted.txt"
    dirty_file.write_text("preserve me\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="clean committed change worktree"):
        manager.restart(coordination.change_id, writer.attempt_id, initial)

    assert dirty_file.read_text(encoding="utf-8") == "preserve me\n"
    assert not _git_ref_exists(
        repository,
        f"refs/owlbear/attempts/{coordination.change_id}/{writer.attempt_id}",
    )
    assert coordinator.show(coordination.change_id).writer == writer


def test_quarantine_dirty_worktree_preserves_all_nonignored_bytes_and_environment(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    (repository / ".gitignore").write_text(".venv/\nnode_modules/\ndist/\n", encoding="utf-8")
    (repository / "deleted.txt").write_text("delete me\n", encoding="utf-8")
    (repository / "rename-source.txt").write_text("rename me\n", encoding="utf-8")
    _git(repository, "add", ".gitignore", "deleted.txt", "rename-source.txt")
    _git(repository, "commit", "-m", "seed quarantine boundaries")
    base_head = _git(repository, "rev-parse", "HEAD")
    _git(repository, "branch", "-f", "release", base_head)
    _git(repository, "update-ref", "refs/remotes/origin/release", base_head)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("quarantine-change")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    worktree = coordination.worktree_path
    (worktree / "shared.txt").write_bytes(b"staged binary\x00\xff")
    _git(worktree, "add", "shared.txt")
    (worktree / "new.txt").write_bytes(b"untracked binary\x00\xfe")
    _git(worktree, "mv", "rename-source.txt", "rename-target.txt")
    (worktree / "deleted.txt").unlink()
    (worktree / "uv.lock").write_bytes(b"lock\x00\xff")
    for directory in (".venv", "node_modules", "dist"):
        path = worktree / directory
        path.mkdir()
        (path / "keep.bin").write_bytes(b"ignored environment")

    receipt = manager.quarantine_dirty_worktree(
        coordination.change_id,
        writer.attempt_id,
        writer.claim_id,
        "quarantine-operation",
    )

    assert receipt.base_head == _git(repository, "rev-parse", coordination.branch)
    assert receipt.quarantine_ref == f"refs/owlbear/quarantine/{coordination.change_id}/{writer.attempt_id}"
    assert receipt.paths == tuple(sorted(receipt.paths))
    assert set(receipt.paths) == {
        "deleted.txt",
        "new.txt",
        "rename-source.txt",
        "rename-target.txt",
        "shared.txt",
        "uv.lock",
    }
    assert _git(worktree, "status", "--porcelain") == ""
    assert _git(worktree, "rev-parse", "HEAD") == base_head
    assert (worktree / "shared.txt").read_bytes() == b"base\n"
    assert not (worktree / "new.txt").exists()
    assert (worktree / "rename-source.txt").read_text(encoding="utf-8") == "rename me\n"
    assert not (worktree / "rename-target.txt").exists()
    assert (worktree / "deleted.txt").exists()
    for directory in (".venv", "node_modules", "dist"):
        assert (worktree / directory / "keep.bin").read_bytes() == b"ignored environment"
    assert _git(repository, "rev-parse", receipt.quarantine_ref) == receipt.quarantine_commit
    assert (
        subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            ("git", "-C", str(repository), "show", f"{receipt.quarantine_commit}:shared.txt"),  # noqa: S607
            check=True,
            capture_output=True,
        ).stdout
        == b"staged binary\x00\xff"
    )
    assert (
        subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            ("git", "-C", str(repository), "show", f"{receipt.quarantine_commit}:uv.lock"),  # noqa: S607
            check=True,
            capture_output=True,
        ).stdout
        == b"lock\x00\xff"
    )


def test_quarantine_replays_after_receipt_persistence_failure(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("quarantine-replay")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    dirty_file = coordination.worktree_path / "uncommitted.bin"
    dirty_file.write_bytes(b"preserve\x00\xff")

    with (
        patch.object(coordinator, "update", side_effect=CoordinationConflictError("injected receipt failure")),
        pytest.raises(CoordinationConflictError, match="injected receipt failure"),
    ):
        manager.quarantine_dirty_worktree(
            coordination.change_id,
            writer.attempt_id,
            writer.claim_id,
            "quarantine-replay-operation",
        )

    quarantine_ref = f"refs/owlbear/quarantine/{coordination.change_id}/{writer.attempt_id}"
    assert _git_ref_exists(repository, quarantine_ref)
    assert coordinator.show(coordination.change_id).dirty_worktree_quarantine is None
    assert dirty_file.read_bytes() == b"preserve\x00\xff"

    receipt = manager.quarantine_dirty_worktree(
        coordination.change_id,
        writer.attempt_id,
        writer.claim_id,
        "quarantine-replay-operation",
    )

    assert receipt.quarantine_ref == quarantine_ref
    assert coordinator.show(coordination.change_id).dirty_worktree_quarantine == receipt
    assert dirty_file.exists() is False
    assert _git(coordination.worktree_path, "status", "--porcelain") == ""


def test_quarantine_replay_rejects_changed_bytes_after_preservation(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("quarantine-drift")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    dirty_file = coordination.worktree_path / "uncommitted.bin"
    dirty_file.write_bytes(b"first\x00\xff")

    with (
        patch.object(coordinator, "update", side_effect=CoordinationConflictError("injected receipt failure")),
        pytest.raises(CoordinationConflictError, match="injected receipt failure"),
    ):
        manager.quarantine_dirty_worktree(
            coordination.change_id,
            writer.attempt_id,
            writer.claim_id,
            "quarantine-drift-operation",
        )

    dirty_file.write_bytes(b"newer\x00\xfe")

    with pytest.raises(RuntimeError, match="changed after quarantine preservation"):
        manager.quarantine_dirty_worktree(
            coordination.change_id,
            writer.attempt_id,
            writer.claim_id,
            "quarantine-drift-operation",
        )

    assert dirty_file.read_bytes() == b"newer\x00\xfe"
    assert coordinator.show(coordination.change_id).writer == writer
    assert coordinator.show(coordination.change_id).dirty_worktree_quarantine is None
    assert _git(coordination.worktree_path, "status", "--porcelain")


def test_quarantine_verifies_after_restart_moves_branch_to_reviewed_head(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("quarantine-restart-replay")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    dirty_file = coordination.worktree_path / "uncommitted.bin"
    dirty_file.write_bytes(b"preserve\x00\xff")

    receipt = manager.quarantine_dirty_worktree(
        coordination.change_id,
        writer.attempt_id,
        writer.claim_id,
        "quarantine-restart-replay-operation",
    )
    manager.restart(coordination.change_id, writer.attempt_id, rejected)

    assert _git(repository, "rev-parse", coordination.branch) == initial
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == initial
    assert (
        manager.verify_dirty_worktree_quarantine(
            coordination.change_id,
            writer.attempt_id,
            writer.claim_id,
            "quarantine-restart-replay-operation",
        )
        == receipt
    )


def test_cleanup_replays_persisted_intent_after_receipt_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("interrupted-cleanup")
    original_update = coordinator.update
    update_count = 0
    failure_message = "simulated cleanup receipt write failure"

    def fail_receipt_update(updated: ChangeCoordination) -> ChangeCoordination:
        nonlocal update_count
        update_count += 1
        if update_count == 2:
            raise CoordinationConflictError(failure_message)
        return original_update(updated)

    monkeypatch.setattr(coordinator, "update", fail_receipt_update)

    with pytest.raises(CoordinationConflictError, match=failure_message):
        manager.cleanup(coordination.change_id)

    interrupted = coordinator.show(coordination.change_id)
    assert interrupted.worktree_cleanup_intent is not None
    assert interrupted.worktree_cleanup is None
    assert not coordination.worktree_path.exists()
    assert _git_ref_exists(repository, coordination.branch)
    assert _git(repository, "rev-parse", coordination.branch) == initial
    with pytest.raises(CoordinationConflictError, match="change already has an active writer"):
        coordinator.acquire(
            coordination.change_id,
            ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build"),
        )

    monkeypatch.setattr(coordinator, "update", original_update)
    receipt = manager.cleanup(coordination.change_id)

    assert receipt.branch_head == initial
    assert coordinator.show(coordination.change_id).worktree_cleanup == receipt
    assert coordinator.show(coordination.change_id).worktree_cleanup_intent is None
    assert manager.cleanup(coordination.change_id) == receipt


def test_cleanup_refuses_missing_worktree_without_recording_cleanup(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("missing-cleanup")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.cleanup(coordination.change_id)

    assert ChangeWorktreeAttentionCode.WORKTREE_MISSING in raised.value.attention
    assert ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING in raised.value.attention
    assert coordinator.show(coordination.change_id).worktree_cleanup is None


def test_cleanup_refuses_registration_for_another_branch_or_path(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)
    _, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("ambiguous-cleanup")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    alternate = tmp_path / "alternate-worktree"
    _git(repository, "worktree", "add", str(alternate), coordination.branch)

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.cleanup(coordination.change_id)

    assert ChangeWorktreeAttentionCode.WORKTREE_MISSING in raised.value.attention
    assert ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS in raised.value.attention
    assert alternate.exists()


def test_cleanup_refuses_unexpected_worktree_filesystem_state(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("file-cleanup")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    coordination.worktree_path.write_text("not a worktree\n", encoding="utf-8")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.cleanup(coordination.change_id)

    assert ChangeWorktreeAttentionCode.UNEXPECTED_FILESYSTEM_STATE in raised.value.attention
    assert coordination.worktree_path.read_text(encoding="utf-8") == "not a worktree\n"


def test_list_registered_ignores_runtime_transaction_temp_files(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    manager.ensure("stable-change")
    coordination_root = tmp_path / "state/coordination/changes"
    (coordination_root / ".tmp-deadbeef-stable-change.json").write_text("not json", encoding="utf-8")

    assert [item.change_id for item in coordinator.list_registered()] == ["stable-change"]


def test_list_registered_rejects_malformed_or_misnamed_records(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    manager.ensure("valid-change")
    coordination_root = tmp_path / "state/coordination/changes"
    (coordination_root / "broken.json").write_text("{", encoding="utf-8")

    with pytest.raises(CoordinationConflictError, match="record is invalid"):
        coordinator.list_registered()

    (coordination_root / "broken.json").unlink()
    payload = _coordination(tmp_path, "valid-change").model_dump(mode="json")
    (coordination_root / "wrong-name.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CoordinationConflictError, match="identity is invalid"):
        coordinator.list_registered()


def test_ensure_replays_a_healthy_change_worktree(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    first = manager.ensure("healthy-replay")

    replayed = manager.ensure("healthy-replay", recovery_reviewed_head=first.last_reviewed_commit)

    assert replayed == first


def test_ensure_rejects_invalid_change_id_before_git_access(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    before = _workspace_bytes(repository, tmp_path / "state")
    with (
        patch.object(manager, "_git", wraps=manager._git) as git,  # noqa: SLF001
        pytest.raises(ValueError, match="safe worktree identity"),
    ):
        manager.ensure("../invalid")

    assert git.call_count == 0
    assert _workspace_bytes(repository, tmp_path / "state") == before


@pytest.mark.parametrize("missing_state", ["directory", "registration"])
def test_ensure_refuses_missing_worktree_state_without_writes(tmp_path: Path, missing_state: str) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"missing-{missing_state}")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    if missing_state == "registration":
        coordination.worktree_path.mkdir(parents=True)
        (coordination.worktree_path / "preserved.txt").write_text("preserve\n", encoding="utf-8")
    before = _workspace_bytes(repository, tmp_path / "state")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.ensure(coordination.change_id, recovery_reviewed_head=coordination.last_reviewed_commit)

    assert (
        ChangeWorktreeAttentionCode.WORKTREE_MISSING
        if missing_state == "directory"
        else ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING
    ) in raised.value.attention
    assert _workspace_bytes(repository, tmp_path / "state") == before
    if missing_state == "registration":
        assert (coordination.worktree_path / "preserved.txt").read_text(encoding="utf-8") == "preserve\n"


def test_recover_recreates_missing_worktree_from_exact_reviewed_head(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("recoverable-change")
    shutil.rmtree(coordination.worktree_path)

    recovered = manager.recover(coordination.change_id, coordination.last_reviewed_commit)

    assert recovered == coordination
    assert recovered.worktree_path.is_dir()
    assert _git(recovered.worktree_path, "rev-parse", "HEAD") == coordination.last_reviewed_commit
    assert _git(repository, "worktree", "list", "--porcelain").count(str(recovered.worktree_path)) == 1
    assert coordinator.show(coordination.change_id) == coordination


def test_recover_rejects_unregistered_worktree_without_discarding_content(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("preserved-recovery")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    coordination.worktree_path.mkdir(parents=True)
    preserved = coordination.worktree_path / "preserved.txt"
    preserved.write_text("preserve\n", encoding="utf-8")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.recover(coordination.change_id, coordination.last_reviewed_commit)

    assert ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING in raised.value.attention
    assert preserved.read_text(encoding="utf-8") == "preserve\n"


def test_recover_requires_the_registered_reviewed_head(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("exact-recovery")
    shutil.rmtree(coordination.worktree_path)

    with pytest.raises(CoordinationConflictError, match="recovery reviewed head differs"):
        manager.recover(coordination.change_id, "a" * 40)

    assert not coordination.worktree_path.exists()


def test_recover_rejects_branch_registered_at_a_foreign_path(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("foreign-recovery")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    foreign_path = tmp_path / "foreign-worktree"
    _git(repository, "worktree", "add", str(foreign_path), coordination.branch)

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.recover(coordination.change_id, coordination.last_reviewed_commit)

    assert ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS in raised.value.attention
    assert foreign_path.is_dir()
    assert not coordination.worktree_path.exists()


def test_ensure_preserves_dirty_change_worktree(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("dirty-replay")
    dirty_file = coordination.worktree_path / "dirty.txt"
    dirty_file.write_text("uncommitted\n", encoding="utf-8")
    before = _workspace_bytes(repository, tmp_path / "state")

    replayed = manager.ensure(coordination.change_id)

    assert replayed == coordination
    assert dirty_file.read_text(encoding="utf-8") == "uncommitted\n"
    assert _workspace_bytes(repository, tmp_path / "state") == before


def test_ensure_refuses_coordination_path_mismatch_without_writes(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("path-mismatch")
    mismatched = coordination.model_copy(update={"worktree_path": tmp_path / "elsewhere" / "path-mismatch"})
    coordinator.update(mismatched)
    before = _workspace_bytes(repository, tmp_path / "state")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.ensure(coordination.change_id)

    assert ChangeWorktreeAttentionCode.COORDINATION_PATH_MISMATCH in raised.value.attention
    assert _workspace_bytes(repository, tmp_path / "state") == before


@pytest.mark.parametrize(
    ("mutation", "expected_attention"),
    [
        ("missing-directory", ChangeWorktreeAttentionCode.WORKTREE_MISSING),
        ("missing-registration", ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING),
        ("missing-branch", ChangeWorktreeAttentionCode.BRANCH_MISSING),
        ("detached", ChangeWorktreeAttentionCode.DETACHED),
        ("branch-mismatch", ChangeWorktreeAttentionCode.BRANCH_MISMATCH),
    ],
)
def test_list_retained_worktrees_reports_independent_degraded_facts(
    tmp_path: Path,
    mutation: str,
    expected_attention: ChangeWorktreeAttentionCode,
) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"degraded-{mutation}")
    if mutation == "missing-directory":
        _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    elif mutation == "missing-registration":
        _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
        coordination.worktree_path.mkdir(parents=True)
    elif mutation == "missing-branch":
        _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
        if _git_ref_exists(repository, coordination.branch):
            _git(repository, "update-ref", "-d", f"refs/heads/{coordination.branch}")
    elif mutation == "detached":
        _git(coordination.worktree_path, "checkout", "--detach", "HEAD")
    elif mutation == "branch-mismatch":
        _git(coordination.worktree_path, "checkout", "-b", f"other-{mutation}")

    retained = manager.list_retained()
    row = next(item for item in retained if item.change_id == coordination.change_id)

    assert expected_attention in row.attention
    assert row.coordination_registered
    assert row.worktree_present is (mutation not in {"missing-directory", "missing-branch"})
    assert row.git_registered is (mutation not in {"missing-directory", "missing-registration", "missing-branch"})


def test_list_retained_worktrees_reports_orphaned_registration(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("orphaned-change")
    (tmp_path / "state/coordination/changes/orphaned-change.json").unlink()

    row = next(item for item in manager.list_retained() if item.change_id == coordination.change_id)

    assert row.coordination_registered is False
    assert row.git_registered is True
    assert row.worktree_present is True
    assert ChangeWorktreeAttentionCode.COORDINATION_MISSING in row.attention


def _commit_file(worktree: Path, content: str, message: str) -> str:
    (worktree / "shared.txt").write_text(content, encoding="utf-8")
    _git(worktree, "add", "shared.txt")
    _git(worktree, "commit", "-m", message)
    return _git(worktree, "rev-parse", "HEAD")


def _commit_new_file(worktree: Path, name: str, content: str, message: str) -> str:
    (worktree / name).write_text(content, encoding="utf-8")
    _git(worktree, "add", name)
    _git(worktree, "commit", "-m", message)
    return _git(worktree, "rev-parse", "HEAD")


def _publish_external_change_head(
    tmp_path: Path,
    repository: Path,
    branch: str,
    base_head: str,
    *,
    filename: str = "external.txt",
) -> tuple[Path, str]:
    remote = tmp_path / "external-remote.git"
    _git(tmp_path, "init", "--bare", "-b", branch, str(remote))
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", f"{base_head}:refs/heads/{branch}")
    external = tmp_path / "external-repository"
    _git(tmp_path, "clone", str(remote), str(external))
    _git(external, "checkout", "-b", "external", base_head)
    _git(external, "config", "user.name", "External User")
    _git(external, "config", "user.email", "external@example.com")
    adopted = _commit_new_file(external, filename, "external\n", "external Change update")
    _git(external, "push", "origin", f"{adopted}:refs/heads/{branch}")
    return remote, adopted


def test_adopt_external_head_fast_forwards_managed_worktree_and_preserves_review_authority(
    tmp_path: Path,
) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("adoptable-change")
    remote, adopted = _publish_external_change_head(
        tmp_path,
        repository,
        coordination.branch,
        initial,
    )

    receipt = manager.adopt_external_head(
        AdoptExternalHead(
            change_id=coordination.change_id,
            expected_head=initial,
            adopted_head=adopted,
            operation_id="adopt-external-change",
        )
    )

    assert isinstance(receipt, ChangeExternalHeadAdoptionReceipt)
    assert receipt.expected_head == initial
    assert receipt.adopted_head == adopted
    assert receipt.provenance == "fast-forward"
    assert _git(repository, "rev-parse", coordination.branch) == adopted
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == adopted
    assert coordinator.show(coordination.change_id).last_reviewed_commit == initial
    with pytest.raises(RuntimeError, match="reviewed source boundary"):
        manager.reviewed_source_head(coordination.change_id)
    assert manager.source_head(coordination.change_id) == adopted
    promoted = manager.promote_external_head(
        PromoteExternalHead(
            change_id=coordination.change_id,
            expected_head=adopted,
            operation_id="promote-external-change",
        )
    )
    assert isinstance(promoted, ChangeExternalHeadPromotionReceipt)
    assert promoted.promoted_head == adopted
    assert coordinator.show(coordination.change_id).last_reviewed_commit == adopted
    assert manager.reviewed_source_head(coordination.change_id) == adopted
    assert (
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=initial,
                adopted_head=adopted,
                operation_id="adopt-external-change",
            )
        )
        == receipt
    )
    assert _git(remote, "rev-parse", f"refs/heads/{coordination.branch}") == adopted


def test_adopt_external_head_observes_exact_remote_head_already_on_managed_branch(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("observed-adoption")
    _remote, adopted = _publish_external_change_head(tmp_path, repository, coordination.branch, initial)
    _git(
        repository,
        "fetch",
        "origin",
        f"refs/heads/{coordination.branch}:refs/remotes/origin/{coordination.branch}",
    )
    _git(coordination.worktree_path, "merge", "--ff-only", adopted)

    callback = Mock()
    receipt = manager.adopt_external_head(
        AdoptExternalHead(
            change_id=coordination.change_id,
            expected_head=initial,
            adopted_head=adopted,
            operation_id="observe-external-change",
        ),
        before_head_change=callback,
    )

    assert receipt.schema_version == 2
    assert receipt.provenance == "observed"
    assert receipt.expected_head == initial
    assert receipt.adopted_head == adopted
    callback.assert_not_called()
    assert coordinator.show(coordination.change_id).last_reviewed_commit == initial
    assert (
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=initial,
                adopted_head=adopted,
                operation_id="observe-external-change",
            )
        )
        == receipt
    )


def test_adopt_external_head_rejects_local_only_advanced_head(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("local-only-adoption")
    _remote, _remote_adopted = _publish_external_change_head(
        tmp_path,
        repository,
        coordination.branch,
        initial,
    )
    local_only = _commit_new_file(
        coordination.worktree_path,
        "local-only.txt",
        "local\n",
        "local-only Change update",
    )
    before = coordinator.show(coordination.change_id)

    with pytest.raises(CoordinationConflictError, match="remote Change branch differs from the adoption request"):
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=initial,
                adopted_head=local_only,
                operation_id="reject-local-only-change",
            )
        )

    assert _git(repository, "rev-parse", coordination.branch) == local_only
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == local_only
    assert coordinator.show(coordination.change_id) == before


def test_external_head_adoption_receipt_rejects_legacy_fast_forward_schema(tmp_path: Path) -> None:
    _repository(tmp_path)
    receipt = ChangeExternalHeadAdoptionReceipt.create(
        operation_id="legacy-adoption",
        change_id="legacy-adoption",
        branch="owlbear/change/legacy-adoption",
        expected_head="a" * 40,
        adopted_head="b" * 40,
    )
    assert receipt.schema_version == 2
    assert receipt.provenance == "fast-forward"
    assert ChangeExternalHeadAdoptionReceipt.model_validate_json(receipt.model_dump_json()) == receipt

    legacy_payload = receipt.model_dump(mode="json")
    legacy_payload["schema_version"] = 1
    legacy_payload.pop("provenance")
    legacy_payload["receipt_id"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in legacy_payload.items() if key != "receipt_id"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    with pytest.raises(ValueError, match="schema_version"):
        ChangeExternalHeadAdoptionReceipt.model_validate(legacy_payload)


def test_adopt_external_head_rejects_divergent_remote_without_branch_mutation(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("divergent-adoption")
    local_descendant = _commit_new_file(coordination.worktree_path, "local.txt", "local\n", "local change")
    manager.record_reviewed(coordination.change_id, local_descendant)
    _git(coordination.worktree_path, "checkout", coordination.branch)
    divergent_base = _git(repository, "rev-parse", "release")
    assert divergent_base == initial
    _remote, divergent = _publish_external_change_head(
        tmp_path,
        repository,
        coordination.branch,
        initial,
        filename="divergent.txt",
    )
    before = coordinator.show(coordination.change_id)

    with pytest.raises(RuntimeError, match="not a descendant"):
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=local_descendant,
                adopted_head=divergent,
                operation_id="reject-divergent-adoption",
            )
        )

    assert _git(repository, "rev-parse", coordination.branch) == local_descendant
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == local_descendant
    after = coordinator.show(coordination.change_id)
    assert after == before


def test_adopt_external_head_replays_after_crash_between_fast_forward_and_receipt(
    tmp_path: Path,
) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("crash-replay-adoption")
    _remote, adopted = _publish_external_change_head(
        tmp_path,
        repository,
        coordination.branch,
        initial,
    )
    request = AdoptExternalHead(
        change_id=coordination.change_id,
        expected_head=initial,
        adopted_head=adopted,
        operation_id="crash-replay-adoption",
    )

    with (
        patch.object(manager, "_complete_external_head_adoption", side_effect=RuntimeError("simulated crash")),
        pytest.raises(RuntimeError, match="simulated crash"),
    ):
        manager.adopt_external_head(request)

    interrupted = coordinator.show(coordination.change_id)
    assert interrupted.external_head_adoption_intent is not None
    assert interrupted.external_head_adoption_receipt is None
    assert _git(repository, "rev-parse", coordination.branch) == adopted
    assert manager.adopt_external_head(request).adopted_head == adopted
    assert coordinator.show(coordination.change_id).external_head_adoption_intent is None


def test_target_sync_rejects_an_unreviewed_adopted_head(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("adopted-target-sync")
    _remote, adopted = _publish_external_change_head(
        tmp_path,
        repository,
        coordination.branch,
        initial,
    )
    manager.adopt_external_head(
        AdoptExternalHead(
            change_id=coordination.change_id,
            expected_head=initial,
            adopted_head=adopted,
            operation_id="adopt-before-target-sync",
        )
    )
    before = coordinator.show(coordination.change_id)

    with pytest.raises(CoordinationConflictError, match="reviewed Change head"):
        manager.sync_with_target(
            SyncChangeWithTarget(
                change_id=coordination.change_id,
                expected_target="a" * 40,
                operation_id="target-sync-after-adoption",
            )
        )

    assert coordinator.show(coordination.change_id) == before
    assert _git(repository, "rev-parse", coordination.branch) == adopted


def test_adopt_external_head_rejects_active_writer_and_dirty_worktree(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("blocked-adoption")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)

    with pytest.raises(CoordinationConflictError, match="active writer"):
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=initial,
                adopted_head="b" * 40,
                operation_id="blocked-by-writer",
            )
        )

    coordinator.release(coordination.change_id, writer.claim_id)
    (coordination.worktree_path / "dirty.txt").write_text("preserve\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="not clean"):
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=initial,
                adopted_head="b" * 40,
                operation_id="blocked-by-dirty-worktree",
            )
        )
    assert _git(repository, "rev-parse", coordination.branch) == initial
    assert coordinator.show(coordination.change_id).external_head_adoption_receipt is None


def test_restart_rejects_reset_across_unpromoted_external_head(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("restart-adopted-change")
    _remote, adopted = _publish_external_change_head(tmp_path, repository, coordination.branch, initial)
    manager.adopt_external_head(
        AdoptExternalHead(
            change_id=coordination.change_id,
            expected_head=initial,
            adopted_head=adopted,
            operation_id="adopt-before-restart",
        )
    )
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)

    with pytest.raises(CoordinationConflictError, match="unpromoted external Change head"):
        manager.restart(coordination.change_id, writer.attempt_id, adopted)

    assert _git(repository, "rev-parse", coordination.branch) == adopted
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == adopted
    assert coordinator.show(coordination.change_id).writer == writer


def test_restart_accepts_promoted_adoption_after_reviewed_descendant_and_replays(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("restart-promoted-adoption")
    _remote, adopted = _publish_external_change_head(tmp_path, repository, coordination.branch, initial)
    manager.adopt_external_head(
        AdoptExternalHead(
            change_id=coordination.change_id,
            expected_head=initial,
            adopted_head=adopted,
            operation_id="adopt-before-promoted-restart",
        )
    )
    promoted = manager.promote_external_head(
        PromoteExternalHead(
            change_id=coordination.change_id,
            expected_head=adopted,
            operation_id="promote-before-restart",
        )
    )
    reviewed = _commit_new_file(coordination.worktree_path, "reviewed.txt", "reviewed\n", "reviewed descendant")
    manager.record_reviewed(coordination.change_id, reviewed)
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    attempt_ref = f"refs/owlbear/attempts/{coordination.change_id}/{writer.attempt_id}"

    restarted = manager.restart(coordination.change_id, writer.attempt_id, rejected)

    assert promoted is not None
    assert _git(repository, "rev-parse", attempt_ref) == rejected
    assert _git(repository, "rev-parse", coordination.branch) == reviewed
    assert _git(restarted.worktree_path, "rev-parse", "HEAD") == reviewed
    assert restarted.last_reviewed_commit == reviewed
    assert restarted.writer is None
    assert not (tmp_path / "state/capacity-ledger.json").exists()

    replayed = manager.restart(coordination.change_id, writer.attempt_id, rejected)

    assert replayed == restarted


def test_record_reviewed_rejects_backward_boundary(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("monotonic-review")
    reviewed = _commit_new_file(coordination.worktree_path, "reviewed.txt", "reviewed\n", "reviewed")
    manager.record_reviewed(coordination.change_id, reviewed)

    with pytest.raises(RuntimeError, match="not an ancestor"):
        manager.record_reviewed(coordination.change_id, initial)

    assert coordinator.show(coordination.change_id).last_reviewed_commit == reviewed


def test_finalization_rejects_divergent_promoted_task_history(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("divergent-tasks")
    first = _commit_new_file(coordination.worktree_path, "first.txt", "first\n", "first task")
    _git(coordination.worktree_path, "checkout", "-b", "divergent-task", initial)
    second = _commit_new_file(coordination.worktree_path, "second.txt", "second\n", "second task")
    _git(coordination.worktree_path, "checkout", coordination.branch)
    _git(coordination.worktree_path, "merge", "--no-ff", "divergent-task", "-m", "merge divergent tasks")
    exact_head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    manager.record_reviewed(coordination.change_id, exact_head)

    with pytest.raises(RuntimeError, match="not an ancestor"):
        manager.validate_finalization_head(coordination.change_id, exact_head, (first, second))


def test_workspace_recovery_requires_and_preserves_exact_reviewed_head(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    state_root = tmp_path / "state"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "release")
    coordination = manager.ensure("recovered-change")
    reviewed = _commit_new_file(coordination.worktree_path, "product.txt", "reviewed\n", "reviewed product")
    manager.record_reviewed(coordination.change_id, reviewed)
    (state_root / "coordination/changes/recovered-change.json").unlink()
    recovered_manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "release")

    with pytest.raises(CoordinationConflictError, match="exact recovery reviewed head"):
        recovered_manager.ensure("recovered-change")

    recovered = recovered_manager.ensure("recovered-change", recovery_reviewed_head=reviewed)

    assert recovered.last_reviewed_commit == reviewed
    assert _git(recovered.worktree_path, "rev-parse", "HEAD") == reviewed


def test_coordinator_recovers_pending_runtime_transaction(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    coordinator = PortfolioCoordinator(state_root)
    participant = TransactionParticipant(state_root, Path("target-runtime/recovered.json"), b"{}\n")

    def interrupt(stage: str) -> None:
        if stage == "before-publication":
            message = "injected"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="injected"):
        RuntimeTransaction(state_root, "pending-portfolio", (participant,)).commit(failure=interrupt)

    with coordinator.acquisition_lock():
        coordinator.recover_pending_transactions()

    assert (state_root / "target-runtime/recovered.json").read_bytes() == b"{}\n"
    assert not (state_root / "transactions/pending-portfolio.yaml").exists()


def test_coordinator_ignores_legacy_capacity_ledger(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    legacy_ledger_path = state_root / "capacity.json"
    legacy_ledger_path.parent.mkdir(parents=True)
    legacy_ledger_path.write_text(
        CapacityLedger(capacity=4, change_ids=("change-a",)).model_dump_json(),
        encoding="utf-8",
    )

    PortfolioCoordinator(state_root)

    assert CapacityLedger.model_validate_json(legacy_ledger_path.read_bytes()) == CapacityLedger(
        capacity=4,
        change_ids=("change-a",),
    )
    assert not (state_root / "capacity-ledger.json").exists()


def test_coordinator_does_not_validate_legacy_capacity_ledger(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    ledger_path = state_root / "capacity.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        CapacityLedger(capacity=4, change_ids=("change-a", "change-b")).model_dump_json(),
        encoding="utf-8",
    )

    PortfolioCoordinator(state_root)

    assert CapacityLedger.model_validate_json(ledger_path.read_bytes()).capacity == 4


def test_restart_preserves_rejected_head_and_returns_to_reviewed_commit(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("restart-change")
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    coordinator.acquire(
        "restart-change",
        ChangeWriter(**_identity("restart-change").model_dump(), job_id=1, kind="build"),
    )

    restarted = manager.restart("restart-change", "attempt-restart-change", rejected)

    assert _git(repository, "rev-parse", "refs/owlbear/attempts/restart-change/attempt-restart-change") == rejected
    assert _git(repository, "rev-parse", restarted.branch) == initial
    assert _git(restarted.worktree_path, "rev-parse", "HEAD") == initial
    assert restarted.writer is None


def test_recover_out_of_band_head_preserves_and_restores_reviewed_boundary(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("recover-out-of-band")
    reviewed = _commit_file(coordination.worktree_path, "reviewed\n", "reviewed boundary")
    manager.record_reviewed(coordination.change_id, reviewed)
    out_of_band = _commit_file(coordination.worktree_path, "out-of-band\n", "out-of-band change")
    request = RecoverOutOfBandHead(
        change_id=coordination.change_id,
        expected_reviewed_head=reviewed,
        expected_remote_head=initial,
        expected_branch_head=out_of_band,
        operation_id="recover-out-of-band",
    )

    receipt = manager.recover_out_of_band_head(request)

    assert receipt.preserved_head == out_of_band
    assert _git(repository, "rev-parse", receipt.preserved_ref) == out_of_band
    assert _git(repository, "rev-parse", coordination.branch) == reviewed
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == reviewed
    assert coordinator.show(coordination.change_id).out_of_band_head_recovery == receipt


def test_recover_out_of_band_head_replays_after_branch_ref_update(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("recover-out-of-band-replay")
    reviewed = _commit_file(coordination.worktree_path, "reviewed\n", "reviewed boundary")
    manager.record_reviewed(coordination.change_id, reviewed)
    out_of_band = _commit_file(coordination.worktree_path, "out-of-band\n", "out-of-band change")
    request = RecoverOutOfBandHead(
        change_id=coordination.change_id,
        expected_reviewed_head=reviewed,
        expected_remote_head=initial,
        expected_branch_head=out_of_band,
        operation_id="recover-out-of-band-replay",
    )
    _git(repository, "update-ref", f"refs/heads/{coordination.branch}", reviewed, out_of_band)
    _git(coordination.worktree_path, "reset", "--hard", out_of_band)
    recovery_ref = f"refs/owlbear/recovery/{coordination.change_id}/{request.operation_id}"
    _git(repository, "update-ref", recovery_ref, out_of_band)

    receipt = manager.recover_out_of_band_head(request)

    assert receipt.preserved_head == out_of_band
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == reviewed
    assert coordinator.show(coordination.change_id).out_of_band_head_recovery == receipt


def test_restart_recovers_after_git_succeeds_before_writer_release(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("recover-restart")
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    coordinator.acquire(
        "recover-restart",
        ChangeWriter(**_identity("recover-restart").model_dump(), job_id=1, kind="build"),
    )
    original_release = coordinator.release

    with (
        patch.object(coordinator, "release", side_effect=CoordinationConflictError("injected")),
        pytest.raises(CoordinationConflictError, match="injected"),
    ):
        manager.restart("recover-restart", "attempt-recover-restart", rejected)

    recovered = manager.restart("recover-restart", "attempt-recover-restart", rejected)

    assert _git(repository, "rev-parse", "refs/owlbear/attempts/recover-restart/attempt-recover-restart") == rejected
    assert _git(repository, "rev-parse", recovered.branch) == initial
    assert recovered.writer is None
    assert original_release("recover-restart", "claim-recover-restart") == recovered


@pytest.mark.parametrize("interruption", ["attempt-ref", "worktree-reset"])
def test_restart_recovers_from_each_git_interruption(tmp_path: Path, interruption: str) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"restart-{interruption}")
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    coordinator.acquire(
        coordination.change_id,
        ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build"),
    )
    original_git = manager._git  # noqa: SLF001

    def interrupt_after_git(*arguments: str, **kwargs) -> str:
        result = original_git(*arguments, **kwargs)
        if _restart_stage(arguments, coordination, interruption):
            message = "injected"
            raise RuntimeError(message)
        return result

    with (
        patch.object(manager, "_git", side_effect=interrupt_after_git),
        pytest.raises(RuntimeError, match="injected"),
    ):
        manager.restart(coordination.change_id, _identity(coordination.change_id).attempt_id, rejected)

    recovered = manager.restart(coordination.change_id, _identity(coordination.change_id).attempt_id, rejected)

    assert _git(repository, "rev-parse", recovered.branch) == initial
    assert _git(recovered.worktree_path, "rev-parse", "HEAD") == initial
    assert recovered.last_reviewed_commit == initial
    assert recovered.writer is None


def _restart_stage(
    arguments: tuple[str, ...],
    coordination: ChangeCoordination,
    interruption: str,
) -> bool:
    checks = {
        "attempt-ref": arguments[:2]
        == ("update-ref", f"refs/owlbear/attempts/{coordination.change_id}/attempt-{coordination.change_id}"),
        "worktree-reset": arguments[:2] == ("reset", "--hard"),
    }
    return checks[interruption]


@pytest.mark.parametrize("interruption", ["branch-reset", "worktree-add"])
def test_restart_recovers_missing_worktree_at_each_git_interruption(tmp_path: Path, interruption: str) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"restart-missing-{interruption}")
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    _git(repository, "worktree", "remove", str(coordination.worktree_path))
    original_git = manager._git  # noqa: SLF001

    def interrupt_after_git(*arguments: str, **kwargs) -> str:
        result = original_git(*arguments, **kwargs)
        checks = {
            "branch-reset": arguments[:2] == ("update-ref", f"refs/heads/{coordination.branch}"),
            "worktree-add": arguments[:2] == ("worktree", "add"),
        }
        if checks[interruption]:
            message = "injected"
            raise RuntimeError(message)
        return result

    with (
        patch.object(manager, "_git", side_effect=interrupt_after_git),
        pytest.raises(RuntimeError, match="injected"),
    ):
        manager.restart(coordination.change_id, writer.attempt_id, rejected)

    recovered = manager.restart(coordination.change_id, writer.attempt_id, rejected)

    assert _git(repository, "rev-parse", recovered.branch) == initial
    assert _git(recovered.worktree_path, "rev-parse", "HEAD") == initial
    assert recovered.writer is None
