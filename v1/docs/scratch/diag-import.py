"""Diagnostic: check what hangs during pytest collection."""

import pathlib
import sys
import time

out = pathlib.Path("docs/scratch/diag-output.txt")
lines: list[str] = []


def log(msg: str) -> None:
    lines.append(f"[{time.monotonic():.2f}] {msg}")
    out.write_text("\n".join(lines))


log("start")

try:
    log("importing owlbear...")
    import owlbear

    log("owlbear imported ok")
except Exception as e:
    log(f"owlbear import FAILED: {e}")

try:
    log("importing owlbear.config...")
    from owlbear.config import OwlBearSettings, get_settings

    log("config imported ok")
except Exception as e:
    log(f"config import FAILED: {e}")

try:
    log("importing conftest deps (pytest)...")
    import pytest

    log("pytest imported ok")
except Exception as e:
    log(f"pytest import FAILED: {e}")

try:
    log("importing owlbear.tools...")
    from owlbear import tools

    log(f"owlbear.tools imported ok, dir={dir(tools)}")
except Exception as e:
    log(f"owlbear.tools import FAILED: {e}")

try:
    log("importing owlbear.tools.diagram...")
    from owlbear.tools.diagram import service

    log("diagram.service imported ok")
except Exception as e:
    log(f"diagram.service import FAILED: {e}")

try:
    log("importing test_diagram_service module directly...")
    sys.path.insert(0, "tests")
    import test_diagram_service

    log("test_diagram_service imported ok")
except Exception as e:
    log(f"test_diagram_service import FAILED: {e}")

log("ALL IMPORTS DONE")
