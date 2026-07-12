"""Static contract tests for ideation-overhaul implementation (#1040).

These tests intentionally verify repo-visible contract surfaces rather than
runtime agent behavior. The goal is to get the ideation overhaul to a
code-done state in owlbear-dev before any live validation on the main-
consuming runtime.

AC coverage in static form:
  - phase split exists and is documented
  - shared interaction contract is explicit
  - early challengers exist with bounded, model-free contracts
  - no ideation surface reintroduces working-log/checkpoint conventions
  - blackboard docs preserve the multi-file contract
"""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).parent.parent


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _ideation_agent_files() -> list[Path]:
    """Return all ideation-*.agent.md files via glob with a min-count guard."""
    files = sorted(_REPO_ROOT.glob("share/agents/ideation-*.agent.md"))
    assert len(files) >= 11, f"Expected >= 11 ideation agent files, got {len(files)}"
    return files


def _ideation_surface_files() -> list[Path]:
    """Return the full ideation surface: agents + skills + briefs README."""
    agents = sorted(_REPO_ROOT.glob("share/agents/ideation-*.agent.md"))
    files = [
        *agents,
        _REPO_ROOT / "share/skills/h-ideation/SKILL.md",
        _REPO_ROOT / "share/skills/w-ideation-discovery/SKILL.md",
        _REPO_ROOT / "share/skills/w-ideation-mediation/SKILL.md",
        _REPO_ROOT / "share/skills/h-ideation-panel/SKILL.md",
        _REPO_ROOT / ".owlbear/briefs/README.md",
    ]
    assert len(files) >= 16, f"Expected >= 16 ideation surface files, got {len(files)}"
    return files


class TestFromAC_IdeationFilesExist:
    """Static existence checks for the ideation phase split and early challengers."""

    def test_phase_split_files_exist(self) -> None:
        required = [
            "share/skills/h-ideation/SKILL.md",
            "share/skills/w-ideation-discovery/SKILL.md",
            "share/skills/w-ideation-mediation/SKILL.md",
            "share/skills/h-ideation-panel/SKILL.md",
            "share/agents/ideation-discoverer.agent.md",
            "share/agents/ideation-mediator.agent.md",
            "share/agents/ideation-firstprinciples.agent.md",
            "share/agents/ideation-simplifier.agent.md",
            "share/agents/ideation-outsider.agent.md",
            "share/agents/ideation-pragmatist.agent.md",
            "share/agents/ideation-critic.agent.md",
            "share/agents/ideation-architect.agent.md",
            "share/agents/ideation-data.agent.md",
            "share/agents/ideation-enduser.agent.md",
            "share/agents/ideation-security.agent.md",
        ]
        missing = [path for path in required if not (_REPO_ROOT / path).exists()]
        assert not missing, f"Missing ideation-overhaul files: {missing}"


