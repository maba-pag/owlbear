"""Test _wmi directly to confirm it's the bottleneck."""

import pathlib
import sys
import time

out = pathlib.Path("docs/scratch/wmi-direct.txt")
f = out.open("w")


def log(msg: str) -> None:
    f.write(f"[{time.monotonic():.3f}] {msg}\n")
    f.flush()


log("start")

# Test 1: sys.platform (no WMI — instant)
log(f"sys.platform = {sys.platform!r}")

# Test 2: _wmi.exec_query (the exact operation that hangs)
log("calling _wmi.exec_query...")
t0 = time.monotonic()
import _wmi

data = _wmi.exec_query("SELECT Version FROM Win32_OperatingSystem")
dt = time.monotonic() - t0
log(f"_wmi result = {data!r} — took {dt:.3f}s")

log("DONE")
f.close()
