"""OwlBear application settings.

Uses pydantic-settings to load configuration from environment variables
(prefix ``OWLBEAR_``) with sensible defaults. Instantiate with
``OwlBearSettings()`` — no arguments required for local development.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class OwlBearSettings(BaseSettings):
    """Central configuration for the OwlBear daemon and CLI.

    All fields can be overridden via environment variables with the
    ``OWLBEAR_`` prefix. For example, ``OWLBEAR_DEBUG=true`` enables
    debug mode.
    """

    model_config = {"env_prefix": "OWLBEAR_"}

    # --- LLM provider ---
    provider: Literal["copilot"] = "copilot"
    copilot_token_path: Path = Path.home() / ".owlbear" / "copilot_token.json"
    copilot_base_url: str = "https://api.individual.githubcopilot.com"
    chat_model: str = "gpt-4o"

    # --- Directories ---
    config_dir: Path = Path.home() / ".owlbear"

    # --- Runtime ---
    debug: bool = False
