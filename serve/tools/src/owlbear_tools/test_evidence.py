"""Load complete CI dependency maps for task test selection."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import defaultdict
from typing import TYPE_CHECKING, cast

from owlbear_tools.test_dependencies import REPOSITORY, SUITES, Evidence, git, historical_inputs, read_evidence

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

RUN_PAGE_SIZE = 100
PRODUCER = "serve/tools/src/owlbear_tools/test_dependencies.py"


def _gh(root: Path, arguments: Sequence[str]) -> str:
    executable = shutil.which("gh")
    if executable is None:
        msg = f"GitHub CLI is unavailable while loading CI dependency maps in {root}"
        raise RuntimeError(msg)
    result = subprocess.run(  # noqa: S603 - fixed gh executable, argument vector, no shell.
        [executable, *arguments], cwd=root, text=True, capture_output=True, check=False
    )
    if result.returncode:
        msg = f"gh {' '.join(arguments)} in {root} exited {result.returncode}: {result.stderr.strip()}"
        raise RuntimeError(msg)
    return result.stdout


def _artifact(suite: str, shard: int, attempt: int) -> str:
    prefix = {
        "python": f"python-shard-{shard}",
        "python-browser": "python-browser",
        "delivery-next-browser": f"delivery-next-browser-{shard}",
    }[suite]
    return f"test-results-{prefix}-attempt-{attempt}"


def _read_maps(directory: Path, platforms: Sequence[str]) -> list[Evidence]:
    maps: list[Evidence] = []
    for path in sorted(directory.rglob("dependencies.json")):
        if not path.resolve().is_relative_to(directory.resolve()):
            msg = f"Dependency artifact {path} resolves outside {directory}"
            raise ValueError(msg)
        maps.append(read_evidence(path, platforms))
    return maps


def _complete(maps: Sequence[Evidence], required: set[str]) -> bool:
    return all(
        len(selected := [item for item in maps if item.suite == suite]) == SUITES[suite]
        and {item.shard for item in selected} == set(range(1, SUITES[suite] + 1))
        and all(item.shards == SUITES[suite] for item in selected)
        for suite in required
    )


def _validate(root: Path, maps: Sequence[Evidence]) -> None:
    historical = historical_inputs(root, maps[0].head)
    for item in maps:
        if item.inputs != historical:
            msg = f"Dependency inputs disagree with tracked Git objects at {item.head}, {item.suite}/{item.shard}"
            raise ValueError(msg)
        if item.run < 1 or item.attempt < 1:
            msg = f"Invalid CI run provenance at {item.head}: run {item.run}, attempt {item.attempt}"
            raise ValueError(msg)


def _candidate(root: Path, directory: Path, required: set[str]) -> list[Evidence]:
    groups: dict[tuple[str, int, int], list[Evidence]] = defaultdict(list)
    for item in _read_maps(directory, ("linux", sys.platform)):
        groups[item.head, item.run, item.attempt].append(item)
    for identity in sorted(groups, key=lambda key: (key[1], key[2]), reverse=True):
        maps = groups[identity]
        if _complete(maps, required):
            _validate(root, maps)
            sys.stdout.write(f"Candidate dependency evidence: {directory}, head {identity[0]}, run {identity[1]}\n")
            return maps
    msg = f"No complete candidate dependency maps in {directory}; required suites/shards: {required}, {SUITES}"
    raise RuntimeError(msg)


def _download(root: Path, run: dict[str, object], required: set[str]) -> list[Evidence]:
    run_id, attempt, head = run["id"], run["run_attempt"], run["head_sha"]
    names = {
        _artifact(suite, shard, cast("int", attempt)) for suite in required for shard in range(1, SUITES[suite] + 1)
    }
    available = set(
        _gh(
            root,
            [
                "api",
                f"repos/{REPOSITORY}/actions/runs/{run_id}/artifacts",
                "--paginate",
                "--jq",
                ".artifacts[] | select(.expired == false) | .name",
            ],
        ).splitlines()
    )
    if not names <= available:
        return []  # Identical-input cache hits are passes, not new dependency observations.
    destination = root / ".owlbear/scratch/dependency-maps" / f"{run_id}-{attempt}"
    destination.mkdir(parents=True, exist_ok=True)
    for name in sorted(names):
        artifact = destination / name
        if not (artifact / "dependencies.json").is_file():
            _gh(root, ["run", "download", str(run_id), "--repo", REPOSITORY, "--name", name, "--dir", str(artifact)])
    maps = _read_maps(destination, ("linux",))
    if any((item.head, item.run, item.attempt) != (head, run_id, attempt) for item in maps):
        msg = f"Downloaded dependency provenance differs from successful CI run {run_id} at {head}"
        raise ValueError(msg)
    return maps


def _successful_runs(root: Path, query: str) -> list[dict[str, object]]:
    reply: dict[str, object] = json.loads(
        _gh(root, ["api", f"repos/{REPOSITORY}/actions/workflows/ci.yml/runs?status=success&per_page=100&{query}"])
    )
    runs = reply["workflow_runs"]
    if not isinstance(runs, list):
        msg = f"GitHub returned an invalid successful CI run inventory for {REPOSITORY}"
        raise TypeError(msg)
    return runs


def load(root: Path, target: str, directory: Path | None, required: set[str]) -> list[Evidence]:
    """Resolve validated candidate maps or complete successful CI maps at target ancestors."""
    target = git(root, "rev-parse", "--verify", f"{target}^{{commit}}").strip()
    if directory is not None:
        return _candidate(root, directory, required)
    ancestors = set(git(root, "rev-list", target).splitlines())
    # The target's own runs first: later runs on other branches can push them out of the newest 300.
    for query in (f"head_sha={target}", *(f"page={page}" for page in range(1, 4))):
        runs = _successful_runs(root, query)
        for run in runs:
            if not isinstance(run, dict) or run.get("head_sha") not in ancestors:
                continue
            if not git(root, "ls-tree", str(run["head_sha"]), "--", PRODUCER):
                continue
            maps = _download(root, run, required)
            if _complete(maps, required):
                _validate(root, maps)
                sys.stdout.write(f"CI dependency evidence: head {maps[0].head}, run {maps[0].run}\n")
                return maps
        if query.startswith("page=") and len(runs) < RUN_PAGE_SIZE:
            break
    msg = (
        f"No complete successful CI maps among target {target}'s own runs and the last 300 runs at its ancestors; "
        f"required {required}"
    )
    raise RuntimeError(msg)
