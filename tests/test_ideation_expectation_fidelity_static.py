"""Static contracts for ideation expectation-fidelity rules.

These tests cover the static text/contract surfaces, diagram marker, and golden
scenario for the ideation minimalism-collapse fix. They intentionally avoid live
agent execution; live runtime validation belongs to a separate proof pass.
"""

from __future__ import annotations

import json
from pathlib import Path


_REPO_ROOT = Path(__file__).parent.parent
_GOLDEN_ROOT = ".owlbear/briefs/draft-ideation-overhaul-2026-04-20/golden-scenarios/04-expectation-fidelity"


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text(encoding="utf-8")


class TestExpectationSignalContract:
    """Shared expectation signal and tier-scaled fidelity rules."""

    def test_h_ideation_defines_contrastive_expectation_signal(self) -> None:
        text = _read("share/skills/h-ideation/SKILL.md")
        for needle in [
            "## Expectation Fidelity",
            "planning-summary.md",
            "### Expectation Signal",
            "What are we actually trying to give the user?",
            "What would make it feel worth using?",
            "What can arrive first without pretending it is finished?",
            "What would be technically done but still wrong?",
            "What did the user knowingly give up?",
            "First Useful Step is sequencing, not descoping",
        ]:
            assert needle in text, f"h-ideation missing expectation contract text: {needle}"

    def test_h_ideation_defines_tier_scaled_fidelity_matrix(self) -> None:
        text = _read("share/skills/h-ideation/SKILL.md")
        for needle in [
            "### Tier-Scaled Fidelity Checks",
            "Scratch",
            "0 formal checks",
            "Tool",
            "pre-Brief expectation-fidelity Critic check",
            "Shared",
            "M2 expectation-fidelity Critic check",
            "post-planner expectation-fidelity Critic check",
            "Production",
            "post-planner expectation-fidelity Critic check",
        ]:
            assert needle in text, f"h-ideation missing tier matrix text: {needle}"

    def test_discovery_replaces_minimum_viable_win_with_first_useful_step(self) -> None:
        text = _read("share/skills/w-ideation-discovery/SKILL.md")
        assert "minimum viable win" not in text.lower()
        for needle in [
            "First Useful Step",
            "What are we actually trying to give the user?",
            "What would be technically done but still wrong?",
            "Shared and Production",
            "expectation-fidelity Critic check",
        ]:
            assert needle in text, f"discovery skill missing expectation-fidelity text: {needle}"


class TestExpectationFidelityAgents:
    """Agent surfaces expose the new fidelity checks without adding a new role."""

    def test_discoverer_can_call_critic_conditionally(self) -> None:
        text = _read("share/agents/ideation-discoverer.agent.md")
        for needle in [
            "ideation-critic",
            "conditional expectation-fidelity",
            "may sequence or split expectation, but never silently shrink it",
        ]:
            assert needle in text, f"discoverer missing conditional Critic contract: {needle}"

    def test_critic_has_expectation_fidelity_mode(self) -> None:
        text = _read("share/agents/ideation-critic.agent.md")
        for needle in [
            "expectation-fidelity mode",
            "technically done but still wrong",
            "silent descoping",
            "Do not propose fixes",
        ]:
            assert needle in text, f"Critic missing expectation-fidelity mode text: {needle}"

    def test_simplifier_must_not_force_product_shrinkage(self) -> None:
        text = _read("share/agents/ideation-simplifier.agent.md")
        for needle in [
            "preserve the expectation",
            "recommend sequencing or splitting",
            "strongest expectation-preserving cuts",
            "what remains after any First Useful Step",
            "Do not force a cut",
        ]:
            assert needle in text, f"simplifier missing expectation-preservation rule: {needle}"


