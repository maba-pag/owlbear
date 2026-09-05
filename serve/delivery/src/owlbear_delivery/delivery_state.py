"""Remote-backed sparse snapshots for resumable Delivery authority."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from owlbear_delivery.acceptance import CompletionReceiptBundle
from owlbear_delivery.delivery_admission import DeliveryAdmissionReceipt
from owlbear_delivery.delivery_runtime import DeliveryFrontier
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.identities import ChangeId, Digest
from owlbear_delivery.target_contract import DeliveryContract

if TYPE_CHECKING:
    from owlbear_delivery.change_workspace import ChangeCoordination
    from owlbear_delivery.delivery_runtime import DeliveryRuntime

_CHANGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+:-]*$")
_STATE_ROOT = ".owlbear/delivery/state"
_REMOTE_REF_MISSING = 2


class DeliveryStatePublicationError(RuntimeError):
    """A remote Delivery-state snapshot could not be published safely."""

    code = "ERR_DELIVERY_STATE_PUBLICATION"

    def __init__(self, detail: str, *, retry_safe: bool) -> None:
        super().__init__(detail)
        self.retry_safe = retry_safe


class DeliveryStateConflictError(DeliveryStatePublicationError):
    """The expected remote Delivery-state branch no longer matches."""

    code = "ERR_DELIVERY_STATE_CONFLICT"


class DeliveryStateResponseUnknownError(DeliveryStatePublicationError):
    """A state push completed without verifiable remote confirmation."""

    code = "ERR_DELIVERY_STATE_RESPONSE_UNKNOWN"


class _StateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryStateSnapshot(_StateModel):
    """Sanitized resumable state for one Change at one semantic checkpoint."""

    schema_version: Literal[1] = 1
    snapshot_id: Digest = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    package_id: Digest
    authority_digest: Digest
    branch: str = Field(min_length=1)
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    publication_base_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    admission: DeliveryAdmissionReceipt
    contract: DeliveryContract
    frontier: DeliveryFrontier
    completion: CompletionReceiptBundle | None = None
    sequence: int = Field(gt=0)
    parent_snapshot_id: Digest | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    base_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    captured_at: datetime

    @classmethod
    def create(  # noqa: PLR0913 - snapshot identity requires each authority input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        package_id: str,
        coordination: ChangeCoordination,
        runtime: DeliveryRuntime,
        admission: DeliveryAdmissionReceipt,
        sequence: int,
        parent_snapshot_id: str | None,
        base_head: str | None,
        captured_at: datetime,
    ) -> DeliveryStateSnapshot:
        """Create one sanitized snapshot from current runtime and workspace authority."""
        frontier = _portable_frontier(runtime)
        completion = runtime.completion_bundle()
        if any(binding.active_claim is not None for binding in frontier.bindings):
            _raise_state_error("Delivery-state snapshots cannot contain an active Outcome claim", retry_safe=True)
        if frontier.integration_repair_claim is not None:
            _raise_state_error(
                "Delivery-state snapshots cannot contain an active Integration repair claim",
                retry_safe=True,
            )
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "package_id": package_id,
            "authority_digest": runtime.authority_digest,
            "branch": coordination.branch,
            "change_head": coordination.last_reviewed_commit,
            "integration_target": coordination.integration_target,
            "target_head": coordination.target_head,
            "publication_base_head": coordination.publication_base_head,
            "last_reviewed_commit": coordination.last_reviewed_commit,
            "admission": admission,
            "contract": runtime.contract,
            "frontier": frontier,
            "completion": completion,
            "sequence": sequence,
            "parent_snapshot_id": parent_snapshot_id,
            "base_head": base_head,
            "captured_at": captured_at,
        }
        candidate = cls.model_construct(snapshot_id="0" * 64, **values)
        return cls(snapshot_id=_snapshot_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryStateSnapshot:
        if self.snapshot_id != _snapshot_digest(self):
            message = "Delivery-state snapshot identity is invalid"
            raise ValueError(message)
        _validate_snapshot_metadata(self)
        _validate_snapshot_authority(self)
        _validate_snapshot_lifecycle(self)
        return self

    def canonical_bytes(self) -> bytes:
        """Return canonical bytes for Git publication."""
        return _canonical_bytes(self)


class DeliveryStateSnapshotDiagnostic(_StateModel):
    """Bounded read-side diagnostic for one remote snapshot that cannot be used."""

    change_id: str | None = Field(default=None, min_length=1)
    path: str = Field(min_length=1)
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1, max_length=240)


class DeliveryStateSnapshotInventory(_StateModel):
    """Valid remote snapshots and isolated diagnostics from one state-branch read."""

    remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    snapshots: tuple[DeliveryStateSnapshot, ...] = ()
    diagnostics: tuple[DeliveryStateSnapshotDiagnostic, ...] = ()


def _validate_snapshot_metadata(snapshot: DeliveryStateSnapshot) -> None:
    """Validate remote-safe branch and timestamp metadata."""
    if (
        _BRANCH_PATTERN.fullmatch(snapshot.branch) is None
        or _BRANCH_PATTERN.fullmatch(snapshot.integration_target) is None
    ):
        message = "Delivery-state snapshot branch identity is invalid"
        raise ValueError(message)
    if snapshot.captured_at.tzinfo is None:
        message = "Delivery-state snapshot timestamp must include a timezone"
        raise ValueError(message)
    if snapshot.change_head != snapshot.last_reviewed_commit:
        message = "Delivery-state snapshot Change head and reviewed boundary differ"
        raise ValueError(message)


def _validate_snapshot_authority(snapshot: DeliveryStateSnapshot) -> None:
    """Validate package, contract, admission, and frontier identity bindings."""
    if snapshot.contract.change_id != snapshot.change_id or snapshot.admission.change_id != snapshot.change_id:
        message = "Delivery-state snapshot authority does not match its Change"
        raise ValueError(message)
    if snapshot.admission.integration_target != snapshot.integration_target:
        message = "Delivery-state snapshot admission target does not match its Change"
        raise ValueError(message)
    if snapshot.admission.contract_digest != hashlib.sha256(_canonical_bytes(snapshot.contract)).hexdigest():
        message = "Delivery-state snapshot admission contract digest is invalid"
        raise ValueError(message)
    expected_bindings = tuple((scope.outcome_id, scope.scope_id) for scope in snapshot.contract.plan_scopes)
    actual_bindings = tuple((binding.outcome_id, binding.plan_scope_id) for binding in snapshot.frontier.bindings)
    if actual_bindings != expected_bindings:
        message = "Delivery-state snapshot frontier does not match its contract"
        raise ValueError(message)


def _validate_snapshot_lifecycle(snapshot: DeliveryStateSnapshot) -> None:
    """Reject live or transient lifecycle state from portable snapshots."""
    if any(
        binding.output is not None
        or binding.candidate is not None
        or binding.result_candidate is not None
        or binding.recovery_attention is not None
        for binding in snapshot.frontier.bindings
    ):
        _raise_state_error("Delivery-state snapshots cannot contain transient claim output", retry_safe=True)
    if snapshot.frontier.change_completion is None and snapshot.completion is not None:
        message = "Delivery-state completion evidence requires terminal frontier authority"
        raise ValueError(message)
    if snapshot.frontier.change_completion is not None and (
        snapshot.completion is None
        or snapshot.completion.receipt.change_id != snapshot.change_id
        or snapshot.completion.receipt.completion_id != snapshot.frontier.change_completion.completion_id
    ):
        message = "Delivery-state completion evidence does not match its frontier"
        raise ValueError(message)


class DeliveryStatePublicationReceipt(_StateModel):
    """Exact remote branch update for one Delivery-state snapshot."""

    schema_version: Literal[1] = 1
    publication_id: Digest = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    state_branch: str = Field(min_length=1)
    snapshot_id: Digest
    expected_remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def create(  # noqa: PLR0913 - publication identity requires each remote input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        state_branch: str,
        snapshot_id: str,
        expected_remote_head: str | None,
        published_head: str,
    ) -> DeliveryStatePublicationReceipt:
        """Create one deterministic publication receipt."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "state_branch": state_branch,
            "snapshot_id": snapshot_id,
            "expected_remote_head": expected_remote_head,
            "published_head": published_head,
        }
        candidate = cls.model_construct(publication_id="0" * 64, **values)
        return cls(publication_id=_publication_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryStatePublicationReceipt:
        if self.publication_id != _publication_digest(self):
            message = "Delivery-state publication identity is invalid"
            raise ValueError(message)
        return self


class DeliveryStatePublisher:
    """Publish sparse state snapshots without using a checkout index."""

    def __init__(self, repository: Path, *, remote: str, state_branch: str) -> None:
        self._repository = repository.resolve()
        self._remote = remote
        self._state_branch = state_branch
        self._git_executable = resolve_git_executable()
        self._validate_branch()

    @property
    def state_branch(self) -> str:
        """Return the configured remote state branch."""
        return self._state_branch

    def publish(  # noqa: PLR0913 - one publication binds all exact Change inputs.
        self,
        *,
        change_id: str,
        package_id: str,
        coordination: ChangeCoordination,
        runtime: DeliveryRuntime,
        admission: DeliveryAdmissionReceipt,
        operation_id: str,
        captured_at: datetime,
        expected_remote_head: str | None = None,
    ) -> DeliveryStatePublicationReceipt:
        """Publish or replay one exact sparse Change state snapshot."""
        _validate_change_id(change_id)
        remote_head = self._refresh_remote_head()
        current = self._read_snapshot(remote_head, change_id) if remote_head is not None else None
        if expected_remote_head != remote_head and expected_remote_head is not None:
            _raise_state_conflict("Delivery-state branch changed before snapshot publication")
        if current is not None and _same_snapshot_inputs(current, package_id, coordination, runtime, admission):
            return DeliveryStatePublicationReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                state_branch=self._state_branch,
                snapshot_id=current.snapshot_id,
                expected_remote_head=current.base_head,
                published_head=remote_head,
            )
        sequence = current.sequence + 1 if current is not None else 1
        snapshot = DeliveryStateSnapshot.create(
            operation_id=operation_id,
            change_id=change_id,
            package_id=package_id,
            coordination=coordination,
            runtime=runtime,
            admission=admission,
            sequence=sequence,
            parent_snapshot_id=current.snapshot_id if current is not None else None,
            base_head=remote_head,
            captured_at=captured_at,
        )
        commit = self._commit_snapshot(remote_head, snapshot)
        self._push_snapshot(commit, remote_head)
        return DeliveryStatePublicationReceipt.create(
            operation_id=operation_id,
            change_id=change_id,
            state_branch=self._state_branch,
            snapshot_id=snapshot.snapshot_id,
            expected_remote_head=remote_head,
            published_head=commit,
        )

    def read_snapshots(self) -> tuple[DeliveryStateSnapshot, ...]:
        """Fetch and read all remote snapshots in stable path order."""
        remote_head = self._refresh_remote_head()
        if remote_head is None:
            return ()
        paths = self._git("ls-tree", "-r", "--name-only", remote_head, "--", _STATE_ROOT).splitlines()
        snapshots = []
        for path in paths:
            if not path.endswith("/snapshot.json"):
                continue
            snapshots.append(DeliveryStateSnapshot.model_validate_json(self._git_blob(remote_head, path), strict=False))
        return tuple(sorted(snapshots, key=lambda item: item.change_id))

    def read_snapshot_inventory(self) -> DeliveryStateSnapshotInventory:
        """Fetch all remote snapshots while quarantining invalid per-Change records."""
        remote_head = self._refresh_remote_head()
        if remote_head is None:
            return DeliveryStateSnapshotInventory()
        paths = self._git("ls-tree", "-r", "--name-only", remote_head, "--", _STATE_ROOT).splitlines()
        snapshots = []
        diagnostics = []
        for path in paths:
            if not path.endswith("/snapshot.json"):
                continue
            change_id = _snapshot_path_change_id(path)
            if change_id is None:
                diagnostics.append(
                    DeliveryStateSnapshotDiagnostic(
                        path=path,
                        code="snapshot-path-invalid",
                        detail="Remote Delivery snapshot path is invalid and was quarantined.",
                    )
                )
                continue
            try:
                raw = self._git_blob(remote_head, path)
                snapshot = DeliveryStateSnapshot.model_validate_json(raw, strict=False)
            except (OSError, RuntimeError, subprocess.SubprocessError):
                diagnostics.append(
                    DeliveryStateSnapshotDiagnostic(
                        change_id=change_id,
                        path=path,
                        code="snapshot-unreadable",
                        detail="Remote Delivery snapshot could not be read and was quarantined.",
                    )
                )
                continue
            except (TypeError, ValueError, ValidationError) as exc:
                diagnostics.append(
                    DeliveryStateSnapshotDiagnostic(
                        change_id=change_id,
                        path=path,
                        code=_snapshot_validation_code(exc),
                        detail=_snapshot_validation_detail(exc),
                    )
                )
                continue
            if snapshot.change_id != change_id:
                diagnostics.append(
                    DeliveryStateSnapshotDiagnostic(
                        change_id=change_id,
                        path=path,
                        code="snapshot-path-identity-mismatch",
                        detail="Remote Delivery snapshot Change identity does not match its state path.",
                    )
                )
                continue
            snapshots.append(snapshot)
        return DeliveryStateSnapshotInventory(
            remote_head=remote_head,
            snapshots=tuple(sorted(snapshots, key=lambda item: item.change_id)),
            diagnostics=tuple(sorted(diagnostics, key=lambda item: item.path)),
        )

    def read_snapshot(self, change_id: str) -> DeliveryStateSnapshot | None:
        """Fetch and read one remote Change snapshot."""
        _validate_change_id(change_id)
        remote_head = self._refresh_remote_head()
        return None if remote_head is None else self._read_snapshot(remote_head, change_id)

    def _refresh_remote_head(self) -> str | None:
        before = self._remote_head()
        if before is None:
            return None
        fetched = self._run_git(
            "fetch",
            "--no-tags",
            "--no-write-fetch-head",
            "--refmap=",
            self._remote,
            f"refs/heads/{self._state_branch}",
            check=False,
        )
        if fetched.returncode != 0:
            _raise_state_error("remote Delivery-state branch could not be fetched", retry_safe=True)
        after = self._remote_head()
        if after != before:
            _raise_state_conflict("remote Delivery-state branch changed while it was fetched")
        return before

    def _remote_head(self) -> str | None:
        result = self._run_git(
            "ls-remote",
            "--exit-code",
            "--heads",
            self._remote,
            f"refs/heads/{self._state_branch}",
            check=False,
        )
        if result.returncode == _REMOTE_REF_MISSING:
            return None
        if result.returncode != 0:
            _raise_state_error("remote Delivery-state branch could not be observed", retry_safe=True)
        line = result.stdout.decode(errors="replace").strip().splitlines()
        if len(line) != 1 or not line[0].endswith(f"\trefs/heads/{self._state_branch}"):
            _raise_state_error("remote Delivery-state branch response is invalid", retry_safe=False)
        return line[0].split("\t", 1)[0]

    def _read_snapshot(self, commit: str, change_id: str) -> DeliveryStateSnapshot | None:
        raw = self._read_snapshot_bytes(commit, change_id)
        return None if raw is None else DeliveryStateSnapshot.model_validate_json(raw, strict=False)

    def _read_snapshot_bytes(self, commit: str, change_id: str) -> bytes | None:
        path = _snapshot_path(change_id)
        result = self._run_git("show", f"{commit}:{path}", check=False)
        return None if result.returncode != 0 else result.stdout

    def _commit_snapshot(self, base: str | None, snapshot: DeliveryStateSnapshot) -> str:
        index_fd, index_path = tempfile.mkstemp(prefix="owlbear-delivery-state-index-")
        os.close(index_fd)
        Path(index_path).unlink()
        environment = {**os.environ, "GIT_INDEX_FILE": index_path}
        try:
            self._run_git("read-tree", base or "--empty", environment=environment)
            blob = (
                self._run_git(
                    "hash-object",
                    "-w",
                    "--stdin",
                    input_bytes=snapshot.canonical_bytes(),
                    environment=environment,
                )
                .stdout.decode()
                .strip()
            )
            self._run_git(
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob},{_snapshot_path(snapshot.change_id)}",
                environment=environment,
            )
            tree = self._run_git("write-tree", environment=environment).stdout.decode().strip()
            arguments = ["commit-tree", tree]
            if base is not None:
                arguments.extend(("-p", base))
            arguments.extend(("-m", f"chore: checkpoint Delivery state ({snapshot.change_id})"))
            environment = {
                **environment,
                "GIT_AUTHOR_NAME": "OwlBear",
                "GIT_AUTHOR_EMAIL": "owlbear@localhost",
                "GIT_COMMITTER_NAME": "OwlBear",
                "GIT_COMMITTER_EMAIL": "owlbear@localhost",
            }
            return self._run_git(*arguments, environment=environment).stdout.decode().strip()
        finally:
            Path(index_path).unlink(missing_ok=True)

    def _push_snapshot(self, commit: str, expected_remote_head: str | None) -> None:
        destination = f"refs/heads/{self._state_branch}"
        result = self._run_git(
            "push",
            "--porcelain",
            self._remote,
            f"{commit}:{destination}",
            check=False,
        )
        if result.returncode != 0:
            try:
                observed = self._remote_head()
            except DeliveryStatePublicationError as exc:
                error = DeliveryStateResponseUnknownError(
                    "Delivery-state snapshot push outcome could not be observed",
                    retry_safe=False,
                )
                raise error from exc
            if observed == commit:
                return
            if observed != expected_remote_head:
                _raise_state_conflict("remote Delivery-state branch changed before publication")
            _raise_state_error("Delivery-state snapshot push failed", retry_safe=True)
        try:
            observed = self._remote_head()
        except DeliveryStatePublicationError as exc:
            error = DeliveryStateResponseUnknownError(
                "Delivery-state snapshot push outcome could not be verified",
                retry_safe=False,
            )
            raise error from exc
        if observed != commit:
            _raise_state_response_unknown("Delivery-state snapshot push could not be verified")

    def _git_blob(self, commit: str, path: str) -> bytes:
        result = self._run_git("show", f"{commit}:{path}")
        return result.stdout

    def _validate_branch(self) -> None:
        if not _BRANCH_PATTERN.fullmatch(self._state_branch):
            _raise_state_value_error("Delivery-state branch name is invalid")
        result = self._run_git("check-ref-format", f"refs/heads/{self._state_branch}", check=False)
        if result.returncode != 0:
            _raise_state_value_error("Delivery-state branch name is invalid")

    def _git(
        self,
        *arguments: str,
        input_bytes: bytes | None = None,
        environment: dict[str, str] | None = None,
    ) -> str:
        return self._run_git(*arguments, input_bytes=input_bytes, environment=environment).stdout.decode().strip()

    def _run_git(
        self,
        *arguments: str,
        input_bytes: bytes | None = None,
        environment: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
                (self._git_executable, "-C", str(self._repository), *arguments),
                check=check,
                capture_output=True,
                input=input_bytes,
                env=environment,
            )
        except OSError as exc:
            error = DeliveryStatePublicationError("Git is unavailable for Delivery-state publication", retry_safe=False)
            raise error from exc


