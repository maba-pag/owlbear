"""Atomic public admission of a revision and its initial plan jobs."""

from __future__ import annotations

from collections.abc import Mapping
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Never

from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

from owlbear_kanban.admission import AdmissionAssessment, AdmissionEvidence, evaluate_admission
from owlbear_kanban.jobs import JobGeneration, plan_jobs, read_job_generation
from owlbear_kanban.receipt import ReceiptRecord, ReceiptStore
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionConflictError, TransactionParticipant
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


class AdmissionTransaction:
    """Compose admission evaluation and all-or-none receipt/job publication."""

    def __init__(self, revision: ChangeRevision) -> None:
        self.revision = revision

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
        receipt_id = receipt_id or f"admission-{self.revision.delivery_digest[:12]}"
        job_ids = tuple(job_ids or range(1, len(self.revision.graph.nodes) + 1))
        generation = plan_jobs(self.revision, receipt_id, job_ids, timestamp=timestamp)
        try:
            receipt = ReceiptRecord(
                schema_version=1,
                kind="admission",
                receipt_id=receipt_id,
                change_id=self.revision.change_id,
                delivery_digest=self.revision.delivery_digest,
                issued_at=timestamp,
                payload={
                    "assessment": assessment.model_dump(mode="json"),
                    "evidence": evidence.model_dump(mode="json"),
                    "generation": generation.model_dump(mode="json"),
                },
            )
        except ValidationError as exc:
            raise AdmissionValidationError from exc
        transaction = self._transaction(receipt, generation)
        try:
            transaction.recover()
            existing = ReceiptStore(self.revision).read(receipt_id)
            existing_generation = _read_generation(self.revision.source_dir / "jobs", receipt_id, self.revision)
            if existing.receipt is not None:
                if existing.receipt == receipt and existing_generation == generation:
                    return existing.receipt, generation, assessment
                _raise_conflict()
            transaction.commit(failure=failure)
        except TransactionConflictError as exc:
            raise AdmissionConflictError from exc
        except AdmissionConflictError:
            raise
        except AdmissionPublicationError:
            raise
        except Exception as exc:
            raise AdmissionPublicationError(exc) from exc
        return receipt, generation, assessment

    def _transaction(self, receipt: ReceiptRecord, generation: JobGeneration) -> RuntimeTransaction:
        return RuntimeTransaction(
            self.revision.source_dir,
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
            ),
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
    **kwargs: object,
) -> tuple[ReceiptRecord | None, JobGeneration | None, AdmissionAssessment]:
    """Validate and atomically admit one loaded revision."""
    return AdmissionTransaction(revision).validate_and_admit(evidence, **kwargs)


__all__ = [
    "AdmissionConflictError",
    "AdmissionPublicationError",
    "AdmissionTransaction",
    "AdmissionValidationError",
    "validate_and_admit",
]
