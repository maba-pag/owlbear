"""Keep the seconds each test file takes, which the Python shards are packed by; CI runs it, never a person.

``snapshot WEEK MATCHED``
    Scope, from the run times it restored from the Actions cache into ``.ci-durations/``: prints ``value=`` with them as
    one JSON line, ``{}`` when it restored none, and ``current=true`` when they are this week's (``WEEK`` is this
    week's cache key, ``MATCHED`` the key restored). Every shard of the run gets that one copy.
``check FILE``
    A shard, on the copy it got: fails unless it maps test file paths to seconds. The shard's input fingerprint covers
    the copy, so a pass under one split never lets a shard skip under another.
``refresh RESULTS``
    Main's CI, once a week after every shard passed: averages ``$DURATIONS``, the copy the run was split by, with the
    seconds each file took in the ``test-results-python-shard-*`` artifacts under ``RESULTS`` (each shard's latest
    attempt) and writes the result to ``.ci-durations/durations.json`` for the cache. A file this run didn't measure
    drops out; a new one comes in with its seconds.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHED = ".ci-durations/durations.json"
ARTIFACT = re.compile(r"test-results-python-shard-(\d+)-attempt-(\d+)")
# pytest writes each case's dotted classname and its seconds as plain attributes; nothing else of the XML is read.
TESTCASE = re.compile(r"<testcase\b[^>]*?\sclassname=\"([^\"]*)\"[^>]*?\stime=\"([0-9.]+)\"")


def load(text: str) -> dict[str, float]:
    """Return the run times ``text`` holds; raise ValueError unless it maps test file paths to seconds."""
    found = json.loads(text)
    if not isinstance(found, dict) or not all(
        isinstance(path, str) and type(seconds) in (int, float) and seconds >= 0 for path, seconds in found.items()
    ):
        msg = "run times must be a JSON object of test file paths to seconds"
        raise ValueError(msg)
    return found


def dump(found: dict[str, float]) -> str:
    """Return run times as one JSON line, sorted by path."""
    return json.dumps(dict(sorted(found.items())), separators=(",", ":"))


def file_of(classname: str, root: Path = ROOT) -> str | None:
    """Return the repository path of the test file a JUnit classname names, or None when no such file exists."""
    parts = classname.split(".")
    for end in range(len(parts), 0, -1):
        path = "/".join(parts[:end]) + ".py"
        if (root / path).is_file():
            return path
    return None


def latest_reports(results: Path) -> dict[int, Path]:
    """Return each shard's JUnit report from its latest attempt's artifact under ``results``."""
    latest: dict[int, tuple[int, Path]] = {}
    for path in sorted(results.rglob("*.xml")):
        match = next((m for part in path.parts if (m := ARTIFACT.fullmatch(part))), None)
        if match is None:
            continue
        shard, attempt = int(match[1]), int(match[2])
        if shard not in latest or attempt > latest[shard][0]:
            latest[shard] = (attempt, path)
    return {shard: path for shard, (_, path) in sorted(latest.items())}


def run_seconds(reports: list[Path], root: Path = ROOT) -> dict[str, float]:
    """Return the seconds each test file took over the given reports."""
    seconds: dict[str, float] = defaultdict(float)
    for report in reports:
        for classname, time in TESTCASE.findall(report.read_text(encoding="utf-8")):
            path = file_of(classname, root)
            if path is not None:
                seconds[path] += float(time)
    return seconds


def refreshed(previous: dict[str, float], measured: dict[str, float]) -> dict[str, float]:
    """Return each measured file's seconds averaged with its previous ones, rounded to tenths."""
    return {
        path: round((previous[path] + seconds) / 2 if path in previous else seconds, 1)
        for path, seconds in sorted(measured.items())
    }


def main(arguments: list[str], root: Path = ROOT) -> int:
    """Run one command of the module docstring; return its exit code."""
    match arguments:
        case ["snapshot", week, matched]:
            cached = root / CACHED
            found = load(cached.read_text(encoding="utf-8")) if cached.is_file() else {}
            print(f"value={dump(found)}")
            print(f"current={'true' if cached.is_file() and matched == week else 'false'}")
        case ["check", file]:
            load(Path(file).read_text(encoding="utf-8"))
        case ["refresh", results]:
            reports = latest_reports(Path(results))
            shards = int(os.environ["CI_SHARDS"])
            if set(reports) != set(range(1, shards + 1)):
                print(f"need the latest report of each of {shards} shards, found {sorted(reports)}", file=sys.stderr)
                return 1
            found = refreshed(load(os.environ["DURATIONS"]), run_seconds(list(reports.values()), root))
            if not found:
                print("no test run times found", file=sys.stderr)
                return 1
            (root / CACHED).parent.mkdir(parents=True, exist_ok=True)
            (root / CACHED).write_text(dump(found) + "\n", encoding="utf-8")
            print(f"{CACHED}: {len(found)} files, {sum(found.values()):.0f} s")
        case _:
            print(__doc__, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
