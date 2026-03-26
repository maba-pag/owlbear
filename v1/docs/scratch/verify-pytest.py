"""Verify pytest works end-to-end with the WMI fix."""

import pathlib
import subprocess
import sys
import time

out = pathlib.Path("docs/scratch/pytest-verify.txt")
t0 = time.monotonic()

r = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_config.py", "-q", "--tb=short", "-x"],
    capture_output=True,
    text=True,
    timeout=60,
)

dt = time.monotonic() - t0
content = f"exit: {r.returncode}\ntime: {dt:.1f}s\n\n--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}"
out.write_text(content)
print(f"exit={r.returncode} in {dt:.1f}s")
