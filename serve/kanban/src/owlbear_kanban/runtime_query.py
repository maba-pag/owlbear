"""Indexed projections, paginated history, and bounded native work health."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict
from ruamel.yaml.error import YAMLError

from owlbear_kanban.attempts import AttemptEvent, AttemptStore
from owlbear_kanban.change import ChangeRevision, Digest
from owlbear_kanban.finding import Finding, FindingStore
from owlbear_kanban.jobs import JobDisposition, JobKind, JobRecord, JobStore, project_job
from owlbear_kanban.receipt import ReceiptRecord, ReceiptStore, ReceiptValidity, RepositoryHistory
from owlbear_kanban.runtime_requests import NativeRequest, RequestResolution, StoredRequest
from owlbear_kanban.runtime_transaction import RuntimeTransaction
from owlbear_kanban.yaml_rt import make_yaml

if TYPE_CHECKING:
    from owlbear_kanban.proof_checkout import ProofCheckoutManager

HistoryKind = Literal["attempt", "finding", "receipt", "request"]
_ATTEMPT_PATH_PARTS = 3


class RuntimePage[ItemT](BaseModel):
    """One deterministic bounded page."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    items: tuple[ItemT, ...]
    next_cursor: str | None = None


class RuntimeJobProjection(BaseModel):
    """Authority and orthogonal operational state for one native job."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    kind: JobKind
    priority: int
    change_id: str
    delivery_digest: Digest
    target_node_id: str
    title: str
    outcome: str
    acceptance: tuple[str, ...]
    modules: tuple[str, ...]
    interfaces: tuple[str, ...]
    proof: str
    dependency_ready: bool
    claim_id: str | None = None
    requests: tuple[StoredRequest, ...] = ()
    block_id: str | None = None
    attempt: AttemptEvent | None = None
    finding: Finding | None = None
    receipt: ReceiptRecord | None = None
    validity: ReceiptValidity | None = None
    disposition: JobDisposition


class RuntimeHistoryEntry(BaseModel):
    """One identity-stable immutable history record."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    identity: str
    timestamp: str
    kind: HistoryKind
    job_id: int | None = None
    attempt: AttemptEvent | None = None
    finding: Finding | None = None
    receipt: ReceiptRecord | None = None
    request: StoredRequest | None = None


class WorkHealthFinding(BaseModel):
    """One stable native work integrity finding."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: str
    detail: str
    path: str
    target: str | None = None


class WorkHealthResult(BaseModel):
    """Findings and paths from one bounded non-mutating health page."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    findings: tuple[WorkHealthFinding, ...]
    checked_paths: tuple[str, ...]
    next_cursor: str | None = None


def _page[ItemT](
    items: Sequence[ItemT], identities: Sequence[str], cursor: str | None, limit: int
) -> RuntimePage[ItemT]:
    if limit <= 0:
        msg = "page limit must be positive"
        raise ValueError(msg)
    start = 0
    if cursor is not None:
        try:
            start = identities.index(cursor) + 1
        except ValueError as exc:
            msg = "page cursor is not current"
            raise ValueError(msg) from exc
    stop = min(start + limit, len(items))
    return RuntimePage(
        items=tuple(items[start:stop]),
        next_cursor=identities[stop - 1] if stop < len(items) else None,
    )


