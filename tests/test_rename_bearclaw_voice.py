"""Failing tests for task #64: Rename bearclaw-voice to owlbear-voice.

Covers: kanban task body renames (#52, #51, #30), research doc renames
(voice-addon-architecture.md, bearclaw-voice-workspace-package.md + note header,
voice-addon-stt-moonshine.md, voice-stdio-protocol.md, voice-tts-kokoro-pyttsx3.md,
voice-io.md), sources doc section header, and completeness check (zero remaining
bearclaw-voice refs in kanban/tasks/ and docs/research/).

All tests fail on current HEAD because the bearclaw-voice → owlbear-voice
replacements have not yet been applied.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


class TestFromAC_KanbanTaskRenames:
    """AC: kanban task body renames via kanban-md edit."""

    def test_task_52_title_updated(self) -> None:
        """Task #52 title must say 'Create owlbear-voice workspace package'."""
        path = ROOT / "kanban" / "tasks" / "052-create-bearclaw-voice-workspace-package.md"
        content = path.read_text(encoding="utf-8")
        assert "title: Create owlbear-voice workspace package" in content

    def test_task_52_body_scaffold_line_owlbear(self) -> None:
        """Task #52 body: 'Scaffold the owlbear-voice package' replaces bearclaw ref (line 18)."""
        path = ROOT / "kanban" / "tasks" / "052-create-bearclaw-voice-workspace-package.md"
        content = path.read_text(encoding="utf-8")
        assert "Scaffold the bearclaw-voice package" not in content
        assert "Scaffold the owlbear-voice package" in content

    def test_task_52_body_findings_line_updated(self) -> None:
        """Task #52 body: research findings reference (line 31) must not say 'bearclaw-voice'."""
        path = ROOT / "kanban" / "tasks" / "052-create-bearclaw-voice-workspace-package.md"
        content = path.read_text(encoding="utf-8")
        # The 'Key findings from ...' line should no longer reference bearclaw-voice
        assert "Key findings from docs/research/bearclaw-voice-workspace-package.md:" not in content

    def test_task_52_body_followup_line_updated(self) -> None:
        """Task #52 body: follow-up task reference (line 40) must not say 'bearclaw-voice to owlbear-voice (ideation)'."""
        path = ROOT / "kanban" / "tasks" / "052-create-bearclaw-voice-workspace-package.md"
        content = path.read_text(encoding="utf-8")
        # After the rename task completes, this note should be updated
        assert "bearclaw-voice to owlbear-voice (ideation)" not in content

    def test_task_51_body_line32_updated(self) -> None:
        """Task #51 body line 32: dependency note must not say 'bearclaw-voice workspace package'."""
        path = ROOT / "kanban" / "tasks" / "051-implement-voice-addon-tts-with-kokoro-and-pyttsx3.md"
        content = path.read_text(encoding="utf-8")
        assert "Depends on #52 (bearclaw-voice workspace package scaffold)" not in content

    def test_task_51_body_line32_owlbear(self) -> None:
        """Task #51 body line 32: dependency note uses owlbear-voice."""
        path = ROOT / "kanban" / "tasks" / "051-implement-voice-addon-tts-with-kokoro-and-pyttsx3.md"
        content = path.read_text(encoding="utf-8")
        assert "Depends on #52 (owlbear-voice workspace package scaffold)" in content

    def test_task_51_body_line80_updated(self) -> None:
        """Task #51 body line 80: 'Added: #52 (bearclaw-voice workspace package scaffold)' replaced."""
        path = ROOT / "kanban" / "tasks" / "051-implement-voice-addon-tts-with-kokoro-and-pyttsx3.md"
        content = path.read_text(encoding="utf-8")
        assert "Added: #52 (bearclaw-voice workspace package scaffold)" not in content

    def test_task_30_body_line45_updated(self) -> None:
        """Task #30 body line 45: '- #52 bearclaw-voice workspace package' replaced."""
        path = ROOT / "kanban" / "tasks" / "030-research-voice-addon-architecture.md"
        content = path.read_text(encoding="utf-8")
        assert "- #52 bearclaw-voice workspace package" not in content

    def test_task_30_body_line45_owlbear(self) -> None:
        """Task #30 body line 45: entry uses owlbear-voice."""
        path = ROOT / "kanban" / "tasks" / "030-research-voice-addon-architecture.md"
        content = path.read_text(encoding="utf-8")
        assert "- #52 owlbear-voice workspace package" in content


