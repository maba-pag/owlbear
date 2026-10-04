"""``delivery-controller``: install, pin and switch immutable Delivery controller releases (N02 D1).

A release is ``.owlbear/controller/releases/<commit>/``: ``git archive <commit>``, a locked
``uv sync --compile-bytecode`` environment, the Cockpit bundle and ``RELEASE.json`` (commit, supported
format, interpreter identity, tree digest), then made read-only. ``pin`` and ``switch`` write the generated
launchers ``bin/delivery-mcp`` and ``bin/cockpit`` and commit ``pin.json`` (with the digest of
``RELEASE.json``) last. Every pinned start verifies the release against that digest before any release code
runs, and refuses a controller whose code is not its pinned release (I6). ``preflight``, ``backup``, ``pin``,
``switch`` and ``prune`` hold the workspace controller lock exclusively and refuse while any controller runs.
"""

from __future__ import annotations

import argparse
import contextlib
import errno
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from owlbear_delivery import release_integrity
from owlbear_delivery.release_integrity import RELEASE_FILE, ReleaseIntegrityError, file_sha256, tree_digest
from owlbear_delivery.state_formats import (
    CONTROLLER_PIN,
    CONTROLLER_RELEASES,
    CONTROLLER_ROOT,
    DELIVERY_STATE_ROOT,
    PIN_SCHEMA_VERSION,
    ControllerPin,
    ControllerPinError,
    read_controller_pin,
    scan_capability,
)
from owlbear_delivery.storage_io import ControllerFencedError, acquire_controller_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from types import ModuleType

RELEASE_SCHEMA_VERSION = 1
LAUNCHERS = ("delivery-mcp", "cockpit")
_MAINTENANCE_LOCK = ".maintenance.lock"
_COMMIT = re.compile(r"[0-9a-f]{40}")
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_RECORD_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_MAX_RECORD_BYTES = 64 << 20
_WRITE_BITS = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
_CLEAN_ENVIRONMENT = ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT", "CONDA_PREFIX")
_PROBE = """
import json, os, sys
import owlbear_delivery, owlbear_delivery_mcp, owlbear_cockpit, owlbear_tools
try:
    from owlbear_delivery import state_formats
    supported = state_formats.SUPPORTED_FORMAT
except ImportError:
    supported = None
print(json.dumps({"modules": [m.__file__ for m in (owlbear_delivery, owlbear_delivery_mcp, owlbear_cockpit,
    owlbear_tools)], "supported_format": supported, "python": sys.version.split()[0],
    "interpreter": os.path.realpath(sys.executable)}))
"""
_GATE_PROBE = """
import json, sys
from pathlib import Path
try:
    from owlbear_delivery.state_formats import scan_capability
except ImportError:
    print(json.dumps({"gated": False, "refusals": []}))
    raise SystemExit(0)
report = scan_capability(Path(sys.argv[1]))
print(json.dumps({"gated": True, "refusals": [[item.code, item.locator] for item in report.refusals]}))
"""
# Command-line forms of a Delivery controller: MCP, Cockpit (module or console script) and the launchers.
_CONTROLLER_MARKERS = ("owlbear_delivery_mcp", "owlbear_cockpit")
_CONTROLLER_PROGRAMS = frozenset({"cockpit", "delivery-mcp"})
_INTERPRETER_NAMES = re.compile(r"^(python[0-9.]*|uv|uvx|cockpit|delivery-mcp)$")


class ControllerError(RuntimeError):
    """A typed refusal; nothing was changed unless ``detail`` says otherwise."""

    def __init__(self, *, code: str, detail: str, **evidence: object) -> None:
        self.code = code
        self.detail = detail
        self.evidence = evidence
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class Layout:
    """Controller paths of one workspace (the primary Git worktree that Delivery manages)."""

    workspace: Path

    @property
    def root(self) -> Path:
        """``.owlbear/controller``."""
        return self.workspace / CONTROLLER_ROOT

    @property
    def releases(self) -> Path:
        """Installed release trees."""
        return self.workspace / CONTROLLER_RELEASES

    @property
    def bin(self) -> Path:
        """Generated launchers."""
        return self.root / "bin"

    @property
    def pin(self) -> Path:
        """``pin.json``."""
        return self.workspace / CONTROLLER_PIN

    @property
    def runtime(self) -> Path:
        """Delivery runtime root holding ``controller.lock``."""
        return self.workspace / DELIVERY_STATE_ROOT / "runtime"

    def release(self, commit: str) -> Path:
        """Return one release tree, refusing anything but a full commit name."""
        if _COMMIT.fullmatch(commit) is None:
            raise ControllerError(code="commit-invalid", detail=f"not a full commit: {commit!r}")
        return self.releases / commit


class Toolchain(Protocol):
    """Environment and bundle builders; replaced only below the release owner in tests."""

    def sync(self, tree: Path) -> None:
        """Create ``tree/.venv`` from the release's lock file."""
        ...

    def build_bundle(self, tree: Path) -> None:
        """Build ``tree/serve/cockpit/dist`` from the release's frontend sources."""
        ...


def _clean_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key not in _CLEAN_ENVIRONMENT}


