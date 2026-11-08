"""Select local task checks from complete CI observations and current consumers."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING, cast

from testmon.process_code import Module, bytes_to_string_and_fsha, match_fingerprint

from owlbear_tools import task_scope
from owlbear_tools.test_consumers import _Consumers, changed_symbols
from owlbear_tools.test_dependencies import (
    REPOSITORY,
    SUITES,
    Evidence,
    git,
    historical_inputs,
    inputs,
    node_path,
    read_evidence,
    relative,
    run_git,
)
from owlbear_tools.test_dependencies import (
    is_test_module as _is_test,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_tools.task_scope import Context

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


def _load(root: Path, target: str, directory: Path | None, required: set[str]) -> list[Evidence]:
    target = git(root, "rev-parse", "--verify", f"{target}^{{commit}}").strip()
    if directory is not None:
        return _candidate(root, directory, required)
    ancestors = set(git(root, "rev-list", target).splitlines())
    for page in range(1, 4):
        reply: dict[str, object] = json.loads(
            _gh(
                root,
                ["api", f"repos/{REPOSITORY}/actions/workflows/ci.yml/runs?status=success&per_page=100&page={page}"],
            )
        )
        runs = reply["workflow_runs"]
        if not isinstance(runs, list):
            msg = f"GitHub returned an invalid successful CI run inventory for {REPOSITORY}"
            raise TypeError(msg)
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
        if len(runs) < RUN_PAGE_SIZE:
            break
    msg = f"No complete successful CI maps among the last 300 runs at ancestors of target {target}; required {required}"
    raise RuntimeError(msg)


def _module(source: str | None) -> Module | None:
    if source is None:
        return None
    ast.parse(source)  # Native testmon tolerates syntax errors; task evidence must not.
    return Module(source_code=source)


def _revision(root: Path, reference: str, paths: set[str]) -> dict[str, Module | None]:
    tracked = set(git(root, "ls-tree", "-rz", "--name-only", reference).split("\0")) - {""}
    return {
        path: _module(bytes_to_string_and_fsha(git(root, "show", f"{reference}:{path}").encode())[0])
        if path in tracked
        else None
        for path in paths
    }


def _kept_paths(root: Path, span: str, target: str) -> set[str]:
    endpoints = span.split("..")
    if len(endpoints) != task_scope.SPAN_ENDPOINTS or not all(endpoints):
        msg = f"Invalid kept dependency span {span!r} in {root}; expected OLD..NEW"
        raise ValueError(msg)
    return task_scope.between(
        lambda arguments: run_git(root, arguments),
        lambda arguments: set(git(root, *arguments).split("\0")) - {""},
        endpoints[0],
        endpoints[1],
        target,
    )


def _unobserved(before: Module | None, current: Module | None, observed: set[int]) -> bool:
    old = before.checksums if before is not None else []
    new = current.checksums if current is not None else []
    for kind, start, end, after, last in SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
        if kind != "equal" and (set(old[start:end]) - observed or (start == end and after != last)):
            return True
    return False


def _suites(paths: set[str]) -> set[str]:
    required = {"python"}
    if any(path.startswith("serve/delivery-next/") for path in paths):
        required.add("delivery-next-browser")
    if any(path.startswith(("serve/browser/", "serve/browser-mcp/")) for path in paths):
        required.add("python-browser")
    return required


@dataclass
class _Selection:
    root: Path
    paths: Sequence[str]
    consumers: _Consumers
    maps: list[Evidence]
    current_hashes: dict[str, str]

    def __post_init__(self) -> None:
        self.recorded = self.maps[0].inputs
        self.rows = [
            row for item in self.maps for row in item.observations if node_path(row.test) in self.consumers.tests
        ]
        self.reasons: dict[str, set[str]] = defaultdict(set)

    def add(self, node: str, reason: str) -> None:
        module = node_path(node)
        if not (self.root / module).is_file():
            return  # Historical consumers of a deleted source survive; deleted tests are not executable.
        if not reason.startswith("caller-supplied"):
            node = node.split("[", 1)[0]
            if self.current_hashes.get(module) != self.recorded.get(module):
                node = module
        self.reasons[node].add(reason)

    def fingerprints(self, touched: set[str], callers: set[str], base: str, after: str | None = None) -> None:
        before = _revision(self.root, base, touched)
        current = {path: _module(self.consumers.texts.get(path)) for path in touched | callers}
        original = _revision(self.root, after, touched) if after is not None else current
        label = f"kept span {base}..{after}" if after is not None else "task-before/current"
        for row in self.rows:
            if row.source in touched and any(
                module is None or not match_fingerprint(module, row.blocks)
                for module in (before[row.source], original[row.source], current[row.source])
            ):
                self.add(row.test, f"native footprint: {label} {row.source}")
            elif (
                row.source in callers
                and self.current_hashes.get(row.source) != self.recorded.get(row.source)
                and (current[row.source] is None or not match_fingerprint(current[row.source], row.blocks))
            ):
                self.add(row.test, f"stale current production caller: {row.source}")
        for source in touched:
            self.supplements(source, before[source], original[source])

    def supplements(self, source: str, before: Module | None, current: Module | None) -> None:
        observed = {block for row in self.rows if row.source == source for block in row.blocks}
        relevant_callers = self.consumers.callers({source})
        relevant_tests = self.consumers.tests_for(relevant_callers)
        relevant_tests.update({source} & self.consumers.tests)
        footprint_tests = {node_path(row.test) for row in self.rows if row.source in relevant_callers}
        for node in {node for item in self.maps for node in item.skipped}:
            if node_path(node) in relevant_tests | footprint_tests:
                self.add(node, f"recorded platform/skip consumer: {source}")
        for node in self.consumers.platform_nodes({*relevant_callers, *relevant_tests, *footprint_tests}):
            self.add(node, f"current platform branch consumer: {source}")
        symbols = changed_symbols(before, current)
        affected = self.consumers.affected(source, symbols or set(self.consumers.definitions.get(source, {})))
        fixtures = set(affected) & self.consumers.fixtures.keys()
        for node in self.consumers.platform_nodes(fixtures, affected):
            self.add(node, f"current platform fixture consumer: {source}")
        if _unobserved(before, current, observed):
            self.named_consumers(source, affected)

    def named_consumers(self, source: str, affected: dict[str, set[str]]) -> None:
        historical = _revision(self.root, self.maps[0].head, set(affected) - self.consumers.tests)
        hashes = {
            path: (
                self.consumers.block_hashes(path, symbols)
                | self.consumers.block_hashes(path, symbols, historical.get(path))
            )
            for path, symbols in affected.items()
            if path not in self.consumers.tests
        }
        mapped: set[str] = set()
        for row in self.rows:
            if set(row.blocks) & hashes.get(row.source, set()):
                self.add(row.test, f"unobserved block via current production caller: {source}")
                mapped.add(row.test)
        direct = self.consumers.test_nodes(affected)
        for node in direct:
            if not any(test == node or test.startswith((f"{node}[", f"{node}::")) for test in mapped):
                self.add(node, f"unobserved block current named consumer: {source}")
        if not mapped and not direct:
            msg = f"Unobserved task blocks in {self.root}/{source} have no resolved current consumers"
            raise RuntimeError(msg)

    def reconcile(self) -> None:
        python = {path for path in self.paths if path.endswith(".py")}
        relevant = self.consumers.tests_for(self.consumers.callers(python))
        relevant.update(node_path(node) for node in self.reasons)
        for test in relevant & self.consumers.tests:
            if self.current_hashes[test] != self.recorded.get(test):
                self.add(test, "current test differs from map")
        helpers = {
            path
            for path in self.current_hashes.keys() | self.recorded.keys()
            if self.current_hashes.get(path) != self.recorded.get(path)
            and (path == "conftest.py" or "/tests/" in path or path.startswith("tests/"))
            and not _is_test(path)
        }
        for helper in helpers:
            self.helper(helper, None if helper in self.paths else relevant)
        for config in self.recorded:
            if (
                config.endswith("pyproject.toml") or config in {"uv.lock", ".python-version"}
            ) and self.current_hashes.get(config) != self.recorded[config]:
                msg = f"Dependency configuration {config} differs from map {self.maps[0].head}; collect current CI maps"
                raise RuntimeError(msg)

    def helper(self, helper: str, relevant: set[str] | None = None) -> None:
        if not helper.endswith(".py"):
            for node in self.consumers.outside_nodes({helper}, self.consumers.tests, required=helper in self.paths):
                if relevant is None or node_path(node) in relevant:
                    self.add(node, f"current test-data reader: {helper}")
            return
        associated = {test for test in self.consumers.tests_for({helper}) if relevant is None or test in relevant}
        if (
            relevant is not None
            and not associated
            and not any(row.source == helper and node_path(row.test) in relevant for row in self.rows)
        ):
            return
        module = _module(self.consumers.texts.get(helper))
        observed = {block for row in self.rows if row.source == helper for block in row.blocks}
        historical = (
            _module(git(self.root, "show", f"{self.maps[0].head}:{helper}")) if helper in self.recorded else None
        )
        if Path(helper).name != "conftest.py" or _unobserved(historical, module, observed):
            for test in associated:
                self.add(test, f"current helper/fixture: {helper}")
        for row in self.rows:
            if (
                row.source == helper
                and (relevant is None or node_path(row.test) in relevant)
                and (module is None or not match_fingerprint(module, row.blocks))
            ):
                self.add(row.test, f"current helper footprint: {helper}")
        unresolved = _unobserved(historical, module, observed) or not any(row.source == helper for row in self.rows)
        if not associated and helper in self.paths and unresolved:
            msg = f"Unresolved current fixture/helper consumers in {self.root}: {helper}"
            raise RuntimeError(msg)


@dataclass(frozen=True)
class RequiredScope:
    """Full task paths and explicit/invariant/configuration selectors, separate from router candidates."""

    paths: Sequence[str]
    tests: Sequence[str]


def select(
    root: Path,
    paths: Sequence[str],
    context: Context,
    forced: Sequence[str],
    scope: RequiredScope,
) -> list[str]:
    """Return one union of current pytest node/module selectors, never a bootstrap full suite."""
    root = root.resolve()
    all_paths = scope.paths
    for path in {*paths, *all_paths}:
        if not relative(path):
            msg = f"Invalid task dependency path in {root}: {path!r}"
            raise ValueError(msg)
    files = set(git(root, "ls-files", "-co", "--exclude-standard", "-z").split("\0")) - {""}
    files = {name for name in files if (root / name).is_file()}
    if any(not (root / name).resolve().is_relative_to(root) for name in files):
        msg = f"A tracked or current input resolves outside dependency checkout {root}"
        raise ValueError(msg)
    touched = {path for path in paths if path.endswith(".py")}
    consumers = _Consumers(root, files | touched)
    callers = consumers.callers(touched)
    importing = consumers.tests_for(callers)
    suites = _suites({*all_paths, *importing, *(node_path(node) for node in forced)})
    selection = _Selection(
        root, all_paths, consumers, _load(root, context.target, context.maps_dir, suites), inputs(root, files)
    )
    for node in scope.tests:
        selection.add(node, "caller-supplied invariant/source-reading/subprocess/neighbor")
    for node in consumers.outside_nodes(set(all_paths), {node_path(node) for node in forced}):
        selection.add(node, "current named page/source-reading/subprocess consumer")
    selection.fingerprints(touched, callers, context.base)
    for span in context.kept_spans:
        kept = touched & _kept_paths(root, span, context.target)
        selection.fingerprints(kept, consumers.callers(kept), *span.split(".."))
    selection.reconcile()
    if not selection.reasons:
        msg = f"No executable tests resolved for task paths {list(paths)} in {root}; refusing empty check"
        raise RuntimeError(msg)
    for node, why in sorted(selection.reasons.items()):
        sys.stdout.write(f"Selected {node}: {'; '.join(sorted(why))}\n")
    return sorted(selection.reasons)