class TestMediationAndPipelineGuards:
    """Mediation, planner, and architect keep the Brief from shrinking downstream."""

    def test_mediation_brief_o15_and_m6_rules_exist(self) -> None:
        text = _read("share/skills/w-ideation-mediation/SKILL.md")
        for needle in [
            "wanted, not merely necessary for bare function",
            "No mandatory/recommended tiers",
            "expectation fit",
            "expected-experience coverage",
            "additive-only repair",
            "coverage omissions go back to planner",
            "value or scope trade-offs go back to the user",
        ]:
            assert needle in text, f"mediation skill missing expectation-fidelity rule: {needle}"

    def test_mediator_agent_names_tier_scaled_checks(self) -> None:
        text = _read("share/agents/ideation-mediator.agent.md")
        for needle in [
            "tier-scaled expectation-fidelity checks",
            "M6 is not complete",
            "approved Brief is the binding product promise",
        ]:
            assert needle in text, f"mediator agent missing fidelity rule: {needle}"

    def test_planner_and_architect_do_not_scope_delete_brief_requirements(self) -> None:
        planner = _read("share/skills/w-task-decomposition/SKILL.md")
        architect = _read("share/skills/w-arch-review/SKILL.md")
        assert "sequences or splits Brief requirements but does not delete them" in planner
        assert "KISS/YAGNI applies to implementation shape, not product promise" in architect


class TestIdeationPromptsExposeExpectationFidelity:
    """User-facing prompts advertise the expectation-fidelity behavior."""

    def test_ideation_prompts_name_expectation_fidelity(self) -> None:
        discover = _read("share/prompts/ideation-discover.prompt.md")
        mediate = _read("share/prompts/ideation-mediate.prompt.md")
        assert "Expectation Signal" in discover
        assert "First Useful Step" in discover
        assert "expectation-fidelity" in mediate
        assert "Brief is the binding product promise" in mediate


class TestExpectationFidelityDiagramAndFixture:
    """Stage 2 diagram and golden-scenario coverage."""

    def test_ideation_diagram_names_expectation_fidelity(self) -> None:
        data = json.loads(_read("share/diagrams/ideation.excalidraw"))
        text = " ".join(
            elem.get("text", "") for elem in data.get("elements", []) if isinstance(elem.get("text"), str)
        ).lower()
        for needle in [
            "expectation fidelity",
            "expectation signal",
            "brief binding",
            "first useful step is sequencing",
        ]:
            assert needle in text, f"ideation diagram missing expectation-fidelity text: {needle}"

    def test_golden_expectation_fidelity_scenario_files_exist(self) -> None:
        required = [
            "context.md",
            "decisions.md",
            "research-notes.md",
            "synthesis.md",
            "brief.md",
            "planning-summary.md",
        ]
        missing = [name for name in required if not (_REPO_ROOT / _GOLDEN_ROOT / name).exists()]
        assert not missing, f"Missing expectation-fidelity golden scenario files: {missing}"

    def test_golden_scenario_preserves_expectation_signal(self) -> None:
        context = _read(f"{_GOLDEN_ROOT}/context.md")
        for needle in [
            "What are we actually trying to give the user?",
            "What would make it feel worth using?",
            "What can arrive first without pretending it is finished?",
            "What would be technically done but still wrong?",
            "What did the user knowingly give up?",
        ]:
            assert needle in context, f"golden context missing expectation heading: {needle}"

    def test_golden_scenario_rejects_passable_but_wrong_result(self) -> None:
        decisions = _read(f"{_GOLDEN_ROOT}/decisions.md")
        synthesis = _read(f"{_GOLDEN_ROOT}/synthesis.md")
        combined = decisions + "\n" + synthesis
        for needle in [
            "First Useful Step is not replacement scope",
            "passable-but-wrong version is rejected",
            "M6 uses additive-only repair",
            "The user should see their desired product preserved",
        ]:
            assert needle in combined, f"golden scenario missing anti-minimalism evidence: {needle}"

    def test_golden_brief_and_planning_keep_brief_binding(self) -> None:
        brief = _read(f"{_GOLDEN_ROOT}/brief.md")
        planning = _read(f"{_GOLDEN_ROOT}/planning-summary.md")
        assert "Binding Product Promise" in brief
        assert "Expected Experience" in brief
        assert "First Release Is Not The Promise" in brief
        assert "Passable-But-Wrong Result" in brief
        assert "the workflow is not complete" in brief
        assert "Planner sequences or splits Brief requirements but does not delete them" in brief
        assert "Qualitative Preservation Check" in planning
        assert "Additive-Only Repair Example" in planning
