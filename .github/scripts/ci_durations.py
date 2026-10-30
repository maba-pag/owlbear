"""Refresh ``.github/ci-durations.json``, the seconds each test file takes, which the Python shards are packed by.

Run it by hand from the repository root with one folder per passing CI run on main, each holding that run's
``test-results-python-shard-*`` artifacts::

    gh run download <run-id> -p 'test-results-python-shard-*' -D /tmp/durations/<run-id>
    python3 .github/scripts/ci_durations.py /tmp/durations/*

Only each shard's latest attempt counts. A file's seconds are the sum of its test cases in a run, averaged over the
runs that have it. Commit the result; a stale file costs the shards balance, never tests.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / ".github/ci-durations.json"
ARTIFACT = re.compile(r"test-results-python-shard-(\d+)-attempt-(\d+)")
# pytest writes each case's dotted classname and its seconds as plain attributes; nothing else of the XML is read.
TESTCASE = re.compile(r"<testcase\b[^>]*?\sclassname=\"([^\"]*)\"[^>]*?\stime=\"([0-9.]+)\"")


def file_of(classname: str, root: Path = ROOT) -> str | None:
    """Return the repository path of the test file a JUnit classname names, or None when no such file exists."""
    parts = classname.split(".")
    for end in range(len(parts), 0, -1):
        path = "/".join(parts[:end]) + ".py"
        if (root / path).is_file():
            return path
    return None


def junit_files(run: Path) -> list[Path]:
    """Return a run's JUnit files, only the latest attempt of each shard where artifacts name them."""
    latest: dict[str, tuple[int, Path]] = {}
    plain: list[Path] = []
    for path in sorted(run.rglob("*.xml")):
        match = next((m for part in path.parts if (m := ARTIFACT.fullmatch(part))), None)
        if match is None:
            plain.append(path)
        elif match[1] not in latest or int(match[2]) > latest[match[1]][0]:
            latest[match[1]] = (int(match[2]), path)
    return plain + [path for _, path in latest.values()]


def run_seconds(run: Path, root: Path = ROOT) -> dict[str, float]:
    """Return the seconds each test file took in one run."""
    seconds: dict[str, float] = defaultdict(float)
    for junit in junit_files(run):
        for classname, time in TESTCASE.findall(junit.read_text(encoding="utf-8")):
            path = file_of(classname, root)
            if path is not None:
                seconds[path] += float(time)
    return seconds


def durations(runs: list[Path], root: Path = ROOT) -> dict[str, float]:
    """Return each test file's seconds, averaged over the runs that have it, rounded to tenths."""
    found: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        for path, seconds in run_seconds(run, root).items():
            found[path].append(seconds)
    return {path: round(sum(values) / len(values), 1) for path, values in sorted(found.items())}


def main(arguments: list[str]) -> int:
    """Write the durations file from the given run folders."""
    runs = [Path(argument) for argument in arguments]
    if not runs or not all(run.is_dir() for run in runs):
        print(__doc__, file=sys.stderr)
        return 2
    found = durations(runs)
    if not found:
        print("no test durations found", file=sys.stderr)
        return 1
    TARGET.write_text(json.dumps(found, indent=2) + "\n", encoding="utf-8")
    print(f"{TARGET.relative_to(ROOT)}: {len(found)} files, {sum(found.values()):.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
