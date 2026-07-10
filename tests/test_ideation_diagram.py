"""Durable tests for ideation diagram coverage.

Promoted from archived task #1034 during test curation.

Historical task context from the original task-scoped suite:

Tests for ideation diagram file — task #1034, 6th-cycle rewrite.

Reflects the current two-phase ideation model as specified in the 6th-cycle
Architecture Review. All tests for the obsolete single-agent orchestrator model
(Mediator/Investigator/Facilitative) have been replaced. Tests that assert new
two-phase model content FAIL against the old diagram; tests for AC1/AC4/AC5/AC6
pass because those criteria are unchanged and the diagram already satisfies them.

AC coverage:
  AC1  — file exists, valid JSON, required top-level fields
  AC2  — current two-phase model:
          Router: ideator as thin entry point (not orchestrator)
          Phase 1 Discovery (ideation-discoverer): Step 0, M1, M2, early
            challenge lane (simplifier + firstprinciples always, outsider
            conditional), optional pragmatist denoise, research bridge to Phase 2
          Phase 2 Mediation (ideation-mediator): Step 0, M3-M6, late domain
            panel (architect, data, enduser, security), embedded Critic loops
            <=5 cycles (bidirectional), pragmatist convergence to synthesis.md
            to M4, O15 Critic validation at M4, Brief at M5, pipeline handoff at M6
          Absence: no "investigator mode", no "facilitative mode"
          Structural connections as bound arrows (semantic element lookups)
  AC3  — top-level "describes" field with exactly 6 required globs
  AC4  — footer text element: Last verified: YYYY-MM-DD (commit-hash)
  AC5  — descriptive (not authoritative) note is present
  AC6  — 6 mechanical Excalidraw convention sub-criteria (unchanged from 4th cycle)
  AC-idx — doc-index includes ideation.excalidraw entry with all 6 required globs

"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from owlbear_tools.doc_index import generate_index
# Promoted from archived task #1034.

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_DIAGRAM_PATH = _PROJECT_ROOT / "share" / "diagrams" / "ideation.excalidraw"
_DOC_INDEX_PATH = _PROJECT_ROOT / ".owlbear" / "doc-index.md"

# AC3 (6th-cycle update) — 6 required describes globs (was 4, added phase skills)
_REQUIRED_DESCRIBES_GLOBS = [
    "share/skills/h-ideation/**",
    "share/skills/w-ideation-discovery/**",
    "share/skills/w-ideation-mediation/**",
    "share/skills/h-ideation-panel/**",
    "share/agents/ideation-*.agent.md",
]

# AC2 — Phase 1 early challenge lane agents (lowercase label fragments)
_EARLY_CHALLENGE_AGENTS = [
    "simplifier",
    "first principles",
    "outsider",
]

# AC2 — Phase 2 late-domain panel agents (lowercase label fragments)
_LATE_PANEL_AGENTS = [
    "architect",
    "data",
    "end user",
    "security",
]

# AC4 — footer pattern (applied to lowercased text)
_FOOTER_RE = re.compile(r"last verified: \d{4}-\d{2}-\d{2} \([0-9a-f]+\)")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def diagram_data() -> dict:
    """Parse ideation.excalidraw and return the top-level dict."""
    return json.loads(_DIAGRAM_PATH.read_text())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_element_text(data: dict) -> str:
    """Return all text content from all Excalidraw elements, lowercased."""
    parts: list[str] = []
    for elem in data.get("elements", []):
        if isinstance(elem.get("text"), str):
            parts.append(elem["text"])
        label = elem.get("label")
        if isinstance(label, dict) and isinstance(label.get("text"), str):
            parts.append(label["text"])
    return " ".join(parts).lower()


def _find_elem_by_text(data: dict, *keywords: str) -> dict | None:
    """Return the first non-deleted element whose text contains all keywords."""
    for elem in data.get("elements", []):
        if elem.get("isDeleted"):
            continue
        text = (elem.get("text") or "").lower()
        if all(k.lower() in text for k in keywords):
            return elem
    return None


def _arrows_between(data: dict, start_id: str, end_id: str) -> list[dict]:
    """Return arrows with startBinding->start_id and endBinding->end_id."""
    result: list[dict] = []
    for elem in data.get("elements", []):
        if elem.get("type") != "arrow":
            continue
        sb = (elem.get("startBinding") or {}).get("elementId")
        eb = (elem.get("endBinding") or {}).get("elementId")
        if sb == start_id and eb == end_id:
            result.append(elem)
    return result


def _build_by_id(data: dict) -> dict[str, dict]:
    """Return a dict mapping element id -> element for all non-deleted elements."""
    return {e["id"]: e for e in data.get("elements", []) if e.get("id")}


def _resolve_text(by_id: dict[str, dict], element_id: str) -> str:
    """Return display text for an element, following containerId for shapes.

    Arrows bind to container rects, not directly to their contained text
    elements. This helper resolves the semantic text for any element:
    - text elements: return el["text"] directly
    - shape/rect elements: find the first non-deleted text child (containerId == shape.id)
    - missing or deleted element: return ""
    """
    el = by_id.get(element_id)
    if not el or el.get("isDeleted"):
        return ""
    if el.get("type") == "text":
        return el.get("text") or ""
    # Shape — find its contained text element
    for other in by_id.values():
        if other.get("containerId") == element_id and other.get("type") == "text" and not other.get("isDeleted"):
            return other.get("text") or ""
    return ""


# ===========================================================================
# TestFromAC_IdeationDiagramFile — AC1 (unchanged)
# ===========================================================================


class TestFromAC_IdeationDiagramFile:
    """AC1: file exists at share/diagrams/ideation.excalidraw, valid JSON,
    required top-level fields present."""

    def test_file_exists_at_expected_path(self) -> None:
        """Happy: share/diagrams/ideation.excalidraw exists in the workspace."""
        assert _DIAGRAM_PATH.exists(), f"Diagram not found: {_DIAGRAM_PATH}"

    def test_file_is_valid_json(self) -> None:
        """Happy: file content parses as valid JSON without error."""
        text = _DIAGRAM_PATH.read_text()
        data = json.loads(text)
        assert isinstance(data, dict)

    def test_json_source_field_is_owlbear(self, diagram_data: dict) -> None:
        """Happy: top-level source field equals owlbear."""
        assert diagram_data.get("source") == "owlbear"

    def test_json_has_elements_list(self, diagram_data: dict) -> None:
        """Happy: top-level elements key is present and is a non-empty list."""
        elements = diagram_data.get("elements")
        assert isinstance(elements, list)
        assert len(elements) > 0, "Diagram has no elements"

    def test_json_type_is_excalidraw(self, diagram_data: dict) -> None:
        """Happy: top-level type field is excalidraw."""
        assert diagram_data.get("type") == "excalidraw"


# ===========================================================================
# TestFromAC_IdeationTwoPhaseModel — AC2: router + two-phase structure
# ===========================================================================


class TestFromAC_IdeationTwoPhaseModel:
    """AC2: diagram shows two-phase model with ideator as thin router, not orchestrator.

    Old diagram encoded Mediator (ideator agent) Orchestrator with
    Investigator/Facilitative modes. These tests FAIL against that old content.
    """

    def test_ideator_labeled_as_router(self, diagram_data: dict) -> None:
        """Happy: ideator labeled as router or routes — NOT orchestrator."""
        all_text = _all_element_text(diagram_data)
        assert "router" in all_text or "routes" in all_text, (
            "ideator must be labeled as a router (router or routes not found). "
            "Old model used orchestrator — that is obsolete."
        )

    def test_phase_1_discovery_labeled(self, diagram_data: dict) -> None:
        """Happy: Phase 1 is labeled as a distinct discovery phase."""
        all_text = _all_element_text(diagram_data)
        assert "phase 1" in all_text or "discovery" in all_text, (
            "Phase 1 Discovery region not found. Diagram must show two distinct phases per AC2."
        )

    def test_phase_2_mediation_labeled(self, diagram_data: dict) -> None:
        """Happy: Phase 2 is labeled as a distinct mediation phase."""
        all_text = _all_element_text(diagram_data)
        assert "phase 2" in all_text or "mediation" in all_text, (
            "Phase 2 Mediation region not found. Diagram must show two distinct phases per AC2."
        )

    def test_discoverer_agent_present_as_phase1_owner(self, diagram_data: dict) -> None:
        """Happy: ideation-discoverer (or discoverer) appears as Phase 1 agent."""
        all_text = _all_element_text(diagram_data)
        assert "discoverer" in all_text, (
            "discoverer agent not found. Phase 1 is owned by ideation-discoverer, not a single Mediator."
        )

    def test_phase1_step0_setup_entry_present(self, diagram_data: dict) -> None:
        """Happy: Phase 1 has its own Step 0 (setup & entry) as a precondition."""
        all_text = _all_element_text(diagram_data)
        assert "step 0" in all_text, "Phase 1 Step 0 (Setup & Entry precondition) not found in diagram"

    def test_obsolete_investigator_mode_absent(self, diagram_data: dict) -> None:
        """Edge: investigator mode must NOT appear — belongs to the old model.
        Old diagram has Investigator mode (M1-M3). This test FAILS against old."""
        all_text = _all_element_text(diagram_data)
        assert "investigator mode" not in all_text, (
            "Obsolete investigator mode label found. New model has two separate phase agents, not behavioral modes."
        )

    def test_obsolete_facilitative_mode_absent(self, diagram_data: dict) -> None:
        """Edge: facilitative mode must NOT appear — belongs to the old model.
        Old diagram has Facilitative mode (M4-M6). This test FAILS against old."""
        all_text = _all_element_text(diagram_data)
        assert "facilitative mode" not in all_text, (
            "Obsolete facilitative mode label found. New model has two separate phase agents, not behavioral modes."
        )


# ===========================================================================
# TestFromAC_IdeationPhase1Discovery — AC2: Phase 1 structural content
# ===========================================================================


class TestFromAC_IdeationPhase1Discovery:
    """AC2: Phase 1 — Discovery (ideation-discoverer): Step 0, M1, M2,
    early challenge lane, optional pragmatist denoise, research bridge."""

    def test_m1_understanding_moment_present(self, diagram_data: dict) -> None:
        """Happy: M1 (Understanding) moment label is present."""
        all_text = _all_element_text(diagram_data)
        assert "m1" in all_text, "M1 moment label not found"

    def test_m2_outcomes_moment_present(self, diagram_data: dict) -> None:
        """Happy: M2 (Outcomes & Early Challenge Lane) moment label is present."""
        all_text = _all_element_text(diagram_data)
        assert "m2" in all_text, "M2 moment label not found"

    def test_early_challenge_lane_labeled(self, diagram_data: dict) -> None:
        """Happy: early challenge lane is labeled as a distinct group in Phase 1."""
        all_text = _all_element_text(diagram_data)
        assert "early challenge" in all_text, (
            "Early challenge lane not labeled. Phase 1 M2 fans out to the early challenge lane per AC2."
        )

    @pytest.mark.parametrize("agent", _EARLY_CHALLENGE_AGENTS)
    def test_early_challenge_agent_present(self, diagram_data: dict, agent: str) -> None:
        """Happy: each early challenge lane agent appears in the diagram."""
        all_text = _all_element_text(diagram_data)
        assert agent in all_text, (
            f"Early challenge lane agent {agent!r} not found. "
            "Simplifier and firstprinciples are always invoked; outsider is conditional."
        )

    def test_research_bridge_to_phase2_present(self, diagram_data: dict) -> None:
        """Happy: research bridge and explicit handoff to Phase 2 is shown."""
        all_text = _all_element_text(diagram_data)
        assert "research bridge" in all_text or "handoff" in all_text, (
            "Research bridge / Phase 1 to Phase 2 handoff not found. "
            "Phase 1 must show explicit handoff to @ideation-mediator per AC2."
        )

    def test_pragmatist_denoise_annotated(self, diagram_data: dict) -> None:
        """Edge: pragmatist denoise pass is shown as optional in Phase 1."""
        all_text = _all_element_text(diagram_data)
        has_denoise = "denoise" in all_text
        has_optional_prag = "pragmatist" in all_text and "optional" in all_text
        assert has_denoise or has_optional_prag, (
            "Pragmatist denoise pass not annotated. "
            "Phase 1 shows optional pragmatist denoise if challenger output is noisy."
        )


# ===========================================================================
# TestFromAC_IdeationPhase2Mediation — AC2: Phase 2 structural content
# ===========================================================================


class TestFromAC_IdeationPhase2Mediation:
    """AC2: Phase 2 — Mediation (ideation-mediator): Step 0, M3-M6,
    late domain panel, embedded Critic loops, pragmatist convergence,
    O15, Brief at M5, pipeline handoff at M6."""

    def test_phase2_step0_reads_discovery_artifacts(self, diagram_data: dict) -> None:
        """Happy: Phase 2 has its own Step 0 that reads discovery artifacts."""
        all_text = _all_element_text(diagram_data)
        has_phase2_step0 = "phase 2" in all_text
        has_reads_artifacts = "reads" in all_text and "artifacts" in all_text
        assert has_phase2_step0 or has_reads_artifacts, (
            "Phase 2 Step 0 (reads discovery artifacts) not found in diagram"
        )

    def test_m3_landscape_moment_present(self, diagram_data: dict) -> None:
        """Happy: M3 (Landscape Presentation) moment label is present."""
        all_text = _all_element_text(diagram_data)
        assert "m3" in all_text, "M3 moment label not found"

    def test_late_domain_panel_labeled(self, diagram_data: dict) -> None:
        """Happy: late domain panel is labeled as a distinct group in Phase 2."""
        all_text = _all_element_text(diagram_data)
        assert "late" in all_text or "domain panel" in all_text, (
            "Late domain panel not found. Phase 2 orchestrates architect/data/enduser/security per AC2."
        )

    @pytest.mark.parametrize("agent", _LATE_PANEL_AGENTS)
    def test_late_panel_agent_present(self, diagram_data: dict, agent: str) -> None:
        """Happy: each late-domain panel agent appears in the Phase 2 section."""
        all_text = _all_element_text(diagram_data)
        assert agent in all_text, (
            f"Late-domain panel agent {agent!r} not found. Phase 2 late panel: architect, data, enduser, security."
        )

    def test_embedded_critic_loops_present(self, diagram_data: dict) -> None:
        """Happy: embedded Critic loops appear in Phase 2."""
        all_text = _all_element_text(diagram_data)
        assert "critic" in all_text, "Critic not found — embedded loops required in Phase 2"

    def test_critic_loop_max_cycles_annotated(self, diagram_data: dict) -> None:
        """Boundary: Critic loop annotation shows <=5 cycle limit per panelist."""
        all_text = _all_element_text(diagram_data)
        assert "<=5" in all_text or "≤5" in all_text or "5 cycle" in all_text, (
            "Critic loop <=5 cycle limit not annotated in diagram"
        )

    def test_pragmatist_convergence_after_panel(self, diagram_data: dict) -> None:
        """Happy: pragmatist convergence step appears after domain panel in Phase 2."""
        all_text = _all_element_text(diagram_data)
        assert "pragmatist" in all_text, "Pragmatist convergence not found"

    def test_o15_critic_validation_at_m4(self, diagram_data: dict) -> None:
        """Happy: M4 includes O15 Critic validation pass per AC2."""
        all_text = _all_element_text(diagram_data)
        assert "o15" in all_text, (
            "O15 Critic validation pass not found. M4 Decision Support must include the O15 validation step per AC2."
        )

    def test_m4_decision_support_present(self, diagram_data: dict) -> None:
        """Happy: M4 (Decision Support) moment label is present."""
        all_text = _all_element_text(diagram_data)
        assert "m4" in all_text, "M4 moment label not found"

    def test_m5_brief_drafting_present(self, diagram_data: dict) -> None:
        """Happy: M5 (Brief Drafting) and Brief output artifact are shown."""
        all_text = _all_element_text(diagram_data)
        assert "m5" in all_text, "M5 moment label not found"
        assert "brief" in all_text, "Brief output not found at M5"

    def test_m6_pipeline_handoff_present(self, diagram_data: dict) -> None:
        """Happy: M6 (Pipeline Handoff) is labeled with kanban or shaper reference."""
        all_text = _all_element_text(diagram_data)
        assert "m6" in all_text, "M6 moment label not found"
        has_handoff = "handoff" in all_text or "shaper" in all_text or "kanban" in all_text
        assert has_handoff, "Pipeline handoff not found at M6"


# ===========================================================================
# TestFromAC_IdeationStructuralConnections — AC2: bound-arrow assertions
# ===========================================================================


class TestFromAC_IdeationStructuralConnections:
    """AC2: key relationships expressed as bound arrows between semantic elements.
    Builder chooses element IDs; tests use text-based element lookup.

    All tests FAIL against old diagram because Phase 1/Phase 2 structural
    elements, early challenge lane, and new late-panel elements do not exist.
    """

    def test_router_has_arrow_to_phase1(self, diagram_data: dict) -> None:
        """Structural: a bound arrow from the router entry to Phase 1."""
        router = _find_elem_by_text(diagram_data, "router")
        assert router is not None, (
            "Router element not found by text router. ideator must be labeled as a routing node per AC2."
        )
        phase1 = _find_elem_by_text(diagram_data, "phase 1") or _find_elem_by_text(diagram_data, "discovery")
        assert phase1 is not None, "Phase 1 entry element not found. Diagram must have a labeled Phase 1 region."
        arrows = _arrows_between(diagram_data, router["id"], phase1["id"])
        assert len(arrows) >= 1, "No bound arrow from router to Phase 1. Router -> Phase 1 path must be explicit."

    def test_router_has_arrow_to_phase2(self, diagram_data: dict) -> None:
        """Structural: a bound arrow from the router entry to Phase 2."""
        router = _find_elem_by_text(diagram_data, "router")
        assert router is not None, "Router element not found by text router"
        phase2 = _find_elem_by_text(diagram_data, "phase 2") or _find_elem_by_text(diagram_data, "mediation")
        assert phase2 is not None, "Phase 2 entry element not found. Diagram must have a labeled Phase 2 region."
        arrows = _arrows_between(diagram_data, router["id"], phase2["id"])
        assert len(arrows) >= 1, "No bound arrow from router to Phase 2. Router -> Phase 2 path must be explicit."

    def test_m2_connects_to_early_challenge_lane(self, diagram_data: dict) -> None:
        """Structural: M2 fans out to the early challenge lane via a bound arrow."""
        m2_elem = _find_elem_by_text(diagram_data, "m2")
        assert m2_elem is not None, "M2 element not found"
        challenge = _find_elem_by_text(diagram_data, "early challenge")
        assert challenge is not None, (
            "Early challenge lane element not found. M2 must fan out to the early challenge lane per AC2."
        )
        arrows = _arrows_between(diagram_data, m2_elem["id"], challenge["id"])
        assert len(arrows) >= 1, "No bound arrow from M2 to early challenge lane"

    def test_phase1_connects_to_phase2_via_research_bridge(self, diagram_data: dict) -> None:
        """Structural: a bound arrow encodes the Phase 1 -> Phase 2 handoff."""
        bridge = _find_elem_by_text(diagram_data, "research bridge") or _find_elem_by_text(diagram_data, "handoff")
        assert bridge is not None, (
            "Research bridge / handoff element not found. Phase 1 must have an explicit handoff to Phase 2 per AC2."
        )
        phase2 = _find_elem_by_text(diagram_data, "phase 2") or _find_elem_by_text(diagram_data, "mediation")
        assert phase2 is not None, "Phase 2 entry element not found"
        arrows = _arrows_between(diagram_data, bridge["id"], phase2["id"])
        assert len(arrows) >= 1, "No bound arrow from handoff/bridge to Phase 2"

    def test_m3_connects_to_late_domain_panel(self, diagram_data: dict) -> None:
        """Structural: an arrow from M3 triggers the late domain panel."""
        m3_elem = _find_elem_by_text(diagram_data, "m3")
        assert m3_elem is not None, "M3 element not found"
        panel = _find_elem_by_text(diagram_data, "late", "panel") or _find_elem_by_text(diagram_data, "domain panel")
        assert panel is not None, (
            "Late domain panel element not found. M3 must trigger the late domain panel via a bound arrow."
        )
        arrows = _arrows_between(diagram_data, m3_elem["id"], panel["id"])
        assert len(arrows) >= 1, "No bound arrow from M3 to late domain panel"

    def test_each_late_panelist_has_bidirectional_critic_loop(self, diagram_data: dict) -> None:
        """Structural: each late-domain panelist has a bidirectional Critic arrow.
        FAILS on old model because data and security elements do not exist.
        """
        critic = _find_elem_by_text(diagram_data, "critic")
        assert critic is not None, "Critic element not found"

        late_panel_keywords: list[tuple[str, ...]] = [
            ("architect",),
            ("data",),
            ("end user",),
            ("security",),
        ]
        missing_bidirectional: list[str] = []
        for kws in late_panel_keywords:
            panelist_elem = _find_elem_by_text(diagram_data, *kws)
            if panelist_elem is None:
                missing_bidirectional.append(f"element for {kws!r} not found")
                continue
            arrows = _arrows_between(diagram_data, panelist_elem["id"], critic["id"])
            bidi = [a for a in arrows if a.get("startArrowhead") is not None and a.get("endArrowhead") is not None]
            if not bidi:
                missing_bidirectional.append(f"{kws!r} -> critic: no bidirectional arrow")
        assert not missing_bidirectional, "Missing bidirectional Critic loop arrows for: " + "; ".join(
            missing_bidirectional
        )

    def test_pragmatist_convergence_connects_to_m4(self, diagram_data: dict) -> None:
        """Structural: an arrow from Phase 2 pragmatist convergence to M4.

        Uses phase-disambiguated lookup (pragmatist + converge) to target the
        Phase 2 convergence node, not the Phase 1 denoise node which also
        contains 'pragmatist'. Both phases use the same agent role name, so
        a first-match lookup would be ambiguous after the 9th-cycle label fix.
        """
        prag = _find_elem_by_text(diagram_data, "pragmatist", "converge")
        assert prag is not None, (
            "Phase 2 pragmatist convergence element not found "
            "(text must contain both 'pragmatist' AND 'converge'). "
            "Use 'Pragmatist (mode=converge)' following the h-ideation-panel convention."
        )
        m4_elem = _find_elem_by_text(diagram_data, "m4")
        assert m4_elem is not None, "M4 element not found"
        arrows = _arrows_between(diagram_data, prag["id"], m4_elem["id"])
        assert len(arrows) >= 1, (
            "No bound arrow from Phase 2 pragmatist (mode=converge) to M4. "
            "Pragmatist convergence must structurally feed M4 in Phase 2."
        )

    def test_m5_brief_output_bound_arrow(self, diagram_data: dict) -> None:
        """Structural: M5 has a bound arrow to the Brief output element."""
        m5_elem = _find_elem_by_text(diagram_data, "m5")
        assert m5_elem is not None, "M5 element not found"
        brief = _find_elem_by_text(diagram_data, "brief")
        assert brief is not None, "Brief output element not found"
        arrows = _arrows_between(diagram_data, m5_elem["id"], brief["id"])
        assert len(arrows) >= 1, "No bound arrow from M5 to brief output"

    def test_m6_handoff_bound_arrow(self, diagram_data: dict) -> None:
        """Structural: M6 has a bound arrow to the pipeline handoff element."""
        m6_elem = _find_elem_by_text(diagram_data, "m6")
        assert m6_elem is not None, "M6 element not found"
        handoff = _find_elem_by_text(diagram_data, "handoff") or _find_elem_by_text(diagram_data, "shaper")
        assert handoff is not None, "Pipeline handoff element not found"
        arrows = _arrows_between(diagram_data, m6_elem["id"], handoff["id"])
        assert len(arrows) >= 1, "No bound arrow from M6 to handoff/shaper"


# ===========================================================================
# TestFromAC_IdeationDescribesField — AC3 (6th-cycle: 6 globs)
# ===========================================================================


class TestFromAC_IdeationDescribesField:
    """AC3: top-level describes field is a list with exactly 6 required globs.

    Two new phase-specific globs (w-ideation-discovery/**, w-ideation-mediation/**)
    were added in the 6th-cycle AC update — parametrized tests for those FAIL
    against the old diagram that has only 4 globs.
    """

    def test_describes_field_exists(self, diagram_data: dict) -> None:
        """Happy: top-level describes key is present."""
        assert "describes" in diagram_data, "Missing describes field"

    def test_describes_is_a_list(self, diagram_data: dict) -> None:
        """Happy: describes is a list, not a string or other type."""
        assert isinstance(diagram_data.get("describes"), list)

    def test_describes_is_not_empty(self, diagram_data: dict) -> None:
        """Happy: describes list has at least one entry."""
        assert len(diagram_data.get("describes", [])) > 0

    @pytest.mark.parametrize("glob", _REQUIRED_DESCRIBES_GLOBS)
    def test_required_glob_present_in_describes(self, diagram_data: dict, glob: str) -> None:
        """Happy: each of the 6 required file-path globs appears in describes."""
        describes: list = diagram_data.get("describes", [])
        assert glob in describes, f"Required glob {glob!r} not found in describes: {describes}"

    def test_describes_has_exactly_six_entries(self, diagram_data: dict) -> None:
        """Boundary: describes contains exactly 6 entries.
        Old diagram had 4 entries; FAILS until phase-specific globs are added."""
        describes: list = diagram_data.get("describes", [])
        assert len(describes) == len(_REQUIRED_DESCRIBES_GLOBS), (
            f"Expected {len(_REQUIRED_DESCRIBES_GLOBS)} describes entries, got {len(describes)}: {describes}"
        )


# ===========================================================================
# TestFromAC_IdeationFooterElement — AC4 (unchanged)
# ===========================================================================


class TestFromAC_IdeationFooterElement:
    """AC4: footer text element with Last verified: YYYY-MM-DD (commit-hash) format."""

    def test_footer_element_contains_last_verified(self, diagram_data: dict) -> None:
        """Happy: at least one diagram element contains the text Last verified:."""
        all_text = _all_element_text(diagram_data)
        assert "last verified:" in all_text, "No element contains Last verified: — footer element missing"

    def test_footer_text_matches_date_hash_pattern(self, diagram_data: dict) -> None:
        """Boundary: footer matches Last verified: YYYY-MM-DD (short-hash) pattern."""
        all_text = _all_element_text(diagram_data)
        assert _FOOTER_RE.search(all_text), (
            f"Footer does not match pattern {_FOOTER_RE.pattern!r}. "
            f"All diagram text (lowercased, first 400 chars): {all_text[:400]}"
        )


# ===========================================================================
# TestFromAC_IdeationDescriptiveNote — AC5 (unchanged)
# ===========================================================================


class TestFromAC_IdeationDescriptiveNote:
    """AC5: diagram is descriptive (not authoritative); note is present."""

    def test_descriptive_note_present(self, diagram_data: dict) -> None:
        """Happy: a text element containing descriptive is present."""
        all_text = _all_element_text(diagram_data)
        assert "descriptive" in all_text, (
            "No descriptive annotation found — AC5 requires diagram to be "
            "explicitly marked as descriptive, not authoritative"
        )

    def test_authority_deferred_to_skill_files(self, diagram_data: dict) -> None:
        """Happy: the descriptive note references skill or authority."""
        all_text = _all_element_text(diagram_data)
        assert "skill" in all_text or "authority" in all_text, (
            "Descriptive note must reference skill files as authority — AC5"
        )


# ===========================================================================
# TestFromAC_IdeationExcalidrawConventions — AC6 (unchanged, 4th-cycle)
# ===========================================================================


class TestFromAC_IdeationExcalidrawConventions:
    """AC6 (4th-cycle refined): 6 mechanical sub-criteria from h-excalidraw-diagram.

    1. All element IDs unique (no duplicates).
    2. Text elements: fontSize >= 16.
    3. Arrows: both startBinding and endBinding reference valid element IDs.
    4. Origin: top-left non-deleted non-arrow element at (100, 100).
    5. Grid: all non-arrow element x/y are multiples of 20.
    6. No standalone text overlap (bounding-box check on standalone text elements).
    """

    def test_all_elements_have_unique_ids(self, diagram_data: dict) -> None:
        """Boundary (sub-criterion 1): every element has an id and no two are the same."""
        elements = diagram_data.get("elements", [])
        ids = [e.get("id") for e in elements]
        missing = [i for i, eid in enumerate(ids) if eid is None]
        assert not missing, f"Elements at indices {missing} are missing id"
        duplicates = {eid for eid in ids if ids.count(eid) > 1}
        assert not duplicates, f"Duplicate element IDs found: {duplicates}"

    def test_text_elements_font_size_at_least_16(self, diagram_data: dict) -> None:
        """Boundary (sub-criterion 2): no text element has fontSize < 16px."""
        elements = diagram_data.get("elements", [])
        violators = [
            e.get("id", f"idx:{i}")
            for i, e in enumerate(elements)
            if e.get("type") == "text" and isinstance(e.get("fontSize"), (int, float)) and e["fontSize"] < 16
        ]
        assert not violators, f"Text elements with fontSize < 16px: {violators}"

    def test_all_arrows_have_both_bindings_referencing_valid_ids(self, diagram_data: dict) -> None:
        """Boundary (sub-criterion 3): every arrow must have startBinding AND
        endBinding, each referencing an element ID that exists in the diagram."""
        elements = diagram_data.get("elements", [])
        valid_ids = {e.get("id") for e in elements if e.get("id")}
        arrows = [e for e in elements if e.get("type") == "arrow"]

        missing_start = [e.get("id", f"idx:{i}") for i, e in enumerate(arrows) if not e.get("startBinding")]
        missing_end = [e.get("id", f"idx:{i}") for i, e in enumerate(arrows) if not e.get("endBinding")]
        invalid_start = [
            (e.get("id"), e["startBinding"]["elementId"])
            for e in arrows
            if e.get("startBinding") and e["startBinding"].get("elementId") not in valid_ids
        ]
        invalid_end = [
            (e.get("id"), e["endBinding"]["elementId"])
            for e in arrows
            if e.get("endBinding") and e["endBinding"].get("elementId") not in valid_ids
        ]
        assert not missing_start, f"Arrows missing startBinding: {missing_start}"
        assert not missing_end, f"Arrows missing endBinding: {missing_end}"
        assert not invalid_start, f"Arrows with invalid startBinding elementId: {invalid_start}"
        assert not invalid_end, f"Arrows with invalid endBinding elementId: {invalid_end}"

    def test_origin_top_left_non_arrow_element_at_100_100(self, diagram_data: dict) -> None:
        """Boundary (sub-criterion 4): topmost-leftmost non-deleted non-arrow
        element must start at exactly (x=100, y=100)."""
        elements = diagram_data.get("elements", [])
        candidates = [e for e in elements if e.get("type") != "arrow" and not e.get("isDeleted")]
        assert candidates, "No non-deleted non-arrow elements found"
        top_left = min(candidates, key=lambda e: (e.get("y", 0), e.get("x", 0)))
        x, y = top_left.get("x", 0), top_left.get("y", 0)
        assert x == 100, f"Top-left non-arrow element has x={x} — expected 100"
        assert y == 100, (
            f"Top-left non-arrow element starts at y={y} — expected y=100 per h-excalidraw-diagram origin rule"
        )

    def test_all_non_arrow_elements_on_20px_grid(self, diagram_data: dict) -> None:
        """Boundary (sub-criterion 5): every non-deleted non-arrow element must
        have x and y coordinates that are exact multiples of 20."""
        elements = diagram_data.get("elements", [])
        violators = [
            {"id": e.get("id"), "x": e.get("x"), "y": e.get("y")}
            for e in elements
            if e.get("type") != "arrow"
            and not e.get("isDeleted")
            and (
                isinstance(e.get("x"), (int, float))
                and isinstance(e.get("y"), (int, float))
                and (int(e["x"]) % 20 != 0 or int(e["y"]) % 20 != 0)
            )
        ]
        assert not violators, (
            f"{len(violators)} non-arrow elements have off-grid coordinates (not multiples of 20): {violators}"
        )

    def test_no_standalone_text_elements_overlap(self, diagram_data: dict) -> None:
        """Boundary (sub-criterion 6): no two non-deleted standalone text elements
        (containerId=null) have overlapping bounding boxes."""
        elements = diagram_data.get("elements", [])
        standalone_texts = [
            e for e in elements if e.get("type") == "text" and not e.get("isDeleted") and e.get("containerId") is None
        ]
        overlapping_pairs: list[tuple[str, str]] = []
        for i, a in enumerate(standalone_texts):
            for b in standalone_texts[i + 1 :]:
                ax, ay = a.get("x", 0), a.get("y", 0)
                aw, ah = a.get("width", 0), a.get("height", 0)
                bx, by = b.get("x", 0), b.get("y", 0)
                bw, bh = b.get("width", 0), b.get("height", 0)
                if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                    overlapping_pairs.append((a.get("id", "?"), b.get("id", "?")))
        assert not overlapping_pairs, (
            f"{len(overlapping_pairs)} overlapping standalone text element pair(s) found "
            f"(violates AC6 sub-criterion 6): {overlapping_pairs}"
        )


# ===========================================================================
# TestFromAC_IdeationDocIndexIntegration — AC-idx (updated for 6 globs)
# ===========================================================================


class TestFromAC_IdeationDocIndexIntegration:
    """AC-idx: generate_index() on a tree with ideation.excalidraw produces
    an entry with all 6 required describes globs (updated from 4 in 5th cycle)."""

    def _generate_entry(self, tmp_path: Path) -> str:
        dest = tmp_path / "share" / "diagrams" / "ideation.excalidraw"
        dest.parent.mkdir(parents=True)
        shutil.copy(_DIAGRAM_PATH, dest)
        index_path = tmp_path / "doc-index.md"
        generate_index(tmp_path, index_path)
        text = index_path.read_text()
        assert "## share/diagrams/ideation.excalidraw" in text, (
            "ideation.excalidraw entry not found in generated doc-index"
        )
        start = text.index("## share/diagrams/ideation.excalidraw")
        nxt = text.find("\n## ", start + 1)
        return text[start:] if nxt == -1 else text[start:nxt]

    def test_doc_index_entry_includes_describes_line(self, tmp_path: Path) -> None:
        """Happy: generate_index emits a describes: line in the entry."""
        entry = self._generate_entry(tmp_path)
        assert "describes:" in entry, "No describes: line in ideation.excalidraw doc-index entry"

    def test_doc_index_entry_includes_all_six_required_globs(self, tmp_path: Path) -> None:
        """Happy: all 6 required globs appear in the generated doc-index entry.
        Fails for the 2 new phase-specific globs until the diagram is updated."""
        entry = self._generate_entry(tmp_path)
        for glob in _REQUIRED_DESCRIBES_GLOBS:
            assert glob in entry, f"Required glob {glob!r} not found in generated doc-index entry"


# ===========================================================================
# TestFromAC_IdeationCommittedDocIndex — AC-idx committed (updated for 6 globs)
# ===========================================================================


class TestFromAC_IdeationCommittedDocIndex:
    """AC-idx (committed): the checked-in .owlbear/doc-index.md contains the
    ideation.excalidraw section with all 6 required describes globs."""

    def _ideation_entry_text(self) -> str:
        assert _DOC_INDEX_PATH.exists(), f"Committed doc-index not found: {_DOC_INDEX_PATH}"
        text = _DOC_INDEX_PATH.read_text()
        assert "## share/diagrams/ideation.excalidraw" in text, (
            "Committed .owlbear/doc-index.md has no entry for share/diagrams/ideation.excalidraw"
        )
        start = text.index("## share/diagrams/ideation.excalidraw")
        nxt = text.find("\n## ", start + 1)
        return text[start:] if nxt == -1 else text[start:nxt]

    def test_committed_doc_index_has_ideation_entry(self) -> None:
        """Regression: the committed doc-index contains the ideation.excalidraw section header."""
        entry = self._ideation_entry_text()
        assert "## share/diagrams/ideation.excalidraw" in entry

    def test_committed_doc_index_has_describes_line(self) -> None:
        """Regression: the committed doc-index entry has a describes: line."""
        entry = self._ideation_entry_text()
        assert "describes:" in entry, "No describes: line in committed doc-index ideation entry"

    @pytest.mark.parametrize("glob", _REQUIRED_DESCRIBES_GLOBS)
    def test_committed_doc_index_ideation_entry_contains_glob(self, glob: str) -> None:
        """Regression: each required describes glob appears in the committed
        doc-index ideation entry. Fails for 2 new phase-specific globs
        until diagram and doc-index are rebuilt and recommitted."""
        entry = self._ideation_entry_text()
        assert glob in entry, f"Required glob {glob!r} not found in committed .owlbear/doc-index.md ideation entry"

    def test_committed_doc_index_has_exactly_six_describes_globs(
        self,
    ) -> None:
        """Boundary: committed doc-index ideation entry references exactly 6 globs."""
        entry = self._ideation_entry_text()
        found = [g for g in _REQUIRED_DESCRIBES_GLOBS if g in entry]
        assert len(found) == len(_REQUIRED_DESCRIBES_GLOBS), (
            f"Expected {len(_REQUIRED_DESCRIBES_GLOBS)} globs in committed entry, found {len(found)}: {found}"
        )

    def test_committed_doc_index_ideation_entry_has_no_extra_describes_globs(
        self,
    ) -> None:
        """Boundary (13th-cycle exactness): the committed doc-index ideation entry's
        describes line contains exactly 6 glob entries when parsed — no extras.

        The prior test only counts how many *required* globs appear in the entry
        text.  It would still pass if a 7th (or more) glob were silently added.
        This test parses the actual `describes:` line and counts every entry,
        failing whenever the count diverges from exactly 6.
        """
        entry = self._ideation_entry_text()
        describes_line = next(
            (ln for ln in entry.splitlines() if ln.strip().startswith("describes:")),
            None,
        )
        assert describes_line is not None, (
            "No 'describes:' line found in the committed doc-index ideation entry. "
            "Regenerate the doc-index with 'uv run doc-index' after updating the diagram."
        )
        after_prefix = describes_line.split("describes:", 1)[1].strip()
        actual_globs = [g.strip() for g in after_prefix.split(",") if g.strip()]
        assert len(actual_globs) == len(_REQUIRED_DESCRIBES_GLOBS), (
            f"Committed doc-index ideation entry has {len(actual_globs)} describes "
            f"glob(s) (parsed from line), expected exactly "
            f"{len(_REQUIRED_DESCRIBES_GLOBS)}. "
            f"Actual parsed globs: {actual_globs}. "
            "Remove any extra globs not in the AC3 required list and regenerate "
            "the doc-index."
        )


# ===========================================================================
# TestFromAC_IdeationAbsenceRequirements — AC2 absence requirements (7th-cycle)
# ===========================================================================


class TestFromAC_IdeationAbsenceRequirements:
    """AC2 absence requirements from the 7th-cycle architecture review.

    The 7th-cycle AC added 4 structural absence requirements that guard against
    the legacy single-agent model surviving under new labels. All 4 tests FAIL
    against the current 6th-cycle artifact, which still carries:
      - 'Mediator orchestrates timeline' subtitle text
      - 'Standalone Critic checks at M1, M2, M4, M5 boundaries' annotation text
      - 'Step 0 + M1-M6' unified-timeline title framing
      - O15 embedded as annotation inside M4 instead of as a separate structural step
    """

    def test_orchestrates_timeline_text_absent(self, diagram_data: dict) -> None:
        """Absence (AC2 req 1): no element may contain 'orchestrates timeline'.

        The 7th-cycle AC bans this phrasing because the two-phase model has no
        single orchestrating agent. Ideator is a thin router; discoverer owns
        Phase 1; mediator owns Phase 2. A subtitle saying 'Mediator orchestrates
        timeline' contradicts that model.

        Current artifact has: 'Mediator orchestrates timeline' at subtitle_text
        (share/diagrams/ideation.excalidraw:396).
        """
        all_text = _all_element_text(diagram_data)
        assert "orchestrates timeline" not in all_text, (
            "Found element containing 'orchestrates timeline'. "
            "AC2 absence requirement 1: no single agent orchestrates the unified timeline "
            "in the two-phase model — remove or replace this subtitle."
        )

    def test_standalone_critic_text_absent(self, diagram_data: dict) -> None:
        """Absence (AC2 req 1): no element may contain 'Standalone Critic'.

        The 7th-cycle AC bans this phrasing because Critic appears only within
        the late-domain panel embedded loops and as the O15 validation step at
        M4. The phrase 'Standalone Critic' implies independent boundary checks
        at moments (M1, M2, M4, M5), which current authority (h-ideation-panel,
        w-ideation-mediation) does not include.

        Current artifact has: 'Standalone Critic checks at M1, M2, M4, M5
        boundaries' at share/diagrams/ideation.excalidraw:1300.
        """
        all_text = _all_element_text(diagram_data)
        assert "standalone critic" not in all_text, (
            "Found element containing 'Standalone Critic'. "
            "AC2 absence requirement 1: Critic is structurally connected only within "
            "the late domain panel and the O15 validation step at M4 — remove this "
            "boundary-check annotation."
        )

    def test_unified_m1_m6_timeline_framing_absent(self, diagram_data: dict) -> None:
        """Absence (AC2 req 4): no element may frame the diagram as a unified M1-M6 timeline.

        The 7th-cycle AC requires the title/subtitle to reflect the two-phase
        structure, not a single shared moment backbone. 'M1-M6' in any element
        implies a unified timeline spanning both phases, contradicting the clean
        phase separation required by the two-phase model.

        Current artifact has: 'OwlBear Ideation Flow (Step 0 + M1-M6)' in the
        title element at share/diagrams/ideation.excalidraw:366.
        """
        all_text = _all_element_text(diagram_data)
        assert "m1-m6" not in all_text, (
            "Diagram text contains 'M1-M6' implying a single shared moment backbone. "
            "AC2 absence requirement 4 requires Phase 1 moments (Step\u00a00, M1, M2) "
            "and Phase 2 moments (Step\u00a00, M3-M6) to be visually separate "
            "phase-owned sequences with no unified M1-M6 framing."
        )
        assert "m1\u2013m6" not in all_text, (
            "Diagram text contains 'M1\u2013M6' (en-dash variant) implying a single "
            "shared moment backbone. AC2 absence requirement 4 requires separate "
            "phase-owned moment sequences with no unified M1\u2013M6 framing."
        )

    def test_o15_is_separate_structural_step_with_arrow_from_m4(self, diagram_data: dict) -> None:
        """Structural (AC2 Phase 2): O15 Critic validation is a distinct element
        with a bound arrow from M4.

        The 7th-cycle AC corrects the Phase 2 flow ordering: O15 is a SEPARATE
        step after M4 decision support (not an annotation embedded in M4 text).
        The mediator validates each Critic finding at this step before the output
        affects the user-facing recommendation. The sequence must be:
        M4 -> O15 element -> M5.

        Current artifact embeds O15 as annotation inside M4:
        'M4\\nDecision support\\n(O15 Critic validation)' — same element, no arrow.
        """
        elements = diagram_data.get("elements", [])

        # Find M4 element
        m4_elem = _find_elem_by_text(diagram_data, "m4")
        assert m4_elem is not None, "M4 element not found — cannot verify O15 separation"

        # O15 must be a SEPARATE element from M4
        o15_elems = [
            e
            for e in elements
            if not e.get("isDeleted")
            and e.get("type") != "arrow"
            and "o15" in (e.get("text") or "").lower()
            and e.get("id") != m4_elem.get("id")
        ]
        assert o15_elems, (
            "O15 Critic validation must be a separate structural element from M4. "
            "Current diagram embeds O15 as text annotation inside the M4 element "
            "('M4\\nDecision support\\n(O15 Critic validation)'). "
            "AC2 requires O15 to be a distinct node so the M4 -> O15 -> M5 "
            "sequence can be expressed as bound arrows."
        )

        # M4 must have a bound arrow to the separate O15 element
        o15_ids = {e["id"] for e in o15_elems if e.get("id")}
        arrows = [
            e
            for e in elements
            if e.get("type") == "arrow"
            and (e.get("startBinding") or {}).get("elementId") == m4_elem.get("id")
            and (e.get("endBinding") or {}).get("elementId") in o15_ids
        ]
        assert arrows, (
            "No bound arrow from M4 to the O15 element found. "
            "AC2 requires the Phase 2 flow to show M4 -> O15 Critic validation as "
            "a structural bound-arrow connection, not just an inline text annotation."
        )


# ===========================================================================
# TestFromAC_IdeationStructuralAbsenceSx — AC2 S2-S5 (8th-cycle)
# Arrow-binding graph checks that cannot be satisfied by relabeling.
# All 4 tests FAIL against the current artifact (legacy structural skeleton).
# ===========================================================================

_MOMENT_RE = re.compile(r"\bM[1-6]\b|\bStep 0\b", re.IGNORECASE)
_M4_RE = re.compile(r"\bM4\b", re.IGNORECASE)
_M2_RE = re.compile(r"\bM2\b", re.IGNORECASE)
_M3_RE = re.compile(r"\bM3\b", re.IGNORECASE)
_MOMENT_ONLY_RE = re.compile(r"\bM[1-6]\b", re.IGNORECASE)
# S8 — phase-boundary exclusivity
_PHASE1_FLOW_RE = re.compile(r"denoise|early challenge", re.IGNORECASE)
_PHASE2_MOMENT_RE = re.compile(r"\bM[3-6]\b", re.IGNORECASE)


class TestFromAC_IdeationStructuralAbsenceSx:
    """AC2 structural sub-criteria S2-S5 (8th-cycle Architecture Review).

    Each test resolves arrow bindings to their semantic text via _resolve_text,
    which follows containerId chains so shape-bound arrows are handled correctly.
    These tests catch structural defects that text-presence checks cannot find:
    legacy boundary-Critic arrows, a shared M2-M3 backbone, an incorrectly
    targeted bridge arrow, and router-to-mode dispatch that bypasses Step 0.

    All 4 tests FAIL against the current artifact:
      S2 — moment→Critic arrows still exist at ideation.excalidraw:2419,2463,2507,2551
      S3 — M2→M3 shared backbone still exists at ideation.excalidraw:1539
      S4 — bridge arrow targets mode_facilitative_text, not Phase 2 Step 0
      S5 — router→mode→M1/M4 dispatch bypasses Step 0 at ideation.excalidraw:1803,1847
    """

    def test_s2_no_moment_to_critic_boundary_arrows(self, diagram_data: dict) -> None:
        """Structural-absence (S2): no arrow may run from a moment (M1-M6 or
        Step 0) to a Critic element, except M4→O15 (the O15 validation step).

        Legacy boundary-Critic arrows (M1/M2/M4/M5 → critic_rect) violate the
        current authority (h-ideation-panel, w-ideation-mediation): Critic
        appears only in the embedded late-panel loops and the O15 step, not as
        a standalone boundary check triggered directly by moments.
        """
        by_id = _build_by_id(diagram_data)
        elements = diagram_data.get("elements", [])
        violations: list[str] = []
        for el in elements:
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            start_id = (el.get("startBinding") or {}).get("elementId")
            end_id = (el.get("endBinding") or {}).get("elementId")
            if not start_id or not end_id:
                continue
            start_text = _resolve_text(by_id, start_id)
            end_text = _resolve_text(by_id, end_id)
            if _MOMENT_RE.search(start_text) and "critic" in end_text.lower():
                if "o15" in end_text.lower():
                    # Only M4 → O15 permitted
                    if not _M4_RE.search(start_text):
                        violations.append(f"Arrow {el.get('id')}: non-M4 moment '{start_text}' → O15 '{end_text}'")
                else:
                    violations.append(
                        f"Arrow {el.get('id')}: moment '{start_text}' "
                        f"→ Critic '{end_text}' (legacy boundary-Critic arrow)"
                    )
        assert not violations, (
            "AC2 S2 violation — moment→Critic boundary arrows found. "
            "Critic must appear only inside late-panel embedded loops and O15. "
            f"Violations: {violations}"
        )

    def test_s3_no_shared_m2_to_m3_backbone_arrow(self, diagram_data: dict) -> None:
        """Structural-absence (S3): no arrow may have resolved start text matching
        M2 AND resolved end text matching M3.

        Phase 1 ends at M2 (via early challenge and bridge); Phase 2 starts at
        its own Step 0 then M3. A direct M2→M3 arrow creates a shared moment
        backbone across both phases, contradicting the two-phase clean separation
        required by the current authority (w-ideation, w-ideation-discovery).
        """
        by_id = _build_by_id(diagram_data)
        elements = diagram_data.get("elements", [])
        violations: list[str] = []
        for el in elements:
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            start_id = (el.get("startBinding") or {}).get("elementId")
            end_id = (el.get("endBinding") or {}).get("elementId")
            if not start_id or not end_id:
                continue
            start_text = _resolve_text(by_id, start_id)
            end_text = _resolve_text(by_id, end_id)
            if _M2_RE.search(start_text) and _M3_RE.search(end_text):
                violations.append(
                    f"Arrow {el.get('id')}: M2 '{start_text}' → M3 '{end_text}' "
                    "(creates shared backbone — Phase 1 and Phase 2 must be "
                    "separate sequences connected only through the research bridge)"
                )
        assert not violations, f"AC2 S3 violation — shared moment backbone M2→M3 arrow found. Violations: {violations}"

    def test_s4_bridge_arrow_targets_phase2_step0(self, diagram_data: dict) -> None:
        """Structural (S4): exactly one bridge/handoff outgoing arrow must exist,
        and its endBinding must resolve to text containing 'Phase 2' AND 'Step 0'.

        The bridge element is the Phase 1 → Phase 2 handoff node. Its outgoing
        arrow must land on the Phase 2 Step 0 gate element. If it lands on a
        legacy intermediary (e.g. mode_facilitative_text), the two phases are
        not cleanly separated and the Phase 2 Step 0 stop-if-thin gate is bypassed.
        """
        by_id = _build_by_id(diagram_data)
        elements = diagram_data.get("elements", [])
        bridge_arrows: list[dict] = []
        for el in elements:
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            start_id = (el.get("startBinding") or {}).get("elementId")
            if not start_id:
                continue
            start_text = _resolve_text(by_id, start_id)
            if re.search(r"bridge|handoff", start_text, re.IGNORECASE):
                bridge_arrows.append(el)

        assert len(bridge_arrows) == 1, (
            f"AC2 S4: expected exactly 1 bridge/handoff outgoing arrow, "
            f"found {len(bridge_arrows)}. "
            "The Phase 1→Phase 2 handoff must be expressed as a single bound arrow "
            "from the bridge/handoff element to Phase 2 Step 0."
        )

        arr = bridge_arrows[0]
        end_id = (arr.get("endBinding") or {}).get("elementId")
        end_text = _resolve_text(by_id, end_id or "")
        assert "phase 2" in end_text.lower(), (
            f"AC2 S4: bridge arrow (id={arr.get('id')}) targets '{end_text}' "
            "which does not contain 'Phase 2'. Bridge must land on the Phase 2 "
            "Step 0 gate element, not a legacy intermediary node."
        )
        assert "step 0" in end_text.lower(), (
            f"AC2 S4: bridge arrow (id={arr.get('id')}) targets '{end_text}' "
            "which does not contain 'Step 0'. Bridge must land on the Phase 2 "
            "Step 0 gate element (reads discovery artifacts; stops if thin)."
        )

    def test_s5_router_targets_do_not_dispatch_directly_to_moments(  # noqa: C901, PLR0912
        self, diagram_data: dict
    ) -> None:
        """Structural-absence (S5): no element that is a direct arrow target of
        the router may itself have an outgoing arrow to a moment (M1-M6).

        The router (ideator) dispatches to Phase 1 and Phase 2 entry elements.
        Those entry elements must connect only to their own Step 0 gates, not
        directly to moment nodes. Legacy intermediary dispatch (router → mode node
        → M1 or M4) bypasses the Phase Step 0 gates and preserves the obsolete
        single-agent model structure even if labels are updated.
        """
        by_id = _build_by_id(diagram_data)
        elements = diagram_data.get("elements", [])

        # Find the router container element(s)
        router_ids: set[str] = set()
        for el in elements:
            if el.get("type") == "text" and not el.get("isDeleted"):
                txt = (el.get("text") or "").lower()
                if "ideator" in txt or "router" in txt:
                    router_ids.add(el["id"])
                    if el.get("containerId"):
                        router_ids.add(el["containerId"])

        assert router_ids, (
            "AC2 S5: router element not found (no element with 'ideator' or 'router' text). "
            "Cannot verify phase-dispatch integrity."
        )

        # Find all elements that are direct arrow targets from the router
        router_targets: set[str] = set()
        for el in elements:
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            start_id = (el.get("startBinding") or {}).get("elementId")
            if start_id in router_ids:
                end_id = (el.get("endBinding") or {}).get("elementId")
                if end_id:
                    router_targets.add(end_id)

        assert router_targets, (
            "AC2 S5: router has no outgoing arrows to phase entry elements. "
            "Router must dispatch to Phase 1 and Phase 2 regions."
        )

        # Check that no router target dispatches directly to a moment
        violations: list[str] = []
        for el in elements:
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            start_id = (el.get("startBinding") or {}).get("elementId")
            if start_id not in router_targets:
                continue
            end_id = (el.get("endBinding") or {}).get("elementId")
            if not end_id:
                continue
            end_text = _resolve_text(by_id, end_id)
            if _MOMENT_ONLY_RE.search(end_text):
                target_text = _resolve_text(by_id, start_id)
                violations.append(
                    f"Router target '{target_text}' (id={start_id}) "
                    f"dispatches directly to moment '{end_text}' "
                    f"via arrow {el.get('id')} — bypasses Step 0 gate"
                )
        assert not violations, (
            "AC2 S5 violation — router target dispatches directly to moment nodes. "
            "Each phase entry element must connect only to its Step 0 gate, "
            "not directly to M1/M4 or other moment nodes. "
            f"Violations: {violations}"
        )

    def test_s6_phase1_denoise_label_contains_authority_terms(self, diagram_data: dict) -> None:
        """Content (S6a): the Phase 1 denoise element must name 'pragmatist' AND 'denoise'.

        Authority: w-ideation-discovery Step 2 item 6 ("invoke ideation-pragmatist
        in denoise mode") and h-ideation-panel Early Challenge Lane invocation
        pattern (ideation-pragmatist → synthesis-idea-panel.md, optional,
        mode=denoise). A label that only says 'Optional denoise pass' omits the
        agent and mode, making the diagram inaccurate relative to the authority
        files it declares in describes.

        Current artifact says 'Optional denoise pass' at p1_denoise_text
        → FAILS until label includes both 'pragmatist' and 'denoise'.
        """
        elements = diagram_data.get("elements", [])
        denoise_found = False
        for el in elements:
            if el.get("type") == "text" and not el.get("isDeleted"):
                lower = (el.get("text") or "").lower()
                if "denoise" in lower:
                    denoise_found = True
                    assert "pragmatist" in lower, (
                        f"Denoise element {el['id']!r} says {el['text']!r} but "
                        f"must also name 'pragmatist' per authority "
                        f"(w-ideation-discovery Step 2-6, h-ideation-panel invocation pattern). "
                        f"Expected label like 'Pragmatist (mode=denoise)' — "
                        f"follow the Phase 2 convention 'Pragmatist (mode=converge)'."
                    )
        assert denoise_found, (
            "No text element contains 'denoise'. "
            "Phase 1 optional pragmatist denoise step must be labeled with 'denoise'."
        )

    def test_s6_phase2_step0_label_contains_compound_stop_gate(self, diagram_data: dict) -> None:
        """Content (S6b): Phase 2 Step 0 must express BOTH the condition (thin/
        insufficient/correction) AND the action (stop/stops/halt).

        Authority: w-ideation-mediation Step 0 item 3 — 'If the Phase 1 artifacts
        are too thin, say so explicitly and stop for correction rather than
        improvising.' A label saying only 'Reads discovery artifacts' omits
        this compound gate.

        Current artifact says 'Reads discovery artifacts' at phase2_step0_text
        → FAILS until label includes both an action term and a condition term.
        """
        action_terms = ["stop", "stops", "halt"]
        condition_terms = ["thin", "insufficient", "correction"]
        elements = diagram_data.get("elements", [])
        for el in elements:
            if el.get("type") == "text" and not el.get("isDeleted"):
                lower = (el.get("text") or "").lower()
                if "phase 2" in lower and "step 0" in lower:
                    has_action = any(t in lower for t in action_terms)
                    has_condition = any(t in lower for t in condition_terms)
                    assert has_action, (
                        f"Phase 2 Step 0 element {el['id']!r} says {el['text']!r} "
                        f"but must include an action term ({'/'.join(action_terms)}). "
                        f"Authority (w-ideation-mediation Step 0-3): 'stop for correction "
                        f"if artifacts are too thin'."
                    )
                    assert has_condition, (
                        f"Phase 2 Step 0 element {el['id']!r} says {el['text']!r} "
                        f"but must include a condition term ({'/'.join(condition_terms)}). "
                        f"Authority (w-ideation-mediation Step 0-3): 'stop for correction "
                        f"if artifacts are too thin'."
                    )
                    return
        pytest.fail(
            "No text element found whose text contains both 'Phase 2' and 'Step 0'. "
            "Phase 2 Step 0 gate element is missing from the diagram."
        )

    def test_s7_phase1_denoise_has_incoming_and_outgoing_arrows(self, diagram_data: dict) -> None:
        """Wiring (S7): the Phase 1 denoise element must have BOTH an incoming
        AND an outgoing bound arrow.

        Authority: w-ideation-discovery Step 2-3 and h-ideation-panel invocation
        pattern — denoise sits between the early challenge lane output and the
        research bridge. Even as an optional branch, a flow-step element must be
        wired on both sides; a floating annotation is not a connected flow step.

        Current artifact: p1_denoise_text exists but has no incoming arrow
        binding → FAILS until connected from early challenge lane AND toward bridge.
        """
        elements = diagram_data.get("elements", [])

        # Find the denoise element and its container (if any)
        denoise_ids: set[str] = set()
        for el in elements:
            if el.get("type") == "text" and not el.get("isDeleted"):
                lower = (el.get("text") or "").lower()
                if "pragmatist" in lower and "denoise" in lower:
                    denoise_ids.add(el["id"])
                    if el.get("containerId"):
                        denoise_ids.add(el["containerId"])

        assert denoise_ids, (
            "No denoise element found whose text contains both 'pragmatist' and 'denoise'. "
            "S6a must pass before S7 can locate the denoise element."
        )

        has_incoming = False
        has_outgoing = False
        for el in elements:
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            end_id = (el.get("endBinding") or {}).get("elementId")
            start_id = (el.get("startBinding") or {}).get("elementId")
            if end_id in denoise_ids:
                has_incoming = True
            if start_id in denoise_ids:
                has_outgoing = True

        assert has_incoming, (
            f"Denoise element(s) {denoise_ids} have no incoming bound arrows. "
            "AC2 S7: denoise must be connected from the early challenge lane — "
            "an incoming arrow from the challenge lane output is required."
        )
        assert has_outgoing, (
            f"Denoise element(s) {denoise_ids} have no outgoing bound arrows. "
            "AC2 S7: denoise must feed forward toward the research bridge or handoff — "
            "a dead end is not a connected flow step."
        )

    def test_s10_bridge_element_names_target_agent(self, diagram_data: dict) -> None:
        """Content (S10): the bridge element (start of the S4 bridge arrow) must
        contain 'ideation-mediator' (case-insensitive). Element-scoped check —
        not a diagram-wide text scan.

        Authority: w-ideation/SKILL.md:149 and w-ideation-discovery/SKILL.md:97-98
        require the Phase 1 handoff to explicitly name @ideation-mediator as the
        target agent. A generic 'Research Bridge' label omits that specificity,
        making the handoff anonymous relative to the authority contract.

        Current artifact: p1_bridge_text says 'Research Bridge' — no 'ideation-mediator'
        → FAILS until bridge element includes the target agent name.
        """
        by_id = _build_by_id(diagram_data)
        elements = diagram_data.get("elements", [])

        bridge_checks: list[tuple[str, str, str]] = []  # (arrow_id, bridge_id, bridge_text)
        for el in elements:
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            start_id = (el.get("startBinding") or {}).get("elementId")
            if not start_id:
                continue
            start_text = _resolve_text(by_id, start_id)
            if re.search(r"bridge|handoff", start_text, re.IGNORECASE):
                bridge_checks.append((el.get("id", ""), start_id, start_text))

        assert bridge_checks, (
            "AC2 S10: no bridge/handoff arrow found. "
            "S4 must pass before S10 can locate the bridge element — "
            "add a bound arrow from the Research Bridge element to Phase 2 Step 0."
        )

        for _arr_id, bridge_id, bridge_text in bridge_checks:
            assert "ideation-mediator" in bridge_text.lower(), (
                f"AC2 S10: bridge element (id={bridge_id!r}) says {bridge_text!r} "
                "but must contain 'ideation-mediator'. "
                "Authority (w-ideation:149, w-ideation-discovery:97-98) requires "
                "the Phase 1 handoff to explicitly name @ideation-mediator as the "
                "target agent — e.g., add '→ @ideation-mediator' to the bridge label."
            )

    def test_s8_no_phase1_flow_to_phase2_moment_arrows(self, diagram_data: dict) -> None:
        """Structural-absence (S8): no arrow from a Phase 1 flow element
        (resolved text matches 'denoise' or 'early challenge') may bind
        directly to a Phase 2 moment node (M3-M6).

        The research bridge is the ONLY legitimate Phase 1→Phase 2 crossing,
        and S4 constrains its target to Phase 2 Step 0. Any direct Phase 1
        flow element → Phase 2 moment arrow creates an unauthorized shortcut
        that skips the Phase 2 Step 0 stop-if-thin gate, contradicting the
        clean phase separation required by the current two-phase model.

        Current artifact has arr_denoise_m4 binding p1_denoise_text
        ('Pragmatist (mode=denoise)\\nOptional denoise pass') → p2_m4_text
        ('M4\\nDecision Support') — FAILS until that arrow is removed.
        """
        by_id = _build_by_id(diagram_data)
        elements = diagram_data.get("elements", [])
        violations: list[str] = []
        for el in elements:
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            start_id = (el.get("startBinding") or {}).get("elementId")
            end_id = (el.get("endBinding") or {}).get("elementId")
            if not start_id or not end_id:
                continue
            start_text = _resolve_text(by_id, start_id)
            end_text = _resolve_text(by_id, end_id)
            if _PHASE1_FLOW_RE.search(start_text) and _PHASE2_MOMENT_RE.search(end_text):
                violations.append(
                    f"Arrow {el.get('id')!r}: Phase 1 flow element "
                    f"{start_text!r} → Phase 2 moment {end_text!r} "
                    f"(unauthorized cross-phase shortcut)"
                )
        assert not violations, (
            "AC2 S8 violation — non-bridge Phase 1 flow element(s) bind directly "
            "to Phase 2 moments. Only the research bridge may cross from Phase 1 "
            "to Phase 2, and S4 constrains its target to Phase 2 Step 0. "
            f"Violations: {violations}"
        )


# ===========================================================================
# S9 — Phase 2 sequential chain proof (11th-cycle)
# ===========================================================================

_PHASE2_CHAIN: list[tuple] = [
    ("s9a", ("step 0", "phase 2"), (re.compile(r"\bM3\b", re.IGNORECASE),)),
    ("s9b", ("domain", "panel"), ("pragmatist", "converge")),
    ("s9c", (re.compile(r"\bM3\b", re.IGNORECASE),), ("domain", "panel")),
    ("s9d", ("pragmatist", "converge"), (re.compile(r"\bM4\b", re.IGNORECASE),)),
    ("s9e", (re.compile(r"\bM4\b", re.IGNORECASE),), ("o15",)),
    ("s9f", ("o15",), (re.compile(r"\bM5\b", re.IGNORECASE),)),
    (
        "s9g",
        (re.compile(r"\bM5\b", re.IGNORECASE),),
        (re.compile(r"\bM6\b", re.IGNORECASE),),
    ),
    ("s9h", (re.compile(r"\bM6\b", re.IGNORECASE),), ("handoff",)),
]


def _text_matches(text: str, criteria: tuple) -> bool:
    """Return True if text satisfies ALL criteria.

    Each criterion is a plain string (case-insensitive substring) or a compiled
    regex (re.search applied to the original-case text).
    """
    lower = text.lower()
    for c in criteria:
        if isinstance(c, re.Pattern):
            if not c.search(text):
                return False
        elif c not in lower:
            return False
    return True


# ===========================================================================


class TestFromAC_IdeationPhase2ChainProof:
    """AC2 structural sub-criterion S9 (11th-cycle Architecture Review).

    The Phase 2 flow described in AC2 must be expressed as a complete chain of
    bound arrows covering all 8 sequential hops. Each hop is checked by
    resolving arrow start/end bindings to their semantic text via
    _resolve_text (follows containerId chains).

    S9a and S9b are artifact defects (missing edges) -- FAIL against current
    artifact. S9c-S9h are regression guards on edges that already exist.

    S9a: Phase 2 Step 0 -> M3               FAIL (arr_step0_m3 missing)
    S9b: late domain panel -> pragmatist(converge)  FAIL (arr_panel_prag missing)
    S9c: M3 -> late domain panel            PASS (arr_m3_panel exists)
    S9d: pragmatist(converge) -> M4         PASS (arr_prag_m4 exists)
    S9e: M4 -> O15                          PASS (arr_m4_o15 exists)
    S9f: O15 -> M5                          PASS (arr_o15_m5 exists)
    S9g: M5 -> M6                           PASS (arr_m5_m6 exists)
    S9h: M6 -> handoff/shaper               PASS (arr_m6_handoff exists)
    """

    @pytest.mark.parametrize(
        ("hop_id", "start_criteria", "end_criteria"),
        _PHASE2_CHAIN,
        ids=[h[0] for h in _PHASE2_CHAIN],
    )
    def test_s9_phase2_chain_hop(
        self,
        diagram_data: dict,
        hop_id: str,
        start_criteria: tuple,
        end_criteria: tuple,
    ) -> None:
        """S9: Phase 2 sequential chain — each hop must have at least one bound arrow."""
        by_id = _build_by_id(diagram_data)
        for el in diagram_data.get("elements", []):
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            start_id = (el.get("startBinding") or {}).get("elementId")
            end_id = (el.get("endBinding") or {}).get("elementId")
            if not start_id or not end_id:
                continue
            start_text = _resolve_text(by_id, start_id)
            end_text = _resolve_text(by_id, end_id)
            if _text_matches(start_text, start_criteria) and _text_matches(end_text, end_criteria):
                return  # Hop satisfied

        start_desc = ", ".join(c.pattern if isinstance(c, re.Pattern) else repr(c) for c in start_criteria)
        end_desc = ", ".join(c.pattern if isinstance(c, re.Pattern) else repr(c) for c in end_criteria)
        pytest.fail(
            f"AC2 S9 hop {hop_id}: no bound arrow from element matching "
            f"[{start_desc}] to element matching [{end_desc}]. "
            f"Phase 2 sequential chain is incomplete — add the missing edge "
            f"to satisfy the AC2 flow contract."
        )


# ===========================================================================
# S11 — Phase 1 sequential chain proof (12th-cycle)
# ===========================================================================

_PHASE1_CHAIN: list[tuple] = [
    ("s11a", ("phase 1", "discovery"), ("step 0", "setup")),
    ("s11b", ("step 0", "setup"), (re.compile(r"\bM1\b", re.IGNORECASE),)),
    (
        "s11c",
        (re.compile(r"\bM1\b", re.IGNORECASE),),
        (re.compile(r"\bM2\b", re.IGNORECASE),),
    ),
    ("s11d", (re.compile(r"\bM2\b", re.IGNORECASE),), ("early challenge",)),
    ("s11e", ("early challenge",), ("pragmatist", "denoise")),
    ("s11f", ("pragmatist", "denoise"), ("bridge",)),
]


class TestFromAC_IdeationPhase1ChainProof:
    """AC2 structural sub-criterion S11 (12th-cycle Architecture Review).

    The Phase 1 flow (Discovery) must be expressed as a complete chain of bound
    arrows covering all 6 sequential hops. Each hop is checked by resolving
    arrow start/end bindings to their semantic text via _resolve_text (follows
    containerId chains). All 6 arrows already exist in the artifact — these are
    regression guards.

    S11a: Phase 1 Entry → Phase 1 Step 0      PASS (arr_p1_entry_step0 exists)
    S11b: Phase 1 Step 0 → M1                 PASS (arr_step0_m1 exists)
    S11c: M1 → M2                             PASS (arr_m1_m2 exists)
    S11d: M2 → Early Challenge Lane           PASS (arr_m2_early exists)
    S11e: Early Challenge → Denoise (prag)    PASS (arr_early_denoise exists)
    S11f: Denoise → Research Bridge           PASS (arr_denoise_bridge exists)

    Bridge → Phase 2 Step 0 is the final Phase 1 hop and is already covered by S4.

    Lookup disambiguation: 'step 0' + 'setup' targets Phase 1 Step 0
    ('Step 0\\nSetup & Entry') and excludes Phase 2 Step 0 ('Phase 2 Step 0\\n
    Mediation\\n...'). M1/M2 regexes use word boundaries to avoid false matches.
    """

    @pytest.mark.parametrize(
        ("hop_id", "start_criteria", "end_criteria"),
        _PHASE1_CHAIN,
        ids=[h[0] for h in _PHASE1_CHAIN],
    )
    def test_s11_phase1_chain_hop(
        self,
        diagram_data: dict,
        hop_id: str,
        start_criteria: tuple,
        end_criteria: tuple,
    ) -> None:
        """S11: Phase 1 sequential chain — each hop must have at least one bound arrow."""
        by_id = _build_by_id(diagram_data)
        for el in diagram_data.get("elements", []):
            if el.get("type") != "arrow" or el.get("isDeleted"):
                continue
            start_id = (el.get("startBinding") or {}).get("elementId")
            end_id = (el.get("endBinding") or {}).get("elementId")
            if not start_id or not end_id:
                continue
            start_text = _resolve_text(by_id, start_id)
            end_text = _resolve_text(by_id, end_id)
            if _text_matches(start_text, start_criteria) and _text_matches(end_text, end_criteria):
                return  # Hop satisfied

        start_desc = ", ".join(c.pattern if isinstance(c, re.Pattern) else repr(c) for c in start_criteria)
        end_desc = ", ".join(c.pattern if isinstance(c, re.Pattern) else repr(c) for c in end_criteria)
        pytest.fail(
            f"AC2 S11 hop {hop_id}: no bound arrow from element matching "
            f"[{start_desc}] to element matching [{end_desc}]. "
            f"Phase 1 sequential chain is incomplete — add the missing edge "
            f"to satisfy the AC2 flow contract."
        )
