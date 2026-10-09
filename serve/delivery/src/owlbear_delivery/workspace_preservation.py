"""Finalization and recovery workspace capture, preservation receipts and restoration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from contextlib import contextmanager, suppress
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RecoveryEvidence,
    RecoveryIntent,
    RecoveryReceipt,
    digest,
    is_canonical_admitted_path,
    journal_path,
    read_record,
)
from owlbear_delivery.runtime_transaction import (
    ContainedWriteLimits,
    contained_directory,
    read_contained,
    write_contained,
)
from owlbear_delivery.workspace_models import (
    _DIGEST_PATTERN,
    _FILE_PERMISSION_MASK,
    _MAX_PRESERVED_FILE_BYTES,
    _MAX_PRESERVED_PATHS,
    _MAX_PRESERVED_TOTAL_BYTES,
    _MAX_RESTORATION_INCOMPLETE_ARTIFACTS,
    _PRESERVATION_ENV_OVERRIDES,
    _PRESERVATION_FILE_IDENTITY_FIELDS,
    _PRESERVATION_INDEX_METADATA_FIELDS,
    _RESTORATION_RECORD_TEMPORARY_MODE,
    _RESTORATION_RECORD_TEMPORARY_PATTERN,
    _RESTORATION_STAGE_PATTERN,
    ChangeCoordination,
    PreservationEntry,
    PreservationFenceError,
    PreservationProvenanceEvidence,
    PreservationRejectedError,
    WorktreePreservationReceipt,
    _ManagedIndexIdentity,
    _open_worktree_parent,
    _preservation_manifest_payload,
    _preservation_receipt_from_payload,
    _preservation_temporary_name,
    _PreservedPathState,
    _reject_symlink_ancestors,
    _same_staging_identity,
    _WorktreeRestorationContext,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class _PreservationMixin:
    """Finalization and recovery workspace capture, preservation receipts and restoration."""

    def capture_finalization_workspace(
        self,
        change_id: str,
        promoted_commits: tuple[str, ...],
    ) -> tuple[ChangeCoordination, str, str, tuple[str, ...], str | None]:
        """Capture bounded workspace facts without changing checkout or custody."""
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        head = self.observed_change_head(change_id)
        self._require_worktree(change_id, coordination.worktree_path, coordination.branch, head)
        status = self._run_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            cwd=coordination.worktree_path,
            environment={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        ).stdout
        paths = self._dirty_paths(status)
        fingerprint = hashlib.sha256(head.encode() + b"\0" + status)
        fingerprint.update(self._run_git("diff", "HEAD", "--binary", cwd=coordination.worktree_path).stdout)
        for relative in paths:
            try:
                metadata = (coordination.worktree_path / relative).lstat()
            except FileNotFoundError:
                fingerprint.update(repr((relative, "absent")).encode())
            else:
                fingerprint.update(
                    repr(
                        (relative, metadata.st_mode, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)
                    ).encode()
                )
        reason = self._captured_finalization_guard(coordination, head, promoted_commits)
        return coordination, head, fingerprint.hexdigest(), paths, reason or ("workspace-dirty" if status else None)

    def capture_recovery_workspace(
        self,
        change_id: str,
        promoted_commits: tuple[str, ...],
        *,
        expected_paths: tuple[str, ...] | None = None,
        expected_scope_details: tuple[tuple[str, ...], dict[str, str]] | None = None,
    ) -> tuple[ChangeCoordination, str, str, tuple[str, ...], str | None]:
        """Inspect retained custody without exempting damaged or dirty workspace state."""
        coordination, head, status, paths, reason = self.capture_recovery_workspace_metadata(
            change_id, promoted_commits
        )
        ignored = self._run_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--ignored=matching",
            "--untracked-files=normal",
            cwd=coordination.worktree_path,
            environment={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        ).stdout
        ignored_inventory = self._has_ignored_inventory(ignored)
        if ignored_inventory and expected_paths is not None:
            raise DeliveryWorkerExclusionRequiredError
        if expected_paths is not None and paths != expected_paths:
            raise DeliveryWorkerExclusionRequiredError
        if expected_paths is not None:
            self._validate_recovery_path_containment(coordination.worktree_path, expected_paths)
        self._validate_recovery_scope(coordination.worktree_path, expected_scope_details)
        fingerprint_hex = self._recovery_workspace_fingerprint(
            coordination.worktree_path,
            head,
            status,
            paths,
            expected_paths,
        )
        return (
            coordination,
            head,
            fingerprint_hex,
            paths,
            reason or ("workspace-dirty" if status or ignored_inventory else None),
        )

    @staticmethod
    def _validate_recovery_scope(
        worktree: Path,
        expected_scope_details: tuple[tuple[str, ...], dict[str, str]] | None,
    ) -> None:
        if expected_scope_details is None:
            return
        scope, expected_kinds = expected_scope_details
        for relative in scope:
            if not is_canonical_admitted_path(relative):
                raise DeliveryWorkerExclusionRequiredError
            candidate = worktree
            try:
                for part in PurePosixPath(relative).parts:
                    candidate /= part
                    metadata = candidate.lstat()
                    if stat.S_ISLNK(metadata.st_mode):
                        raise DeliveryWorkerExclusionRequiredError
            except FileNotFoundError:
                actual_kind = expected_kinds[relative]
            else:
                actual_kind = "directory" if stat.S_ISDIR(metadata.st_mode) else "file"
            if actual_kind != expected_kinds[relative]:
                raise DeliveryWorkerExclusionRequiredError

    def _recovery_workspace_fingerprint(
        self,
        worktree: Path,
        head: str,
        status: bytes,
        paths: tuple[str, ...],
        expected_paths: tuple[str, ...] | None,
    ) -> str:
        fingerprint = hashlib.sha256(head.encode() + b"\0" + status)
        if expected_paths:
            # Admission has fenced the path set; keep the content read inside that fence.
            fingerprint.update(
                self._run_git(
                    "diff",
                    "HEAD",
                    "--binary",
                    "--",
                    *(f":(literal){path}" for path in expected_paths),
                    cwd=worktree,
                ).stdout
            )
        for relative in paths:
            try:
                metadata = (worktree / relative).lstat()
            except FileNotFoundError:
                fingerprint.update(repr((relative, "absent")).encode())
            else:
                fingerprint.update(
                    repr(
                        (relative, metadata.st_mode, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)
                    ).encode()
                )
        # The admission caller supplies the exact path set only after checking
        # the active task scope.  Read those paths now, rather than during the
        # metadata-only preflight, so untracked bytes participate in the
        # persisted authority fingerprint without widening the read boundary.
        if expected_paths is not None:
            for relative in paths:
                state = self._read_worktree_state(worktree, relative)
                fingerprint.update(
                    repr(
                        (
                            relative,
                            state.kind,
                            state.mode,
                            state.identity,
                            digest(state.content) if state.content is not None else None,
                        )
                    ).encode()
                )
        return fingerprint.hexdigest()

    def capture_recovery_workspace_metadata(
        self, change_id: str, promoted_commits: tuple[str, ...], *, ignored_is_dirty: bool = True
    ) -> tuple[ChangeCoordination, str, bytes, tuple[str, ...], str | None]:
        """Capture recovery status and custody facts without reading dirty content.

        Builder handoff passes `ignored_is_dirty=False`: ignored caches stay in place, unpreserved and unfenced.
        """
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        head = self.observed_change_head(change_id)
        self._require_worktree(change_id, coordination.worktree_path, coordination.branch, head)
        status = self._run_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            cwd=coordination.worktree_path,
            environment={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        ).stdout
        paths = self._dirty_paths(status)
        reason = self._captured_finalization_guard(coordination, head, promoted_commits)
        if ignored_is_dirty and self._has_ignored_inventory(
            self._run_git(
                "status",
                "--porcelain=v1",
                "-z",
                "--ignored=matching",
                "--untracked-files=normal",
                cwd=coordination.worktree_path,
                environment={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            ).stdout
        ):
            return coordination, head, status, paths, reason or "workspace-dirty"
        if reason == "active-custody" and coordination.publication_lease is None:
            reason = self._captured_finalization_guard(
                coordination.model_copy(update={"writer": None}), head, promoted_commits
            )
        return coordination, head, status, paths, reason or ("workspace-dirty" if status else None)

    def baseline_scope_kinds(self, worktree: Path, head: str, scopes: tuple[str, ...]) -> dict[str, str]:
        """Classify missing task surfaces from the exact reviewed tree."""
        self._require_preservation_environment()
        kinds: dict[str, str] = {}
        for scope in scopes:
            output = self._run_git("ls-tree", "-z", head, "--", scope, cwd=worktree).stdout
            if not output:
                kinds[scope] = "missing"
                continue
            fields = output.split(b"\t", 1)[0].split()
            if not fields:
                raise DeliveryWorkerExclusionRequiredError
            mode = fields[0]
            if mode == b"040000":
                kinds[scope] = "directory"
            elif mode == b"120000":
                raise DeliveryWorkerExclusionRequiredError
            else:
                kinds[scope] = "file"
        return kinds

    def capture_preservation(  # noqa: C901, PLR0912, PLR0915 - capture keeps each fence in one transaction.
        self,
        change_id: str,
        recovery_id: str,
    ) -> WorktreePreservationReceipt:
        """Capture exact dirty paths and the managed index before any private write.

        This is deliberately independent of the legacy commit quarantine.  It reads the
        registered worktree's real index through Git, rejects unsafe/private material
        before creating the preservation directory, and stores raw bytes only below the
        owner-private recovery receipt.
        """
        self._require_preservation_identity(recovery_id)
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        intent, _recovery = self._require_preservation_authority(change_id, recovery_id, coordination)
        branch_head = self._resolve(coordination.branch)
        if branch_head != intent.exact_head:
            msg = "Change branch head does not match the verified recovery boundary"
            raise PreservationFenceError(msg)
        worktree = self._canonical_worktree_path(change_id, coordination.worktree_path)
        self._require_worktree(change_id, worktree, coordination.branch, branch_head)
        target_head = self.observed_target_head()
        if target_head != intent.target_head:
            msg = "integration target moved since verified recovery"
            raise PreservationFenceError(msg)
        frontier_bytes = self._read_frontier_bytes(change_id)
        coordination_authority = self._coordinator.recovery_authority_digest(change_id)
        worktree_identity = self._directory_identity(worktree, "registered worktree")
        repository_identity = self._directory_identity(self._repository, "managed repository")
        index = self._resolve_managed_index(worktree)
        common_identity = self._directory_identity(index.common_directory, "Git common directory")
        administration_identity = self._directory_identity(index.administration, "Git administration directory")
        runtime_identity = self._directory_identity(self.runtime_root, "runtime root")
        # Classify the complete dirty-path inventory before reading any raw
        # index or worktree bytes into the private preservation store.
        staged = self._preservation_git(
            "diff",
            "--cached",
            "--quiet",
            "--ignore-submodules",
            "--",
            cwd=worktree,
            check=False,
        )
        if staged.returncode == 1:
            msg = "pre-existing staged content is not eligible for raw recovery"
            raise PreservationRejectedError(msg)
        if staged.returncode != 0:
            msg = "managed index state could not be compared with the exact HEAD"
            raise PreservationRejectedError(msg)
        status = self._preservation_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--ignored=matching",
            "--untracked-files=all",
            cwd=worktree,
        ).stdout
        paths = self._preservation_status_paths(status)
        if len(paths) > _MAX_PRESERVED_PATHS:
            msg = "changed path count exceeds the bounded preservation policy"
            raise PreservationRejectedError(msg)
        self._require_admitted_paths(intent, paths)
        self._validate_private_paths(paths)

        index_bytes = self._read_managed_index(index)
        self._validate_private_content(index_bytes)
        shared_index = self._preservation_git(
            "rev-parse",
            "--shared-index-path",
            cwd=worktree,
            check=False,
        )
        if shared_index.returncode not in (0, 128):
            msg = "managed index split-state could not be established"
            raise PreservationRejectedError(msg)
        if shared_index.returncode == 0 and shared_index.stdout.strip():
            msg = "split-index dependencies require containment"
            raise PreservationRejectedError(msg)
        index_records = self._index_entry_records(worktree)
        entries = tuple((path, mode, stage) for path, mode, stage, _object_id in index_records)
        self._validate_index_entries(entries)
        head_entries = self._head_entries(worktree, branch_head)
        index_path_names = self._validate_index_extensions(
            index_bytes,
            expected_entries=index_records,
            head_entries=head_entries,
        )
        if len(index_bytes) > _MAX_PRESERVED_FILE_BYTES:
            msg = "managed Git index exceeds the per-file preservation limit"
            raise PreservationRejectedError(msg)
        index_bytes_digest = hashlib.sha256(index_bytes).hexdigest()
        current_metadata = tuple((path, *self._read_worktree_metadata(worktree, path)) for path in paths)
        provenance = self._classify_preservation(
            change_id=change_id,
            intent=intent,
            recovery_id=recovery_id,
            worktree_path=worktree,
            current_metadata=current_metadata,
            exact_head=branch_head,
            index_digest=index_bytes_digest,
            index_entries=index_records,
            head_entries=head_entries,
            paths=paths,
        )
        self._validate_index_path_names(index_path_names)
        raw_states: dict[str, tuple[_PreservedPathState, _PreservedPathState]] = {}
        total = len(index_bytes)
        for path in paths:
            self._validate_preservation_path(worktree, path)
            current = self._read_worktree_state(worktree, path)
            baseline = self._read_head_state(worktree, branch_head, path)
            for state in (current, baseline):
                if state.content is not None:
                    self._validate_private_content(state.content)
                    if len(state.content) > _MAX_PRESERVED_FILE_BYTES:
                        msg = "a preserved file exceeds the per-file limit"
                        raise PreservationRejectedError(msg)
                    total += len(state.content)
            raw_states[path] = (current, baseline)
        self._validate_provenance_states(provenance, {path: state[0] for path, state in raw_states.items()})
        if total > _MAX_PRESERVED_TOTAL_BYTES:
            msg = "raw preservation exceeds the total bounded limit"
            raise PreservationRejectedError(msg)
        reread_states = {path: self._read_worktree_state(worktree, path) for path in paths}
        if any(not self._same_state(reread_states[path], raw_states[path][0]) for path in paths):
            msg = "worktree path bytes or metadata changed during preservation capture"
            raise PreservationFenceError(msg)
        self._validate_provenance_states(
            provenance,
            {path: reread_states[path] for path in paths},
        )
        # Recheck the complete authority, manifest inputs, and every root descriptor after
        # the complete read and before the first preservation write.
        current_coordination = self._coordinator.show(change_id)
        current_intent, current_recovery = self._require_preservation_authority(
            change_id, recovery_id, current_coordination
        )
        if (
            current_intent != intent
            or current_recovery != _recovery
            or self._coordinator.recovery_authority_digest(change_id) != coordination_authority
            or self._read_frontier_bytes(change_id) != frontier_bytes
            or self.observed_target_head() != target_head
            or self._directory_identity(worktree, "registered worktree")[:3] != worktree_identity[:3]
            or self._directory_identity(self._repository, "managed repository") != repository_identity
            or self._directory_identity(self.runtime_root, "runtime root") != runtime_identity
        ):
            msg = "preservation authority or root descriptor changed during capture"
            raise PreservationFenceError(msg)
        self._require_worktree(change_id, worktree, coordination.branch, branch_head)
        current_index = self._resolve_managed_index(worktree)
        current_common = self._directory_identity(current_index.common_directory, "Git common directory")
        current_administration = self._directory_identity(current_index.administration, "Git administration directory")
        if (
            current_index != index
            or current_common != common_identity
            or current_administration != administration_identity
            or self._read_managed_index(current_index) != index_bytes
        ):
            msg = "managed index changed during preservation capture"
            raise PreservationFenceError(msg)
        if self._resolve(coordination.branch) != branch_head:
            msg = "Change branch moved during preservation capture"
            raise PreservationFenceError(msg)
        current_shared_index = self._preservation_git(
            "rev-parse",
            "--shared-index-path",
            cwd=worktree,
            check=False,
        )
        if (
            current_shared_index.returncode != shared_index.returncode
            or current_shared_index.stdout != shared_index.stdout
        ):
            msg = "managed index split state changed during preservation capture"
            raise PreservationFenceError(msg)
        current_staged = self._preservation_git(
            "diff",
            "--cached",
            "--quiet",
            "--ignore-submodules",
            "--",
            cwd=worktree,
            check=False,
        )
        if current_staged.returncode != staged.returncode:
            msg = "managed index content changed during preservation capture"
            raise PreservationFenceError(msg)
        current_status = self._preservation_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--ignored=matching",
            "--untracked-files=all",
            cwd=worktree,
        ).stdout
        if current_status != status:
            msg = "worktree path inventory changed during preservation capture"
            raise PreservationFenceError(msg)
        final_states = {path: self._read_worktree_state(worktree, path) for path in paths}
        if any(not self._same_state(final_states[path], raw_states[path][0]) for path in paths):
            msg = "worktree path bytes or metadata changed before preservation write"
            raise PreservationFenceError(msg)
        self._validate_provenance_states(provenance, final_states)
        final_metadata = tuple((path, final_states[path].kind, final_states[path].mode) for path in paths)

        entries_meta: list[PreservationEntry] = []
        objects: dict[str, bytes] = {index_bytes_digest: index_bytes}
        provenance_by_path = {item.path: item for item in provenance.paths}
        for path in paths:
            current, baseline = raw_states[path]
            before_object = self._preservation_object_name(current.content)
            after_object = self._preservation_object_name(baseline.content)
            if current.content is not None:
                objects[before_object] = current.content
            if baseline.content is not None:
                objects[after_object] = baseline.content
            entries_meta.append(
                PreservationEntry(
                    path=path,
                    before_kind=current.kind,
                    after_kind=baseline.kind,
                    before_digest=self._state_digest(current),
                    after_digest=self._state_digest(baseline),
                    before_mode=current.mode,
                    after_mode=baseline.mode,
                    before_object=before_object if current.content is not None else None,
                    after_object=after_object if baseline.content is not None else None,
                    before_identity=current.identity,
                    provenance=provenance_by_path[path],
                )
            )
        preservation_material = [
            recovery_id.encode(),
            change_id.encode(),
            index_bytes,
            status,
            json.dumps(provenance.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode(),
        ]
        for entry in entries_meta:
            preservation_material.extend(
                (
                    entry.path.encode(),
                    entry.before_kind.encode(),
                    entry.after_kind.encode(),
                    (entry.before_digest or "").encode(),
                    (entry.after_digest or "").encode(),
                    repr(entry.before_mode).encode(),
                    repr(entry.after_mode).encode(),
                    repr(entry.before_identity).encode(),
                    json.dumps(
                        entry.provenance.model_dump(mode="json") if entry.provenance is not None else None,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode(),
                )
            )
        preservation_id = hashlib.sha256(b"\0".join(preservation_material)).hexdigest()
        receipt = WorktreePreservationReceipt.create(
            preservation_id=preservation_id,
            recovery_id=recovery_id,
            change_id=change_id,
            branch=coordination.branch,
            worktree_path=worktree,
            branch_head=branch_head,
            reviewed_head=coordination.last_reviewed_commit,
            target_head=target_head,
            integration_target=coordination.integration_target,
            frontier_digest=digest(frontier_bytes),
            coordination_digest=coordination_authority,
            repository=self._repository,
            runtime_root=self.runtime_root,
            worktree_device=worktree_identity[0],
            worktree_inode=worktree_identity[1],
            worktree_mode=worktree_identity[2],
            worktree_links=worktree_identity[3],
            repository_device=repository_identity[0],
            repository_inode=repository_identity[1],
            common_device=common_identity[0],
            common_inode=common_identity[1],
            administration_device=administration_identity[0],
            administration_inode=administration_identity[1],
            runtime_device=runtime_identity[0],
            runtime_inode=runtime_identity[1],
            index_path=index.path,
            administration=index.administration,
            common_directory=index.common_directory,
            maintained_surfaces=intent.maintained_surfaces,
            last_write_provenance=intent.last_write_provenance,
            index_digest=index_bytes_digest,
            index_size=len(index_bytes),
            paths=tuple(sorted(entries_meta, key=lambda item: item.path)),
            provenance=provenance,
        )
        self._reverify_preservation_provenance(
            change_id=change_id,
            intent=current_intent,
            evidence=provenance,
            recovery_id=recovery_id,
            worktree_path=worktree,
            current_metadata=final_metadata,
            exact_head=branch_head,
            index_digest=index_bytes_digest,
            index_entries=index_records,
            head_entries=head_entries,
            paths=paths,
        )
        self._write_preservation_store(
            receipt,
            objects,
            index=index,
        )
        self._verify_preservation_store(receipt, objects)
        return receipt

    # The explicit aliases keep the owner operation discoverable without creating a
    # second implementation or a second authority identity.
    capture_raw_preservation = capture_preservation

    def verify_preservation(
        self,
        change_id: str,
        preservation_id: str,
    ) -> WorktreePreservationReceipt:
        """Verify private preservation evidence and current registration without mutation."""
        self._require_preservation_identity(preservation_id)
        self._require_preservation_environment()
        receipt, index_metadata, inventory = self._read_preservation_manifest(change_id, preservation_id)
        if receipt.change_id != change_id or receipt.preservation_id != preservation_id:
            msg = "preservation identity does not match its private manifest"
            raise PreservationFenceError(msg)
        self._verify_preservation_fences(
            change_id,
            receipt,
            index_metadata,
            allow_legacy_provenance=True,
        )
        objects: dict[str, bytes] = {}
        for object_name in inventory:
            content = self._read_private_preservation_object(receipt, object_name)
            if hashlib.sha256(content).hexdigest() != object_name:
                msg = "private preservation object failed verification"
                raise PreservationFenceError(msg)
            objects[object_name] = content
        self._verify_preservation_store(receipt, objects, allow_legacy_index_extensions=True)
        return receipt

    def restore_preservation(  # noqa: C901, PLR0912, PLR0915 - restoration keeps each exact fence in one transaction.
        self,
        change_id: str,
        preservation_id: str,
        *,
        paths: tuple[str, ...] | None = None,
    ) -> WorktreePreservationReceipt:
        """Restore only recorded paths, retaining private evidence on any fence failure."""
        self._require_preservation_identity(preservation_id)
        self._require_preservation_environment()
        receipt, index_metadata, inventory = self._read_preservation_manifest(change_id, preservation_id)
        provenance_by_path = (
            {item.path: item for item in receipt.provenance.paths} if receipt.provenance is not None else {}
        )
        if paths is None:
            selected = tuple(
                entry.path
                for entry in receipt.paths
                if provenance_by_path.get(entry.path) is not None
                and provenance_by_path[entry.path].disposition == "disposable"
            )
        else:
            selected = tuple(paths)
            if selected != tuple(sorted(set(selected))) or not set(selected) <= {entry.path for entry in receipt.paths}:
                msg = "restoration paths must be an exact subset of the preservation"
                raise PreservationRejectedError(msg)
            if any(provenance_by_path.get(path) is None for path in selected):
                raise PreservationRejectedError("restoration provenance is unavailable")  # noqa: EM101, TRY003
            if any(provenance_by_path[path].disposition != "disposable" for path in selected):
                raise PreservationRejectedError(  # noqa: TRY003
                    "only proven disposable paths may be restored automatically"  # noqa: EM101
                )
        worktree, _index = self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
        objects = {
            object_name: self._read_private_preservation_object(receipt, object_name) for object_name in inventory
        }
        if (
            len(objects[receipt.index_digest]) != receipt.index_size
            or hashlib.sha256(objects[receipt.index_digest]).hexdigest() != receipt.index_digest
        ):
            msg = "private preservation index object failed verification"
            raise PreservationFenceError(msg)
        self._verify_preservation_store(receipt, objects)
        entries = {entry.path: entry for entry in receipt.paths}
        expected_states = {
            path: self._state_from_entry(entry, before=True, receipt=receipt) for path, entry in entries.items()
        }
        desired_states = {
            path: self._state_from_entry(entry, before=False, receipt=receipt) for path, entry in entries.items()
        }
        for path in entries:
            self._validate_preservation_path(worktree, path)
        # A process can die after replacing the target but before unlinking the
        # owner-private source.  Let the inventory fence authenticate and
        # remove that exact co-link before ordinary strict reads below.
        self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
        current_states = {path: self._read_worktree_state(worktree, path) for path in entries}
        if any(
            not self._same_state(current_states[path], expected_states[path])
            and not self._same_state(current_states[path], desired_states[path])
            for path in entries
        ):
            changed = next(
                path
                for path in entries
                if not self._same_state(current_states[path], expected_states[path])
                and not self._same_state(current_states[path], desired_states[path])
            )
            msg = f"path identity changed before restoration: {changed}"
            raise PreservationFenceError(msg)
        # Recheck the complete manifest and every path before the first effect.
        self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
        current_states = {path: self._read_worktree_state(worktree, path) for path in entries}
        if any(
            not self._same_state(current_states[path], expected_states[path])
            and not self._same_state(current_states[path], desired_states[path])
            for path in entries
        ):
            msg = "preservation path inventory changed before restoration"
            raise PreservationFenceError(msg)
        with self._restoration_attempt(receipt, selected) as operation_id:
            for path in selected:
                record_name = f"paths/{digest(path.encode())}"
                record = entries[path].model_dump(mode="json")
                self._write_restoration_record(receipt, operation_id, f"{record_name}/intent.json", record)
                self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
                current_states = {item: self._read_worktree_state(worktree, item) for item in entries}
                if any(
                    not self._same_state(current_states[item], expected_states[item])
                    and not self._same_state(current_states[item], desired_states[item])
                    for item in entries
                ):
                    msg = "preservation path inventory changed during restoration"
                    raise PreservationFenceError(msg)
                current = current_states[path]
                desired = desired_states[path]
                if not self._same_state(current, desired):
                    if not self._same_state(current, expected_states[path]):
                        msg = f"path identity changed before restoration: {path}"
                        raise PreservationFenceError(msg)
                    self._write_worktree_state(
                        path,
                        desired,
                        _WorktreeRestorationContext(expected_states[path], operation_id, receipt, worktree),
                    )
                if not self._same_state(self._read_worktree_state(worktree, path), desired):
                    msg = f"path identity changed during restoration: {path}"
                    raise PreservationFenceError(msg)
                self._cleanup_restoration_staging_source(receipt, operation_id, path)
                self._sync_restored_path(worktree, path, desired)
                self._write_restoration_record(receipt, operation_id, f"{record_name}/result.json", record)
            self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
            final_states = {path: self._read_worktree_state(worktree, path) for path in selected}
            if any(not self._same_state(final_states[path], desired_states[path]) for path in selected):
                msg = "preservation restore did not reach every requested path"
                raise PreservationFenceError(msg)
        return receipt

    restore_raw_preservation = restore_preservation

    @contextmanager
    def _restoration_attempt(self, receipt: WorktreePreservationReceipt, selected: tuple[str, ...]) -> Iterator[str]:
        record = {"preservation_receipt_id": receipt.receipt_id, "paths": selected}
        operation_id = digest(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
        self._write_restoration_record(receipt, operation_id, "intent.json", record)
        try:
            yield operation_id
            self._write_restoration_record(receipt, operation_id, "result.json", record)
        except OSError, ValueError, RuntimeError, subprocess.SubprocessError:
            with suppress(OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                self._write_restoration_record(
                    receipt, operation_id, "failure.json", {"code": "restoration-interrupted"}
                )
            raise

    def _write_restoration_record(
        self, receipt: WorktreePreservationReceipt, operation_id: str, name: str, payload: dict[str, object]
    ) -> None:
        relative = Path(receipt.storage_ref) / "restoration" / operation_id / Path(name).parent
        content = (json.dumps({"schema_version": 1, **payload}, sort_keys=True, separators=(",", ":")) + "\n").encode()
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative, create=True) as parent_fd:
                record_path = Path(name).name
                write_contained(parent_fd, Path(record_path), content)
                if read_contained(parent_fd, Path(record_path), limit=len(content)) != content:
                    msg = "private restoration record failed readback"
                    raise PreservationFenceError(msg)
                descriptor = os.open(record_path, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
                try:
                    os.fsync(descriptor)
                    os.fsync(parent_fd)
                finally:
                    os.close(descriptor)
        finally:
            os.close(root_fd)

    @staticmethod
    def _sync_restored_path(worktree: Path, path: str, state: _PreservedPathState) -> None:
        """Establish durability again after a response lost beyond the path effect."""
        relative = PurePosixPath(path)
        parent_fd = _open_worktree_parent(worktree, relative.parts[:-1], create=False)
        try:
            if state.kind == "regular":
                descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)

    def _require_preservation_identity(self, recovery_id: str) -> None:
        if not _DIGEST_PATTERN.fullmatch(recovery_id):
            msg = "recovery identity is not an engine-issued digest"
            raise PreservationRejectedError(msg)

    def _require_preservation_authority(
        self,
        change_id: str,
        recovery_id: str,
        coordination: ChangeCoordination,
    ) -> tuple[RecoveryIntent, RecoveryReceipt]:
        """Require a completed, host-verified A recovery before raw custody."""
        if (
            coordination.recovery_owner_id is not None
            or coordination.writer is not None
            or coordination.publication_lease is not None
            or (coordination.continuation_action is not None and coordination.continuation_action.finished_at is None)
        ):
            raise DeliveryWorkerExclusionRequiredError
        try:
            intent = RecoveryIntent.model_validate_json(
                read_record(self.runtime_root, journal_path(change_id, recovery_id, "intent"))
            )
            receipt = RecoveryReceipt.model_validate_json(
                read_record(self.runtime_root, journal_path(change_id, recovery_id, "receipt"))
            )
            recorded_evidence = RecoveryEvidence.model_validate_json(
                read_record(self.runtime_root, journal_path(change_id, recovery_id, "evidence"))
            )
        except (OSError, TypeError, ValueError) as exc:
            raise DeliveryWorkerExclusionRequiredError from exc
        if (
            intent.recovery_id != recovery_id
            or intent.invocation.request.change_id != change_id
            or receipt.recovery_id != recovery_id
            or receipt.evidence.recovery_id != recovery_id
            or receipt.evidence.status not in {"closed", "excluded"}
            or receipt.evidence != recorded_evidence
            or recorded_evidence.invocation != intent.invocation
            or not intent.maintained_surfaces
            or not intent.last_write_provenance
        ):
            raise DeliveryWorkerExclusionRequiredError
        verified = (
            receipt.evidence.status == "excluded"
            and recovery_id in coordination.recovery_exclusions
            and self._coordinator.recovery_exclusions_verified(coordination)
        ) or (receipt.evidence.status == "closed" and self._coordinator.recovery_verification_recorded(recovery_id))
        if not verified:
            raise DeliveryWorkerExclusionRequiredError
        request = intent.invocation.request
        try:
            worktree = self._canonical_worktree_path(change_id, coordination.worktree_path)
            request_worktree = Path(request.worktree).resolve()
            request_repository = Path(request.repository).resolve()
            request_runtime = Path(request.runtime_root).resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeliveryWorkerExclusionRequiredError from exc
        if (
            request.branch != coordination.branch
            or request_worktree != worktree
            or request_repository != self._repository
            or request_runtime != self.runtime_root
            or request.integration_target != coordination.integration_target
            or request.target_head != self.observed_target_head()
            or intent.exact_head != self._resolve(coordination.branch)
        ):
            msg = "verified recovery authority no longer matches the managed workspace"
            raise PreservationFenceError(msg)
        return intent, receipt

    def _classify_preservation(  # noqa: PLR0913 - preserve each exact evidence input at the gate.
        self,
        *,
        change_id: str,
        intent: RecoveryIntent,
        recovery_id: str,
        worktree_path: Path,
        current_metadata: tuple[tuple[str, str, int | None], ...],
        exact_head: str,
        index_digest: str,
        index_entries: tuple[tuple[str, int, int, str], ...],
        head_entries: tuple[tuple[str, int, str], ...],
        paths: tuple[str, ...],
    ) -> PreservationProvenanceEvidence:
        """Ask the configured owner for exact producer classifications before copying bytes."""
        try:
            evidence = self._preservation_provenance_provider.classify(
                change_id=change_id,
                intent=intent,
                recovery_id=recovery_id,
                worktree_path=worktree_path,
                current_metadata=current_metadata,
                exact_head=exact_head,
                index_digest=index_digest,
                index_entries=index_entries,
                head_entries=head_entries,
                paths=paths,
            )
            if evidence is not None and not isinstance(evidence, PreservationProvenanceEvidence):
                evidence = PreservationProvenanceEvidence.model_validate(evidence)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise PreservationRejectedError("trusted path provenance is unavailable") from exc  # noqa: EM101, TRY003
        if evidence is None:
            raise PreservationRejectedError("trusted path provenance is unavailable")  # noqa: EM101, TRY003
        self._validate_preservation_provenance(
            intent,
            evidence=evidence,
            change_id=change_id,
            recovery_id=recovery_id,
            worktree_path=worktree_path,
            exact_head=exact_head,
            index_digest=index_digest,
            paths=paths,
        )
        return evidence

    @staticmethod
    def _validate_preservation_provenance(  # noqa: PLR0913 - validation binds each exact owner boundary.
        intent: RecoveryIntent,
        *,
        evidence: PreservationProvenanceEvidence | None,
        change_id: str,
        recovery_id: str,
        worktree_path: Path,
        exact_head: str,
        index_digest: str,
        paths: tuple[str, ...],
    ) -> None:
        """Require exact producer evidence; task scope and hashes are not substitutes."""
        if (
            evidence is None
            or evidence.change_id != change_id
            or evidence.recovery_id != recovery_id
            or evidence.worktree_path != worktree_path
            or evidence.workspace_fingerprint != intent.workspace_fingerprint
            or evidence.exact_head != exact_head
            or evidence.index_digest != index_digest
            or tuple(item.path for item in evidence.paths) != paths
            or (paths and (intent.admitted_task_id is None or intent.admitted_task_digest is None))
            or (
                paths
                and (evidence.task_id != intent.admitted_task_id or evidence.task_digest != intent.admitted_task_digest)
            )
            or any(item.disposition not in {"useful", "disposable"} for item in evidence.paths)
            or any(not item.producer_id for item in evidence.paths)
        ):
            raise PreservationRejectedError(  # noqa: TRY003
                "path provenance is foreign, ambiguous, private, or stale"  # noqa: EM101
            )

    def _reverify_preservation_provenance(  # noqa: PLR0913 - reverify the complete persisted owner boundary.
        self,
        *,
        change_id: str,
        intent: RecoveryIntent,
        evidence: PreservationProvenanceEvidence,
        recovery_id: str,
        worktree_path: Path,
        current_metadata: tuple[tuple[str, str, int | None], ...],
        exact_head: str,
        index_digest: str,
        index_entries: tuple[tuple[str, int, int, str], ...],
        head_entries: tuple[tuple[str, int, str], ...],
        paths: tuple[str, ...],
    ) -> None:
        """Reverify immutable producer evidence instead of trusting private manifest bytes alone."""
        try:
            verified = self._preservation_provenance_provider.verify(
                change_id=change_id,
                intent=intent,
                evidence=evidence,
                recovery_id=recovery_id,
                worktree_path=worktree_path,
                current_metadata=current_metadata,
                exact_head=exact_head,
                index_digest=index_digest,
                index_entries=index_entries,
                head_entries=head_entries,
                paths=paths,
            )
            if verified is not None and not isinstance(verified, PreservationProvenanceEvidence):
                verified = PreservationProvenanceEvidence.model_validate(verified)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise PreservationRejectedError(  # noqa: TRY003
                "trusted path provenance could not be reverified"  # noqa: EM101
            ) from exc
        if verified is None or verified != evidence:
            raise PreservationRejectedError(  # noqa: TRY003
                "trusted path provenance could not be reverified"  # noqa: EM101
            )
        self._validate_preservation_provenance(
            intent,
            evidence=verified,
            change_id=change_id,
            recovery_id=recovery_id,
            worktree_path=worktree_path,
            exact_head=exact_head,
            index_digest=index_digest,
            paths=paths,
        )

    @staticmethod
    def _require_admitted_paths(intent: RecoveryIntent, paths: tuple[str, ...]) -> None:
        """Reject dirty paths outside the persisted active-task admission before raw reads."""
        if not set(paths) <= set(intent.admitted_paths):
            if intent.admitted_task_id is None:
                msg = "dirty paths require an admitted Builder task"
                raise PreservationRejectedError(msg)
            msg = "dirty paths fall outside the admitted task path authority"
            raise PreservationRejectedError(msg)

    @staticmethod
    def _directory_identity(path: Path, label: str) -> tuple[int, int, int, int]:
        """Pin one owner directory without following a substituted ancestor."""
        try:
            _reject_symlink_ancestors(path)
            metadata = path.lstat()
        except (FileNotFoundError, OSError) as exc:
            msg = f"{label} is unavailable"
            raise PreservationRejectedError(msg) from exc
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_nlink < 1:
            msg = f"{label} is not a directory"
            raise PreservationRejectedError(msg)
        return (
            metadata.st_dev,
            metadata.st_ino,
            stat.S_IMODE(metadata.st_mode),
            metadata.st_nlink,
        )

    def _read_frontier_bytes(self, change_id: str) -> bytes:
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            content = read_contained(
                root_fd,
                Path("changes") / change_id / "frontier.json",
                limit=65_536,
            )
        finally:
            os.close(root_fd)
        if content is None:
            msg = "Delivery frontier is missing"
            raise PreservationRejectedError(msg)
        return content

    def _verify_preservation_fences(
        self,
        change_id: str,
        receipt: WorktreePreservationReceipt,
        index_metadata: tuple[int, int, int, int],
        *,
        selected_paths: tuple[str, ...] = (),
        allow_legacy_provenance: bool = False,
    ) -> tuple[Path, _ManagedIndexIdentity]:
        """Revalidate every durable identity before a read or exact-path effect."""
        coordination = self._coordinator.show(change_id)
        intent, _recovery = self._require_preservation_authority(change_id, receipt.recovery_id, coordination)
        recorded_paths = tuple(entry.path for entry in receipt.paths)
        checked_paths = tuple(sorted(set(recorded_paths) | set(selected_paths)))
        if checked_paths:
            if intent.admitted_task_id is None:
                msg = "preservation receipt lacks admitted Builder task authority"
                raise PreservationRejectedError(msg)
            self._require_admitted_paths(intent, checked_paths)
        worktree = self._canonical_worktree_path(change_id, coordination.worktree_path)
        if (
            receipt.change_id != change_id
            or receipt.branch != coordination.branch
            or receipt.worktree_path != worktree
            or receipt.reviewed_head != coordination.last_reviewed_commit
            or receipt.integration_target != coordination.integration_target
            or receipt.repository != self._repository
            or receipt.runtime_root != self.runtime_root
            or receipt.maintained_surfaces != intent.maintained_surfaces
            or receipt.last_write_provenance != intent.last_write_provenance
        ):
            msg = "preservation authority no longer matches its registered roots"
            raise PreservationFenceError(msg)
        if receipt.provenance is not None or not allow_legacy_provenance:
            provenance = receipt.provenance
            self._validate_preservation_provenance(
                intent,
                evidence=provenance,
                change_id=change_id,
                recovery_id=receipt.recovery_id,
                worktree_path=worktree,
                exact_head=receipt.branch_head,
                index_digest=receipt.index_digest,
                paths=recorded_paths,
            )
        branch_head = self._resolve(coordination.branch)
        if branch_head != receipt.branch_head or branch_head != intent.exact_head:
            msg = "Change branch head changed since preservation"
            raise PreservationFenceError(msg)
        if self.observed_target_head() != receipt.target_head or receipt.target_head != intent.target_head:
            msg = "integration target changed since preservation"
            raise PreservationFenceError(msg)
        frontier = self._read_frontier_bytes(change_id)
        if digest(frontier) != receipt.frontier_digest:
            msg = "Delivery frontier changed since preservation"
            raise PreservationFenceError(msg)
        if self._coordinator.recovery_authority_digest(change_id) != receipt.coordination_digest:
            msg = "Change coordination changed since preservation"
            raise PreservationFenceError(msg)
        index = self._verify_preservation_roots(change_id, receipt, worktree)
        index_bytes = self._verify_index_metadata(index, receipt.index_digest, index_metadata)
        # A process can die after replacing the worktree path but before unlinking
        # its owner-private staging source.  Authenticate and clean that exact
        # co-link before the strict provenance metadata read below.
        self._verify_preservation_inventory(worktree, receipt)
        if receipt.provenance is not None:
            index_records = self._index_entry_records(worktree)
            entries = tuple((path, mode, stage) for path, mode, stage, _object_id in index_records)
            self._validate_index_entries(entries)
            head_entries = self._head_entries(worktree, branch_head)
            index_path_names = self._validate_index_extensions(
                index_bytes,
                expected_entries=index_records,
                head_entries=head_entries,
            )
            self._reverify_preservation_provenance(
                change_id=change_id,
                intent=intent,
                evidence=receipt.provenance,
                recovery_id=receipt.recovery_id,
                worktree_path=worktree,
                current_metadata=tuple(
                    (path, *self._read_worktree_metadata(worktree, path)) for path in recorded_paths
                ),
                exact_head=branch_head,
                index_digest=receipt.index_digest,
                index_entries=index_records,
                head_entries=head_entries,
                paths=recorded_paths,
            )
            self._validate_index_path_names(index_path_names)
            self._verify_index_metadata(index, receipt.index_digest, index_metadata)
        self._verify_preservation_inventory(worktree, receipt)
        return worktree, index

    def _verify_preservation_roots(
        self,
        change_id: str,
        receipt: WorktreePreservationReceipt,
        worktree: Path,
    ) -> _ManagedIndexIdentity:
        self._require_worktree(change_id, worktree, receipt.branch, receipt.branch_head)
        worktree_identity = self._directory_identity(worktree, "registered worktree")
        repository_identity = self._directory_identity(self._repository, "managed repository")
        runtime_identity = self._directory_identity(self.runtime_root, "runtime root")
        if (
            worktree_identity[:3]
            != (
                receipt.worktree_device,
                receipt.worktree_inode,
                receipt.worktree_mode,
            )
            or repository_identity[:2] != (receipt.repository_device, receipt.repository_inode)
            or runtime_identity[:2] != (receipt.runtime_device, receipt.runtime_inode)
        ):
            msg = "preservation root descriptor changed"
            raise PreservationFenceError(msg)
        index = self._resolve_managed_index(worktree)
        common_identity = self._directory_identity(index.common_directory, "Git common directory")
        administration_identity = self._directory_identity(index.administration, "Git administration directory")
        if (
            index.path != receipt.index_path
            or index.administration != receipt.administration
            or index.common_directory != receipt.common_directory
            or common_identity[:2] != (receipt.common_device, receipt.common_inode)
            or administration_identity[:2] != (receipt.administration_device, receipt.administration_inode)
        ):
            msg = "Git common directory identity changed"
            raise PreservationFenceError(msg)
        return index

    def _verify_preservation_inventory(self, worktree: Path, receipt: WorktreePreservationReceipt) -> None:
        status = self._preservation_git(
            "status", "--porcelain=v1", "-z", "--ignored=matching", "--untracked-files=all", cwd=worktree
        ).stdout
        known_paths = {entry.path for entry in receipt.paths}
        authorized_staging = self._authorized_restoration_staging(receipt, worktree)
        if not set(self._preservation_status_paths(status)) <= known_paths | authorized_staging:
            msg = "worktree path inventory expanded after preservation"
            raise PreservationFenceError(msg)

    def _authorized_restoration_staging(  # noqa: C901, PLR0912, PLR0915 - validate every durable staging fence.
        self,
        receipt: WorktreePreservationReceipt,
        worktree: Path,
    ) -> set[str]:
        """Return only operation-owned staging paths that are durably journaled and byte-exact."""
        relative = Path(receipt.storage_ref) / "restoration"
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        authorized: set[str] = set()
        entries_by_path = {entry.path: entry for entry in receipt.paths}
        try:
            try:
                with contained_directory(root_fd, relative) as restoration_fd:
                    with os.scandir(restoration_fd) as operations:
                        operation_entries = tuple(operations)
                    if any(not item.is_dir(follow_symlinks=False) for item in operation_entries):
                        msg = "restoration journal operation inventory is malformed"
                        raise PreservationFenceError(msg)
                    operation_names = tuple(sorted(item.name for item in operation_entries))
                    if len(operation_names) > _MAX_PRESERVED_PATHS:
                        msg = "restoration journal exceeds its bounded operation inventory"
                        raise PreservationFenceError(msg)
                    for operation_id in operation_names:
                        if not _DIGEST_PATTERN.fullmatch(operation_id):
                            msg = "restoration journal operation identity is malformed"
                            raise PreservationFenceError(msg)
                        intent_bytes = read_contained(
                            restoration_fd,
                            Path(operation_id) / "intent.json",
                            limit=_MAX_PRESERVED_TOTAL_BYTES,
                        )
                        if intent_bytes is None:
                            with (
                                contained_directory(restoration_fd, Path(operation_id)) as operation_fd,
                                os.scandir(operation_fd) as incomplete_entries,
                            ):
                                incomplete_size = 0
                                for incomplete_count, entry in enumerate(incomplete_entries, start=1):
                                    if incomplete_count > _MAX_RESTORATION_INCOMPLETE_ARTIFACTS:
                                        message = "restoration operation intent is missing with artifacts"
                                        raise PreservationFenceError(message)
                                    try:
                                        metadata = entry.stat(follow_symlinks=False)
                                    except OSError as exc:
                                        message = "restoration operation intent is missing with artifacts"
                                        raise PreservationFenceError(message) from exc
                                    if (
                                        _RESTORATION_RECORD_TEMPORARY_PATTERN.fullmatch(entry.name) is None
                                        or not stat.S_ISREG(metadata.st_mode)
                                        or metadata.st_nlink != 1
                                        or stat.S_IMODE(metadata.st_mode) != _RESTORATION_RECORD_TEMPORARY_MODE
                                        or metadata.st_size < 0
                                        or metadata.st_size > _MAX_PRESERVED_TOTAL_BYTES
                                    ):
                                        message = "restoration operation intent is missing with artifacts"
                                        raise PreservationFenceError(message)
                                    incomplete_size += metadata.st_size
                                    if incomplete_size > _MAX_PRESERVED_TOTAL_BYTES:
                                        message = "restoration operation intent is missing with artifacts"
                                        raise PreservationFenceError(message)
                            for path in entries_by_path:
                                staging_path = str(
                                    PurePosixPath(path).parent / _preservation_temporary_name(operation_id, path)
                                )
                                self._validate_preservation_path(worktree, staging_path)
                                try:
                                    (worktree / PurePosixPath(staging_path)).lstat()
                                except FileNotFoundError:
                                    continue
                                message = "restoration operation intent is missing with worktree exposure"
                                raise PreservationFenceError(message)
                            continue
                        try:
                            operation_payload = json.loads(intent_bytes)
                        except json.JSONDecodeError as exc:
                            msg = "restoration operation intent is malformed"
                            raise PreservationFenceError(msg) from exc
                        if not isinstance(operation_payload, dict) or operation_payload.get("schema_version") != 1:
                            msg = "restoration operation intent is malformed"
                            raise PreservationFenceError(msg)
                        if set(operation_payload) != {"schema_version", "preservation_receipt_id", "paths"}:
                            msg = "restoration operation intent is malformed"
                            raise PreservationFenceError(msg)
                        if operation_payload["preservation_receipt_id"] != receipt.receipt_id:
                            msg = "restoration operation authority does not match its receipt"
                            raise PreservationFenceError(msg)
                        selected_raw = operation_payload["paths"]
                        if (
                            not isinstance(selected_raw, list)
                            or any(not isinstance(path, str) for path in selected_raw)
                            or selected_raw != sorted(set(selected_raw))
                            or not set(selected_raw) <= entries_by_path.keys()
                        ):
                            msg = "restoration operation paths are malformed"
                            raise PreservationFenceError(msg)
                        operation_record = {
                            "preservation_receipt_id": receipt.receipt_id,
                            "paths": selected_raw,
                        }
                        expected_operation_id = digest(
                            json.dumps(operation_record, sort_keys=True, separators=(",", ":")).encode()
                        )
                        if operation_id != expected_operation_id:
                            msg = "restoration operation identity is invalid"
                            raise PreservationFenceError(msg)
                        for path in selected_raw:
                            entry_bytes = read_contained(
                                restoration_fd,
                                Path(operation_id) / "paths" / digest(path.encode()) / "intent.json",
                                limit=_MAX_PRESERVED_TOTAL_BYTES,
                            )
                            if entry_bytes is None:
                                staging_path = str(
                                    PurePosixPath(path).parent / _preservation_temporary_name(operation_id, path)
                                )
                                self._validate_preservation_path(worktree, staging_path)
                                try:
                                    (worktree / PurePosixPath(staging_path)).lstat()
                                except FileNotFoundError:
                                    continue
                                msg = "restoration path intent is missing"
                                raise PreservationFenceError(msg)
                            try:
                                entry_payload = json.loads(entry_bytes)
                            except json.JSONDecodeError as exc:
                                msg = "restoration path intent is malformed"
                                raise PreservationFenceError(msg) from exc
                            if not isinstance(entry_payload, dict) or entry_payload.get("schema_version") != 1:
                                msg = "restoration path intent is malformed"
                                raise PreservationFenceError(msg)
                            entry_payload = {
                                key: value for key, value in entry_payload.items() if key != "schema_version"
                            }
                            try:
                                recorded_entry = PreservationEntry.model_validate(entry_payload)
                            except (TypeError, ValueError) as exc:
                                msg = "restoration path intent is malformed"
                                raise PreservationFenceError(msg) from exc
                            if recorded_entry != entries_by_path[path]:
                                msg = "restoration path intent does not match its receipt"
                                raise PreservationFenceError(msg)
                            staging_record = read_contained(
                                restoration_fd,
                                Path(operation_id) / "paths" / digest(path.encode()) / "staging.json",
                                limit=_MAX_PRESERVED_TOTAL_BYTES,
                            )
                            if staging_record is not None:
                                try:
                                    staging_payload = json.loads(staging_record)
                                except json.JSONDecodeError as exc:
                                    msg = "restoration staging identity is malformed"
                                    raise PreservationFenceError(msg) from exc
                                if (
                                    not isinstance(staging_payload, dict)
                                    or set(staging_payload)
                                    != {
                                        "schema_version",
                                        "preservation_receipt_id",
                                        "operation_id",
                                        "path",
                                        "source",
                                        "identity",
                                    }
                                    or staging_payload.get("schema_version") != 1
                                    or staging_payload.get("preservation_receipt_id") != receipt.receipt_id
                                    or staging_payload.get("operation_id") != operation_id
                                    or staging_payload.get("path") != path
                                ):
                                    msg = "restoration staging identity is invalid"
                                    raise PreservationFenceError(msg)
                                source = staging_payload.get("source")
                                if not isinstance(source, str) or not _RESTORATION_STAGE_PATTERN.fullmatch(source):
                                    msg = "restoration staging source is malformed"
                                    raise PreservationFenceError(msg)
                                identity = staging_payload.get("identity")
                                if (
                                    not isinstance(identity, list)
                                    or len(identity) != _PRESERVATION_FILE_IDENTITY_FIELDS
                                    or any(type(value) is not int or value < 0 for value in identity)
                                ):
                                    msg = "restoration staging identity is malformed"
                                    raise PreservationFenceError(msg)
                                source_relative = (
                                    Path(receipt.storage_ref)
                                    / "restoration"
                                    / operation_id
                                    / "paths"
                                    / digest(path.encode())
                                    / source
                                )
                            else:
                                source = None
                                identity = None
                                source_relative = None
                            if recorded_entry.after_kind == "absent":
                                if staging_record is not None:
                                    msg = "unexpected restoration staging for absent path"
                                    raise PreservationFenceError(msg)
                                continue
                            try:
                                desired_state = self._state_from_entry(
                                    recorded_entry,
                                    before=False,
                                    receipt=receipt,
                                )
                                expected_state = self._state_from_entry(
                                    recorded_entry,
                                    before=True,
                                    receipt=receipt,
                                )
                                source_state = (
                                    self._read_private_staging_state(root_fd, source_relative)
                                    if source_relative is not None
                                    else None
                                )
                            except (OSError, PreservationRejectedError, PreservationFenceError, ValueError) as exc:
                                message = "owned restoration staging type or bytes are invalid"
                                raise PreservationFenceError(message) from exc
                            if source_state is not None:
                                if (
                                    identity is None
                                    or source_state.identity is None
                                    or not _same_staging_identity(tuple(identity), source_state.identity)
                                ):
                                    msg = "restoration staging owner identity changed"
                                    raise PreservationFenceError(msg)
                                if not self._same_state(source_state, desired_state):
                                    msg = "owned restoration staging bytes or type changed"
                                    raise PreservationFenceError(msg)
                            staging_path = str(
                                PurePosixPath(path).parent / _preservation_temporary_name(operation_id, path)
                            )
                            self._validate_preservation_path(worktree, staging_path)
                            try:
                                (worktree / PurePosixPath(staging_path)).lstat()
                            except FileNotFoundError as exc:
                                if identity is not None:
                                    try:
                                        if source_state is None:
                                            target_state = self._read_worktree_state(worktree, path)
                                        else:
                                            target_state = self._read_worktree_state(
                                                worktree,
                                                path,
                                                expected_staging_identity=tuple(identity),
                                            )
                                    except (
                                        OSError,
                                        PreservationRejectedError,
                                        PreservationFenceError,
                                        ValueError,
                                    ) as exc:
                                        message = "restoration staging target identity is invalid"
                                        raise PreservationFenceError(message) from exc
                                    if source_state is not None and self._same_state(target_state, desired_state):
                                        if target_state.identity is None or not _same_staging_identity(
                                            tuple(identity), target_state.identity
                                        ):
                                            message = "restoration staging owner identity changed"
                                            raise PreservationFenceError(message) from None
                                        self._remove_private_staging(
                                            receipt,
                                            operation_id,
                                            path,
                                            source,
                                            tuple(identity),
                                        )
                                    elif not self._same_state(target_state, expected_state) and not self._same_state(
                                        target_state, desired_state
                                    ):
                                        msg = "restoration staging identity has no artifact"
                                        raise PreservationFenceError(msg) from exc
                                continue
                            if identity is None:
                                msg = "restoration staging identity is missing"
                                raise PreservationFenceError(msg)
                            try:
                                staging_state = self._read_worktree_state(
                                    worktree,
                                    staging_path,
                                    expected_staging_identity=tuple(identity),
                                )
                            except (OSError, PreservationRejectedError, PreservationFenceError, ValueError) as exc:
                                message = "owned restoration staging type or bytes are invalid"
                                raise PreservationFenceError(message) from exc
                            if staging_state.identity is None or not _same_staging_identity(
                                tuple(identity), staging_state.identity
                            ):
                                msg = "restoration staging owner identity changed"
                                raise PreservationFenceError(msg)
                            if not self._same_state(staging_state, desired_state):
                                msg = "owned restoration staging bytes or type changed"
                                raise PreservationFenceError(msg)
                            authorized.add(staging_path)
            except FileNotFoundError:
                return authorized
        finally:
            os.close(root_fd)
        return authorized

    @staticmethod
    def _require_preservation_environment() -> None:
        inherited = tuple(name for name in _PRESERVATION_ENV_OVERRIDES if name in os.environ)
        if inherited:
            msg = "inherited Git repository/index overrides are not accepted"
            raise PreservationRejectedError(msg)

    @staticmethod
    def _preservation_object_name(content: bytes | None) -> str:
        return "0" * 64 if content is None else hashlib.sha256(content).hexdigest()

    def _write_preservation_store(
        self,
        receipt: WorktreePreservationReceipt,
        objects: dict[str, bytes],
        *,
        index: _ManagedIndexIdentity,
    ) -> None:
        relative = Path("changes") / receipt.change_id / "recovery-receipts" / receipt.recovery_id / "preservation"
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative, create=True) as preservation_fd:
                os.fchmod(preservation_fd, 0o700)
                for object_name, content in objects.items():
                    object_path = Path("objects") / f"{object_name}.raw"
                    write_contained(
                        preservation_fd,
                        object_path,
                        content,
                        limits=ContainedWriteLimits(
                            max_content_bytes=_MAX_PRESERVED_FILE_BYTES,
                            max_temporary_bytes=_MAX_PRESERVED_TOTAL_BYTES,
                        ),
                    )
                manifest = {
                    "schema_version": 1,
                    "receipt": receipt.model_dump(mode="json"),
                    "index_mode": index.mode,
                    "index_device": index.device,
                    "index_inode": index.inode,
                    "index_links": index.link_count,
                    "objects": tuple(sorted(objects)),
                }
                write_contained(
                    preservation_fd,
                    Path("manifest.json"),
                    (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(),
                )
        finally:
            os.close(root_fd)

    def _verify_preservation_store(
        self,
        receipt: WorktreePreservationReceipt,
        objects: dict[str, bytes],
        *,
        allow_legacy_index_extensions: bool = False,
    ) -> None:
        loaded, _metadata, inventory = self._read_preservation_manifest(receipt.change_id, receipt.preservation_id)
        if loaded != receipt:
            msg = "private preservation manifest does not match its receipt"
            raise PreservationFenceError(msg)
        if tuple(sorted(objects)) != inventory:
            msg = "private preservation object inventory changed"
            raise PreservationFenceError(msg)
        self._validate_private_paths(tuple(entry.path for entry in receipt.paths))
        for object_name, content in objects.items():
            if object_name == receipt.index_digest:
                if allow_legacy_index_extensions and receipt.provenance is None:
                    self._validate_legacy_index_extensions(content)
                else:
                    self._validate_index_extensions(content)
            else:
                self._validate_private_content(content)
            stored = self._read_private_preservation_object(receipt, object_name)
            if stored != content or hashlib.sha256(stored).hexdigest() != object_name:
                msg = "private preservation object failed verification"
                raise PreservationFenceError(msg)

    def _preservation_storage_relative(self, change_id: str, preservation_id: str) -> Path:
        """Find one private preservation by its receipt identity without following links."""
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        base = Path("changes") / change_id / "recovery-receipts"
        try:
            with contained_directory(root_fd, base) as receipts_fd:
                with os.scandir(receipts_fd) as scanner:
                    entries = tuple(sorted(scanner, key=lambda item: item.name))
                if len(entries) > _MAX_PRESERVED_PATHS:
                    msg = "private preservation inventory exceeds its bound"
                    raise PreservationRejectedError(msg)
                for entry in entries:
                    if not _DIGEST_PATTERN.fullmatch(entry.name) or not entry.is_dir(follow_symlinks=False):
                        msg = "private preservation inventory is malformed"
                        raise PreservationRejectedError(msg)
                    relative = base / entry.name / "preservation"
                    try:
                        with contained_directory(root_fd, relative) as preservation_fd:
                            content = read_contained(
                                preservation_fd,
                                Path("manifest.json"),
                                limit=_MAX_PRESERVED_TOTAL_BYTES,
                            )
                    except FileNotFoundError:
                        continue
                    if content is None:
                        continue
                    try:
                        receipt = _preservation_receipt_from_payload(json.loads(content))
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        msg = "private preservation manifest is malformed"
                        raise PreservationRejectedError(msg) from exc
                    if receipt.change_id == change_id and receipt.preservation_id == preservation_id:
                        return relative
        except FileNotFoundError as exc:
            msg = "private preservation inventory is missing"
            raise PreservationRejectedError(msg) from exc
        finally:
            os.close(root_fd)
        msg = "private preservation receipt is absent"
        raise PreservationRejectedError(msg)

    def _read_preservation_manifest(
        self,
        change_id: str,
        preservation_id: str,
    ) -> tuple[WorktreePreservationReceipt, tuple[int, int, int, int], tuple[str, ...]]:
        self._require_preservation_identity(preservation_id)
        relative = self._preservation_storage_relative(change_id, preservation_id)
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative) as preservation_fd:
                content = read_contained(preservation_fd, Path("manifest.json"), limit=_MAX_PRESERVED_TOTAL_BYTES)
                if content is None:
                    msg = "private preservation manifest is missing"
                    raise PreservationRejectedError(msg)
                try:
                    payload = _preservation_manifest_payload(content)
                    receipt = _preservation_receipt_from_payload(payload)
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    msg = "private preservation manifest is malformed"
                    raise PreservationRejectedError(msg) from exc
                try:
                    metadata = tuple(
                        int(payload.get(key)) for key in ("index_mode", "index_device", "index_inode", "index_links")
                    )
                except (TypeError, ValueError) as exc:
                    msg = "private preservation index metadata is malformed"
                    raise PreservationRejectedError(msg) from exc
                if (
                    len(metadata) != _PRESERVATION_INDEX_METADATA_FIELDS
                    or metadata[0] < 0
                    or metadata[0] > _FILE_PERMISSION_MASK
                    or metadata[1] < 0
                    or metadata[2] < 0
                    or metadata[3] < 1
                ):
                    msg = "private preservation index metadata is malformed"
                    raise PreservationRejectedError(msg)
                objects = payload.get("objects")
                if (
                    not isinstance(objects, list)
                    or len(objects) > (_MAX_PRESERVED_PATHS * 2) + 1
                    or any(not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item) for item in objects)
                    or objects != sorted(set(objects))
                ):
                    msg = "private preservation object inventory is malformed"
                    raise PreservationRejectedError(msg)
                if receipt.index_digest not in objects:
                    msg = "private preservation index object is missing"
                    raise PreservationRejectedError(msg)
                expected_objects = {
                    receipt.index_digest,
                    *(
                        object_name
                        for entry in receipt.paths
                        for object_name in (entry.before_object, entry.after_object)
                        if object_name is not None
                    ),
                }
                if tuple(objects) != tuple(sorted(expected_objects)):
                    msg = "private preservation object inventory does not match its manifest"
                    raise PreservationRejectedError(msg)
                return receipt, metadata, tuple(objects)
        finally:
            os.close(root_fd)

    def _read_private_preservation_object(self, receipt: WorktreePreservationReceipt, object_name: str) -> bytes:
        relative = Path("changes") / receipt.change_id / "recovery-receipts" / receipt.recovery_id / "preservation"
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative) as preservation_fd:
                content = read_contained(
                    preservation_fd,
                    Path("objects") / f"{object_name}.raw",
                    limit=_MAX_PRESERVED_FILE_BYTES,
                )
                if content is None:
                    msg = "private preservation object is missing"
                    raise PreservationRejectedError(msg)
                return content
        finally:
            os.close(root_fd)

    def _state_from_entry(
        self,
        entry: PreservationEntry,
        *,
        before: bool,
        receipt: WorktreePreservationReceipt,
    ) -> _PreservedPathState:
        kind = entry.before_kind if before else entry.after_kind
        object_name = entry.before_object if before else entry.after_object
        mode = entry.before_mode if before else entry.after_mode
        identity = entry.before_identity if before else None
        if kind == "absent":
            return _PreservedPathState("absent", None, None)
        if object_name is None or mode is None:
            msg = "private preservation entry is incomplete"
            raise PreservationRejectedError(msg)
        content = self._read_private_preservation_object(receipt, object_name)
        expected = entry.before_digest if before else entry.after_digest
        if expected is None or hashlib.sha256(content).hexdigest() != expected:
            msg = "private preservation object digest changed"
            raise PreservationFenceError(msg)
        return _PreservedPathState(kind, content, mode, identity)
