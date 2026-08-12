"""Bounded Git-backed projections of completed Delivery packages."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import subprocess
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from owlbear_delivery.acceptance import (
    CompletionPullRequestIdentity,
    CompletionReceiptBundle,
    CompletionReceiptConflictError,
    CompletionReceiptStore,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryFrontier,
    DeliveryStage,
    DeliveryTaskResult,
    parse_delivery_frontier,
)
from owlbear_delivery.design_package import (
    CompletionPackageManifest,
    CompletionPackageSnapshot,
    DesignPackageManifest,
)
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.identities import ChangeId, Digest
from owlbear_delivery.target_contract import DeliveryContract

if TYPE_CHECKING:
    from pathlib import Path

_LEGACY_COMPLETED_ROOT = ".owlbear/legacy/completed"
_HISTORICAL_COMPLETED_ROOT = ".owlbear/completed"
_COMPLETION_NAMES = {
    "authority.json",
    "completion.json",
    "design.md",
    "intent.md",
    "manifest.json",
    "results.json",
    "runtime.json",
}
_MAX_PAGE_SIZE = 100
_SAFE_CHANGE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TREE_ENTRY_PARTS = 3
_RESULT_HISTORY = TypeAdapter(tuple[DeliveryTaskResult, ...])


class _CompletedHistoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CompletedHistoryDiagnosticCode(StrEnum):
    """Stable failure categories for read-only completed-history queries."""

    MISSING = "completed-history-missing"
    MALFORMED = "completed-history-malformed"
    STALE = "completed-history-stale"
    RECEIPT_SET_ADVANCED = "completed-history-receipt-set-advanced"
    DIGEST_MISMATCH = "completed-history-digest-mismatch"


class CompletedHistoryDiagnostic(_CompletedHistoryModel):
    """Bounded named evidence for one failed catalog query."""

    code: CompletedHistoryDiagnosticCode
    detail: str = Field(min_length=1)
    change_id: str | None = None
    completion_id: str | None = None


class CompletedHistoryError(RuntimeError):
    """A completed-history query failed without mutating Git or catalog authority."""

    def __init__(self, diagnostic: CompletedHistoryDiagnostic) -> None:
        super().__init__(diagnostic.detail)
        self.diagnostic = diagnostic


class CompletedHistoryMissingError(CompletedHistoryError):
    """The configured target or requested completion is absent."""


class CompletedHistoryMalformedError(CompletedHistoryError):
    """Persisted completed history cannot be parsed structurally."""


class CompletedHistoryStaleError(CompletedHistoryError):
    """A cursor or persisted target binding names another target state."""


class CompletedHistoryReceiptSetAdvancedError(CompletedHistoryError):
    """Append-only receipt history advanced beyond one pagination cursor."""


class CompletedHistoryDigestMismatchError(CompletedHistoryError):
    """Persisted completed package bytes differ from their digest bindings."""


class _CompletedChangeRecordBase(_CompletedHistoryModel):
    schema_version: Literal[2] = 2
    change_id: ChangeId
    completion_id: Digest
    title: str = Field(min_length=1)
    semantic_summary: str = Field(min_length=1)


class LegacyCompletedChangeRecord(_CompletedChangeRecordBase):
    """Verified legacy package with historical target-ancestry semantics."""

    record_kind: Literal["legacy-package"] = "legacy-package"
    completion_path: str = Field(pattern=r"^\.owlbear/legacy/completed/[a-z0-9]+(?:-[a-z0-9]+)*$")
    historical_completion_locator: str = Field(pattern=r"^\.owlbear/completed/[a-z0-9]+(?:-[a-z0-9]+)*$")
    package_id: Digest
    introducing_target_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_target_commit: str = Field(pattern=r"^[0-9a-f]{40}$")


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


type CompletedChangeRecord = Annotated[
    LegacyCompletedChangeRecord | ReceiptCompletedChangeRecord,
    Field(discriminator="record_kind"),
]


class CompletedChangePage(_CompletedHistoryModel):
    """One deterministic bounded page from an exact target snapshot."""

    records: tuple[CompletedChangeRecord, ...]
    next_cursor: str | None = None


class _Cursor(_CompletedHistoryModel):
    schema_version: Literal[2] = 2
    legacy_source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    receipt_set_digest: Digest
    query_digest: Digest
    offset: int = Field(ge=0)


class _CatalogSnapshot(_CompletedHistoryModel):
    legacy_source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    receipt_set_digest: Digest
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
    """Rebuild bounded legacy-package and receipt-backed completion records."""

    def __init__(
        self,
        repository: Path,
        target_branch: str,
        legacy_source_ref: str,
        runtime_root: Path,
    ) -> None:
        if not target_branch or not legacy_source_ref:
            message = "target branch and legacy source ref must be nonempty"
            raise ValueError(message)
        self._repository = repository.resolve()
        self._target_branch = target_branch
        self._legacy_source_ref = legacy_source_ref
        self._completion_store = CompletionReceiptStore(runtime_root)

    def list(self, cursor: str | None = None, limit: int = 100) -> CompletedChangePage:
        """List one stable identity-ordered page from completed history."""
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
        """Show one verified completion by change and optional exact completion identity."""
        for record in self._rebuild().records:
            if record.change_id == change_id and completion_id in {None, record.completion_id}:
                return record
        return self._missing("completed change is absent", change_id, completion_id)

    def _rebuild(self) -> _CatalogSnapshot:
        target_commit = self._resolve_target()
        legacy_records = tuple(
            self._legacy_record(target_commit, path) for path in self._completion_paths(target_commit)
        )
        try:
            bundles = self._completion_store.list()
        except CompletionReceiptConflictError as exc:
            self._malformed("completion receipt history is malformed", cause=exc)
        receipt_records = tuple(self._receipt_record(bundle) for bundle in bundles)
        receipt_change_ids = {record.change_id for record in receipt_records}
        records = (
            *receipt_records,
            *(record for record in legacy_records if record.change_id not in receipt_change_ids),
        )
        receipt_set_digest = _receipt_set_digest(bundles)
        return _CatalogSnapshot(
            legacy_source_commit=target_commit,
            receipt_set_digest=receipt_set_digest,
            records=tuple(sorted(records, key=lambda item: (item.change_id, item.record_kind, item.completion_id))),
        )

    def _legacy_record(self, target_commit: str, path: str) -> LegacyCompletedChangeRecord:
        snapshot = self._snapshot(target_commit, path)
        contract = self._verify_design_package(target_commit, path, snapshot)
        self._verify_runtime_capture(target_commit, path, snapshot, contract)
        introducing_commit, source_commit = self._introduction(target_commit, snapshot)
        summary = " | ".join((contract.title, *(outcome.title for outcome in contract.outcomes)))
        return LegacyCompletedChangeRecord(
            change_id=snapshot.manifest.change_id,
            completion_id=snapshot.completion_id,
            completion_path=path,
            historical_completion_locator=snapshot.manifest.completion_path,
            package_id=snapshot.package_id,
            introducing_target_commit=introducing_commit,
            source_target_commit=source_commit,
            title=contract.title,
            semantic_summary=summary,
        )

    @staticmethod
    def _receipt_record(bundle: CompletionReceiptBundle) -> ReceiptCompletedChangeRecord:
        receipt = bundle.receipt
        display = bundle.display
        return ReceiptCompletedChangeRecord(
            change_id=receipt.change_id,
            completion_id=receipt.completion_id,
            title=display.title,
            semantic_summary=" | ".join((display.title, *display.outcome_titles)),
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
        return "\n".join(fields).casefold()

    def _snapshot(self, commit: str, path: str) -> CompletionPackageSnapshot:
        self._require_completion_names(commit, path)
        content = self._blob(commit, path, "completion.json")
        try:
            manifest = CompletionPackageManifest.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            self._malformed("completion manifest is malformed", path.rsplit("/", 1)[-1], cause=exc)
        if content != manifest.canonical_bytes():
            self._malformed("completion manifest is not canonical", manifest.change_id)
        completion_id = hashlib.sha256(content).hexdigest()
        tree = self._git("rev-parse", f"{commit}:{path}").decode().strip()
        snapshot = CompletionPackageSnapshot(
            completion_id=completion_id,
            package_id=manifest.package_id,
            manifest=manifest,
            package_tree=tree,
        )
        self._require_snapshot_binding(path, snapshot)
        return snapshot

    def _verify_design_package(
        self,
        commit: str,
        path: str,
        snapshot: CompletionPackageSnapshot,
    ) -> DeliveryContract:
        content = self._blob(commit, path, "manifest.json")
        try:
            manifest = DesignPackageManifest.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            self._malformed("package manifest is malformed", snapshot.manifest.change_id, cause=exc)
        if content != manifest.canonical_bytes():
            self._malformed("package manifest is not canonical", snapshot.manifest.change_id)
        if hashlib.sha256(content).hexdigest() != snapshot.package_id:
            self._digest_mismatch("package identity does not match its manifest", snapshot)
        self._verify_authored_digests(commit, path, snapshot, manifest)
        return self._contract(commit, path, snapshot)

    def _verify_authored_digests(
        self,
        commit: str,
        path: str,
        snapshot: CompletionPackageSnapshot,
        manifest: DesignPackageManifest,
    ) -> None:
        expected = {
            "authority.json": manifest.authority_sha256,
            "design.md": manifest.design_sha256,
            "intent.md": manifest.intent_sha256,
        }
        if manifest.change_id != snapshot.manifest.change_id:
            self._digest_mismatch("package and completion change identities differ", snapshot)
        if manifest.authority_sha256 != snapshot.manifest.authority_digest:
            self._digest_mismatch("completion authority digest differs from its package", snapshot)
        for name, digest in expected.items():
            if hashlib.sha256(self._blob(commit, path, name)).hexdigest() != digest:
                self._digest_mismatch(f"{name} does not match its package digest", snapshot)

    def _contract(self, commit: str, path: str, snapshot: CompletionPackageSnapshot) -> DeliveryContract:
        content = self._blob(commit, path, "authority.json")
        try:
            contract = DeliveryContract.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            self._malformed("completed authority is malformed", snapshot.manifest.change_id, cause=exc)
        if content != _canonical_model(contract):
            self._malformed("completed authority is not canonical", snapshot.manifest.change_id)
        if contract.change_id != snapshot.manifest.change_id:
            self._stale("completed authority names another change", snapshot)
        return contract

    def _verify_runtime_capture(
        self,
        commit: str,
        path: str,
        snapshot: CompletionPackageSnapshot,
        contract: DeliveryContract,
    ) -> None:
        runtime_bytes = self._blob(commit, path, "runtime.json")
        results_bytes = self._blob(commit, path, "results.json")
        self._require_capture_digests(snapshot, runtime_bytes, results_bytes)
        try:
            frontier = parse_delivery_frontier(runtime_bytes)[0]
            results = _RESULT_HISTORY.validate_json(results_bytes)
        except (TypeError, ValidationError, ValueError) as exc:
            self._malformed("completed runtime capture is malformed", snapshot.manifest.change_id, cause=exc)
        self._require_capture_shape(snapshot, contract, frontier, results)
        if runtime_bytes != _canonical_model(frontier) or results_bytes != _canonical_results(results):
            self._malformed("completed runtime capture is not canonical", snapshot.manifest.change_id)

    def _require_capture_digests(
        self,
        snapshot: CompletionPackageSnapshot,
        runtime_bytes: bytes,
        results_bytes: bytes,
    ) -> None:
        manifest = snapshot.manifest
        digests = (
            (runtime_bytes, manifest.runtime_sha256, "runtime capture"),
            (results_bytes, manifest.result_history_sha256, "result history"),
        )
        for content, expected, label in digests:
            if hashlib.sha256(content).hexdigest() != expected:
                self._digest_mismatch(f"{label} does not match its digest", snapshot)

    def _require_capture_shape(
        self,
        snapshot: CompletionPackageSnapshot,
        contract: DeliveryContract,
        frontier: DeliveryFrontier,
        results: tuple[DeliveryTaskResult, ...],
    ) -> None:
        bindings = frontier.bindings
        flattened = tuple(result for binding in bindings for result in binding.results)
        if tuple(binding.outcome_id for binding in bindings) != tuple(item.outcome_id for item in contract.outcomes):
            self._stale("completed runtime does not match authority outcomes", snapshot)
        if {binding.stage for binding in bindings} != {DeliveryStage.COMPLETED} or results != flattened:
            self._stale("completed runtime is not a complete immutable capture", snapshot)
        if any(result.authority_digest != snapshot.manifest.authority_digest for result in results):
            self._digest_mismatch("result history names another authority digest", snapshot)

    def _introduction(
        self,
        target_commit: str,
        snapshot: CompletionPackageSnapshot,
    ) -> tuple[str, str]:
        historical_path = snapshot.manifest.completion_path
        output = self._git(
            "log",
            "--reverse",
            "--format=%H",
            target_commit,
            "--",
            f"{historical_path}/completion.json",
        ).decode()
        commits = tuple(line for line in output.splitlines() if line)
        if not commits:
            self._malformed("completion has no introducing target commit", snapshot.manifest.change_id)
        introducing = commits[0]
        introduced_tree = self._git("rev-parse", f"{introducing}:{historical_path}").decode().strip()
        if introduced_tree != snapshot.package_tree:
            self._stale("completed package changed after its introduction", snapshot)
        parents = self._git("rev-list", "--parents", "-n", "1", introducing).decode().split()
        source_commit = parents[1] if len(parents) > 1 else introducing
        self._require_reviewed_ancestry(introducing, snapshot)
        return introducing, source_commit

    def _require_reviewed_ancestry(self, introducing: str, snapshot: CompletionPackageSnapshot) -> None:
        reviewed = snapshot.manifest.reviewed_change_head
        result = self._run_git("merge-base", "--is-ancestor", reviewed, introducing, check=False)
        if result.returncode != 0:
            self._stale("reviewed change head is not in completion ancestry", snapshot)

    def _completion_paths(self, target_commit: str) -> tuple[str, ...]:
        root = f"{target_commit}:{_LEGACY_COMPLETED_ROOT}"
        kind = self._run_git("cat-file", "-t", root, check=False)
        if kind.returncode != 0:
            return ()
        if kind.stdout.strip() != b"tree":
            self._malformed("completed-history root is not a Git tree")
        entries = self._git("ls-tree", "-z", root).split(b"\0")
        return tuple(sorted(self._completion_path(entry) for entry in entries if entry))

    def _completion_path(self, entry: bytes) -> str:
        metadata, separator, name = entry.partition(b"\t")
        parts = metadata.split()
        try:
            change_id = name.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            self._malformed("completed-history path is not UTF-8", cause=exc)
        if (
            separator != b"\t"
            or len(parts) != _TREE_ENTRY_PARTS
            or parts[1] != b"tree"
            or not _SAFE_CHANGE_ID.fullmatch(change_id)
        ):
            self._malformed("completed-history entry is not a valid change tree", change_id)
        return f"{_LEGACY_COMPLETED_ROOT}/{change_id}"

    def _require_completion_names(self, commit: str, path: str) -> None:
        content = self._git("ls-tree", "--name-only", "-z", f"{commit}:{path}")
        try:
            names = {name.decode("utf-8", errors="strict") for name in content.split(b"\0") if name}
        except UnicodeDecodeError as exc:
            self._malformed("completed package entry is not UTF-8", cause=exc)
        if names != _COMPLETION_NAMES:
            self._malformed("completed package entries differ", path.rsplit("/", 1)[-1])

    def _require_snapshot_binding(self, path: str, snapshot: CompletionPackageSnapshot) -> None:
        manifest = snapshot.manifest
        if (
            manifest.completion_path != f"{_HISTORICAL_COMPLETED_ROOT}/{manifest.change_id}"
            or path != f"{_LEGACY_COMPLETED_ROOT}/{manifest.change_id}"
        ):
            self._stale("completion manifest path or change identity is stale", snapshot)
        if manifest.integration_target != self._target_branch:
            self._stale("completion manifest names another integration target", snapshot)

    def _page(
        self,
        snapshot: _CatalogSnapshot,
        query: str,
        cursor: str | None,
        limit: int,
    ) -> CompletedChangePage:
        if not 1 <= limit <= _MAX_PAGE_SIZE:
            self._malformed("completed-history limit must be between 1 and 100")
        offset = self._cursor_offset(
            cursor,
            snapshot.legacy_source_commit,
            snapshot.receipt_set_digest,
            query,
        )
        selected = snapshot.records[offset : offset + limit]
        next_offset = offset + len(selected)
        next_cursor = None
        if next_offset < len(snapshot.records):
            next_cursor = _encode_cursor(
                _Cursor(
                    legacy_source_commit=snapshot.legacy_source_commit,
                    receipt_set_digest=snapshot.receipt_set_digest,
                    query_digest=_query_digest(query),
                    offset=next_offset,
                )
            )
        return CompletedChangePage(records=selected, next_cursor=next_cursor)

    def _cursor_offset(
        self,
        cursor: str | None,
        source_commit: str,
        receipt_set_digest: str,
        query: str,
    ) -> int:
        if cursor is None:
            return 0
        decoded = _decode_cursor(cursor)
        if decoded.legacy_source_commit != source_commit or decoded.query_digest != _query_digest(query):
            diagnostic = CompletedHistoryDiagnostic(
                code=CompletedHistoryDiagnosticCode.STALE,
                detail="completed-history cursor does not match this target snapshot and query",
            )
            raise CompletedHistoryStaleError(diagnostic)
        if decoded.receipt_set_digest != receipt_set_digest:
            diagnostic = CompletedHistoryDiagnostic(
                code=CompletedHistoryDiagnosticCode.RECEIPT_SET_ADVANCED,
                detail="completed-history receipts advanced beyond this cursor",
            )
            raise CompletedHistoryReceiptSetAdvancedError(diagnostic)
        return decoded.offset

    def _resolve_target(self) -> str:
        result = self._run_git("rev-parse", "--verify", f"{self._legacy_source_ref}^{{commit}}", check=False)
        if result.returncode != 0:
            self._missing("configured integration target is absent")
        return result.stdout.decode().strip()

    def _blob(self, commit: str, path: str, name: str) -> bytes:
        result = self._run_git("show", f"{commit}:{path}/{name}", check=False)
        if result.returncode != 0:
            self._malformed(f"completed package is missing {name}", path.rsplit("/", 1)[-1])
        return result.stdout

    def _git(self, *arguments: str) -> bytes:
        result = self._run_git(*arguments, check=False)
        if result.returncode != 0:
            self._malformed("Git completed-history traversal failed")
        return result.stdout

    def _run_git(self, *arguments: str, check: bool) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            (resolve_git_executable(), "-C", str(self._repository), *arguments),
            check=check,
            capture_output=True,
        )

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

    @staticmethod
    def _stale(detail: str, snapshot: CompletionPackageSnapshot) -> Never:
        diagnostic = CompletedHistoryDiagnostic(
            code=CompletedHistoryDiagnosticCode.STALE,
            detail=detail,
            change_id=snapshot.manifest.change_id,
            completion_id=snapshot.completion_id,
        )
        raise CompletedHistoryStaleError(diagnostic)

    @staticmethod
    def _digest_mismatch(detail: str, snapshot: CompletionPackageSnapshot) -> Never:
        diagnostic = CompletedHistoryDiagnostic(
            code=CompletedHistoryDiagnosticCode.DIGEST_MISMATCH,
            detail=detail,
            change_id=snapshot.manifest.change_id,
            completion_id=snapshot.completion_id,
        )
        raise CompletedHistoryDigestMismatchError(diagnostic)


def _canonical_model(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json")
    return f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n".encode()


def _receipt_set_digest(bundles: tuple[CompletionReceiptBundle, ...]) -> str:
    identities = tuple(
        (bundle.receipt.change_id, bundle.receipt.completion_id, bundle.display.display_id) for bundle in bundles
    )
    return hashlib.sha256(json.dumps(identities, separators=(",", ":")).encode()).hexdigest()


def _canonical_results(results: tuple[DeliveryTaskResult, ...]) -> bytes:
    payload = [result.model_dump(mode="json") for result in results]
    return f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n".encode()
