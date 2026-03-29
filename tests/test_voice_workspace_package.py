"""Failing tests for task #52: Create owlbear-voice workspace package.

Covers AC items NOT covered by tests/test_voice_package_scaffolding.py (task #100):
  - Base dependency minimum version constraints (moonshine-voice>=0.0.49, numpy>=1.26,
    pyttsx3>=2.90, sounddevice>=0.4)
  - Kokoro optional-extra minimum version constraint (kokoro>=0.9.4)
  - uv workspace membership: packages/voice is declared as a workspace member

All tests fail on current HEAD because packages/voice/pyproject.toml specifies bare
dependencies without version pins (e.g., "moonshine-voice" instead of "moonshine-voice>=0.0.49").
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
VOICE_PYPROJECT = ROOT / "packages" / "voice" / "pyproject.toml"


def _load_voice_pyproject() -> dict:
    assert VOICE_PYPROJECT.exists(), "packages/voice/pyproject.toml not found"
    with VOICE_PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


# ---------------------------------------------------------------------------
# AC5: base dependency version constraints
# ---------------------------------------------------------------------------


class TestFromAC_VoiceDepVersionConstraints:
    """AC5: [project.dependencies] must specify minimum version pins."""

    def _deps(self) -> list[str]:
        return _load_voice_pyproject().get("project", {}).get("dependencies", [])

    def test_moonshine_voice_min_version_0_0_49(self) -> None:
        """moonshine-voice must declare >=0.0.49 minimum version."""
        deps = self._deps()
        assert any("moonshine-voice>=0.0.49" in d for d in deps), (
            f"Expected 'moonshine-voice>=0.0.49' in base dependencies, found: {deps}"
        )

    def test_numpy_min_version_1_26(self) -> None:
        """numpy must declare >=1.26 minimum version."""
        deps = self._deps()
        assert any("numpy>=1.26" in d for d in deps), (
            f"Expected 'numpy>=1.26' in base dependencies, found: {deps}"
        )

    def test_pyttsx3_min_version_2_90(self) -> None:
        """pyttsx3 must declare >=2.90 minimum version."""
        deps = self._deps()
        assert any("pyttsx3>=2.90" in d for d in deps), (
            f"Expected 'pyttsx3>=2.90' in base dependencies, found: {deps}"
        )

    def test_sounddevice_min_version_0_4(self) -> None:
        """sounddevice must declare >=0.4 minimum version."""
        deps = self._deps()
        assert any("sounddevice>=0.4" in d for d in deps), (
            f"Expected 'sounddevice>=0.4' in base dependencies, found: {deps}"
        )


# ---------------------------------------------------------------------------
# AC6: kokoro optional-extra version constraint
# ---------------------------------------------------------------------------


class TestFromAC_VoiceKokoroVersionConstraint:
    """AC6: [project.optional-dependencies.kokoro] must pin kokoro>=0.9.4."""

    def test_kokoro_min_version_0_9_4(self) -> None:
        """kokoro in [kokoro] optional-extra must declare >=0.9.4 minimum version."""
        data = _load_voice_pyproject()
        kokoro_deps = (
            data.get("project", {})
            .get("optional-dependencies", {})
            .get("kokoro", [])
        )
        assert any("kokoro>=0.9.4" in d for d in kokoro_deps), (
            f"Expected 'kokoro>=0.9.4' in [kokoro] optional-dependencies, found: {kokoro_deps}"
        )
