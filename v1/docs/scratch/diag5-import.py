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
from pydantic_settings.exceptions import SettingsError

log("ok")

log("step 2: pydantic_settings.main...")
from pydantic_settings.main import BaseSettings

log("ok")

log("step 3: pydantic_settings.sources.base...")
from pydantic_settings.sources.base import PydanticBaseSettingsSource

log("ok")

log("step 4: pydantic_settings.sources.providers.aws...")
from pydantic_settings.sources.providers.aws import AWSSecretsManagerSettingsSource

log("ok")

log("step 5: pydantic_settings.sources.providers.azure...")
from pydantic_settings.sources.providers.azure import AzureKeyVaultSettingsSource

log("ok")

log("step 6: pydantic_settings.sources.providers.gcp...")
from pydantic_settings.sources.providers.gcp import GoogleSecretManagerSettingsSource

log("ok")

log("step 7: pydantic_settings.sources.providers.cli...")
from pydantic_settings.sources.providers.cli import CliSettingsSource

log("ok")

log("step 8: pydantic_settings.sources.providers.dotenv...")
from pydantic_settings.sources.providers.dotenv import DotEnvSettingsSource

log("ok")

log("step 9: pydantic_settings.sources.providers.env...")
from pydantic_settings.sources.providers.env import EnvSettingsSource

log("ok")

log("step 10: pydantic_settings.sources.providers.toml...")
from pydantic_settings.sources.providers.toml import TomlConfigSettingsSource

log("ok")

log("step 11: pydantic_settings.sources.providers.yaml...")
from pydantic_settings.sources.providers.yaml import YamlConfigSettingsSource

log("ok")

log("ALL DONE")
