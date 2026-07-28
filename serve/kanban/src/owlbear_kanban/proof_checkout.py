"""Contained disposable checkouts for acceptance and audit proof."""

from __future__ import annotations

import contextlib
import hashlib
import shutil
import stat
import subprocess
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from owlbear_kanban.yaml_rt import make_yaml

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from owlbear_kanban.jobs import JobRecord


class ProofCheckoutDiagnosticCode(StrEnum):
    """Stable failures for disposable proof checkout operations."""

    PATH_UNSAFE = "ERR_PROOF_PATH_UNSAFE"
    COMMIT_MISSING = "ERR_PROOF_COMMIT_MISSING"
    COMMIT_MISMATCH = "ERR_PROOF_COMMIT_MISMATCH"
    TRACKED_MUTATION = "ERR_PROOF_TRACKED_MUTATION"
    AUTHORITY_MUTATION = "ERR_PROOF_AUTHORITY_MUTATION"
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
    authority: Path
    authority_digest: str
    manifest: Path


class ProofCheckoutSnapshot(BaseModel):
    """Immutable authority needed to restore one cleaned proof checkout."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    target: str
    commit: str
    authority_digest: str
    environment: dict[str, str] = Field(default_factory=dict)
    replacements: tuple[str, ...] = ()


class ProofCheckoutResult(BaseModel):
    """One successful checkout or one diagnostic."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    checkout: ProofCheckout | None = None
    diagnostic: ProofCheckoutDiagnostic | None = None


