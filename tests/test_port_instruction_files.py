"""Failing tests for task #98: Test: Port instruction files.

Verifies the migration from .github/instructions/ to instructions/ completed
correctly. All tests should FAIL until task #10 (Port instruction files) is done.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
INSTRUCTIONS_DIR = ROOT / "share" / "instructions"

EXPECTED_FILES = [
    "python.instructions.md",
    "agent-common.instructions.md",
    "research-docs.instructions.md",
    "frontend.instructions.md",
]


def _parse_frontmatter(content: str) -> dict[str, str] | None:
    """Extract YAML frontmatter key-value pairs, or None if frontmatter is absent."""
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    result: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip().strip('"')
    return result


# ---------------------------------------------------------------------------
# AC: instructions/ contains the expected files
# ---------------------------------------------------------------------------


class TestFromAC_PortInstructionFiles:
    """Verify migration from .github/instructions/ to instructions/ is complete."""

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_instruction_file_present(self, filename: str) -> None:
        """Each expected instruction file must exist under instructions/."""
        assert (INSTRUCTIONS_DIR / filename).exists(), (
            f"{filename} not found in instructions/ — migration not complete"
        )

    # ---------------------------------------------------------------------------
    # AC: each file has valid YAML frontmatter with applyTo and description fields
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_instruction_file_frontmatter_has_apply_to(self, filename: str) -> None:
        """Each instruction file must declare an applyTo field in YAML frontmatter."""
        path = INSTRUCTIONS_DIR / filename
        assert path.exists(), f"{filename} not found in instructions/"
        fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
        assert fm is not None, f"{filename}: no valid YAML frontmatter block found"
        assert "applyTo" in fm, f"{filename}: frontmatter missing 'applyTo' field"

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_instruction_file_frontmatter_has_description(self, filename: str) -> None:
        """Each instruction file must declare a description field in YAML frontmatter."""
        path = INSTRUCTIONS_DIR / filename
        assert path.exists(), f"{filename} not found in instructions/"
        fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
        assert fm is not None, f"{filename}: no valid YAML frontmatter block found"
        assert "description" in fm, f"{filename}: frontmatter missing 'description' field"

    # ---------------------------------------------------------------------------
    # AC: python.instructions.md must not contain banned legacy references
    # ---------------------------------------------------------------------------

    def test_python_instructions_no_pydanticai(self) -> None:
        """python.instructions.md must not contain the string 'PydanticAI'."""
        path = INSTRUCTIONS_DIR / "python.instructions.md"
        assert path.exists(), "python.instructions.md not found in instructions/"
        assert "PydanticAI" not in path.read_text(encoding="utf-8"), (
            "python.instructions.md still references 'PydanticAI'"
        )

    def test_python_instructions_no_bearclaw(self) -> None:
        """python.instructions.md must not contain the string 'BearClaw'."""
        path = INSTRUCTIONS_DIR / "python.instructions.md"
        assert path.exists(), "python.instructions.md not found in instructions/"
        assert "BearClaw" not in path.read_text(encoding="utf-8"), (
            "python.instructions.md still references 'BearClaw'"
        )

    def test_python_instructions_no_src_owlbear_path(self) -> None:
        """python.instructions.md must not contain the string 'src/owlbear/'."""
        path = INSTRUCTIONS_DIR / "python.instructions.md"
        assert path.exists(), "python.instructions.md not found in instructions/"
        assert "src/owlbear/" not in path.read_text(encoding="utf-8"), (
            "python.instructions.md still references 'src/owlbear/'"
        )

    # ---------------------------------------------------------------------------
    # AC: .github/instructions/ directory must be removed after migration
    # ---------------------------------------------------------------------------

    def test_github_instructions_dir_removed(self) -> None:
        """.github/instructions/ must not exist after the migration."""
        assert not (ROOT / ".github" / "instructions").is_dir(), (
            ".github/instructions/ still exists — migration not complete"
        )

    # ---------------------------------------------------------------------------
    # AC: .vscode/settings.json must not list .github/instructions
    # ---------------------------------------------------------------------------

    def test_vscode_settings_no_github_instructions_path(self) -> None:
        """.vscode/settings.json chat.instructionsFilesLocations must exclude .github/instructions."""
        settings_path = ROOT / ".vscode" / "settings.json"
        assert settings_path.exists(), ".vscode/settings.json not found"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        locations = settings.get("chat.instructionsFilesLocations", {})
        if isinstance(locations, dict):
            assert ".github/instructions" not in locations, (
                ".github/instructions still present in chat.instructionsFilesLocations"
            )
        else:
            assert not any(".github/instructions" in str(loc) for loc in locations), (
                ".github/instructions still listed in chat.instructionsFilesLocations"
            )

    # ---------------------------------------------------------------------------
    # AC6: .github/copilot-instructions.md must still exist after migration
    # ---------------------------------------------------------------------------

    def test_copilot_instructions_still_exists(self) -> None:
        """.github/copilot-instructions.md must not be removed during the migration."""
        assert (ROOT / ".github" / "copilot-instructions.md").exists(), (
            ".github/copilot-instructions.md was removed during migration — it must be preserved"
        )
