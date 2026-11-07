"""CI records reusable test-to-code influence without shortening its test suites."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import pytest
from testmon.db import DATA_VERSION
from testmon.process_code import blob_to_checksums

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

FORMAT = 1
REPOSITORY = "maba-pag/owlbear"
OUTPUT = "OWLBEAR_DEPENDENCIES_OUT"
STATE: pytest.StashKey[Collection] = pytest.StashKey()
SUITES = {"python": 4, "delivery-next-browser": 2, "python-browser": 1}
PACKAGE_TEST_DEPTH = 4
SHA1_LENGTH = 40
CONFIGS = {
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "conftest.py",
    ".github/workflows/python.yml",
    ".github/workflows/python-browser.yml",
    ".github/scripts/ci_shard.py",
    ".github/scripts/flaky_issues.py",
    ".github/scripts/check_uv_version.py",
}


def git(root: Path, *arguments: str) -> str:
    """A repository query whose failure retains the command, directory and Git's details."""
    executable = shutil.which("git")
    if executable is None:
        msg = "Git is unavailable while reading test dependency evidence"
        raise RuntimeError(msg)
    result = subprocess.run(  # noqa: S603 - fixed executable, no shell.
        [executable, *arguments], cwd=root, text=True, capture_output=True, check=False
    )
    if result.returncode:
        msg = f"Git {' '.join(arguments)} in {root} exited {result.returncode}: {result.stderr.strip()}"
        raise RuntimeError(msg)
    return result.stdout


def relative(value: str) -> bool:
    """A nonempty repository path with no parent, absolute or platform-dependent spelling."""
    path = PurePosixPath(value)
    return bool(value) and bool(path.parts) and not path.is_absolute() and ".." not in path.parts and "\\" not in value


def node_path(node: str) -> str:
    """The repository test file of a node, never an option or an outside executable."""
    value = node.split("::", 1)[0]
    path = PurePosixPath(value)
    parts = path.parts
    under_tests = parts and parts[0] == "tests"
    under_package = len(parts) >= PACKAGE_TEST_DEPTH and parts[0] == "serve" and parts[2] == "tests"
    if (
        not relative(value)
        or not (under_tests or under_package)
        or path.suffix != ".py"
        or any(character in node for character in "\0\r\n")
        or any(not part or part.startswith(("-", "/", ".")) for part in node.split("::")[1:])
    ):
        msg = f"Invalid dependency test identity: {node!r} is not a repository test"
        raise ValueError(msg)
    return value


def snapshot(path: Path) -> str:
    """The bytes the dependency evidence describes, independent of timestamps."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_test_module(path: str) -> bool:
    """Recognize current test modules without collecting similarly named production helpers."""
    return (
        (path.startswith("tests/") or "/tests/" in path)
        and Path(path).name.startswith("test_")
        and path.endswith(".py")
    )


def input_names(tracked: set[str]) -> set[str]:
    """Tracked source, test data, fixture and producer/configuration inputs."""
    return {
        path
        for path in tracked
        if path in CONFIGS
        or (path.startswith(("serve/", "tests/", ".github/scripts/")) and path.endswith((".py", "/pyproject.toml")))
        or "/tests/" in path
        or path.startswith("tests/")
    }


def inputs(root: Path, tracked: set[str]) -> dict[str, str]:
    """Source, test, fixture and configuration inputs at the recorded checkout."""
    found: dict[str, str] = {}
    for name in sorted(input_names(tracked)):
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            msg = f"Dependency input {name} resolves outside {root}"
            raise ValueError(msg)
        found[name] = snapshot(path)
    return found


@dataclass(frozen=True)
class Observation:
    """One testmon-native test-to-file footprint."""

    test: str
    source: str
    blocks: tuple[int, ...]


@dataclass(frozen=True)
class Evidence:
    """Validated historical evidence, separate from the current executable test inventory."""

    head: str
    run: int
    attempt: int
    suite: str
    shard: int
    shards: int
    inputs: dict[str, str]
    nodes: frozenset[str]
    skipped: frozenset[str]
    observations: tuple[Observation, ...]


def historical_inputs(root: Path, head: str) -> dict[str, str]:
    """Hash regular tracked inputs from Git objects, without checking out the map's revision."""
    entries: dict[str, str] = {}
    for entry in git(root, "ls-tree", "-rz", "--full-tree", head).split("\0"):
        if entry:
            metadata, name = entry.split("\t", 1)
            mode, kind, oid = metadata.split()
            if kind == "blob" and mode in {"100644", "100755"}:
                entries[name] = oid
    names = sorted(input_names(set(entries)))
    executable = shutil.which("git")
    if executable is None:
        msg = "Git is unavailable while checking historical dependency inputs"
        raise RuntimeError(msg)
    result = subprocess.run(  # noqa: S603 - fixed executable and Git object IDs.
        [executable, "cat-file", "--batch"],
        cwd=root,
        input="".join(f"{entries[name]}\n" for name in names).encode(),
        capture_output=True,
        check=True,
    )
    found: dict[str, str] = {}
    offset = 0
    for name in names:
        end = result.stdout.index(b"\n", offset)
        size = int(result.stdout[offset:end].split()[2])
        offset = end + 1
        found[name] = hashlib.sha256(result.stdout[offset : offset + size]).hexdigest()
        offset += size + 1
    return found


