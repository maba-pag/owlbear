"""Frontier, binding, checkpoint and receipt helpers for the Delivery runtime."""

from __future__ import annotations

import hashlib
import json
from contextvars import ContextVar
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery.runtime_models import (
    _FRONTIER_SCHEMA_VERSION,
    _LEGACY_FRONTIER_SCHEMA_VERSION,
    _MAX_BUILDER_HANDOFF_CHANGE_INTENT_RECEIPTS,
    _MAX_BUILDER_HANDOFF_CHANGE_INTENTS,
    _NORMAL_CHANGE_MUTATIONS,
    _READABLE_LEGACY_FRONTIER_SCHEMA_VERSION,
    _STAGE_ORDER,
    DeliveryBuilderHandoffContext,
    DeliveryChangeDisposition,
    DeliveryChangeDispositionConflictError,
    DeliveryChangeDispositionKind,
    DeliveryChangePublicationIdentity,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryFrontier,
    DeliveryPendingCheckpoint,
    DeliveryRequest,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    PrepareCompletedOutcomeRepair,
    _model_content,
    _normalize_frontier,
    _reference,
)
from owlbear_delivery.runtime_receipts import (
    _DeliveryAttemptGrantReceipt,
    _DeliveryBuilderAttemptGrantReceipt,
    _DeliveryBuilderHandoffChangeIntentHead,
    _DeliveryBuilderHandoffChangeIntentReceipt,
    _DeliveryBuilderRequestResolutionReceipt,
)

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery.draft_pull_request import (
        PublicationPullRequestObservationReceipt,
        PullRequestReadyReceipt,
    )
    from owlbear_delivery.target_contract import DeliveryContract


def _find_binding(frontier: DeliveryFrontier, outcome_id: str) -> OutcomeAuthorityBinding:
    try:
        return next(binding for binding in frontier.bindings if binding.outcome_id == outcome_id)
    except StopIteration as exc:
        _reference(f"Delivery outcome is absent: {outcome_id}", exc)


# The writer name the next custody-guarded frontier replacement classifies for Pause (K7).
_DECLARED_MUTATION: ContextVar[str | None] = ContextVar("declared_delivery_mutation", default=None)


def _declare_mutation(operation: str) -> None:
    _DECLARED_MUTATION.set(operation)


def _declared_mutation() -> str | None:
    return _DECLARED_MUTATION.get()


def _consume_declared_mutation() -> str | None:
    operation = _DECLARED_MUTATION.get()
    _DECLARED_MUTATION.set(None)
    return operation


def _require_change_mutable(
    frontier: DeliveryFrontier,
    operation: str,
    *,
    allow_attention: bool = False,
) -> None:
    if operation not in _NORMAL_CHANGE_MUTATIONS:
        message = f"unregistered Delivery Change mutation: {operation}"
        raise ValueError(message)
    _declare_mutation(operation)
    if frontier.change_completion is not None:
        _conflict("completed Delivery Change is terminal")
    if frontier.change_abandonment is not None:
        _conflict("abandoned Delivery Change is terminal")
    if frontier.change_deferral is not None and operation not in {
        "resume_change",
        "abandon_change",
        "release_design_return",
    }:
        _conflict("paused Delivery Change requires resumption before mutation")
    if (
        frontier.change_disposition is not None
        and not allow_attention
        and operation
        not in {
            "defer_change",
            "resume_change",
            "abandon_change",
            "record_publication_successor",
        }
    ):
        _conflict("Delivery Change requires attention resolution before mutation")


def _require_no_active_change_claim(frontier: DeliveryFrontier, operation: str) -> None:
    has_outcome_claim = any(binding.active_claim is not None for binding in frontier.bindings)
    if frontier.integration_repair_claim is not None:
        _conflict(f"{operation} cannot overlap an active Integration repair claim")
    if has_outcome_claim:
        _conflict(f"{operation} cannot overlap an active mutation claim")


def _require_no_review_repair(frontier: DeliveryFrontier, operation: str) -> None:
    """Reject head mutations while external review repair owns the Change boundary."""
    invalidation = frontier.finalization_invalidation
    if invalidation is not None and invalidation.reason == "review-repair":
        _conflict(f"{operation} cannot overlap an active review repair")


