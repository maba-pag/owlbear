"""Diagnostic 6: bypass pydantic_settings __init__.py, import providers individually."""

import importlib.util
import pathlib
import sys
import time

out = pathlib.Path("docs/scratch/diag6-output.txt")
lines: list[str] = []


def log(msg: str) -> None:
    lines.append(f"[{time.monotonic():.2f}] {msg}")
    out.write_text("\n".join(lines))


def load_module(name: str, filepath: str) -> None:
    spec = importlib.util.spec_from_file_location(name, filepath)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)


base = r".venv\Lib\site-packages\pydantic_settings"

log("start - direct file imports (no __init__.py)")

# First import pydantic (needed by pydantic_settings submodules)
log("importing pydantic...")
import pydantic

log(f"pydantic ok v{pydantic.__version__}")

log("importing pydantic_settings.version...")
load_module("pydantic_settings.version", f"{base}\\version.py")
log("ok")

log("importing pydantic_settings.exceptions...")
load_module("pydantic_settings.exceptions", f"{base}\\exceptions.py")
log("ok")

# The main module imports from sources, so skip it and test providers directly
log("importing sources.types...")
load_module("pydantic_settings.sources.types", f"{base}\\sources\\types.py")
log("ok")

log("importing sources.utils...")
load_module("pydantic_settings.sources.utils", f"{base}\\sources\\utils.py")
log("ok")

# Now try each provider
providers = [
    "aws",
    "azure",
    "gcp",
    "cli",
    "dotenv",
    "env",
    "json",
    "nested_secrets",
    "pyproject",
    "secrets",
    "toml",
    "yaml",
]

for p in providers:
    log(f"importing providers.{p}...")
    try:
        load_module(
            f"pydantic_settings.sources.providers.{p}", f"{base}\\sources\\providers\\{p}.py"
        )
        log(f"providers.{p} ok")
    except Exception as e:
        log(f"providers.{p} FAILED: {type(e).__name__}: {e}")

log("importing sources.base...")
try:
    load_module("pydantic_settings.sources.base", f"{base}\\sources\\base.py")
    log("ok")
except Exception as e:
    log(f"FAILED: {type(e).__name__}: {e}")

log("importing pydantic_settings.main...")
try:
    load_module("pydantic_settings.main", f"{base}\\main.py")
    log("ok")
except Exception as e:
    log(f"FAILED: {type(e).__name__}: {e}")

log("ALL DONE")
