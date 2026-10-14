"""The builder's lint (TD-87): fast static linters the repository configures, on the files a build changed."""

from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import PurePosixPath
from time import monotonic
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

TIMEOUT = 120  # seconds per linter run
BUDGET = 180  # seconds for all linters of one submit
DRAIN = 5  # seconds to read a killed linter's output
SHOWN = 60  # output lines the builder reads
REFUSALS = 3  # submits lint may refuse in one session; later ones pass with lint-unresolved
PY = (".py", ".pyi")
JS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
ESLINT = (
    *(f"eslint.config.{e}" for e in ("js", "mjs", "cjs", "ts", "mts", "cts")),
    *(f".eslintrc{e}" for e in ("", ".js", ".cjs", ".json", ".yml", ".yaml")),
)
BIOME = (*JS, ".json", ".jsonc", ".css", ".graphql", ".gql")
NODE = {  # tool: its configuration files, the files it lints and its arguments, never a fixing mode
    "biome": (("biome.json", "biome.jsonc"), BIOME, ("check", "--colors=off", "--no-errors-on-unmatched")),
    "eslint": (ESLINT, JS, ()),
}


@dataclass(frozen=True)
class Linter:
    """One linter run: its command, the directory it runs in and the repository-relative files it checks."""

    name: str
    command: tuple[str, ...]
    home: PurePosixPath
    files: tuple[str, ...]


@dataclass(frozen=True)
class Outcome:
    """How one run ended: passed, failed with problems, or broken (crashed, timed out, could not start)."""

    state: Literal["passed", "failed", "broken"]
    output: str = ""
    reason: str = ""


def _few(paths: Sequence[str]) -> str:
    return ", ".join(paths[:5]) + (f" and {len(paths) - 5} more" if len(paths) > 5 else "")  # noqa: PLR2004


def _ruff_config(folder: Path) -> bool:
    if (folder / "ruff.toml").is_file() or (folder / ".ruff.toml").is_file():
        return True
    try:
        return "ruff" in tomllib.loads((folder / "pyproject.toml").read_text(encoding="utf-8")).get("tool", {})
    except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError:
        return False


def _ruff(root: Path) -> tuple[str, ...] | None:
    """The repository's locked ruff through uv when uv.lock lists it, else ruff on PATH."""
    uv = shutil.which("uv")
    with contextlib.suppress(OSError, UnicodeDecodeError):
        locked = '\nname = "ruff"\n' in (root / "uv.lock").read_text(encoding="utf-8")
        if uv and locked and (root / "pyproject.toml").is_file():
            return uv, "run", "--locked", "--offline", "--quiet", "ruff"
    ruff = shutil.which("ruff")
    return (ruff,) if ruff else None


def _python(root: Path, files: Sequence[str]) -> tuple[list[Linter], list[str]]:
    py = [f for f in files if f.endswith(PY)]
    configured = {d: _ruff_config(root / d) for d in {d for f in py for d in PurePosixPath(f).parents}}
    linted = tuple(f for f in py if any(configured[d] for d in PurePosixPath(f).parents))
    unconfigured = [f for f in py if f not in linted]
    skipped = [f"ruff: no configuration for {_few(unconfigured)}"] if unconfigured else []
    if not linted:
        return [], skipped
    if (ruff := _ruff(root)) is None:
        return [], [*skipped, "ruff: not installed"]
    here = PurePosixPath()
    return [
        Linter("ruff check", (*ruff, "check", "--no-fix", "--no-cache", "--force-exclude"), here, linted),
        Linter("ruff format", (*ruff, "format", "--check", "--no-cache", "--force-exclude"), here, linted),
    ], skipped


def _homes(root: Path, files: Sequence[str], configs: Sequence[str]) -> dict[PurePosixPath, list[str]]:
    """Each file under the nearest directory holding one of *configs*; files without one are left out."""
    homes: dict[PurePosixPath, list[str]] = {}
    for f in files:
        dirs = PurePosixPath(f).parents
        if (home := next((d for d in dirs if any((root / d / c).is_file() for c in configs)), None)) is not None:
            homes.setdefault(home, []).append(f)
    return homes


def _binary(root: Path, home: PurePosixPath, name: str) -> Path | str:
    """The nearest installed *name*, resolved, or why it is skipped: no link runs a program outside the repository."""
    bins = (root / d / "node_modules" / ".bin" / name for d in (home, *home.parents))
    if (binary := next((b for b in bins if b.is_file()), None)) is None:
        return f"{name}: not installed for {home}"
    real, binary = root.resolve(), binary.resolve()
    if binary.is_relative_to(real) and (root / home).resolve().is_relative_to(real):
        return binary
    return f"{name} for {home}: its executable or folder resolves outside the repository"


