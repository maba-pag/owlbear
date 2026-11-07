"""The machine settings in force (D-01M5MZKEPPVMFC9HK795MMG91B): this machine's own value, else Global's, else unset.

Code ships no defaults (the owner, 2026-10-23): an unset setting is an error on the Settings page, and while one is
unset or can't be read no project's work starts (#808). What needs it does not run either: no update by itself without
its switches and channel, no automatic curation without its trigger, no agent session without the machine's total.
"""

from __future__ import annotations

import os
import stat
import subprocess
from collections import deque
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field

from owlbear_delivery_next.git.command_failure import failed, failure
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.local_system import data_place, data_repo, local_home
from owlbear_delivery_next.settings.config import GlobalLayer, MachineValues
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import StoreError, read_layer

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo

FIELDS: tuple[str, ...] = tuple(MachineValues.model_fields)
NO_SHARED = "no shared repository is set up, so there are no global machine settings"
BASE: MachineValues | None = None  # a layer under Global; empty in production (no code defaults), tests set one
type Inputs = tuple[bytes | str | None, ...]


def _input(path: Path) -> bytes | str | None:
    try:
        return "directory" if stat.S_ISDIR(path.stat().st_mode) else path.read_bytes()
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        return failure(exc)


def _identity(path: Path) -> str:
    try:
        target = str(path.resolve())
        try:
            found = path.stat()
        except FileNotFoundError:
            return repr((target, None))
        return repr((target, found.st_dev, found.st_ino, found.st_mode))
    except (OSError, ValueError, RuntimeError) as exc:
        return failure(exc)


def _location(view: str | None) -> tuple[Path | None, dict[str, str] | str | None]:
    record: dict[str, str] | str | None = None
    try:
        if view is not None:
            root = Path(view) if view else None
        else:
            record = data_place.stored()
            named = record.get("repository") if record else None
            root = data_place.default() if record is None else Path(named).expanduser().resolve() if named else None
    except (OSError, ValueError, RuntimeError) as exc:
        root, record = None, failure(exc)
    return root, record