class TestFromAC_SharedWorkflowContract:
    """Shared workflow skill exposes the cross-phase rules explicitly."""

    def test_w_ideation_documents_interaction_modes(self) -> None:
        text = _read("share/skills/h-ideation/SKILL.md")
        for needle in [
            "## Shared Interaction Contract",
            "### Investigative Turns",
            "### Synthesis Turns",
            "### Decision Turns",
            "structured context header",
            "anchor-recall",
        ]:
            assert needle in text, f"w-ideation missing interaction-contract text: {needle}"

    def test_w_ideation_documents_validation_disciplines(self) -> None:
        """Validation disciplines live in their respective phase skills."""
        discovery = _read("share/skills/w-ideation-discovery/SKILL.md")
        assert "## Conditional Denoise" in discovery, "Discovery skill missing Conditional Denoise section"
        mediation = _read("share/skills/w-ideation-mediation/SKILL.md")
        for needle in [
            "## Critic Validation (O15)",
            "nonsense",
            "minor",
            "material",
            "## Disclosure Ladder",
            "Never hide decision-critical detail behind a file reference alone",
        ]:
            assert needle in mediation, f"Mediation skill missing validation discipline: {needle}"

    def test_discovery_skill_keeps_freeform_discovery_and_explicit_handoff(
        self,
    ) -> None:
        text = _read("share/skills/w-ideation-discovery/SKILL.md")
        for needle in [
            "freeform",
            "@ideation-mediator",
            "existing-feature/refactor",
        ]:
            assert needle in text, f"Discovery skill missing required contract text: {needle}"
        # Interaction turn shapes live in the shared w-ideation handbook
        shared = _read("share/skills/h-ideation/SKILL.md")
        for needle in [
            "### Investigative Turns",
            "### Synthesis Turns",
            "### Decision Turns",
            "structured context header",
            "anchor-recall",
        ]:
            assert needle in shared, f"Shared handbook missing interaction contract text: {needle}"

    def test_mediation_skill_keeps_o15_disclosure_and_decision_shape(self) -> None:
        text = _read("share/skills/w-ideation-mediation/SKILL.md")
        for needle in [
            "Apply O15 to every Critic pass.",
            "Do not bulk-accept Critic output.",
            "Default Summary",
            "Concrete Specifics",
            "Inline Verbatim Evidence",
        ]:
            assert needle in text, f"Mediation skill missing required contract text: {needle}"

    def test_decision_entry_template_is_visible_in_workflow_surface(self) -> None:
        targets = [
            ".owlbear/briefs/README.md",
            "share/skills/h-ideation/SKILL.md",
        ]
        for path in targets:
            text = _read(path)
            for needle in [
                "Decision Entry Template",
                "## D{N} — {YYYY-MM-DD HH:MM} — {Topic}",
                "**Status quo:** ...",
                "**Decision to make:** ...",
                "**Rejected:**",
            ]:
                assert needle in text, f"Decision template missing from {path}: {needle}"

    def test_decision_entry_template_has_full_field_set(self) -> None:
        targets = [
            ".owlbear/briefs/README.md",
            "share/skills/h-ideation/SKILL.md",
        ]
        for path in targets:
            text = _read(path)
            for needle in [
                "**Options considered:**",
                "**Chosen:**",
                "**Source inputs (when relevant):**",
            ]:
                assert needle in text, f"Decision template missing field in {path}: {needle}"


class TestFromAC_ExplicitShapingHandoff:
    """Approved Briefs enter a separate interactive shaping session."""

    def test_mediator_cannot_mutate_kanban_or_dispatch_shaper(self) -> None:
        text = _read("share/agents/ideation-mediator.agent.md")
        assert "ob-kanban/" not in text
        assert "  - shaper" not in text
        assert "do not create Kanban tasks or invoke shaper" in text

    def test_mediation_handoff_names_brief_and_shape_command(self) -> None:
        workflow = _read("share/skills/w-ideation-mediation/SKILL.md")
        prompt = _read("share/prompts/ideation-mediate.prompt.md")
        for needle in ["approved Brief path", "/shape", "Do not create Kanban tasks"]:
            assert needle in workflow, f"Mediation workflow missing explicit handoff contract: {needle}"
        assert "no Kanban task is created and shaper is not dispatched" in prompt

    def test_shape_prompt_accepts_approved_brief(self) -> None:
        text = _read("share/prompts/shape.prompt.md")
        for needle in [
            "approved `brief.md` path",
            "Brief-readiness gate",
            "contract authority guard",
            "product invariant map",
        ]:
            assert needle in text, f"Shape prompt missing approved-Brief contract: {needle}"


class TestFromAC_ShapeGroundingContracts:
    """Shaping records authority, invariant ownership, and normal-path proof."""

    def test_decomposition_requires_readiness_authority_and_invariant_map(self) -> None:
        text = _read("share/skills/w-task-decomposition/SKILL.md")
        for needle in [
            "### Brief Readiness Gate",
            "## Step 1b — Source And Contract Authority Guard",
            "### Product Invariant Map",
            "Every invariant has exactly one owner",
            "Prefer roughly 3",
            "outcome-cohesive tasks",
        ]:
            assert needle in text, f"Task decomposition missing grounding contract: {needle}"

    def test_ac_and_pipeline_proof_cannot_replace_claimed_boundary(self) -> None:
        ac_quality = _read("share/skills/h-ac-quality/SKILL.md")
        protocol = _read("share/skills/r-pipeline-protocol/SKILL.md")
        assert "### B4 - Boundary-Valid Proof" in ac_quality
        assert "may replace only a layer below the boundary being proved" in ac_quality
        assert "must not replace the command, endpoint, workflow" in protocol
        assert "A SHA without tied proof is not closure evidence" in protocol

    def test_pipeline_roles_enforce_authority_and_aggregate_proof(self) -> None:
        builder = _read("share/agents/builder.agent.md")
        verifier = _read("share/agents/verifier.agent.md")
        collector = _read("share/agents/collector.agent.md")
        challenger = _read("share/agents/shaper-challenger.agent.md")
        assert "Reject canonical-source contradictions" in builder
        assert "Verify named authorities and the claimed boundary" in verifier
        assert "Require SHA-linked aggregate proof" in collector
        assert "product invariant" in challenger
        assert "no owning task" in challenger


