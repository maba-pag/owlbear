"""Diagnostic 11: disable pydantic plugin loading."""

import os
import pathlib
import time

out = pathlib.Path("docs/scratch/diag11-output.txt")
f = open(out, "w")
start = time.monotonic()


def log(msg):
    f.write(f"[{time.monotonic() - start:7.3f}] {msg}\n")
    f.flush()


log("start")

# Try various approaches to disable logfire/pydantic plugins
os.environ["LOGFIRE_SEND_TO_LOGFIRE"] = "false"
os.environ["LOGFIRE_IGNORE_NO_CONFIG"] = "1"
os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"  # might not exist but worth trying

log("test A: import logfire._internal.config_params directly")
try:
    import importlib
    import importlib.util

    spec = importlib.util.find_spec("logfire._internal.config_params")
    log(f"spec found: {spec.origin if spec else 'NOT FOUND'}")
except Exception as e:
    log(f"find_spec error: {e}")

log("test B: check _internal __init__.py")
try:
    spec2 = importlib.util.find_spec("logfire._internal")
    log(f"_internal spec: {spec2.origin if spec2 else 'NOT FOUND'}")
    has_init = spec2 and spec2.origin and spec2.origin.endswith("__init__.py") is not False
    log(f"has __init__.py: {spec2.origin}")
except Exception as e:
    log(f"error: {e}")

log("test C: check if logfire._internal.__init__ imports config")
try:
    content = pathlib.Path(spec2.origin).read_text()
    log(f"_internal/__init__.py content ({len(content)} chars):")
    for line in content.splitlines()[:20]:
        log(f"  {line}")
except Exception as e:
    log(f"error: {e}")

log("test D: try importing JUST config_params, bypassing package init")
try:
    spec3 = importlib.util.find_spec("logfire._internal.config_params")
    if spec3 and spec3.loader:
        import sys

        # Register the package first without running its init
        if "logfire._internal" not in sys.modules:
            import types

            pkg = types.ModuleType("logfire._internal")
            pkg.__path__ = [str(pathlib.Path(spec2.origin).parent)]
            sys.modules["logfire._internal"] = pkg
        mod = importlib.util.module_from_spec(spec3)
        sys.modules["logfire._internal.config_params"] = mod
        spec3.loader.exec_module(mod)
        log("config_params loaded directly!")
except Exception as e:
    log(f"error: {type(e).__name__}: {e}")

log("ALL DONE")
f.close()
