"""Per-change writer coordination and Git workspace management."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_kanban.change import ChangeId
from owlbear_kanban.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)
from owlbear_kanban.target_runtime import TargetJob

if TYPE_CHECKING:
    from collections.abc import Mapping

    from owlbear_kanban.target_runtime import TargetRuntime

_GIT_EXECUTABLE = "/usr/bin/git"
_MERGE_RECORD_PARTS = 3


class _WorkspaceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class WriterIdentity(_WorkspaceModel):
    """Actor identity supplied when portfolio dispatch grants one writer."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    claimed_at: str = Field(min_length=1)


class ChangeWriter(WriterIdentity):
    """One active writer bound to a target transformation."""

    job_id: int = Field(gt=0)
    kind: Literal["plan", "build", "assembly"]


class ChangeCoordination(_WorkspaceModel):
    """One OCC-guarded writable workspace record per change."""

    schema_version: Literal[1] = 1
    change_id: ChangeId
    branch: str = Field(min_length=1)
    worktree_path: Path
    integration_target: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    writer: ChangeWriter | None = None


class CapacityLedger(_WorkspaceModel):
    """Global writer capacity without serializing independent changes."""

    schema_version: Literal[1] = 1
    capacity: int = Field(gt=0)
    change_ids: tuple[ChangeId, ...] = ()

    @model_validator(mode="after")
    def _validate_holders(self) -> CapacityLedger:
        if self.change_ids != tuple(sorted(set(self.change_ids))):
            msg = "capacity holders must be unique and sorted"
            raise ValueError(msg)
        if len(self.change_ids) > self.capacity:
            msg = "capacity holders exceed the global limit"
            raise ValueError(msg)
        return self


class WriterGrant(_WorkspaceModel):
    """One portfolio dispatch grant."""

    coordination: ChangeCoordination
    job: TargetJob


class IntegrationFinding(_WorkspaceModel):
    """Immutable evidence that integration requires solution planning."""

    finding_id: str = Field(min_length=1)
    change_id: ChangeId
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class IntegrationResult(_WorkspaceModel):
    """Contain either one reviewed merge commit or one integration finding."""

    merge_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    finding: IntegrationFinding | None = None

    @model_validator(mode="after")
    def _require_one_result(self) -> IntegrationResult:
        if (self.merge_commit is None) == (self.finding is None):
            msg = "integration requires either a merge commit or a finding"
            raise ValueError(msg)
        return self


class CoordinationConflictError(RuntimeError):
    """A per-change writer or global capacity slot is unavailable."""

    code = "ERR_TARGET_COORDINATION_CONFLICT"