class TestFromAC_AgentContracts:
    """Agent prompts keep narrow file contracts and avoid model-string coupling."""

    def test_role_files_do_not_use_model_field_as_contract(self) -> None:
        offenders = []
        for path in _ideation_agent_files():
            if path.name == "ideation-critic.agent.md":
                continue  # critic is intentionally pinned to a specific model
            if "model:" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(_REPO_ROOT)))
        assert not offenders, f"Model-string contracts still present: {offenders}"

    def test_critic_has_pinned_model(self) -> None:
        text = _read("share/agents/ideation-critic.agent.md")
        assert "model:" in text, "Critic must have a pinned model field for adversarial quality"

    def test_ideation_surfaces_keep_context_and_decisions_contract(self) -> None:
        paired_contract_files = [
            "share/agents/ideation-discoverer.agent.md",
            "share/agents/ideation-mediator.agent.md",
            "share/agents/ideation-firstprinciples.agent.md",
            "share/agents/ideation-simplifier.agent.md",
            "share/agents/ideation-outsider.agent.md",
            "share/agents/ideation-pragmatist.agent.md",
            "share/agents/ideation-architect.agent.md",
            "share/agents/ideation-data.agent.md",
            "share/agents/ideation-enduser.agent.md",
            "share/agents/ideation-security.agent.md",
        ]
        missing = []
        for path in paired_contract_files:
            text = _read(path)
            if "context.md" not in text or "decisions.md" not in text:
                missing.append(path)
        assert not missing, f"Ideation contract missing context/decisions references: {missing}"

    def test_critic_keeps_narrow_context_only_contract(self) -> None:
        text = _read("share/agents/ideation-critic.agent.md")
        assert "context.md" in text, "Critic must keep the context.md engagement snapshot contract"
        assert "decisions.md" not in text, "Critic contract should stay narrow and avoid decisions.md"

    def test_no_working_log_or_checkpoint_contract_reappears(self) -> None:
        offenders = []
        for path in _ideation_surface_files():
            text = path.read_text(encoding="utf-8").lower()
            if "working-log.md" in text or "checkpoint" in text:
                offenders.append(str(path.relative_to(_REPO_ROOT)))
        assert not offenders, f"Deprecated ideation contract terms reappeared: {offenders}"


class TestFromAC_BlackboardDocs:
    """Blackboard docs preserve the multi-file contract and handoff artifacts."""

    def test_briefs_readme_documents_multi_file_blackboard(self) -> None:
        text = _read(".owlbear/briefs/README.md")
        for needle in [
            "context.md",
            "decisions.md",
            "research-notes.md",
            "synthesis-idea-panel.md",
            "## `context.md` scaffold",
            "## `decisions.md` scaffold",
            "Chosen",
            "Rejected",
            "@ideation-mediator",
        ]:
            assert needle in text, f"Brief blackboard docs missing required content: {needle}"


