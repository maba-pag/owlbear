"""Contained disposable checkouts for acceptance and audit proof."""

from __future__ import annotations

import contextlib
import shutil
import stat
import subprocess
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from owlbear_kanban.yaml_rt import make_yaml

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from owlbear_kanban.jobs import JobRecord


class ProofCheckoutDiagnosticCode(StrEnum):
    """Stable failures for disposable proof checkout operations."""

    PATH_UNSAFE = "ERR_PROOF_PATH_UNSAFE"
    COMMIT_MISSING = "ERR_PROOF_COMMIT_MISSING"
    SETUP_FAILED = "ERR_PROOF_SETUP_FAILED"


class ProofCheckoutDiagnostic(BaseModel):
    """One materialization failure without a usable checkout."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: ProofCheckoutDiagnosticCode
    detail: str


class ProofCheckout(BaseModel):
    """A materialized exact-commit proof environment."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    target: str
    commit: str
    root: Path
    checkout: Path
    manifest: Path


class ProofCheckoutResult(BaseModel):
    """One successful checkout or one diagnostic."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    checkout: ProofCheckout | None = None
    diagnostic: ProofCheckoutDiagnostic | None = None


class ProofCheckoutManager:
    """Materialize and remove contained read-only Git worktrees."""

    def __init__(self, repository: Path, proof_root: Path) -> None:
        self._repository = repository
        self._proof_root = proof_root

    def materialize(
        self,
        job: JobRecord,
        commit: str,
        *,
        environment: Mapping[str, str] | None = None,
        replacements: Sequence[str] = (),
    ) -> ProofCheckoutResult:
        """Create one detached, read-only worktree for an accept or audit job."""
        if job.kind not in {"accept", "audit"}:
            return self._diagnostic(ProofCheckoutDiagnosticCode.PATH_UNSAFE, "job kind is not eligible for proof")
        paths = self._paths(job.job_id)
        if paths is None:
            return self._diagnostic(ProofCheckoutDiagnosticCode.PATH_UNSAFE, "proof path is not contained")
        root, checkout, manifest = paths
        resolved_commit = self._resolve_commit(commit)
        if resolved_commit is None:
            return self._diagnostic(ProofCheckoutDiagnosticCode.COMMIT_MISSING, "requested commit is not resolvable")
        try:
            self._proof_root.mkdir(mode=0o700, parents=True, exist_ok=True)
            paths = self._paths(job.job_id)
            if paths is None:
                return self._diagnostic(ProofCheckoutDiagnosticCode.PATH_UNSAFE, "proof path is not contained")
            root, checkout, manifest = paths
            root.mkdir(mode=0o700)
            self._git("worktree", "add", "--detach", str(checkout), resolved_commit)
            self._make_tracked_files_read_only(checkout)
            self._write_manifest(manifest, job, resolved_commit, environment or {}, replacements)
        except (OSError, subprocess.CalledProcessError, ValueError):
            self._remove(root, checkout)
            return self._diagnostic(ProofCheckoutDiagnosticCode.SETUP_FAILED, "proof checkout setup failed")
        return ProofCheckoutResult(
            checkout=ProofCheckout(
                job_id=job.job_id,
                target=job.target_node_id,
                commit=resolved_commit,
                root=root,
                checkout=checkout,
                manifest=manifest,
            )
        )

    def cleanup(self, job_id: int) -> None:
        """Remove a checkout when present, without affecting any sibling path."""
        paths = self._paths(job_id)
        if paths is None:
            return
        root, checkout, _manifest = paths
        self._remove(root, checkout)

    def health_paths(self) -> tuple[str, ...]:
        """Return contained job roots left by interrupted cleanup."""
        if self._proof_root.is_symlink() or not self._proof_root.is_dir():
            return ()
        paths = []
        for item in self._proof_root.iterdir():
            if item.is_symlink() or not item.is_dir() or not item.name.isdigit():
                paths.append(item.name)
                continue
            expected = self._paths(int(item.name))
            if expected is None or expected[0] != item:
                paths.append(item.name)
                continue
            paths.append(item.name)
        return tuple(sorted(paths))

    def is_orphan(self, path: str) -> bool:
        """Return whether a health path still identifies a contained checkout root."""
        return path in self.health_paths()

    def _paths(self, job_id: int) -> tuple[Path, Path, Path] | None:
        if job_id <= 0 or self._proof_root.is_symlink():
            return None
        try:
            proof_root = self._proof_root.resolve(strict=False)
            root = proof_root / str(job_id)
            checkout = root / "checkout"
            manifest = root / "manifest.yaml"
            root.relative_to(proof_root)
            checkout.relative_to(root)
            manifest.relative_to(root)
        except ValueError:
            return None
        if root.is_symlink() or checkout.is_symlink() or manifest.is_symlink():
            return None
        return root, checkout, manifest

    def _resolve_commit(self, commit: str) -> str | None:
        try:
            return self._git("rev-parse", "--verify", f"{commit}^{{commit}}")
        except subprocess.CalledProcessError:
            return None

    def _git(self, *arguments: str) -> str:
        return subprocess.run(  # noqa: S603 -- fixed Git executable with explicit arguments.
            ["git", "-C", str(self._repository), *arguments],  # noqa: S607 -- Git is a required platform tool.
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _make_tracked_files_read_only(self, checkout: Path) -> None:
        tracked = self._git("-C", str(checkout), "ls-files", "-z").split("\0")
        for relative_path in tracked:
            if not relative_path:
                continue
            path = checkout / relative_path
            if path.is_symlink() or not path.is_file():
                msg = "tracked path is not a regular file"
                raise ValueError(msg)
            path.chmod(stat.S_IMODE(path.stat().st_mode) & ~0o222)

    @staticmethod
    def _write_manifest(
        path: Path,
        job: JobRecord,
        commit: str,
        environment: Mapping[str, str],
        replacements: Sequence[str],
    ) -> None:
        stream = StringIO()
        make_yaml(explicit_start=True).dump(
            {
                "job_id": job.job_id,
                "target": job.target_node_id,
                "commit": commit,
                "environment": dict(sorted(environment.items())),
                "replacements": list(replacements),
            },
            stream,
        )
        path.write_text(stream.getvalue(), encoding="utf-8")

    def _remove(self, root: Path, checkout: Path) -> None:
        if root.is_symlink():
            return
        if checkout.exists() and not checkout.is_symlink():
            with contextlib.suppress(subprocess.CalledProcessError):
                self._git("worktree", "remove", "--force", str(checkout))
        if root.exists() and root.is_dir():
            shutil.rmtree(root)

    @staticmethod
    def _diagnostic(code: ProofCheckoutDiagnosticCode, detail: str) -> ProofCheckoutResult:
        return ProofCheckoutResult(diagnostic=ProofCheckoutDiagnostic(code=code, detail=detail))


__all__ = [
    "ProofCheckout",
    "ProofCheckoutDiagnostic",
    "ProofCheckoutDiagnosticCode",
    "ProofCheckoutManager",
    "ProofCheckoutResult",
]
