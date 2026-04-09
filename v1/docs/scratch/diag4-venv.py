"""Diagnostic 4: test with direct venv python (no uv run)."""

import pathlib
import time

out = pathlib.Path("docs/scratch/diag4-output.txt")
lines: list[str] = []


def log(msg: str) -> None:
    lines.append(f"[{time.monotonic():.2f}] {msg}")
    out.write_text("\n".join(lines))


log("start - using venv python directly")

log("importing pydantic_settings...")

log("pydantic_settings ok!")

log("importing owlbear.config...")

log("owlbear.config ok!")

log("running pytest collect-only...")
import subprocess
import sys

r = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_config.py", "--collect-only", "-q"],
    capture_output=True,
    text=True,
    timeout=30,
)
log(f"pytest collect exit={r.returncode}")
log(f"stdout={r.stdout[:500]}")
log(f"stderr={r.stderr[:500]}")

log("ALL DONE")
