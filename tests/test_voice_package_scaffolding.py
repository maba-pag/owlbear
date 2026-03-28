"""Failing tests for task #100: Test owlbear-voice workspace package scaffolding.

Covers:
  - File existence: packages/voice/pyproject.toml, __init__.py, main.py, tests/__init__.py
  - pyproject.toml metadata: name, version, requires-python, build-backend, hatch wheel config
  - Dependencies: base deps (moonshine-voice, numpy, pyttsx3, sounddevice), optional [kokoro]
  - Entry point: owlbear-voice scripts key declared
  - Root pyproject.toml: ruff src includes packages/voice/src
  - Importability: owlbear_voice is importable

All tests fail on current HEAD because packages/voice/ does not exist yet.
"""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
VOICE_DIR = ROOT / "packages" / "voice"
VOICE_PYPROJECT = VOICE_DIR / "pyproject.toml"


# ---------------------------------------------------------------------------
# Helper — load pyproject.toml once per test (but fail fast if not present)
# ---------------------------------------------------------------------------


def _load_voice_pyproject() -> dict:
    assert VOICE_PYPROJECT.exists(), "packages/voice/pyproject.toml not found"
    with VOICE_PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


# ---------------------------------------------------------------------------
# AC1, AC8, AC9, AC10: File stubs exist
# ---------------------------------------------------------------------------


class TestFromAC_VoicePackageFiles:
    """File stubs required by the voice package scaffold must exist."""

    def test_voice_pyproject_toml_exists(self) -> None:
        """AC1: packages/voice/pyproject.toml must exist."""
        assert VOICE_PYPROJECT.exists(), "packages/voice/pyproject.toml not found"

    def test_voice_init_stub_exists(self) -> None:
        """AC8: packages/voice/src/owlbear_voice/__init__.py must exist."""
        assert (VOICE_DIR / "src" / "owlbear_voice" / "__init__.py").exists(), (
            "packages/voice/src/owlbear_voice/__init__.py not found"
        )

    def test_voice_main_stub_exists(self) -> None:
        """AC9 (existence): packages/voice/src/owlbear_voice/main.py must exist."""
        assert (VOICE_DIR / "src" / "owlbear_voice" / "main.py").exists(), (
            "packages/voice/src/owlbear_voice/main.py not found"
        )

    def test_voice_tests_init_exists(self) -> None:
        """AC10: packages/voice/tests/__init__.py must exist."""
        assert (VOICE_DIR / "tests" / "__init__.py").exists(), (
            "packages/voice/tests/__init__.py not found"
        )


# ---------------------------------------------------------------------------
# AC2: pyproject.toml project metadata
# ---------------------------------------------------------------------------


class TestFromAC_VoiceProjectMetadata:
    """pyproject.toml [project] section must declare correct metadata."""

    def test_package_name_is_owlbear_voice(self) -> None:
        """AC2: [project] name must be 'owlbear-voice'."""
        data = _load_voice_pyproject()
        assert data["project"]["name"] == "owlbear-voice", (
            f"expected name='owlbear-voice', got {data['project'].get('name')!r}"
        )

    def test_package_version_is_0_1_0(self) -> None:
        """AC2: [project] version must be '0.1.0'."""
        data = _load_voice_pyproject()
        assert data["project"]["version"] == "0.1.0", (
            f"expected version='0.1.0', got {data['project'].get('version')!r}"
        )

    def test_requires_python_gte_3_12(self) -> None:
        """AC2: requires-python must be '>=3.12'."""
        data = _load_voice_pyproject()
        assert data["project"]["requires-python"] == ">=3.12", (
            f"expected requires-python='>=3.12', got {data['project'].get('requires-python')!r}"
        )


# ---------------------------------------------------------------------------
# AC3: hatchling build-backend
# ---------------------------------------------------------------------------


class TestFromAC_VoiceBuildSystem:
    """pyproject.toml [build-system] must declare hatchling."""

    def test_build_backend_is_hatchling(self) -> None:
        """AC3: [build-system] build-backend must be 'hatchling.build'."""
        data = _load_voice_pyproject()
        backend = data.get("build-system", {}).get("build-backend")
        assert backend == "hatchling.build", (
            f"expected build-backend='hatchling.build', got {backend!r}"
        )

    def test_hatchling_in_build_requires(self) -> None:
        """AC3: [build-system] requires must include 'hatchling'."""
        data = _load_voice_pyproject()
        requires = data.get("build-system", {}).get("requires", [])
        assert any("hatchling" in r for r in requires), (
            f"'hatchling' not found in build-system.requires: {requires}"
        )


# ---------------------------------------------------------------------------
# AC4: hatch wheel config
# ---------------------------------------------------------------------------


class TestFromAC_VoiceHatchWheelConfig:
    """[tool.hatch.build.targets.wheel] must target the owlbear_voice source tree."""

    def test_hatch_wheel_packages_targets_owlbear_voice(self) -> None:
        """AC4: wheel.packages must contain 'src/owlbear_voice'."""
        data = _load_voice_pyproject()
        wheel_cfg = (
            data.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
        )
        packages = wheel_cfg.get("packages", [])
        assert "src/owlbear_voice" in packages, (
            f"'src/owlbear_voice' not in wheel packages: {packages}"
        )


# ---------------------------------------------------------------------------
# AC5: base dependencies
# ---------------------------------------------------------------------------


