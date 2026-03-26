"""Verify voice extras in pyproject.toml include all required packages."""

from __future__ import annotations

import tomllib
from pathlib import Path


def _voice_extras() -> list[str]:
    """Return the voice extras list from pyproject.toml."""
    root = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with root.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["optional-dependencies"]["voice"]


class TestVoiceExtras:
    """F-05: sounddevice must be declared in voice extras."""

    def test_sounddevice_in_voice_extras(self) -> None:
        extras = _voice_extras()
        pkgs = [dep.split(">")[0].split("<")[0].split("=")[0].strip() for dep in extras]
        assert "sounddevice" in pkgs, f"sounddevice missing from voice extras: {extras}"

    def test_sounddevice_min_version(self) -> None:
        extras = _voice_extras()
        sd = [dep for dep in extras if dep.startswith("sounddevice")]
        assert sd, "sounddevice not found in voice extras"
        assert ">=0.4" in sd[0], f"Expected >=0.4 constraint, got: {sd[0]}"
