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
import dataclasses

log("ok")

log("importing functools...")
import functools

log("ok")

log("importing pathlib.Path...")
from pathlib import Path

log("ok")

log("importing pydantic...")
from pydantic import Field, SecretStr

log("pydantic ok")

log("importing pydantic_settings...")
from pydantic_settings import BaseSettings

log("pydantic_settings ok")

log("importing owlbear.config directly...")
from owlbear.config import OwlBearSettings

log("owlbear.config ok")

log("ALL DONE")