def _same_snapshot_inputs(
    current: DeliveryStateSnapshot,
    package_id: str,
    coordination: ChangeCoordination,
    runtime: DeliveryRuntime,
    admission: DeliveryAdmissionReceipt,
) -> bool:
    return (
        _same_snapshot_authority(current, package_id, coordination, runtime, admission)
        and current.frontier == _portable_frontier(runtime)
        and current.completion == runtime.completion_bundle()
    )


def _same_snapshot_authority(
    current: DeliveryStateSnapshot,
    package_id: str,
    coordination: ChangeCoordination,
    runtime: DeliveryRuntime,
    admission: DeliveryAdmissionReceipt,
) -> bool:
    return (
        current.change_id == coordination.change_id
        and current.package_id == package_id
        and current.authority_digest == runtime.authority_digest
        and current.branch == coordination.branch
        and current.change_head == coordination.last_reviewed_commit
        and current.integration_target == coordination.integration_target
        and current.target_head == coordination.target_head
        and current.publication_base_head == coordination.publication_base_head
        and current.last_reviewed_commit == coordination.last_reviewed_commit
        and current.admission == admission
        and current.contract == runtime.contract
    )


def _portable_frontier(runtime: DeliveryRuntime) -> DeliveryFrontier:
    """Project a frontier after the exact checkpoint already published remotely."""
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)
    pending = frontier.pending_checkpoint
    if pending is not None and pending.head == frontier.published_head:
        return frontier.model_copy(update={"pending_checkpoint": None})
    return frontier


