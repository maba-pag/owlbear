"""Diagnostic 7: use sys.settrace to monitor import progress."""

import pathlib
import sys
import time

out = pathlib.Path("docs/scratch/diag7-output.txt")
lines: list[str] = []
start = time.monotonic()


def log(msg: str) -> None:
    elapsed = time.monotonic() - start
    lines.append(f"[{elapsed:7.3f}] {msg}")
    # Write every 10 lines to reduce I/O
    if len(lines) % 10 == 0:
        out.write_text("\n".join(lines))


original_import = __builtins__.__import__


def tracing_import(name, *args, **kwargs):
    log(f"IMPORT {name}")
    t0 = time.monotonic()
    result = original_import(name, *args, **kwargs)
    dt = time.monotonic() - t0
    if dt > 0.1:
        log(f"  SLOW ({dt:.2f}s): {name}")
    return result


__builtins__.__import__ = tracing_import

log("start - tracing all imports")

try:
    log(">>> from pydantic_settings import BaseSettings")
    from pydantic_settings import BaseSettings

    log("<<< pydantic_settings imported ok")
except Exception as e:
    log(f"FAILED: {e}")

# Final flush
out.write_text("\n".join(lines))
log("ALL DONE")
out.write_text("\n".join(lines))
