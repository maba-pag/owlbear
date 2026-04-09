"""Diagnostic: granular import trace for owlbear.config hang."""

import pathlib
import time

out = pathlib.Path("docs/scratch/diag2-output.txt")
lines: list[str] = []


def log(msg: str) -> None:
    lines.append(f"[{time.monotonic():.2f}] {msg}")
    out.write_text("\n".join(lines))


log("start")

log("importing dataclasses...")

log("ok")

log("importing functools...")

log("ok")

log("importing pathlib.Path...")

log("ok")

log("importing pydantic...")

log("pydantic ok")

log("importing pydantic_settings...")

log("pydantic_settings ok")

log("importing owlbear.config directly...")

log("owlbear.config ok")

log("ALL DONE")
