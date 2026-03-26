"""Test if platform._wmi_query is the source of the hang."""

import pathlib
import time

out = pathlib.Path("docs/scratch/wmi-test.txt")
f = out.open("w")


def log(msg: str) -> None:
    f.write(f"[{time.monotonic():.3f}] {msg}\n")
    f.flush()


log("start")

# Test 1: platform.system() — this calls _wmi_query on Windows
log("calling platform.system()...")
t0 = time.monotonic()
import platform

result = platform.system()
dt = time.monotonic() - t0
log(f"platform.system() = {result!r} — took {dt:.3f}s")

# Test 2: direct _wmi call
log("calling _wmi.exec_query directly...")
t0 = time.monotonic()
try:
    import _wmi

    data = _wmi.exec_query("SELECT Version FROM Win32_OperatingSystem")
    dt = time.monotonic() - t0
    log(f"_wmi.exec_query = {data!r} — took {dt:.3f}s")
except Exception as e:
    dt = time.monotonic() - t0
    log(f"_wmi.exec_query failed after {dt:.3f}s: {e}")

# Test 3: can we import pydantic_settings after platform is cached?
log("now importing pydantic_settings (platform already cached)...")
t0 = time.monotonic()
from pydantic_settings import BaseSettings  # noqa: F401

dt = time.monotonic() - t0
log(f"pydantic_settings imported — took {dt:.3f}s")

log("ALL DONE")
f.close()