def is_acceptance_waiting_observation(
    observation: PublicationPullRequestObservationReceipt,
) -> bool:
    """Return whether a bound pull request is normally waiting for a user merge."""
    snapshot = observation.snapshot
    return snapshot.state == "open" and not snapshot.merged


def parse_stored_delivery_frontier(content: bytes) -> DeliveryFrontier:
    """Parse one frontier strictly at its stored version; schema 17 reads as its registered 18 form."""
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise TypeError
    schema_version = payload.get("schema_version")
    if schema_version == _LEGACY_FRONTIER_SCHEMA_VERSION and type(schema_version) is int:
        content = json.dumps({**payload, "schema_version": _READABLE_LEGACY_FRONTIER_SCHEMA_VERSION}).encode()
    elif type(schema_version) is not int or schema_version not in {
        _READABLE_LEGACY_FRONTIER_SCHEMA_VERSION,
        _FRONTIER_SCHEMA_VERSION,
    }:
        raise ValueError
    return DeliveryFrontier.model_validate_json(content, strict=True)


def normalize_frontier(frontier: DeliveryFrontier) -> DeliveryFrontier:
    """Apply the registered 18 -> 19 representation change: the schema version only (I2)."""
    return _normalize_frontier(frontier)


def stored_frontier_version(content: bytes) -> int:
    """Return the verified stored schema version of frontier bytes (17 for an unmigrated record)."""
    payload = json.loads(content)
    version = payload.get("schema_version") if isinstance(payload, dict) else None
    if type(version) is not int:
        raise ValueError
    return version


def parse_delivery_frontier(
    content: bytes,
) -> tuple[DeliveryFrontier, bytes]:
    """Return the writable schema-19 frontier and its stored bytes.

    Schema 19 yields canonical bytes; schema 18 yields the verified file bytes, never re-serialized;
    schema 17 yields the canonical bytes of its registered 18 rewrite.
    """
    stored = parse_stored_delivery_frontier(content)
    if stored_frontier_version(content) == _READABLE_LEGACY_FRONTIER_SCHEMA_VERSION:
        return normalize_frontier(stored), content
    return normalize_frontier(stored), _model_content(stored)


def repair_missing_request_provenance(  # noqa: C901 - narrow structural migration validates each legacy layer.
    content: bytes,
    request_id: str,
) -> tuple[DeliveryFrontier, bytes]:
    """Repair only one legacy free-text request lacking explicit confirmation."""
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise TypeError
    bindings = payload.get("bindings")
    if not isinstance(bindings, list):
        _reference("Delivery frontier bindings are invalid")
    missing: list[tuple[dict[str, object], dict[str, object]]] = []
    for binding in bindings:
        if not isinstance(binding, dict):
            _reference("Delivery frontier binding is invalid")
        requests = binding.get("requests")
        if not isinstance(requests, list):
            _reference("Delivery frontier requests are invalid")
        for request in requests:
            if not isinstance(request, dict):
                _reference("Delivery frontier request is invalid")
            resolution = request.get("resolution")
            if not isinstance(resolution, dict):
                continue
            response_text = resolution.get("response_text")
            if isinstance(response_text, str) and response_text.strip() and resolution.get("provenance") is None:
                missing.append((request, resolution))
    if len(missing) != 1 or missing[0][0].get("request_id") != request_id:
        _reference("frontier contains an unsupported request-provenance defect")
    missing[0][1]["provenance"] = "user-confirmed"
    repaired_payload = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    repaired = parse_delivery_frontier(repaired_payload)[0]
    return repaired, _model_content(repaired)


def _find_request(frontier: DeliveryFrontier, request_id: str) -> tuple[OutcomeAuthorityBinding, DeliveryRequest]:
    matches = [
        (binding, request)
        for binding in frontier.bindings
        for request in binding.requests
        if request.request_id == request_id
    ]
    if len(matches) != 1:
        _reference(f"Delivery request is absent or ambiguous: {request_id}")
    return matches[0]


