"""Regression tests for intentional agent loading of shared project authorities."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENTS_ROOT = _REPO_ROOT / "share/agents"
_SHARE_ROOT = _REPO_ROOT / "share"

_EXPECTED_REQUIRED_READERS = {
    "h-codebase-orientation": {"builder", "verifier"},
    "h-module-design": {"ideation-architect", "shaper-challenger"},
    "r-workspace-governance": {
        "builder",
        "collector",
        "ideation-discoverer",
        "ideation-mediator",
        "shaper",
        "verifier",
    },
}


def _required_skills(path: Path) -> set[str]:
    content = path.read_text(encoding="utf-8")
    match = re.search(r"<required_reading>(.*?)</required_reading>", content, re.DOTALL)
    assert match is not None, f"Missing required_reading in {path.name}"
    return set(re.findall(r"`([hwr]-[a-z0-9-]+)`", match.group(1)))


def test_authorities_have_intentional_regular_agent_readers() -> None:
    """Regular loading stays limited to roles that need an authority in nearly every session."""
    actual = {skill: set() for skill in _EXPECTED_REQUIRED_READERS}
    for agent_path in _AGENTS_ROOT.glob("*.agent.md"):
        for skill in _required_skills(agent_path):
            if skill in actual:
                actual[skill].add(agent_path.name.removesuffix(".agent.md"))

    assert actual == _EXPECTED_REQUIRED_READERS


def test_on_demand_authority_paths_are_declared() -> None:
    """Roles with situational needs can discover the authority without regular loading."""
    orientation = (_REPO_ROOT / "share/skills/h-codebase-orientation/SKILL.md").read_text(encoding="utf-8")
    protocol = (_REPO_ROOT / "share/skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")
    discovery = (_REPO_ROOT / "share/skills/w-ideation-discovery/SKILL.md").read_text(encoding="utf-8")
    mediation = (_REPO_ROOT / "share/skills/w-ideation-mediation/SKILL.md").read_text(encoding="utf-8")
    spec_shaping = (_REPO_ROOT / "share/skills/w-spec-shaping/SKILL.md").read_text(encoding="utf-8")
    task_repair = (_REPO_ROOT / "share/skills/w-task-repair/SKILL.md").read_text(encoding="utf-8")

    assert "`h-module-design`" in orientation
    assert "`r-workspace-governance`" in protocol
    assert "`h-codebase-orientation`" in discovery
    assert "`h-codebase-orientation`" in mediation
    assert "`h-codebase-orientation`" in spec_shaping
    assert "`h-module-design`" in spec_shaping
    assert "`h-codebase-orientation`" in task_repair


def test_pipeline_commit_gate_includes_final_task_state() -> None:
    """Pipeline closure commits after end_work and includes archive moves explicitly."""
    governance = (_REPO_ROOT / "share/skills/r-workspace-governance/SKILL.md").read_text(encoding="utf-8")
    protocol = (_REPO_ROOT / "share/skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")

    assert "call `end_work` first" in governance
    assert "Do not return `DONE`, `PASS`, or `ARCHIVED`" in governance
    assert "### After `end_work`" in protocol
    assert "Include the final task record in every pipeline commit" in protocol
    assert "both its former task path and final archive path" in protocol
    assert 'block_reason="COMMIT_FAILED:' in governance
    assert "filesystem block prevents orchestrator" in governance
    assert 'block_reason=""' in governance
    assert re.search(r"archived\s+tasks are already off-board", protocol, re.IGNORECASE)
    assert "### Owned Auto-Staging Recovery" in governance
    assert "git diff --cached --name-status --" in governance
    assert "git reset HEAD --" in governance
    assert "Otherwise apply `COMMIT_FAILED`; do not unstage it" in governance


def test_retired_authority_names_are_absent_from_shared_ecosystem() -> None:
    """Shared consumers use one current name for each authority."""
    retired = {"h-project-orientation", "r-project-standards", "r-architecture-standards"}
    offenders: list[str] = []
    for path in _SHARE_ROOT.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        if any(name in content for name in retired):
            offenders.append(str(path.relative_to(_REPO_ROOT)))

    assert not offenders, f"Retired authority references remain: {offenders}"