class PortfolioCoordinator:
    """Atomically coordinate independent per-change writers and global capacity."""

    def __init__(self, state_root: Path, capacity: int) -> None:
        self._state_root = state_root
        self._coordination_root = state_root / "target-runtime" / "coordination"
        self._ledger_path = state_root / "target-runtime" / "capacity.json"
        self._capacity = capacity
        state_root.mkdir(parents=True, exist_ok=True)
        self._initialize_ledger()

    def register(self, coordination: ChangeCoordination) -> ChangeCoordination:
        """Create one replayable per-change coordination record."""
        path = self._coordination_path(coordination.change_id)
        content = _model_content(coordination)
        if path.exists():
            existing = ChangeCoordination.model_validate_json(path.read_bytes())
            if existing != coordination:
                _coordination_conflict("change workspace is already registered differently")
            return existing
        self._commit(
            f"register-{coordination.change_id}",
            (TransactionParticipant(self._state_root, path.relative_to(self._state_root), content),),
        )
        return coordination

    def show(self, change_id: str) -> ChangeCoordination:
        """Return one current per-change coordination record."""
        path = self._coordination_path(change_id)
        try:
            return ChangeCoordination.model_validate_json(path.read_bytes())
        except FileNotFoundError as exc:
            msg = f"change workspace is not registered: {change_id}"
            raise CoordinationConflictError(msg) from exc

    def acquire(self, change_id: str, writer: ChangeWriter) -> ChangeCoordination:
        """Atomically bind one writer and one global capacity slot."""
        coordination_path = self._coordination_path(change_id)
        coordination_bytes = coordination_path.read_bytes()
        coordination = ChangeCoordination.model_validate_json(coordination_bytes)
        ledger_bytes = self._ledger_path.read_bytes()
        ledger = CapacityLedger.model_validate_json(ledger_bytes)
        if coordination.writer is not None or change_id in ledger.change_ids:
            _coordination_conflict("change already has an active writer")
        if len(ledger.change_ids) >= ledger.capacity:
            _coordination_conflict("global writer capacity is exhausted")
        claimed = coordination.model_copy(update={"writer": writer})
        occupied = ledger.model_copy(update={"change_ids": tuple(sorted((*ledger.change_ids, change_id)))})
        participants = (
            _replacement(self._state_root, coordination_path, coordination_bytes, claimed),
            _replacement(self._state_root, self._ledger_path, ledger_bytes, occupied),
        )
        try:
            self._commit(f"acquire-{change_id}-{writer.claim_id}", participants)
        except TransactionConflictError as exc:
            msg = "writer coordination changed concurrently"
            raise CoordinationConflictError(msg) from exc
        return claimed

    def release(self, change_id: str, claim_id: str) -> ChangeCoordination:
        """Release one exact writer and its capacity slot."""
        coordination_path = self._coordination_path(change_id)
        coordination_bytes = coordination_path.read_bytes()
        coordination = ChangeCoordination.model_validate_json(coordination_bytes)
        ledger_bytes = self._ledger_path.read_bytes()
        ledger = CapacityLedger.model_validate_json(ledger_bytes)
        if coordination.writer is None or coordination.writer.claim_id != claim_id:
            _coordination_conflict("writer claim does not own the change workspace")
        released = coordination.model_copy(update={"writer": None})
        available = ledger.model_copy(
            update={"change_ids": tuple(item for item in ledger.change_ids if item != change_id)}
        )
        participants = (
            _replacement(self._state_root, coordination_path, coordination_bytes, released),
            _replacement(self._state_root, self._ledger_path, ledger_bytes, available),
        )
        try:
            self._commit(f"release-{change_id}-{claim_id}", participants)
        except TransactionConflictError as exc:
            msg = "writer coordination changed concurrently"
            raise CoordinationConflictError(msg) from exc
        return released

    def update(self, coordination: ChangeCoordination) -> ChangeCoordination:
        """OCC-replace one registered per-change record without touching capacity."""
        path = self._coordination_path(coordination.change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        if existing.writer != coordination.writer:
            _coordination_conflict("workspace update cannot change writer ownership")
        participant = _replacement(self._state_root, path, previous, coordination)
        try:
            self._commit(f"update-{coordination.change_id}", (participant,))
        except TransactionConflictError as exc:
            msg = "change workspace changed concurrently"
            raise CoordinationConflictError(msg) from exc
        return coordination

    def publish_finding(self, finding: IntegrationFinding) -> IntegrationFinding:
        """Publish one immutable integration finding inside target evidence."""
        relative = Path("target-runtime/integration-findings") / f"{finding.finding_id}.json"
        self._commit(
            f"finding-{finding.finding_id}",
            (TransactionParticipant(self._state_root, relative, _model_content(finding)),),
        )
        return finding

    def _initialize_ledger(self) -> None:
        initial = CapacityLedger(capacity=self._capacity)
        if self._ledger_path.exists():
            existing = CapacityLedger.model_validate_json(self._ledger_path.read_bytes())
            if existing.capacity != self._capacity:
                _coordination_conflict("configured writer capacity differs from the durable ledger")
            return
        self._commit(
            "initialize-capacity",
            (
                TransactionParticipant(
                    self._state_root,
                    self._ledger_path.relative_to(self._state_root),
                    _model_content(initial),
                ),
            ),
        )

    def _coordination_path(self, change_id: str) -> Path:
        if not change_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in change_id):
            msg = "change identity is not a safe coordination path"
            raise ValueError(msg)
        return self._coordination_root / f"{change_id}.json"

    def _commit(
        self,
        transaction_id: str,
        participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...],
    ) -> None:
        RuntimeTransaction(self._state_root, f"portfolio-{transaction_id}", participants).commit()


class PortfolioDispatcher:
    """Grant at most one ready writer from each change under global capacity."""

    def __init__(self, coordinator: PortfolioCoordinator) -> None:
        self._coordinator = coordinator

    def dispatch(
        self,
        runtimes: Mapping[str, TargetRuntime],
        identities: Mapping[str, WriterIdentity],
    ) -> tuple[WriterGrant, ...]:
        """Grant ready jobs in stable cross-change order until capacity is full."""
        candidates = []
        for change_id, runtime in runtimes.items():
            frontier = runtime.list_frontier()
            if frontier:
                candidates.append((frontier[0].created_at, frontier[0].job_id, change_id, frontier[0]))
        grants: list[WriterGrant] = []
        for _created_at, _job_id, change_id, job in sorted(candidates):
            identity = identities[change_id]
            writer = ChangeWriter(**identity.model_dump(), job_id=job.job_id, kind=job.kind)
            try:
                coordination = self._coordinator.acquire(change_id, writer)
            except CoordinationConflictError as exc:
                if "capacity" in str(exc):
                    break
                continue
            grants.append(WriterGrant(coordination=coordination, job=job))
        return tuple(grants)


