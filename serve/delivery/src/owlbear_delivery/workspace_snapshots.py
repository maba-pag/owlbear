"""Finalization boundaries, design-package snapshots and dirty-worktree quarantine."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery.workspace_models import (
    _COMMIT_PARENT_COUNT,
    _DESIGN_PACKAGE_NAMES,
    _DIGEST_PATTERN,
    _PORCELAIN_WORKTREE_STATUS_PREFIX_LENGTH,
    ChangeCoordination,
    ChangeDesignPackageSnapshotIntent,
    ChangeDesignPackageSnapshotReceipt,
    DesignPackageSnapshotEditedError,
    DirtyWorktreeQuarantineReceipt,
    PublicationLock,
    WorkspaceRecoverySnapshot,
    _coordination_conflict,
    _quarantine_commit_message,
    _workspace_failure,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from owlbear_delivery.runtime_transaction import (
        ReplacementTransactionParticipant,
    )

DESIGN_PACKAGE_SNAPSHOT_SUBJECT = "chore: snapshot admitted Design package ({change_id}, {operation_id})"


class _SnapshotMixin:
    """Finalization boundaries, design-package snapshots and dirty-worktree quarantine."""

    def prepare_finalization_boundary(
        self,
        change_id: str,
        exact_head: str,
        promoted_commits: tuple[str, ...],
        lock: PublicationLock,
        *,
        completion: tuple[str, str] | None = None,
    ) -> ReplacementTransactionParticipant | None:
        """Prepare a reviewed-boundary advance for one clean finalization head."""
        current = self._coordinator.show(change_id)
        attempt = current.finalization_attempt
        active = attempt is not None and attempt.finished_at is None
        if active and (
            completion is None
            or attempt.writer.attempt_id != completion[0]
            or attempt.exact_head != exact_head
            or attempt.target_head != self.observed_target_head()
        ):
            _coordination_conflict("finalization attempt or target head changed")
        coordination = self.validate_finalization_head(
            change_id, exact_head, promoted_commits, expected_writer=attempt.writer if active else None
        )
        adoption = coordination.external_head_adoption_receipt
        if active:
            reviewed_head = (
                coordination.last_reviewed_commit
                if adoption is not None and adoption.adopted_head == exact_head
                else exact_head
            )
            return self._coordinator.prepare_finalization_completion(coordination, reviewed_head, completion[1], lock)
        if coordination.last_reviewed_commit == exact_head or (
            adoption is not None and adoption.adopted_head == exact_head
        ):
            return None
        return self._coordinator.prepare_reviewed_boundary(coordination, exact_head, lock)

    def snapshot_design_package(
        self,
        change_id: str,
        package_id: str,
        package_files: Mapping[str, bytes],
        operation_id: str,
        expected_existing_receipt_id: str | None = None,
    ) -> ChangeDesignPackageSnapshotReceipt:
        """Commit one verified admitted Design package on its managed Change branch."""
        if set(package_files) != set(_DESIGN_PACKAGE_NAMES):
            _workspace_failure("Design package snapshot must contain the canonical package files")
        if not _DIGEST_PATTERN.fullmatch(package_id):
            _workspace_failure("Design package snapshot identity is invalid")
        with self._coordinator.publication_lock(change_id) as lock:
            coordination = self._coordinator.show(change_id)
            existing = coordination.design_package_snapshot
            if existing is not None:
                if existing.package_id == package_id:
                    self._validate_design_package_snapshot_replay(existing, package_id)
                    return existing
                if expected_existing_receipt_id != existing.receipt_id:
                    _coordination_conflict("Design package snapshot differs from the expected receipt")
                return self._replace_design_package_snapshot(
                    coordination,
                    package_id,
                    package_files,
                    operation_id,
                    lock=lock,
                )
            intent = coordination.design_package_snapshot_intent
            branch_head = self._resolve(coordination.branch)
            if intent is None:
                if branch_head != coordination.last_reviewed_commit:
                    _workspace_failure("Design package snapshot requires the reviewed Change branch head")
                intent = ChangeDesignPackageSnapshotIntent.create(
                    operation_id=operation_id,
                    change_id=change_id,
                    package_id=package_id,
                    branch=coordination.branch,
                    worktree_path=coordination.worktree_path,
                    expected_head=branch_head,
                )
                coordination = self._coordinator.update(
                    coordination.model_copy(update={"design_package_snapshot_intent": intent}),
                    lock=lock,
                )
            elif intent.operation_id != operation_id or intent.package_id != package_id:
                _coordination_conflict("Design package snapshot intent differs from the request")
            snapshot_head = self._commit_design_package_snapshot(coordination, intent, package_files, branch_head)
            receipt = ChangeDesignPackageSnapshotReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                package_id=package_id,
                branch=coordination.branch,
                worktree_path=coordination.worktree_path,
                previous_head=intent.expected_head,
                snapshot_head=snapshot_head,
            )
            current = self._coordinator.show(change_id)
            updated = current.model_copy(
                update={
                    "design_package_snapshot_intent": None,
                    "design_package_snapshot": receipt,
                    "last_reviewed_commit": snapshot_head,
                }
            )
            self._coordinator.update(updated, lock=lock)
            return receipt

    def _replace_design_package_snapshot(
        self,
        coordination: ChangeCoordination,
        package_id: str,
        package_files: Mapping[str, bytes],
        operation_id: str,
        *,
        lock: PublicationLock,
    ) -> ChangeDesignPackageSnapshotReceipt:
        """Replace one exact package snapshot on the reviewed head after an admitted Design revision."""
        existing = coordination.design_package_snapshot
        if existing is None:
            _coordination_conflict("Design package snapshot replacement requires an existing snapshot")
        if coordination.writer is not None:
            _coordination_conflict("Design package snapshot replacement cannot overlap an active writer")
        branch_head = self._resolve(coordination.branch)
        intent = coordination.design_package_snapshot_intent
        if intent is None:
            if branch_head != coordination.last_reviewed_commit:
                _workspace_failure("Design package snapshot requires the reviewed Change branch head")
            intent = ChangeDesignPackageSnapshotIntent.create(
                operation_id=operation_id,
                change_id=coordination.change_id,
                package_id=package_id,
                branch=coordination.branch,
                worktree_path=coordination.worktree_path,
                expected_head=coordination.last_reviewed_commit,
            )
            coordination = self._coordinator.update(
                coordination.model_copy(update={"design_package_snapshot_intent": intent}),
                lock=lock,
            )
        elif intent.operation_id != operation_id or intent.package_id != package_id:
            _coordination_conflict("Design package snapshot replacement intent differs from the request")
        elif branch_head == intent.expected_head:
            self._restore_interrupted_package_paths(coordination, intent.expected_head, package_files)
        snapshot_head = self._commit_design_package_snapshot(coordination, intent, package_files, branch_head)
        receipt = ChangeDesignPackageSnapshotReceipt.create(
            operation_id=operation_id,
            change_id=coordination.change_id,
            package_id=package_id,
            branch=coordination.branch,
            worktree_path=coordination.worktree_path,
            previous_head=intent.expected_head,
            snapshot_head=snapshot_head,
        )
        current = self._coordinator.show(coordination.change_id)
        updated = current.model_copy(
            update={
                "design_package_snapshot_intent": None,
                "design_package_snapshot": receipt,
                "last_reviewed_commit": snapshot_head,
            }
        )
        self._coordinator.update(updated, lock=lock)
        return receipt

    def is_design_package_snapshot_child(self, intent: ChangeDesignPackageSnapshotIntent, head: str) -> bool:
        """Return whether ``head`` is the intent's own snapshot commit, made before its receipt was stored."""
        subject = DESIGN_PACKAGE_SNAPSHOT_SUBJECT.format(change_id=intent.change_id, operation_id=intent.operation_id)
        return (
            self._is_direct_child(intent.expected_head, head) and self._git("log", "-1", "--format=%s", head) == subject
        )

    def _restore_interrupted_package_paths(
        self, coordination: ChangeCoordination, head: str, package_files: Mapping[str, bytes]
    ) -> None:
        """Undo package files an interrupted snapshot wrote or staged; refuse bytes it did not write."""
        worktree = coordination.worktree_path
        relative_paths = tuple(
            f".owlbear/delivery/packages/{coordination.change_id}/{name}" for name in _DESIGN_PACKAGE_NAMES
        )
        status = self._run_git("status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=worktree).stdout
        dirty = self._dirty_paths(status)
        if not dirty:
            return
        if not set(dirty) <= set(relative_paths):
            _workspace_failure("Design package snapshot worktree changed outside its package paths")
        tracked = set(self._git("ls-tree", "-r", "--name-only", head, "--", *relative_paths).splitlines())
        existing = {
            name: self._git_blob_bytes(head, relative_path) if relative_path in tracked else None
            for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
        }
        edited = tuple(
            relative_path
            for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
            if relative_path in dirty
            and not {
                self._read_optional_worktree_file(worktree / relative_path),
                self._index_blob_bytes(worktree, relative_path),
            }
            <= {existing[name], package_files[name]}
        )
        if edited:
            raise DesignPackageSnapshotEditedError(coordination.change_id, edited)
        self._restore_worktree_files(worktree, relative_paths, existing)

    def _index_blob_bytes(self, worktree: Path, relative_path: str) -> bytes | None:
        result = self._run_git("cat-file", "blob", f":{relative_path}", cwd=worktree, check=False)
        return result.stdout if result.returncode == 0 else None

    def _validate_design_package_snapshot_replay(
        self,
        receipt: ChangeDesignPackageSnapshotReceipt,
        package_id: str,
    ) -> None:
        if receipt.package_id != package_id:
            _coordination_conflict("Design package snapshot differs from the request")
        self._require_worktree(
            receipt.change_id,
            receipt.worktree_path,
            receipt.branch,
            receipt.snapshot_head,
        )
        self._require_clean_worktree(receipt.worktree_path)

    def _commit_design_package_snapshot(
        self,
        coordination: ChangeCoordination,
        intent: ChangeDesignPackageSnapshotIntent,
        package_files: Mapping[str, bytes],
        branch_head: str | None,
    ) -> str:
        worktree = coordination.worktree_path
        relative_paths = tuple(
            f".owlbear/delivery/packages/{coordination.change_id}/{name}" for name in _DESIGN_PACKAGE_NAMES
        )
        existing = {
            name: self._read_optional_worktree_file(worktree / relative_path)
            for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
        }
        if branch_head == intent.expected_head and self._package_files_match_commit(
            intent.expected_head,
            relative_paths,
            existing,
            package_files,
        ):
            return intent.expected_head
        if branch_head != intent.expected_head:
            return self._replay_design_package_snapshot(coordination, intent, package_files, branch_head)
        self._require_worktree(coordination.change_id, worktree, coordination.branch, intent.expected_head)
        self._require_clean_worktree(worktree)
        committed = False
        try:
            self._write_design_package_files(worktree, relative_paths, package_files)
            self._git("add", "-f", "--", *relative_paths, cwd=worktree)
            message = DESIGN_PACKAGE_SNAPSHOT_SUBJECT.format(
                change_id=coordination.change_id, operation_id=intent.operation_id
            )
            result = self._run_git(
                "commit",
                "--only",
                "-m",
                message,
                "--",
                *relative_paths,
                cwd=worktree,
                check=False,
            )
            if result.returncode != 0:
                _workspace_failure("Design package snapshot could not be committed")
            committed = True
        except Exception:
            if not committed:
                self._restore_worktree_files(worktree, relative_paths, existing)
            raise
        else:
            snapshot_head = self._resolve("HEAD", cwd=worktree)
            if snapshot_head is None:
                _workspace_failure("Design package snapshot commit has no resolvable head")
            self._require_clean_worktree(worktree)
            current = {
                name: self._read_optional_worktree_file(worktree / relative_path)
                for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
            }
            if not self._package_files_match_commit(snapshot_head, relative_paths, current, package_files):
                _workspace_failure("Design package snapshot committed unexpected package bytes")
            changed = self._git(
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                snapshot_head,
                cwd=worktree,
            ).splitlines()
            if not changed or not set(changed).issubset(set(relative_paths)):
                _workspace_failure("Design package snapshot committed an unexpected path")
            return snapshot_head

    def _replay_design_package_snapshot(
        self,
        coordination: ChangeCoordination,
        intent: ChangeDesignPackageSnapshotIntent,
        package_files: Mapping[str, bytes],
        branch_head: str,
    ) -> str:
        """Recover a package snapshot after its commit succeeded before receipt storage."""
        if not self._is_direct_child(intent.expected_head, branch_head):
            _workspace_failure("Design package snapshot branch changed before its commit")
        self._require_clean_worktree(coordination.worktree_path)
        relative_paths = tuple(
            f".owlbear/delivery/packages/{coordination.change_id}/{name}" for name in _DESIGN_PACKAGE_NAMES
        )
        existing = {
            name: self._read_optional_worktree_file(coordination.worktree_path / relative_path)
            for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
        }
        if not self._package_files_match_commit(branch_head, relative_paths, existing, package_files):
            _workspace_failure("Design package snapshot commit does not match its package")
        message = DESIGN_PACKAGE_SNAPSHOT_SUBJECT.format(
            change_id=coordination.change_id, operation_id=intent.operation_id
        )
        if self._git("log", "-1", "--format=%s", branch_head, cwd=coordination.worktree_path) != message:
            _workspace_failure("Design package snapshot branch commit is not replayable")
        return branch_head

    def _package_files_match_commit(
        self,
        commit: str,
        relative_paths: tuple[str, ...],
        existing: Mapping[str, bytes | None],
        package_files: Mapping[str, bytes],
    ) -> bool:
        tracked = self._git("ls-tree", "-r", "--name-only", commit, "--", *relative_paths).splitlines()
        return set(tracked) == set(relative_paths) and all(
            self._git_blob_bytes(commit, relative_path) == package_files[name] and existing[name] == package_files[name]
            for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
        )

    def _git_blob_bytes(self, commit: str, relative_path: str) -> bytes:
        result = self._run_git("show", f"{commit}:{relative_path}", check=False)
        return result.stdout if result.returncode == 0 else b""

    def _is_direct_child(self, parent: str, commit: str) -> bool:
        parents = self._git("rev-list", "--parents", "-n", "1", commit).split()
        return len(parents) == _COMMIT_PARENT_COUNT and parents[1] == parent

    @staticmethod
    def _read_optional_worktree_file(path: Path) -> bytes | None:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            _workspace_failure("Design package snapshot path is unsafe")
        return path.read_bytes() if path.exists() else None

    @staticmethod
    def _write_design_package_files(
        worktree: Path,
        relative_paths: tuple[str, ...],
        package_files: Mapping[str, bytes],
    ) -> None:
        for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True):
            path = worktree / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(package_files[name])

    def _restore_worktree_files(
        self,
        worktree: Path,
        relative_paths: tuple[str, ...],
        existing: Mapping[str, bytes | None],
    ) -> None:
        self._git("reset", "HEAD", "--", *relative_paths, cwd=worktree, check=False)
        for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True):
            path = worktree / relative_path
            previous = existing[name]
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous)

    def observed_change_head(self, change_id: str) -> str:
        """Read the current managed Change branch head without mutating any checkout."""
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        return self._resolve(coordination.branch)

    def recovery_snapshot(self, change_id: str, attempt_id: str) -> WorkspaceRecoverySnapshot:
        """Inspect exact recovery state without changing the branch, worktree, or custody."""
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        branch_head = self._resolve(coordination.branch)
        attempt_ref = f"refs/owlbear/attempts/{change_id}/{attempt_id}"
        self._git("check-ref-format", attempt_ref)
        preserved = self._resolve(attempt_ref, missing_ok=True)
        worktree_head = None
        worktree_branch = None
        clean = False
        if coordination.worktree_path.exists():
            worktree_head = self._resolve("HEAD", cwd=coordination.worktree_path)
            worktree_branch = self._git(
                "-C",
                str(coordination.worktree_path),
                "branch",
                "--show-current",
            )
            clean = not self._git("--no-optional-locks", "-C", str(coordination.worktree_path), "status", "--porcelain")
        quarantine = coordination.dirty_worktree_quarantine
        return WorkspaceRecoverySnapshot(
            change_id=change_id,
            worktree_path=coordination.worktree_path,
            branch=coordination.branch,
            branch_head=branch_head,
            worktree_head=worktree_head,
            worktree_branch=worktree_branch,
            last_reviewed_commit=coordination.last_reviewed_commit,
            preserved_commit=preserved,
            quarantine_ref=quarantine.quarantine_ref if quarantine is not None else None,
            quarantine_commit=quarantine.quarantine_commit if quarantine is not None else None,
            clean=clean,
            reviewed_ancestor=self._is_ancestor(
                coordination.last_reviewed_commit,
                branch_head,
                cwd=self._repository,
            ),
            preserved_reviewed_ancestor=(
                preserved is None
                or self._is_ancestor(
                    coordination.last_reviewed_commit,
                    preserved,
                    cwd=self._repository,
                )
            ),
            writer=coordination.writer,
        )

    def quarantine_dirty_worktree(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
        operation_id: str,
    ) -> DirtyWorktreeQuarantineReceipt:
        """Preserve a dirty Builder worktree as an isolated commit before cleanup."""
        coordination = self._coordinator.show(change_id)
        writer = coordination.writer
        if (
            coordination.builder_handoff is not None
            or coordination.finalization_attention is not None
            or (writer is not None and writer.kind in {"handoff", "finalization-attention"})
        ):
            _coordination_conflict("passive workspace custody cannot quarantine preserved content")
        if writer is None or writer.attempt_id != attempt_id or writer.claim_id != claim_id:
            _coordination_conflict("dirty worktree quarantine requires matching writer custody")
        worktree = coordination.worktree_path
        branch_head = self._resolve(coordination.branch)
        self._require_worktree(change_id, worktree, coordination.branch, branch_head)
        quarantine_ref = f"refs/owlbear/quarantine/{change_id}/{attempt_id}"
        self._git("check-ref-format", quarantine_ref)
        receipt = self._prepare_dirty_worktree_quarantine(
            coordination=coordination,
            worktree=worktree,
            branch_head=branch_head,
            quarantine_ref=quarantine_ref,
            operation_id=operation_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
        )
        if self._resolve(coordination.branch) != branch_head:
            _workspace_failure("change branch moved while dirty worktree was being quarantined")
        self._git("reset", "--hard", branch_head, cwd=worktree)
        self._git("clean", "-fd", cwd=worktree)
        if self._git("status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=worktree):
            _workspace_failure("dirty worktree quarantine did not clean the managed worktree")
        return receipt

    def _prepare_dirty_worktree_quarantine(  # noqa: PLR0913, PLR0917
        self,
        coordination: ChangeCoordination,
        worktree: Path,
        branch_head: str,
        quarantine_ref: str,
        operation_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DirtyWorktreeQuarantineReceipt:
        current = self._coordinator.show(coordination.change_id)
        existing_receipt = current.dirty_worktree_quarantine
        if existing_receipt is not None:
            if (
                existing_receipt.operation_id != operation_id
                or existing_receipt.attempt_id != attempt_id
                or existing_receipt.claim_id != claim_id
                or existing_receipt.quarantine_ref != quarantine_ref
            ):
                _coordination_conflict("dirty worktree quarantine already has different authority")
            if not self._quarantine_base_matches_current(coordination, branch_head, existing_receipt):
                _workspace_failure("dirty worktree quarantine base moved outside the recoverable restart state")
            existing_commit = self._resolve(existing_receipt.quarantine_ref)
            if existing_commit != existing_receipt.quarantine_commit:
                _workspace_failure("dirty worktree quarantine ref does not match its receipt")
            self._verify_quarantine_commit(
                existing_receipt.quarantine_commit,
                existing_receipt.base_head,
                existing_receipt.paths,
                existing_receipt.operation_id,
            )
            self._verify_worktree_matches_quarantine(worktree, existing_receipt)
            return existing_receipt

        paths = self._worktree_change_paths(worktree)
        receipt_base_head = branch_head
        existing = self._resolve(quarantine_ref, missing_ok=True)
        if existing is None:
            if not paths:
                _coordination_conflict("dirty worktree quarantine requires changed content")
            quarantine_commit = self._quarantine_commit(worktree, branch_head, paths, operation_id)
            self._git("update-ref", quarantine_ref, quarantine_commit, "0" * 40)
        else:
            quarantine_commit = existing
            quarantine_base = self._quarantine_commit_parent(quarantine_commit)
            paths = self._quarantine_commit_paths(quarantine_commit, quarantine_base)
            self._verify_quarantine_commit(quarantine_commit, quarantine_base, paths, operation_id)
            replay_receipt = DirtyWorktreeQuarantineReceipt.create(
                operation_id=operation_id,
                change_id=coordination.change_id,
                attempt_id=attempt_id,
                claim_id=claim_id,
                branch=coordination.branch,
                worktree_path=worktree,
                base_head=quarantine_base,
                quarantine_ref=quarantine_ref,
                quarantine_commit=quarantine_commit,
                paths=paths,
            )
            if not self._quarantine_base_matches_current(coordination, branch_head, replay_receipt):
                _workspace_failure("dirty worktree quarantine base moved outside the recoverable restart state")
            self._verify_worktree_matches_quarantine(worktree, replay_receipt)
            receipt_base_head = quarantine_base
        receipt = DirtyWorktreeQuarantineReceipt.create(
            operation_id=operation_id,
            change_id=coordination.change_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
            branch=coordination.branch,
            worktree_path=worktree,
            base_head=receipt_base_head,
            quarantine_ref=quarantine_ref,
            quarantine_commit=quarantine_commit,
            paths=paths,
        )
        self._coordinator.update(current.model_copy(update={"dirty_worktree_quarantine": receipt}))
        return receipt

    def verify_dirty_worktree_quarantine(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
        operation_id: str,
    ) -> DirtyWorktreeQuarantineReceipt:
        """Verify preserved dirty-worktree evidence after workspace cleanup and writer release."""
        coordination = self._coordinator.show(change_id)
        receipt = coordination.dirty_worktree_quarantine
        if receipt is None:
            _coordination_conflict("dirty worktree quarantine receipt is missing")
        if receipt.operation_id != operation_id or receipt.attempt_id != attempt_id or receipt.claim_id != claim_id:
            _coordination_conflict("dirty worktree quarantine receipt does not match the recovery claim")
        branch_head = self._resolve(coordination.branch)
        if self._resolve(receipt.quarantine_ref) != receipt.quarantine_commit:
            _workspace_failure("dirty worktree quarantine ref does not match its receipt")
        if not self._quarantine_base_matches_current(coordination, branch_head, receipt):
            _workspace_failure("dirty worktree quarantine base moved outside the recoverable restart state")
        self._verify_quarantine_commit(
            receipt.quarantine_commit,
            receipt.base_head,
            receipt.paths,
            receipt.operation_id,
        )
        self._require_worktree(change_id, coordination.worktree_path, coordination.branch, branch_head)
        if self._git("status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=coordination.worktree_path):
            _workspace_failure("dirty worktree quarantine evidence requires a clean managed worktree")
        return receipt

    def _quarantine_base_matches_current(
        self,
        coordination: ChangeCoordination,
        branch_head: str,
        receipt: DirtyWorktreeQuarantineReceipt,
    ) -> bool:
        if receipt.base_head == branch_head:
            return True
        if branch_head != coordination.last_reviewed_commit:
            return False
        attempt_ref = f"refs/owlbear/attempts/{coordination.change_id}/{receipt.attempt_id}"
        preserved = self._resolve(attempt_ref, missing_ok=True)
        return preserved == receipt.base_head and self._is_ancestor(
            coordination.last_reviewed_commit,
            receipt.base_head,
            cwd=self._repository,
        )

    def _worktree_change_paths(self, worktree: Path) -> tuple[str, ...]:
        status = self._run_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            cwd=worktree,
        ).stdout
        if status and not status.endswith(b"\0"):
            _workspace_failure("Git returned an unterminated dirty worktree status")
        paths: set[str] = set()
        records = status.split(b"\0")
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            if len(record) < _PORCELAIN_WORKTREE_STATUS_PREFIX_LENGTH:
                _workspace_failure("Git returned an invalid dirty worktree status record")
            status_code = record[:2].decode("ascii")
            paths.add(os.fsdecode(record[3:]))
            if "R" in status_code or "C" in status_code:
                if index >= len(records) or not records[index]:
                    _workspace_failure("Git returned an incomplete rename status record")
                paths.add(os.fsdecode(records[index]))
                index += 1
        return tuple(sorted(paths))

    def _verify_worktree_matches_quarantine(
        self,
        worktree: Path,
        receipt: DirtyWorktreeQuarantineReceipt,
    ) -> None:
        current_paths = self._worktree_change_paths(worktree)
        if not set(current_paths).issubset(receipt.paths):
            _workspace_failure("dirty worktree changed after quarantine preservation")
        if not current_paths:
            return
        self._verify_worktree_paths_match_commit(
            worktree,
            receipt.base_head,
            current_paths,
            receipt.quarantine_commit,
        )

    def _verify_worktree_paths_match_commit(
        self,
        worktree: Path,
        base_head: str,
        paths: tuple[str, ...],
        commit: str,
    ) -> None:
        tree = self._worktree_tree(worktree, base_head, paths)
        result = self._run_git(
            "--literal-pathspecs",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--quiet",
            commit,
            tree,
            "--",
            *paths,
            check=False,
        )
        if result.returncode != 0:
            _workspace_failure("dirty worktree content changed after quarantine preservation")

    def _worktree_tree(self, worktree: Path, base_head: str, paths: tuple[str, ...]) -> str:
        index_fd, index_path = tempfile.mkstemp(prefix="owlbear-quarantine-index-")
        os.close(index_fd)
        Path(index_path).unlink()
        environment = {**os.environ, "GIT_INDEX_FILE": index_path}
        try:
            self._run_git("read-tree", base_head, cwd=worktree, environment=environment)
            self._run_git(
                "--literal-pathspecs",
                "add",
                "--all",
                "--",
                *paths,
                cwd=worktree,
                environment=environment,
            )
            return self._run_git("write-tree", cwd=worktree, environment=environment).stdout.decode().strip()
        finally:
            Path(index_path).unlink(missing_ok=True)

    def _quarantine_commit(
        self,
        worktree: Path,
        base_head: str,
        paths: tuple[str, ...],
        operation_id: str,
    ) -> str:
        index_fd, index_path = tempfile.mkstemp(prefix="owlbear-quarantine-index-")
        os.close(index_fd)
        Path(index_path).unlink()
        environment = {**os.environ, "GIT_INDEX_FILE": index_path}
        try:
            tree = self._worktree_tree(worktree, base_head, paths)
            commit = (
                self._run_git(
                    "commit-tree",
                    tree,
                    "-p",
                    base_head,
                    "-m",
                    _quarantine_commit_message(operation_id),
                    cwd=worktree,
                    environment={
                        **environment,
                        "GIT_AUTHOR_NAME": "OwlBear",
                        "GIT_AUTHOR_EMAIL": "owlbear@localhost",
                        "GIT_COMMITTER_NAME": "OwlBear",
                        "GIT_COMMITTER_EMAIL": "owlbear@localhost",
                    },
                )
                .stdout.decode()
                .strip()
            )
            self._verify_quarantine_commit(commit, base_head, paths, operation_id)
            return commit
        finally:
            Path(index_path).unlink(missing_ok=True)

    def _verify_quarantine_commit(
        self,
        commit: str,
        base_head: str,
        paths: tuple[str, ...],
        operation_id: str,
    ) -> None:
        parents = self._git("rev-list", "--parents", "-n", "1", commit).split()
        if parents != [commit, base_head]:
            _workspace_failure("quarantine commit does not have the exact reviewed worktree parent")
        message = self._git("show", "-s", "--format=%B", commit).rstrip()
        if message != _quarantine_commit_message(operation_id):
            _workspace_failure("quarantine commit does not belong to the recovery operation")
        changed = self._quarantine_commit_paths(commit, base_head)
        if changed != paths:
            _workspace_failure("quarantine commit does not contain the complete dirty worktree")

    def _quarantine_commit_paths(self, commit: str, base_head: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                os.fsdecode(path)
                for path in self._run_git(
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--no-renames",
                    "--name-only",
                    "-z",
                    base_head,
                    commit,
                ).stdout.split(b"\0")
                if path
            )
        )

    def _quarantine_commit_parent(self, commit: str) -> str:
        parents = self._git("rev-list", "--parents", "-n", "1", commit).split()
        if len(parents) != _COMMIT_PARENT_COUNT:
            _workspace_failure("quarantine commit does not have exactly one parent")
        return parents[1]
