"""Bounded Git-backed projections of completed Delivery packages."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import subprocess
from enum import StrEnum
from typing import TYPE_CHECKING, Never

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from owlbear_kanban.delivery_runtime import DeliveryFrontier, DeliveryStage, DeliveryTaskResult
from owlbear_kanban.design_package import (
    CompletionPackageManifest,
    CompletionPackageSnapshot,
    DesignPackageManifest,
)
from owlbear_kanban.identities import ChangeId, Digest
from owlbear_kanban.target_contract import DeliveryContract

if TYPE_CHECKING:
    from pathlib import Path

_COMPLETED_ROOT = ".owlbear/completed"
_COMPLETION_NAMES = {
    "authority.json",
    "completion.json",
    "design.md",
    "intent.md",
    "manifest.json",
    "results.json",
    "runtime.json",
}
_GIT_EXECUTABLE = "/usr/bin/git"
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


class CompletedHistoryDigestMismatchError(CompletedHistoryError):
    """Persisted completed package bytes differ from their digest bindings."""


class CompletedChangeRecord(_CompletedHistoryModel):
    """Bounded immutable semantic projection of one completed package."""

    change_id: ChangeId
    completion_id: Digest
    completion_path: str = Field(pattern=r"^\.owlbear/completed/[a-z0-9]+(?:-[a-z0-9]+)*$")
    package_id: Digest
    introducing_target_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_target_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    title: str = Field(min_length=1)
    semantic_summary: str = Field(min_length=1)


class CompletedChangePage(_CompletedHistoryModel):
    """One deterministic bounded page from an exact target snapshot."""

    records: tuple[CompletedChangeRecord, ...]
    next_cursor: str | None = None


class _Cursor(_CompletedHistoryModel):
    source_target_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    query_digest: Digest
    offset: int = Field(ge=0)


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
    """Rebuild bounded completed-package records from one configured Git target."""

    def __init__(self, repository: Path, integration_target: str) -> None:
        if not integration_target:
            message = "integration target must be nonempty"
            raise ValueError(message)
        self._repository = repository.resolve()
        self._integration_target = integration_target

    def list(self, cursor: str | None = None, limit: int = 100) -> CompletedChangePage:
        """List one stable identity-ordered page from completed history."""
        source_commit, records = self._rebuild()
        return self._page(records, source_commit, "", cursor, limit)

    def search(self, query: str, cursor: str | None = None, limit: int = 100) -> CompletedChangePage:
        """Search semantic summaries and return one stable bounded page."""
        normalized = query.strip().casefold()
        if not normalized:
            self._malformed("completed-history search query must be nonempty")
        source_commit, records = self._rebuild()
        matches = tuple(record for record in records if normalized in record.semantic_summary.casefold())
        return self._page(matches, source_commit, normalized, cursor, limit)

    def show(self, change_id: str, completion_id: str | None = None) -> CompletedChangeRecord:
        """Show one verified completion by change and optional exact completion identity."""
        records = self._rebuild()[1]
        for record in records:
            if record.change_id == change_id and completion_id in {None, record.completion_id}:
                return record
        return self._missing("completed change is absent", change_id, completion_id)

    def _rebuild(self) -> tuple[str, tuple[CompletedChangeRecord, ...]]:
        target_commit = self._resolve_target()
        records = tuple(self._record(target_commit, path) for path in self._completion_paths(target_commit))
        return target_commit, tuple(sorted(records, key=lambda item: (item.change_id, item.completion_id)))

    def _record(self, target_commit: str, path: str) -> CompletedChangeRecord:
        snapshot = self._snapshot(target_commit, path)
        contract = self._verify_design_package(target_commit, path, snapshot)
        self._verify_runtime_capture(target_commit, path, snapshot, contract)
        introducing_commit, source_commit = self._introduction(target_commit, path, snapshot)
        summary = " | ".join((contract.title, *(outcome.title for outcome in contract.outcomes)))
        return CompletedChangeRecord(
            change_id=snapshot.manifest.change_id,
            completion_id=snapshot.completion_id,
            completion_path=path,
            package_id=snapshot.package_id,
            introducing_target_commit=introducing_commit,
            source_target_commit=source_commit,
            title=contract.title,
            semantic_summary=summary,
        )

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
            frontier = DeliveryFrontier.model_validate_json(runtime_bytes)
            results = _RESULT_HISTORY.validate_json(results_bytes)
        except (ValidationError, ValueError) as exc:
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
        path: str,
        snapshot: CompletionPackageSnapshot,
    ) -> tuple[str, str]:
        output = self._git(
            "log",
            "--reverse",
            "--format=%H",
            target_commit,
            "--",
            f"{path}/completion.json",
        ).decode()
        commits = tuple(line for line in output.splitlines() if line)
        if not commits:
            self._malformed("completion has no introducing target commit", snapshot.manifest.change_id)
        introducing = commits[0]
        introduced_tree = self._git("rev-parse", f"{introducing}:{path}").decode().strip()
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
        root = f"{target_commit}:{_COMPLETED_ROOT}"
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
        return f"{_COMPLETED_ROOT}/{change_id}"

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
        if manifest.completion_path != path or path != f"{_COMPLETED_ROOT}/{manifest.change_id}":
            self._stale("completion manifest path or change identity is stale", snapshot)
        if manifest.integration_target != self._integration_target:
            self._stale("completion manifest names another integration target", snapshot)

    def _page(
        self,
        records: tuple[CompletedChangeRecord, ...],
        source_commit: str,
        query: str,
        cursor: str | None,
        limit: int,
    ) -> CompletedChangePage:
        if not 1 <= limit <= _MAX_PAGE_SIZE:
            self._malformed("completed-history limit must be between 1 and 100")
        offset = self._cursor_offset(cursor, source_commit, query)
        selected = records[offset : offset + limit]
        next_offset = offset + len(selected)
        next_cursor = None
        if next_offset < len(records):
            next_cursor = _encode_cursor(
                _Cursor(
                    source_target_commit=source_commit,
                    query_digest=_query_digest(query),
                    offset=next_offset,
                )
            )
        return CompletedChangePage(records=selected, next_cursor=next_cursor)

    def _cursor_offset(self, cursor: str | None, source_commit: str, query: str) -> int:
        if cursor is None:
            return 0
        decoded = _decode_cursor(cursor)
        if decoded.source_target_commit != source_commit or decoded.query_digest != _query_digest(query):
            diagnostic = CompletedHistoryDiagnostic(
                code=CompletedHistoryDiagnosticCode.STALE,
                detail="completed-history cursor does not match this target snapshot and query",
            )
            raise CompletedHistoryStaleError(diagnostic)
        return decoded.offset

    def _resolve_target(self) -> str:
        result = self._run_git("rev-parse", "--verify", f"{self._integration_target}^{{commit}}", check=False)
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
            (_GIT_EXECUTABLE, "-C", str(self._repository), *arguments),
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


def _canonical_results(results: tuple[DeliveryTaskResult, ...]) -> bytes:
    payload = [result.model_dump(mode="json") for result in results]
    return f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n".encode()
