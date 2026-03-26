"""Diagnostic 9: test the exact operations logfire runs at module load."""

import pathlib
import subprocess
import sys
import time

out = pathlib.Path("docs/scratch/diag9-output.txt")
f = open(out, "w")
start = time.monotonic()


def log(msg):
    f.write(f"[{time.monotonic() - start:7.3f}] {msg}\n")
    f.flush()


log("start")

# Test 1: git rev-parse HEAD (logfire calls this without timeout)
log("test 1: git rev-parse HEAD...")
try:
    r = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.STDOUT, timeout=5)
    log(f"git ok: {r.decode().strip()}")
except subprocess.TimeoutExpired:
    log("git TIMED OUT after 5s!")
except Exception as e:
    log(f"git error: {e}")

# Test 2: ParamManager.create (reads config files)
log("test 2: logfire ParamManager.create...")
try:
    from logfire._internal.config_params import ParamManager

    pm = ParamManager.create(None)
    log(f"ParamManager ok")
except Exception as e:
    log(f"ParamManager error: {e}")

# Test 3: LogfireConfig() directly
log("test 3: LogfireConfig()...")
try:
    from logfire._internal.config import LogfireConfig

    c = LogfireConfig()
    log("LogfireConfig ok")
except Exception as e:
    log(f"LogfireConfig error: {e}")

# Test 4: GLOBAL_CONFIG access
log("test 4: GLOBAL_CONFIG access...")
try:
    from logfire._internal.config import GLOBAL_CONFIG

    log(f"GLOBAL_CONFIG ok: {type(GLOBAL_CONFIG)}")
except Exception as e:
    log(f"GLOBAL_CONFIG error: {e}")

log("ALL DONE")
f.close()
