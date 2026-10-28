"""Check a project's sources log (`owlbear-data/<project>/sources/overview.md`) against its code.

Every table row needs a source, an `<https://…>` URL, a licence, what was adopted and at least one backticked
"Where Used" path that exists under the code root.

Invocation
----------
    python .owlbear/scripts/check_sources_log.py LOG CODE_ROOT

Exit codes
----------
    0 — every row is well formed
    1 — at least one problem; each is printed
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HEADER = ["| Source | URL | Licence | What | Where Used |", "| --- | --- | --- | --- | --- |"]
_URL = re.compile(r"<https://[^\s<>]+>")
_PATH = re.compile(r"`([^`]+)`")
_DELIMITER = re.compile(r"(?<!\\)\|")


def _table(text: str) -> list[str] | None:
    """Return the table's lines from its header on, or None when it has no header.

    Every non-blank line after the header up to a blank line is a row, with or without a leading pipe, and so is
    any later line that starts with one: no row is skipped.
    """
    lines = [line.strip() for line in text.splitlines()]
    start = next((index for index, line in enumerate(lines) if line.startswith("|")), None)
    if start is None:
        return None
    end = next((index for index in range(start, len(lines)) if not lines[index]), len(lines))
    return lines[start:end] + [line for line in lines[end:] if line.startswith("|")]


def _cells(row: str) -> list[str]:
    """Split a row on every unescaped pipe, whatever its spacing, as Markdown renders it."""
    row = row.removeprefix("|")
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    return [cell.strip() for cell in _DELIMITER.split(row)]


def check_sources_log(text: str, code_root: Path) -> list[str]:
    """Return the problems of a sources log; an empty list means it is well formed."""
    table = _table(text)
    if table is None or table[:2] != HEADER:
        return [f"the table must start with {HEADER[0]!r} and its separator"]
    rows = table[2:]
    if not rows:
        return ["the table has no rows"]
    problems: list[str] = []
    for row in rows:
        cells = _cells(row)
        if len(cells) != len(_cells(HEADER[0])):
            problems.append(f"needs 5 cells: {row}")
            continue
        source, url, licence, what, where = cells
        if not (source and licence and what):
            problems.append(f"source, licence and what must not be empty: {row}")
        if not _URL.fullmatch(url):
            problems.append(f"URL must be written <https://…>: {row}")
        paths = _PATH.findall(where)
        if not paths:
            problems.append(f"Where Used names no backticked path: {row}")
        problems.extend(f"{problem}: {row}" for path in paths if (problem := _path_problem(path, code_root)))
    return problems


def _path_problem(path: str, code_root: Path) -> str | None:
    if Path(path).is_absolute():
        return f"{path} must be relative to the code root"
    root = code_root.resolve()
    if not (root / path).resolve().is_relative_to(root):
        return f"{path} is outside the code root {code_root}"
    if not (root / path).exists():
        return f"{path} does not exist under {code_root}"
    return None


def main(argv: list[str] | None = None) -> int:
    """Check the log named on the command line; print each problem and exit 1 when there is one."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("log", type=Path, help="The sources log, e.g. owlbear-data/owlbear/sources/overview.md")
    parser.add_argument("code_root", type=Path, help="The project's checkout the Where Used paths are relative to")
    args = parser.parse_args(argv)
    text = args.log.read_text(encoding="utf-8")
    problems = check_sources_log(text, args.code_root)
    for problem in problems:
        print(problem)
    if not problems:
        rows = (_table(text) or [])[2:]
        paths = sum(len(_PATH.findall(_cells(row)[-1])) for row in rows)
        print(f"{args.log}: {len(rows)} rows and {paths} Where Used paths are well formed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
