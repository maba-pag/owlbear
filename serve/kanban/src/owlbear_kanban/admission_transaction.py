"""Atomic public admission of a revision and its initial plan jobs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Never

from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

from owlbear_kanban.admission import AdmissionAssessment, AdmissionEvidence, evaluate_admission
from owlbear_kanban.jobs import JobGeneration, JobRecord, JobStore, plan_jobs, read_job_generation
from owlbear_kanban.receipt import ReceiptRecord, ReceiptStore
from owlbear_kanban.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)
from owlbear_kanban.yaml_rt import make_yaml

if TYPE_CHECKING:
    from owlbear_kanban.change import ChangeRevision


class AdmissionConflictError(RuntimeError):
    """The native stores contain incompatible admission identities."""

    code = "ERR_ADMISSION_CONFLICT"


class AdmissionValidationError(ValueError):
    """The admission request contains an invalid immutable identity."""

    code = "ERR_ADMISSION_VALIDATION"

    def __init__(self) -> None:
        super().__init__(self.code)


class AdmissionPublicationError(RuntimeError):
    """A staged receipt/job publication failed before commit."""

    code = "ERR_ADMISSION_PUBLICATION"

    def __init__(self, cause: Exception) -> None:
        super().__init__(self.code)
        self.cause = cause


@dataclass(frozen=True)
class _AdmissionContext:
    receipt_id: str
    evidence: AdmissionEvidence
    assessment: AdmissionAssessment
    timestamp: str


class AdmissionTransaction:
    """Compose admission evaluation and all-or-none receipt/job publication."""

    def __init__(self, revision: ChangeRevision, work_root: Path) -> None:
        self.revision = revision
        self._work_root = work_root
        self._jobs = JobStore(work_root)

    def validate_and_admit(
        self,
        evidence: AdmissionEvidence,
        *,
        receipt_id: str | None = None,
        job_ids: Sequence[int] | None = None,
        timestamp: str = "1970-01-01T00:00:00Z",
        failure: Callable[[str], None] | None = None,
    ) -> tuple[ReceiptRecord | None, JobGeneration | None, AdmissionAssessment]:
        """Evaluate a revision and atomically publish its admission receipt and plan jobs."""
        assessment = evaluate_admission(self.revision, evidence)
        if not assessment.admitted:
            return None, None, assessment
        context = _AdmissionContext(
            receipt_id=receipt_id or f"admission-{self.revision.delivery_digest[:12]}",
            evidence=evidence,
            assessment=assessment,
            timestamp=timestamp,
        )
        try:
            RuntimeTransaction.recover_all(
                self._work_root,
                roots=(self._work_root, self.revision.source_dir),
            )
            replay = self._replay(context)
            if replay is not None:
                return replay
            return self._publish(context, job_ids, failure)
        except ValidationError as exc:
            raise AdmissionValidationError from exc
        except TransactionConflictError as exc:
            raise AdmissionConflictError from exc
        except AdmissionConflictError:
            raise
        except AdmissionPublicationError:
            raise
        except Exception as exc:
            raise AdmissionPublicationError(exc) from exc

    def _publish(
        self,
        context: _AdmissionContext,
        job_ids: Sequence[int] | None,
        failure: Callable[[str], None] | None,
    ) -> tuple[ReceiptRecord, JobGeneration, AdmissionAssessment]:
        automatic_ids = job_ids is None
        for attempt in range(2 if automatic_ids else 1):
            reservation = self._jobs.reserve_job_ids(len(self.revision.graph.nodes)) if automatic_ids else None
            selected_ids = reservation.job_ids if reservation is not None else tuple(job_ids or ())
            generation = plan_jobs(
                self.revision,
                context.receipt_id,
                selected_ids,
                timestamp=context.timestamp,
            )
            if not automatic_ids:
                self._reject_existing_job_ids(selected_ids)
            receipt = _receipt(self.revision, context, generation)
            participants = (
                *((reservation.participant,) if reservation is not None else ()),
                *(
                    self._jobs.create_participant(JobRecord(schema_version=1, **job.model_dump()))
                    for job in generation.jobs
                ),
            )
            try:
                self._transaction(receipt, generation, participants).commit(failure=failure)
            except TransactionConflictError:
                if not automatic_ids or attempt > 0:
                    raise
                replay = self._replay(context)
                if replay is not None:
                    return replay
                continue
            return receipt, generation, context.assessment
        msg = "admission transaction exhausted without an outcome"
        raise AssertionError(msg)

    def _reject_existing_job_ids(self, job_ids: Sequence[int]) -> None:
        for job_id in job_ids:
            for archived in (False, True):
                try:
                    self._jobs.read(job_id, archived=archived)
                except FileNotFoundError:
                    continue
                except OSError, ValueError:
                    _raise_conflict()
                _raise_conflict()

    def _replay(
        self,
        context: _AdmissionContext,
    ) -> tuple[ReceiptRecord, JobGeneration, AdmissionAssessment] | None:
        receipt_path = self.revision.source_dir / "receipts" / f"{context.receipt_id}.yaml"
        generation_path = self.revision.source_dir / "jobs" / f"{context.receipt_id}.yaml"
        if not receipt_path.exists() and not generation_path.exists():
            return None
        existing = ReceiptStore(self.revision).read(context.receipt_id)
        generation = _read_generation(self.revision.source_dir / "jobs", context.receipt_id, self.revision)
        if existing.receipt is None or generation is None:
            _raise_conflict()
        expected_receipt = _receipt(self.revision, context, generation)
        if existing.receipt != expected_receipt:
            _raise_conflict()
        for planned in generation.jobs:
            expected_job = JobRecord(schema_version=1, **planned.model_dump())
            try:
                stored = self._jobs.read(planned.job_id)
            except FileNotFoundError, OSError, ValueError:
                _raise_conflict()
            if stored.job != expected_job:
                _raise_conflict()
        return existing.receipt, generation, context.assessment

    def _transaction(
        self,
        receipt: ReceiptRecord,
        generation: JobGeneration,
        work_participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...],
    ) -> RuntimeTransaction:
        return RuntimeTransaction(
            self._work_root,
            f"admission-{receipt.receipt_id}",
            (
                TransactionParticipant(
                    self.revision.source_dir,
                    Path("receipts") / f"{receipt.receipt_id}.yaml",
                    _yaml_bytes(receipt.to_mapping()),
                ),
                TransactionParticipant(
                    self.revision.source_dir,
                    Path("jobs") / f"{generation.receipt_id}.yaml",
                    _yaml_bytes(generation.model_dump(mode="json")),
                ),
                *work_participants,
            ),
        )


def _receipt(
    revision: ChangeRevision,
    context: _AdmissionContext,
    generation: JobGeneration,
) -> ReceiptRecord:
    return ReceiptRecord(
        schema_version=1,
        kind="admission",
        receipt_id=context.receipt_id,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        issued_at=context.timestamp,
        payload={
            "assessment": context.assessment.model_dump(mode="json"),
            "evidence": context.evidence.model_dump(mode="json"),
            "generation": generation.model_dump(mode="json"),
        },
    )


def _read_generation(jobs_dir: Path, receipt_id: str, revision: ChangeRevision) -> JobGeneration | None:
    path = jobs_dir / f"{receipt_id}.yaml"
    if not path.is_file():
        return None
    generation, diagnostics = read_job_generation(make_yaml().load(path.read_text(encoding="utf-8")), revision)
    if diagnostics or generation is None or generation.receipt_id != receipt_id:
        return None
    return generation


def _yaml_bytes(value: object) -> bytes:
    stream = StringIO()
    make_yaml(explicit_start=True).dump(_plain_value(value), stream)
    return stream.getvalue().encode("utf-8")


def _plain_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_value(item) for item in value]
    if isinstance(value, list):
        return [_plain_value(item) for item in value]
    return value


def _raise_conflict() -> Never:
    raise AdmissionConflictError


def validate_and_admit(
    revision: ChangeRevision,
    evidence: AdmissionEvidence,
    work_root: Path,
    **kwargs: object,
) -> tuple[ReceiptRecord | None, JobGeneration | None, AdmissionAssessment]:
    """Validate and atomically admit one loaded revision."""
    return AdmissionTransaction(revision, work_root).validate_and_admit(evidence, **kwargs)


__all__ = [
    "AdmissionConflictError",
    "AdmissionPublicationError",
    "AdmissionTransaction",
    "AdmissionValidationError",
    "validate_and_admit",
]
