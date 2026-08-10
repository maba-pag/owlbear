"""Durable exact-candidate Integration verification."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import signal
import subprocess
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionParticipant
from owlbear_delivery.storage_io import locked_roots

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from owlbear_delivery.change_workspace import AtomicIntegrationPreparation
    from owlbear_delivery.delivery_runtime import DeliveryIntegrationCandidate

INTEGRATION_VERIFICATION_PROFILE_PATH = ".owlbear/delivery/verification.json"
_OUTPUT_LIMIT = 8_192
_DIAGNOSTIC_LIMIT = 1_024


class _VerificationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class IntegrationVerificationStep(_VerificationModel):
    """One ordered argv verification step."""

    step_id: str = Field(max_length=128, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    argv: tuple[Annotated[str, Field(min_length=1, max_length=1_024)], ...] = Field(min_length=1)
    cwd: str = Field(default=".", min_length=1, max_length=512)
    timeout_seconds: int = Field(gt=0, le=3_600)

    @model_validator(mode="after")
    def _validate_cwd(self) -> IntegrationVerificationStep:
        path = PurePosixPath(self.cwd)
        if path.is_absolute() or ".." in path.parts:
            message = "verification cwd must stay within the candidate checkout"
            raise ValueError(message)
        return self


class IntegrationVerificationProfile(_VerificationModel):
    """Tracked project policy governing every Integration candidate."""

    schema_version: Literal[1]
    pass_environment: tuple[str, ...] = Field(max_length=32)
    steps: tuple[IntegrationVerificationStep, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def _validate_unique_values(self) -> IntegrationVerificationProfile:
        step_ids = tuple(step.step_id for step in self.steps)
        if len(step_ids) != len(set(step_ids)):
            message = "verification step IDs must be unique"
            raise ValueError(message)
        if len(self.pass_environment) != len(set(self.pass_environment)):
            message = "verification environment names must be unique"
            raise ValueError(message)
        for name in self.pass_environment:
            if not name or not name.replace("_", "A").isalnum() or not name[0].isalpha():
                message = "verification environment names must be portable identifiers"
                raise ValueError(message)
        return self


class IntegrationVerificationProfileState(StrEnum):
    """Authority state observed while binding a verification request."""

    CONFIGURED = "configured"
    UNCONFIGURED = "unconfigured"
    INVALID = "invalid"
    CHANGED = "changed"


class IntegrationVerificationProfileBinding(_VerificationModel):
    """Target and candidate profile identities bound before execution."""

    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_profile_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    profile_state: IntegrationVerificationProfileState
    profile: IntegrationVerificationProfile | None = None
    profile_diagnostic: str | None = Field(default=None, max_length=1_024)


class IntegrationVerificationRequest(_VerificationModel):
    """Immutable exact-candidate verification authority."""

    request_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    candidate_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    candidate_ref: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    completion_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_profile_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    profile_state: IntegrationVerificationProfileState
    profile: IntegrationVerificationProfile | None = None
    profile_diagnostic: str | None = Field(default=None, max_length=1_024)

    @model_validator(mode="after")
    def _validate_profile_state(self) -> IntegrationVerificationRequest:
        configured = self.profile_state == IntegrationVerificationProfileState.CONFIGURED
        if configured != (self.profile is not None):
            message = "configured verification requests require exactly one parsed profile"
            raise ValueError(message)
        if configured == (self.profile_diagnostic is not None):
            message = "unconfigured verification requests require one diagnostic"
            raise ValueError(message)
        return self

    @classmethod
    def create(
        cls,
        candidate: DeliveryIntegrationCandidate,
        preparation: AtomicIntegrationPreparation,
        binding: IntegrationVerificationProfileBinding,
    ) -> IntegrationVerificationRequest:
        """Bind one request ID to all publication-critical identities."""
        if (
            preparation.candidate_commit is None
            or preparation.candidate_ref is None
            or preparation.target_head is None
            or preparation.change_head is None
        ):
            message = "verification requires one complete Integration preparation"
            raise ValueError(message)
        payload = {
            "candidate_commit": preparation.candidate_commit,
            "candidate_id": candidate.candidate_id,
            "candidate_profile_digest": binding.candidate_profile_digest,
            "candidate_ref": preparation.candidate_ref,
            "change_head": preparation.change_head,
            "change_id": candidate.change_id,
            "completion_id": candidate.completion_id,
            "package_id": candidate.package_id,
            "profile_digest": binding.profile_digest,
            "profile_state": binding.profile_state,
            "target_head": preparation.target_head,
        }
        return cls(
            request_id=hashlib.sha256(
                _canonical({**payload, "profile_state": binding.profile_state.value})
            ).hexdigest(),
            **payload,
            profile=binding.profile,
            profile_diagnostic=binding.profile_diagnostic,
        )


class IntegrationVerificationStepStatus(StrEnum):
    """Mechanical result of one declared verification step."""

    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed-out"
    EXECUTION_ERROR = "execution-error"


class IntegrationVerificationStepReceipt(_VerificationModel):
    """Bounded process evidence for one verification step."""

    step_id: str = Field(min_length=1)
    status: IntegrationVerificationStepStatus
    exit_code: int | None = None
    stdout: str = Field(max_length=_OUTPUT_LIMIT)
    stderr: str = Field(max_length=_OUTPUT_LIMIT)


class IntegrationVerificationStatus(StrEnum):
    """Terminal mechanical disposition of one exact request."""

    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed-out"
    EXECUTION_ERROR = "execution-error"
    UNCONFIGURED = "unconfigured"
    INVALID_PROFILE = "invalid-profile"
    PROFILE_CHANGED = "profile-changed"
    CANDIDATE_MISSING = "candidate-missing"
    CANDIDATE_MUTATED = "candidate-mutated"
    CLEANUP_FAILED = "cleanup-failed"


class IntegrationVerificationReceipt(_VerificationModel):
    """Durable bounded proof bound to one exact request."""

    request_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: IntegrationVerificationStatus
    steps: tuple[IntegrationVerificationStepReceipt, ...] = ()
    diagnostics: tuple[Annotated[str, Field(min_length=1, max_length=1_024)], ...] = Field(max_length=16)

    @property
    def passed(self) -> bool:
        """Return whether this receipt authorizes publication."""
        return self.status == IntegrationVerificationStatus.PASSED


class IntegrationVerificationStore:
    """Persist exact requests and receipts through runtime transactions."""

    def __init__(self, target_root: Path) -> None:
        self._target_root = target_root.resolve()
        RuntimeTransaction.recover_all(self._target_root)

    def publish_request(self, request: IntegrationVerificationRequest) -> IntegrationVerificationRequest:
        """Publish or replay one immutable request."""
        self._publish("requests", request.request_id, request)
        return request

    def publish_receipt(self, receipt: IntegrationVerificationReceipt) -> IntegrationVerificationReceipt:
        """Publish or replay one immutable receipt."""
        self._publish("receipts", receipt.request_id, receipt)
        return receipt

    def read_receipt(self, request_id: str) -> IntegrationVerificationReceipt | None:
        """Read one existing exact receipt when present."""
        path = self._path("receipts", request_id)
        if not path.exists():
            return None
        return IntegrationVerificationReceipt.model_validate_json(path.read_bytes())

    def verification_lock(self, request_id: str) -> AbstractContextManager[None]:
        """Serialize execution only for one exact request identity."""
        root = self._target_root / "claims" / "integration-verification" / "locks" / request_id
        return locked_roots((root,))

    def _publish(self, kind: str, identity: str, model: _VerificationModel) -> None:
        relative = Path("claims/integration-verification") / kind / f"{identity}.json"
        content = model.model_dump_json(indent=2).encode() + b"\n"
        RuntimeTransaction(
            self._target_root,
            f"integration-verification-{kind}-{identity}",
            (TransactionParticipant(self._target_root, relative, content),),
        ).commit()

    def _path(self, kind: str, identity: str) -> Path:
        return self._target_root / "claims" / "integration-verification" / kind / f"{identity}.json"


class IntegrationVerifier:
    """Create, execute, and persist exact-candidate verification receipts."""

    def __init__(self, repository: Path, checkout_root: Path, store: IntegrationVerificationStore) -> None:
        self._repository = repository.resolve()
        self._checkout_root = checkout_root.resolve()
        self._store = store
        self._git_executable = resolve_git_executable()

    def verify(
        self,
        candidate: DeliveryIntegrationCandidate,
        preparation: AtomicIntegrationPreparation,
    ) -> IntegrationVerificationReceipt:
        """Verify one exact candidate or replay its durable receipt."""
        request = self._store.publish_request(self._request(candidate, preparation))
        with self._store.verification_lock(request.request_id):
            existing = self._store.read_receipt(request.request_id)
            if existing is not None:
                return existing
            if request.profile_state != IntegrationVerificationProfileState.CONFIGURED:
                return self._store.publish_receipt(self._profile_failure(request))
            if not self._candidate_ref_matches(request):
                return self._store.publish_receipt(
                    self._receipt(request, IntegrationVerificationStatus.CANDIDATE_MISSING, ("candidate ref moved",))
                )
            receipt = self._execute(request)
            return self._store.publish_receipt(receipt)

    def _request(
        self,
        candidate: DeliveryIntegrationCandidate,
        preparation: AtomicIntegrationPreparation,
    ) -> IntegrationVerificationRequest:
        if preparation.target_head is None or preparation.candidate_commit is None:
            message = "verification requires prepared target and candidate identities"
            raise ValueError(message)
        target_bytes = self._profile_bytes(preparation.target_head)
        candidate_bytes = self._profile_bytes(preparation.candidate_commit)
        profile_digest = hashlib.sha256(target_bytes or b"").hexdigest()
        candidate_digest = hashlib.sha256(candidate_bytes).hexdigest() if candidate_bytes is not None else None
        profile, state, diagnostic = self._parse_profile(target_bytes, candidate_bytes)
        binding = IntegrationVerificationProfileBinding(
            profile_digest=profile_digest,
            candidate_profile_digest=candidate_digest,
            profile_state=state,
            profile=profile,
            profile_diagnostic=diagnostic,
        )
        return IntegrationVerificationRequest.create(candidate, preparation, binding)

    def _parse_profile(
        self,
        target_bytes: bytes | None,
        candidate_bytes: bytes | None,
    ) -> tuple[IntegrationVerificationProfile | None, IntegrationVerificationProfileState, str | None]:
        if target_bytes is None:
            return None, IntegrationVerificationProfileState.UNCONFIGURED, "target has no Integration profile"
        if candidate_bytes != target_bytes:
            return None, IntegrationVerificationProfileState.CHANGED, "candidate changes its governing profile"
        try:
            profile = IntegrationVerificationProfile.model_validate_json(target_bytes)
        except ValidationError:
            return None, IntegrationVerificationProfileState.INVALID, "target Integration profile is invalid"
        return profile, IntegrationVerificationProfileState.CONFIGURED, None

    def _profile_bytes(self, commit: str) -> bytes | None:
        result = self._run_git("show", f"{commit}:{INTEGRATION_VERIFICATION_PROFILE_PATH}", check=False)
        return result.stdout if result.returncode == 0 else None

    def _profile_failure(self, request: IntegrationVerificationRequest) -> IntegrationVerificationReceipt:
        status = {
            IntegrationVerificationProfileState.UNCONFIGURED: IntegrationVerificationStatus.UNCONFIGURED,
            IntegrationVerificationProfileState.INVALID: IntegrationVerificationStatus.INVALID_PROFILE,
            IntegrationVerificationProfileState.CHANGED: IntegrationVerificationStatus.PROFILE_CHANGED,
        }[request.profile_state]
        return self._receipt(request, status, (request.profile_diagnostic or "verification profile rejected",))

    def _execute(self, request: IntegrationVerificationRequest) -> IntegrationVerificationReceipt:
        checkout = self._checkout_root / request.request_id
        step_receipts: list[IntegrationVerificationStepReceipt] = []
        status = IntegrationVerificationStatus.PASSED
        diagnostics: tuple[str, ...] = ()
        try:
            self._materialize(checkout, request.candidate_commit)
            for step in request.profile.steps if request.profile is not None else ():
                step_receipt = self._execute_step(request, checkout, step)
                step_receipts.append(step_receipt)
                if step_receipt.status != IntegrationVerificationStepStatus.PASSED:
                    status = IntegrationVerificationStatus(step_receipt.status.value)
                    diagnostics = (f"verification step {step.step_id} {step_receipt.status.value}",)
                    break
            if status == IntegrationVerificationStatus.PASSED and self._checkout_mutated(checkout):
                status = IntegrationVerificationStatus.CANDIDATE_MUTATED
                diagnostics = ("verification mutated tracked or untracked candidate files",)
        except (OSError, subprocess.CalledProcessError) as exc:
            status = IntegrationVerificationStatus.EXECUTION_ERROR
            diagnostics = (_bounded_diagnostic(str(exc)),)
        cleanup_diagnostic = self._cleanup(checkout)
        if cleanup_diagnostic is not None:
            diagnostics = (*diagnostics, cleanup_diagnostic)
            if status == IntegrationVerificationStatus.PASSED:
                status = IntegrationVerificationStatus.CLEANUP_FAILED
        return self._receipt(request, status, diagnostics, tuple(step_receipts))

    def _execute_step(
        self,
        request: IntegrationVerificationRequest,
        checkout: Path,
        step: IntegrationVerificationStep,
    ) -> IntegrationVerificationStepReceipt:
        cwd = (checkout / step.cwd).resolve()
        if cwd != checkout and checkout not in cwd.parents:
            message = "verification cwd escaped the candidate checkout"
            raise OSError(message)
        environment = {name: os.environ[name] for name in request.profile.pass_environment if name in os.environ}
        try:
            process = subprocess.Popen(  # noqa: S603 - reviewed profile provides argv without a shell.
                step.argv,
                cwd=cwd,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=step.timeout_seconds)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                return IntegrationVerificationStepReceipt(
                    step_id=step.step_id,
                    status=IntegrationVerificationStepStatus.TIMED_OUT,
                    stdout=_bounded_text(stdout),
                    stderr=_bounded_text(stderr),
                )
        except OSError as exc:
            return IntegrationVerificationStepReceipt(
                step_id=step.step_id,
                status=IntegrationVerificationStepStatus.EXECUTION_ERROR,
                stdout="",
                stderr=_bounded_text(str(exc).encode()),
            )
        return IntegrationVerificationStepReceipt(
            step_id=step.step_id,
            status=(
                IntegrationVerificationStepStatus.PASSED
                if process.returncode == 0
                else IntegrationVerificationStepStatus.FAILED
            ),
            exit_code=process.returncode,
            stdout=_bounded_text(stdout),
            stderr=_bounded_text(stderr),
        )

    def _materialize(self, checkout: Path, candidate_commit: str) -> None:
        checkout.parent.mkdir(parents=True, exist_ok=True)
        self._cleanup(checkout)
        self._run_git("worktree", "add", "--detach", str(checkout), candidate_commit)

    def _cleanup(self, checkout: Path) -> str | None:
        if not checkout.exists():
            return None
        result = self._run_git("worktree", "remove", "--force", str(checkout), check=False)
        if result.returncode == 0 and not checkout.exists():
            return None
        shutil.rmtree(checkout, ignore_errors=True)
        self._run_git("worktree", "prune", check=False)
        return None if not checkout.exists() else "candidate checkout cleanup failed"

    def _candidate_ref_matches(self, request: IntegrationVerificationRequest) -> bool:
        result = self._run_git("rev-parse", "--verify", f"{request.candidate_ref}^{{commit}}", check=False)
        return result.returncode == 0 and result.stdout.decode().strip() == request.candidate_commit

    def _checkout_mutated(self, checkout: Path) -> bool:
        result = self._run_git("-C", str(checkout), "status", "--porcelain", "--untracked-files=all")
        return bool(result.stdout.strip())

    def _run_git(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(  # noqa: S603 - fixed Git executable and argument vectors.
            (self._git_executable, "-C", str(self._repository), *arguments),
            check=check,
            capture_output=True,
        )

    @staticmethod
    def _receipt(
        request: IntegrationVerificationRequest,
        status: IntegrationVerificationStatus,
        diagnostics: tuple[str, ...],
        steps: tuple[IntegrationVerificationStepReceipt, ...] = (),
    ) -> IntegrationVerificationReceipt:
        return IntegrationVerificationReceipt(
            request_id=request.request_id,
            candidate_commit=request.candidate_commit,
            profile_digest=request.profile_digest,
            status=status,
            steps=steps,
            diagnostics=diagnostics,
        )


def _bounded_text(content: bytes) -> str:
    if len(content) <= _OUTPUT_LIMIT:
        return content.decode(errors="replace")
    half = _OUTPUT_LIMIT // 2
    return (content[:half] + b"\n... output truncated ...\n" + content[-half:]).decode(errors="replace")[:_OUTPUT_LIMIT]


def _bounded_diagnostic(content: str) -> str:
    return content[:_DIAGNOSTIC_LIMIT] or "verification execution failed"


def _canonical(payload: object) -> bytes:
    return f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n".encode()


__all__ = [
    "INTEGRATION_VERIFICATION_PROFILE_PATH",
    "IntegrationVerificationProfile",
    "IntegrationVerificationProfileBinding",
    "IntegrationVerificationReceipt",
    "IntegrationVerificationRequest",
    "IntegrationVerificationStatus",
    "IntegrationVerificationStep",
    "IntegrationVerificationStepReceipt",
    "IntegrationVerificationStepStatus",
    "IntegrationVerificationStore",
    "IntegrationVerifier",
]