class ProofCheckoutManager:
    """Materialize and remove contained read-only Git worktrees."""

    def __init__(self, repository: Path, proof_root: Path, authority_root: Path | None = None) -> None:
        self._repository = repository
        self._proof_root = proof_root
        self._authority_root = authority_root or repository / ".owlbear/changes"

    def materialize(  # noqa: PLR0911
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
        root, checkout, authority, manifest = paths
        resolved_commit = self._resolve_commit(commit)
        if resolved_commit is None:
            return self._diagnostic(ProofCheckoutDiagnosticCode.COMMIT_MISSING, "requested commit is not resolvable")
        authority_source = self._authority_source(job.change_id)
        if authority_source is None:
            return self._diagnostic(ProofCheckoutDiagnosticCode.SETUP_FAILED, "proof authority is unavailable")
        root_created = False
        try:
            self._proof_root.mkdir(mode=0o700, parents=True, exist_ok=True)
            paths = self._paths(job.job_id)
            if paths is None:
                return self._diagnostic(ProofCheckoutDiagnosticCode.PATH_UNSAFE, "proof path is not contained")
            root, checkout, authority, manifest = paths
            root.mkdir(mode=0o700)
            root_created = True
            self._git("worktree", "add", "--detach", str(checkout), resolved_commit)
            shutil.copytree(authority_source, authority, symlinks=True)
            authority_digest = self._tree_digest(authority)
            self._make_tree_read_only(authority)
            self._make_tracked_files_read_only(checkout)
            self._write_manifest(
                manifest,
                job,
                resolved_commit,
                authority_digest,
                environment or {},
                replacements,
            )
        except OSError, subprocess.CalledProcessError, ValueError:
            if root_created:
                self._remove(root, checkout)
            return self._diagnostic(ProofCheckoutDiagnosticCode.SETUP_FAILED, "proof checkout setup failed")
        return ProofCheckoutResult(
            checkout=ProofCheckout(
                job_id=job.job_id,
                target=job.target_node_id,
                commit=resolved_commit,
                root=root,
                checkout=checkout,
                authority=authority,
                authority_digest=authority_digest,
                manifest=manifest,
            )
        )

    def cleanup(self, job_id: int) -> None:
        """Remove a checkout when present, without affecting any sibling path."""
        paths = self._paths(job_id)
        if paths is None:
            return
        root, checkout, _authority, _manifest = paths
        self._remove(root, checkout)

    def snapshot(self, job_id: int) -> ProofCheckoutSnapshot | None:
        """Capture the exact manifest authority needed to restore a checkout."""
        existing = self.existing(job_id)
        if existing is None:
            return None
        try:
            payload = make_yaml().load(existing.manifest.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("replacements"), list):
                payload = dict(payload) | {"replacements": tuple(payload["replacements"])}
            return ProofCheckoutSnapshot.model_validate(payload)
        except OSError, TypeError, ValueError:
            return None

    def restore(self, job: JobRecord, snapshot: ProofCheckoutSnapshot) -> bool:
        """Restore one previously cleaned checkout from its exact manifest authority."""
        if (
            job.job_id != snapshot.job_id
            or job.target_node_id != snapshot.target
            or self.existing(job.job_id) is not None
        ):
            return False
        result = self.materialize(
            job,
            snapshot.commit,
            environment=snapshot.environment,
            replacements=snapshot.replacements,
        )
        if result.checkout is None or result.checkout.authority_digest != snapshot.authority_digest:
            self.cleanup(job.job_id)
            return False
        return True

    def existing(self, job_id: int) -> ProofCheckout | None:
        """Return a valid existing checkout context without materializing another worktree."""
        paths = self._paths(job_id)
        if paths is None:
            return None
        root, checkout, authority, manifest = paths
        if not checkout.is_dir() or not authority.is_dir() or not manifest.is_file():
            return None
        try:
            payload = make_yaml().load(manifest.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None
            target = payload["target"]
            commit = payload["commit"]
            authority_digest = payload["authority_digest"]
            if not all(isinstance(item, str) for item in (target, commit, authority_digest)):
                return None
        except OSError, TypeError, ValueError, KeyError:
            return None
        return ProofCheckout(
            job_id=job_id,
            target=target,
            commit=commit,
            root=root,
            checkout=checkout,
            authority=authority,
            authority_digest=authority_digest,
            manifest=manifest,
        )

    def resolve_commit(self, commit: str) -> str | None:
        """Resolve caller revision syntax to the canonical commit identity."""
        return self._resolve_commit(commit)

    def validate(  # noqa: PLR0911
        self, job_id: int, expected_commit: str
    ) -> ProofCheckoutDiagnostic | None:
        """Require the existing checkout to remain at the expected clean revision."""
        checkout = self.existing(job_id)
        if checkout is None:
            return ProofCheckoutDiagnostic(
                code=ProofCheckoutDiagnosticCode.SETUP_FAILED,
                detail="proof checkout is unavailable",
            )
        if expected_commit != checkout.commit:
            return ProofCheckoutDiagnostic(
                code=ProofCheckoutDiagnosticCode.COMMIT_MISMATCH,
                detail="proof checkout revision differs from acceptance evidence",
            )
        try:
            head = self._git("-C", str(checkout.checkout), "rev-parse", "HEAD")
            status = self._git("-C", str(checkout.checkout), "status", "--porcelain=v1", "--untracked-files=no")
        except subprocess.CalledProcessError:
            return ProofCheckoutDiagnostic(
                code=ProofCheckoutDiagnosticCode.SETUP_FAILED,
                detail="proof checkout state is unavailable",
            )
        if head != checkout.commit:
            return ProofCheckoutDiagnostic(
                code=ProofCheckoutDiagnosticCode.COMMIT_MISMATCH,
                detail="proof checkout HEAD differs from acceptance evidence",
            )
        if status:
            return ProofCheckoutDiagnostic(
                code=ProofCheckoutDiagnosticCode.TRACKED_MUTATION,
                detail="proof checkout contains tracked mutations",
            )
        try:
            authority_digest = self._tree_digest(checkout.authority)
        except OSError, ValueError:
            authority_digest = ""
        if authority_digest != checkout.authority_digest:
            return ProofCheckoutDiagnostic(
                code=ProofCheckoutDiagnosticCode.AUTHORITY_MUTATION,
                detail="proof authority differs from its materialized snapshot",
            )
        return None

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

    def _paths(self, job_id: int) -> tuple[Path, Path, Path, Path] | None:
        if job_id <= 0 or self._proof_root.is_symlink():
            return None
        try:
            proof_root = self._proof_root.resolve(strict=False)
            root = proof_root / str(job_id)
            checkout = root / "checkout"
            authority = root / "authority"
            manifest = root / "manifest.yaml"
            root.relative_to(proof_root)
            checkout.relative_to(root)
            authority.relative_to(root)
            manifest.relative_to(root)
        except ValueError:
            return None
        if root.is_symlink() or checkout.is_symlink() or authority.is_symlink() or manifest.is_symlink():
            return None
        return root, checkout, authority, manifest

    def _authority_source(self, change_id: str) -> Path | None:
        if self._authority_root.is_symlink():
            return None
        source = self._authority_root / change_id
        try:
            root = self._authority_root.resolve(strict=True)
            resolved = source.resolve(strict=True)
            resolved.relative_to(root)
        except OSError, ValueError:
            return None
        if source.is_symlink() or not resolved.is_dir() or any(path.is_symlink() for path in resolved.rglob("*")):
            return None
        return resolved

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
    def _make_tree_read_only(root: Path) -> None:
        directories = [root]
        for path in root.rglob("*"):
            if path.is_symlink():
                msg = "authority path is not a regular tree"
                raise ValueError(msg)
            if path.is_dir():
                directories.append(path)
            elif path.is_file():
                path.chmod(stat.S_IMODE(path.stat().st_mode) & ~0o222)
            else:
                msg = "authority path is not a regular tree"
                raise ValueError(msg)
        for directory in reversed(directories):
            directory.chmod(stat.S_IMODE(directory.stat().st_mode) & ~0o222)

    @staticmethod
    def _tree_digest(root: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
            if path.is_symlink():
                msg = "authority path is not a regular tree"
                raise ValueError(msg)
            relative = path.relative_to(root).as_posix().encode()
            digest.update(relative)
            if path.is_dir():
                digest.update(b"\0directory\0")
            elif path.is_file():
                digest.update(b"\0file\0")
                digest.update(path.read_bytes())
            else:
                msg = "authority path is not a regular tree"
                raise ValueError(msg)
        return digest.hexdigest()

    @staticmethod
    def _write_manifest(  # noqa: PLR0913, PLR0917
        path: Path,
        job: JobRecord,
        commit: str,
        authority_digest: str,
        environment: Mapping[str, str],
        replacements: Sequence[str],
    ) -> None:
        stream = StringIO()
        make_yaml(explicit_start=True).dump(
            {
                "job_id": job.job_id,
                "target": job.target_node_id,
                "commit": commit,
                "authority_digest": authority_digest,
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
        authority = root / "authority"
        if authority.exists() and not authority.is_symlink():
            for path in (authority, *authority.rglob("*")):
                if not path.is_symlink():
                    path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR)
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
    "ProofCheckoutSnapshot",
]
