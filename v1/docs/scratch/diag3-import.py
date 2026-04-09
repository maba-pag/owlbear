"""Diagnostic 3: even more granular — trace pydantic_settings import."""

import pathlib
import time

out = pathlib.Path("docs/scratch/diag3-output.txt")
lines: list[str] = []


def log(msg: str) -> None:
    lines.append(f"[{time.monotonic():.2f}] {msg}")
    out.write_text("\n".join(lines))


log("start")

log("importing python-dotenv...")
import dotenv

log(f"dotenv ok, version={dotenv.__version__ if hasattr(dotenv, '__version__') else 'unknown'}")

log("importing typing_inspection...")

log("typing_inspection ok")

log("importing pydantic_settings now...")
import pydantic_settings

log(
    f"pydantic_settings ok, version={pydantic_settings.__version__ if hasattr(pydantic_settings, '__version__') else 'unknown'}"
)

log("importing BaseSettings from pydantic_settings...")

log("BaseSettings ok")

log("ALL DONE")
