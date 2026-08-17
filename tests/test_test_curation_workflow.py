"""Guard the test-curation workflow contract."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).parent.parent
_SKILL = (_ROOT / "share/skills/w-test-curation/SKILL.md").read_text(encoding="utf-8")
_AGENT = (_ROOT / "share/agents/test-curator.agent.md").read_text(encoding="utf-8")


def test_curation_skill_requires_inventory_and_explicit_provenance() -> None:
    assert "uv run test-curation-inventory --json" in _SKILL
    assert "verified" in _SKILL
    assert "unverified" in _SKILL
    assert "missing" in _SKILL
    assert "Mined from #...` as provenance" in _SKILL


def test_curation_skill_distinguishes_negative_contracts_and_mixed_files() -> None:
    assert "### Negative assertions" in _SKILL
    assert "standing negative contract" in _SKILL
    assert "`remove nodes`" in _SKILL
    assert "`mine in place`" in _SKILL
    assert "`skip`" in _SKILL


def test_curation_skill_requires_quality_gates_and_scoped_commit() -> None:
    assert "git diff --check" in _SKILL
    assert "uv run typecheck-cockpit" in _SKILL
    assert "commit-owned" in _SKILL
    assert "git add -A && git commit" not in _SKILL


def test_test_curator_agent_requires_inventory_and_scoped_commit() -> None:
    assert "uv run test-curation-inventory --json" in _AGENT
    assert "commit-owned" in _AGENT
    assert "explicit owned-path list" in _AGENT
    assert "`Mined from` comments" in _AGENT