def _config_roots(root: Path) -> tuple[Path, ...]:
    home = Path.home()
    xdg = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    named = [os.environ.get(key) for key in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG")]
    return tuple(
        (root / p).absolute() for p in (home / ".gitconfig", xdg / "git/config", *(Path(p) for p in named if p))
    )


def update_check_inputs(sources: tuple[Path, ...] = ()) -> Inputs:
    """Native bytes and identities of base inputs and refresh-discovered dependencies; never run Git."""
    home, view = local_home.root(), os.environ.get(data_repo.VIEW)
    root, record = _location(view)
    paths = [home / registry.MACHINE]
    if root is not None:
        paths.extend((root, root / data_repo.CONFIG))
    environment = None
    if view is None:
        paths.extend(
            (home / data_place.POINTER, home / data_place.OLD_POINTER, *_config_roots(root or Path.cwd()), *sources)
        )
        if root is not None:
            paths.extend((root / ".git", root / ".git/config", root / ".git/commondir"))
        # Config injected through the environment can contain credentials; the key retains only its digest.
        selected = sorted(
            (k, v)
            for k, v in os.environ.items()
            if k.startswith("GIT_CONFIG")
            or k
            in {
                "HOME",
                "XDG_CONFIG_HOME",
                "GIT_DIR",
                "GIT_COMMON_DIR",
                "GIT_WORK_TREE",
                "GIT_CEILING_DIRECTORIES",
                "GIT_DISCOVERY_ACROSS_FILESYSTEM",
            }
        )
        environment = sha256(repr(selected).encode(errors="surrogateescape")).hexdigest()
    return (
        str(home),
        view,
        repr(record),
        str(root) if root else None,
        environment,
        BASE.model_dump_json() if BASE is not None else None,
        *(token for path in dict.fromkeys(paths) for token in (str(path), _identity(path), _input(path))),
    )


def _reference(base: Path, name: str, prefix: str = "") -> Path | None:
    """Read .git/commondir's path protocol, without admission-specific validation or error wording."""
    path = base / name
    try:
        if stat.S_ISDIR(path.stat().st_mode):
            return path
        text = path.read_text()
    except FileNotFoundError:
        return None
    if not text.startswith(prefix) or not (value := text[len(prefix) :].rstrip("\r\n")):
        msg = f"{path} is not a readable Git directory reference"
        raise ValueError(msg)
    return (base / value).absolute()


def _git_sources(root: Path, paths: dict[Path, None]) -> tuple[Path, ...]:
    admin = (root / named).absolute() if (named := os.environ.get("GIT_DIR")) else _reference(root, ".git", "gitdir: ")
    if admin is None:
        return ()
    paths.update(
        dict.fromkeys((admin, admin / "commondir", admin / "HEAD", admin / "config", admin / "config.worktree"))
    )
    common = (
        (root / named).absolute()
        if (named := os.environ.get("GIT_COMMON_DIR"))
        else _reference(admin, "commondir") or admin
    )
    paths.update(dict.fromkeys((common, common / "config", common / "HEAD", common / "objects", common / "refs")))
    return admin / "config", admin / "config.worktree", common / "config"


def _native(*args: str, system: bool = False) -> subprocess.CompletedProcess[str]:
    """Parse one file independently, even when Git's ordinary startup config is broken."""
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    if system:
        for name in ("GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM"):
            if name in os.environ:
                environment[name] = os.environ[name]
    else:
        environment["GIT_CONFIG_NOSYSTEM"] = "1"
    command = ("git", f"--git-dir={os.devnull}", *args)
    try:
        command = (resolve_git_executable(), *command[1:])
        done = subprocess.run(  # noqa: S603 - validated Git executable, fixed metadata verbs and path arguments
            command,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=data_repo.GIT_SECONDS,
            check=False,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 128, "", failure(exc))
    return subprocess.CompletedProcess(
        done.args,
        done.returncode,
        done.stdout.decode("utf-8", "surrogateescape"),
        done.stderr.decode("utf-8", "surrogateescape"),
    )


_INCLUDES = ("--show-origin", "--null", "--path", "--get-regexp", r"^include(if\..*)?\.path$")


def _include_paths(done: subprocess.CompletedProcess[str], root: Path) -> tuple[Path, ...]:
    """Decode Git's NUL-delimited origin/key-value records, not Git configuration syntax."""
    records = done.stdout.split("\0")
    paths: list[Path] = []
    for origin, record in zip(records[0:-1:2], records[1:-1:2], strict=True):
        _, value = record.split("\n", 1)
        path = Path(value)
        if not path.is_absolute():
            path = (root / origin.removeprefix("file:")).parent / path if origin.startswith("file:") else root / path
        if origin.startswith("file:"):
            paths.append((root / origin.removeprefix("file:")).absolute())
        paths.append(path.absolute())
    return tuple(paths)


def _walk_includes(configs: tuple[Path, ...], root: Path, paths: dict[Path, None]) -> list[str]:
    """Recover dependency paths with independent native parses after --includes suppressed its output."""
    errors: list[str] = []
    pending, seen = deque(configs), set()
    while pending:
        path = pending.popleft()
        try:
            path.stat()
        except FileNotFoundError:
            continue
        identity = (path.resolve(), path.parent.resolve())
        if identity in seen:
            continue
        seen.add(identity)
        queried = _native("config", "--no-includes", "--file", str(path), *_INCLUDES)
        if queried.returncode not in {0, 1}:
            errors.append(f"the includes in {path} could not be read: {failed(queried)}")
            continue
        children = _include_paths(queried, root)
        paths.update(dict.fromkeys(children))
        pending.extend(children)
    return errors


def update_check_sources() -> tuple[tuple[Path, ...], str]:
    """Refresh-only Git dependency discovery; keep partial paths and whole diagnostics on failure."""
    if os.environ.get(data_repo.VIEW) is not None:
        return (), ""
    root, record = _location(None)
    if root is None:
        return (), record if isinstance(record, str) else ""
    configs = _config_roots(root)
    paths = dict.fromkeys(configs)
    errors: list[str] = []
    try:
        configs += _git_sources(root, paths)
    except (OSError, ValueError, RuntimeError) as exc:
        errors.append(f"the Git settings dependencies of {root} could not be found: {failure(exc)}")
    system = _native("var", "GIT_CONFIG_SYSTEM", system=True)
    if system.returncode == 0:
        system_paths = tuple(Path(p) for p in system.stdout.splitlines())
        configs += system_paths
        paths.update(dict.fromkeys(system_paths))
    elif system.returncode != 1:
        errors.append(f"the system Git settings path could not be found: {failed(system)}")
    try:
        try:
            root.stat()
        except FileNotFoundError:
            return tuple(paths), "\n".join(errors)
        included = data_repo.DataRepo(root).git("config", "--includes", *_INCLUDES, lossless=True)
        if included.returncode in {0, 1}:
            paths.update(dict.fromkeys(_include_paths(included, root)))
        else:
            errors.append(f"the Git settings dependencies of {root} could not be read: {failed(included)}")
            errors.extend(_walk_includes(configs, root, paths))
    except (OSError, ValueError, RuntimeError) as exc:
        errors.append(f"the Git settings dependencies of {root} could not be read: {failure(exc)}")
    return tuple(paths), "\n".join(dict.fromkeys(errors))


class Resolved(MachineValues):
    """Each machine setting in force, ``None`` where unset; where it came from; what is unset; Global's own."""

    sources: dict[str, Literal["machine", "global", "default"]] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)
    shared: dict[str, Any] = Field(default_factory=dict)  # Global's values, for the page's "inherit (…)"
    notice: str = ""  # why Global's could not be read


def resolve(local: MachineValues, glob: MachineValues | None, notice: str = "") -> Resolved:
    """Each field on its own: this machine's, else Global's, else unset."""
    layers = [("machine", local), ("global", glob or MachineValues())]
    if BASE is not None:
        layers.append(("default", BASE))
    values: dict[str, Any] = {}
    sources: dict[str, Any] = {}
    for name in FIELDS:
        source, value = next(((s, v) for s, layer in layers if (v := getattr(layer, name)) is not None), (None, None))
        values[name] = value
        if source:
            sources[name] = source
    missing = [n for n in FIELDS if values[n] is None]
    shared = (glob or MachineValues()).model_dump()
    return Resolved(**values, sources=sources, missing=missing, shared=shared, notice=notice)


def shared_values(shared: DataRepo | None) -> tuple[MachineValues | None, str]:
    """Global's machine settings, and why they could not be read; none without a shared repository."""
    if shared is None:
        return None, NO_SHARED
    try:
        return read_layer(shared.global_path, GlobalLayer).machine, ""
    except StoreError as exc:
        return None, f"the global settings are unreadable: {failure(exc)}"


def current(local: registry.Settings | None = None) -> Resolved:
    """The machine settings in force now; this machine's from ``machine.json`` unless given."""
    try:
        glob, notice = shared_values(data_repo.locate())
    except data_repo.DataRepoError as exc:
        glob, notice = None, failure(exc)
    return resolve(registry.load().settings if local is None else local, glob, notice)
