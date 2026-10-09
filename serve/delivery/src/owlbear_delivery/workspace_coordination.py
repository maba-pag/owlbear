"""Per-change writer coordination and publication leases."""

from __future__ import annotations

import hashlib
import os
import re
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import ValidationError

from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RecoveryIntent,
    RecoveryReceipt,
    digest,
    encoded,
    journal_path,
)
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery.workspace_models import (
    _OCC_RETRY_LIMIT,
    _PUBLICATION_LEASE_MAX_SECONDS,
    _PUBLICATION_OPERATION_PATTERN,
    BuilderHandoffMetadata,
    ChangeBuilderHandoff,
    ChangeContinuationAction,
    ChangeCoordination,
    ChangeDirectOperation,
    ChangeFinalizationAttempt,
    ChangeFinalizationAttention,
    ChangePauseRequest,
    ChangePauseRequestedError,
    ChangeWriter,
    CoordinationConflictError,
    PublicationLease,
    PublicationLock,
    _coordination_conflict,
    _is_settled_finalizer_attention_sync,
    _model_content,
    _publication_timestamp,
    _replacement,
    direct_operation_marker_name,
    recovery_authority_digest,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from contextlib import AbstractContextManager


DrainPermitKind = Literal["mutation", "operator", "reserve", "acquire", "provider", "state", "lease", "snapshot"]


@dataclass
class DrainAuthority:
    """Process-local K2 token: one owner's permitted drain operations for one Change.

    Each entry rebuilds it from durable evidence or creates it with its own start marker; it is
    never persisted. It permits only the named operations, each bound to the owner's identity.
    ``publishes_checkpoint`` marks owners whose K2 row includes the queued checkpoint's branch
    reservation; ``requires_lease`` keeps a standalone publication token inert until its own lease commits.
    """

    change_id: str
    owner: str
    permits: dict[str, set[str]] = field(default_factory=dict)
    publishes_checkpoint: bool = False
    requires_lease: bool = False

    @property
    def active(self) -> bool:
        """Return whether this token currently grants anything (a lease token needs its committed lease)."""
        return not self.requires_lease or bool(self.permits.get("lease"))

    def permit(self, kind: DrainPermitKind, *identities: str) -> None:
        """Add operations this owner learned it must finish (for example a merged head's push)."""
        self.permits.setdefault(kind, set()).update(identities)

    def allows(self, kind: DrainPermitKind, identity: str) -> bool:
        """Return whether this token permits one exact operation."""
        return identity in self.permits.get(kind, set())


class PortfolioCoordinator:
    """Atomically coordinate independent per-change writers."""

    def __init__(self, state_root: Path) -> None:
        self._state_root = state_root
        self._coordination_root = state_root / "coordination" / "changes"
        self._continuation_owner: ContextVar[str | None] = ContextVar("continuation_owner", default=None)
        self._drain_authorities: ContextVar[tuple[DrainAuthority, ...]] = ContextVar("drain_authorities", default=())
        self._verified_exclusions: set[tuple[int, str]] = set()
        state_root.mkdir(parents=True, exist_ok=True)
        RuntimeTransaction.recover_all(state_root)

    def recover_pending_transactions(self) -> None:
        """Complete pending coordinator transactions before reading ownership state."""
        RuntimeTransaction.recover_all(self._state_root)

    @property
    def runtime_root(self) -> Path:
        """Return the shared transaction and recovery root."""
        return self._state_root.resolve()

    def acquisition_lock(self, *, blocking: bool = True) -> AbstractContextManager[None]:
        """Serialize portfolio selection and staged claim preparation."""
        lock_root = self._state_root / "claims" / "acquisition-lock"
        return locked_roots((lock_root,), blocking=blocking)

    @contextmanager
    def publication_lock(self, change_id: str, *, blocking: bool = True) -> Iterator[PublicationLock]:
        """Serialize bounded publication attempts for one Change across processes."""
        with self.recovery_lock(change_id, blocking=blocking):
            lock = PublicationLock(self, change_id)
            try:
                self.require_continuation_access(change_id)
                yield lock
            finally:
                lock.close()

    @contextmanager
    def recovery_lock(self, change_id: str, *, blocking: bool = True) -> Iterator[None]:
        """Lock exact custody for observation/CAS, without granting effect-entry access."""
        self._coordination_path(change_id)
        namespace_root = self._state_root / "claims" / "publication-locks"
        lock_root = namespace_root / change_id
        with ExitStack() as child_locks:
            with locked_roots((namespace_root,), blocking=blocking):
                child_locks.enter_context(locked_roots((lock_root,), blocking=blocking))
            yield

    def recovery_coordination_bytes(self, change_id: str, owner_id: str) -> bytes:
        """Capture the exact fenced coordination bytes that intent publication will CAS."""
        coordination, _previous = self._read_coordination(change_id)
        if (
            coordination.builder_handoff is not None
            or coordination.finalization_attention is not None
            or coordination.recovery_owner_id not in {None, owner_id}
        ):
            raise DeliveryWorkerExclusionRequiredError
        return _model_content(coordination.model_copy(update={"recovery_owner_id": owner_id}))

    def record_recovery_intent(self, intent: RecoveryIntent) -> None:
        """Atomically fence ordinary writers and persist intent without releasing custody."""
        request = intent.invocation.request
        _coordination, previous = self._read_coordination(request.change_id)
        replacement = self.recovery_coordination_bytes(request.change_id, request.owner_id)
        frontier_path = Path("changes") / request.change_id / "frontier.json"
        frontier = (self._state_root / frontier_path).read_bytes()
        authority = recovery_authority_digest(ChangeCoordination.model_validate_json(replacement))
        if authority != intent.coordination_digest or digest(frontier) != intent.frontier_digest:
            raise DeliveryWorkerExclusionRequiredError
        self._commit(
            f"propose-recovery-{intent.recovery_id}",
            (
                ReplacementTransactionParticipant(
                    self._state_root,
                    self._coordination_path(request.change_id).relative_to(self._state_root),
                    previous,
                    replacement,
                ),
                TransactionParticipant(
                    self._state_root, journal_path(request.change_id, intent.recovery_id, "intent"), encoded(intent)
                ),
                ReplacementTransactionParticipant(self._state_root, frontier_path, frontier, frontier),
            ),
        )

    def prepare_recovery_release(
        self, intent: RecoveryIntent, receipt: RecoveryReceipt
    ) -> ReplacementTransactionParticipant:
        """Prepare only the journal-verified exact release for the runtime transaction."""
        request = intent.invocation.request
        coordination, previous = self._read_coordination(request.change_id)
        if coordination.builder_handoff is not None or coordination.finalization_attention is not None:
            raise DeliveryWorkerExclusionRequiredError
        if (
            recovery_authority_digest(coordination) != intent.coordination_digest
            or coordination.recovery_owner_id != request.owner_id
            or receipt.recovery_id != intent.recovery_id
            or receipt.evidence.recovery_id != intent.recovery_id
            or receipt.evidence.invocation != intent.invocation
            or receipt.evidence.status not in {"closed", "excluded"}
            or (self._state_root / journal_path(request.change_id, intent.recovery_id, "intent")).read_bytes()
            != encoded(intent)
            or (self._state_root / journal_path(request.change_id, intent.recovery_id, "evidence")).read_bytes()
            != encoded(receipt.evidence)
        ):
            raise DeliveryWorkerExclusionRequiredError
        changes = {"recovery_owner_id": None}
        if receipt.evidence.status == "excluded":
            changes["recovery_exclusions"] = (*coordination.recovery_exclusions, intent.recovery_id)
        if intent.kind == "ready-readback":
            action = coordination.continuation_action
            if action is None or action.operation_id != request.owner_id or action.finished_at is not None:
                raise DeliveryWorkerExclusionRequiredError
            changes["continuation_action"] = action.model_copy(update={"finished_at": receipt.finished_at})
        else:
            writer = coordination.writer
            if writer is not None:
                if writer.claim_id != request.owner_id or writer.attempt_id != request.attempt_id:
                    raise DeliveryWorkerExclusionRequiredError
                changes["writer"] = None
            if intent.kind == "clean-finalizer":
                attempt = coordination.finalization_attempt
                if writer is None or attempt is None or attempt.writer != writer or attempt.finished_at is not None:
                    raise DeliveryWorkerExclusionRequiredError
                changes["finalization_attempt"] = attempt.model_copy(update={"finished_at": receipt.finished_at})
        return _replacement(
            self._state_root,
            self._coordination_path(request.change_id),
            previous,
            coordination.model_copy(update=changes),
        )

    def prepare_finalization_repair_release(
        self, change_id: str, attempt_id: str, finished_at: str
    ) -> TransactionParticipant | ReplacementTransactionParticipant:
        """Join one failed finalizer's custody release to a repair transaction.

        Recovery A may have already released the failed finalizer before its private
        preservation is captured.  In that case retain an exact no-op participant
        rather than reopening or silently replacing the completed attempt.
        """
        coordination, previous = self._read_coordination(change_id)
        self.require_no_pending_recovery(change_id)
        self._require_continuation_coordination(coordination)
        writer = coordination.writer
        attempt = coordination.finalization_attempt
        if (
            writer is None
            and attempt is not None
            and attempt.writer.attempt_id == attempt_id
            and attempt.finished_at is not None
        ):
            return TransactionParticipant(
                self._state_root,
                self._coordination_path(change_id).relative_to(self._state_root),
                previous,
            )
        if (
            writer is None
            or writer.kind != "finalize"
            or writer.attempt_id != attempt_id
            or attempt is None
            or attempt.writer != writer
            or attempt.finished_at is not None
        ):
            raise DeliveryWorkerExclusionRequiredError
        updated = coordination.model_copy(
            update={
                "writer": None,
                "finalization_attempt": attempt.model_copy(update={"finished_at": finished_at}),
            }
        )
        return _replacement(
            self._state_root,
            self._coordination_path(change_id),
            previous,
            updated,
        )

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
        return self._read_coordination(change_id)[0]

    def coordination_bytes(self, change_id: str) -> bytes:
        """Return the exact current coordination bytes for an OCC fence."""
        return self._read_coordination(change_id)[1]

    def require_continuation_access(self, change_id: str) -> None:
        """Refuse mutations outside the fixed executor while an action retains custody."""
        self._require_continuation_coordination(self.show(change_id))

    def _require_continuation_coordination(self, coordination: ChangeCoordination) -> None:
        self.require_no_pending_recovery(coordination.change_id)
        action = coordination.continuation_action
        if action is not None and action.finished_at is None and self._continuation_owner.get() != action.operation_id:
            _coordination_conflict(f"Change retains continuation action custody: {action.operation_id}")

    def require_no_pending_recovery(self, change_id: str) -> None:
        """Keep every normal mutation behind an unfinished recovery's custody fence."""
        coordination = self.show(change_id)
        if coordination.recovery_owner_id is not None or not self.recovery_exclusions_verified(coordination):
            raise DeliveryWorkerExclusionRequiredError

    def recovery_exclusions_verified(self, coordination: ChangeCoordination) -> bool:
        """Require fresh process-local verification of every restart-durable exclusion."""
        return all(
            (os.getpid(), recovery_id) in self._verified_exclusions for recovery_id in coordination.recovery_exclusions
        )

    def recovery_verification_recorded(self, recovery_id: str) -> bool:
        """Return whether this process verified one closed or excluded recovery."""
        return (os.getpid(), recovery_id) in self._verified_exclusions

    def record_verified_exclusion(self, recovery_id: str) -> None:
        """Remember the application owner's verification, never a persisted timestamp."""
        self._verified_exclusions.add((os.getpid(), recovery_id))

    def forget_verified_exclusion(self, recovery_id: str) -> None:
        """Fail closed while a previously accepted exclusion is being revalidated."""
        self._verified_exclusions.discard((os.getpid(), recovery_id))

    def executing_continuation(self, change_id: str) -> bool:
        """Report whether this call context owns the retained fixed operation."""
        action = self.show(change_id).continuation_action
        return (
            action is not None and action.finished_at is None and self._continuation_owner.get() == action.operation_id
        )

    @contextmanager
    def continuation_execution(self, action: ChangeContinuationAction) -> Iterator[None]:
        """Authorize only this call context to run one retained deterministic owner."""
        if self.show(action.change_id).continuation_action != action or action.finished_at is not None:
            _coordination_conflict("continuation execution does not match retained custody")
        token = self._continuation_owner.set(action.operation_id)
        try:
            yield
        finally:
            self._continuation_owner.reset(token)

    @contextmanager
    def drain_authority(
        self,
        change_id: str,
        owner: str,
        *,
        publishes_checkpoint: bool = False,
        requires_lease: bool = False,
        **permits: Iterable[str],
    ) -> Iterator[DrainAuthority]:
        """Hold one process-local K2 drain token for this call context only."""
        self._coordination_path(change_id)
        authority = DrainAuthority(
            change_id, owner, publishes_checkpoint=publishes_checkpoint, requires_lease=requires_lease
        )
        for kind, identities in permits.items():
            authority.permit(kind, *identities)  # type: ignore[arg-type]
        token = self._drain_authorities.set((*self._drain_authorities.get(), authority))
        try:
            yield authority
        finally:
            self._drain_authorities.reset(token)

    def drain_permits(self, change_id: str, kind: DrainPermitKind, identity: str) -> bool:
        """Return whether an active token in this call context permits one exact drain operation."""
        return any(
            authority.change_id == change_id and authority.active and authority.allows(kind, identity)
            for authority in self._drain_authorities.get()
        )

    def current_drain_authority(self, change_id: str) -> DrainAuthority | None:
        """Return the innermost active token for one Change, if this context owns one."""
        return next(
            (
                authority
                for authority in reversed(self._drain_authorities.get())
                if authority.change_id == change_id and authority.active
            ),
            None,
        )

    def _grant_committed_lease(self, change_id: str, operation_id: str) -> None:
        """K2 lease row: the token created with this context's committed lease now drains its call."""
        for authority in self._drain_authorities.get():
            if authority.change_id == change_id and authority.requires_lease:
                authority.permit("lease", operation_id)

    def start_pause_fenced(self, change_id: str, owner: str) -> None:
        """K3 operator start: commit Pause-free coordination bytes as this entry's start point.

        A Pause committed first refuses the start before any effect; one committed later finds a
        started owner that drains under its own token. Takes no lock of its own.
        """
        path = self._coordination_path(change_id).relative_to(self._state_root)
        for _attempt in range(_OCC_RETRY_LIMIT):
            coordination, previous = self._read_coordination(change_id)
            if coordination.pause_request is not None:
                raise ChangePauseRequestedError
            identity = hashlib.sha256(owner.encode() + previous).hexdigest()
            try:
                self._commit(
                    f"operator-start-{identity}",
                    (ReplacementTransactionParticipant(self._state_root, path, previous, previous),),
                )
            except TransactionConflictError:
                continue
            return
        _coordination_conflict("operator start coordination remained concurrent")

    def require_pause_permits(
        self,
        change_id: str,
        kind: DrainPermitKind,
        identity: str,
        coordination: ChangeCoordination | None = None,
    ) -> None:
        """Refuse one new start while a Pause request exists unless its own drain token permits it."""
        current = coordination if coordination is not None else self.show(change_id)
        if current.pause_request is not None and not self.drain_permits(change_id, kind, identity):
            raise ChangePauseRequestedError

    def pause_request(self, change_id: str) -> ChangePauseRequest | None:
        """Return the durable Pause request recorded beside custody, if any."""
        return self.show(change_id).pause_request

    def record_pause_request(self, request: ChangePauseRequest, expected_frontier_digest: str) -> ChangePauseRequest:
        """K1 Record: commit the request with the exact observed frontier, taking no Change lock."""
        return self._replace_pause_request(request.change_id, request, expected_frontier_digest)

    def clear_pause_request(self, change_id: str, expected_frontier_digest: str) -> ChangePauseRequest | None:
        """K1 Resume of a request: clear it through the same frontier-bound transaction."""
        return self._replace_pause_request(change_id, None, expected_frontier_digest)

    def _replace_pause_request(
        self,
        change_id: str,
        request: ChangePauseRequest | None,
        expected_frontier_digest: str,
    ) -> ChangePauseRequest | None:
        frontier_path = Path("changes") / change_id / "frontier.json"
        for _attempt in range(_OCC_RETRY_LIMIT):
            coordination, previous = self._read_coordination(change_id)
            existing = coordination.pause_request
            if request is not None and existing is not None:
                if existing.reason != request.reason:
                    _coordination_conflict("Change pause request already exists with another reason")
                return existing
            if request is None and existing is None:
                return None
            frontier = (self._state_root / frontier_path).read_bytes()
            if hashlib.sha256(frontier).hexdigest() != expected_frontier_digest:
                _coordination_conflict("Change intent frontier changed")
            replacement = coordination.model_copy(update={"pause_request": request})
            identity = hashlib.sha256(previous + _model_content(replacement)).hexdigest()
            try:
                self._commit(
                    f"pause-request-{change_id}-{identity}",
                    (
                        _replacement(self._state_root, self._coordination_path(change_id), previous, replacement),
                        ReplacementTransactionParticipant(self._state_root, frontier_path, frontier, frontier),
                    ),
                )
            except TransactionConflictError:
                continue
            return request if request is not None else existing
        return _coordination_conflict("Change pause request coordination remained concurrent")

    def prepare_pause_request_clear(
        self, change_id: str, request: ChangePauseRequest
    ) -> ReplacementTransactionParticipant:
        """Join one exact request's removal to a conversion, completion or abandonment transaction."""
        coordination, previous = self._read_coordination(change_id)
        if coordination.pause_request != request:
            _coordination_conflict("Change pause request changed before conversion")
        return _replacement(
            self._state_root,
            self._coordination_path(change_id),
            previous,
            coordination.model_copy(update={"pause_request": None}),
        )

    def recovery_authority_digest(self, change_id: str) -> str:
        """Return the K4 recovery authority digest of current coordination."""
        return recovery_authority_digest(self.show(change_id))

    def prepare_pause_fence(
        self, change_id: str, kind: DrainPermitKind, identity: str
    ) -> ReplacementTransactionParticipant:
        """Join exact Pause-free (or token-permitted) coordination bytes to one start commit (K3)."""
        coordination, previous = self._read_coordination(change_id)
        self.require_pause_permits(change_id, kind, identity, coordination)
        return ReplacementTransactionParticipant(
            self._state_root,
            self._coordination_path(change_id).relative_to(self._state_root),
            previous,
            previous,
        )

    def direct_operation_path(self, operation: ChangeDirectOperation, *, finished: bool = False) -> Path:
        """Locate one direct marker under ``action-receipts/direct-<sha256(kind:operation_id)>/``."""
        self._coordination_path(operation.change_id)
        return (
            self._state_root
            / "changes"
            / operation.change_id
            / "action-receipts"
            / direct_operation_marker_name(operation.kind, operation.operation_id)
            / ("finished.json" if finished else "started.json")
        )

    def direct_operation_state(self, operation: ChangeDirectOperation) -> Literal["absent", "started", "finished"]:
        """Read one direct marker's identity-checked state without writing."""
        started = self._read_direct_marker(operation, finished=False)
        if started is None:
            return "absent"
        return "finished" if self._read_direct_marker(operation, finished=True) is not None else "started"

    def _read_direct_marker(self, operation: ChangeDirectOperation, *, finished: bool) -> ChangeDirectOperation | None:
        try:
            content = self.direct_operation_path(operation, finished=finished).read_bytes()
        except FileNotFoundError:
            return None
        recorded = ChangeDirectOperation.model_validate_json(content)
        if (recorded.change_id, recorded.kind, recorded.operation_id) != (
            operation.change_id,
            operation.kind,
            operation.operation_id,
        ):
            _coordination_conflict("direct operation marker identity is invalid")
        if recorded.request_digest != operation.request_digest:
            _coordination_conflict("direct operation identity was started with another request")
        return recorded

    def start_direct_operation(self, operation: ChangeDirectOperation) -> bool:
        """K3: commit ``started.json`` fenced by Pause-free coordination; an identical replay returns False.

        Runs inside the entry's checkpoint lock and takes no lock of its own.
        """
        if self._read_direct_marker(operation, finished=False) is not None:
            return False
        path = self.direct_operation_path(operation).relative_to(self._state_root)
        for _attempt in range(_OCC_RETRY_LIMIT):
            coordination, previous = self._read_coordination(operation.change_id)
            if coordination.pause_request is not None:
                raise ChangePauseRequestedError
            try:
                self._commit(
                    f"direct-start-{direct_operation_marker_name(operation.kind, operation.operation_id)}",
                    (
                        TransactionParticipant(self._state_root, path, _model_content(operation)),
                        ReplacementTransactionParticipant(
                            self._state_root,
                            self._coordination_path(operation.change_id).relative_to(self._state_root),
                            previous,
                            previous,
                        ),
                    ),
                )
            except TransactionConflictError:
                if self._read_direct_marker(operation, finished=False) is not None:
                    return False
                continue
            return True
        return _coordination_conflict("direct operation start remained concurrent")

    def finish_direct_operation(self, operation: ChangeDirectOperation) -> None:
        """Write ``finished.json`` for one exact started marker; a repeated finish is a no-op."""
        if self._read_direct_marker(operation, finished=False) is None:
            _coordination_conflict("direct operation finish requires its matching start marker")
        if self._read_direct_marker(operation, finished=True) is not None:
            return
        path = self.direct_operation_path(operation, finished=True).relative_to(self._state_root)
        self._commit(
            f"direct-finish-{direct_operation_marker_name(operation.kind, operation.operation_id)}",
            (TransactionParticipant(self._state_root, path, _model_content(operation)),),
        )

    def continuation_record_path(self, change_id: str, operation_id: str, *, result: bool = False) -> Path:
        """Locate an immutable action intent or exact result in existing Change state."""
        self._coordination_path(change_id)
        if re.fullmatch(r"continue-[0-9a-f]{64}", operation_id) is None:
            _coordination_conflict("invalid continuation operation identity")
        return (
            self._state_root
            / "changes"
            / change_id
            / "action-receipts"
            / operation_id
            / ("result.json" if result else "intent.json")
        )

    def acquire_continuation_action(self, action: ChangeContinuationAction) -> None:
        """CAS-bind exact frontier custody and immutable intent in one transaction."""
        with self.publication_lock(action.change_id):
            coordination, previous = self._read_coordination(action.change_id)
            self.require_continuation_access(action.change_id)
            if coordination.pause_request is not None:
                raise ChangePauseRequestedError
            attention_sync = _is_settled_finalizer_attention_sync(coordination, action)
            if (coordination.writer is not None and not attention_sync) or coordination.publication_lease is not None:
                _coordination_conflict("continuation cannot overlap active ownership")
            if coordination.worktree_cleanup_intent is not None or coordination.worktree_cleanup is not None:
                _coordination_conflict("continuation cannot overlap worktree cleanup")
            frontier_path = self._state_root / "changes" / action.change_id / "frontier.json"
            frontier = frontier_path.read_bytes()
            if hashlib.sha256(frontier).hexdigest() != action.frontier_digest:
                _coordination_conflict("continuation frontier changed before acquisition")
            retained = coordination.model_copy(update={"continuation_action": action})
            intent_path = self.continuation_record_path(action.change_id, action.operation_id)
            self._commit(
                action.operation_id,
                (
                    _replacement(self._state_root, self._coordination_path(action.change_id), previous, retained),
                    ReplacementTransactionParticipant(
                        self._state_root, frontier_path.relative_to(self._state_root), frontier, frontier
                    ),
                    TransactionParticipant(
                        self._state_root, intent_path.relative_to(self._state_root), _model_content(action)
                    ),
                ),
            )

    def continuation_action_started(self, action: ChangeContinuationAction) -> bool:
        """Read exact effect-entry evidence without creating it."""
        self.require_continuation_access(action.change_id)
        return self.continuation_start_recorded(action)

    def continuation_start_recorded(self, action: ChangeContinuationAction) -> bool:
        """Read one action's identity-checked effect-entry marker without a mutation guard."""
        path = self.continuation_record_path(action.change_id, action.operation_id).with_name("started.json")
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return False
        if content != _model_content(action):
            _coordination_conflict("continuation start identity differs from retained custody")
        return True

    def start_continuation_action(self, action: ChangeContinuationAction) -> bool:
        """Record effect entry fenced by Pause-free coordination (K3).

        An interrupted call is not permission for another effect.
        """
        if self.continuation_action_started(action):
            return False
        path = self.continuation_record_path(action.change_id, action.operation_id).with_name("started.json")
        for _attempt in range(_OCC_RETRY_LIMIT):
            coordination, previous = self._read_coordination(action.change_id)
            if coordination.pause_request is not None:
                raise ChangePauseRequestedError
            try:
                self._commit(
                    f"start-{action.operation_id}",
                    (
                        TransactionParticipant(
                            self._state_root, path.relative_to(self._state_root), _model_content(action)
                        ),
                        ReplacementTransactionParticipant(
                            self._state_root,
                            self._coordination_path(action.change_id).relative_to(self._state_root),
                            previous,
                            previous,
                        ),
                    ),
                )
            except TransactionConflictError:
                if self.continuation_start_recorded(action):
                    return False
                continue
            return True
        return _coordination_conflict("continuation start remained concurrent")

    def release_target_sync_conflict_action(self, action: ChangeContinuationAction) -> None:
        """Hand one conflicted engine sync's retained custody to its preserved-conflict exit; journals remain."""
        self.require_no_pending_recovery(action.change_id)
        for _attempt in range(_OCC_RETRY_LIMIT):
            coordination, previous = self._read_coordination(action.change_id)
            if coordination.continuation_action != action or action.finished_at is not None:
                _coordination_conflict("target-sync conflict custody does not match the retained action")
            try:
                self._commit(
                    f"release-{action.operation_id}",
                    (
                        _replacement(
                            self._state_root,
                            self._coordination_path(action.change_id),
                            previous,
                            coordination.model_copy(update={"continuation_action": None}),
                        ),
                    ),
                )
            except TransactionConflictError:
                continue
            return
        _coordination_conflict("target-sync conflict custody release remained concurrent")

    def finish_continuation_action(
        self, action: ChangeContinuationAction, result: bytes, finished_at: str, *, release: bool
    ) -> None:
        """Persist exact result with custody release, or retain custody on a blocked effect."""
        self.require_continuation_access(action.change_id)
        result_path = self.continuation_record_path(action.change_id, action.operation_id, result=True)
        for _attempt in range(_OCC_RETRY_LIMIT):
            coordination, previous = self._read_coordination(action.change_id)
            if coordination.continuation_action != action:
                _coordination_conflict("continuation result does not match retained custody")
            retained = action.model_copy(update={"finished_at": finished_at}) if release else action
            try:
                self._commit(
                    f"result-{action.operation_id}",
                    (
                        _replacement(
                            self._state_root,
                            self._coordination_path(action.change_id),
                            previous,
                            coordination.model_copy(update={"continuation_action": retained}),
                        ),
                        TransactionParticipant(self._state_root, result_path.relative_to(self._state_root), result),
                    ),
                )
            except TransactionConflictError:
                continue
            return
        _coordination_conflict("continuation result coordination remained concurrent")

    def find_registered(self, change_id: str) -> ChangeCoordination | None:
        """Distinguish genuine absence from unreadable or invalid coordination."""
        try:
            return self.show(change_id)
        except CoordinationConflictError as exc:
            if not isinstance(exc.__cause__, FileNotFoundError):
                raise
            return None

    def _read_coordination(self, change_id: str) -> tuple[ChangeCoordination, bytes]:
        path = self._coordination_path(change_id)
        try:
            content = path.read_bytes()
            coordination = ChangeCoordination.model_validate_json(content)
        except FileNotFoundError as exc:
            msg = f"change workspace is not registered: {change_id}"
            raise CoordinationConflictError(msg) from exc
        except (OSError, ValidationError) as exc:
            msg = f"change coordination record is unreadable or invalid: {change_id}"
            raise CoordinationConflictError(msg) from exc
        if coordination.change_id != change_id:
            _coordination_conflict(f"change coordination record identity is invalid: {change_id}")
        return coordination, content

    def list_registered(self) -> tuple[ChangeCoordination, ...]:
        """Return all registered Change coordination records in stable order."""
        if not self._coordination_root.exists():
            return ()
        if self._coordination_root.is_symlink() or not self._coordination_root.is_dir():
            _coordination_conflict("change coordination root is not a safe directory")
        records = []
        for path in sorted(self._coordination_root.iterdir(), key=lambda item: item.name):
            if path.name.startswith(".") or path.suffix != ".json":
                continue
            try:
                coordination = ChangeCoordination.model_validate_json(path.read_bytes())
            except OSError, ValidationError:
                _coordination_conflict(f"change coordination record is invalid: {path}")
            if path.stem != coordination.change_id:
                _coordination_conflict(f"change coordination record identity is invalid: {path}")
            records.append(coordination)
        return tuple(sorted(records, key=lambda item: item.change_id))

    def acquire(
        self,
        change_id: str,
        writer: ChangeWriter,
        *,
        finalization_attempt: ChangeFinalizationAttempt | None = None,
    ) -> ChangeCoordination:
        """Atomically bind one writer to a Change."""
        coordination = self.show(change_id)
        publication_expiry = coordination.publication_expiry
        if publication_expiry is not None and publication_expiry > datetime.now(UTC):
            _coordination_conflict("change already has an active writer")
        with self.publication_lock(change_id):
            return self._acquire(
                change_id,
                writer,
                finalization_attempt=finalization_attempt,
            )

    @staticmethod
    def _validate_finalizer_attention_retry(
        coordination: ChangeCoordination,
        writer: ChangeWriter,
        finalization_attempt: ChangeFinalizationAttempt | None,
        expected_finalization_attention: ChangeFinalizationAttention | None,
    ) -> bool:
        if expected_finalization_attention is None:
            return False
        prior_attempt = coordination.finalization_attempt
        expected_attention_writer = (
            prior_attempt.writer.model_copy(update={"kind": "finalization-attention"})
            if prior_attempt is not None
            else None
        )
        if (
            prior_attempt is None
            or prior_attempt.finished_at is None
            or coordination.finalization_attention != expected_finalization_attention
            or coordination.writer != expected_attention_writer
            or expected_finalization_attention.attempt_id != prior_attempt.writer.attempt_id
            or expected_finalization_attention.expected_head != prior_attempt.exact_head
            or expected_finalization_attention.expected_reviewed_base != coordination.last_reviewed_commit
            or prior_attempt.writer.attempt_id == writer.attempt_id
            or prior_attempt.writer.claim_id == writer.claim_id
            or finalization_attempt is None
            or finalization_attempt.contract_digest != prior_attempt.contract_digest
            or finalization_attempt.frontier_digest != prior_attempt.frontier_digest
            or finalization_attempt.exact_head != prior_attempt.exact_head
        ):
            _coordination_conflict("finalizer retry does not match its retained attention")
        return True

    def _acquire(
        self,
        change_id: str,
        writer: ChangeWriter,
        *,
        finalization_attempt: ChangeFinalizationAttempt | None = None,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
    ) -> ChangeCoordination:
        if writer.kind in {"handoff", "finalization-attention"}:
            _coordination_conflict("passive workspace custody is not an executable writer")
        if (writer.kind == "finalize") != (finalization_attempt is not None) or (
            finalization_attempt is not None
            and (finalization_attempt.writer != writer or finalization_attempt.finished_at is not None)
        ):
            _coordination_conflict("finalizer acquisition requires its exact unfinished attempt")
        self.require_continuation_access(change_id)
        coordination_path = self._coordination_path(change_id)
        coordination_bytes = coordination_path.read_bytes()
        coordination = ChangeCoordination.model_validate_json(coordination_bytes)
        self.require_pause_permits(change_id, "acquire", writer.claim_id, coordination)
        publication_expiry = coordination.publication_expiry
        publication_active = publication_expiry is not None and publication_expiry > datetime.now(UTC)
        attention_retry = self._validate_finalizer_attention_retry(
            coordination,
            writer,
            finalization_attempt,
            expected_finalization_attention,
        )
        if (
            (coordination.writer is not None and not attention_retry)
            or publication_active
            or coordination.worktree_cleanup_intent is not None
            or coordination.worktree_cleanup is not None
        ):
            _coordination_conflict("change already has an active writer")
        claimed = coordination.model_copy(
            update={
                "writer": writer,
                "finalization_attempt": finalization_attempt or coordination.finalization_attempt,
                "publication_lease": None,
                "finalization_attention": None if attention_retry else coordination.finalization_attention,
                "dirty_worktree_quarantine": (coordination.dirty_worktree_quarantine if attention_retry else None),
            }
        )
        participants = [_replacement(self._state_root, coordination_path, coordination_bytes, claimed)]
        if finalization_attempt is not None:
            frontier_path = self._state_root / "changes" / change_id / "frontier.json"
            frontier_bytes = frontier_path.read_bytes()
            if hashlib.sha256(frontier_bytes).hexdigest() != finalization_attempt.frontier_digest:
                _coordination_conflict("finalization frontier changed before acquisition")
            participants.append(
                ReplacementTransactionParticipant(
                    self._state_root, frontier_path.relative_to(self._state_root), frontier_bytes, frontier_bytes
                )
            )
        try:
            self._commit(
                f"acquire-{change_id}-{writer.claim_id}",
                tuple(participants),
            )
        except TransactionConflictError as exc:
            current = self.show(change_id)
            if current.model_copy(update={"pause_request": None}) == coordination.model_copy(
                update={"pause_request": None}
            ):
                self.require_pause_permits(change_id, "acquire", writer.claim_id, current)
                return self._acquire(
                    change_id,
                    writer,
                    finalization_attempt=finalization_attempt,
                    expected_finalization_attention=expected_finalization_attention,
                )
            msg = "writer coordination changed concurrently"
            raise CoordinationConflictError(msg) from exc
        return claimed

    def release(self, change_id: str, claim_id: str) -> ChangeCoordination:
        """Release one exact writer."""
        self.require_continuation_access(change_id)
        for _attempt in range(_OCC_RETRY_LIMIT):
            coordination_path = self._coordination_path(change_id)
            coordination_bytes = coordination_path.read_bytes()
            coordination = ChangeCoordination.model_validate_json(coordination_bytes)
            self._require_continuation_coordination(coordination)
            if coordination.writer is None:
                return coordination
            if (
                coordination.writer.kind in {"handoff", "finalization-attention"}
                or coordination.builder_handoff is not None
                or coordination.finalization_attention is not None
            ):
                _coordination_conflict("passive workspace custody cannot be released as a worker claim")
            if coordination.writer is None or coordination.writer.claim_id != claim_id:
                _coordination_conflict("writer claim does not own the change workspace")
            if coordination.writer.kind == "finalize":
                _coordination_conflict("finalizer custody requires atomic finalization completion")
            released = coordination.model_copy(update={"writer": None})
            try:
                self._commit(
                    f"release-{change_id}-{claim_id}",
                    (_replacement(self._state_root, coordination_path, coordination_bytes, released),),
                )
            except TransactionConflictError:
                continue
            return released
        return _coordination_conflict("writer coordination remained concurrent")

    def update(
        self,
        coordination: ChangeCoordination,
        *,
        lock: PublicationLock | None = None,
    ) -> ChangeCoordination:
        """OCC-replace one registered per-change record without changing ownership."""
        existing = self.show(coordination.change_id)
        coordination = coordination.model_copy(update={"pause_request": existing.pause_request})
        if existing.publication_lease is not None and existing != coordination:
            _coordination_conflict("workspace update cannot change a reserved publication boundary")
        if lock is not None:
            self._require_publication_lock(lock, coordination.change_id)
            return self._update(coordination)
        with self.publication_lock(coordination.change_id):
            return self._update(coordination)

    def _update(self, coordination: ChangeCoordination) -> ChangeCoordination:
        self.require_continuation_access(coordination.change_id)
        for _attempt in range(_OCC_RETRY_LIMIT):
            path = self._coordination_path(coordination.change_id)
            previous = path.read_bytes()
            existing = ChangeCoordination.model_validate_json(previous)
            # K6: carry the concurrent Pause policy field forward; never erase it.
            coordination = coordination.model_copy(update={"pause_request": existing.pause_request})
            self._validate_update(existing, coordination)
            participant = _replacement(self._state_root, path, previous, coordination)
            try:
                self._commit(f"update-{coordination.change_id}", (participant,))
            except TransactionConflictError as exc:
                current = ChangeCoordination.model_validate_json(path.read_bytes())
                if current.model_copy(update={"pause_request": None}) == existing.model_copy(
                    update={"pause_request": None}
                ):
                    continue
                msg = "change workspace changed concurrently"
                raise CoordinationConflictError(msg) from exc
            return coordination
        return _coordination_conflict("change workspace changed concurrently")

    def _validate_update(self, existing: ChangeCoordination, coordination: ChangeCoordination) -> None:
        # K3: only an intent-creating replacement starts snapshot work; receipt completion and identical intents drain.
        if (
            existing.pause_request is not None
            and coordination.design_package_snapshot_intent is not None
            and coordination.design_package_snapshot_intent != existing.design_package_snapshot_intent
        ):
            raise ChangePauseRequestedError
        self._validate_coordination_ownership_update(existing, coordination)
        if existing.publication_lease is not None and existing != coordination:
            _coordination_conflict("workspace update cannot change a reserved publication boundary")
        baseline_changed = existing.publication_base_head != coordination.publication_base_head
        baseline_recovered_explicitly = (
            existing.publication_base_head is None
            and coordination.publication_base_head is not None
            and coordination.publication_baseline_recovery is not None
        )
        if baseline_changed and not baseline_recovered_explicitly:
            _coordination_conflict("publication baseline requires explicit recovery")
        if (
            existing.publication_baseline_recovery is not None
            and existing.publication_baseline_recovery != coordination.publication_baseline_recovery
        ):
            _coordination_conflict("publication baseline recovery authority cannot be replaced")
        if (
            existing.publication_baseline_recovery is None
            and coordination.publication_baseline_recovery is not None
            and existing.publication_base_head is not None
        ):
            _coordination_conflict("publication baseline recovery authority cannot be added")
        if existing.dirty_worktree_quarantine is not None and (
            existing.dirty_worktree_quarantine != coordination.dirty_worktree_quarantine
        ):
            _coordination_conflict("dirty worktree quarantine authority cannot be replaced")
        if existing.dirty_worktree_quarantine is None and coordination.dirty_worktree_quarantine is not None:
            receipt = coordination.dirty_worktree_quarantine
            writer = coordination.writer
            if writer is None or writer.attempt_id != receipt.attempt_id or writer.claim_id != receipt.claim_id:
                _coordination_conflict("dirty worktree quarantine authority requires matching writer custody")
        self._validate_out_of_band_head_recovery_update(existing, coordination)

    def _validate_coordination_ownership_update(
        self,
        existing: ChangeCoordination,
        replacement: ChangeCoordination,
    ) -> None:
        if existing.builder_handoff is not None and existing != replacement:
            receipt_added = existing.dirty_worktree_quarantine is None and existing == replacement.model_copy(
                update={"dirty_worktree_quarantine": None}
            )
            if not receipt_added:
                _coordination_conflict("workspace update cannot mutate retained Builder handoff custody")
        action = existing.continuation_action
        receipt = replacement.target_sync_receipt
        conflict = replacement.target_sync_conflict
        sync_outcome_matches = action is not None and (
            (
                receipt is not None
                and receipt.operation_id == action.operation_id
                and receipt.expected_target == action.target_head
                and receipt.change_head_before == action.exact_head
                and receipt.merged_head == replacement.last_reviewed_commit
            )
            or (
                conflict is not None
                and conflict.operation_id == action.operation_id
                and conflict.target_head == action.target_head
                and conflict.change_head_before == action.exact_head
                and conflict.change_id == action.change_id
            )
        )
        attention_sync_release = (
            action is not None
            and self.executing_continuation(existing.change_id)
            and action.finished_at is None
            and action == replacement.continuation_action
            and _is_settled_finalizer_attention_sync(existing, action)
            and replacement.writer is None
            and replacement.finalization_attention is None
            and sync_outcome_matches
        )
        ownership_changed = (
            existing.writer != replacement.writer
            or existing.finalization_attention != replacement.finalization_attention
        )
        if (
            (ownership_changed and not attention_sync_release)
            or existing.builder_handoff != replacement.builder_handoff
            or existing.recovery_owner_id != replacement.recovery_owner_id
            or existing.recovery_exclusions != replacement.recovery_exclusions
            or existing.publication_lease != replacement.publication_lease
            or existing.continuation_action != replacement.continuation_action
        ):
            _coordination_conflict("workspace update cannot change ownership")

    @staticmethod
    def _validate_out_of_band_head_recovery_update(
        existing: ChangeCoordination,
        replacement: ChangeCoordination,
    ) -> None:
        if existing.out_of_band_head_recovery is not None and (
            existing.out_of_band_head_recovery != replacement.out_of_band_head_recovery
        ):
            _coordination_conflict("out-of-band head recovery authority cannot be replaced")

    def prepare_reviewed_boundary(
        self,
        coordination: ChangeCoordination,
        reviewed_head: str,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant | None:
        """Prepare a reviewed-boundary replacement for a shared Delivery transaction."""
        self._require_publication_lock(lock, coordination.change_id)
        path = self._coordination_path(coordination.change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        if existing != coordination:
            _coordination_conflict("change workspace changed during finalization preparation")
        if existing.builder_handoff is not None:
            _coordination_conflict("finalization cannot advance a retained Builder handoff boundary")
        if existing.last_reviewed_commit == reviewed_head:
            return None
        updated = existing.model_copy(update={"last_reviewed_commit": reviewed_head})
        return _replacement(self._state_root, path, previous, updated)

    def prepare_finalization_completion(
        self,
        coordination: ChangeCoordination,
        reviewed_head: str,
        finished_at: str,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant:
        """Join custody release and reviewed-boundary advancement to the receipt transaction."""
        self._require_publication_lock(lock, coordination.change_id)
        path = self._coordination_path(coordination.change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        attempt = existing.finalization_attempt
        if existing != coordination or attempt is None or attempt.finished_at is not None:
            _coordination_conflict("finalization custody changed during completion")
        updated = existing.model_copy(
            update={
                "writer": None,
                "last_reviewed_commit": reviewed_head,
                "finalization_attempt": attempt.model_copy(update={"finished_at": finished_at}),
            }
        )
        return _replacement(self._state_root, path, previous, updated)

    def prepare_finalization_attention(
        self,
        change_id: str,
        writer: ChangeWriter,
        attention: ChangeFinalizationAttention,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant:
        """Prepare one exact normal-return failure as passive, receipt-backed custody."""
        self._require_publication_lock(lock, change_id)
        self.require_no_pending_recovery(change_id)
        path = self._coordination_path(change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        attempt = existing.finalization_attempt
        if (
            existing.writer != writer
            or writer.kind != "finalize"
            or attempt is None
            or attempt.writer != writer
            or attempt.finished_at is not None
            or attention.change_id != change_id
            or attention.attempt_id != writer.attempt_id
        ):
            _coordination_conflict("Finalizer settlement does not match the exact active workspace attempt")
        updated = existing.model_copy(
            update={
                "writer": writer.model_copy(update={"kind": "finalization-attention"}),
                "finalization_attempt": attempt.model_copy(update={"finished_at": attention.finished_at}),
                "finalization_attention": attention,
            }
        )
        try:
            ChangeCoordination.model_validate(updated.model_dump(mode="python"))
        except ValidationError as exc:
            _coordination_conflict("Finalizer settlement does not form valid passive workspace custody")
            raise AssertionError from exc
        return _replacement(self._state_root, path, previous, updated)

    def prepare_runtime_custody_guard(
        self,
        change_id: str,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
        operation: str | None = None,
        mutation_class: Literal["completion", "owner-drain", "pause-gated"] = "pause-gated",
    ) -> ReplacementTransactionParticipant:
        """Fence a runtime mutation against concurrent finalizer acquisition and Pause (K7)."""
        self.require_continuation_access(change_id)
        path = self._coordination_path(change_id)
        coordination, previous = self._read_coordination(change_id)
        self._require_continuation_coordination(coordination)
        # K7: owner-drain names need their K2 token; a pause-gated name only a started operator's own token.
        permit_kind: DrainPermitKind = "mutation" if mutation_class == "owner-drain" else "operator"
        if (
            coordination.pause_request is not None
            and mutation_class != "completion"
            and (operation is None or not self.drain_permits(change_id, permit_kind, operation))
        ):
            raise ChangePauseRequestedError
        attempt = coordination.finalization_attempt
        if expected_finalization_attention is None and (
            (coordination.writer is not None and coordination.writer.kind == "finalize")
            or coordination.finalization_attention is not None
        ):
            _coordination_conflict("mutation cannot overlap active or retained Finalizer custody")
        if expected_finalization_attention is not None and (
            coordination.finalization_attention != expected_finalization_attention
            or attempt is None
            or attempt.finished_at != expected_finalization_attention.finished_at
            or coordination.writer != attempt.writer.model_copy(update={"kind": "finalization-attention"})
        ):
            _coordination_conflict("finalization attention changed during a passive Change intent")
        return ReplacementTransactionParticipant(
            self._state_root, path.relative_to(self._state_root), previous, previous
        )

    def reserve_publication(
        self,
        change_id: str,
        lease: PublicationLease,
        lock: PublicationLock,
        *,
        now: str,
    ) -> ChangeCoordination:
        """Reserve one idle Change for an exact replayable publication operation."""
        self._require_publication_lock(lock, change_id)
        self.require_continuation_access(change_id)
        now_value = self._publication_timestamp(now)
        expires_value = self._publication_timestamp(lease.expires_at)
        if expires_value <= now_value:
            msg = "publication reservation expiry must be in the future"
            raise ValueError(msg)
        if (expires_value - now_value).total_seconds() > _PUBLICATION_LEASE_MAX_SECONDS:
            msg = "publication reservation exceeds the maximum duration"
            raise ValueError(msg)
        path = self._coordination_path(change_id)
        previous = path.read_bytes()
        coordination = ChangeCoordination.model_validate_json(previous)
        self.require_pause_permits(change_id, "reserve", lease.operation_id, coordination)
        existing_lease = coordination.publication_lease
        existing_expiry = coordination.publication_expiry
        same_owner = existing_lease is not None and existing_lease.owner_id == lease.owner_id
        expired = existing_expiry is not None and existing_expiry <= now_value
        if (
            coordination.writer is not None
            or coordination.worktree_cleanup_intent is not None
            or coordination.worktree_cleanup is not None
            or (existing_lease is not None and not same_owner and not expired)
        ):
            _coordination_conflict("change already has active ownership")
        reserved = coordination.model_copy(update={"publication_lease": lease})
        operation_digest = hashlib.sha256(lease.operation_id.encode()).hexdigest()
        try:
            self._commit(
                f"reserve-publication-{change_id}-{operation_digest}",
                (_replacement(self._state_root, path, previous, reserved),),
            )
        except TransactionConflictError as exc:
            current = self.show(change_id)
            if current.model_copy(update={"pause_request": None}) == coordination.model_copy(
                update={"pause_request": None}
            ):
                self.require_pause_permits(change_id, "reserve", lease.operation_id, current)
                return self.reserve_publication(change_id, lease, lock, now=now)
            msg = "change ownership changed during publication reservation"
            raise CoordinationConflictError(msg) from exc
        self._grant_committed_lease(change_id, lease.operation_id)
        return reserved

    def release_publication(
        self,
        change_id: str,
        operation_id: str,
        owner_id: str,
        lock: PublicationLock,
    ) -> ChangeCoordination:
        """Release one exact publication reservation without changing reviewed state."""
        self._require_publication_lock(lock, change_id)
        self._validate_publication_operation_id(operation_id)
        if not owner_id:
            msg = "publication owner identity is invalid"
            raise ValueError(msg)
        for _attempt in range(_OCC_RETRY_LIMIT):
            path = self._coordination_path(change_id)
            previous = path.read_bytes()
            coordination = ChangeCoordination.model_validate_json(previous)
            lease = coordination.publication_lease
            if lease is None or lease.operation_id != operation_id or lease.owner_id != owner_id:
                _coordination_conflict("publication operation does not own the change workspace")
            released = coordination.model_copy(update={"publication_lease": None})
            operation_digest = hashlib.sha256(operation_id.encode()).hexdigest()
            try:
                self._commit(
                    f"release-publication-{change_id}-{operation_digest}",
                    (_replacement(self._state_root, path, previous, released),),
                )
            except TransactionConflictError:
                continue
            return released
        return _coordination_conflict("publication ownership remained concurrent")

    @staticmethod
    def _validate_publication_operation_id(operation_id: str) -> None:
        if _PUBLICATION_OPERATION_PATTERN.fullmatch(operation_id) is None:
            msg = "publication operation identity is invalid"
            raise ValueError(msg)

    def _require_publication_lock(self, lock: PublicationLock, change_id: str) -> None:
        if not lock.owns(self, change_id):
            msg = "active publication lock does not own the Change"
            raise ValueError(msg)

    @staticmethod
    def _publication_timestamp(value: str) -> datetime:
        return _publication_timestamp(value)

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

    def _prepare_builder_handoff(
        self,
        coordination: ChangeCoordination,
        handoff: ChangeBuilderHandoff,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant:
        """Prepare the exact build-writer replacement for a shared settlement transaction."""
        self._require_publication_lock(lock, coordination.change_id)
        self.require_no_pending_recovery(coordination.change_id)
        path = self._coordination_path(coordination.change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        if existing != coordination or existing.builder_handoff is not None:
            _coordination_conflict("Change workspace changed during Builder handoff preparation")
        if (
            existing.writer is None
            or existing.writer != handoff.original_writer
            or existing.writer.kind != "build"
            or handoff.change_id != coordination.change_id
            or handoff.last_reviewed_commit != existing.last_reviewed_commit
        ):
            _coordination_conflict("Builder handoff does not match the exact active build writer")
        updated = existing.model_copy(
            update={
                "writer": existing.writer.model_copy(update={"kind": "handoff"}),
                "builder_handoff": handoff,
            }
        )
        return _replacement(self._state_root, path, previous, updated)

    def _prepare_builder_handoff_acquisition(
        self,
        change_id: str,
        writer: ChangeWriter,
        handoff: ChangeBuilderHandoff,
        metadata: BuilderHandoffMetadata,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant:
        """Prepare exact handoff consumption for a shared claim-activation transaction."""
        self._require_publication_lock(lock, change_id)
        self.require_no_pending_recovery(change_id)
        coordination, previous = self._read_coordination(change_id)
        retained = coordination.builder_handoff
        expected_handoff_writer = (
            None if retained is None else retained.original_writer.model_copy(update={"kind": "handoff"})
        )
        if (
            retained != handoff
            or coordination.writer != expected_handoff_writer
            or writer.kind != "build"
            or writer.attempt_id == handoff.original_writer.attempt_id
            or writer.claim_id == handoff.original_writer.claim_id
            or metadata.change_id != change_id
            or metadata.branch != coordination.branch
            or metadata.worktree_path != coordination.worktree_path
            or metadata.last_reviewed_commit != handoff.last_reviewed_commit
            or coordination.last_reviewed_commit != handoff.last_reviewed_commit
            or coordination.publication_lease is not None
            or coordination.worktree_cleanup_intent is not None
            or coordination.worktree_cleanup is not None
            or coordination.dirty_worktree_quarantine is not None
        ):
            _coordination_conflict("Builder handoff does not match the exact settlement, task, and workspace")
        claimed = coordination.model_copy(update={"writer": writer, "builder_handoff": None})
        return _replacement(self._state_root, self._coordination_path(change_id), previous, claimed)

    def _prepare_design_return_release(
        self,
        change_id: str,
        handoff: ChangeBuilderHandoff,
        lock: PublicationLock,
        *,
        release_quarantine: bool = False,
    ) -> ReplacementTransactionParticipant:
        """Prepare the exact retained Design-return handoff release for its runtime transaction (N04 §1.7).

        ``release_quarantine`` (N13 target sync) also drops the capture receipt; its refs stay.
        """
        self._require_publication_lock(lock, change_id)
        self.require_no_pending_recovery(change_id)
        coordination, previous = self._read_coordination(change_id)
        if coordination.builder_handoff != handoff or coordination.writer != handoff.original_writer.model_copy(
            update={"kind": "handoff"}
        ):
            _coordination_conflict("Design return release does not match its retained Builder handoff")
        update: dict[str, object] = {"writer": None, "builder_handoff": None}
        if release_quarantine:
            update["dirty_worktree_quarantine"] = None
        released = coordination.model_copy(update=update)
        return _replacement(self._state_root, self._coordination_path(change_id), previous, released)

    def release_finalization_attention(
        self, change_id: str, attention: ChangeFinalizationAttention, lock: PublicationLock
    ) -> ChangeCoordination:
        """Release one exact clean, settled Finalizer attention for a paused requirement revision."""
        self._require_publication_lock(lock, change_id)
        self.require_no_pending_recovery(change_id)
        coordination, previous = self._read_coordination(change_id)
        attempt = coordination.finalization_attempt
        if (
            coordination.finalization_attention != attention
            or attention.workspace_paths
            or attempt is None
            or coordination.writer != attempt.writer.model_copy(update={"kind": "finalization-attention"})
            or coordination.dirty_worktree_quarantine is not None
        ):
            _coordination_conflict("revision release requires its exact clean, settled Finalizer attention")
        released = coordination.model_copy(update={"writer": None, "finalization_attention": None})
        self._commit(
            f"finalization-attention-release-{change_id}-{attention.attempt_id}",
            (_replacement(self._state_root, self._coordination_path(change_id), previous, released),),
        )
        return released
