"""Tests for task #52: Create owlbear-voice workspace package.

Covers AC items NOT covered by tests/test_voice_package_scaffolding.py (task #100):
  - Base dependency minimum version constraints (moonshine-voice>=0.0.49, numpy>=1.26,
    pyttsx3>=2.90, sounddevice>=0.4)
  - Kokoro optional-extra minimum version constraint (kokoro>=0.9.4)
  - uv workspace membership: packages/voice is declared as a workspace member
  - Exact entry point target: scripts['owlbear-voice'] == 'owlbear_voice.main:main'

NOTE: Implementation was scaffolded before the TDD workflow ran. Tests verify the
AC contract is met; all pass on current HEAD (expected for a pre-built scaffold).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
VOICE_PYPROJECT = ROOT / "serve" / "voice" / "pyproject.toml"


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


# ---------------------------------------------------------------------------
# AC7 strict: entry point exact target
# ---------------------------------------------------------------------------


class TestFromAC_VoiceEntryPointTarget:
    """[project.scripts] owlbear-voice must point to the exact target owlbear_voice.main:main."""

    def test_entry_point_target_is_owlbear_voice_main_main(self) -> None:
        """AC7: scripts['owlbear-voice'] must equal 'owlbear_voice.main:main'."""
        data = _load_voice_pyproject()
        scripts = data.get("project", {}).get("scripts", {})
        target = scripts.get("owlbear-voice")
        assert target == "owlbear_voice.main:main", (
            f"Expected scripts['owlbear-voice'] == 'owlbear_voice.main:main', got {target!r}"
        )


# ---------------------------------------------------------------------------
# Workspace integration: uv workspace membership
# ---------------------------------------------------------------------------


class TestFromAC_VoiceWorkspaceMembership:
    """Root pyproject.toml [tool.uv.workspace] must cover packages/voice as a member."""

    def test_root_workspace_members_key_exists(self) -> None:
        """Workspace integration: [tool.uv.workspace].members must be declared."""
        root_pyproject = ROOT / "pyproject.toml"
        assert root_pyproject.exists(), "ROOT/pyproject.toml not found"
        with root_pyproject.open("rb") as fh:
            data = tomllib.load(fh)
        members = data.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
        assert members, "[tool.uv.workspace] members not declared in root pyproject.toml"

    def test_workspace_members_pattern_covers_voice_package(self) -> None:
        """Workspace integration: workspace members pattern must cover packages/voice."""
        import fnmatch

        root_pyproject = ROOT / "pyproject.toml"
        with root_pyproject.open("rb") as fh:
            data = tomllib.load(fh)
        members = data.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
        voice_rel = "packages/voice"
        matched = any(
            fnmatch.fnmatch(voice_rel, pattern) or voice_rel == pattern
            for pattern in members
        )
        assert matched, (
            f"packages/voice not covered by workspace members: {members}. "
            "Add 'packages/voice' or 'packages/*' to [tool.uv.workspace] members."
        )