def _snapshot_path(change_id: str) -> str:
    _validate_change_id(change_id)
    return f"{_STATE_ROOT}/{change_id}/snapshot.json"


def _snapshot_path_change_id(path: str) -> str | None:
    prefix = f"{_STATE_ROOT}/"
    suffix = "/snapshot.json"
    if not path.startswith(prefix) or not path.endswith(suffix):
        return None
    change_id = path[len(prefix) : -len(suffix)]
    return change_id if _CHANGE_ID_PATTERN.fullmatch(change_id) is not None else None


def _snapshot_validation_code(error: Exception) -> str:
    if "snapshot identity is invalid" in str(error):
        return "snapshot-identity-invalid"
    return "snapshot-invalid"


def _snapshot_validation_detail(error: Exception) -> str:
    if isinstance(error, ValidationError):
        errors = error.errors(include_url=False, include_context=False, include_input=False)
        if errors:
            first = errors[0]
            location = first.get("loc")
            field = (
                ".".join(str(part) for part in location)
                if isinstance(location, tuple | list) and location
                else "snapshot"
            )
            message = " ".join(str(first.get("msg", "invalid value")).split())
            return f"Remote Delivery snapshot field {field} is invalid: {message}"[:240]
    return "Remote Delivery snapshot is invalid and was quarantined."


