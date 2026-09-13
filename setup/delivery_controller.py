"""Inspect Delivery before a controller switch without importing its application."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

MAX_STATE_BYTES = 16 * 1024 * 1024
COMMIT_LENGTH = 40
CURRENT_RECORD_DEPTH = 3


def read_document(path: Path) -> dict[str, Any]:
    """Read one bounded regular JSON object without accepting symlinks."""
    return decode_document(read_content(path), path.name)


def read_content(path: Path) -> bytes:
    """Read one regular document once, for both parsing and compare-and-swap."""
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_STATE_BYTES:
        message = f"unsafe or oversized state document: {path.name}"
        raise ValueError(message)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            _refuse("state document changed type")
        content = stream.read(MAX_STATE_BYTES + 1)
    if len(content) > MAX_STATE_BYTES:
        _refuse("oversized state document")
    return content


def decode_document(content: bytes, name: str) -> dict[str, Any]:
    """Require an object while retaining the exact bytes used by the caller."""
    document = json.loads(content)
    if not isinstance(document, dict):
        message = f"state document must be an object: {name}"
        raise TypeError(message)
    return document


def _documents(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        message = f"unsafe state directory: {root.name}"
        raise ValueError(message)
    documents = []
    for child in sorted(root.iterdir()):
        if child.is_symlink():
            message = f"symlink in state directory: {child.name}"
            raise ValueError(message)
        if child.is_dir():
            documents.extend(_documents(child))
        elif child.suffix in {".json", ".yaml", ".yml"}:
            documents.append(child)
    return documents


def _frontier_blockers(document: dict[str, Any]) -> list[str]:
    bindings = document.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        return ["frontier bindings missing or invalid"]
    blockers = []
    for binding in bindings:
        if not isinstance(binding, dict):
            blockers.append("invalid outcome binding")
        elif binding.get("active_claim"):
            blockers.append("active outcome claim")
    blockers.extend(field for field in ("integration_repair_claim", "pending_checkpoint") if document.get(field))
    return blockers


def inspect_workspace(workspace: Path) -> dict[str, Any]:
    """Report switch blockers without recovery, imports, or filesystem mutation."""
    runtime = workspace / ".owlbear/delivery/runtime"
    blockers: list[dict[str, str]] = []
    versions: dict[str, Any] = {}
    if not runtime.is_dir():
        blockers.append({"path": ".owlbear/delivery/runtime", "reason": "runtime missing"})
    try:
        for path in _documents(runtime):
            relative = path.relative_to(runtime).as_posix()
            try:
                if path.suffix != ".json":
                    blockers.append({"path": relative, "reason": "transaction requires explicit recovery"})
                    continue
                document = read_document(path)
                reasons = _document_blockers(relative, document)
                if path.name == "frontier.json" and len(path.relative_to(runtime).parts) == CURRENT_RECORD_DEPTH:
                    versions[relative] = document.get("schema_version")
                blockers.extend({"path": relative, "reason": reason} for reason in reasons)
            except (OSError, TypeError, ValueError) as error:
                blockers.append({"path": relative, "reason": type(error).__name__})
    except (OSError, ValueError) as error:
        blockers.append({"path": ".owlbear/delivery/runtime", "reason": str(error)})
    return {"ready_for_switch": not blockers, "frontier_versions": versions, "blockers": blockers}


def _document_blockers(relative: str, document: dict[str, Any]) -> list[str]:
    path = Path(relative)
    if path.name == "frontier.json" and path.parts[0] == "changes" and len(path.parts) == CURRENT_RECORD_DEPTH:
        return _frontier_blockers(document)
    if path.parts[:2] == ("coordination", "changes"):
        return [
            field
            for field in (
                "writer",
                "publication_lease",
                "target_sync_conflict",
                "design_package_snapshot_intent",
                "external_head_adoption_intent",
                "worktree_cleanup_intent",
            )
            if document.get(field)
        ]
    if path.name == "state-publication.json":
        return [] if document.get("status") == "acknowledged" else ["pending state publication"]
    if "transactions" in path.parts:
        return ["transaction requires explicit recovery"]
    return []


def _git(release: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        _refuse("Git is unavailable")
    return subprocess.run(  # noqa: S603 - fixed read-only Git operations, no shell.
        [executable, "--no-optional-locks", "-C", str(release), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip()


def _refuse(detail: str) -> None:
    raise ValueError(detail)


@contextlib.contextmanager
def controller_lock(workspace: Path, *, shared: bool = False) -> Iterator[None]:
    """Exclude another pinned controller or a concurrent activation."""
    root = workspace / ".owlbear/controllers"
    if root.is_symlink():
        _refuse("unsafe controller directory")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(root / "active.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        fcntl.flock(descriptor, mode | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


@contextlib.contextmanager
def switch_locks(workspace: Path) -> Iterator[None]:
    """Use existing acquisition and checkpoint locks during a bounded switch."""
    runtime = workspace / ".owlbear/delivery/runtime"
    roots = [runtime / "claims/acquisition-lock"]
    roots.extend(runtime / "publications/checkpoints/locks" / path.name for path in (runtime / "changes").iterdir())
    with contextlib.ExitStack() as stack:
        for root in roots:
            if root.is_symlink():
                _refuse("unsafe Delivery lock root")
            root.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(root / ".storage.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            stack.callback(os.close, descriptor)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def verify_release(release: Path, revision: str, workspace: Path) -> None:
    """Refuse mutable, substituted, or primary-checkout controller source."""
    if len(revision) != COMMIT_LENGTH or any(character not in "0123456789abcdef" for character in revision):
        _refuse("controller revision must be a full commit ID")
    if release.resolve() == workspace.resolve():
        _refuse("controller release must be separate from the primary checkout")
    if _git(release, "rev-parse", "HEAD") != revision:
        _refuse("controller release revision differs from its pin")
    if _git(release, "status", "--porcelain", "--untracked-files=all"):
        _refuse("controller release contains uncommitted changes")
    if _git(release, "branch", "--show-current"):
        _refuse("controller release must have detached HEAD")


def validate_state(workspace: Path) -> list[dict[str, str]]:
    """Validate current records with this release's schemas, without constructing owners."""
    root = workspace / ".owlbear/delivery"
    loader = importlib.import_module("owlbear_delivery.delivery_application_loader")
    frontier = importlib.import_module("owlbear_delivery.delivery_runtime").DeliveryFrontier
    contract = importlib.import_module("owlbear_delivery.target_contract").DeliveryContract
    admission = importlib.import_module("owlbear_delivery.delivery_admission").DeliveryAdmissionReceipt
    coordination = importlib.import_module("owlbear_delivery.change_workspace").ChangeCoordination
    records: list[tuple[Path, Any]] = [(root / "config.json", loader.DeliveryStartupConfig)]
    records.append((root / "runtime/host.json", loader.DeliveryHostConfig))
    for change in sorted((root / "runtime/changes").iterdir()):
        if change.is_dir():
            records.extend(
                (change / name, model)
                for name, model in (
                    ("frontier.json", frontier),
                    ("contract.json", contract),
                    ("admission.json", admission),
                )
            )
    records.extend((path, coordination) for path in (root / "runtime/coordination/changes").glob("*.json"))
    errors = []
    for path, model in records:
        try:
            document = read_document(path)
            model.model_validate_json(json.dumps(document), strict=True)
        except (OSError, TypeError, ValueError):
            errors.append({"path": str(path.relative_to(workspace)), "reason": "incompatible controller schema"})
    return errors


