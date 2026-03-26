"""Quick verification that pytest runs after conftest.py WMI fix."""

import pathlib
import subprocess
import sys

out = pathlib.Path("docs/scratch/pytest-verify-out.txt")
r = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_config.py", "-q", "--tb=short", "-x"],
    capture_output=True,
    text=True,
    timeout=60,
)
out.write_text(f"exit: {r.returncode}\n---STDOUT---\n{r.stdout}\n---STDERR---\n{r.stderr}")
print(f"exit: {r.returncode}")