def _validate_change_id(change_id: str) -> None:
    if _CHANGE_ID_PATTERN.fullmatch(change_id) is None:
        message = "Delivery-state Change identity is invalid"
        raise ValueError(message)


def _canonical_bytes(model: BaseModel) -> bytes:
    return _canonical_payload(model.model_dump(mode="json"))


def _canonical_payload(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _snapshot_digest(snapshot: DeliveryStateSnapshot) -> str:
    return hashlib.sha256(_canonical_bytes(snapshot.model_copy(update={"snapshot_id": ""}))).hexdigest()


def _publication_digest(receipt: DeliveryStatePublicationReceipt) -> str:
    return hashlib.sha256(_canonical_bytes(receipt.model_copy(update={"publication_id": ""}))).hexdigest()


def _raise_state_error(detail: str, *, retry_safe: bool) -> NoReturn:
    raise DeliveryStatePublicationError(detail, retry_safe=retry_safe)


def _raise_state_conflict(detail: str) -> NoReturn:
    raise DeliveryStateConflictError(detail, retry_safe=True)


def _raise_state_value_error(detail: str) -> NoReturn:
    raise ValueError(detail)


__all__ = [
    "DeliveryStateConflictError",
    "DeliveryStatePublicationError",
    "DeliveryStatePublicationReceipt",
    "DeliveryStatePublisher",
    "DeliveryStateResponseUnknownError",
    "DeliveryStateSnapshot",
    "DeliveryStateSnapshotDiagnostic",
    "DeliveryStateSnapshotInventory",
]


def _raise_state_response_unknown(detail: str) -> NoReturn:
    raise DeliveryStateResponseUnknownError(detail, retry_safe=False)
