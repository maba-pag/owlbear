"""Diagnostic 8: import tracer with per-line flush."""

import pathlib
import time

out = pathlib.Path("docs/scratch/diag8-output.txt")
f = open(out, "w")
start = time.monotonic()


def log(msg):
    elapsed = time.monotonic() - start
    f.write(f"[{elapsed:7.3f}] {msg}\n")
    f.flush()


original_import = __builtins__.__import__


def tracing_import(name, *args, **kwargs):
    log(f"IMPORT {name}")
    t0 = time.monotonic()
    result = original_import(name, *args, **kwargs)
    dt = time.monotonic() - t0
    if dt > 0.05:
        log(f"  SLOW ({dt:.3f}s): {name}")
    return result


__builtins__.__import__ = tracing_import
log("start")

try:
    from pydantic_settings import BaseSettings

    log("pydantic_settings imported ok")
except Exception as e:
    log(f"FAILED: {e}")

log("ALL DONE")
f.close()