class RuntimeQuery:
    """Lazy indexed read facade over native runtime stores."""

    def __init__(
        self,
        revision: ChangeRevision,
        work_root: Path,
        history: RepositoryHistory,
        proof_checkouts: ProofCheckoutManager | None = None,
    ) -> None:
        self._revision = revision
        self._work_root = work_root
        self._history = history
        self._jobs = JobStore(work_root)
        self._attempts = AttemptStore(work_root)
        self._findings = FindingStore(work_root)
        self._receipts = ReceiptStore(revision)
        self._proof_checkouts = proof_checkouts
        self.reset()

    def reset(self) -> None:
        """Discard indexes after a general runtime mutation."""
        self._jobs_by_id: dict[int, JobRecord] | None = None
        self._archived_ids: set[int] = set()
        self._attempts_by_job: dict[int, tuple[AttemptEvent, ...]] | None = None
        self._findings_by_job: dict[int, tuple[Finding, ...]] | None = None
        self._findings_by_id: dict[str, Finding] | None = None
        self._receipts_by_id: dict[str, ReceiptRecord] | None = None
        self._requests_by_id: dict[str, StoredRequest] | None = None
        self._validity: dict[tuple[str, str], ReceiptValidity] = {}

    def refresh_closure(self, receipt_ids: tuple[str, ...], job_ids: tuple[int, ...]) -> None:
        """Refresh only identities explicitly returned by invalidation."""
        if self._jobs_by_id is None:
            return
        for job_id in job_ids:
            try:
                stored = self._jobs.read(job_id)
                self._archived_ids.discard(job_id)
            except FileNotFoundError:
                try:
                    stored = self._jobs.read(job_id, archived=True)
                    self._archived_ids.add(job_id)
                except FileNotFoundError:
                    self._jobs_by_id.pop(job_id, None)
                    continue
            self._jobs_by_id[job_id] = stored.job
        if self._receipts_by_id is not None:
            for receipt_id in receipt_ids:
                result = self._receipts.read(receipt_id)
                if result.receipt is not None:
                    self._receipts_by_id[receipt_id] = result.receipt
        affected = set(receipt_ids)
        self._validity = {key: value for key, value in self._validity.items() if key[0] not in affected}

    def list_jobs(
        self,
        *,
        candidate_revision: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> RuntimePage[RuntimeJobProjection]:
        """Project only one numeric job-ID page from lazy indexes."""
        self._ensure_indexes()
        assert self._jobs_by_id is not None
        identities = tuple(str(job_id) for job_id in sorted(self._jobs_by_id))
        id_page = _page(identities, identities, cursor, limit)
        items = tuple(
            self._project_job(self._jobs_by_id[int(identity)], candidate_revision) for identity in id_page.items
        )
        return RuntimePage(items=items, next_cursor=id_page.next_cursor)

    def list_attempts(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[AttemptEvent]:
        """List attempt history by attempt ID and sequence."""
        self._ensure_indexes()
        assert self._attempts_by_job is not None
        items = tuple(
            sorted(
                (event for values in self._attempts_by_job.values() for event in values),
                key=lambda event: (event.attempt_id, event.sequence),
            )
        )
        return _page(items, tuple(f"{item.attempt_id}/{item.sequence}" for item in items), cursor, limit)

    def list_findings(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[Finding]:
        """List finding history by finding ID."""
        self._ensure_indexes()
        assert self._findings_by_job is not None
        items = tuple(
            sorted(
                (finding for values in self._findings_by_job.values() for finding in values),
                key=lambda finding: finding.finding_id,
            )
        )
        return _page(items, tuple(item.finding_id for item in items), cursor, limit)

    def list_receipts(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[ReceiptRecord]:
        """List receipt history by receipt ID."""
        self._ensure_indexes()
        assert self._receipts_by_id is not None
        items = tuple(self._receipts_by_id[receipt_id] for receipt_id in sorted(self._receipts_by_id))
        return _page(items, tuple(item.receipt_id for item in items), cursor, limit)

    def list_requests(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[StoredRequest]:
        """List request history by request ID."""
        self._ensure_indexes()
        assert self._requests_by_id is not None
        items = tuple(self._requests_by_id[request_id] for request_id in sorted(self._requests_by_id))
        return _page(items, tuple(item.request.request_id for item in items), cursor, limit)

    def list_history(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[RuntimeHistoryEntry]:
        """List chronological immutable history across native stores."""
        self._ensure_indexes()
        items = tuple(sorted(self._history_entries(), key=lambda item: (item.timestamp, item.identity)))
        return _page(items, tuple(item.identity for item in items), cursor, limit)

    def work_health(self, *, cursor: str | None = None, limit: int = 100) -> WorkHealthResult:
        """Check only one deterministic path page without mutation."""
        paths = self._health_paths()
        page = _page(paths, paths, cursor, limit)
        findings = tuple(finding for path in page.items for finding in self._check_path(path))
        return WorkHealthResult(
            findings=tuple(sorted(findings, key=lambda item: (item.path, item.code, item.target or ""))),
            checked_paths=page.items,
            next_cursor=page.next_cursor,
        )

    def _ensure_indexes(self) -> None:
        if self._jobs_by_id is not None:
            return
        active = self._jobs.list()
        archived = self._jobs.list(archived=True)
        self._jobs_by_id = {item.job.job_id: item.job for item in (*active, *archived)}
        self._archived_ids = {item.job.job_id for item in archived}
        attempts: dict[int, list[AttemptEvent]] = {}
        for event in self._attempts.list():
            attempts.setdefault(event.job_id, []).append(event)
        self._attempts_by_job = {job_id: tuple(values) for job_id, values in attempts.items()}
        findings: dict[int, list[Finding]] = {}
        for result in self._findings.list():
            if result.finding is not None:
                findings.setdefault(result.finding.source_job_id, []).append(result.finding)
        self._findings_by_job = {job_id: tuple(values) for job_id, values in findings.items()}
        self._findings_by_id = {
            finding.finding_id: finding for values in self._findings_by_job.values() for finding in values
        }
        self._receipts_by_id = {
            result.receipt.receipt_id: result.receipt for result in self._receipts.list() if result.receipt is not None
        }
        self._requests_by_id = self._read_requests()

    def _project_job(self, job: JobRecord, candidate_revision: str) -> RuntimeJobProjection:
        authority = project_job(job, self._revision)
        assert self._attempts_by_job is not None
        assert self._findings_by_job is not None
        assert self._findings_by_id is not None
        assert self._receipts_by_id is not None
        assert self._requests_by_id is not None
        attempts = self._attempts_by_job.get(job.job_id, ())
        findings = self._findings_by_job.get(job.job_id, ())
        receipt = self._receipts_by_id.get(job.receipt_id) if job.receipt_id else None
        return RuntimeJobProjection(
            job_id=job.job_id,
            kind=job.kind,
            priority=job.priority,
            change_id=job.change_id,
            delivery_digest=job.delivery_digest,
            target_node_id=job.target_node_id,
            title=authority.title,
            outcome=authority.outcome,
            acceptance=authority.acceptance,
            modules=authority.modules,
            interfaces=authority.interfaces,
            proof=authority.proof,
            dependency_ready=all(
                self._dependency_current(item, candidate_revision) for item in job.predecessor_job_ids
            ),
            claim_id=job.claim_id,
            requests=tuple(
                self._requests_by_id[request_id]
                for request_id in job.pending_request_ids
                if request_id in self._requests_by_id
            ),
            block_id=job.block_id,
            attempt=(
                max(attempts, key=lambda item: (item.timestamp, item.attempt_id, item.sequence)) if attempts else None
            ),
            finding=(
                self._findings_by_id.get(job.finding_id)
                if job.finding_id is not None
                else max(findings, key=lambda item: (item.created_at, item.finding_id))
                if findings
                else None
            ),
            receipt=receipt,
            validity=self._receipt_validity(receipt.receipt_id, candidate_revision) if receipt else None,
            disposition=job.disposition,
        )

    def _dependency_current(self, job_id: int, candidate_revision: str) -> bool:
        assert self._jobs_by_id is not None
        predecessor = self._jobs_by_id.get(job_id)
        if predecessor is None or job_id not in self._archived_ids or predecessor.receipt_id is None:
            return False
        return self._receipt_validity(predecessor.receipt_id, candidate_revision).current

    def _receipt_validity(self, receipt_id: str, candidate_revision: str) -> ReceiptValidity:
        key = (receipt_id, candidate_revision)
        if key not in self._validity:
            self._validity[key] = self._receipts.evaluate_currentness(receipt_id, self._history, candidate_revision)
        return self._validity[key]

    def _history_entries(self) -> tuple[RuntimeHistoryEntry, ...]:
        assert self._attempts_by_job is not None
        assert self._findings_by_job is not None
        assert self._receipts_by_id is not None
        assert self._requests_by_id is not None
        entries = [
            RuntimeHistoryEntry(
                identity=f"attempt:{event.attempt_id}/{event.sequence}",
                timestamp=event.timestamp,
                kind="attempt",
                job_id=event.job_id,
                attempt=event,
            )
            for values in self._attempts_by_job.values()
            for event in values
        ]
        entries.extend(
            RuntimeHistoryEntry(
                identity=f"finding:{finding.finding_id}",
                timestamp=finding.created_at,
                kind="finding",
                job_id=finding.source_job_id,
                finding=finding,
            )
            for values in self._findings_by_job.values()
            for finding in values
        )
        entries.extend(
            RuntimeHistoryEntry(
                identity=f"receipt:{receipt.receipt_id}",
                timestamp=receipt.issued_at,
                kind="receipt",
                receipt=receipt,
            )
            for receipt in self._receipts_by_id.values()
        )
        entries.extend(
            RuntimeHistoryEntry(
                identity=f"request:{request.request.request_id}",
                timestamp=request.request.created_at,
                kind="request",
                job_id=request.request.job_ids[0] if len(request.request.job_ids) == 1 else None,
                request=request,
            )
            for request in self._requests_by_id.values()
        )
        return tuple(entries)

    def _health_paths(self) -> tuple[str, ...]:
        paths: list[str] = []
        for root, prefix in (
            (self._work_root / "jobs", "jobs"),
            (self._work_root / "archive", "archive"),
            (self._work_root / "findings", "findings"),
            (self._work_root / ".runtime-transactions", ".runtime-transactions"),
            (self._revision.source_dir / "receipts", "receipts"),
        ):
            paths.extend(self._entries(root, prefix))
        attempts = self._work_root / "attempts"
        if attempts.is_dir():
            for directory in sorted(attempts.iterdir(), key=lambda item: item.name):
                if directory.is_symlink() or not directory.is_dir():
                    paths.append(f"attempts/{directory.name}")
                else:
                    paths.extend(self._entries(directory, f"attempts/{directory.name}"))
        for status in ("pending", "resolved"):
            paths.extend(self._entries(self._work_root / "requests" / status, f"requests/{status}"))
        if self._proof_checkouts is not None:
            paths.extend(f"proof-checkouts/{path}" for path in self._proof_checkouts.health_paths())
        return tuple(sorted(paths))

    @staticmethod
    def _entries(root: Path, prefix: str) -> tuple[str, ...]:
        if not root.is_dir():
            return ()
        return tuple(f"{prefix}/{item.name}" for item in sorted(root.iterdir(), key=lambda item: item.name))

    def _check_path(self, path: str) -> tuple[WorkHealthFinding, ...]:  # noqa: PLR0911
        if path.startswith("proof-checkouts/"):
            return self._check_proof_checkout(path)
        if path.startswith(".runtime-transactions/"):
            return self._check_manifest(path)
        if path.startswith(("jobs/", "archive/")):
            return self._check_job(path)
        if path.startswith("attempts/"):
            return self._check_attempt(path)
        if path.startswith("findings/"):
            return self._check_finding(path)
        if path.startswith("requests/"):
            return self._check_request(path)
        return self._check_receipt(path)

    def _check_proof_checkout(self, path: str) -> tuple[WorkHealthFinding, ...]:
        if self._proof_checkouts is None or not self._proof_checkouts.is_orphan(path.removeprefix("proof-checkouts/")):
            return self._finding("ERR_WORK_PATH_UNSAFE", "proof checkout path is not canonical", path)
        return self._finding(
            "ERR_WORK_PROOF_CHECKOUT_ORPHAN",
            "proof checkout requires cleanup",
            path,
            path.removeprefix("proof-checkouts/"),
        )

    @staticmethod
    def _finding(code: str, detail: str, path: str, target: str | None = None) -> tuple[WorkHealthFinding, ...]:
        return (WorkHealthFinding(code=code, detail=detail, path=path, target=target),)

    def _check_manifest(self, path: str) -> tuple[WorkHealthFinding, ...]:
        try:
            RuntimeTransaction._from_manifest(  # noqa: SLF001 - health validates without recovering.
                self._work_root.resolve(),
                self._work_root / path,
                (self._work_root.resolve(), self._revision.source_dir.resolve()),
            )
        except OSError, TypeError, ValueError:
            return self._finding("ERR_WORK_MANIFEST_INVALID", "transaction manifest is invalid", path)
        return self._finding("ERR_WORK_MANIFEST_PENDING", "transaction manifest requires recovery", path)

    def _check_job(self, path: str) -> tuple[WorkHealthFinding, ...]:  # noqa: C901, PLR0911
        absolute = self._work_root / path
        if absolute.is_symlink() or not absolute.is_file() or absolute.suffix != ".yaml" or not absolute.stem.isdigit():
            return self._finding("ERR_WORK_PATH_UNSAFE", "job path is not canonical", path)
        job_id = int(absolute.stem)
        try:
            job = self._jobs.read(job_id, archived=path.startswith("archive/")).job
        except FileNotFoundError, OSError, TypeError, ValueError, YAMLError:
            return self._finding("ERR_WORK_JOB_INVALID", "job record is malformed or unsafe", path)
        if self._jobs_by_id is not None and self._jobs_by_id.get(job_id) != job:
            return self._finding("ERR_WORK_INDEX_DISAGREEMENT", "job index disagrees with storage", path, str(job_id))
        if job.change_id != self._revision.change_id or job.delivery_digest != self._revision.delivery_digest:
            return self._finding("ERR_WORK_DIGEST_STALE", "job authority identity is stale", path, str(job_id))
        missing = next((item for item in job.predecessor_job_ids if not self._job_exists(item)), None)
        if missing is not None:
            return self._finding("ERR_WORK_PREDECESSOR_MISSING", "job predecessor is missing", path, str(missing))
        missing_request = next(
            (
                item
                for item in job.pending_request_ids
                if not (self._work_root / "requests/pending" / f"{item}.yaml").is_file()
            ),
            None,
        )
        if missing_request is not None:
            return self._finding("ERR_WORK_REQUEST_MISSING", "pending request is missing", path, missing_request)
        if (job.claim_id is None) != (job.attempt_id is None):
            return self._finding("ERR_WORK_CLAIM_INVALID", "claim and attempt pointers disagree", path, str(job_id))
        if job.receipt_id is not None and not self._receipt_path(job.receipt_id).is_file():
            return self._finding("ERR_WORK_RECEIPT_MISSING", "job receipt is missing", path, job.receipt_id)
        if job.superseded_by_receipt_id is not None:
            supersession = self._receipts.read(job.superseded_by_receipt_id).receipt
            if (
                supersession is None
                or supersession.kind != "supersession"
                or not self._supersession_reaches_job(job, supersession)
            ):
                return self._finding(
                    "ERR_WORK_SUPERSESSION_BROKEN",
                    "job supersession chain is broken",
                    path,
                    job.superseded_by_receipt_id,
                )
        return ()

    def _supersession_reaches_job(self, job: JobRecord, supersession: ReceiptRecord) -> bool:
        invalidated = {
            receipt_id
            for receipt_id in supersession.payload.get("invalidated_receipt_ids", ())
            if isinstance(receipt_id, str)
        }
        if job.receipt_id in invalidated:
            return True
        pending = list(job.predecessor_job_ids)
        visited: set[int] = set()
        while pending:
            predecessor_id = pending.pop()
            if predecessor_id in visited:
                continue
            visited.add(predecessor_id)
            predecessor = None
            for archived in (False, True):
                try:
                    predecessor = self._jobs.read(predecessor_id, archived=archived).job
                except FileNotFoundError, OSError, TypeError, ValueError:
                    continue
                break
            if predecessor is None:
                continue
            if predecessor.receipt_id in invalidated:
                return True
            pending.extend(predecessor.predecessor_job_ids)
        return False

    def _check_attempt(self, path: str) -> tuple[WorkHealthFinding, ...]:
        absolute = self._work_root / path
        parts = Path(path).parts
        if (
            absolute.is_symlink()
            or not absolute.is_file()
            or len(parts) != _ATTEMPT_PATH_PARTS
            or not absolute.stem.isdigit()
        ):
            return self._finding("ERR_WORK_PATH_UNSAFE", "attempt path is not canonical", path)
        result = self._attempts.read(parts[1], int(absolute.stem))
        if result.event is None:
            return self._finding(result.diagnostics[0].code.value, result.diagnostics[0].detail, path)
        if not self._job_exists(result.event.job_id):
            return self._finding("ERR_WORK_ATTEMPT_ORPHAN", "attempt job is missing", path, str(result.event.job_id))
        return ()

    def _check_finding(self, path: str) -> tuple[WorkHealthFinding, ...]:
        absolute = self._work_root / path
        if absolute.is_symlink() or not absolute.is_file() or absolute.suffix != ".yaml":
            return self._finding("ERR_WORK_PATH_UNSAFE", "finding path is not canonical", path)
        result = self._findings.read(absolute.stem)
        if result.finding is None:
            return self._finding(result.diagnostics[0].code.value, result.diagnostics[0].detail, path)
        if not self._job_exists(result.finding.source_job_id):
            return self._finding(
                "ERR_WORK_FINDING_ORPHAN",
                "finding source job is missing",
                path,
                str(result.finding.source_job_id),
            )
        return ()

    def _check_request(self, path: str) -> tuple[WorkHealthFinding, ...]:
        absolute = self._work_root / path
        if absolute.is_symlink() or not absolute.is_file() or absolute.suffix != ".yaml":
            return self._finding("ERR_WORK_PATH_UNSAFE", "request path is not canonical", path)
        try:
            value = self._load_mapping(absolute)
            job_ids = value.get("job_ids", ()) if path.startswith("requests/pending/") else ()
        except OSError, TypeError, ValueError:
            return self._finding("ERR_WORK_REQUEST_INVALID", "request record is malformed", path)
        missing = next((item for item in job_ids if isinstance(item, int) and not self._job_exists(item)), None)
        if missing is not None:
            return self._finding("ERR_WORK_REQUEST_ORPHAN", "request job is missing", path, str(missing))
        if (
            path.startswith("requests/resolved/")
            and not (self._work_root / "requests/pending" / absolute.name).is_file()
        ):
            return self._finding(
                "ERR_WORK_RESOLUTION_ORPHAN",
                "request resolution has no request",
                path,
                absolute.stem,
            )
        return ()

    def _check_receipt(self, path: str) -> tuple[WorkHealthFinding, ...]:
        absolute = self._revision.source_dir / path
        if absolute.is_symlink() or not absolute.is_file() or absolute.suffix != ".yaml":
            return self._finding("ERR_WORK_PATH_UNSAFE", "receipt path is not canonical", path)
        result = self._receipts.read(absolute.stem)
        if result.receipt is None:
            diagnostic = result.diagnostics[0]
            return self._finding(diagnostic.code.value, diagnostic.detail, path, diagnostic.target)
        receipt = result.receipt
        if self._receipts_by_id is not None and self._receipts_by_id.get(receipt.receipt_id) != receipt:
            return self._finding(
                "ERR_WORK_INDEX_DISAGREEMENT",
                "receipt index disagrees with storage",
                path,
                receipt.receipt_id,
            )
        references = receipt.payload.get("predecessor_receipt_ids", ())
        if receipt.kind == "supersession":
            references = (*references, *receipt.payload.get("invalidated_receipt_ids", ()))
        missing = next(
            (item for item in references if isinstance(item, str) and not self._receipt_path(item).is_file()),
            None,
        )
        if missing is not None:
            return self._finding("ERR_WORK_RECEIPT_REFERENCE_MISSING", "receipt reference is missing", path, missing)
        return ()

    @staticmethod
    def _load_mapping(path: Path) -> Mapping[str, object]:
        value = make_yaml().load(path.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            msg = "runtime document must be a mapping"
            raise TypeError(msg)
        return value

    def _read_requests(self) -> dict[str, StoredRequest]:
        pending = self._work_root / "requests/pending"
        if not pending.is_dir():
            return {}
        records: dict[str, StoredRequest] = {}
        for path in sorted(pending.glob("*.yaml")):
            value = dict(self._load_mapping(path))
            for field in ("job_ids", "options", "evidence"):
                if isinstance(value.get(field), list):
                    value[field] = tuple(value[field])
            if isinstance(value.get("options"), tuple):
                value["options"] = tuple(
                    {
                        **option,
                        **{
                            field: tuple(option[field])
                            for field in ("pros", "cons", "risks")
                            if isinstance(option.get(field), list)
                        },
                    }
                    for option in value["options"]
                )
            request = NativeRequest.model_validate(value)
            resolution_path = self._work_root / "requests/resolved" / path.name
            resolution = (
                RequestResolution.model_validate(self._load_mapping(resolution_path))
                if resolution_path.is_file()
                else None
            )
            records[request.request_id] = StoredRequest(request=request, resolution=resolution)
        return records

    def _job_exists(self, job_id: int) -> bool:
        for archived in (False, True):
            try:
                self._jobs.read(job_id, archived=archived)
            except FileNotFoundError, OSError, TypeError, ValueError:
                continue
            return True
        return False

    def _receipt_path(self, receipt_id: str) -> Path:
        return self._revision.source_dir / "receipts" / f"{receipt_id}.yaml"


__all__ = [
    "RuntimeHistoryEntry",
    "RuntimeJobProjection",
    "RuntimePage",
    "RuntimeQuery",
    "WorkHealthFinding",
    "WorkHealthResult",
]