def _node(root: Path, files: Sequence[str]) -> tuple[list[Linter], list[str]]:
    linters, skipped = [], []
    for name, (configs, suffixes, args) in NODE.items():
        for home, group in _homes(root, [f for f in files if f.endswith(suffixes)], configs).items():
            if isinstance(binary := _binary(root, home, name), str):
                skipped.append(binary)
            else:
                linters.append(Linter(name, (str(binary), *args), home, tuple(group)))
    return linters, skipped


def plan(root: Path, files: Sequence[str]) -> tuple[list[Linter], list[str]]:
    """The linters the repository configures for *files*, and why any linter is skipped."""
    python, skipped = _python(root, files)
    node, more = _node(root, files)
    return [*python, *node], [*skipped, *more]


def _arg(path: PurePosixPath) -> str:
    return f"./{path}" if str(path).startswith("-") else str(path)


def _killed(proc: subprocess.Popen[str]) -> str:
    """Kill the linter's process group and read its output briefly; a detached descendant may hold it open."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGKILL)
    try:
        return proc.communicate(timeout=DRAIN)[0].strip()
    except subprocess.TimeoutExpired:
        if proc.stdout:
            proc.stdout.close()
        return "(output unread: a process the linter started still holds it open)"


def run(root: Path, linter: Linter, timeout: float = TIMEOUT) -> Outcome:
    """Run one linter with a timeout; its whole process group is killed when it runs over."""
    argv = [*linter.command, *(_arg(PurePosixPath(f).relative_to(linter.home)) for f in linter.files)]
    try:
        proc = subprocess.Popen(  # noqa: S603 - an argument vector of a configured linter, no shell
            argv,
            cwd=root / linter.home,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,
        )
    except OSError as exc:
        return Outcome("broken", str(exc), f"could not start: {type(exc).__name__}")
    with proc:
        try:
            output = proc.communicate(timeout=timeout)[0]
        except subprocess.TimeoutExpired:
            return Outcome("broken", _killed(proc), "timed out")
    code = proc.returncode
    if code in {0, 1}:
        return Outcome("passed" if code == 0 else "failed", output.strip())
    return Outcome("broken", output.strip(), f"exited {code}")


def _shown(output: str) -> str:
    lines = output.splitlines() or ["(no output)"]
    more = f"\n... {len(lines) - SHOWN} more lines" if len(lines) > SHOWN else ""
    return "\n".join(lines[:SHOWN]) + more


class Lint:
    """One session's lint; a linter that breaks the same way twice is skipped, so a broken tool never traps it."""

    def __init__(self, log: Callable[..., None]) -> None:
        """Bind the step's activity log."""
        self.log = log
        self.broken: dict[tuple[str, PurePosixPath], str] = {}  # each linter's last breakage in this session
        self.skipped: dict[tuple[str, PurePosixPath], str] = {}  # linters that broke the same way twice
        self.refused = 0

    def check(self, root: Path, changed: Sequence[str]) -> list[str]:
        """Lint the changed files that still exist; return one submit error per failing linter."""
        errors = self._check(root, changed)
        if errors and self.refused >= REFUSALS:
            self.log(event="lint-unresolved", errors=[e.split("\n", 1)[0] for e in errors])
            return []
        self.refused += bool(errors)
        return errors

    def _check(self, root: Path, changed: Sequence[str]) -> list[str]:
        """Lint the changed files that still exist; return one submit error per failing linter."""
        linters, skipped = plan(root, [f for f in dict.fromkeys(changed) if (root / f).is_file()])
        errors, ran, end = [], [], monotonic() + BUDGET
        for linter in linters:
            if why := self._skip(linter, end):
                skipped.append(why)
                continue
            out = run(root, linter, min(TIMEOUT, end - monotonic()))
            ran.append({"tool": linter.name, "files": list(linter.files), "state": out.state})
            errors += self._error(linter, out)
        if ran or skipped:
            self.log(event="lint", ran=ran, skipped=skipped, passed=not errors)
        return errors

    def _skip(self, linter: Linter, end: float) -> str:
        if (reason := self.skipped.get((linter.name, linter.home))) is not None:
            return f"{linter.name}: skipped for this session, it broke twice ({reason})"
        if monotonic() >= end:
            return f"{linter.name}: not run, the {BUDGET} s lint budget for this submit is spent"
        return ""

    def _error(self, linter: Linter, out: Outcome) -> list[str]:
        where, shown = _few(linter.files), _shown(out.output)
        if out.state == "passed":
            return []
        if out.state == "failed":
            return [f"lint: {linter.name} found problems in {where} - fix them, commit, then submit again:\n{shown}"]
        if self.broken.get(key := (linter.name, linter.home)) == out.reason:
            self.skipped[key] = out.reason
            self.log(event="lint-skipped", tool=linter.name, reason=out.reason)
            return []
        self.broken[key] = out.reason
        advice = "if your change caused it, fix it and submit again; if the tool is broken, submit again and Delivery"
        return [f"lint: {linter.name} could not run ({out.reason}) on {where} - {advice} skips it:\n{shown}"]
