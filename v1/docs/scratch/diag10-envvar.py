"""Diagnostic 10: test with logfire disabled via env var."""

import os
import pathlib
import time

out = pathlib.Path("docs/scratch/diag10-output.txt")
f = open(out, "w")
start = time.monotonic()


def log(msg):
    f.write(f"[{time.monotonic() - start:7.3f}] {msg}\n")
    f.flush()


log("start")

# Disable logfire
os.environ["LOGFIRE_SEND_TO_LOGFIRE"] = "false"
os.environ["LOGFIRE_IGNORE_NO_CONFIG"] = "1"
log("env vars set: LOGFIRE_SEND_TO_LOGFIRE=false, LOGFIRE_IGNORE_NO_CONFIG=1")

log("importing pydantic_settings...")
from pydantic_settings import BaseSettings

log("pydantic_settings ok!")

log("importing owlbear.config...")
from owlbear.config import OwlBearSettings

log("owlbear.config ok!")

log("ALL DONE")
f.close()
