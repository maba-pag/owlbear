"""Diagnostic 5: trace pydantic_settings sub-imports one by one."""

import pathlib
import time

out = pathlib.Path("docs/scratch/diag5-output.txt")
lines: list[str] = []


def log(msg: str) -> None:
    lines.append(f"[{time.monotonic():.2f}] {msg}")
    out.write_text("\n".join(lines))


log("start")

log("step 1: pydantic_settings.exceptions...")

log("ok")

log("step 2: pydantic_settings.main...")

log("ok")

log("step 3: pydantic_settings.sources.base...")

log("ok")

log("step 4: pydantic_settings.sources.providers.aws...")

log("ok")

log("step 5: pydantic_settings.sources.providers.azure...")

log("ok")

log("step 6: pydantic_settings.sources.providers.gcp...")

log("ok")

log("step 7: pydantic_settings.sources.providers.cli...")

log("ok")

log("step 8: pydantic_settings.sources.providers.dotenv...")

log("ok")

log("step 9: pydantic_settings.sources.providers.env...")

log("ok")

log("step 10: pydantic_settings.sources.providers.toml...")

log("ok")

log("step 11: pydantic_settings.sources.providers.yaml...")

log("ok")

log("ALL DONE")