class TestFromAC_VoiceBaseDependencies:
    """[project.dependencies] must list all required runtime packages."""

    def _deps(self) -> list[str]:
        return _load_voice_pyproject().get("project", {}).get("dependencies", [])

    def test_base_deps_moonshine_voice(self) -> None:
        """AC5: moonshine-voice must appear in base dependencies."""
        deps = self._deps()
        assert any("moonshine-voice" in d for d in deps), (
            f"moonshine-voice not found in dependencies: {deps}"
        )

    def test_base_deps_numpy(self) -> None:
        """AC5: numpy must appear in base dependencies."""
        deps = self._deps()
        assert any("numpy" in d for d in deps), (
            f"numpy not found in dependencies: {deps}"
        )

    def test_base_deps_pyttsx3(self) -> None:
        """AC5: pyttsx3 must appear in base dependencies."""
        deps = self._deps()
        assert any("pyttsx3" in d for d in deps), (
            f"pyttsx3 not found in dependencies: {deps}"
        )

    def test_base_deps_sounddevice(self) -> None:
        """AC5: sounddevice must appear in base dependencies."""
        deps = self._deps()
        assert any("sounddevice" in d for d in deps), (
            f"sounddevice not found in dependencies: {deps}"
        )


# ---------------------------------------------------------------------------
# AC6: [kokoro] optional extra
# ---------------------------------------------------------------------------


class TestFromAC_VoiceKokoroOptionalExtra:
    """[project.optional-dependencies.kokoro] must exist and list kokoro + soundfile."""

    def _kokoro_deps(self) -> list[str]:
        data = _load_voice_pyproject()
        return data.get("project", {}).get("optional-dependencies", {}).get("kokoro", [])

    def test_kokoro_optional_extra_key_declared(self) -> None:
        """AC6: [project.optional-dependencies] must have a 'kokoro' key."""
        data = _load_voice_pyproject()
        opt_deps = data.get("project", {}).get("optional-dependencies", {})
        assert "kokoro" in opt_deps, (
            f"'kokoro' optional-dependencies key not found; keys present: {list(opt_deps)}"
        )

    def test_kokoro_extra_includes_kokoro_package(self) -> None:
        """AC6: [kokoro] extra must include the kokoro package."""
        deps = self._kokoro_deps()
        assert any("kokoro" in d for d in deps), (
            f"kokoro package not in [kokoro] extra: {deps}"
        )

    def test_kokoro_extra_includes_soundfile(self) -> None:
        """AC6: [kokoro] extra must include soundfile."""
        deps = self._kokoro_deps()
        assert any("soundfile" in d for d in deps), (
            f"soundfile not in [kokoro] extra: {deps}"
        )


# ---------------------------------------------------------------------------
# AC7: entry point
# ---------------------------------------------------------------------------


class TestFromAC_VoiceEntryPoint:
    """[project.scripts] must declare the owlbear-voice command."""

    def test_entry_point_owlbear_voice_declared(self) -> None:
        """AC7: [project.scripts] must contain 'owlbear-voice' key."""
        data = _load_voice_pyproject()
        scripts = data.get("project", {}).get("scripts", {})
        assert "owlbear-voice" in scripts, (
            f"'owlbear-voice' entry point not found in [project.scripts]: {scripts}"
        )


# ---------------------------------------------------------------------------
# AC9: main.py callable main()
# ---------------------------------------------------------------------------


class TestFromAC_VoiceMainCallable:
    """main.py stub must define a callable main() function."""

    def test_main_py_defines_main_function(self) -> None:
        """AC9: packages/voice/src/owlbear_voice/main.py must define 'def main'."""
        main_path = VOICE_DIR / "src" / "owlbear_voice" / "main.py"
        assert main_path.exists(), "main.py not found"
        source = main_path.read_text(encoding="utf-8")
        assert "def main" in source, (
            "No 'def main' found in main.py — entry point must define a callable main()"
        )


# ---------------------------------------------------------------------------
# AC11: root pyproject.toml ruff src
# ---------------------------------------------------------------------------


class TestFromAC_VoiceRootRuffConfig:
    """Root pyproject.toml [tool.ruff] src must include packages/voice/src."""

    def test_root_ruff_src_includes_voice(self) -> None:
        """AC11: ROOT/pyproject.toml tool.ruff.src must list 'packages/voice/src'."""
        root_pyproject = ROOT / "pyproject.toml"
        assert root_pyproject.exists(), "ROOT/pyproject.toml not found"
        with root_pyproject.open("rb") as fh:
            data = tomllib.load(fh)
        ruff_src = data.get("tool", {}).get("ruff", {}).get("src", [])
        assert "packages/voice/src" in ruff_src, (
            f"'packages/voice/src' not in [tool.ruff] src: {ruff_src}"
        )


# ---------------------------------------------------------------------------
# AC12: importability
# ---------------------------------------------------------------------------


class TestFromAC_VoiceImportability:
    """owlbear_voice must be importable after package installation."""

    def test_owlbear_voice_importable(self) -> None:
        """AC12: importlib.util.find_spec('owlbear_voice') must return a spec."""
        spec = importlib.util.find_spec("owlbear_voice")
        assert spec is not None, (
            "owlbear_voice is not importable — find_spec returned None. "
            "Package may not be installed in the workspace virtual environment."
        )
