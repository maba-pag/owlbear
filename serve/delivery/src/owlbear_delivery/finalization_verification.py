"""Engine-owned finalization profile execution in the managed Change worktree."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import signal
import subprocess
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.change_workspace import FinalizationTargetProvenance
from owlbear_delivery.delivery_runtime import FinalizationVerificationScope
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionParticipant

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery.integration_verification import (
        IntegrationVerificationProfile,
        IntegrationVerificationStep,
    )

_OUTPUT_LIMIT = 8_192
_DIAGNOSTIC_LIMIT = 1_024


class _FinalizationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FinalizationVerificationStepStatus(StrEnum):
    """Bounded result for one target-governed finalization step."""

    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed-out"
    EXECUTION_ERROR = "execution-error"


class FinalizationVerificationStatus(StrEnum):
    """Terminal result for one exact finalization proof run."""

    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed-out"
    EXECUTION_ERROR = "execution-error"
    HEAD_CHANGED = "head-changed"
    TARGET_CHANGED = "target-changed"
    WORKTREE_CHANGED = "worktree-changed"


class FinalizationVerificationStepReceipt(_FinalizationModel):
    """Bounded engine-produced observation for one declared profile step."""

    step_id: str = Field(min_length=1)
    argv: tuple[str, ...] = Field(min_length=1)
    cwd: str = Field(min_length=1)
    timeout_seconds: int = Field(gt=0)
    status: FinalizationVerificationStepStatus
    exit_code: int | None = None
    stdout: str = Field(max_length=_OUTPUT_LIMIT)
    stderr: str = Field(max_length=_OUTPUT_LIMIT)


class FinalizationVerificationReceipt(_FinalizationModel):
    """Persisted proof bound to one Change head and target verification authority."""

    schema_version: Literal[1] = 1
    run_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_ref: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_provenance: FinalizationTargetProvenance
    target_observed_at: datetime
    proof_scope: FinalizationVerificationScope
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    declared_step_ids: tuple[str, ...] = Field(min_length=1)
    steps: tuple[FinalizationVerificationStepReceipt, ...] = Field(min_length=1)
    status: FinalizationVerificationStatus
    observed_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    clean: bool
    diagnostics: tuple[str, ...] = Field(max_length=16)

    @model_validator(mode="after")
    def _validate_identity(self) -> FinalizationVerificationReceipt:
        if self.target_observed_at.tzinfo is None:
            message = "finalization target observation time must include a timezone"
            raise ValueError(message)
        step_ids = tuple(step.step_id for step in self.steps)
        if len(self.declared_step_ids) != len(set(self.declared_step_ids)):
            message = "finalization verification declared step identities must be unique"
            raise ValueError(message)
        if len(step_ids) != len(set(step_ids)):
            message = "finalization verification step identities must be unique"
            raise ValueError(message)
        if self.run_id != _run_id(
            self.change_id,
            self.exact_head,
            self.target_ref,
            self.target_head,
            self.target_provenance,
            self.proof_scope,
            self.profile_digest,
            self.declared_step_ids,
        ):
            message = "finalization verification run identity is invalid"
            raise ValueError(message)
        return self


class FinalizationVerificationStore:
    """Persist engine-produced finalization proof through runtime transactions."""

    def __init__(self, target_root: Path) -> None:
        self._target_root = target_root.resolve()
        RuntimeTransaction.recover_all(self._target_root)

    def publish(self, receipt: FinalizationVerificationReceipt) -> FinalizationVerificationReceipt:
        """Publish or replay one immutable finalization proof receipt."""
        relative = Path("claims/finalization-verification/runs") / f"{receipt.run_id}.json"
        content = receipt.model_dump_json(indent=2).encode() + b"\n"
        RuntimeTransaction(
            self._target_root,
            f"finalization-verification-{receipt.run_id}",
            (TransactionParticipant(self._target_root, relative, content),),
        ).commit()
        return receipt

    def read(self, run_id: str) -> FinalizationVerificationReceipt | None:
        """Read one exact proof receipt when it has already been persisted."""
        path = self._target_root / "claims/finalization-verification/runs" / f"{run_id}.json"
        if not path.exists():
            return None
        return FinalizationVerificationReceipt.model_validate_json(path.read_bytes())


class FinalizationVerifier:
    """Execute target-governed steps without creating another checkout."""

    def __init__(self, repository: Path, store: FinalizationVerificationStore) -> None:
        self._repository = repository.resolve()
        self._store = store
        self._git_executable = resolve_git_executable()

    def run(  # noqa: PLR0913
        self,
        *,
        change_id: str,
        worktree: Path,
        branch: str,
        exact_head: str,
        target_ref: str,
        target_head: str,
        profile_digest: str,
        profile: IntegrationVerificationProfile,
        target_provenance: FinalizationTargetProvenance = FinalizationTargetProvenance.CACHED_REMOTE_TRACKING,
        target_observed_at: datetime | None = None,
        proof_scope: FinalizationVerificationScope = FinalizationVerificationScope.CHANGE_HEAD_PROFILE,
    ) -> FinalizationVerificationReceipt:
        """Run or replay one exact target-profile proof in the supplied worktree."""
        step_ids = tuple(step.step_id for step in profile.steps)
        run_id = _run_id(
            change_id,
            exact_head,
            target_ref,
            target_head,
            target_provenance,
            proof_scope,
            profile_digest,
            step_ids,
        )
        existing = self._store.read(run_id)
        if existing is not None:
            return existing
        observed_at = target_observed_at or datetime.now(UTC)

        if self._resolve_target_head(target_ref) != target_head:
            receipt = self._failure_receipt(
                run_id=run_id,
                change_id=change_id,
                exact_head=exact_head,
                target_ref=target_ref,
                target_head=target_head,
                target_provenance=target_provenance,
                target_observed_at=observed_at,
                proof_scope=proof_scope,
                profile_digest=profile_digest,
                declared_step_ids=step_ids,
                steps=(),
                status=FinalizationVerificationStatus.TARGET_CHANGED,
                observed_head=None,
                clean=False,
                diagnostics=("cached remote-tracking target changed before finalization proof",),
            )
            return self._store.publish(receipt)

        initial_head, initial_branch, initial_clean = self._workspace_state(worktree)
        if initial_head != exact_head or initial_branch != branch or not initial_clean:
            receipt = self._failure_receipt(
                run_id=run_id,
                change_id=change_id,
                exact_head=exact_head,
                target_ref=target_ref,
                target_head=target_head,
                target_provenance=target_provenance,
                target_observed_at=observed_at,
                proof_scope=proof_scope,
                profile_digest=profile_digest,
                declared_step_ids=step_ids,
                steps=(),
                status=FinalizationVerificationStatus.WORKTREE_CHANGED,
                observed_head=initial_head,
                clean=initial_clean,
                diagnostics=("managed Change worktree is not at the exact clean reviewed head",),
            )
            return self._store.publish(receipt)

        step_receipts: list[FinalizationVerificationStepReceipt] = []
        status = FinalizationVerificationStatus.PASSED
        diagnostics: tuple[str, ...] = ()
        for step in profile.steps:
            step_receipt = self._execute_step(worktree, step, profile.pass_environment)
            step_receipts.append(step_receipt)
            if self._resolve_target_head(target_ref) != target_head:
                status = FinalizationVerificationStatus.TARGET_CHANGED
                diagnostics = ("cached remote-tracking target changed during finalization proof",)
                break
            if step_receipt.status != FinalizationVerificationStepStatus.PASSED:
                status = FinalizationVerificationStatus(step_receipt.status.value)
                diagnostics = (f"finalization step {step.step_id} {step_receipt.status.value}",)
                break

        observed_head, observed_branch, clean = self._workspace_state(worktree)
        if self._resolve_target_head(target_ref) != target_head:
            status = FinalizationVerificationStatus.TARGET_CHANGED
            diagnostics = (*diagnostics, "cached remote-tracking target changed during finalization proof")
        elif observed_head != exact_head or observed_branch != branch:
            status = FinalizationVerificationStatus.HEAD_CHANGED
            diagnostics = (*diagnostics, "managed Change branch or HEAD changed during finalization proof")
        elif not clean:
            status = FinalizationVerificationStatus.WORKTREE_CHANGED
            diagnostics = (*diagnostics, "finalization proof changed tracked or untracked worktree files")

        receipt = FinalizationVerificationReceipt(
            run_id=run_id,
            change_id=change_id,
            exact_head=exact_head,
            target_ref=target_ref,
            target_head=target_head,
            target_provenance=target_provenance,
            target_observed_at=observed_at,
            proof_scope=proof_scope,
            profile_digest=profile_digest,
            declared_step_ids=step_ids,
            steps=tuple(step_receipts),
            status=status,
            observed_head=observed_head,
            clean=clean,
            diagnostics=tuple(_bounded_diagnostic(item) for item in diagnostics),
        )
        return self._store.publish(receipt)

    def _execute_step(
        self,
        worktree: Path,
        step: IntegrationVerificationStep,
        environment_names: tuple[str, ...],
    ) -> FinalizationVerificationStepReceipt:
        cwd = (worktree / step.cwd).resolve()
        if cwd != worktree and worktree not in cwd.parents:
            return FinalizationVerificationStepReceipt(
                step_id=step.step_id,
                argv=step.argv,
                cwd=step.cwd,
                timeout_seconds=step.timeout_seconds,
                status=FinalizationVerificationStepStatus.EXECUTION_ERROR,
                stdout="",
                stderr="verification cwd escaped the managed Change worktree",
            )
        environment = {name: os.environ[name] for name in environment_names if name in os.environ}
        try:
            process = subprocess.Popen(  # noqa: S603 - profile supplies reviewed argv without a shell.
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
                return FinalizationVerificationStepReceipt(
                    step_id=step.step_id,
                    argv=step.argv,
                    cwd=step.cwd,
                    timeout_seconds=step.timeout_seconds,
                    status=FinalizationVerificationStepStatus.TIMED_OUT,
                    stdout=_bounded_text(stdout),
                    stderr=_bounded_text(stderr),
                )
        except OSError as exc:
            return FinalizationVerificationStepReceipt(
                step_id=step.step_id,
                argv=step.argv,
                cwd=step.cwd,
                timeout_seconds=step.timeout_seconds,
                status=FinalizationVerificationStepStatus.EXECUTION_ERROR,
                stdout="",
                stderr=_bounded_diagnostic(str(exc)),
            )
        return FinalizationVerificationStepReceipt(
            step_id=step.step_id,
            argv=step.argv,
            cwd=step.cwd,
            timeout_seconds=step.timeout_seconds,
            status=(
                FinalizationVerificationStepStatus.PASSED
                if process.returncode == 0
                else FinalizationVerificationStepStatus.FAILED
            ),
            exit_code=process.returncode,
            stdout=_bounded_text(stdout),
            stderr=_bounded_text(stderr),
        )

    def _workspace_state(self, worktree: Path) -> tuple[str | None, str, bool]:
        head_result = self._run_git("-C", str(worktree), "rev-parse", "--verify", "HEAD", check=False)
        branch_result = self._run_git("-C", str(worktree), "branch", "--show-current", check=False)
        status_result = self._run_git(
            "-C",
            str(worktree),
            "status",
            "--porcelain",
            "--untracked-files=all",
            check=False,
        )
        head = head_result.stdout.decode().strip() if head_result.returncode == 0 else None
        branch = branch_result.stdout.decode().strip() if branch_result.returncode == 0 else ""
        clean = status_result.returncode == 0 and not status_result.stdout.strip()
        return head, branch, clean

    def _resolve_target_head(self, target_ref: str) -> str | None:
        result = self._run_git(
            "-C",
            str(self._repository),
            "rev-parse",
            "--verify",
            f"{target_ref}^{{commit}}",
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.decode().strip()

    def _run_git(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(  # noqa: S603 - executable and arguments are fixed by the engine.
            (self._git_executable, *arguments),
            cwd=self._repository,
            check=check,
            capture_output=True,
        )

    @staticmethod
    def _failure_receipt(  # noqa: PLR0913
        *,
        run_id: str,
        change_id: str,
        exact_head: str,
        target_ref: str,
        target_head: str,
        target_provenance: FinalizationTargetProvenance,
        target_observed_at: datetime,
        proof_scope: FinalizationVerificationScope,
        profile_digest: str,
        declared_step_ids: tuple[str, ...],
        steps: Sequence[FinalizationVerificationStepReceipt],
        status: FinalizationVerificationStatus,
        observed_head: str | None,
        clean: bool,
        diagnostics: tuple[str, ...],
    ) -> FinalizationVerificationReceipt:
        return FinalizationVerificationReceipt(
            run_id=run_id,
            change_id=change_id,
            exact_head=exact_head,
            target_ref=target_ref,
            target_head=target_head,
            target_provenance=target_provenance,
            target_observed_at=target_observed_at,
            proof_scope=proof_scope,
            profile_digest=profile_digest,
            declared_step_ids=declared_step_ids,
            steps=tuple(steps)
            or (
                FinalizationVerificationStepReceipt(
                    step_id="preflight",
                    argv=("git", "status", "--porcelain", "--untracked-files=all"),
                    cwd=".",
                    timeout_seconds=1,
                    status=FinalizationVerificationStepStatus.EXECUTION_ERROR,
                    stdout="",
                    stderr=diagnostics[0] if diagnostics else "finalization preflight failed",
                ),
            ),
            status=status,
            observed_head=observed_head,
            clean=clean,
            diagnostics=tuple(_bounded_diagnostic(item) for item in diagnostics),
        )


def _run_id(  # noqa: PLR0913, PLR0917
    change_id: str,
    exact_head: str,
    target_ref: str,
    target_head: str,
    target_provenance: FinalizationTargetProvenance,
    proof_scope: FinalizationVerificationScope,
    profile_digest: str,
    step_ids: tuple[str, ...],
) -> str:
    payload = {
        "change_id": change_id,
        "exact_head": exact_head,
        "target_ref": target_ref,
        "target_head": target_head,
        "target_provenance": target_provenance.value,
        "proof_scope": proof_scope.value,
        "profile_digest": profile_digest,
        "step_ids": step_ids,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _bounded_text(value: bytes) -> str:
    return value.decode(errors="replace")[:_OUTPUT_LIMIT]


def _bounded_diagnostic(value: str) -> str:
    return value[:_DIAGNOSTIC_LIMIT]


__all__ = [
    "FinalizationVerificationReceipt",
    "FinalizationVerificationScope",
    "FinalizationVerificationStatus",
    "FinalizationVerificationStepReceipt",
    "FinalizationVerificationStepStatus",
    "FinalizationVerificationStore",
    "FinalizationVerifier",
]
