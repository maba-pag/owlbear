"""
Tests for #1411 — C3: Role boundary documentation — in-scope/out-of-scope for each agent skill.

AC coverage:
  P1: Each pipeline agent skill file contains an explicit "In Scope / Out of Scope" section.
  P2: Agents covered: planner, architect/challenger, test-writer, builder, reviewer, auditor, doc-writer.
  P2: Boundaries are consistent across agents — no overlapping mandates, no uncovered gaps.
  P2: Boundaries reflect the post-rethink division of responsibilities (A2, A3, B1, C1 changes incorporated).
  P3: Verification by artifact inspection of each agent's skill file; cross-reference check for consistency.
"""

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).parent.parent / "share" / "skills"

# P2: All 7 required pipeline agents and their canonical skill file paths.
AGENT_SKILLS: dict[str, Path] = {
    "planner": SKILLS_DIR / "w-task-decomposition" / "SKILL.md",
    "architect": SKILLS_DIR / "w-arch-review" / "SKILL.md",
    "test-writer": SKILLS_DIR / "w-tdd-red" / "SKILL.md",
    "builder": SKILLS_DIR / "w-tdd-green" / "SKILL.md",
    "reviewer": SKILLS_DIR / "w-code-review" / "SKILL.md",
    "auditor": SKILLS_DIR / "w-task-verification" / "SKILL.md",
    "doc-writer": SKILLS_DIR / "w-doc-update" / "SKILL.md",
}

# Agents referenced in Out-of-Scope attributions (research §3.3 convention).
KNOWN_AGENT_LABELS = frozenset(
    label.lower()
    for labels in [
        ["planner", "w-task-decomposition"],
        ["architect", "architect/challenger", "w-arch-review"],
        ["test-writer", "w-tdd-red"],
        ["builder", "w-tdd-green"],
        ["reviewer", "w-code-review"],
        ["auditor", "w-task-verification"],
        ["doc-writer", "w-doc-update"],
        ["ci/sast"],          # documented transitional exception — research §3.4
        ["separate task"],    # documented exception for unrelated refactor work
    ]
    for label in labels
)


def _read(skill_path: Path) -> str:
    return skill_path.read_text(encoding="utf-8")