def _strings(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        msg = f"Expected a string list in dependency evidence, got {value!r}"
        raise ValueError(msg)
    return value


def _integer(value: object) -> int:
    if type(value) is not int:
        msg = f"Expected an integer in dependency evidence, got {value!r}"
        raise ValueError(msg)
    return value


def _document(path: Path, platforms: Sequence[str]) -> dict[str, object]:
    document: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        msg = f"Dependency evidence {path} is not a JSON object"
        raise TypeError(msg)
    if (
        document.get("format") != FORMAT
        or document.get("testmon") != version("pytest-testmon")
        or document.get("python") != f"{sys.version_info.major}.{sys.version_info.minor}"
        or document.get("repo") != REPOSITORY
        or document.get("platform") not in platforms
        or document.get("complete") is not True
        or document.get("failed") != []
    ):
        msg = f"Incompatible or unsuccessful dependency evidence in {path}"
        raise ValueError(msg)
    return document


def _hashes(document: dict[str, object], path: Path) -> dict[str, str]:
    hashes = document.get("inputs")
    if not isinstance(hashes, dict) or any(
        not isinstance(name, str)
        or not relative(name)
        or not isinstance(digest, str)
        or len(digest) != hashlib.sha256().digest_size * 2
        or any(character not in "0123456789abcdef" for character in digest)
        for name, digest in hashes.items()
    ):
        msg = f"Invalid dependency input hashes in {path}"
        raise ValueError(msg)
    return hashes


def _nodes(document: dict[str, object], hashes: dict[str, str], path: Path) -> tuple[frozenset[str], frozenset[str]]:
    nodes = frozenset(_strings(document.get("nodes")))
    skipped = frozenset(_strings(document.get("skipped")))
    completed = frozenset(_strings(document.get("completed")))
    for node in nodes | skipped | completed:
        if node_path(node) not in hashes:
            msg = f"Dependency test {node!r} has no historical input in {path}"
            raise ValueError(msg)
    if completed != nodes or not skipped <= nodes:
        msg = f"Unfinished dependency inventory in {path}"
        raise ValueError(msg)
    return nodes, skipped


def _observations(
    document: dict[str, object], nodes: frozenset[str], hashes: dict[str, str], path: Path
) -> tuple[Observation, ...]:
    observations: list[Observation] = []
    rows = document.get("observations")
    if not isinstance(rows, list):
        msg = f"Missing native dependency rows in {path}"
        raise TypeError(msg)
    for row in rows:
        if not isinstance(row, dict):
            msg = f"Invalid dependency row in {path}: {row!r}"
            raise TypeError(msg)
        test, source, blocks = row.get("test"), row.get("source"), row.get("blocks")
        if (
            not isinstance(test, str)
            or test not in nodes
            or not isinstance(source, str)
            or not relative(source)
            or source not in hashes
            or not source.endswith(".py")
            or not isinstance(blocks, list)
            or any(type(block) is not int or not -(2**31) <= block < 2**31 for block in blocks)
        ):
            msg = f"Invalid dependency footprint in {path}: {row!r}"
            raise ValueError(msg)
        observations.append(Observation(test, source, tuple(blocks)))
    return tuple(observations)


def read_evidence(path: Path, platforms: Sequence[str] = ("linux",)) -> Evidence:
    """Reject malformed paths, nodes, incomplete observations and incompatible native fingerprints."""
    document = _document(path, platforms)
    hashes = _hashes(document, path)
    nodes, skipped = _nodes(document, hashes, path)
    observations = _observations(document, nodes, hashes, path)
    observed = {row.test for row in observations if row.blocks}
    if nodes - skipped - observed:
        msg = f"Missing observations in {path}: {sorted(nodes - skipped - observed)}"
        raise ValueError(msg)
    head, suite = document.get("head"), document.get("suite")
    if not isinstance(head, str) or len(head) != SHA1_LENGTH or any(c not in "0123456789abcdef" for c in head):
        msg = f"Invalid dependency checkout head in {path}: {head!r}"
        raise ValueError(msg)
    if not isinstance(suite, str) or suite not in SUITES:
        msg = f"Unknown dependency suite in {path}: {suite!r}"
        raise ValueError(msg)
    return Evidence(
        head,
        _integer(document.get("run")),
        _integer(document.get("attempt")),
        suite,
        _integer(document.get("shard")),
        _integer(document.get("shards")),
        hashes,
        nodes,
        skipped,
        observations,
    )


@dataclass
class Collection:
    """The controller's current test inventory and outcomes, not a cache of passing results."""

    root: Path
    output: Path
    head: str
    database: Path
    provenance: dict[str, str]
    initial_inputs: dict[str, str]
    collected: set[str] = field(default_factory=set)
    completed: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)
    failed: set[str] = field(default_factory=set)