def _builder_request_resolution_receipt_path(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> Path:
    return (
        runtime_root
        / "changes"
        / change_id
        / "builder-request-resolution-receipts"
        / f"{builder_handoff_context.settlement_id}.json"
    )


def _builder_handoff_change_intent_directory(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> Path:
    return (
        runtime_root
        / "changes"
        / change_id
        / "builder-handoff-change-intent-receipts"
        / builder_handoff_context.settlement_id
    )


def _builder_handoff_change_intent_head_path(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> Path:
    return _builder_handoff_change_intent_directory(runtime_root, change_id, builder_handoff_context) / "head.json"


def _read_builder_handoff_change_intent_receipts(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...]:
    """Read only the bounded receipt chain addressed by one known Builder handoff."""
    root = runtime_root.resolve()
    directory = _builder_handoff_change_intent_directory(root, change_id, builder_handoff_context)
    head = _read_builder_handoff_change_intent_head(root, change_id, builder_handoff_context)
    if head is None:
        return ()

    reverse_chain: list[_DeliveryBuilderHandoffChangeIntentReceipt] = []
    receipt_id: str | None = head.latest_receipt_id
    for sequence in range(head.sequence, 0, -1):
        if receipt_id is None:
            _reference("Builder handoff change-intent receipt chain is incomplete")
        receipt = _read_builder_handoff_change_intent_receipt(
            directory,
            change_id,
            builder_handoff_context,
            receipt_id,
        )
        if receipt.sequence != sequence:
            _reference("Builder handoff change-intent receipt chain is invalid")
        reverse_chain.append(receipt)
        receipt_id = receipt.previous_receipt_id
        if sequence > 1 and receipt_id is None:
            _reference("Builder handoff change-intent receipt chain is incomplete")
    if receipt_id is not None:
        _reference("Builder handoff change-intent receipt chain has an unknown predecessor")

    chain = tuple(reversed(reverse_chain))
    _validate_builder_handoff_change_intent_chain(chain, head)
    return chain


def _read_builder_handoff_change_intent_head(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> _DeliveryBuilderHandoffChangeIntentHead | None:
    head_path = _builder_handoff_change_intent_head_path(runtime_root, change_id, builder_handoff_context)
    change_root = runtime_root / "changes" / change_id
    if any(path.is_symlink() for path in (runtime_root / "changes", change_root, head_path.parent, head_path)):
        _reference("Builder handoff change-intent receipt path is unsafe")
    try:
        content = head_path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        _reference("Builder handoff change-intent head is unavailable", exc)
    try:
        head = _DeliveryBuilderHandoffChangeIntentHead.model_validate_json(content, strict=True)
    except (TypeError, ValueError) as exc:
        _reference("Builder handoff change-intent head is invalid", exc)
    if (
        content != _model_content(head)
        or head.change_id != change_id
        or head.builder_handoff_context != builder_handoff_context
    ):
        _reference("Builder handoff change-intent head does not match its known settlement")
    return head


def _read_builder_handoff_change_intent_receipt(
    directory: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
    receipt_id: str,
) -> _DeliveryBuilderHandoffChangeIntentReceipt:
    receipt_path = directory / f"{receipt_id}.json"
    if receipt_path.is_symlink():
        _reference("Builder handoff change-intent receipt path is unsafe")
    try:
        content = receipt_path.read_bytes()
    except OSError as exc:
        _reference("Builder handoff change-intent receipt is unavailable", exc)
    try:
        receipt = _DeliveryBuilderHandoffChangeIntentReceipt.model_validate_json(content, strict=True)
    except (TypeError, ValueError) as exc:
        _reference("Builder handoff change-intent receipt is invalid", exc)
    if (
        content != _model_content(receipt)
        or receipt.receipt_id != receipt_id
        or receipt.change_id != change_id
        or receipt.builder_handoff_context != builder_handoff_context
    ):
        _reference("Builder handoff change-intent receipt chain is invalid")
    return receipt


def _validate_builder_handoff_change_intent_chain(
    chain: tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...],
    head: _DeliveryBuilderHandoffChangeIntentHead,
) -> None:
    if not chain or (
        chain[-1].receipt_id != head.latest_receipt_id
        or chain[-1].sequence != head.sequence
        or chain[-1].outcome_id != head.outcome_id
    ):
        _reference("Builder handoff change-intent head does not identify the end of its receipt chain")
    if len(chain) > _MAX_BUILDER_HANDOFF_CHANGE_INTENTS and (
        len(chain) != _MAX_BUILDER_HANDOFF_CHANGE_INTENT_RECEIPTS or chain[-1].action != "abandon"
    ):
        _reference("Builder handoff change-intent receipt chain exceeds its supported limit")
    for previous, current in pairwise(chain):
        if current.previous_receipt_id != previous.receipt_id or current.sequence != previous.sequence + 1:
            _reference("Builder handoff change-intent receipt chain is invalid")


def _read_builder_request_resolution_receipt(
    runtime_root: Path,
    change_id: str,
    request_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> _DeliveryBuilderRequestResolutionReceipt:
    """Read one exact local Builder answer without constructing a DeliveryRuntime."""
    receipt_path = _builder_request_resolution_receipt_path(runtime_root, change_id, builder_handoff_context)
    change_root = runtime_root / "changes" / change_id
    receipt_directory = receipt_path.parent
    if any(path.is_symlink() for path in (runtime_root / "changes", change_root, receipt_directory, receipt_path)):
        _reference("Builder request resolution receipt path is unsafe")
    try:
        content = receipt_path.read_bytes()
    except OSError as exc:
        _reference("Builder request resolution receipt is unavailable", exc)
    try:
        receipt = _DeliveryBuilderRequestResolutionReceipt.model_validate_json(content, strict=True)
    except (TypeError, ValueError) as exc:
        _reference("Builder request resolution receipt is invalid", exc)
    if (
        receipt.change_id != change_id
        or receipt.request_id != request_id
        or receipt.builder_handoff_context != builder_handoff_context
    ):
        _reference("Builder request resolution receipt does not match its exact handoff")
    return receipt


def _builder_attempt_grant_receipt_path(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> Path:
    return (
        runtime_root
        / "changes"
        / change_id
        / "builder-attempt-grant-receipts"
        / f"{builder_handoff_context.settlement_id}.json"
    )


def _read_builder_attempt_grant_receipt(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> _DeliveryBuilderAttemptGrantReceipt | None:
    """Read one exact user attempt grant, or ``None`` when this handoff has none."""
    receipt_path = _builder_attempt_grant_receipt_path(runtime_root, change_id, builder_handoff_context)
    change_root = runtime_root / "changes" / change_id
    if any(path.is_symlink() for path in (runtime_root / "changes", change_root, receipt_path.parent, receipt_path)):
        _reference("Builder attempt grant receipt path is unsafe")
    try:
        content = receipt_path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        _reference("Builder attempt grant receipt is unavailable", exc)
    try:
        receipt = _DeliveryBuilderAttemptGrantReceipt.model_validate_json(content, strict=True)
    except (TypeError, ValueError) as exc:
        _reference("Builder attempt grant receipt is invalid", exc)
    if (
        content != _model_content(receipt)
        or receipt.change_id != change_id
        or receipt.builder_handoff_context != builder_handoff_context
    ):
        _reference("Builder attempt grant receipt does not match its exact handoff")
    return receipt


def _attempt_grant_receipt_path(runtime_root: Path, change_id: str, attempt_id: str) -> Path:
    name = hashlib.sha256(attempt_id.encode()).hexdigest()
    return runtime_root / "changes" / change_id / "attempt-grant-receipts" / f"{name}.json"


def _read_attempt_grant_receipt(
    runtime_root: Path,
    change_id: str,
    attempt_id: str,
) -> _DeliveryAttemptGrantReceipt | None:
    """Read the user's grant after one exact exhausted Planner or Finalizer attempt, or ``None``."""
    receipt_path = _attempt_grant_receipt_path(runtime_root, change_id, attempt_id)
    change_root = runtime_root / "changes" / change_id
    if any(path.is_symlink() for path in (runtime_root / "changes", change_root, receipt_path.parent, receipt_path)):
        _reference("attempt grant receipt path is unsafe")
    try:
        content = receipt_path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        _reference("attempt grant receipt is unavailable", exc)
    try:
        receipt = _DeliveryAttemptGrantReceipt.model_validate_json(content, strict=True)
    except (TypeError, ValueError) as exc:
        _reference("attempt grant receipt is invalid", exc)
    if content != _model_content(receipt) or receipt.change_id != change_id or receipt.attempt_id != attempt_id:
        _reference("attempt grant receipt does not match its exact attempt")
    return receipt


def _replace_binding(
    frontier: DeliveryFrontier,
    previous: OutcomeAuthorityBinding,
    replacement: OutcomeAuthorityBinding,
) -> DeliveryFrontier:
    return frontier.model_copy(
        update={"bindings": tuple(replacement if item == previous else item for item in frontier.bindings)}
    )


def _queue_promoted_result_checkpoint(
    replacement: DeliveryFrontier,
    previous: DeliveryFrontier,
    binding: OutcomeAuthorityBinding,
    updated: OutcomeAuthorityBinding,
) -> DeliveryFrontier:
    candidate = binding.result_candidate
    if candidate is None:
        _conflict("promoted Task checkpoint requires the published result candidate")
    triggers: list[DeliveryCheckpointTrigger] = []
    pending = previous.pending_checkpoint
    if not any(item.results for item in previous.bindings) and not _has_checkpoint_trigger(
        pending,
        DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
    ):
        triggers.append(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
            )
        )
    elif pending is None and updated.stage != DeliveryStage.COMPLETED:
        triggers.append(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_TASK,
            )
        )
    if updated.stage == DeliveryStage.COMPLETED:
        triggers.append(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id=binding.outcome_id,
            )
        )
    if pending is None and not triggers:
        return replacement
    combined = (*(() if pending is None else pending.triggers), *triggers)
    return replacement.model_copy(
        update={
            "pending_checkpoint": _checkpoint_with_head(
                pending,
                candidate.result.completed_commit,
                tuple(dict.fromkeys(combined)),
            )
        }
    )


def _queue_finalization_checkpoint(frontier: DeliveryFrontier, exact_head: str) -> DeliveryFrontier:
    pending = frontier.pending_checkpoint
    trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FINALIZATION)
    combined = (*(() if pending is None else pending.triggers), trigger)
    return frontier.model_copy(
        update={"pending_checkpoint": _checkpoint_with_head(pending, exact_head, tuple(dict.fromkeys(combined)))}
    )


def _invalidate_finalization_checkpoint(
    pending: DeliveryPendingCheckpoint | None,
) -> DeliveryPendingCheckpoint | None:
    if pending is None:
        return None
    retained = tuple(
        trigger for trigger in pending.triggers if trigger.kind != DeliveryCheckpointTriggerKind.FINALIZATION
    )
    if not retained:
        return None
    return _checkpoint_with_head(pending, None, retained)


def _has_checkpoint_trigger(
    pending: DeliveryPendingCheckpoint | None,
    kind: DeliveryCheckpointTriggerKind,
) -> bool:
    return pending is not None and any(trigger.kind == kind for trigger in pending.triggers)


def invalidate_checkpoint_publication(
    pending: DeliveryPendingCheckpoint | None,
    invalidated_outcome_ids: set[str],
) -> DeliveryPendingCheckpoint | None:
    """Retain valid obligations while removing their invalidated publication head."""
    if pending is None:
        return None
    if not invalidated_outcome_ids:
        return pending
    retained = tuple(
        trigger
        for trigger in pending.triggers
        if trigger.outcome_id is None or trigger.outcome_id not in invalidated_outcome_ids
    )
    if not retained:
        return None
    return _checkpoint_with_head(pending, None, retained)


def _checkpoint_with_head(
    previous: DeliveryPendingCheckpoint | None,
    head: str | None,
    triggers: tuple[DeliveryCheckpointTrigger, ...] | None = None,
) -> DeliveryPendingCheckpoint:
    """Create or re-anchor one checkpoint, retaining retry metadata only for the same head."""
    next_triggers = triggers if triggers is not None else (() if previous is None else previous.triggers)
    if previous is not None and previous.head == head:
        return previous.model_copy(update={"triggers": next_triggers})
    return DeliveryPendingCheckpoint(head=head, triggers=next_triggers)


def _require_claim(binding: OutcomeAuthorityBinding, claim_id: str) -> None:
    if binding.active_claim_id != claim_id:
        _conflict("transition does not match the active claim")


def _retry_fingerprint(
    change_id: str,
    outcome_id: str,
    worker_role: DeliveryWorkerRole,
    failure_code: str,
) -> str:
    """Return a stable fingerprint for one repeated worker failure class."""
    payload = f"{change_id}\0{outcome_id}\0{worker_role.value}\0{failure_code.casefold()}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _reset_binding(binding: OutcomeAuthorityBinding, stage: DeliveryStage) -> OutcomeAuthorityBinding:
    return binding.model_copy(
        update={
            "stage": stage,
            "tasks": (),
            "results": (),
            "active_claim": None,
            "output": None,
            "candidate": None,
            "result_candidate": None,
            "return_context": None,
            "recovery_attention": None,
            "block": None,
            "requests": (),
        }
    )


def _completed_dependent_closure(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    outcome_id: str,
) -> set[str]:
    bindings = {binding.outcome_id: binding for binding in frontier.bindings}
    invalidated = {outcome_id}
    while True:
        expanded = invalidated | {
            outcome.outcome_id
            for outcome in contract.outcomes
            if bindings[outcome.outcome_id].stage == DeliveryStage.COMPLETED
            if set(outcome.dependency_ids) & invalidated
        }
        if expanded == invalidated:
            return invalidated
        invalidated = expanded


def _administrative_move_closure(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    outcome_id: str,
    target: DeliveryStage,
) -> tuple[str, ...]:
    if frontier.integration_repair_claim is not None:
        _conflict("administrative movement cannot overlap an active Integration repair claim")
    binding = _find_binding(frontier, outcome_id)
    if _STAGE_ORDER[target] >= _STAGE_ORDER[binding.stage]:
        _conflict("administrative movement must target an earlier stage")
    invalidated = _completed_dependent_closure(contract, frontier, outcome_id)
    return tuple(item.outcome_id for item in frontier.bindings if item.outcome_id in invalidated)


def _pull_request_identity(ready: PullRequestReadyReceipt | None) -> DeliveryChangePublicationIdentity | None:
    if ready is None:
        return None
    return DeliveryChangePublicationIdentity(
        change_id=ready.change_id,
        repository=ready.repository,
        number=ready.number,
        node_id=ready.node_id,
        head_sha=ready.head_sha,
    )


def _attention_conflict(message: str) -> None:
    raise DeliveryChangeDispositionConflictError(message)


def _completed_outcome_repair_id(
    change_id: str,
    request: PrepareCompletedOutcomeRepair,
    source_digest: str,
) -> str:
    """Derive one stable repair identity from admitted lineage and evidence."""
    material = (
        f"{change_id}\0{request.outcome_id}\0{request.owning_task_id}\0{source_digest}\0"
        f"{request.episode_id}\0{request.attempt_id}\0{request.defect_code}\0{request.finding_boundary}\0"
        f"{request.original_action_id}\0{request.preservation_id}\0{request.expected_frontier_digest}"
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _target_sync_operation_id(disposition: DeliveryChangeDisposition) -> str | None:
    prefix = "target-sync-operation:"
    for diagnostic in disposition.diagnostics:
        if diagnostic.startswith(prefix):
            return diagnostic.removeprefix(prefix)
    return None


def _require_target_sync_attention(
    frontier: DeliveryFrontier,
    expected_disposition_id: str,
    operation_id: str,
) -> DeliveryChangeDisposition:
    current = frontier.change_disposition
    if current is None:
        _attention_conflict("target synchronization attention is absent or already resolved")
    if current.disposition_id != expected_disposition_id:
        _attention_conflict("target synchronization attention identity is stale")
    if current.kind != DeliveryChangeDispositionKind.PUBLICATION_ATTENTION:
        _attention_conflict("target synchronization attention has the wrong disposition kind")
    if _target_sync_operation_id(current) != operation_id:
        _attention_conflict("target synchronization operation identity is stale")
    return current


def _conflict(message: str) -> None:
    raise DeliveryRuntimeConflictError(message)