class TestFromAC_GoldenScenarioFixtures:
    """Golden scenario fixtures exist for repo-side ideation-overhaul validation."""

    _ROOT = ".owlbear/briefs/draft-ideation-overhaul-2026-04-20/golden-scenarios"

    def test_golden_scenario_readme_lists_three_named_classes(self) -> None:
        text = _read(f"{self._ROOT}/README.md")
        for needle in [
            "repo-side worked validation fixtures",
            "01-net-new-work",
            "02-existing-feature-refactor",
            "03-overscoped-request",
            "not runtime transcripts",
            "Live validation on the main-consuming runtime is still required",
        ]:
            assert needle in text, f"Golden-scenario README missing: {needle}"

    def test_each_scenario_has_core_artifacts(self) -> None:
        required = [
            f"{self._ROOT}/01-net-new-work/context.md",
            f"{self._ROOT}/01-net-new-work/decisions.md",
            f"{self._ROOT}/01-net-new-work/research-notes.md",
            f"{self._ROOT}/02-existing-feature-refactor/context.md",
            f"{self._ROOT}/02-existing-feature-refactor/decisions.md",
            f"{self._ROOT}/02-existing-feature-refactor/research-notes.md",
            f"{self._ROOT}/03-overscoped-request/context.md",
            f"{self._ROOT}/03-overscoped-request/decisions.md",
            f"{self._ROOT}/03-overscoped-request/research-notes.md",
        ]
        missing = [path for path in required if not (_REPO_ROOT / path).exists()]
        assert not missing, f"Missing golden-scenario core artifacts: {missing}"

    def test_phase_handoff_and_project_type_are_recorded(self) -> None:
        net_new = _read(f"{self._ROOT}/01-net-new-work/decisions.md")
        refactor = _read(f"{self._ROOT}/02-existing-feature-refactor/decisions.md")
        assert "@ideation-mediator" in net_new
        assert "context.md, `decisions.md`, and `research-notes.md`".replace("`", "") not in net_new
        for needle in ["net-new", "existing-feature/refactor"]:
            assert needle in (net_new + refactor), f"Project type missing from golden scenarios: {needle}"

    def test_overscoped_scenario_records_scope_reduction_and_o15(self) -> None:
        decisions = _read(f"{self._ROOT}/03-overscoped-request/decisions.md")
        for needle in [
            "split the work",
            "Material findings:",
            "Minor findings (grouped):",
            "Nonsense findings:",
        ]:
            assert needle in decisions, f"Overscoped scenario missing required evidence: {needle}"

    def test_end_to_end_scenario_has_human_review_and_phase_two_outputs(self) -> None:
        readme = _read(f"{self._ROOT}/README.md")
        synthesis = _read(f"{self._ROOT}/02-existing-feature-refactor/synthesis.md")
        brief = _read(f"{self._ROOT}/02-existing-feature-refactor/brief.md")
        assert "Human review was applied" in readme
        assert "## Recommendation" in synthesis
        assert "## Proposal" in brief

    def test_golden_scenario_readme_names_class_labels(self) -> None:
        text = _read(f"{self._ROOT}/README.md")
        for label in [
            "net-new work",
            "existing-feature/refactor",
            "overscoped request",
        ]:
            assert label in text, f"Golden-scenario README missing class label: {label}"

    def test_overscoped_scenario_has_conditional_denoise_artifact(self) -> None:
        path = f"{self._ROOT}/03-overscoped-request/synthesis-idea-panel.md"
        assert (_REPO_ROOT / path).exists(), f"Missing conditional-denoise artifact for overscoped scenario: {path}"
        text = _read(path)
        for marker in ["## Distinct Claims", "## Divergences"]:
            assert marker in text, f"synthesis-idea-panel.md missing structural section: {marker}"

    def test_overscoped_scenario_has_phase_two_outputs(self) -> None:
        synthesis = _read(f"{self._ROOT}/03-overscoped-request/synthesis.md")
        brief = _read(f"{self._ROOT}/03-overscoped-request/brief.md")
        assert "## Recommendation" in synthesis, "03-overscoped-request/synthesis.md missing ## Recommendation"
        assert "## Proposal" in brief, "03-overscoped-request/brief.md missing ## Proposal"

    def test_scenario_briefs_carry_runtime_disclaimer(self) -> None:
        scenarios = [
            "02-existing-feature-refactor",
            "03-overscoped-request",
        ]
        for scenario in scenarios:
            text = _read(f"{self._ROOT}/{scenario}/brief.md")
            assert "main-consuming" in text, f"{scenario}/brief.md missing runtime-validation disclaimer"


