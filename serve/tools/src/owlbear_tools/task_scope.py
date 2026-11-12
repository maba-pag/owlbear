"""Task-owned Git changes, excluding imported history and preserving restorations and kept work."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable, Sequence
    from pathlib import Path

    type Run = Callable[[list[str]], subprocess.CompletedProcess[bytes]]
    type Paths = Callable[[list[str]], set[str]]

MERGE_PARENTS = 2
SPAN_ENDPOINTS = 2


@dataclass(frozen=True)
class Context:
    """Immutable task and target boundaries, with original kept work and optional candidate evidence."""

    base: str
    target: str
    maps_dir: Path | None = None
    kept_spans: tuple[str, ...] = ()
    measurement: bool = False


class ScopeError(ValueError):
    """The task's recorded scope cannot be derived from its Git objects."""


def text(run: Run, arguments: list[str]) -> str:
    """A Git query, with its command and error retained rather than interpreted as an empty result."""
    completed = run(arguments)
    if completed.returncode:
        detail = completed.stderr.decode(errors="replace").strip()
        msg = f"Git {' '.join(arguments)} exited {completed.returncode}: {detail}"
        raise ScopeError(msg)
    return completed.stdout.decode(errors="surrogateescape").strip()


def commit(run: Run, reference: str) -> str:
    """Resolve a supplied task or target reference to its immutable commit."""
    if not reference:
        msg = "A task or target commit reference is empty"
        raise ScopeError(msg)
    return text(run, ["rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"])


def between(run: Run, paths: Paths, before: str, after: str, target: str) -> set[str]:
    """Every own change along the first-parent task history, both rename ends and restorations included."""
    first, last = commit(run, before), commit(run, after)
    history = text(run, ["rev-list", "--first-parent", last]).splitlines()
    if first not in history:
        msg = f"Task base {first} is not on the first-parent history of {last}; its own changes are unknown"
        raise ScopeError(msg)
    selected: set[str] = set()
    for revision in reversed(history[: history.index(first)]):
        parents = text(run, ["show", "-s", "--format=%P", revision]).split()
        if len(parents) == 1:
            selected.update(paths(["diff", "--name-only", "-z", "--no-renames", parents[0], revision]))
        elif len(parents) == MERGE_PARENTS:
            imported = run(["merge-base", "--is-ancestor", parents[1], target])
            if imported.returncode not in {0, 1}:
                msg = (
                    f"Cannot identify target imports at {revision}: {imported.stderr.decode(errors='replace').strip()}"
                )
                raise ScopeError(msg)
            arguments = (
                ["show", "--remerge-diff", "--format=", "--name-only", "-z", "--no-renames", revision]
                if imported.returncode == 0
                else ["diff", "--name-only", "-z", "--no-renames", parents[0], revision]
            )
            selected.update(paths(arguments))
        else:
            msg = f"Cannot derive task changes at {revision}: expected one or two parents, found {len(parents)}"
            raise ScopeError(msg)
    return selected


def changed(run: Run, paths: Paths, base: str, kept: Sequence[str], target: str) -> list[str]:
    """Current task edits plus frozen original deltas of kept tasks; never the branch's whole diff."""
    head = commit(run, "HEAD")
    selected = between(run, paths, base, head, target)
    selected.update(paths(["diff", "--name-only", "-z", "--no-renames", head]))
    selected.update(paths(["ls-files", "--others", "--exclude-standard", "-z"]))
    for span in kept:
        endpoints = span.split("..")
        if len(endpoints) != SPAN_ENDPOINTS or not all(endpoints):
            msg = f"Invalid kept task span {span!r}; expected OLD..NEW"
            raise ScopeError(msg)
        selected.update(between(run, paths, endpoints[0], endpoints[1], target))
    return sorted(selected)


def explicit_targets(root: Path, targets: Sequence[str], recorded: Sequence[str] = ()) -> set[str]:
    """Current and recorded target members; the caller requires every surviving module."""
    selected: set[str] = set()
    for target in targets:
        name = PurePosixPath(target.split("::", 1)[0])
        path = root / name
        msg = (
            f"Explicit task test target {target!r} must name an existing checkout-relative "
            "test module, directory or node"
        )
        if name.is_absolute() or ".." in name.parts or not path.resolve().is_relative_to(root.resolve()):
            raise ScopeError(msg)
        modules = [path] if path.is_file() else sorted(path.rglob("test_*.py")) if path.is_dir() else []
        modules = sorted(
            {
                *modules,
                *(
                    root / module
                    for module in recorded
                    if (module == name.as_posix() or module.startswith(f"{name.as_posix()}/"))
                    and PurePosixPath(module).name.startswith("test_")
                    and module.endswith(".py")
                ),
            }
        )
        if (
            not modules
            or ("::" in target and not path.is_file() and name.as_posix() not in recorded)
            or any(
                not module.name.startswith("test_")
                or module.suffix != ".py"
                or not module.resolve().is_relative_to(root.resolve())
                for module in modules
            )
        ):
            raise ScopeError(msg)
        selected.update([target] if path.is_file() else (str(module.relative_to(root)) for module in modules))
    if recorded:
        selected = {target for target in selected if "::" not in target or target.split("::", 1)[0] not in selected}
    return selected


def arguments() -> argparse.Namespace:
    """Maintained test arguments, with explicit task context separate from ordinary branch scope."""
    parser = argparse.ArgumentParser(prog="test")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("-a", "--all", action="store_true", dest="all_tests")
    scope.add_argument("--changed", action="store_true")
    bases = parser.add_mutually_exclusive_group()
    bases.add_argument("--base", help="Git ref used as the committed-change baseline for --changed")
    bases.add_argument("--task-base", help="The task's recorded starting commit, never its branch upstream")
    parser.add_argument("--target", help="The resolved integration-target commit for task dependency evidence")
    parser.add_argument("--keep-span", action="append", default=[], help="An original kept task's OLD..NEW scope")
    parser.add_argument("--maps-dir", help="Explicit candidate CI-map directory for disposable proof")
    parser.add_argument("-m", "--measurement", action="store_true", help="Measure the surviving pinned suite members")
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    if args.all_tests and args.paths:
        parser.error("--all cannot be combined with paths")
    if args.base is not None and not args.changed:
        parser.error("--base requires --changed")
    if args.changed and args.paths and args.task_base is None:
        parser.error("--changed paths require --task-base and --target")
    if args.task_base is not None and not args.changed:
        parser.error("--task-base requires --changed")
    if args.task_base is not None and args.target is None:
        parser.error("--task-base requires --target")
    if args.measurement and args.task_base is None:
        parser.error("--measurement requires --task-base and --target")
    if any((args.target is not None, args.keep_span, args.maps_dir is not None)) and args.task_base is None:
        parser.error("--target, --keep-span and --maps-dir require --task-base")
    return args
