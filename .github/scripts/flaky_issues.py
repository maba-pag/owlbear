"""Find which issues named by flaky marks are open, so CI re-runs only those tests (see owlbear_tools.flaky).

Writes ``OWLBEAR_FLAKY_OPEN_ISSUES`` to ``$GITHUB_ENV`` and a note to the job summary. An issue that is
closed, is a pull request or can't be looked up is left out, so its tests run strict.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

_MARK = re.compile(r"\bflaky\(\s*(?:#[^\n]*\n\s*)*issue\s*=\s*(\d[\d_]*)")
_TIMEOUT_SECONDS = 10


def marked_issues(root: Path) -> list[int]:
    """Issue numbers named by flaky marks in the repository's tracked Python files.

    A match inside a string only adds an issue to look up; the plugin re-runs only tests whose mark names it.
    """
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.py"],  # noqa: S607
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout.decode()
    found: set[int] = set()
    for name in filter(None, listed.split("\0")):
        text = (root / name).read_text(encoding="utf-8", errors="replace")
        found.update(int(number.replace("_", "")) for number in _MARK.findall(text))
    return sorted(found)


def fetch_issue(repository: str, number: int) -> dict[str, object]:
    """One issue from the GitHub API through the gh CLI, read with the job's token."""
    try:
        done = subprocess.run(  # noqa: S603
            ["gh", "api", f"repos/{repository}/issues/{number}"],  # noqa: S607
            capture_output=True,
            check=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(error.stderr.strip() or f"gh exited with {error.returncode}") from error
    return json.loads(done.stdout)


def open_issues(numbers: Iterable[int], fetch: Callable[[int], dict[str, object]]) -> tuple[list[int], list[str]]:
    """The open issues among *numbers*, and a note for each one left out."""
    found: list[int] = []
    notes: list[str] = []
    for number in numbers:
        try:
            issue = fetch(number)
        except Exception as error:  # noqa: BLE001 - any lookup failure leaves the issue's tests strict
            notes.append(f"#{number}: lookup failed ({error}); its tests run strict")
            continue
        if "pull_request" in issue:
            notes.append(f"#{number} is a pull request, not an issue; its tests run strict")
        elif issue.get("state") == "open":
            found.append(number)
        else:
            notes.append(f"#{number} is closed; its tests run strict, and its flaky marks should go")
    return found, notes


def main() -> int:
    """Write the open issues to the job's environment and summary."""
    repository = os.environ["GITHUB_REPOSITORY"]
    numbers = marked_issues(Path.cwd())
    found, notes = open_issues(numbers, lambda number: fetch_issue(repository, number))
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as env:
        env.write(f"OWLBEAR_FLAKY_OPEN_ISSUES={' '.join(map(str, found))}\n")
    lines = [
        (
            f"Flaky marks name issues {', '.join(f'#{n}' for n in numbers) or 'none'}; open: "
            f"{', '.join(f'#{n}' for n in found) or 'none'}."
        ),
        *notes,
    ]
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
        summary.writelines(f"{line}\n\n" for line in lines)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