class TestFromAC_ResearchDocRenames:
    """AC: research doc text replacements (bearclaw-voice / bearclaw_voice → owlbear equivalents)."""

    def test_voice_addon_architecture_line104_updated(self) -> None:
        """voice-addon-architecture.md: line 104 package ref must use owlbear-voice not bearclaw-voice."""
        doc = ROOT / "docs" / "research" / "voice-addon-architecture.md"
        content = doc.read_text(encoding="utf-8")
        # Line 104: "- **Package:** Separate `bearclaw-voice` package..."
        assert "Separate `bearclaw-voice` package" not in content
        assert "Separate `owlbear-voice` package" in content

    def test_voice_addon_architecture_line117_updated(self) -> None:
        """voice-addon-architecture.md: line 117 kanban command must say 'Create owlbear-voice workspace package'."""
        doc = ROOT / "docs" / "research" / "voice-addon-architecture.md"
        content = doc.read_text(encoding="utf-8")
        assert 'create "Create bearclaw-voice workspace package"' not in content

    def test_bearclaw_voice_pkg_doc_note_header_present(self) -> None:
        """bearclaw-voice-workspace-package.md: note header '>Note: Package renamed...' must be added."""
        doc = ROOT / "docs" / "research" / "bearclaw-voice-workspace-package.md"
        content = doc.read_text(encoding="utf-8")
        assert "> Note: Package renamed to owlbear-voice per v2 convention (#64)." in content

    def test_bearclaw_voice_pkg_doc_title_line1_updated(self) -> None:
        """bearclaw-voice-workspace-package.md: title (line 1) must use Owlbear-Voice not Bearclaw-Voice."""
        doc = ROOT / "docs" / "research" / "bearclaw-voice-workspace-package.md"
        lines = doc.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "# Owlbear-Voice Workspace Package Scaffolding"

    def test_bearclaw_voice_pkg_doc_task_ref_line3_updated(self) -> None:
        """bearclaw-voice-workspace-package.md: owning task ref must say owlbear-voice not bearclaw-voice."""
        doc = ROOT / "docs" / "research" / "bearclaw-voice-workspace-package.md"
        content = doc.read_text(encoding="utf-8")
        assert "Create bearclaw-voice workspace package" not in content

    def test_bearclaw_voice_pkg_doc_python_constraint_updated(self) -> None:
        """bearclaw-voice-workspace-package.md: line 42 python constraint text must use owlbear-voice."""
        doc = ROOT / "docs" / "research" / "bearclaw-voice-workspace-package.md"
        content = doc.read_text(encoding="utf-8")
        # "If bearclaw-voice sets `>=3.12`" should become "If owlbear-voice sets..."
        assert "If bearclaw-voice sets" not in content

    def test_bearclaw_voice_pkg_doc_base_install_line_updated(self) -> None:
        """bearclaw-voice-workspace-package.md: line 48 'bearclaw-voice, but the base install' replaced."""
        doc = ROOT / "docs" / "research" / "bearclaw-voice-workspace-package.md"
        content = doc.read_text(encoding="utf-8")
        assert "bearclaw-voice, but the base install" not in content

    def test_bearclaw_voice_pkg_doc_changes_needed_line_updated(self) -> None:
        """bearclaw-voice-workspace-package.md: line 50 'bearclaw-voice changes are needed' replaced."""
        doc = ROOT / "docs" / "research" / "bearclaw-voice-workspace-package.md"
        content = doc.read_text(encoding="utf-8")
        assert "bearclaw-voice changes are needed" not in content

    def test_bearclaw_voice_pkg_doc_line57_updated(self) -> None:
        """bearclaw-voice-workspace-package.md: line 57 reference 'task #52 use `bearclaw-voice`' replaced."""
        doc = ROOT / "docs" / "research" / "bearclaw-voice-workspace-package.md"
        content = doc.read_text(encoding="utf-8")
        assert "task #52 use `bearclaw-voice`" not in content

    def test_bearclaw_voice_pkg_doc_table_row_updated(self) -> None:
        """bearclaw-voice-workspace-package.md: line 62 table row '`bearclaw-voice` (.50)' replaced."""
        doc = ROOT / "docs" / "research" / "bearclaw-voice-workspace-package.md"
        content = doc.read_text(encoding="utf-8")
        assert "| `bearclaw-voice` (.50) |" not in content

    def test_voice_addon_stt_line96_updated(self) -> None:
        """voice-addon-stt-moonshine.md: line 96 '#52 (bearclaw-voice package)' replaced."""
        doc = ROOT / "docs" / "research" / "voice-addon-stt-moonshine.md"
        content = doc.read_text(encoding="utf-8")
        assert "#52 (bearclaw-voice package)" not in content
        assert "#52 (owlbear-voice package)" in content

    def test_voice_stdio_protocol_line62_subprocess_updated(self) -> None:
        """voice-stdio-protocol.md: line 62 '-m bearclaw_voice' replaced with '-m owlbear_voice'."""
        doc = ROOT / "docs" / "research" / "voice-stdio-protocol.md"
        content = doc.read_text(encoding="utf-8")
        assert '"-m", "bearclaw_voice"' not in content
        assert '"-m", "owlbear_voice"' in content

    def test_voice_stdio_protocol_line96_entry_point_updated(self) -> None:
        """voice-stdio-protocol.md: line 96 entry point 'src/bearclaw_voice/__main__.py' replaced."""
        doc = ROOT / "docs" / "research" / "voice-stdio-protocol.md"
        content = doc.read_text(encoding="utf-8")
        assert "src/bearclaw_voice/__main__.py" not in content
        assert "src/owlbear_voice/__main__.py" in content

    def test_voice_tts_line104_updated(self) -> None:
        """voice-tts-kokoro-pyttsx3.md: line 104 'bearclaw-voice package' replaced with 'owlbear-voice package'."""
        doc = ROOT / "docs" / "research" / "voice-tts-kokoro-pyttsx3.md"
        content = doc.read_text(encoding="utf-8")
        assert "module in the bearclaw-voice package" not in content
        assert "module in the owlbear-voice package" in content

    def test_voice_io_line142_updated(self) -> None:
        """voice-io.md: line 142 'bearclaw voice' CLI subcommand replaced with 'owlbear voice'."""
        doc = ROOT / "docs" / "research" / "voice-io.md"
        content = doc.read_text(encoding="utf-8")
        assert "`bearclaw voice` CLI subcommand" not in content
        assert "`owlbear voice` CLI subcommand" in content