def check_controller(workspace: Path, revision: str, *, quiescent: bool = True) -> dict[str, Any]:
    """Validate pinned source and schemas; require quiescence only for a switch."""
    release = Path(__file__).resolve().parents[1]
    verify_release(release, revision, workspace)
    result = inspect_workspace(workspace) if quiescent else {"ready_for_switch": False, "blockers": []}
    if result["blockers"]:
        return result
    delivery = importlib.import_module("owlbear_delivery")
    if not Path(delivery.__file__).resolve().is_relative_to(release):
        _refuse("Delivery imports resolve outside the pinned release")
    result["blockers"].extend(validate_state(workspace))
    result["ready_for_switch"] = quiescent and not result["blockers"]
    result["compatible"] = not result["blockers"]
    result["controller_revision"] = revision
    result["lock_sha256"] = hashlib.sha256((release / "uv.lock").read_bytes()).hexdigest()
    return result


def _atomic_config(path: Path, content: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".controller-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        Path(temporary).replace(path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def state_fingerprint(workspace: Path) -> str:
    """Fence live structured inputs across preservation and configuration publication."""
    root = workspace / ".owlbear/delivery"
    digest = hashlib.sha256()
    paths = [root / "config.json", *_documents(root / "runtime"), *_documents(root / "packages")]
    for path in sorted(paths):
        content = path.read_bytes()
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(len(content).to_bytes(8, "big") + content)
    return digest.hexdigest()


def _preserve_inputs(workspace: Path, previous: bytes) -> Path:
    backup = workspace / ".owlbear/controllers/backups" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup.mkdir(mode=0o700, parents=True)
    (backup / "mcp.json").write_bytes(previous)
    for directory in ("runtime", "packages"):
        shutil.copytree(workspace / ".owlbear/delivery" / directory, backup / directory)
    shutil.copyfile(workspace / ".owlbear/delivery/config.json", backup / "delivery-config.json")
    return backup


def legacy_consumers() -> list[str]:
    """Conservatively refuse activation while an unguarded local consumer is running."""
    executable = shutil.which("ps")
    if executable is None:
        _refuse("process inspection is unavailable")
    output = subprocess.run(  # noqa: S603 - fixed local process inspection, no shell.
        [executable, "-axo", "pid=,command="],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout
    return [
        line.strip().split(maxsplit=1)[0]
        for line in output.splitlines()
        if " -m owlbear_delivery_mcp" in line or "/bin/cockpit" in line or " -m owlbear_cockpit" in line
    ]


def activate_controller(workspace: Path, revision: str) -> dict[str, Any]:
    """Preserve rollback inputs and change only the configured Delivery launch."""
    with controller_lock(workspace), switch_locks(workspace):
        if legacy_consumers():
            _refuse("stop legacy Delivery and Cockpit consumers before activation")
        result = check_controller(workspace, revision)
        if not result["ready_for_switch"]:
            return result
        fingerprint = state_fingerprint(workspace)
        config_path = workspace / ".vscode/mcp.json"
        previous = read_content(config_path)
        config = decode_document(previous, config_path.name)
        if "owlbear-delivery" not in config.get("servers", {}):
            _refuse("existing Delivery MCP configuration is required")
        release = Path(__file__).resolve().parents[1]
        executable = release / ".venv/bin/python"
        if not executable.is_file():
            _refuse("pinned release interpreter is absent")
        server = dict(config["servers"]["owlbear-delivery"])
        server.update(
            command=str(executable),
            args=[
                "-I",
                "-B",
                str(release / "setup/delivery_controller.py"),
                "run",
                "--workspace",
                str(workspace),
                "--revision",
                revision,
            ],
            cwd=str(workspace),
        )
        backup = _preserve_inputs(workspace, previous)
        if config_path.read_bytes() != previous or state_fingerprint(workspace) != fingerprint:
            _refuse("configuration or Delivery state changed during activation")
        config["servers"]["owlbear-delivery"] = server
        _atomic_config(config_path, (json.dumps(config, indent=2) + "\n").encode())
        return {**result, "backup": str(backup), "activated_configuration": True}


def run_controller(workspace: Path, revision: str, *, cockpit: bool = False) -> int:
    """Keep the release locked for a complete MCP or Cockpit process lifetime."""
    with controller_lock(workspace, shared=True):
        result = check_controller(workspace, revision, quiescent=False)
        if not result["compatible"]:
            print(json.dumps(result), file=sys.stderr)
            return 1
        server = read_document(workspace / ".vscode/mcp.json")["servers"]["owlbear-delivery"]
        if revision not in server.get("args", []):
            _refuse("requested controller differs from the active configured pin")
        os.chdir(workspace)
        module = importlib.import_module("owlbear_cockpit.main" if cockpit else "owlbear_delivery_mcp.server")
        if cockpit:
            sys.argv = [sys.argv[0]]
            module.main()
        else:
            module.mcp.run()
    return 0


def main() -> int:
    """Inspect offline or launch a quiescent, schema-compatible pinned controller."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("inspect", "check", "activate", "run", "run-cockpit"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--revision")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    try:
        if args.operation != "inspect" and not sys.flags.isolated:
            _refuse("use the pinned interpreter with -I for controller operations")
        if args.operation == "inspect":
            result = inspect_workspace(workspace)
        elif args.operation in {"run", "run-cockpit"}:
            if args.revision is None:
                parser.error("--revision is required for run")
            return run_controller(workspace, args.revision, cockpit=args.operation == "run-cockpit")
        elif args.operation == "activate":
            if args.revision is None:
                parser.error("--revision is required for activate")
            result = activate_controller(workspace, args.revision)
        else:
            if args.revision is None:
                parser.error("--revision is required for check and run")
            result = check_controller(workspace, args.revision)
        print(json.dumps(result, indent=2), file=sys.stderr if args.operation == "run" else sys.stdout)
        if not result["ready_for_switch"]:
            return 1
    except (ImportError, OSError, TypeError, ValueError, subprocess.SubprocessError) as error:
        print(f"controller refused startup: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
