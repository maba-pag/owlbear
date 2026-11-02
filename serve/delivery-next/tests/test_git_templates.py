"""The session's Git templates, which tests copy byte for byte (#917)."""

import subprocess
from pathlib import Path


def test_a_copied_template_repository_starts_no_background_maintenance(change_repo: Path, shared_repo) -> None:
    """A commit or a push starts Git's maintenance in the background unless the repository turns it off, and a copy
    made meanwhile catches its lock half-gone. Every repository the templates copy has it off in its own config."""
    clone, remote = shared_repo
    for repo in (change_repo / ".git", clone / ".git", remote):
        found = [
            subprocess.run(  # noqa: S603
                ["git", "config", "--file", str(repo / "config"), "--get", key],  # noqa: S607
                capture_output=True,
                text=True,
                check=False,  # a missing key fails the assertion, which names the repository
            ).stdout.strip()
            for key in ("maintenance.auto", "gc.auto")
        ]
        assert found == ["false", "0"], repo