def export(collection: Collection) -> None:
    """Export flushed native fingerprints and current inputs as one portable shard."""
    root = collection.root
    tracked = set(git(root, "ls-files", "-z").split("\0")) - {""}
    observations: list[dict[str, object]] = []
    database = collection.database
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        actual = connection.execute("PRAGMA user_version").fetchone()[0]
        if actual != DATA_VERSION:
            msg = f"Dependency database {database} has format {actual}, expected {DATA_VERSION}"
            raise ValueError(msg)
        rows = connection.execute(
            "SELECT t.test_name, f.filename, f.method_checksums FROM test_execution t "
            "JOIN test_execution_file_fp d ON d.test_execution_id=t.id "
            "JOIN file_fp f ON f.id=d.fingerprint_id"
        )
        for node, source, fingerprint in rows:
            if source not in collection.initial_inputs or not source.endswith(".py"):
                continue
            if node not in collection.collected:
                continue
            if node_path(node) not in tracked:
                msg = f"Dependency node {node!r} is not tracked in {collection.head}"
                raise ValueError(msg)
            observations.append({"test": node, "source": source, "blocks": blob_to_checksums(fingerprint)})
    missing = collection.collected - collection.completed
    if missing:
        msg = f"Dependency collection did not finish these tests: {', '.join(sorted(missing))}"
        raise ValueError(msg)
    if collection.initial_inputs != inputs(root, tracked):
        msg = f"Dependency inputs in {root} changed during collection; refusing stale snapshots"
        raise ValueError(msg)
    provenance = collection.provenance
    document = {
        "format": FORMAT,
        "testmon": version("pytest-testmon"),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "platform": sys.platform,
        "complete": True,
        "repo": provenance["GITHUB_REPOSITORY"],
        "head": collection.head,
        "run": int(provenance["GITHUB_RUN_ID"]),
        "attempt": int(provenance["GITHUB_RUN_ATTEMPT"]),
        "suite": provenance["OWLBEAR_DEPENDENCIES_SUITE"],
        "shard": int(provenance["OWLBEAR_DEPENDENCIES_SHARD"]),
        "shards": int(provenance["OWLBEAR_DEPENDENCIES_SHARDS"]),
        "inputs": collection.initial_inputs,
        "nodes": sorted(collection.collected),
        "completed": sorted(collection.completed),
        "skipped": sorted(collection.skipped),
        "failed": sorted(collection.failed),
        "observations": observations,
    }
    collection.output.parent.mkdir(parents=True, exist_ok=True)
    collection.output.write_text(
        json.dumps(document, ensure_ascii=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    read_evidence(collection.output, (sys.platform,))
    print(f"Dependency evidence: {len(collection.collected)} tests, {len(observations)} footprints")  # noqa: T201


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Bind the controller to its original checkout before tests can change cwd or environment."""
    if hasattr(config, "workerinput"):
        return
    output = os.environ.get(OUTPUT)
    if not output:
        msg = f"The dependency collector requires {OUTPUT}"
        raise pytest.UsageError(msg)
    root = config.rootpath
    database = Path(os.environ["TESTMON_DATAFILE"])
    if not database.is_absolute():
        database = root / database
    if database.exists():
        msg = f"Dependency collection requires a fresh TESTMON_DATAFILE, already exists: {database}"
        raise pytest.UsageError(msg)
    provenance = {
        key: os.environ[key]
        for key in (
            "GITHUB_REPOSITORY",
            "GITHUB_RUN_ID",
            "GITHUB_RUN_ATTEMPT",
            "OWLBEAR_DEPENDENCIES_SUITE",
            "OWLBEAR_DEPENDENCIES_SHARD",
            "OWLBEAR_DEPENDENCIES_SHARDS",
        )
    }
    tracked = set(git(root, "ls-files", "-z").split("\0")) - {""}
    destination = Path(output)
    if not destination.is_absolute():
        destination = root / destination
    config.stash[STATE] = Collection(
        root, destination, git(root, "rev-parse", "HEAD").strip(), database, provenance, inputs(root, tracked)
    )


def pytest_collection_finish(session: pytest.Session) -> None:
    """The ordinary non-xdist selected inventory."""
    if STATE in session.config.stash:
        session.config.stash[STATE].collected.update(item.nodeid for item in session.items)


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_node_collection_finished(node: object, ids: list[str]) -> None:
    """The controller receives the same selected inventory from each xdist worker."""
    config = getattr(node, "config", None)
    if config is None:
        msg = "An xdist dependency collection node has no configuration"
        raise RuntimeError(msg)
    if STATE in config.stash:
        config.stash[STATE].collected.update(ids)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item: pytest.Item) -> Generator[None, object, object]:
    """Retain the local item only when running without xdist."""
    result = yield
    if STATE in item.config.stash:
        item.config.stash[STATE].completed.add(item.nodeid)
    return result


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Reports arrive on the controller too; collected data is kept by the active plugin instance."""
    if _controller is None:
        return
    if report.when == "setup":
        _controller.failed.discard(report.nodeid)
    if report.when == "teardown":
        _controller.completed.add(report.nodeid)
    if report.skipped:
        _controller.skipped.add(report.nodeid)
    if report.failed:
        _controller.failed.add(report.nodeid)


_controller: Collection | None = None
_collection_skips: set[str] = set()


def pytest_collectreport(report: pytest.CollectReport) -> None:
    """Retain module-level skips, which have no runtest reports."""
    if report.skipped:
        _collection_skips.add(report.nodeid)


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node: object) -> None:
    """Bring worker collection skips back to the controller."""
    config, output = getattr(node, "config", None), getattr(node, "workeroutput", {})
    if config is not None and STATE in config.stash:
        _collection_skips.update(output.get("dependency_skips", []))


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> Generator[None, object, object]:
    """Export after every other sessionfinish hook has flushed its worker batches."""
    if hasattr(session.config, "workeroutput"):
        session.config.workeroutput["dependency_skips"] = sorted(_collection_skips)
    result = yield
    if STATE in session.config.stash and exitstatus == 0 and not session.testsfailed:
        collection = session.config.stash[STATE]
        collection.collected.update(_collection_skips)
        collection.completed.update(_collection_skips)
        collection.skipped.update(_collection_skips)
        export(session.config.stash[STATE])
    return result


@pytest.hookimpl(trylast=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Bind reports to this controller; worker reports are forwarded by xdist."""
    global _controller  # noqa: PLW0603 - pytest's logreport hook carries no config.
    _collection_skips.clear()
    _controller = session.config.stash.get(STATE, None)
