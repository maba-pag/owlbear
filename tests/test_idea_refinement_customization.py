"""Structural checks for the idea-refinement customization."""

from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_ideate_refines_a_rough_idea_for_the_next_prompt() -> None:
    prompt = _read("share/prompts/ideate.prompt.md")

    for retired_prompt in ("grill-me.prompt.md", "opsx-refine.prompt.md", "prepare.prompt.md"):
        assert not (REPO_ROOT / "share/prompts" / retired_prompt).exists()
    assert "/opsx:propose" in prompt
    assert "w-idea-refinement" in prompt
    assert "Refined Idea Summary" in prompt
    assert 'name: "ideate"' in prompt
    assert len(prompt.splitlines()) < 30


def test_idea_refinement_preserves_grilling_method_without_decision_theater() -> None:
    skill = _read("share/skills/w-idea-refinement/SKILL.md")

    assert not (REPO_ROOT / "share/skills/w-grilling").exists()
    assert not (REPO_ROOT / "share/skills/w-decision-refinement/SKILL.md").exists()
    for required_section in (
        "## When to Use",
        "## Core Method",
        "## Step 3 - Ask the Next Refinement Question",
        "## Proposal-Readiness Gate",
        "## Refined Idea Summary",
        "## Examples",
        "## Known Pitfalls",
    ):
        assert required_section in skill
    assert "Ask one question at a time" in skill
    assert "Recommend an answer" in skill
    assert "Do not invent decisions" in skill
    assert "Preserve the full promise" in skill
    assert "concrete behavior or effect makes the result worth using" in skill
    assert "Accepted exclusions" in skill
    assert "Do not introduce a smaller first delivery" in skill
    assert "First Useful Step" not in skill
    assert "investment tier" not in skill
    assert "Good:" in skill
    assert "Bad:" in skill
    assert "/opsx:" not in skill


def test_active_planning_path_preserves_full_promise_without_tier_gate() -> None:
    paths = (
        "share/skills/w-idea-refinement/SKILL.md",
        "seed/openspec/config.yaml",
        "share/prompts/shape.prompt.md",
        "share/skills/w-task-decomposition/SKILL.md",
        "share/agents/shaper.agent.md",
        "share/agents/shaper-challenger.agent.md",
    )
    active_surface = "\n".join(_read(path) for path in paths)

    assert "investment tier" not in active_surface
    assert "First Useful Step" not in active_surface
    assert "full Product Promise" in active_surface
    assert "explicit user-approved exclusion" in active_surface
    assert "post-shaping Product Promise check" in active_surface


def test_architecture_review_consumes_generic_idea_refinement() -> None:
    prompt = _read("share/prompts/architecture-review.prompt.md")

    assert not (REPO_ROOT / "share/skills/w-architecture-review/SKILL.md").exists()
    for dependency in (
        "h-module-design",
        "h-codebase-orientation",
        "h-visual-output",
        "w-idea-refinement",
    ):
        assert dependency in prompt
    assert "## Step 2 - Explore Friction" in prompt
    assert "## Step 3 - Present Candidates" in prompt
    assert "## Step 4 - Explore the Selected Design" in prompt
    assert "/opsx:propose" in prompt
