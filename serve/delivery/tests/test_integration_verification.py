from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from owlbear_delivery.integration_verification import (
    INTEGRATION_VERIFICATION_PROFILE_PATH,
    read_target_verification_profile,
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _profile(argv: tuple[str, ...], *, timeout_seconds: int = 30) -> bytes:
    content = {
        "schema_version": 1,
        "pass_environment": ["PATH", "HOME", "TMPDIR"],
        "steps": [
            {
                "step_id": "project-tests",
                "argv": list(argv),
                "cwd": ".",
                "timeout_seconds": timeout_seconds,
            }
        ],
    }
    return (json.dumps(content, indent=2) + "\n").encode()


def _repository(
    tmp_path: Path,
    argv: tuple[str, ...],
    *,
    timeout_seconds: int = 30,
) -> tuple[Path, str, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Verification Test")
    _git(repository, "config", "user.email", "verification@example.invalid")
    profile_path = repository / INTEGRATION_VERIFICATION_PROFILE_PATH
    profile_path.parent.mkdir(parents=True)
    profile_path.write_bytes(_profile(argv, timeout_seconds=timeout_seconds))
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    target_head = _git(repository, "rev-parse", "HEAD")
    _git(repository, "switch", "-c", "change-a")
    (repository / "product.txt").write_text("candidate\n", encoding="utf-8")
    _git(repository, "commit", "-am", "candidate")
    candidate_commit = _git(repository, "rev-parse", "HEAD")
    _git(repository, "update-ref", "refs/owlbear/integration-candidates/change-a", candidate_commit)
    return repository, target_head, candidate_commit


def test_target_profile_resolution_ignores_change_head_profile(tmp_path: Path) -> None:
    repository, target_head, _candidate_commit = _repository(tmp_path, (sys.executable, "-c", "raise SystemExit(0)"))
    profile_path = repository / INTEGRATION_VERIFICATION_PROFILE_PATH
    profile_path.write_bytes(_profile((sys.executable, "-c", "raise SystemExit(3)")))
    _git(repository, "add", INTEGRATION_VERIFICATION_PROFILE_PATH)
    _git(repository, "commit", "-m", "change verification authority")

    resolved = read_target_verification_profile(repository, target_head)

    assert resolved.target_commit == target_head
    assert resolved.profile.steps[0].argv == (sys.executable, "-c", "raise SystemExit(0)")
