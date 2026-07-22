"""Atomic public admission of a revision and its initial shape jobs."""

from __future__ import annotations

import contextlib
import fcntl
import os
import secrets
from threading import RLock
from typing import TYPE_CHECKING, ClassVar

from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from pathlib import Path

from owlbear_kanban.admission import AdmissionAssessment, AdmissionEvidence, evaluate_admission
from owlbear_kanban.jobs import JobGeneration, plan_shape_jobs, read_job_generation
from owlbear_kanban.receipt import ReceiptRecord, ReceiptStore
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

    _locks: ClassVar[dict[Path, RLock]] = {}
    _locks_guard = RLock()

    def __init__(self, revision: ChangeRevision) -> None:
        self.revision = revision

    @classmethod
    def _lock_for(cls, source_dir: Path) -> RLock:
        with cls._locks_guard:
            return cls._locks.setdefault(source_dir.resolve(), RLock())

    def validate_and_admit(
        self,
        evidence: AdmissionEvidence,
        *,
        receipt_id: str | None = None,
        job_ids: Sequence[int] | None = None,
        timestamp: str = "1970-01-01T00:00:00Z",
        failure: Callable[[str], None] | None = None,
    ) -> tuple[ReceiptRecord | None, JobGeneration | None, AdmissionAssessment]:
        assessment = evaluate_admission(self.revision, evidence)
        if not assessment.admitted:
            return None, None, assessment
        receipt_id = receipt_id or f"admission-{self.revision.delivery_digest[:12]}"
        job_ids = tuple(job_ids or range(1, len(self.revision.graph.nodes) + 1))
        generation = plan_shape_jobs(self.revision, receipt_id, job_ids, timestamp=timestamp)
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
                    "generation": generation.model_dump(mode="json"),
                },
            )
        except ValidationError as exc:
            raise AdmissionValidationError from exc
        source = self.revision.source_dir
        jobs_dir = source / "jobs"
        with self._lock_for(source), _process_lock(source):
            existing = ReceiptStore(self.revision).read(receipt_id)
            if existing.receipt is not None:
                existing_generation = _read_generation(jobs_dir, receipt_id, self.revision)
                if existing.receipt == receipt and existing_generation == generation:
                    return existing.receipt, generation, assessment
                raise AdmissionConflictError
            try:
                self._publish(receipt, generation, jobs_dir, failure)
            except (AdmissionConflictError, AdmissionPublicationError):
                raise
            except Exception as exc:
                raise AdmissionPublicationError(exc) from exc
        return receipt, generation, assessment

    def _publish(
        self,
        receipt: ReceiptRecord,
        generation: JobGeneration,
        jobs_dir: Path,
        failure: Callable[[str], None] | None,
    ) -> None:
        jobs_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = self.revision.source_dir / "receipts" / f"{receipt.receipt_id}.yaml"
        generation_path = jobs_dir / f"{generation.receipt_id}.yaml"
        temp_paths: list[Path] = []
        published_paths: list[Path] = []
        try:
            for path, value in (
                (receipt_path, receipt.to_mapping()),
                (generation_path, generation.model_dump(mode="json")),
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                temp = path.with_name(f".tmp-{secrets.token_hex(12)}-{path.name}")
                with temp.open("x", encoding="utf-8") as handle:
                    make_yaml(explicit_start=True).dump(value, handle)
                    handle.flush()
                    os.fsync(handle.fileno())
                temp_paths.append(temp)
            if failure:
                failure("before-publication")
            os.link(temp_paths[0], receipt_path)
            published_paths.append(receipt_path)
            if failure:
                failure("after-receipt")
            os.link(temp_paths[1], generation_path)
            published_paths.append(generation_path)
            _fsync_directory(receipt_path.parent)
            _fsync_directory(generation_path.parent)
        except Exception:
            for path in (*published_paths, *temp_paths):
                with contextlib.suppress(OSError):
                    path.unlink()
            raise
        finally:
            for path in temp_paths:
                with contextlib.suppress(OSError):
                    path.unlink()


def _read_generation(jobs_dir: Path, receipt_id: str, revision: ChangeRevision) -> JobGeneration | None:
    path = jobs_dir / f"{receipt_id}.yaml"
    if not path.is_file():
        return None
    generation, diagnostics = read_job_generation(make_yaml().load(path.read_text(encoding="utf-8")), revision)
    if diagnostics or generation is None or generation.receipt_id != receipt_id:
        return None
    return generation


@contextlib.contextmanager
def _process_lock(source_dir: Path) -> Iterator[None]:
    lock_path = source_dir / ".admission.lock"
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _fsync_directory(directory: Path) -> None:
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


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
