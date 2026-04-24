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
    """Return the full ideation surface: agents + ideator + skills + briefs README."""
    agents = sorted(_REPO_ROOT.glob("share/agents/ideation-*.agent.md"))
    files = [
        *agents,
        _REPO_ROOT / "share/agents/ideator.agent.md",
        _REPO_ROOT / "share/skills/w-ideation/SKILL.md",
        _REPO_ROOT / "share/skills/w-ideation-discovery/SKILL.md",
        _REPO_ROOT / "share/skills/w-ideation-mediation/SKILL.md",
        _REPO_ROOT / "share/skills/h-ideation-panel/SKILL.md",
        _REPO_ROOT / ".owlbear/briefs/README.md",
    ]
    assert len(files) >= 17, f"Expected >= 17 ideation surface files, got {len(files)}"
    return files


class TestFromAC_IdeationFilesExist:
    """Static existence checks for the ideation phase split and early challengers."""

    def test_phase_split_files_exist(self) -> None:
        required = [
            "share/skills/w-ideation/SKILL.md",
            "share/skills/w-ideation-discovery/SKILL.md",
            "share/skills/w-ideation-mediation/SKILL.md",
            "share/skills/h-ideation-panel/SKILL.md",
            "share/agents/ideator.agent.md",
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
        text = _read("share/skills/w-ideation/SKILL.md")
        for needle in [
            "## Shared Interaction Contract",
            "### Investigative Turns",
            "### Synthesis Turns",
            "### Decision Turns",
            "structured context header",
            "anchor-recall",
        ]:
            assert needle in text, (
                f"w-ideation missing interaction-contract text: {needle}"
            )

    def test_w_ideation_documents_validation_disciplines(self) -> None:
        text = _read("share/skills/w-ideation/SKILL.md")
        for needle in [
            "### Conditional Denoise",
            "### Critic Validation (O15)",
            "nonsense",
            "minor",
            "material",
            "### Disclosure Ladder",
            "never hide decision-critical detail behind a file path alone",
        ]:
            assert needle in text, f"w-ideation missing validation discipline: {needle}"

    def test_discovery_skill_keeps_freeform_discovery_and_explicit_handoff(
        self,
    ) -> None:
        text = _read("share/skills/w-ideation-discovery/SKILL.md")
        for needle in [
            "## Interaction Modes",
            "### Investigative Turns",
            "Default for M1-M2.",
            "current phase and moment",
            "per-option pro, con, risk, and confidence",
            "@ideation-mediator",
            "existing-feature/refactor",
        ]:
            assert needle in text, (
                f"Discovery skill missing required contract text: {needle}"
            )

    def test_mediation_skill_keeps_o15_disclosure_and_decision_shape(self) -> None:
        text = _read("share/skills/w-ideation-mediation/SKILL.md")
        for needle in [
            "Apply O15 to every Critic pass.",
            "structured context header and anchor-recall before the option framing",
            "Do not bulk-accept Critic output.",
            "default summary first",
            "concrete specifics",
            "inline verbatim evidence",
        ]:
            assert needle in text, (
                f"Mediation skill missing required contract text: {needle}"
            )

    def test_decision_entry_template_is_visible_in_workflow_surface(self) -> None:
        targets = [
            ".owlbear/briefs/README.md",
            "share/skills/w-ideation-discovery/SKILL.md",
            "share/skills/w-ideation-mediation/SKILL.md",
        ]
        for path in targets:
            text = _read(path)
            for needle in [
                "Decision entry template",
                "## D{N} — {YYYY-MM-DD HH:MM} — {Topic}",
                "**Status quo:** ...",
                "**Decision to make:** ...",
                "**Rejected:**",
            ]:
                assert needle in text, (
                    f"Decision template missing from {path}: {needle}"
                )

    def test_decision_entry_template_has_full_field_set(self) -> None:
        targets = [
            ".owlbear/briefs/README.md",
            "share/skills/w-ideation-discovery/SKILL.md",
            "share/skills/w-ideation-mediation/SKILL.md",
        ]
        for path in targets:
            text = _read(path)
            for needle in [
                "**Options considered:**",
                "**Chosen:**",
                "**Source inputs (when relevant):**",
            ]:
                assert needle in text, (
                    f"Decision template missing field in {path}: {needle}"
                )


class TestFromAC_AgentContracts:
    """Agent prompts keep narrow file contracts and avoid model-string coupling."""

    def test_role_files_do_not_use_model_field_as_contract(self) -> None:
        offenders = []
        for path in _ideation_agent_files():
            if "model:" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(_REPO_ROOT)))
        assert not offenders, f"Model-string contracts still present: {offenders}"

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
        assert not missing, (
            f"Ideation contract missing context/decisions references: {missing}"
        )

    def test_critic_keeps_narrow_context_only_contract(self) -> None:
        text = _read("share/agents/ideation-critic.agent.md")
        assert "context.md" in text, (
            "Critic must keep the context.md engagement snapshot contract"
        )
        assert "decisions.md" not in text, (
            "Critic contract should stay narrow and avoid decisions.md"
        )

    def test_no_working_log_or_checkpoint_contract_reappears(self) -> None:
        offenders = []
        for path in _ideation_surface_files():
            text = path.read_text(encoding="utf-8").lower()
            if "working-log.md" in text or "checkpoint" in text:
                offenders.append(str(path.relative_to(_REPO_ROOT)))
        assert not offenders, (
            f"Deprecated ideation contract terms reappeared: {offenders}"
        )


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
            assert needle in text, (
                f"Brief blackboard docs missing required content: {needle}"
            )


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
        assert (
            "context.md, `decisions.md`, and `research-notes.md`".replace("`", "")
            not in net_new
        )
        for needle in ["net-new", "existing-feature/refactor"]:
            assert needle in (net_new + refactor), (
                f"Project type missing from golden scenarios: {needle}"
            )

    def test_overscoped_scenario_records_scope_reduction_and_o15(self) -> None:
        decisions = _read(f"{self._ROOT}/03-overscoped-request/decisions.md")
        for needle in [
            "split the work",
            "Material findings:",
            "Minor findings (grouped):",
            "Nonsense findings:",
        ]:
            assert needle in decisions, (
                f"Overscoped scenario missing required evidence: {needle}"
            )

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
            assert label in text, (
                f"Golden-scenario README missing class label: {label}"
            )

    def test_overscoped_scenario_has_conditional_denoise_artifact(self) -> None:
        path = f"{self._ROOT}/03-overscoped-request/synthesis-idea-panel.md"
        assert (_REPO_ROOT / path).exists(), (
            f"Missing conditional-denoise artifact for overscoped scenario: {path}"
        )
        text = _read(path)
        for marker in ["## Distinct Claims", "## Divergences"]:
            assert marker in text, (
                f"synthesis-idea-panel.md missing structural section: {marker}"
            )

    def test_overscoped_scenario_has_phase_two_outputs(self) -> None:
        synthesis = _read(f"{self._ROOT}/03-overscoped-request/synthesis.md")
        brief = _read(f"{self._ROOT}/03-overscoped-request/brief.md")
        assert "## Recommendation" in synthesis, (
            "03-overscoped-request/synthesis.md missing ## Recommendation"
        )
        assert "## Proposal" in brief, (
            "03-overscoped-request/brief.md missing ## Proposal"
        )

    def test_scenario_briefs_carry_runtime_disclaimer(self) -> None:
        scenarios = [
            "02-existing-feature-refactor",
            "03-overscoped-request",
        ]
        for scenario in scenarios:
            text = _read(f"{self._ROOT}/{scenario}/brief.md")
            assert "main-consuming" in text, (
                f"{scenario}/brief.md missing runtime-validation disclaimer"
            )