def _run(arguments: list[str], *, cwd: Path | None = None, failure: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(  # noqa: S603 - fixed tool argument vectors built by this module.
        arguments, cwd=cwd, env=_clean_environment(), check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        detail = f"{' '.join(arguments[:3])} failed: {completed.stderr.strip()[-1500:]}"
        raise ControllerError(code=failure, detail=detail)
    return completed


class UvNodeToolchain:
    """``uv sync --locked --compile-bytecode`` and the pinned-Node Cockpit build."""

    def sync(self, tree: Path) -> None:
        """Create the release environment exactly from ``uv.lock``."""
        _run(["uv", "sync", "--locked", "--compile-bytecode", "--no-progress"], cwd=tree, failure="sync-failed")

    def build_bundle(self, tree: Path) -> None:
        """Build the bundle with the Node version pinned by ``.nvmrc``; refuse any other Node."""
        web = tree / "serve/cockpit/web"
        pinned = (web / ".nvmrc").read_text(encoding="utf-8").strip().removeprefix("v")
        node = shutil.which("node")
        actual = _run([node, "--version"], failure="bundle-unavailable").stdout.strip() if node else ""
        if actual.removeprefix("v") != pinned:
            detail = f"Node {pinned} (serve/cockpit/web/.nvmrc) is required to build the bundle, found {actual!r}"
            raise ControllerError(
                code="bundle-unavailable", detail=f"{detail}; pass --bundle-source with a prebuilt dist"
            )
        _run(["npm", "ci", "--no-audit", "--no-fund"], cwd=web, failure="bundle-failed")
        _run(["npm", "run", "build"], cwd=web, failure="bundle-failed")
        shutil.rmtree(web / "node_modules", ignore_errors=True)


# ---------------------------------------------------------------------------
# Locks and running-controller detection
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def maintenance_lock(layout: Layout) -> Iterator[None]:
    """Serialize every controller-layout change; a second upgrade refuses instead of waiting."""
    if layout.root.is_symlink() or (layout.root.parent.is_symlink()):
        raise ControllerError(code="layout-invalid", detail=f"{CONTROLLER_ROOT} must not be a symlink")
    layout.root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(layout.root / _MAINTENANCE_LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            detail = "another delivery-controller command is running"
            raise ControllerError(code="upgrade-in-progress", detail=detail) from exc
        yield
    finally:
        os.close(descriptor)


@dataclass(frozen=True, slots=True)
class ProcessRow:
    """One same-user process: ``cmdline`` or ``cwd`` is ``None`` when it could not be read."""

    pid: int
    name: str
    cmdline: tuple[str, ...] | None
    cwd: str | None


type ProcessSource = Callable[[], list[ProcessRow]]


def psutil_processes() -> list[ProcessRow]:
    """Return same-user processes except this one and its ancestors; raise when the table is unreadable."""
    import psutil  # noqa: PLC0415 - optional at import for the stdlib-only callers of this module.

    excluded = {os.getpid(), *(parent.pid for parent in psutil.Process().parents())}
    rows = []
    for process in psutil.process_iter(["pid", "uids", "name"]):
        uids = process.info.get("uids")
        if process.pid in excluded or uids is None or uids.real != os.getuid():
            continue
        name = str(process.info.get("name") or "")
        rows.append(ProcessRow(process.pid, name, _guarded(process.cmdline, psutil), _guarded(process.cwd, psutil)))
    return rows


def _guarded(read: Callable[[], object], psutil: ModuleType) -> object:
    try:
        value = read()
    except psutil.NoSuchProcess:
        return ()
    except psutil.Error:
        return None
    return tuple(value) if isinstance(value, list) else value


def _is_controller(cmdline: tuple[str, ...]) -> bool:
    return any(marker in argument for argument in cmdline for marker in _CONTROLLER_MARKERS) or any(
        Path(argument).name in _CONTROLLER_PROGRAMS for argument in cmdline[:3]
    )


def _within(path: str, root: Path) -> bool:
    return path == str(root) or path.startswith(f"{root}/")


def running_controllers(workspace: Path, processes: ProcessSource) -> list[int]:
    """Return pids of controllers whose cwd is in the workspace; fail closed on an unreadable candidate.

    D03 controllers do not take ``controller.lock``, so the lock alone cannot prove that none runs.
    """
    try:
        rows = processes()
    except Exception as exc:
        raise ControllerError(code="controller-unknown", detail="the process table could not be read") from exc
    found, unknown = [], []
    for row in rows:
        candidate = _INTERPRETER_NAMES.match(row.name.lower()) is not None
        if row.cmdline is None:
            if candidate:
                unknown.append(row.pid)
        elif row.cmdline and _is_controller(row.cmdline):
            if row.cwd is None:
                unknown.append(row.pid)
            elif _within(row.cwd, workspace):
                found.append(row.pid)
    if unknown:
        detail = "a controller-like process could not be inspected"
        raise ControllerError(code="controller-unknown", detail=detail, pids=unknown)
    return found


@contextlib.contextmanager
def stopped_controllers(layout: Layout, processes: ProcessSource) -> Iterator[None]:
    """Hold the workspace controller lock exclusively after proving no controller process runs."""
    running = running_controllers(layout.workspace, processes)
    if running:
        detail = "stop the Delivery MCP server and Cockpit first"
        raise ControllerError(code="controller-running", detail=detail, pids=running)
    try:
        lock = acquire_controller_lock(layout.runtime, exclusive=True)
    except ControllerFencedError as exc:
        detail = "a Delivery controller holds the controller lock"
        raise ControllerError(code="controller-running", detail=detail) from exc
    try:
        yield
    finally:
        lock.release()


# ---------------------------------------------------------------------------
# Release tree integrity
# ---------------------------------------------------------------------------


def _writable_entries(tree: Path) -> list[str]:
    found = ["."] if tree.lstat().st_mode & _WRITE_BITS else []
    for directory, names, files in os.walk(tree):
        for name in (*names, *files):
            path = Path(directory) / name
            if not path.is_symlink() and path.lstat().st_mode & _WRITE_BITS:
                found.append(path.relative_to(tree).as_posix())
                if len(found) >= 5:  # noqa: PLR2004 - a bounded sample is enough evidence.
                    return found
    return found


def _set_read_only(tree: Path) -> None:
    for directory, names, files in os.walk(tree, topdown=False):
        for name in (*files, *names):
            path = Path(directory) / name
            if not path.is_symlink():
                path.chmod(path.lstat().st_mode & ~_WRITE_BITS)
    tree.chmod(tree.lstat().st_mode & ~_WRITE_BITS)


def _remove_tree(tree: Path) -> None:
    """Remove a (possibly read-only) release tree without following links."""

    def _retry(function: Callable[..., object], path: str, _error: BaseException) -> None:
        Path(path).parent.chmod(stat.S_IRWXU)
        if not Path(path).is_symlink() and Path(path).is_dir():
            Path(path).chmod(stat.S_IRWXU)
        function(path)

    if tree.exists() or tree.is_symlink():
        tree.chmod(stat.S_IRWXU)
        shutil.rmtree(tree, onexc=_retry)


def read_release(layout: Layout, commit: str) -> dict[str, Any] | None:
    """Return a complete release's ``RELEASE.json``; ``None`` when absent (an incomplete install)."""
    path = layout.release(commit) / RELEASE_FILE
    if not path.is_file() or path.is_symlink():
        return None
    try:
        payload = json.loads(path.read_bytes())
    except ValueError as exc:
        raise ControllerError(code="release-invalid", detail=f"{RELEASE_FILE} of {commit} is unreadable") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != RELEASE_SCHEMA_VERSION:
        detail = f"{RELEASE_FILE} of {commit} has an unsupported schema_version"
        raise ControllerError(code="release-invalid", detail=detail)
    return payload


def verify_release(layout: Layout, commit: str) -> list[str]:
    """Return why one installed release is not intact; an empty list proves integrity."""
    tree = layout.release(commit)
    if tree.is_symlink() or not tree.is_dir():
        return [f"release {commit} is not installed"]
    try:
        release = read_release(layout, commit)
    except ControllerError as exc:
        return [exc.detail]
    if release is None:
        return [f"release {commit} is incomplete ({RELEASE_FILE} is absent)"]
    failures = [] if release.get("commit") == commit else [f"{RELEASE_FILE} names {release.get('commit')}"]
    try:
        modified = tree_digest(tree) != release.get("tree_sha256")
    except ReleaseIntegrityError as exc:
        modified, failures = True, [*failures, str(exc)]
    if modified:
        failures.append(f"release {commit} was modified after install (tree digest differs from {RELEASE_FILE})")
    failures += _interpreter_failures(commit, release.get("interpreter"))
    if writable := _writable_entries(tree):
        failures.append(f"release {commit} has writable entries: {writable}")
    return failures


def _interpreter_failures(commit: str, interpreter: object) -> list[str]:
    """The interpreter lives outside the release: its recorded binary must still hash as at install."""
    if not isinstance(interpreter, dict) or not isinstance(interpreter.get("path"), str):
        return [f"{RELEASE_FILE} of {commit} records no interpreter identity"]
    try:
        unchanged = file_sha256(interpreter["path"]) == interpreter.get("sha256")
    except OSError, ReleaseIntegrityError:
        unchanged = False
    return [] if unchanged else [f"the interpreter {interpreter['path']} of release {commit} changed after install"]


def _require_intact(layout: Layout, commit: str) -> dict[str, Any]:
    failures = verify_release(layout, commit)
    if failures:
        raise ControllerError(code="release-invalid", detail="; ".join(failures))
    release = read_release(layout, commit)
    if release is None:  # pragma: no cover - verify_release reports an absent RELEASE.json.
        raise ControllerError(code="release-invalid", detail=f"release {commit} is incomplete")
    return release


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


def resolve_commit(source: Path, revision: str) -> str:
    """Resolve one revision of the source clone to its full commit."""
    arguments = ("rev-parse", "--verify", "--quiet", "--end-of-options", f"{revision}^{{commit}}")
    completed = subprocess.run(  # noqa: S603 - fixed Git argument vector.
        ("git", "-C", str(source), *arguments),  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    )
    commit = completed.stdout.strip()
    if completed.returncode != 0 or _COMMIT.fullmatch(commit) is None:
        raise ControllerError(code="commit-unknown", detail=f"{revision!r} is not a commit of {source}")
    return commit


def _extract(source: Path, commit: str, tree: Path) -> None:
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / "release.tar"
        _run(
            ["git", "-C", str(source), "archive", "--format=tar", "-o", str(archive), commit], failure="archive-failed"
        )
        with tarfile.open(archive) as handle:
            handle.extractall(tree, filter="data")


def _probe_release(tree: Path) -> dict[str, Any]:
    """Import every controller package with the release interpreter and prove each comes from the tree."""
    python = tree / ".venv/bin/python"
    completed = _run([str(python), "-I", "-B", "-c", _PROBE], cwd=tree, failure="release-unusable")
    probe = json.loads(completed.stdout)
    real = Path(os.path.realpath(tree))
    outside = [module for module in probe["modules"] if not Path(os.path.realpath(module)).is_relative_to(real)]
    if outside:
        detail = f"release imports controller code from outside: {outside}"
        raise ControllerError(code="release-unusable", detail=detail)
    return probe


def _compile_sources(tree: Path) -> None:
    """Compile the editable workspace sources, which ``uv sync --compile-bytecode`` leaves uncompiled.

    A release interpreter then never needs to write bytecode into the read-only tree (root ignores modes).
    """
    sources = sorted(str(path) for path in (tree / "serve").glob("*/src") if path.is_dir())
    python = str(tree / ".venv/bin/python")
    _run([python, "-I", "-m", "compileall", "-q", *sources], cwd=tree, failure="release-unusable")


def install(  # noqa: PLR0913 - every install input is an explicit keyword.
    layout: Layout,
    revision: str,
    *,
    source: Path | None = None,
    bundle_source: Path | None = None,
    toolchain: Toolchain | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Build one immutable release; an intact release is reused, an incomplete one rebuilt."""
    source = (source or layout.workspace).resolve()
    commit = resolve_commit(source, revision)
    toolchain = toolchain or UvNodeToolchain()
    with maintenance_lock(layout):
        tree = layout.release(commit)
        if tree.is_symlink():
            raise ControllerError(code="layout-invalid", detail=f"release {commit} is a symlink")
        if tree.exists():
            if read_release(layout, commit) is not None:
                return {"status": "installed", "commit": commit, "reused": True, **_integrity(layout, commit)}
            _remove_tree(tree)
        layout.releases.mkdir(parents=True, exist_ok=True)
        tree.mkdir()
        _extract(source, commit, tree)
        bundle = _install_bundle(tree, bundle_source, toolchain)
        toolchain.sync(tree)
        probe = _probe_release(tree)
        _compile_sources(tree)
        release = {
            "schema_version": RELEASE_SCHEMA_VERSION,
            "commit": commit,
            "supported_format": probe["supported_format"],
            "interpreter": {
                "path": probe["interpreter"],
                "version": probe["python"],
                "sha256": file_sha256(probe["interpreter"]),
            },
            "platform": f"{sys.platform}-{os.uname().machine}",
            "bundle": bundle,
            "installed_at": now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _set_read_only(tree)
        _require_sealed(tree, commit)
        tree.chmod(stat.S_IRWXU)
        release["tree_sha256"] = tree_digest(tree)
        (tree / RELEASE_FILE).write_text(json.dumps(release, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (tree / RELEASE_FILE).chmod(0o444)
        tree.chmod(0o555)
        _require_sealed(tree, commit)
    return {"status": "installed", "commit": commit, "reused": False, "release": release}


def _require_sealed(tree: Path, commit: str) -> None:
    """Refuse a release whose entries kept a write bit (a filesystem that ignores modes cannot hold one)."""
    if writable := _writable_entries(tree):
        detail = f"release {commit} could not be sealed read-only; writable entries: {writable}"
        raise ControllerError(code="release-invalid", detail=detail)


def _integrity(layout: Layout, commit: str) -> dict[str, Any]:
    failures = verify_release(layout, commit)
    if failures:
        raise ControllerError(code="release-invalid", detail="; ".join(failures))
    return {"release": read_release(layout, commit)}


def bundle(
    layout: Layout,
    revision: str,
    output: Path,
    *,
    source: Path | None = None,
    toolchain: Toolchain | None = None,
) -> dict[str, Any]:
    """Build one commit's Cockpit bundle from its archive with the pinned Node into ``output``."""
    source = (source or layout.workspace).resolve()
    commit = resolve_commit(source, revision)
    if output.exists():
        raise ControllerError(code="bundle-invalid", detail=f"{output} already exists")
    with tempfile.TemporaryDirectory() as directory:
        tree = Path(directory) / "tree"
        tree.mkdir()
        _extract(source, commit, tree)
        (toolchain or UvNodeToolchain()).build_bundle(tree)
        shutil.copytree(tree / "serve/cockpit/dist", output)
    return {"status": "built", "commit": commit, "index_sha256": file_sha256(output / "index.html")}


def _install_bundle(tree: Path, bundle_source: Path | None, toolchain: Toolchain) -> dict[str, str]:
    dist = tree / "serve/cockpit/dist"
    if bundle_source is not None:
        if not (bundle_source / "index.html").is_file():
            raise ControllerError(code="bundle-unavailable", detail=f"{bundle_source} has no index.html")
        shutil.rmtree(dist, ignore_errors=True)
        shutil.copytree(bundle_source, dist, symlinks=False)
        origin = "copied"
    else:
        toolchain.build_bundle(tree)
        origin = "built"
    if not (dist / "index.html").is_file():
        raise ControllerError(code="bundle-unavailable", detail="the Cockpit bundle has no index.html")
    return {"origin": origin, "index_sha256": file_sha256(dist / "index.html")}


# ---------------------------------------------------------------------------
# pin, switch, verify, list, prune
# ---------------------------------------------------------------------------


def launcher_bytes(layout: Layout, commit: str, name: str, pinned: ControllerPin) -> bytes:
    """Return the generated launcher: verify the release, then run its controller isolated from the caller.

    The launcher embeds ``owlbear_delivery.release_integrity`` and runs it with ``-I -S``: the release's
    ``RELEASE.json`` must hash to the pinned digest and the tree and interpreter must match it before
    site-packages (and their ``.pth`` files) or any release module load.
    """
    release = os.path.realpath(layout.release(commit))
    python = shlex.quote(f"{release}/.venv/bin/python")
    verifier = shlex.quote(Path(release_integrity.__file__).read_text(encoding="utf-8"))
    anchors = f"{pinned.release_sha256} {pinned.release_stat_sha256}"
    return (
        "#!/bin/sh\n"
        f"# Generated by delivery-controller for release {commit}; do not edit.\n"
        f"exec env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV {python} -I -S -B -c {verifier} "
        f'{shlex.quote(release)} {anchors} {name} "$@"\n'
    ).encode()


def _release_sha256(layout: Layout, commit: str) -> str:
    return hashlib.sha256(release_integrity.read_release_record(layout.release(commit))).hexdigest()


def _release_stat(layout: Layout, commit: str) -> str | None:
    """Stat fingerprint of one release and its recorded interpreter; ``None`` when either is unreadable."""
    try:
        interpreter = (read_release(layout, commit) or {})["interpreter"]["path"]
        return release_integrity.stat_fingerprint(layout.release(commit), interpreter)
    except ControllerError, KeyError, TypeError, OSError:
        return None


def _pin_bytes(pinned: ControllerPin, now: datetime) -> bytes:
    payload = {
        "schema_version": PIN_SCHEMA_VERSION,
        "commit": pinned.commit,
        "previous": pinned.previous,
        "release_sha256": pinned.release_sha256,
        "release_stat_sha256": pinned.release_stat_sha256,
        "pinned_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def _replace(path: Path, content: bytes, mode: int) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.unlink(missing_ok=True)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        os.write(descriptor, content)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.chmod(mode)
    temporary.replace(path)


def release_gate(layout: Layout, commit: str) -> dict[str, Any]:
    """Run one release's own capability gate against the workspace (D3 rollback/downgrade oracle)."""
    python = layout.release(commit) / ".venv/bin/python"
    completed = _run([str(python), "-I", "-B", "-c", _GATE_PROBE, str(layout.workspace)], failure="release-unusable")
    return json.loads(completed.stdout)


def current_pin(layout: Layout) -> ControllerPin | None:
    """Return the workspace pin, raising a typed refusal when it is unusable."""
    try:
        return read_controller_pin(layout.workspace)
    except ControllerPinError as exc:
        raise ControllerError(code="pin-invalid", detail=str(exc)) from exc


def pin(
    layout: Layout,
    revision: str,
    *,
    first: bool,
    processes: ProcessSource = psutil_processes,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Pin (``first``) or switch to an intact release whose gate accepts the stopped workspace's state."""
    commit = revision if _COMMIT.fullmatch(revision) else resolve_commit(layout.workspace, revision)
    with maintenance_lock(layout), stopped_controllers(layout, processes):
        existing = current_pin(layout)
        if first and existing is not None:
            detail = f"the workspace is pinned to {existing.commit}; use switch"
            raise ControllerError(code="already-pinned", detail=detail)
        if not first and existing is None:
            raise ControllerError(code="not-pinned", detail="the workspace has no pinned release; use pin")
        if existing is not None and existing.commit == commit:
            raise ControllerError(code="already-current", detail=f"release {commit} is already pinned")
        fingerprint = _release_stat(layout, commit)
        _require_intact(layout, commit)
        if fingerprint is None or _release_stat(layout, commit) != fingerprint:
            detail = f"release {commit} changed while it was verified"
            raise ControllerError(code="release-invalid", detail=detail)
        gate = release_gate(layout, commit)
        if not gate["gated"]:
            detail = f"release {commit} has no capability gate and cannot be pinned"
            raise ControllerError(code="release-ungated", detail=detail)
        if gate["refusals"]:
            raise ControllerError(
                code="release-refuses-state",
                detail=f"release {commit} refuses this state; restoring a backup is a user decision",
                refusals=gate["refusals"],
            )
        layout.bin.mkdir(parents=True, exist_ok=True)
        previous = existing.commit if existing is not None else None
        pinned = ControllerPin(commit, _release_sha256(layout, commit), fingerprint, previous)
        for name in LAUNCHERS:
            _replace(layout.bin / name, launcher_bytes(layout, commit, name, pinned), 0o555)
        _replace(layout.pin, _pin_bytes(pinned, now()), 0o444)
    return {"status": "pinned", "commit": commit, "previous": previous}


def verify(layout: Layout, commit: str | None = None) -> dict[str, Any]:
    """Verify one release (default: the pinned one) and, for the pin, its generated launchers."""
    pinned = current_pin(layout)
    target = commit or (pinned.commit if pinned else None)
    if target is None:
        detail = "the workspace has no pinned release; name a release to verify"
        raise ControllerError(code="not-pinned", detail=detail)
    failures = verify_release(layout, target)
    current = pinned is not None and pinned.commit == target
    if pinned is not None and current:
        failures += _pin_failures(layout, pinned)
    result = {
        "verified": not failures,
        "commit": target,
        "pinned": current,
        "failures": failures,
    }
    if pinned is not None and current:
        # A false fast_start is not a failure: every start then re-hashes the whole release.
        result["fast_start"] = _release_stat(layout, target) == pinned.release_stat_sha256
    return result


def _pin_failures(layout: Layout, pinned: ControllerPin) -> list[str]:
    try:
        anchored = _release_sha256(layout, pinned.commit) == pinned.release_sha256
    except OSError, ReleaseIntegrityError:
        anchored = False
    failures = [] if anchored else [f"pin.json does not name the {RELEASE_FILE} of release {pinned.commit}"]
    for name in LAUNCHERS:
        path = layout.bin / name
        expected = launcher_bytes(layout, pinned.commit, name, pinned)
        if path.is_symlink() or not path.is_file() or path.read_bytes() != expected:
            failures.append(f"launcher bin/{name} does not exec the pinned release")
        elif not os.access(path, os.X_OK):
            failures.append(f"launcher bin/{name} is not executable")
    return failures


def list_releases(layout: Layout) -> dict[str, Any]:
    """List installed releases with completeness, pin and rollback roles."""
    pinned = current_pin(layout)
    rows = []
    entries = sorted(layout.releases.iterdir()) if layout.releases.is_dir() else []
    for tree in entries:
        if _COMMIT.fullmatch(tree.name) is None:
            continue
        release = read_release(layout, tree.name)
        rows.append(
            {
                "commit": tree.name,
                "complete": release is not None,
                "supported_format": (release or {}).get("supported_format"),
                "installed_at": (release or {}).get("installed_at"),
                "role": _role(pinned, tree.name),
            }
        )
    return {"pin": None if pinned is None else {"commit": pinned.commit, "previous": pinned.previous}, "releases": rows}


def _role(pinned: ControllerPin | None, commit: str) -> str | None:
    if pinned is None:
        return None
    return "current" if pinned.commit == commit else "previous" if pinned.previous == commit else None


def prune(layout: Layout, *, processes: ProcessSource = psutil_processes) -> dict[str, Any]:
    """Remove every release except the pinned (current) one and its previous release (U3)."""
    with maintenance_lock(layout), stopped_controllers(layout, processes):
        pinned = current_pin(layout)
        if pinned is None:
            detail = "prune keeps the current and previous release; nothing is pinned"
            raise ControllerError(code="not-pinned", detail=detail)
        kept = {pinned.commit, *([pinned.previous] if pinned.previous else [])}
        removed = []
        for tree in sorted(layout.releases.iterdir()):
            if tree.name not in kept and not tree.name.startswith("."):
                _remove_tree(tree)
                removed.append(tree.name)
    return {"status": "pruned", "kept": sorted(kept), "removed": removed}


# ---------------------------------------------------------------------------
# preflight (D6): offline custody classification of a stopped workspace
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Finding:
    """One custody observation; ``locator`` is relative to the Delivery state root."""

    code: str
    locator: str
    detail: str


@dataclass
class _Custody:
    blockers: list[Finding] = field(default_factory=list)
    attention: list[Finding] = field(default_factory=list)

    def block(self, code: str, locator: str, detail: str) -> None:
        self.blockers.append(Finding(code, locator, detail))

    def note(self, code: str, locator: str, detail: str) -> None:
        self.attention.append(Finding(code, locator, detail))


type WindowState = Callable[[dict[str, Any]], str]


def process_window_state(window: dict[str, Any]) -> str:
    """Return ``alive``, ``gone`` or ``unknown`` for one recorded issuer window (pid and start time)."""
    from owlbear_delivery.worker_stall import ProcessWindowLivenessProbe, WindowHostIdentity  # noqa: PLC0415

    try:
        identity = WindowHostIdentity.model_validate(window)
    except ValueError:
        return "unknown"
    return ProcessWindowLivenessProbe().window_state(identity)


def _read_json(delivery: Path, path: Path) -> object:
    """Read one bounded regular record inside the Delivery root, never following a link or blocking.

    Every component below ``delivery`` is opened relative to its parent without following links, and the
    record itself nonblocking, so a FIFO, device or symlink is refused (``ValueError``) instead of stalling
    the caller, which holds the exclusive controller lock.
    """
    parts = path.relative_to(delivery).parts
    try:
        descriptor = os.open(delivery, _DIRECTORY_FLAGS)
    except OSError as exc:
        raise ValueError(path.name) from exc
    try:
        for part in parts[:-1]:
            child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        record = os.open(parts[-1], _RECORD_FLAGS, dir_fd=descriptor)
    except OSError as exc:
        raise ValueError(path.name) from exc
    finally:
        os.close(descriptor)
    try:
        info = os.fstat(record)
        if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_RECORD_BYTES:
            raise ValueError(path.name)
        content = os.read(record, _MAX_RECORD_BYTES + 1)
    finally:
        os.close(record)
    if len(content) > _MAX_RECORD_BYTES:
        raise ValueError(path.name)
    try:
        return json.loads(content)
    except RecursionError as exc:
        raise ValueError(path.name) from exc


def preflight(
    layout: Layout,
    *,
    processes: ProcessSource = psutil_processes,
    window_state: WindowState = process_window_state,
) -> dict[str, Any]:
    """Classify blocking custody with every controller stopped and the controller lock held (D6)."""
    with maintenance_lock(layout), stopped_controllers(layout, processes):
        custody = _Custody()
        report = scan_capability(layout.workspace)
        for refusal in report.refusals:
            if refusal.code == "state-migration-required":
                custody.note("migration-required", refusal.locator, "run delivery-migrate propose/apply/verify")
            else:
                custody.block(refusal.code, refusal.locator, refusal.detail)
        delivery = layout.workspace / DELIVERY_STATE_ROOT
        _scan_transactions(delivery, custody)
        _scan_changes(delivery, custody, window_state)
        _scan_pull_request_operations(delivery, custody)
    return {
        "ready": not custody.blockers,
        "format": report.format,
        "blockers": [_row(finding) for finding in custody.blockers],
        "attention": [_row(finding) for finding in custody.attention],
    }


def _row(finding: Finding) -> dict[str, str]:
    return {"code": finding.code, "locator": finding.locator, "detail": finding.detail}


def _scan_transactions(delivery: Path, custody: _Custody) -> None:
    """Any ``RuntimeTransaction`` manifest pending anywhere in Delivery state blocks the upgrade."""
    if not delivery.is_dir():
        return
    for directory, names, files in os.walk(delivery):
        relative = Path(directory).relative_to(delivery)
        if relative == Path():
            names[:] = [name for name in names if name != "worktrees"]
        if relative.name == "transactions":
            for name in sorted(files):
                if name.endswith(".yaml"):
                    custody.block("transaction-pending", (relative / name).as_posix(), "a state transaction is pending")


def _scan_changes(delivery: Path, custody: _Custody, window_state: WindowState) -> None:
    changes, coordination = delivery / "runtime/changes", delivery / "runtime/coordination/changes"
    names = {path.name for path in changes.iterdir() if path.is_dir()} if changes.is_dir() else set()
    if coordination.is_dir():
        names |= {path.stem for path in coordination.glob("*.json")}
    for change in (changes / name for name in sorted(names)):
        if change.is_symlink():
            custody.block("custody-unknown", _locator(delivery, change), "a Change directory is a symlink")
            continue
        claims = _frontier_claims(delivery, change, custody)
        claims += _coordination_claims(delivery, change.name, custody)
        _scan_action_receipts(delivery, change, custody)
        _scan_state_publication(delivery, change / "state-publication.json", custody)
        for attempt_id, role in claims:
            _classify_claim(
                delivery, change, attempt_id=attempt_id, role=role, custody=custody, window_state=window_state
            )


def _locator(delivery: Path, path: Path) -> str:
    return path.relative_to(delivery).as_posix()


def _scan_state_publication(delivery: Path, path: Path, custody: _Custody) -> None:
    """Only a ``pending`` intent blocks; an ``acknowledged`` one records a completed publication."""
    if not path.exists() and not path.is_symlink():
        return
    try:
        status = _read_json(delivery, path).get("status")  # type: ignore[union-attr]
    except ValueError, AttributeError:
        status = None
    if status == "pending":
        custody.block("pending-state-publication", _locator(delivery, path), "a Delivery state publication is pending")
    elif status != "acknowledged":
        custody.block("custody-unknown", _locator(delivery, path), "the state publication intent is unreadable")


def _frontier_claims(delivery: Path, change: Path, custody: _Custody) -> list[tuple[str, str]]:
    path = change / "frontier.json"
    if not path.exists() and not path.is_symlink():
        return []
    try:
        frontier = _read_json(delivery, path)
        bindings = frontier["bindings"]
        claims = [
            (str(binding["active_claim"]["attempt_id"]), str(binding["active_claim"]["worker_role"]))
            for binding in bindings
            if binding.get("active_claim")
        ]
        if frontier.get("integration_repair_claim"):
            claims.append((str(frontier["integration_repair_claim"]["attempt_id"]), "integration-repair"))
    except ValueError, KeyError, TypeError:
        custody.block("custody-unknown", _locator(delivery, path), "the frontier could not be classified")
        return []
    if frontier.get("pending_checkpoint"):
        custody.block("pending-checkpoint", _locator(delivery, path), "a checkpoint publication is pending")
    return claims


def _coordination_claims(delivery: Path, change_id: str, custody: _Custody) -> list[tuple[str, str]]:
    path = delivery / "runtime/coordination/changes" / f"{change_id}.json"
    if not path.exists() and not path.is_symlink():
        return []
    try:
        coordination = _read_json(delivery, path)
        attempt = coordination.get("finalization_attempt")
        lease = coordination.get("publication_lease")
        action = coordination.get("continuation_action")
    except ValueError, AttributeError:
        custody.block("custody-unknown", _locator(delivery, path), "the coordination record could not be classified")
        return []
    if lease:
        custody.block("publication-in-flight", _locator(delivery, path), "a Change publication holds its lease")
    if action and action.get("finished_at") is None:
        custody.note("engine-action-retained", _locator(delivery, path), f"{action.get('kind')} custody is retained")
    if attempt and attempt.get("finished_at") is None:
        return [(str((attempt.get("writer") or {}).get("attempt_id")), "finalizer")]
    return []


def _classify_claim(  # noqa: PLR0913 - one claim classification binds each input explicitly.
    delivery: Path, change: Path, *, attempt_id: str, role: str, custody: _Custody, window_state: WindowState
) -> None:
    issuer = change / "claim-issuers" / f"{attempt_id}.json"
    locator = _locator(delivery, issuer)
    try:
        window = _read_json(delivery, issuer).get("window")
    except ValueError, AttributeError:
        window = None
    state = window_state(window) if isinstance(window, dict) else "unknown"
    if state == "gone":
        custody.note("claim-host-lost", locator, f"{role} claim's issuing window is gone; Delivery settles it")
    else:
        custody.block("claim-running", locator, f"{role} claim {attempt_id} has a {state} issuing window")


def _scan_action_receipts(delivery: Path, change: Path, custody: _Custody) -> None:
    receipts = change / "action-receipts"
    if not receipts.is_dir():
        return
    for operation in sorted(path for path in receipts.iterdir() if path.is_dir() and not path.is_symlink()):
        locator = _locator(delivery, operation)
        started, result = (operation / "started.json").exists(), operation / "result.json"
        if operation.name.startswith("direct-"):
            if started and not (operation / "finished.json").exists():
                custody.block(
                    "direct-operation-started", locator, "a direct engine operation started without finishing"
                )
            continue
        if started and not result.exists():
            custody.block("engine-action-started", locator, "an engine action started without a result")
        elif result.exists():
            _classify_action_result(delivery, change, operation, custody)


def _classify_action_result(delivery: Path, change: Path, operation: Path, custody: _Custody) -> None:
    locator = _locator(delivery, operation / "result.json")
    try:
        result = _read_json(delivery, operation / "result.json")
        kind, reason = result.get("kind"), result.get("reason_code")
        coordination = _read_json(delivery, delivery / "runtime/coordination/changes" / f"{change.name}.json")
        action = coordination.get("continuation_action") or {}
    except ValueError, AttributeError:
        custody.block("custody-unknown", locator, "an engine action result could not be classified")
        return
    retained = action.get("operation_id") == operation.name and action.get("finished_at") is None
    if kind == "blocked" and retained:
        if reason == "engine-action-interrupted":
            custody.block("engine-action-interrupted", locator, "the owner result is unknown; settle its owner first")
        else:
            custody.note(str(reason), locator, "a blocked engine action with a known effect retains custody")


_RECEIPTED_OPERATIONS = {
    "summary-operations": "summary-receipts",
    "draft-state-operations": "draft-state-receipts",
    "supersession-operations": "supersession-receipts",
}


def _scan_pull_request_operations(delivery: Path, custody: _Custody) -> None:
    root = delivery / "runtime/publications/pull-requests"
    for operations, receipts in _RECEIPTED_OPERATIONS.items():
        directory = root / operations
        if not directory.is_dir():
            continue
        for operation in sorted(directory.glob("*.json")):
            if not (root / receipts / operation.name).exists():
                custody.block(
                    "publication-unreceipted", _locator(delivery, operation), "a pull-request operation has no receipt"
                )


# ---------------------------------------------------------------------------
# backup (procedure step 4)
# ---------------------------------------------------------------------------


def _manifest(root: Path) -> dict[str, str]:
    manifest = {}
    for directory, names, files in os.walk(root):
        base = Path(directory)
        if base == root:
            names[:] = [name for name in names if name != "worktrees"]
        for name in [*files, *(name for name in names if (base / name).is_symlink())]:
            path = base / name
            locator = path.relative_to(root).as_posix()
            if path.is_symlink():
                manifest[locator] = f"symlink:{path.readlink()}"
                continue
            try:
                manifest[locator] = file_sha256(path)
            except ReleaseIntegrityError as exc:
                detail = f"{locator} is not a regular file; state was not changed"
                raise ControllerError(code="backup-invalid", detail=detail) from exc
    return manifest


_DELIVERY_REF = re.compile(r"refs/(heads/owlbear|owlbear|remotes/[^/]+/owlbear)/.+")


def _delivery_refs(workspace: Path) -> list[str]:
    """Return ``<object> <ref>`` lines of Change branches, Delivery state and engine refs."""
    arguments = ["git", "-C", str(workspace), "for-each-ref", "--format=%(objectname) %(refname)"]
    completed = _run([*arguments, "refs/heads/owlbear/", "refs/owlbear/", "refs/remotes/"], failure="backup-failed")
    return [line for line in completed.stdout.splitlines() if _DELIVERY_REF.fullmatch(line.split(" ", 1)[1])]


def backup(layout: Layout, destination: Path, *, processes: ProcessSource = psutil_processes) -> dict[str, Any]:
    """Copy Delivery state (without worktrees) and Delivery refs outside the repository, then verify them."""
    destination = destination.resolve()
    if destination.is_relative_to(layout.workspace):
        detail = "the backup destination must be outside the repository"
        raise ControllerError(code="backup-invalid", detail=detail)
    if destination.exists():
        raise ControllerError(code="backup-invalid", detail=f"{destination} already exists")
    with maintenance_lock(layout), stopped_controllers(layout, processes):
        source = layout.workspace / DELIVERY_STATE_ROOT
        before = _manifest(source)
        destination.mkdir(parents=True)
        shutil.copytree(source, destination / "delivery", symlinks=True, ignore=_ignore_worktrees(source))
        refs = _delivery_refs(layout.workspace)
        (destination / "refs.txt").write_text("".join(f"{line}\n" for line in refs), encoding="utf-8")
        if refs:
            names = [line.split(" ", 1)[1] for line in refs]
            _run(
                [
                    "git",
                    "-C",
                    str(layout.workspace),
                    "bundle",
                    "create",
                    str(destination / "delivery-refs.bundle"),
                    *names,
                ],
                failure="backup-failed",
            )
        copied = _manifest(destination / "delivery")
        (destination / "manifest.json").write_text(
            json.dumps(before, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if copied != before or _manifest(source) != before:
        detail = "the copy does not match the source manifest; state was not changed"
        raise ControllerError(code="backup-invalid", detail=detail)
    return {"status": "backed-up", "destination": str(destination), "files": len(before), "refs": len(refs)}


def _ignore_worktrees(source: Path) -> Callable[[str, list[str]], list[str]]:
    def ignore(directory: str, names: list[str]) -> list[str]:
        return ["worktrees"] if Path(directory) == source and "worktrees" in names else []

    return ignore


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="delivery-controller", description=__doc__.splitlines()[0])
    parser.add_argument("--project-root", type=Path, default=None, help="workspace root (default: cwd)")
    commands = parser.add_subparsers(dest="command", required=True)
    install_parser = commands.add_parser("install", help="build one immutable release from a commit")
    install_parser.add_argument("revision")
    install_parser.add_argument("--source", type=Path, default=None, help="OwlBear clone (default: the workspace)")
    install_parser.add_argument("--bundle-source", type=Path, default=None, help="prebuilt Cockpit dist directory")
    install_parser.add_argument("--pin", action="store_true", help="pin the release on an unpinned workspace")
    for name in ("pin", "switch"):
        commands.add_parser(name).add_argument("revision")
    commands.add_parser("verify").add_argument("revision", nargs="?", default=None)
    commands.add_parser("list")
    commands.add_parser("preflight")
    commands.add_parser("prune")
    commands.add_parser("backup").add_argument("--destination", type=Path, required=True)
    bundle_parser = commands.add_parser("bundle", help="build one commit's Cockpit bundle with the pinned Node")
    bundle_parser.add_argument("revision")
    bundle_parser.add_argument("--output", type=Path, required=True)
    bundle_parser.add_argument("--source", type=Path, default=None)
    return parser


def _install_command(layout: Layout, args: argparse.Namespace) -> dict[str, Any]:
    installed = install(layout, args.revision, source=args.source, bundle_source=args.bundle_source)
    if args.pin:
        installed["pin"] = pin(layout, installed["commit"], first=True)
    return installed


def run(argv: list[str] | None = None) -> tuple[int, dict[str, Any]]:
    """Execute one command and return its exit status and JSON payload."""
    args = _parser().parse_args(argv)
    layout = Layout((args.project_root or Path.cwd()).resolve())
    commands: dict[str, Callable[[], dict[str, Any]]] = {
        "install": lambda: _install_command(layout, args),
        "pin": lambda: pin(layout, args.revision, first=True),
        "switch": lambda: pin(layout, args.revision, first=False),
        "verify": lambda: verify(layout, args.revision),
        "list": lambda: list_releases(layout),
        "preflight": lambda: preflight(layout),
        "prune": lambda: prune(layout),
        "backup": lambda: backup(layout, args.destination),
        "bundle": lambda: bundle(layout, args.revision, args.output.resolve(), source=args.source),
    }
    try:
        payload = commands[args.command]()
    except ControllerError as exc:
        return 1, {"status": "refused", "code": exc.code, "detail": exc.detail, **exc.evidence}
    except OSError as exc:
        code = "layout-invalid" if exc.errno in {errno.ELOOP, errno.ENOTDIR} else "io-failed"
        return 1, {"status": "refused", "code": code, "detail": str(exc)}
    failed = payload.get("verified") is False or payload.get("ready") is False
    return (1 if failed else 0), payload


def main(argv: list[str] | None = None) -> int:
    """Console entry point: print one JSON object; exit 1 on a refusal, a failed verify or a blocked preflight."""
    code, payload = run(argv)
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return code


if __name__ == "__main__":  # pragma: no cover - console entry point.
    raise SystemExit(main())
