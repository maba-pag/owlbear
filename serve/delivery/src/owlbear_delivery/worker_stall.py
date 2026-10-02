"""Claim-issuer host liveness and worker-stall evidence; never a proof of worker death."""

from __future__ import annotations

import fcntl
import os
import re
import secrets
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

HOSTS_DIRECTORY = "hosts"
CLAIM_ISSUERS_DIRECTORY = "claim-issuers"
DEFAULT_WORKER_QUIET_PERIOD = timedelta(minutes=2)
_INSTANCE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_ATTEMPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CHANGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

type WorkerHostState = Literal["alive", "lost", "unknown"]


class WorkerHostInstance(Protocol):
    """Identity of the process that issues claims."""

    @property
    def instance_id(self) -> str:
        """Return the 32-hex issuer identity bound into claim-issuer records."""
        ...


class WorkerHostLivenessProbe(Protocol):
    """Engine dependency answering whether one claim issuer can still make progress."""

    def host_state(self, instance_id: str) -> WorkerHostState:
        """Return ``lost`` only when the issuer's process-lifetime lock is free."""
        ...


class DeliveryWorkerActiveError(RuntimeError):
    """A stuck-worker release found recent worktree activity and changed nothing."""

    code = "ERR_DELIVERY_WORKER_ACTIVE"

    def __init__(self, retry_after: datetime | None) -> None:
        self.retry_after = retry_after
        when = (
            f"at or after {retry_after.isoformat().replace('+00:00', 'Z')}"
            if retry_after is not None
            else "after the worktree can be observed safely and stays unchanged for the quiet period"
        )
        super().__init__(
            "Custody, files and retry accounting are unchanged. The worker's worktree changed recently or "
            f"could not be observed safely, so the worker may still be active. Retry {when}."
        )


class DeliveryClaimIssuer(BaseModel):
    """Immutable binding of one issued claim to the host instance that issued it."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1] = 1
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN.pattern)
    outcome_id: str | None = Field(default=None, pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(pattern=_ATTEMPT_ID_PATTERN.pattern)
    claim_id: str = Field(min_length=1, max_length=256)
    role: Literal["planner", "builder", "finalizer"]
    issuer_instance: str = Field(pattern=_INSTANCE_ID_PATTERN.pattern)
    issued_at: str = Field(min_length=1, max_length=64)


def is_issuable_attempt_id(attempt_id: str) -> bool:
    """Return whether an attempt identity can name a contained issuer record."""
    return _ATTEMPT_ID_PATTERN.fullmatch(attempt_id) is not None


def claim_issuer_path(change_id: str, attempt_id: str) -> Path:
    """Locate one issuer record relative to the runtime root."""
    if _CHANGE_ID_PATTERN.fullmatch(change_id) is None or not is_issuable_attempt_id(attempt_id):
        message = "claim issuer identity is not a contained record name"
        raise ValueError(message)
    return Path("changes") / change_id / CLAIM_ISSUERS_DIRECTORY / f"{attempt_id}.json"


def _hosts_directory(runtime_root: Path, *, create: bool) -> Path:
    root = runtime_root.resolve()
    directory = root / HOSTS_DIRECTORY
    if create:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = directory.lstat()
    if not stat.S_ISDIR(metadata.st_mode):
        message = "Delivery host lock directory is not a real directory"
        raise OSError(message)
    return directory


class DeliveryHostInstance:
    """One process-owned claim issuer; its exclusive lock lasts until close or process death."""

    def __init__(self, instance_id: str, descriptor: int) -> None:
        self._instance_id = instance_id
        self._descriptor: int | None = descriptor

    @classmethod
    def acquire(cls, runtime_root: Path) -> DeliveryHostInstance:
        """Create and exclusively lock a fresh host lock before publishing its name."""
        directory = _hosts_directory(runtime_root, create=True)
        instance_id = secrets.token_hex(16)
        staging = directory / f".staging-{instance_id}"
        descriptor = os.open(staging, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.link(staging, directory / f"{instance_id}.lock")
        except BaseException:
            os.close(descriptor)
            raise
        finally:
            staging.unlink(missing_ok=True)
        return cls(instance_id, descriptor)

    @property
    def instance_id(self) -> str:
        """Return this process's issuer identity."""
        return self._instance_id

    def close(self) -> None:
        """Release the host lock; the operating system also releases it when the process exits."""
        descriptor, self._descriptor = self._descriptor, None
        if descriptor is not None:
            os.close(descriptor)


class HostLockLivenessProbe:
    """Probe issuer host locks without waiting, holding, or deleting them."""

    def __init__(self, runtime_root: Path) -> None:
        self._runtime_root = runtime_root

    def host_state(self, instance_id: str) -> WorkerHostState:
        """A free lock is a lost host; missing, unsafe, or unreadable locks stay unknown."""
        if _INSTANCE_ID_PATTERN.fullmatch(instance_id) is None:
            return "unknown"
        try:
            directory = _hosts_directory(self._runtime_root, create=False)
            descriptor = os.open(
                directory / f"{instance_id}.lock", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            )
        except OSError:
            return "unknown"
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                return "unknown"
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return "alive"
            except OSError:
                return "unknown"
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            return "lost"
        finally:
            os.close(descriptor)


__all__ = [
    "CLAIM_ISSUERS_DIRECTORY",
    "DEFAULT_WORKER_QUIET_PERIOD",
    "HOSTS_DIRECTORY",
    "DeliveryClaimIssuer",
    "DeliveryHostInstance",
    "DeliveryWorkerActiveError",
    "HostLockLivenessProbe",
    "WorkerHostInstance",
    "WorkerHostLivenessProbe",
    "WorkerHostState",
    "claim_issuer_path",
    "is_issuable_attempt_id",
]