class TestFromAC_IdeatorRouterContract:
    """Ideator must be a compatibility router, not a workflow performer."""

    def test_ideator_does_not_run_workflow_itself(self) -> None:
        text = _read("share/agents/ideator.agent.md")
        assert "Do not run the full ideation workflow yourself." in text, (
            "Ideator is missing the explicit non-performer rule — "
            "it must not claim to run discovery or mediation directly"
        )

    def test_ideator_routes_new_work_to_discoverer(self) -> None:
        text = _read("share/agents/ideator.agent.md")
        assert "Route new or unclear work to `@ideation-discoverer`." in text, (
            "Ideator missing explicit routing rule: new/unclear work → @ideation-discoverer"
        )

    def test_ideator_routes_post_discovery_to_mediator(self) -> None:
        text = _read("share/agents/ideator.agent.md")
        assert "Route post-discovery work to `@ideation-mediator`." in text, (
            "Ideator missing explicit routing rule: post-discovery work → @ideation-mediator"
        )

    def test_ideator_has_disable_model_invocation(self) -> None:
        text = _read("share/agents/ideator.agent.md")
        assert "disable-model-invocation: true" in text, (
            "Ideator must set disable-model-invocation: true — "
            "a router must not invoke a model to perform ideation itself"
        )

    def test_ideator_mediator_route_names_three_artifacts(self) -> None:
        text = _read("share/agents/ideator.agent.md")
        for artifact in ["context.md", "decisions.md", "research-notes.md"]:
            assert artifact in text, (
                f"Ideator mediator-route condition missing artifact reference: {artifact}"
            )

    def test_ideator_names_artifact_paths_explicitly(self) -> None:
        text = _read("share/agents/ideator.agent.md")
        assert "Name the artifact paths explicitly" in text, (
            "Ideator missing explicit rule to name artifact paths — "
            "router must tell users where handoff artifacts live"
        )

    def test_ideator_askquestions_every_turn(self) -> None:
        text = _read("share/agents/ideator.agent.md")
        assert "askQuestions ends every user-facing turn" in text, (
            "Ideator missing interaction contract: askQuestions must end every user-facing turn"
        )


class TestFromAC_EarlyChallengeLane:
    """Early challenge lane selection, critic exclusion, and bounded-output rules."""

    def test_early_lane_always_invokes_simplifier_and_firstprinciples(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert (
            "Always invoke `ideation-simplifier` and `ideation-firstprinciples`"
            in text
        ), (
            "Panel handbook missing the default-roster 'always invoke' rule for "
            "simplifier and firstprinciples"
        )

    def test_outsider_is_conditional_not_default(self) -> None:
        text = _read("share/skills/h-ideation-panel/SKILL.md")
        assert (
            "Invoke `ideation-outsider` only when the discovery agent sees "
            "tunnel vision" in text
        ), (
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

