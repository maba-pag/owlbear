"""Failing tests for task #746: Archive voice I/O research docs to handoff location.

Covers (TDD RED phase — all tests must FAIL before builder implements #746):
  - AC2: Originals deleted from .owlbear/research/

Pre-completed state (already satisfied on current HEAD, no tests needed):
  - AC1: All 11 + voicechannel-adapter.md already present in research-archive/
  - AC3: Handoff doc already has ## Research Archive manifest section

Only AC2 remains: the 11 originals have not been deleted from .owlbear/research/.
All 11 tests below fail on current HEAD because every original still exists.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent

RESEARCH_DIR = ROOT / ".owlbear" / "research"


# ---------------------------------------------------------------------------
# AC2: Originals deleted from .owlbear/research/
# ---------------------------------------------------------------------------


class TestFromAC_OriginalsDeleted:
    """AC2: All 11 voice I/O research docs absent from .owlbear/research/ after archiving."""

    def test_voice_addon_architecture_deleted_from_research(self) -> None:
        """voice-addon-architecture.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "voice-addon-architecture.md").exists(), (
            "voice-addon-architecture.md still exists in .owlbear/research/ — builder must delete it"
        )

    def test_voice_addon_stt_moonshine_deleted_from_research(self) -> None:
        """voice-addon-stt-moonshine.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "voice-addon-stt-moonshine.md").exists(), (
            "voice-addon-stt-moonshine.md still exists in .owlbear/research/ — builder must delete it"
        )

    def test_voice_channel_import_deleted_from_research(self) -> None:
        """voice-channel-import.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "voice-channel-import.md").exists(), (
            "voice-channel-import.md still exists in .owlbear/research/ — builder must delete it"
        )

    def test_voice_io_deleted_from_research(self) -> None:
        """voice-io.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "voice-io.md").exists(), (
            "voice-io.md still exists in .owlbear/research/ — builder must delete it"
        )

    def test_voice_panel_handbook_deleted_from_research(self) -> None:
        """voice-panel-handbook.md must be absent from .owlbear/research/ (NOT the share/skills/ copy)."""
        assert not (RESEARCH_DIR / "voice-panel-handbook.md").exists(), (
            "voice-panel-handbook.md still exists in .owlbear/research/ — builder must delete this copy only"
        )

    def test_voice_process_manager_deleted_from_research(self) -> None:
        """voice-process-manager.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "voice-process-manager.md").exists(), (
            "voice-process-manager.md still exists in .owlbear/research/ — builder must delete it"
        )

    def test_voice_protocol_models_deleted_from_research(self) -> None:
        """voice-protocol-models.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "voice-protocol-models.md").exists(), (
            "voice-protocol-models.md still exists in .owlbear/research/ — builder must delete it"
        )

    def test_voice_stdio_protocol_deleted_from_research(self) -> None:
        """voice-stdio-protocol.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "voice-stdio-protocol.md").exists(), (
            "voice-stdio-protocol.md still exists in .owlbear/research/ — builder must delete it"
        )

    def test_voice_tts_kokoro_pyttsx3_deleted_from_research(self) -> None:
        """voice-tts-kokoro-pyttsx3.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "voice-tts-kokoro-pyttsx3.md").exists(), (
            "voice-tts-kokoro-pyttsx3.md still exists in .owlbear/research/ — builder must delete it"
        )

    def test_moonshine_streaming_deleted_from_research(self) -> None:
        """moonshine-streaming.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "moonshine-streaming.md").exists(), (
            "moonshine-streaming.md still exists in .owlbear/research/ — builder must delete it"
        )

    def test_moonshine_vs_whisper_deleted_from_research(self) -> None:
        """moonshine-vs-whisper.md must be absent from .owlbear/research/."""
        assert not (RESEARCH_DIR / "moonshine-vs-whisper.md").exists(), (
            "moonshine-vs-whisper.md still exists in .owlbear/research/ — builder must delete it"
        )
