"""Prove that uv lock regeneration observes workspace-member changes."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from shutil import which
from typing import NoReturn


def _raise_runtime_error(message: str) -> NoReturn:
    """Raise one named workspace-lock proof failure."""
    raise RuntimeError(message)


def _run_uv(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    uv_executable = which("uv")
    if uv_executable is None:
        _raise_runtime_error("uv is required for workspace-lock proof")
    result = subprocess.run(  # noqa: S603
        [uv_executable, *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        _raise_runtime_error(result.stderr or result.stdout)
    return result


def main() -> int:
    """Run the workspace-member lock regeneration proof."""
    with tempfile.TemporaryDirectory(prefix="uv-workspace-lock-") as temporary_directory:
        root = Path(temporary_directory)
        member = root / "packages/member"
        member.mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            """[project]
name = "workspace-root"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["workspace-member"]

[tool.uv.sources]
workspace-member = { workspace = true }

[tool.uv.workspace]
members = ["packages/member"]
""",
            encoding="utf-8",
        )
        member_config = member / "pyproject.toml"
        member_config.write_text(
            """[project]
name = "workspace-member"
version = "0.1.0"
requires-python = ">=3.14"
""",
            encoding="utf-8",
        )

        _run_uv(root, "lock")
        member_config.write_text(member_config.read_text(encoding="utf-8").replace("0.1.0", "0.2.0"), encoding="utf-8")
        stale = _run_uv(root, "lock", "--check", check=False)
        if stale.returncode == 0:
            _raise_runtime_error("uv lock --check accepted a stale workspace-member lock")
        _run_uv(root, "lock")
        _run_uv(root, "lock", "--check")
        lock_text = (root / "uv.lock").read_text(encoding="utf-8")
        if 'name = "workspace-member"' not in lock_text or 'version = "0.2.0"' not in lock_text:
            _raise_runtime_error("uv lock did not record the updated workspace-member version")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