class TestFromAC_SourcesDocRenames:
    """AC: docs/sources/overview.md section header rename."""

    def test_sources_section_header_updated(self) -> None:
        """docs/sources/overview.md: 'Bearclaw-Voice Package Scaffolding Research' section header removed."""
        doc = ROOT / "docs" / "sources" / "overview.md"
        content = doc.read_text(encoding="utf-8")
        assert "## Bearclaw-Voice Package Scaffolding Research (Task #52)" not in content

    def test_sources_section_header_owlbear(self) -> None:
        """docs/sources/overview.md: 'Owlbear-Voice Package Scaffolding Research' section header present."""
        doc = ROOT / "docs" / "sources" / "overview.md"
        content = doc.read_text(encoding="utf-8")
        assert "## Owlbear-Voice Package Scaffolding Research (Task #52)" in content


class TestFromAC_CompletenessCheck:
    """AC: zero remaining bearclaw-voice / bearclaw_voice / 'bearclaw voice' refs."""

    _PATTERN = re.compile(r"bearclaw[-_]voice|bearclaw voice", re.IGNORECASE)
    # Filename of the historical research doc that is NOT renamed (kept as cross-reference)
    _UNCHANGED_FILENAME = "bearclaw-voice-workspace-package.md"

    def test_no_bearclaw_voice_in_kanban_tasks(self) -> None:
        """Zero bearclaw-voice refs in kanban/tasks/ (excluding task #64's own body)."""
        tasks_dir = ROOT / "kanban" / "tasks"
        violators: list[tuple[str, int, str]] = []
        for task_file in sorted(tasks_dir.glob("*.md")):
            if task_file.name.startswith("064-"):
                continue  # AC explicitly excludes task #64's own body history
            content = task_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if self._PATTERN.search(line):
                    violators.append((task_file.name, lineno, line.strip()))
        assert violators == [], f"Remaining bearclaw-voice refs in kanban/tasks/: {violators}"

    def test_no_bearclaw_voice_in_research_docs(self) -> None:
        """Zero bearclaw-voice refs in docs/research/ (excluding cli-split.md and lines that are file-path references to the unchanged filename)."""
        research_dir = ROOT / "docs" / "research"
        violators: list[tuple[str, int, str]] = []
        for doc_file in sorted(research_dir.glob("*.md")):
            if doc_file.name == "cli-split.md":
                continue  # AC: cli-split.md is v1 CLI scope, explicitly excluded
            content = doc_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if self._PATTERN.search(line):
                    # Allow lines that contain only a file-path reference to the
                    # historical doc that is intentionally not renamed
                    if self._UNCHANGED_FILENAME in line:
                        continue
                    violators.append((doc_file.name, lineno, line.strip()))
        assert violators == [], f"Remaining bearclaw-voice refs in docs/research/: {violators}"
