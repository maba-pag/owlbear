"""Static contract tests for DR skill replacement — P2-01 (#1186).

Validates that the scribe agent and w-decision-routing skill have been
replaced by the h-decision-requests skill, and that all cross-references
in agent and skill files have been updated accordingly.

AC coverage (all static structural assertions):
  AC1 — h-decision-requests/SKILL.md exists with valid YAML frontmatter
  AC2 — scribe.agent.md does NOT exist
  AC3 — w-decision-routing/SKILL.md does NOT exist
  AC4 — no "scribe" references in any share/agents/*.agent.md file
  AC5 — r-pipeline-protocol/SKILL.md contains "create_dr", not "scribe"
  AC6 — w-orchestration/SKILL.md has no "dispatch scribe" or scribe dispatch
"""

from __future__ import annotations

import re
import yaml

from pathlib import Path


_REPO_ROOT = Path(__file__).parent.parent


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _parse_frontmatter(text: str) -> dict:
    """Extract and parse YAML frontmatter from a --- delimited file."""
    parts = text.split("---", maxsplit=2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


class TestFromAC_DRSkillReplacement:
    """Static structural assertions validating P2-01 deliverables."""

    # AC1 — h-decision-requests/SKILL.md exists with valid YAML frontmatter

    def test_h_decision_requests_skill_exists(self) -> None:
        """share/skills/h-decision-requests/SKILL.md must exist."""
        skill_path = _REPO_ROOT / "share/skills/h-decision-requests/SKILL.md"
        assert skill_path.exists(), (
            f"Expected {skill_path} to exist but it does not. Create h-decision-requests skill as part of P2."
        )

    def test_h_decision_requests_skill_has_valid_frontmatter(self) -> None:
        """h-decision-requests/SKILL.md must have name and description frontmatter."""
        skill_path = _REPO_ROOT / "share/skills/h-decision-requests/SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        assert "name" in fm, f"h-decision-requests/SKILL.md frontmatter missing 'name' field. Parsed frontmatter: {fm}"
        assert "description" in fm, (
            f"h-decision-requests/SKILL.md frontmatter missing 'description' field. Parsed frontmatter: {fm}"
        )
        assert fm["name"], "h-decision-requests/SKILL.md 'name' field must be non-empty"
        assert fm["description"], "h-decision-requests/SKILL.md 'description' field must be non-empty"

    # AC2 — scribe.agent.md does NOT exist

    def test_scribe_agent_does_not_exist(self) -> None:
        """share/agents/scribe.agent.md must be deleted in P2."""
        scribe_path = _REPO_ROOT / "share/agents/scribe.agent.md"
        assert not scribe_path.exists(), f"{scribe_path} still exists. Delete scribe.agent.md as part of P2."

    # AC3 — w-decision-routing/SKILL.md does NOT exist

    def test_w_decision_routing_skill_does_not_exist(self) -> None:
        """share/skills/w-decision-routing/SKILL.md must be deleted in P2."""
        routing_path = _REPO_ROOT / "share/skills/w-decision-routing/SKILL.md"
        assert not routing_path.exists(), f"{routing_path} still exists. Delete w-decision-routing skill as part of P2."

    # AC4 — no "scribe" references in any share/agents/*.agent.md

    def test_no_scribe_references_in_agent_files(self) -> None:
        """No agent file may reference 'scribe' in its agents: list or body."""
        agent_files = sorted(_REPO_ROOT.glob("share/agents/*.agent.md"))
        assert agent_files, "No agent files found — check repo structure"
        _scribe_word = re.compile(r"\bscribe\b", re.IGNORECASE)
        offenders: list[str] = []
        for agent_file in agent_files:
            text = agent_file.read_text(encoding="utf-8")
            if _scribe_word.search(text):
                # Collect the specific lines for useful diagnostics
                lines = [
                    f"  line {i + 1}: {line.rstrip()}"
                    for i, line in enumerate(text.splitlines())
                    if _scribe_word.search(line)
                ]
                offenders.append(f"{agent_file.name}:\n" + "\n".join(lines))
        assert not offenders, "Found 'scribe' references in agent files (must be removed in P2):\n" + "\n".join(
            offenders
        )

    # AC5 — r-pipeline-protocol/SKILL.md contains "create_dr", not "scribe"

    def test_r_pipeline_protocol_contains_create_dr(self) -> None:
        """r-pipeline-protocol/SKILL.md must reference the new create_dr pattern."""
        text = _read("share/skills/r-pipeline-protocol/SKILL.md")
        assert "create_dr" in text, (
            "r-pipeline-protocol/SKILL.md must contain 'create_dr' — "
            "update DR creation instructions to use the new h-decision-requests pattern."
        )

    def test_r_pipeline_protocol_does_not_contain_scribe(self) -> None:
        """r-pipeline-protocol/SKILL.md must not reference the deprecated scribe agent."""
        text = _read("share/skills/r-pipeline-protocol/SKILL.md")
        _scribe_word = re.compile(r"\bscribe\b", re.IGNORECASE)
        assert not _scribe_word.search(text), (
            "r-pipeline-protocol/SKILL.md still contains 'scribe' references. "
            "Replace all scribe references with the h-decision-requests pattern."
        )

    # AC6 — w-orchestration/SKILL.md has no "dispatch scribe" or scribe dispatch pattern

    def test_w_orchestration_does_not_reference_scribe(self) -> None:
        """w-orchestration/SKILL.md must contain no mention of the deprecated scribe agent."""
        text = _read("share/skills/w-orchestration/SKILL.md")
        _scribe_word = re.compile(r"\bscribe\b", re.IGNORECASE)
        assert not _scribe_word.search(text), (
            "w-orchestration/SKILL.md still references 'scribe'. "
            "Remove all scribe dispatch sections and prose references as part of P2."
        )

    def test_w_orchestration_does_not_contain_scribe_subagent_dispatch(self) -> None:
        """w-orchestration/SKILL.md must not contain runSubagent('scribe', ...) dispatch."""
        text = _read("share/skills/w-orchestration/SKILL.md")
        assert 'runSubagent("scribe"' not in text, (
            'w-orchestration/SKILL.md contains runSubagent("scribe", ...) — '
            "remove the scribe subagent dispatch block as part of P2."
        )
