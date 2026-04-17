"""Failing tests for task #747: Delete all voice I/O code and test files.

Covers (TDD RED phase — all tests must FAIL before builder implements #747):
  - AC1: serve/voice/ directory removed entirely
  - AC2: serve/orchestrator/src/owlbear/voice/ directory removed entirely
  - AC3: Six voice I/O test files deleted
  - AC4: Zero grep matches for voice package imports in serve/ and tests/

All tests fail on current HEAD because serve/voice/ and
serve/orchestrator/src/owlbear/voice/ still exist along with the 6 test files.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# AC1: serve/voice/ directory deleted entirely
# ---------------------------------------------------------------------------


class TestFromAC_VoicePackageRemoval:
    """AC1: serve/voice/ directory and all its contents deleted."""

    def test_serve_voice_dir_does_not_exist(self) -> None:
        """serve/voice/ must be absent after deletion."""
        assert not (ROOT / "serve" / "voice").exists(), "serve/voice/ still exists — builder must delete this directory"

    def test_serve_voice_pyproject_does_not_exist(self) -> None:
        """serve/voice/pyproject.toml must be absent after deletion."""
        assert not (ROOT / "serve" / "voice" / "pyproject.toml").exists(), (
            "serve/voice/pyproject.toml still exists — builder must delete this file"
        )

    def test_serve_voice_src_does_not_exist(self) -> None:
        """serve/voice/src/ directory must be absent after deletion."""
        assert not (ROOT / "serve" / "voice" / "src").exists(), (
            "serve/voice/src/ still exists — builder must delete this directory"
        )

    def test_owlbear_voice_package_does_not_exist(self) -> None:
        """serve/voice/src/owlbear_voice/ package must be absent after deletion."""
        assert not (ROOT / "serve" / "voice" / "src" / "owlbear_voice").exists(), (
            "serve/voice/src/owlbear_voice/ still exists — builder must delete this directory"
        )

    def test_serve_voice_tests_dir_does_not_exist(self) -> None:
        """serve/voice/tests/ directory must be absent after deletion."""
        assert not (ROOT / "serve" / "voice" / "tests").exists(), (
            "serve/voice/tests/ still exists — builder must delete this directory"
        )


# ---------------------------------------------------------------------------
# AC2: serve/orchestrator/src/owlbear/voice/ directory deleted entirely
# ---------------------------------------------------------------------------


class TestFromAC_OrchestratorVoiceRemoval:
    """AC2: serve/orchestrator/src/owlbear/voice/ and its 4 files deleted."""

    def test_orchestrator_voice_dir_does_not_exist(self) -> None:
        """serve/orchestrator/src/owlbear/voice/ must be absent after deletion."""
        assert not (ROOT / "serve" / "orchestrator" / "src" / "owlbear" / "voice").exists(), (
            "serve/orchestrator/src/owlbear/voice/ still exists — builder must delete this directory"
        )

    def test_orchestrator_voice_init_does_not_exist(self) -> None:
        """serve/orchestrator/src/owlbear/voice/__init__.py must be absent."""
        assert not (ROOT / "serve" / "orchestrator" / "src" / "owlbear" / "voice" / "__init__.py").exists(), (
            "voice/__init__.py still exists — builder must delete this file"
        )

    def test_orchestrator_voice_channel_does_not_exist(self) -> None:
        """serve/orchestrator/src/owlbear/voice/channel.py must be absent."""
        assert not (ROOT / "serve" / "orchestrator" / "src" / "owlbear" / "voice" / "channel.py").exists(), (
            "voice/channel.py still exists — builder must delete this file"
        )

    def test_orchestrator_voice_process_does_not_exist(self) -> None:
        """serve/orchestrator/src/owlbear/voice/process.py must be absent."""
        assert not (ROOT / "serve" / "orchestrator" / "src" / "owlbear" / "voice" / "process.py").exists(), (
            "voice/process.py still exists — builder must delete this file"
        )

    def test_orchestrator_voice_protocol_does_not_exist(self) -> None:
        """serve/orchestrator/src/owlbear/voice/protocol.py must be absent."""
        assert not (ROOT / "serve" / "orchestrator" / "src" / "owlbear" / "voice" / "protocol.py").exists(), (
            "voice/protocol.py still exists — builder must delete this file"
        )


# ---------------------------------------------------------------------------
# AC3: Six voice I/O test files deleted
# ---------------------------------------------------------------------------


class TestFromAC_VoiceTestFileRemoval:
    """AC3: All six voice I/O test files must be absent after deletion."""

    def test_test_voice_channel_does_not_exist(self) -> None:
        """tests/test_voice_channel.py must be absent after deletion."""
        assert not (ROOT / "tests" / "test_voice_channel.py").exists(), (
            "tests/test_voice_channel.py still exists — builder must delete this file"
        )

    def test_test_voice_process_manager_does_not_exist(self) -> None:
        """tests/test_voice_process_manager.py must be absent after deletion."""
        assert not (ROOT / "tests" / "test_voice_process_manager.py").exists(), (
            "tests/test_voice_process_manager.py still exists — builder must delete this file"
        )

    def test_test_voice_process_manager_kill_62_does_not_exist(self) -> None:
        """tests/test_voice_process_manager_kill_62.py must be absent after deletion."""
        assert not (ROOT / "tests" / "test_voice_process_manager_kill_62.py").exists(), (
            "tests/test_voice_process_manager_kill_62.py still exists — builder must delete this file"
        )

    def test_test_voice_protocol_does_not_exist(self) -> None:
        """tests/test_voice_protocol.py must be absent after deletion."""
        assert not (ROOT / "tests" / "test_voice_protocol.py").exists(), (
            "tests/test_voice_protocol.py still exists — builder must delete this file"
        )

    def test_test_voice_stt_does_not_exist(self) -> None:
        """tests/test_voice_stt.py must be absent after deletion."""
        assert not (ROOT / "tests" / "test_voice_stt.py").exists(), (
            "tests/test_voice_stt.py still exists — builder must delete this file"
        )

    def test_test_voice_tts_does_not_exist(self) -> None:
        """tests/test_voice_tts.py must be absent after deletion."""
        assert not (ROOT / "tests" / "test_voice_tts.py").exists(), (
            "tests/test_voice_tts.py still exists — builder must delete this file"
        )


# ---------------------------------------------------------------------------
# AC4: Zero grep matches for voice package imports in serve/ and tests/
# ---------------------------------------------------------------------------


_VOICE_IMPORT_PATTERN = re.compile(r"from owlbear\.voice|from owlbear_voice|import owlbear\.voice|import owlbear_voice")

_SCAN_DIRS = ["serve", "tests"]


def _collect_voice_import_matches() -> list[tuple[Path, int, str]]:
    """Return (file, line_no, line) tuples for any remaining voice imports."""
    matches = []
    for dir_name in _SCAN_DIRS:
        scan_root = ROOT / dir_name
        if not scan_root.exists():
            continue
        for py_file in scan_root.rglob("*.py"):
            # Skip this test file itself
            if py_file.name == "test_delete_voice_io_747.py":
                continue
            for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), start=1):
                if _VOICE_IMPORT_PATTERN.search(line):
                    matches.append((py_file, lineno, line.strip()))
    return matches


class TestFromAC_NoVoiceImportsRemaining:
    """AC4: Zero voice package import statements remain in serve/ and tests/."""

    def test_no_voice_imports_in_serve_or_tests(self) -> None:
        """grep for voice imports across serve/ and tests/ must return no matches."""
        matches = _collect_voice_import_matches()
        formatted = "\n".join(f"  {path.relative_to(ROOT)}:{lineno}: {line}" for path, lineno, line in matches)
        assert not matches, f"Found {len(matches)} voice import(s) still present — builder must remove:\n{formatted}"

    def test_no_owlbear_voice_subpackage_imports_in_serve(self) -> None:
        """No file under serve/ may import from owlbear.voice sub-modules."""
        serve_root = ROOT / "serve"
        if not serve_root.exists():
            return  # serve/ already gone — this AC is satisfied
        bad: list[str] = []
        for py_file in serve_root.rglob("*.py"):
            for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), start=1):
                if re.search(r"owlbear\.voice\.|owlbear_voice\.", line):
                    bad.append(f"  {py_file.relative_to(ROOT)}:{lineno}: {line.strip()}")
        assert not bad, f"Found {len(bad)} owlbear.voice sub-module reference(s) in serve/:\n" + "\n".join(bad)
