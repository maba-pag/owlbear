"""Check that generated decisions views are unedited: the sha256 on each last line matches everything above it.

Stdlib only, so pull-request CI checks the view without owlbear-data's token (TD-436); the decisions-view workflow,
on pushes to main and daily, checks the view against owlbear-data itself.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

HASH_LINE = re.compile(rb"<!-- decisions-view sha256:([0-9a-f]{64}) -->")
REGENERATE = "the lead chat regenerates it by pull request with `uv run decisions-view <owlbear-data>`"


def problem(data: bytes) -> str:
    """Why *data* is not an unedited view, or "" when it is."""
    body, _, last = data.removesuffix(b"\n").rpartition(b"\n")
    match = HASH_LINE.fullmatch(last)
    if not data.endswith(b"\n") or match is None:
        return "its last line is not the `<!-- decisions-view sha256:... -->` hash comment"
    if hashlib.sha256(body + b"\n").hexdigest().encode() != match[1]:
        return "it was edited by hand: its content does not match the hash on its last line"
    return ""


def main(paths: list[str]) -> int:
    """Exit 1 when any view is edited by hand or lacks its hash."""
    failed = 0
    for name in paths:
        if found := problem(Path(name).read_bytes()):
            sys.stderr.write(f"{name}: {found}; {REGENERATE}\n")
            failed = 1
    return failed


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
