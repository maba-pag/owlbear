"""Bounded projections of current completed Delivery records."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery.acceptance import (
    CompletionPullRequestIdentity,
    CompletionReceiptBundle,
    CompletionReceiptConflictError,
    CompletionReceiptStore,
)
from owlbear_delivery.change_workspace import ChangeCoordination
from owlbear_delivery.delivery_runtime import DeliveryChangeStage, DeliveryFrontier, parse_delivery_frontier
from owlbear_delivery.identities import ChangeId, Digest
from owlbear_delivery.target_contract import DeliveryContract

if TYPE_CHECKING:
    from pathlib import Path

_MAX_PAGE_SIZE = 100
_SAFE_CHANGE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class _CompletedHistoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CompletedHistoryDiagnosticCode(StrEnum):
    """Stable failure categories for read-only completed-history queries."""

    MISSING = "completed-history-missing"
    MALFORMED = "completed-history-malformed"
    STALE = "completed-history-stale"
    RECEIPT_SET_ADVANCED = "completed-history-receipt-set-advanced"


class CompletedHistoryDiagnostic(_CompletedHistoryModel):
    """Bounded named evidence for one failed catalog query."""

    code: CompletedHistoryDiagnosticCode
    detail: str = Field(min_length=1)
    change_id: str | None = None
    completion_id: str | None = None


class CompletedHistoryError(RuntimeError):
    """A completed-history query failed without mutating catalog authority."""

    def __init__(self, diagnostic: CompletedHistoryDiagnostic) -> None:
        super().__init__(diagnostic.detail)
        self.diagnostic = diagnostic


class CompletedHistoryMissingError(CompletedHistoryError):
    """The requested completion is absent."""


class CompletedHistoryMalformedError(CompletedHistoryError):
    """Persisted completed history cannot be parsed structurally."""


class CompletedHistoryStaleError(CompletedHistoryError):
    """A cursor names another current record set or query."""


class CompletedHistoryReceiptSetAdvancedError(CompletedHistoryError):
    """Current completion records advanced beyond one pagination cursor."""


class _CompletedChangeRecordBase(_CompletedHistoryModel):
    schema_version: Literal[2] = 2
    change_id: ChangeId
    completion_id: Digest
    title: str = Field(min_length=1)
    semantic_summary: str = Field(min_length=1)
    outcome_titles: tuple[str, ...] = Field(min_length=1)
    outcome_promises: tuple[str, ...] | None = None


class ReceiptCompletedChangeRecord(_CompletedChangeRecordBase):
    """Receipt-backed completion facts without graph or target-reachability claims."""

    record_kind: Literal["completion-receipt"] = "completion-receipt"
    finalization_receipt_id: Digest
    finalized_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    repository_identity: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    pull_request_identity: CompletionPullRequestIdentity
    accepted_target_ref: str = Field(min_length=1)
    accepted_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    merged_at: datetime
    acceptance_observation_id: Digest
    check_observation_ids: tuple[Digest, ...]
    review_receipt_ids: tuple[Digest, ...]
    acceptance_evidence_digest: Digest
    completed_at: datetime


class AbandonedChangeRecord(_CompletedHistoryModel):
    """Terminal abandonment facts retained separately from accepted history."""

    schema_version: Literal[1] = 1
    record_kind: Literal["abandoned-change"] = "abandoned-change"
    change_id: ChangeId
    abandonment_id: Digest
    title: str = Field(min_length=1)
    semantic_summary: str = Field(min_length=1)
    outcome_titles: tuple[str, ...] = Field(min_length=1)
    outcome_promises: tuple[str, ...] | None = None
    prior_stage: DeliveryChangeStage
    reason: str = Field(min_length=1)
    abandoned_at: datetime
    cleanup_available: bool
    target_sync_conflict: bool = False
    target_sync_conflict_target_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    target_sync_conflict_operation_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
    )


type CompletedChangeRecord = Annotated[
    ReceiptCompletedChangeRecord | AbandonedChangeRecord,
    Field(discriminator="record_kind"),
]


class CompletedChangePage(_CompletedHistoryModel):
    """One deterministic bounded page from current completion records."""

    records: tuple[CompletedChangeRecord, ...]
    total_count: int = Field(ge=0)
    next_cursor: str | None = None


class _Cursor(_CompletedHistoryModel):
    schema_version: Literal[3] = 3
    record_set_digest: Digest
    query_digest: Digest
    offset: int = Field(ge=0)


class _CatalogSnapshot(_CompletedHistoryModel):
    record_set_digest: Digest
    records: tuple[CompletedChangeRecord, ...]


def _decode_cursor(cursor: str) -> _Cursor:
    try:
        padding = "=" * (-len(cursor) % 4)
        content = base64.urlsafe_b64decode(f"{cursor}{padding}")
        return _Cursor.model_validate_json(content)
    except (binascii.Error, ValueError, ValidationError, json.JSONDecodeError) as exc:
        diagnostic = CompletedHistoryDiagnostic(
            code=CompletedHistoryDiagnosticCode.MALFORMED,
            detail="completed-history cursor is malformed",
        )
        raise CompletedHistoryMalformedError(diagnostic) from exc


def _encode_cursor(cursor: _Cursor) -> str:
    content = json.dumps(
        cursor.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(content).decode().rstrip("=")


def _query_digest(query: str) -> str:
    return hashlib.sha256(query.casefold().encode()).hexdigest()


class CompletedHistoryCatalog:
    """Rebuild bounded receipt-backed and abandoned completion records."""

    def __init__(self, runtime_root: Path) -> None:
        self._runtime_root = runtime_root.resolve()
        self._completion_store = CompletionReceiptStore(self._runtime_root)

    def list(self, cursor: str | None = None, limit: int = 100) -> CompletedChangePage:
        """List one stable identity-ordered page from current completion history."""
        return self._page(self._rebuild(), "", cursor, limit)

    def search(self, query: str, cursor: str | None = None, limit: int = 100) -> CompletedChangePage:
        """Search semantic summaries and return one stable bounded page."""
        normalized = query.strip().casefold()
        if not normalized:
            self._malformed("completed-history search query must be nonempty")
        snapshot = self._rebuild()
        matches = tuple(record for record in snapshot.records if normalized in self._search_text(record))
        return self._page(snapshot.model_copy(update={"records": matches}), normalized, cursor, limit)

    def show(self, change_id: str, completion_id: str | None = None) -> CompletedChangeRecord:
        """Show one current completion by Change and optional exact identity."""
        for record in self._rebuild().records:
            if record.change_id == change_id and completion_id in {None, _record_identity(record)}:
                return record
        return self._missing("completed change is absent", change_id, completion_id)

    def _rebuild(self) -> _CatalogSnapshot:
        try:
            bundles = self._completion_store.list()
        except CompletionReceiptConflictError as exc:
            self._malformed("completion receipt history is malformed", cause=exc)
        receipt_records = tuple(self._receipt_record(bundle) for bundle in bundles)
        receipt_change_ids = {record.change_id for record in receipt_records}
        abandoned_records = tuple(
            self._abandoned_record(observation)
            for observation in self._abandoned_observations()
            if observation[0] not in receipt_change_ids
        )
        records = (*receipt_records, *abandoned_records)
        ordered_records = tuple(
            sorted(records, key=lambda item: (item.change_id, item.record_kind, _record_identity(item)))
        )
        return _CatalogSnapshot(
            record_set_digest=_history_record_set_digest(ordered_records),
            records=ordered_records,
        )

    @staticmethod
    def _receipt_record(bundle: CompletionReceiptBundle) -> ReceiptCompletedChangeRecord:
        receipt = bundle.receipt
        display = bundle.display
        return ReceiptCompletedChangeRecord(
            change_id=receipt.change_id,
            completion_id=receipt.completion_id,
            title=display.title,
            semantic_summary=" | ".join(display.outcome_titles),
            outcome_titles=display.outcome_titles,
            outcome_promises=display.outcome_promises,
            finalization_receipt_id=receipt.finalization_receipt_id,
            finalized_change_head=receipt.finalized_change_head,
            repository_identity=receipt.repository_identity,
            pull_request_identity=receipt.pull_request_identity,
            accepted_target_ref=receipt.accepted_target_ref,
            accepted_merge_commit=receipt.accepted_merge_commit,
            merged_at=receipt.merged_at,
            acceptance_observation_id=receipt.acceptance_observation_id,
            check_observation_ids=receipt.check_observation_ids,
            review_receipt_ids=receipt.review_receipt_ids,
            acceptance_evidence_digest=receipt.acceptance_evidence_digest,
            completed_at=receipt.completed_at,
        )

    def _abandoned_observations(self) -> tuple[tuple[str, DeliveryFrontier], ...]:
        """Read terminal abandoned frontiers from local Delivery runtime state."""
        changes_root = self._runtime_root / "changes"
        if not changes_root.exists():
            return ()
        if changes_root.is_symlink() or not changes_root.is_dir():
            self._malformed("Delivery abandoned-history root is invalid")
        observations = []
        for change_root in sorted(changes_root.iterdir(), key=lambda path: path.name):
            if (
                change_root.is_symlink()
                or not change_root.is_dir()
                or not _SAFE_CHANGE_ID.fullmatch(change_root.name)
            ):
                continue
            path = change_root / "frontier.json"
            if path.is_symlink() or not path.is_file():
                continue
            try:
                frontier = parse_delivery_frontier(path.read_bytes())[0]
            except (OSError, TypeError, ValueError, ValidationError) as exc:
                self._malformed("Delivery abandoned-history frontier is invalid", change_root.name, cause=exc)
            if frontier.change_abandonment is not None:
                observations.append((change_root.name, frontier))
        return tuple(observations)

    def _abandoned_record(self, observation: tuple[str, DeliveryFrontier]) -> AbandonedChangeRecord:
        change_id, frontier = observation
        abandonment = frontier.change_abandonment
        if abandonment is None:
            self._malformed("abandoned-history frontier has no abandonment receipt", change_id)
        contract = self._local_contract(change_id)
        cleanup_available, target_sync_conflict, target_head, operation_id = self._cleanup_state(change_id)
        return AbandonedChangeRecord(
            change_id=change_id,
            abandonment_id=abandonment.abandonment_id,
            title=contract.title,
            semantic_summary=f"Abandoned before completion: {abandonment.reason}",
            outcome_titles=tuple(outcome.title for outcome in contract.outcomes),
            outcome_promises=tuple(outcome.promise for outcome in contract.outcomes),
            prior_stage=abandonment.prior_stage,
            reason=abandonment.reason,
            abandoned_at=abandonment.abandoned_at,
            cleanup_available=cleanup_available,
            target_sync_conflict=target_sync_conflict,
            target_sync_conflict_target_head=target_head,
            target_sync_conflict_operation_id=operation_id,
        )

    def _local_contract(self, change_id: str) -> DeliveryContract:
        path = self._runtime_root / "changes" / change_id / "contract.json"
        try:
            contract = DeliveryContract.model_validate_json(path.read_bytes())
        except (OSError, TypeError, ValueError, ValidationError) as exc:
            self._malformed("abandoned-history contract is invalid", change_id, cause=exc)
        if contract.change_id != change_id:
            self._malformed("abandoned-history contract identity is invalid", change_id)
        return contract

    def _cleanup_state(self, change_id: str) -> tuple[bool, bool, str | None, str | None]:
        path = self._runtime_root / "coordination" / "changes" / f"{change_id}.json"
        if not path.is_file() or path.is_symlink():
            return False, False, None, None
        try:
            coordination = ChangeCoordination.model_validate_json(path.read_bytes())
        except (OSError, TypeError, ValueError, ValidationError) as exc:
            self._malformed("abandoned-history coordination is invalid", change_id, cause=exc)
        conflict = coordination.target_sync_conflict
        return (
            coordination.worktree_cleanup is None,
            conflict is not None,
            conflict.target_head if conflict is not None else None,
            conflict.operation_id if conflict is not None else None,
        )

    @staticmethod
    def _search_text(record: CompletedChangeRecord) -> str:
        fields = [record.change_id, record.title, record.semantic_summary]
        if isinstance(record, ReceiptCompletedChangeRecord):
            fields.extend(
                (
                    record.repository_identity,
                    record.accepted_target_ref,
                    str(record.pull_request_identity.number),
                )
            )
        elif isinstance(record, AbandonedChangeRecord):
            fields.extend((record.prior_stage.value, record.reason))
        return "\n".join(fields).casefold()

    def _page(self, snapshot: _CatalogSnapshot, query: str, cursor: str | None, limit: int) -> CompletedChangePage:
        if not 1 <= limit <= _MAX_PAGE_SIZE:
            self._malformed("completed-history limit must be between 1 and 100")
        offset = self._cursor_offset(cursor, snapshot.record_set_digest, query)
        selected = snapshot.records[offset : offset + limit]
        next_offset = offset + len(selected)
        next_cursor = None
        if next_offset < len(snapshot.records):
            next_cursor = _encode_cursor(
                _Cursor(
                    record_set_digest=snapshot.record_set_digest,
                    query_digest=_query_digest(query),
                    offset=next_offset,
                )
            )
        return CompletedChangePage(records=selected, total_count=len(snapshot.records), next_cursor=next_cursor)

    def _cursor_offset(self, cursor: str | None, record_set_digest: str, query: str) -> int:
        if cursor is None:
            return 0
        decoded = _decode_cursor(cursor)
        if decoded.query_digest != _query_digest(query):
            diagnostic = CompletedHistoryDiagnostic(
                code=CompletedHistoryDiagnosticCode.STALE,
                detail="completed-history cursor does not match this current record set and query",
            )
            raise CompletedHistoryStaleError(diagnostic)
        if decoded.record_set_digest != record_set_digest:
            diagnostic = CompletedHistoryDiagnostic(
                code=CompletedHistoryDiagnosticCode.RECEIPT_SET_ADVANCED,
                detail="completed-history records advanced beyond this cursor",
            )
            raise CompletedHistoryReceiptSetAdvancedError(diagnostic)
        return decoded.offset

    @staticmethod
    def _missing(detail: str, change_id: str | None = None, completion_id: str | None = None) -> Never:
        diagnostic = CompletedHistoryDiagnostic(
            code=CompletedHistoryDiagnosticCode.MISSING,
            detail=detail,
            change_id=change_id,
            completion_id=completion_id,
        )
        raise CompletedHistoryMissingError(diagnostic)

    @staticmethod
    def _malformed(detail: str, change_id: str | None = None, *, cause: Exception | None = None) -> Never:
        diagnostic = CompletedHistoryDiagnostic(
            code=CompletedHistoryDiagnosticCode.MALFORMED,
            detail=detail,
            change_id=change_id,
        )
        raise CompletedHistoryMalformedError(diagnostic) from cause


def _record_identity(record: CompletedChangeRecord) -> str:
    return record.abandonment_id if isinstance(record, AbandonedChangeRecord) else record.completion_id


def _history_record_set_digest(records: tuple[CompletedChangeRecord, ...]) -> str:
    payload = [record.model_dump(mode="json") for record in records]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
