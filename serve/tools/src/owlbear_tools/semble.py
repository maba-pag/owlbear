"""Launch the Semble CLI without making it an OwlBear dependency."""

from __future__ import annotations

import subprocess
import sys


def main(arguments: list[str] | None = None) -> int:
    """Delegate to the current Semble release through uv's cached tool runner."""
    command = ["uv", "tool", "run", "--from", "semble", "semble", *(arguments or sys.argv[1:])]
    # The uv/Semble entry point is fixed; CLI operands are intentionally forwarded without shell interpretation.
    return subprocess.run(command, check=False).returncode  # noqa: S603 - intentional Semble CLI argument forwarding