class ChangeWorkspaceManager:
    """Own one warm writable Git worktree and non-rewriting integration per change."""

    def __init__(
        self,
        repository: Path,
        worktree_root: Path,
        coordinator: PortfolioCoordinator,
        integration_target: str,
    ) -> None:
        self._repository = repository.resolve()
        self._worktree_root = worktree_root.resolve()
        self._coordinator = coordinator
        self._integration_target = integration_target
        self._git("check-ref-format", f"refs/heads/{integration_target}")

    def create(self, change_id: str) -> ChangeCoordination:
        """Create or replay one warm branch and worktree from the configured target."""
        try:
            existing = self._coordinator.show(change_id)
        except CoordinationConflictError:
            existing = None
        if existing is not None:
            if existing.integration_target != self._integration_target:
                _workspace_failure("registered workspace uses another integration target")
            self._require_worktree(
                existing.worktree_path,
                existing.branch,
                self._resolve(existing.branch),
            )
            return existing
        branch = f"owlbear/change/{change_id}"
        self._git("check-ref-format", f"refs/heads/{branch}")
        worktree = self._worktree_root / change_id
        target_head = self._resolve(self._integration_target)
        branch_head = self._resolve(branch, missing_ok=True)
        if branch_head is None:
            self._git("branch", branch, target_head)
            branch_head = target_head
        if not worktree.exists():
            worktree.parent.mkdir(parents=True, exist_ok=True)
            self._git("worktree", "add", str(worktree), branch)
        self._require_worktree(worktree, branch, branch_head)
        coordination = ChangeCoordination(
            change_id=change_id,
            branch=branch,
            worktree_path=worktree,
            integration_target=self._integration_target,
            target_head=target_head,
            last_reviewed_commit=target_head,
        )
        return self._coordinator.register(coordination)

    def record_reviewed(self, change_id: str, commit: str) -> ChangeCoordination:
        """Advance the recorded reviewed boundary to an exact branch ancestor."""
        coordination = self._coordinator.show(change_id)
        branch_head = self._resolve(coordination.branch)
        self._require_ancestor(commit, branch_head)
        updated = coordination.model_copy(update={"last_reviewed_commit": commit})
        return self._coordinator.update(updated)

    def restart(self, change_id: str, attempt_id: str, rejected_head: str) -> ChangeCoordination:
        """Preserve a rejected head and recreate the change at its reviewed boundary."""
        coordination = self._coordinator.show(change_id)
        if coordination.writer is None or coordination.writer.attempt_id != attempt_id:
            _coordination_conflict("restart attempt does not own the change writer")
        if self._resolve(coordination.branch) != rejected_head:
            _workspace_failure("rejected head is not the current change branch")
        worktree = coordination.worktree_path
        if self._git("-C", str(worktree), "status", "--porcelain"):
            _workspace_failure("restart requires a clean committed change worktree")
        attempt_ref = f"refs/owlbear/attempts/{change_id}/{attempt_id}"
        self._git("check-ref-format", attempt_ref)
        if self._resolve(attempt_ref, missing_ok=True) is not None:
            _workspace_failure("attempt history ref already exists")
        self._git("update-ref", attempt_ref, rejected_head, "0" * 40)
        self._git("worktree", "remove", str(worktree))
        self._git(
            "update-ref",
            f"refs/heads/{coordination.branch}",
            coordination.last_reviewed_commit,
            rejected_head,
        )
        self._git("worktree", "add", str(worktree), coordination.branch)
        return self._coordinator.release(change_id, coordination.writer.claim_id)

    def integrate(self, change_id: str, reviewed_commits: tuple[str, ...]) -> IntegrationResult:
        """Merge one change without rewriting reviewed commits and CAS the configured target."""
        coordination = self._coordinator.show(change_id)
        change_head = self._resolve(coordination.branch)
        for commit in reviewed_commits:
            self._require_ancestor(commit, change_head)
        target_head = self._resolve(coordination.integration_target)
        integration_worktree = self._worktree_root / f".integration-{change_id}"
        if integration_worktree.exists():
            _workspace_failure("integration worktree already exists")
        self._require_clean_checked_out_target(coordination.integration_target)
        self._git("worktree", "add", "--detach", str(integration_worktree), target_head)
        try:
            self._git("-C", str(integration_worktree), "merge", "--no-ff", "--no-edit", coordination.branch)
        except subprocess.CalledProcessError:
            self._git("-C", str(integration_worktree), "merge", "--abort", check=False)
            self._git("worktree", "remove", "--force", str(integration_worktree))
            return IntegrationResult(finding=self._publish_integration_finding(coordination, change_head, target_head))
        merge_commit = self._resolve("HEAD", cwd=integration_worktree)
        self._require_merge_commit(merge_commit, reviewed_commits, cwd=integration_worktree)
        self._git("worktree", "remove", str(integration_worktree))
        self._git(
            "update-ref",
            f"refs/heads/{coordination.integration_target}",
            merge_commit,
            target_head,
        )
        self._git("-C", str(coordination.worktree_path), "merge", "--ff-only", merge_commit)
        self._refresh_checked_out_target(coordination.integration_target, merge_commit)
        updated = coordination.model_copy(update={"target_head": merge_commit, "last_reviewed_commit": merge_commit})
        self._coordinator.update(updated)
        return IntegrationResult(merge_commit=merge_commit)

    def _publish_integration_finding(
        self,
        coordination: ChangeCoordination,
        change_head: str,
        target_head: str,
    ) -> IntegrationFinding:
        identity = hashlib.sha256(f"{coordination.change_id}:{change_head}:{target_head}".encode()).hexdigest()[:16]
        finding = IntegrationFinding(
            finding_id=f"integration-{identity}",
            change_id=coordination.change_id,
            change_head=change_head,
            target_head=target_head,
            integration_target=coordination.integration_target,
            detail="Change and integration target conflict; accepted change-level composition authority is required.",
        )
        return self._coordinator.publish_finding(finding)

    def _require_worktree(self, worktree: Path, branch: str, expected_head: str) -> None:
        if self._resolve("HEAD", cwd=worktree) != expected_head:
            _workspace_failure("change worktree head differs from its branch")
        current = self._git("-C", str(worktree), "branch", "--show-current")
        if current != branch:
            _workspace_failure("change worktree is attached to another branch")

    def _require_ancestor(self, commit: str, descendant: str) -> None:
        if not self._is_ancestor(commit, descendant, cwd=self._repository):
            _workspace_failure("reviewed commit is not an ancestor of the change head")

    def _require_merge_commit(self, commit: str, reviewed: tuple[str, ...], *, cwd: Path) -> None:
        parents = self._git("-C", str(cwd), "rev-list", "--parents", "-n", "1", commit).split()
        if len(parents) < _MERGE_RECORD_PARTS:
            _workspace_failure("integration did not create a merge commit")
        for reviewed_commit in reviewed:
            if not self._is_ancestor(reviewed_commit, commit, cwd=cwd):
                _workspace_failure("integration rewrote or omitted a reviewed commit")

    @staticmethod
    def _is_ancestor(ancestor: str, descendant: str, *, cwd: Path) -> bool:
        result = subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            (_GIT_EXECUTABLE, "-C", str(cwd), "merge-base", "--is-ancestor", ancestor, descendant),
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    def _require_clean_checked_out_target(self, target: str) -> None:
        current = self._git("branch", "--show-current")
        if current == target and self._git("status", "--porcelain"):
            _workspace_failure("checked-out integration target has uncommitted changes")

    def _refresh_checked_out_target(self, target: str, commit: str) -> None:
        if self._git("branch", "--show-current") == target:
            self._git("reset", "--hard", commit)

    def _resolve(self, revision: str, *, cwd: Path | None = None, missing_ok: bool = False) -> str | None:
        try:
            return self._git("rev-parse", "--verify", f"{revision}^{{commit}}", cwd=cwd)
        except subprocess.CalledProcessError:
            if missing_ok:
                return None
            raise

    def _git(self, *arguments: str, cwd: Path | None = None, check: bool = True) -> str:
        result = subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            (_GIT_EXECUTABLE, "-C", str(cwd or self._repository), *arguments),
            check=check,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()


def _replacement(
    root: Path,
    path: Path,
    previous: bytes,
    replacement: BaseModel,
) -> ReplacementTransactionParticipant:
    return ReplacementTransactionParticipant(
        root,
        path.relative_to(root),
        previous,
        _model_content(replacement),
    )


def _model_content(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json")
    return f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n".encode()


def _coordination_conflict(detail: str) -> Never:
    raise CoordinationConflictError(detail)


def _workspace_failure(detail: str) -> Never:
    raise RuntimeError(detail)