class TestFromAC_EarlyChallengeLane:
    """Early challenge lane selection, critic exclusion, and bounded-output rules."""

    def test_early_lane_always_invokes_simplifier_and_firstprinciples(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert "Always invoke `ideation-simplifier` and `ideation-firstprinciples`" in text, (
            "Panel handbook missing the default-roster 'always invoke' rule for simplifier and firstprinciples"
        )

    def test_outsider_is_conditional_not_default(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert "Invoke `ideation-outsider` only when the discovery agent sees tunnel vision" in text, (
            "Panel handbook missing the conditional-outsider selection rule"
        )

    def test_critic_excluded_from_default_early_lane(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert "Do not use `ideation-critic` as the default early challenger." in text, (
            "Panel handbook missing the explicit critic-exclusion rule for the early lane"
        )

    def test_early_challenger_outputs_are_bounded(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert "Outputs must be short and bounded." in text, (
            "Panel handbook missing the bounded-output rule for early challengers"
        )

    def test_discovery_always_invokes_simplifier_and_firstprinciples(self) -> None:
        text = _read("share/skills/w-ideation-discovery/SKILL.md")
        assert "always: `ideation-simplifier`" in text, (
            "Discovery skill missing mandatory simplifier invocation in early challenge lane"
        )
        assert "always: `ideation-firstprinciples`" in text, (
            "Discovery skill missing mandatory firstprinciples invocation in early challenge lane"
        )

    def test_discovery_outsider_is_conditional(self) -> None:
        text = _read("share/skills/w-ideation-discovery/SKILL.md")
        assert "conditional: `ideation-outsider`" in text, (
            "Discovery skill must mark outsider invocation as conditional, not mandatory"
        )

    def test_discovery_early_challenger_output_bounded(self) -> None:
        text = _read("share/skills/w-ideation-discovery/SKILL.md")
        assert "Keep early challenger output bounded" in text, (
            "Discovery skill missing scope-limit rule for early challenger output — "
            "challenger lane must be framing/scope-control, not a second design panel"
        )


class TestFromAC_CriticExclusion:
    """Critic is absent from the discovery phase roster; its exclusion is explicit in the panel handbook."""

    def test_critic_exclusion_dual_surface(self) -> None:
        # Discovery uses a positive roster (simplifier, firstprinciples, outsider)
        # that implicitly excludes ideation-critic. The explicit exclusion clause lives
        # in h-ideation-panel/SKILL.md (covered by test_critic_excluded_from_default_early_lane).
        text = _read("share/skills/w-ideation-discovery/SKILL.md")
        assert "ideation-critic" not in text, (
            "ideation-critic must not appear in w-ideation-discovery/SKILL.md — "
            "critic is excluded from Phase 1 via positive-roster specification; "
            "the explicit exclusion clause belongs in h-ideation-panel/SKILL.md"
        )


import pytest  # noqa: E402


_PANELIST_AGENTS = [
    ("architect", "share/agents/ideation-architect.agent.md"),
    ("data", "share/agents/ideation-data.agent.md"),
    ("enduser", "share/agents/ideation-enduser.agent.md"),
    ("security", "share/agents/ideation-security.agent.md"),
]


class TestFromAC_ProposalRoundContracts:
    """M3.5 proposal-round contract surfaces — panel handbook, agent files, mediation skill."""

    # --- C1: Propose Mode section in panel handbook ---

    def test_panel_handbook_has_propose_mode_section(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert "### Propose Mode (M3.5 Path)" in text, "Panel handbook missing '### Propose Mode (M3.5 Path)' section"

    def test_propose_mode_requires_five_proposal_sections(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        for section in [
            "Design Summary",
            "Key Structural Choices",
            "Trade-offs",
            "Domain Rationale",
            "Confidence",
        ]:
            assert section in text, f"Panel handbook Propose Mode missing required proposal section: {section}"

    def test_propose_mode_names_stances_proposal_output(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert "stances/{name}-proposal.md" in text, (
            "Panel handbook Propose Mode missing 'stances/{name}-proposal.md' output reference"
        )

    # --- C2: Critic skip in propose mode ---

    def test_propose_mode_skips_critic_loop(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert "In propose mode, panelists skip the embedded Critic loop" in text, (
            "Panel handbook missing Critic-skip rule for propose mode"
        )

    # --- C3: Pragmatist mode=compare in panel handbook ---

    def test_pragmatist_has_compare_mode(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert "### `mode=compare`" in text, "Panel handbook missing '### `mode=compare`' section for pragmatist"

    def test_compare_mode_defines_output_structure(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        for needle in [
            "divergence-only comparison matrix",
            "common ground summary",
            "open questions",
        ]:
            assert needle in text, f"Panel handbook mode=compare missing output-structure element: {needle}"

    def test_compare_mode_reads_proposal_files(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert "reads `stances/*-proposal.md`" in text, (
            "Panel handbook mode=compare missing 'reads `stances/*-proposal.md`' contract"
        )

    # --- C4: Step 1.5 gate in mediation skill ---

    def test_mediation_has_m35_gate(self) -> None:
        text = _read("share/skills/w-ideation-mediation/SKILL.md")
        assert "## Step 1.5" in text, "Mediation skill missing '## Step 1.5' gate section"

    def test_m35_gate_requires_two_viable_approaches(self) -> None:
        text = _read("share/skills/w-ideation-mediation/SKILL.md")
        assert "at least two viable approaches and no dominant option" in text, (
            "Mediation skill Step 1.5 gate missing two-viable-approaches condition"
        )

    # --- C5: Mutual exclusivity of M3.5 and Step 2 ---

    def test_m35_and_step2_mutually_exclusive(self) -> None:
        text = _read("share/skills/w-ideation-mediation/SKILL.md")
        assert "M3.5 and Step 2 are mutually exclusive" in text, (
            "Mediation skill missing explicit M3.5 / Step 2 mutual-exclusivity rule"
        )

    # --- C6: PROPOSE mode in each of the four panelist agent files ---

    @pytest.mark.parametrize(("name", "path"), _PANELIST_AGENTS)
    def test_panelist_agents_support_propose_mode(self, name: str, path: str) -> None:
        text = _read(path)
        assert "PROPOSE mode" in text, f"{path} missing PROPOSE mode contract"
        assert f"stances/{name}-proposal.md" in text, f"{path} missing stances/{name}-proposal.md output reference"
        assert "skip embedded Critic" in text, f"{path} missing Critic-skip rule for PROPOSE mode"

    # --- C7: Pragmatist agent has mode=compare ---

    def test_pragmatist_agent_has_compare_mode(self) -> None:
        text = _read("share/agents/ideation-pragmatist.agent.md")
        assert "mode=compare" in text, "ideation-pragmatist.agent.md missing mode=compare contract"
        assert "stances/*-proposal.md" in text, (
            "ideation-pragmatist.agent.md missing stances/*-proposal.md reference for mode=compare"
        )

    def test_pragmatist_agent_compare_output_has_required_sections(self) -> None:
        text = _read("share/agents/ideation-pragmatist.agent.md")
        for section in ["Divergence Matrix", "Common Ground", "Open Questions"]:
            assert section in text, f"ideation-pragmatist.agent.md mode=compare missing output section: {section}"

    # --- Blackboard proposal artifacts in briefs README ---

    def test_blackboard_documents_proposal_artifacts(self) -> None:
        text = _read(".owlbear/briefs/README.md")
        for needle in [
            "architect-proposal.md",
            "data-proposal.md",
            "enduser-proposal.md",
            "security-proposal.md",
        ]:
            assert needle in text, f"Briefs README missing blackboard proposal artifact: {needle}"

    def test_blackboard_marks_proposal_files_as_conditional(self) -> None:
        text = _read(".owlbear/briefs/README.md")
        assert "*-proposal.md" in text, "Briefs README missing '*-proposal.md' wildcard reference for M3.5 artifacts"
        assert "optional" in text, "Briefs README must mark proposal files as optional (M3.5-triggered)"

    def test_blackboard_proposal_conditionality_tied_to_m35_round(self) -> None:
        """Tighter proof: the specific M3.5 conditionality sentence must exist.

        The sentence uniquely combines *-proposal.md, optional, and 'conditional
        M3.5 proposal round' — so it cannot be satisfied by unrelated Optional
        references elsewhere in the file.
        """
        text = _read(".owlbear/briefs/README.md")
        assert "conditional M3.5 proposal round" in text, (
            "Briefs README must state that *-proposal.md files appear only when the "
            "mediator runs the 'conditional M3.5 proposal round' (specific phrase required)"
        )
        # Combined assertion: the exact conditionality sentence must tie the wildcard
        # to the M3.5 round — not merely have both words somewhere in the document.
        assert "*-proposal.md`) are optional and appear only when" in text, (
            "Briefs README must contain the exact M3.5 conditionality statement: "
            "'*-proposal.md`) are optional and appear only when'"
        )