def _bullets_in_subsection(content: str, heading: str) -> list[str]:
    """Return bullet lines in a ### subsection, up to the next ### or ## heading."""
    match = re.search(
        rf"^{re.escape(heading)}\s*$(.*?)(?=^###|^##|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []
    block = match.group(1)
    return [ln.strip() for ln in block.splitlines() if ln.strip().startswith("- ")]


# ---------------------------------------------------------------------------
# P1 — Explicit "In Scope / Out of Scope" section present in every skill file
# ---------------------------------------------------------------------------


class TestFromAC_ScopeSection:
    """P1: Each pipeline agent skill file contains an explicit ## Scope section."""

    @pytest.mark.parametrize(("agent_name", "skill_path"), list(AGENT_SKILLS.items()))
    def test_has_top_level_scope_heading(self, agent_name: str, skill_path: Path) -> None:
        """P1: The skill file has a standalone '## Scope' heading at the start of a line."""
        content = _read(skill_path)
        assert re.search(r"^## Scope\s*$", content, re.MULTILINE), (
            f"{agent_name} ({skill_path.name}): missing top-level '## Scope' section. "
            "Add '## Scope' heading before '## Step 0' per research §3.2."
        )

    @pytest.mark.parametrize(("agent_name", "skill_path"), list(AGENT_SKILLS.items()))
    def test_has_in_scope_subsection(self, agent_name: str, skill_path: Path) -> None:
        """P1: The ## Scope section contains a '### In Scope' subsection."""
        content = _read(skill_path)
        assert re.search(r"^### In Scope\s*$", content, re.MULTILINE), (
            f"{agent_name} ({skill_path.name}): missing '### In Scope' subsection."
        )

    @pytest.mark.parametrize(("agent_name", "skill_path"), list(AGENT_SKILLS.items()))
    def test_has_out_of_scope_subsection(self, agent_name: str, skill_path: Path) -> None:
        """P1: The ## Scope section contains a '### Out of Scope' subsection."""
        content = _read(skill_path)
        assert re.search(r"^### Out of Scope\s*$", content, re.MULTILINE), (
            f"{agent_name} ({skill_path.name}): missing '### Out of Scope' subsection."
        )


# ---------------------------------------------------------------------------
# P2 — Agents covered: all 7 pipeline roles present
# ---------------------------------------------------------------------------


class TestFromAC_AgentCoverage:
    """P2: All 7 pipeline agent skill files are covered with Scope sections."""

    @pytest.mark.parametrize(("agent_name", "skill_path"), list(AGENT_SKILLS.items()))
    def test_agent_skill_has_scope_section(self, agent_name: str, skill_path: Path) -> None:
        """P2: Each of the 7 required agents has a ## Scope section."""
        content = _read(skill_path)
        assert re.search(r"^## Scope\s*$", content, re.MULTILINE), (
            f"Agent '{agent_name}' ({skill_path.name}) is missing its ## Scope section. "
            "All 7 agents must be covered: planner, architect, test-writer, builder, "
            "reviewer, auditor, doc-writer."
        )


# ---------------------------------------------------------------------------
# P2 — Boundaries are consistent: non-empty, well-formed, attributed
# ---------------------------------------------------------------------------


class TestFromAC_ScopeContent:
    """P2: ## Scope content is non-empty and each Out of Scope bullet names a responsible agent."""

    @pytest.mark.parametrize(("agent_name", "skill_path"), list(AGENT_SKILLS.items()))
    def test_in_scope_has_at_least_one_bullet(self, agent_name: str, skill_path: Path) -> None:
        """P2: ### In Scope has at least one bullet item."""
        content = _read(skill_path)
        bullets = _bullets_in_subsection(content, "### In Scope")
        assert bullets, (
            f"{agent_name} ({skill_path.name}): '### In Scope' section is missing or has no bullet items."
        )

    @pytest.mark.parametrize(("agent_name", "skill_path"), list(AGENT_SKILLS.items()))
    def test_out_of_scope_has_at_least_one_bullet(self, agent_name: str, skill_path: Path) -> None:
        """P2: ### Out of Scope has at least one bullet item."""
        content = _read(skill_path)
        bullets = _bullets_in_subsection(content, "### Out of Scope")
        assert bullets, (
            f"{agent_name} ({skill_path.name}): '### Out of Scope' section is missing or has no bullet items."
        )

    @pytest.mark.parametrize(("agent_name", "skill_path"), list(AGENT_SKILLS.items()))
    def test_out_of_scope_bullets_have_em_dash_attribution(
        self, agent_name: str, skill_path: Path
    ) -> None:
        """P2: Each Out of Scope bullet uses '— agent' convention to name the responsible agent.

        Format from research §3.2: '- {non-responsibility} — {who handles it}'.
        Every bullet must contain an em-dash (—) separating the item from the owner.
        """
        content = _read(skill_path)
        bullets = _bullets_in_subsection(content, "### Out of Scope")
        if not bullets:
            pytest.skip(f"{agent_name}: no Out of Scope bullets (covered by separate test)")
        missing_attr = [b for b in bullets if "—" not in b]
        assert not missing_attr, (
            f"{agent_name} ({skill_path.name}): Out of Scope bullets missing '—' attribution:\n"
            + "\n".join(f"  {b}" for b in missing_attr)
        )

    @pytest.mark.parametrize(("agent_name", "skill_path"), list(AGENT_SKILLS.items()))
    def test_out_of_scope_attributions_name_known_agents(
        self, agent_name: str, skill_path: Path
    ) -> None:
        """P2: Every Out of Scope attribution names a known pipeline agent or documented exception."""
        content = _read(skill_path)
        bullets = _bullets_in_subsection(content, "### Out of Scope")
        if not bullets:
            pytest.skip(f"{agent_name}: no Out of Scope bullets (covered by separate test)")

        violations = []
        for bullet in bullets:
            if "—" not in bullet:
                continue  # missing attribution tested separately
            attribution = bullet.split("—")[-1].strip().lower()
            if not any(label in attribution for label in KNOWN_AGENT_LABELS):
                violations.append(bullet)

        assert not violations, (
            f"{agent_name} ({skill_path.name}): Out of Scope bullets reference unrecognized agents:\n"
            + "\n".join(f"  {b}" for b in violations)
            + f"\nKnown labels: {sorted(KNOWN_AGENT_LABELS)}"
        )


# ---------------------------------------------------------------------------
# P2 — Scope section placement: must precede the first step
# ---------------------------------------------------------------------------


class TestFromAC_ScopePosition:
    """P2: ## Scope section appears before the workflow steps (## Step …)."""

    @pytest.mark.parametrize(("agent_name", "skill_path"), list(AGENT_SKILLS.items()))
    def test_scope_precedes_first_workflow_step(self, agent_name: str, skill_path: Path) -> None:
        """P2: '## Scope' heading must appear before any '## Step N' heading.

        Research §3.2: 'Place a ## Scope section immediately after the skill description
        paragraph and before ## Step 0 — Setup.'
        """
        content = _read(skill_path)
        scope_match = re.search(r"^## Scope\s*$", content, re.MULTILINE)
        step_match = re.search(r"^## Step \d", content, re.MULTILINE)

        assert scope_match is not None, (
            f"{agent_name}: missing '## Scope' section — cannot verify position."
        )
        assert step_match is not None, (
            f"{agent_name}: no '## Step N' heading found — cannot verify Scope placement."
        )
        assert scope_match.start() < step_match.start(), (
            f"{agent_name} ({skill_path.name}): '## Scope' (pos {scope_match.start()}) "
            f"must appear before first '## Step' (pos {step_match.start()})."
        )


# ---------------------------------------------------------------------------
# P2/P3 — Boundary consistency: no overlapping mandates, no uncovered gaps
# ---------------------------------------------------------------------------


class TestFromAC_BoundaryConsistency:
    """P2/P3: Post-rethink responsibilities are assigned exactly once across agents."""

    def test_ac_quality_validation_in_architect_in_scope(self) -> None:
        """P2: AC quality validation is an architect responsibility (In Scope).

        Research §3.3 architect table, §3.4 overlap analysis row 'AC quality':
        planner drafts AC, architect validates — complementary, not overlapping.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["architect"]), "### In Scope")
        mentions_ac = any(
            ("ac" in b.lower() or "acceptance" in b.lower()) and "valid" in b.lower()
            for b in bullets
        )
        assert mentions_ac, (
            "architect In Scope must mention AC quality validation "
            "(research §3.4 confirms this is architect territory)."
        )

    def test_test_writing_excluded_by_builder_out_of_scope(self) -> None:
        """P2: builder Out of Scope excludes test writing (belongs to test-writer).

        Research §3.3 builder table: 'Writing tests — test-writer' is Out of Scope.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["builder"]), "### Out of Scope")
        mentions_test_writing = any(
            "test" in b.lower() and "test-writer" in b.lower() for b in bullets
        )
        assert mentions_test_writing, (
            "builder Out of Scope must exclude test writing and attribute it to test-writer."
        )

    def test_test_writing_excluded_by_reviewer_out_of_scope(self) -> None:
        """P2: reviewer Out of Scope excludes test writing (belongs to test-writer).

        Research §3.3 reviewer table row: test writing is test-writer territory.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["reviewer"]), "### Out of Scope")
        mentions_test_writing = any(
            "test" in b.lower() and ("writ" in b.lower() or "test-writer" in b.lower())
            for b in bullets
        )
        assert mentions_test_writing, (
            "reviewer Out of Scope must exclude test writing and attribute it to test-writer."
        )

    def test_source_code_editing_excluded_by_test_writer_out_of_scope(self) -> None:
        """P2: test-writer Out of Scope excludes editing source code (belongs to builder).

        Research §3.3 test-writer table: 'Writing or editing source code — builder'.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["test-writer"]), "### Out of Scope")
        mentions_source = any(
            "builder" in b.lower()
            and ("source" in b.lower() or "code" in b.lower() or "implement" in b.lower())
            for b in bullets
        )
        assert mentions_source, (
            "test-writer Out of Scope must exclude source code editing and attribute it to builder."
        )

    def test_source_code_editing_excluded_by_reviewer_out_of_scope(self) -> None:
        """P2: reviewer Out of Scope excludes fixing code (belongs to builder).

        Research §3.3 reviewer table: 'Fixing code — builder' is Out of Scope.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["reviewer"]), "### Out of Scope")
        mentions_source = any(
            "builder" in b.lower()
            and ("fix" in b.lower() or "code" in b.lower() or "implement" in b.lower())
            for b in bullets
        )
        assert mentions_source, (
            "reviewer Out of Scope must exclude fixing code and attribute it to builder."
        )

    def test_full_suite_regression_in_auditor_in_scope(self) -> None:
        """P2: Full-suite regression testing is an auditor responsibility (In Scope).

        Research §3.3 auditor table, §3.4 overlap analysis row 'Regression':
        reviewer does scoped evidence; auditor runs the full suite.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["auditor"]), "### In Scope")
        mentions_full_suite = any(
            "full" in b.lower() and ("suite" in b.lower() or "regression" in b.lower())
            for b in bullets
        )
        assert mentions_full_suite, (
            "auditor In Scope must mention full-suite regression testing "
            "(research §3.4: auditor owns breadth, reviewer owns scoped evidence)."
        )

    def test_full_suite_regression_excluded_by_reviewer_out_of_scope(self) -> None:
        """P2: reviewer Out of Scope excludes full-suite regression (belongs to auditor).

        Research §3.3 reviewer table, §3.4: reviewer scope vs auditor breadth separation.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["reviewer"]), "### Out of Scope")
        mentions_auditor_regression = any(
            "auditor" in b.lower()
            and ("full" in b.lower() or "regression" in b.lower() or "suite" in b.lower())
            for b in bullets
        )
        assert mentions_auditor_regression, (
            "reviewer Out of Scope must exclude full-suite regression and attribute it to auditor."
        )

    def test_documentation_updates_excluded_by_builder_out_of_scope(self) -> None:
        """P2: builder Out of Scope excludes documentation updates (belongs to doc-writer).

        Research §3.3 builder table: 'Documentation updates — doc-writer'.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["builder"]), "### Out of Scope")
        mentions_docs = any(
            "doc" in b.lower() for b in bullets
        )
        assert mentions_docs, (
            "builder Out of Scope must exclude documentation updates and attribute them to doc-writer."
        )

    def test_implementation_excluded_by_planner_out_of_scope(self) -> None:
        """P2: planner Out of Scope excludes implementation (belongs to builder).

        Research §3.3 planner table: 'Implementation — builder'.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["planner"]), "### Out of Scope")
        mentions_impl = any(
            "builder" in b.lower() and "implement" in b.lower() for b in bullets
        )
        assert mentions_impl, (
            "planner Out of Scope must exclude implementation and attribute it to builder."
        )

    def test_code_review_excluded_by_architect_out_of_scope(self) -> None:
        """P2: architect Out of Scope excludes code review (belongs to reviewer).

        Research §3.3 architect table: 'Code review — reviewer'.
        """
        bullets = _bullets_in_subsection(_read(AGENT_SKILLS["architect"]), "### Out of Scope")
        mentions_review = any(
            "reviewer" in b.lower() and "review" in b.lower() for b in bullets
        )
        assert mentions_review, (
            "architect Out of Scope must exclude code review and attribute it to reviewer."
        )
