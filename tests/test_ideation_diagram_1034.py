"""Failing tests for ideation diagram file (#1034).

RED phase — all tests must fail until share/diagrams/ideation.excalidraw is
created and satisfies every acceptance criterion.

NOTE (retry cycle): This task was originally passed through as type:docs.
The reviewer found that mechanically-testable JSON artifacts require regression
tests (precedent: test_pipeline_diagram_1033.py). Tests below protect the
ideation.excalidraw artifact and its doc-index entry against regressions.
Since the builder already delivered a complete AC-compliant implementation,
these tests pass against the current state — they are regression guards, not
pre-implementation RED-phase stubs.

AC coverage:
  AC1: share/diagrams/ideation.excalidraw exists, valid JSON, "source": "owlbear",
       "type": "excalidraw", non-empty "elements" list
  AC2: structural elements present — Step 0 precondition, M1-M6 timeline,
       Mediator orchestrator, Investigator and Facilitative modes, 6 panelist
       roles (Critic, Architect, Modeler, End User, Skeptic, Pragmatist),
       Critic-loop protocol (<=5 cycles), standalone Critic boundary checks
       (M1, M2, M4, M5), Pragmatist synthesis, Brief output (M5), pipeline
       handoff (M6: kanban -> planner decomposition)
  AC3: top-level "describes" field is a list containing exactly the 4 required
       globs; no extra entries
  AC4: footer text element with "Last verified: YYYY-MM-DD (commit-hash)" format
  AC5: descriptive (not authoritative) note present
  AC6: h-excalidraw-diagram conventions (refined 4th-cycle) — 6 mechanical
       sub-criteria: unique IDs, fontSize >= 16, arrows have BOTH
       startBinding+endBinding referencing valid IDs, top-left non-arrow element
       at (100, 100), all non-arrow x/y are multiples of 20, no two non-deleted
       standalone text elements (containerId: null) have overlapping bounding boxes
  AC-idx: uv run doc-index includes a "describes:" entry for ideation.excalidraw
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from owlbear_tools.doc_index import generate_index

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_DIAGRAM_PATH = _PROJECT_ROOT / "share" / "diagrams" / "ideation.excalidraw"

# AC2 — 6 panelist labels (lowercased for text search)
_REQUIRED_PANELISTS = [
    "critic",
    "architect",
    "modeler",
    "end user",
    "skeptic",
    "pragmatist",
]

# AC2 -- M1-M6 moment labels (lowercased)
_REQUIRED_MOMENTS = ["m1", "m2", "m3", "m4", "m5", "m6"]

# AC3 — exact describes globs required in the diagram file
_REQUIRED_DESCRIBES_GLOBS = [
    "share/skills/w-ideation/**",
    "share/skills/h-ideation-panel/**",
    "share/agents/ideator.agent.md",
    "share/agents/ideation-*.agent.md",
]

# AC4 — footer pattern: Last verified: YYYY-MM-DD (short-hash)
# All element text is lowercased before matching.
_FOOTER_RE = re.compile(r"last verified: \d{4}-\d{2}-\d{2} \([0-9a-f]+\)")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def diagram_data() -> dict:
    """Parse ideation.excalidraw and return the top-level dict.

    Raises FileNotFoundError (fixture ERROR) if the file does not yet exist —
    expected RED-phase failure mode for all tests using this fixture.
    """
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


# ===========================================================================
# TestFromAC_IdeationDiagramFile — AC1
# ===========================================================================


class TestFromAC_IdeationDiagramFile:
    """AC1: file exists at share/diagrams/ideation.excalidraw, valid JSON, required fields."""

    def test_file_exists_at_expected_path(self) -> None:
        """Happy: share/diagrams/ideation.excalidraw exists in the workspace."""
        assert _DIAGRAM_PATH.exists(), f"Diagram not found: {_DIAGRAM_PATH}"

    def test_file_is_valid_json(self) -> None:
        """Happy: file content parses as valid JSON without error."""
        text = _DIAGRAM_PATH.read_text()
        data = json.loads(text)
        assert isinstance(data, dict)

    def test_json_source_field_is_owlbear(self, diagram_data: dict) -> None:
        """Happy: top-level 'source' field equals 'owlbear'."""
        assert diagram_data.get("source") == "owlbear"

    def test_json_has_elements_list(self, diagram_data: dict) -> None:
        """Happy: top-level 'elements' key is present and is a non-empty list."""
        elements = diagram_data.get("elements")
        assert isinstance(elements, list)
        assert len(elements) > 0, "Diagram has no elements"

    def test_json_type_is_excalidraw(self, diagram_data: dict) -> None:
        """Happy: top-level 'type' field is 'excalidraw'."""
        assert diagram_data.get("type") == "excalidraw"


# ===========================================================================
# TestFromAC_IdeationDiagramStructure — AC2
# ===========================================================================


class TestFromAC_IdeationDiagramStructure:
    """AC2: required structural elements are present as text in the diagram."""

    def test_step0_setup_entry_present(self, diagram_data: dict) -> None:
        """Happy: 'step 0' appears as a precondition element label."""
        all_text = _all_element_text(diagram_data)
        assert "step 0" in all_text, "Step 0 precondition label not found in diagram"

    @pytest.mark.parametrize("moment", _REQUIRED_MOMENTS)
    def test_moment_label_present(self, diagram_data: dict, moment: str) -> None:
        """Happy: each of the 6 moment labels (M1-M6) appears in the diagram."""
        all_text = _all_element_text(diagram_data)
        assert moment in all_text, f"Moment '{moment}' not found in diagram text"

    def test_mediator_orchestrator_present(self, diagram_data: dict) -> None:
        """Happy: 'mediator' appears as the orchestrator label."""
        all_text = _all_element_text(diagram_data)
        assert "mediator" in all_text, "Mediator orchestrator label not found"

    def test_investigator_mode_present(self, diagram_data: dict) -> None:
        """Happy: Mediator 'investigator' behavioral mode (M1-M3) is labelled."""
        all_text = _all_element_text(diagram_data)
        assert "investigator" in all_text, (
            "Investigator mode label not found — required by AC2"
        )

    def test_facilitative_mode_present(self, diagram_data: dict) -> None:
        """Happy: Mediator 'facilitative' behavioral mode (M4-M6) is labelled."""
        all_text = _all_element_text(diagram_data)
        assert "facilitative" in all_text, (
            "Facilitative mode label not found — required by AC2"
        )

    @pytest.mark.parametrize("panelist", _REQUIRED_PANELISTS)
    def test_panelist_label_present(self, diagram_data: dict, panelist: str) -> None:
        """Happy: each of the 6 panelist roles appears as a label in the diagram."""
        all_text = _all_element_text(diagram_data)
        assert panelist in all_text, f"Panelist '{panelist}' not found in diagram text"

    def test_parallel_panel_batch_element_present(self, diagram_data: dict) -> None:
        """Happy: a 'panel batch' grouping element is labelled between M3 and M4."""
        all_text = _all_element_text(diagram_data)
        assert "panel batch" in all_text, (
            "Parallel panel batch label not found — required by AC2"
        )

    def test_critic_loop_protocol_element_present(
        self, diagram_data: dict
    ) -> None:
        """Happy: the Critic-loop protocol note is present (domain panelist → Critic ≤5 cycles)."""
        all_text = _all_element_text(diagram_data)
        assert "critic loop" in all_text, (
            "Critic-loop protocol text element not found — required by AC2"
        )

    def test_critic_loop_max_cycles_annotated(self, diagram_data: dict) -> None:
        """Boundary: the Critic-loop annotation mentions the ≤5 cycle limit."""
        all_text = _all_element_text(diagram_data)
        assert "<=5" in all_text or "≤5" in all_text, (
            "Critic-loop ≤5 cycle limit not annotated in diagram — required by AC2"
        )

    def test_standalone_critic_boundary_checks_present(
        self, diagram_data: dict
    ) -> None:
        """Happy: standalone Critic checks at M1, M2, M4, M5 boundaries are noted."""
        all_text = _all_element_text(diagram_data)
        assert "standalone critic" in all_text, (
            "Standalone Critic boundary-check annotation not found — required by AC2"
        )

    def test_standalone_critic_mentions_m1_m2_m4_m5(
        self, diagram_data: dict
    ) -> None:
        """Boundary: the standalone-Critic annotation references M1, M2, M4, and M5."""
        # Find the specific element text that describes standalone checks
        for elem in diagram_data.get("elements", []):
            raw = (elem.get("text") or "").lower()
            if "standalone" in raw and "critic" in raw:
                assert "m1" in raw, f"Standalone Critic note missing M1: {raw!r}"
                assert "m2" in raw, f"Standalone Critic note missing M2: {raw!r}"
                assert "m4" in raw, f"Standalone Critic note missing M4: {raw!r}"
                assert "m5" in raw, f"Standalone Critic note missing M5: {raw!r}"
                return
        pytest.fail("No element with standalone Critic annotation found")

    def test_pragmatist_synthesis_present(self, diagram_data: dict) -> None:
        """Happy: Pragmatist synthesis step is labelled (after domain panelists complete)."""
        all_text = _all_element_text(diagram_data)
        assert "pragmatist synthesis" in all_text, (
            "'Pragmatist synthesis' label not found — required by AC2"
        )

    def test_brief_output_at_m5_present(self, diagram_data: dict) -> None:
        """Happy: a Brief output element is labelled at M5."""
        all_text = _all_element_text(diagram_data)
        assert "brief" in all_text, "Brief output label not found — required by AC2"

    def test_pipeline_handoff_at_m6_present(self, diagram_data: dict) -> None:
        """Happy: M6 pipeline handoff (kanban parent task → planner decomposition) is labelled."""
        all_text = _all_element_text(diagram_data)
        assert "planner decomposition" in all_text or "kanban parent" in all_text, (
            "M6 handoff to planner decomposition not found — required by AC2"
        )


# ===========================================================================
# TestFromAC_IdeationDescribesField — AC3
# ===========================================================================


class TestFromAC_IdeationDescribesField:
    """AC3: top-level 'describes' field is a list containing exactly the 4 required globs."""

    def test_describes_field_exists(self, diagram_data: dict) -> None:
        """Happy: top-level 'describes' key is present."""
        assert "describes" in diagram_data, "Missing 'describes' field"

    def test_describes_is_a_list(self, diagram_data: dict) -> None:
        """Happy: 'describes' is a list, not a string or other type."""
        assert isinstance(diagram_data.get("describes"), list)

    def test_describes_is_not_empty(self, diagram_data: dict) -> None:
        """Happy: 'describes' list has at least one entry."""
        assert len(diagram_data.get("describes", [])) > 0

    @pytest.mark.parametrize("glob", _REQUIRED_DESCRIBES_GLOBS)
    def test_required_glob_present_in_describes(
        self, diagram_data: dict, glob: str
    ) -> None:
        """Happy: each of the 4 required file-path globs appears in 'describes'."""
        describes: list = diagram_data.get("describes", [])
        assert glob in describes, (
            f"Required glob '{glob}' not found in describes: {describes}"
        )

    def test_describes_has_exactly_four_entries(
        self, diagram_data: dict
    ) -> None:
        """Boundary: 'describes' contains exactly 4 entries — no extra or missing globs."""
        describes: list = diagram_data.get("describes", [])
        assert len(describes) == len(_REQUIRED_DESCRIBES_GLOBS), (
            f"Expected {len(_REQUIRED_DESCRIBES_GLOBS)} describes entries, "
            f"got {len(describes)}: {describes}"
        )


# ===========================================================================
# TestFromAC_IdeationFooterElement — AC4
# ===========================================================================


class TestFromAC_IdeationFooterElement:
    """AC4: footer text element with 'Last verified: YYYY-MM-DD (commit-hash)' format."""

    def test_footer_element_contains_last_verified(
        self, diagram_data: dict
    ) -> None:
        """Happy: at least one diagram element contains the text 'Last verified:'."""
        all_text = _all_element_text(diagram_data)
        assert "last verified:" in all_text, (
            "No element contains 'Last verified:' — footer element missing"
        )

    def test_footer_text_matches_date_hash_pattern(
        self, diagram_data: dict
    ) -> None:
        """Boundary: footer matches 'Last verified: YYYY-MM-DD (short-hash)' pattern."""
        all_text = _all_element_text(diagram_data)
        assert _FOOTER_RE.search(all_text), (
            f"Footer does not match pattern {_FOOTER_RE.pattern!r}.\n"
            f"All diagram text (lowercased): {all_text[:400]}"
        )


# ===========================================================================
# TestFromAC_IdeationDescriptiveNote — AC5
# ===========================================================================


class TestFromAC_IdeationDescriptiveNote:
    """AC5: diagram is descriptive (not authoritative); note is present in diagram."""

    def test_descriptive_note_present(self, diagram_data: dict) -> None:
        """Happy: a text element containing 'descriptive' is present in the diagram."""
        all_text = _all_element_text(diagram_data)
        assert "descriptive" in all_text, (
            "No 'descriptive' annotation found — AC5 requires diagram to be "
            "explicitly marked as descriptive, not authoritative"
        )

    def test_authority_deferred_to_skill_files(self, diagram_data: dict) -> None:
        """Happy: the descriptive note references 'skill' or 'authority' to indicate
        where canonical authority resides."""
        all_text = _all_element_text(diagram_data)
        assert "skill" in all_text or "authority" in all_text, (
            "Descriptive note must reference skill files as authority — AC5"
        )


# ===========================================================================
# TestFromAC_IdeationExcalidrawConventions — AC6
# ===========================================================================


class TestFromAC_IdeationExcalidrawConventions:
    """AC6 (refined, 4th-cycle): 6 mechanical sub-criteria from h-excalidraw-diagram.

    1. All element IDs unique (no duplicates).
    2. Text elements: fontSize >= 16.
    3. Arrows: both startBinding and endBinding reference valid element IDs.
    4. Origin: the top-left non-deleted non-arrow element starts at (100, 100).
    5. Grid: all non-arrow element x and y coordinates are multiples of 20.
       Arrow coordinates are exempt (they are computed from bindings, not placed).
    6. No standalone text overlap: no two non-deleted text elements with
       containerId=null have overlapping bounding boxes.
    """

    def test_all_elements_have_unique_ids(self, diagram_data: dict) -> None:
        """Boundary (sub-criterion 1): every element has an 'id' and no two are the same."""
        elements = diagram_data.get("elements", [])
        ids = [e.get("id") for e in elements]
        missing = [i for i, eid in enumerate(ids) if eid is None]
        assert not missing, f"Elements at indices {missing} are missing 'id'"
        duplicates = {eid for eid in ids if ids.count(eid) > 1}
        assert not duplicates, f"Duplicate element IDs found: {duplicates}"

    def test_text_elements_font_size_at_least_16(
        self, diagram_data: dict
    ) -> None:
        """Boundary (sub-criterion 2): no text element has fontSize < 16px."""
        elements = diagram_data.get("elements", [])
        violators = [
            e.get("id", f"idx:{i}")
            for i, e in enumerate(elements)
            if e.get("type") == "text"
            and isinstance(e.get("fontSize"), (int, float))
            and e["fontSize"] < 16
        ]
        assert not violators, f"Text elements with fontSize < 16px: {violators}"

    def test_arrow_elements_present(self, diagram_data: dict) -> None:
        """Happy: the diagram contains arrow elements connecting stages."""
        elements = diagram_data.get("elements", [])
        arrows = [e for e in elements if e.get("type") == "arrow"]
        assert len(arrows) > 0, "Diagram has no arrow elements — stages must be connected"

    def test_all_arrows_have_both_bindings_referencing_valid_ids(
        self, diagram_data: dict
    ) -> None:
        """Boundary (sub-criterion 3): every arrow must have startBinding AND
        endBinding, each referencing an element ID that exists in the diagram.
        One-sided or floating arrows violate h-excalidraw-diagram conventions."""
        elements = diagram_data.get("elements", [])
        valid_ids = {e.get("id") for e in elements if e.get("id")}
        arrows = [e for e in elements if e.get("type") == "arrow"]

        missing_start = [
            e.get("id", f"idx:{i}")
            for i, e in enumerate(arrows)
            if not e.get("startBinding")
        ]
        missing_end = [
            e.get("id", f"idx:{i}")
            for i, e in enumerate(arrows)
            if not e.get("endBinding")
        ]
        invalid_start = [
            (e.get("id"), e["startBinding"]["elementId"])
            for e in arrows
            if e.get("startBinding")
            and e["startBinding"].get("elementId") not in valid_ids
        ]
        invalid_end = [
            (e.get("id"), e["endBinding"]["elementId"])
            for e in arrows
            if e.get("endBinding")
            and e["endBinding"].get("elementId") not in valid_ids
        ]
        assert not missing_start, f"Arrows missing startBinding: {missing_start}"
        assert not missing_end, f"Arrows missing endBinding: {missing_end}"
        assert not invalid_start, f"Arrows with invalid startBinding elementId: {invalid_start}"
        assert not invalid_end, f"Arrows with invalid endBinding elementId: {invalid_end}"

    def test_origin_top_left_non_arrow_element_at_100_100(
        self, diagram_data: dict
    ) -> None:
        """Boundary (sub-criterion 4): the topmost-leftmost non-deleted non-arrow
        element must start at exactly (x=100, y=100), per h-excalidraw-diagram
        origin convention. Current diagram has title_text at (100, 40) — FAIL."""
        elements = diagram_data.get("elements", [])
        candidates = [
            e for e in elements
            if e.get("type") != "arrow" and not e.get("isDeleted")
        ]
        assert candidates, "No non-deleted non-arrow elements found"
        top_left = min(candidates, key=lambda e: (e.get("y", 0), e.get("x", 0)))
        x, y = top_left.get("x", 0), top_left.get("y", 0)
        assert x == 100, (
            f"Top-left non-arrow element '{top_left.get('id')}' has x={x} — expected 100"
        )
        assert y == 100, (
            f"Top-left non-arrow element '{top_left.get('id')}' starts at y={y} — "
            f"expected y=100 per h-excalidraw-diagram origin rule"
        )

    def test_all_non_arrow_elements_on_20px_grid(
        self, diagram_data: dict
    ) -> None:
        """Boundary (sub-criterion 5): every non-deleted non-arrow element must
        have x and y coordinates that are exact multiples of 20. Arrow element
        coordinates are exempt (they are computed from bindings, not manually placed)."""
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
            f"{len(violators)} non-arrow elements have off-grid coordinates "
            f"(not multiples of 20): {violators}"
        )

    def test_no_standalone_text_elements_overlap(
        self, diagram_data: dict
    ) -> None:
        """Boundary (sub-criterion 6): no two non-deleted text elements with
        containerId=null have overlapping bounding boxes.

        Two elements A and B overlap when ALL of:
          A.x < B.x + B.width  AND  B.x < A.x + A.width
          A.y < B.y + B.height AND  B.y < A.y + A.height

        Current defect: subtitle_text and descriptive_note_text both at (100, 160)
        overlap completely — this test documents and guards that defect.
        """
        elements = diagram_data.get("elements", [])
        standalone_texts = [
            e for e in elements
            if e.get("type") == "text"
            and not e.get("isDeleted")
            and e.get("containerId") is None
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
# TestFromAC_IdeationDocIndexIntegration — AC-idx
# ===========================================================================


class TestFromAC_IdeationDocIndexIntegration:
    """AC-idx: uv run doc-index includes a describes entry for ideation.excalidraw."""

    def test_doc_index_entry_includes_describes_line(
        self, tmp_path: Path
    ) -> None:
        """Happy: generate_index on a tree containing ideation.excalidraw emits
        a 'describes:' line in the entry for that file."""
        dest = tmp_path / "share" / "diagrams" / "ideation.excalidraw"
        dest.parent.mkdir(parents=True)
        shutil.copy(_DIAGRAM_PATH, dest)

        index_path = tmp_path / "doc-index.md"
        generate_index(tmp_path, index_path)
        text = index_path.read_text()

        assert "## share/diagrams/ideation.excalidraw" in text, (
            "ideation.excalidraw entry not found in doc-index output"
        )
        entry_start = text.index("## share/diagrams/ideation.excalidraw")
        next_entry = text.find("\n## ", entry_start + 1)
        entry_text = (
            text[entry_start:] if next_entry == -1 else text[entry_start:next_entry]
        )
        assert "describes:" in entry_text, (
            "No 'describes:' line in ideation.excalidraw doc-index entry"
        )

    def test_doc_index_entry_includes_all_required_globs(
        self, tmp_path: Path
    ) -> None:
        """Happy: all 4 required globs appear in the ideation.excalidraw doc-index entry."""
        dest = tmp_path / "share" / "diagrams" / "ideation.excalidraw"
        dest.parent.mkdir(parents=True)
        shutil.copy(_DIAGRAM_PATH, dest)

        index_path = tmp_path / "doc-index.md"
        generate_index(tmp_path, index_path)
        text = index_path.read_text()

        entry_start = text.index("## share/diagrams/ideation.excalidraw")
        next_entry = text.find("\n## ", entry_start + 1)
        entry_text = (
            text[entry_start:] if next_entry == -1 else text[entry_start:next_entry]
        )
        for glob in _REQUIRED_DESCRIBES_GLOBS:
            assert glob in entry_text, (
                f"Required glob '{glob}' not found in doc-index entry"
            )


# ===========================================================================
# TestFromAC_IdeationStructuralConnections — AC2 (structural, strengthened)
# ===========================================================================

# Canonical element IDs from share/diagrams/ideation.excalidraw
_TIMELINE_ELEMENT_IDS = [
    "step0_rect", "m1_rect", "m2_rect", "m3_rect",
    "m4_rect", "m5_rect", "m6_rect",
]

_DOMAIN_PANELIST_IDS = [
    "architect_rect", "modeler_rect", "enduser_rect", "skeptic_rect",
]

_BOUNDARY_MOMENT_IDS = ["m1_rect", "m2_rect", "m4_rect", "m5_rect"]


def _arrows_from_to(data: dict, start_id: str, end_id: str) -> list[dict]:
    """Return arrows with startBinding→start_id and endBinding→end_id."""
    result: list[dict] = []
    for elem in data.get("elements", []):
        if elem.get("type") != "arrow":
            continue
        sb = (elem.get("startBinding") or {}).get("elementId")
        eb = (elem.get("endBinding") or {}).get("elementId")
        if sb == start_id and eb == end_id:
            result.append(elem)
    return result


def _elem_by_id(data: dict, eid: str) -> dict | None:
    for elem in data.get("elements", []):
        if elem.get("id") == eid:
            return elem
    return None


class TestFromAC_IdeationStructuralConnections:
    """AC2 (structural): key structural relationships are encoded as arrow
    bindings between named element IDs, not only as text labels."""

    def test_m3_arrow_triggers_panel_batch(self, diagram_data: dict) -> None:
        """Structural: an arrow from m3_rect to panel_batch_rect encodes the
        panel-batch trigger point — removing it breaks the M3→batch connection."""
        arrows = _arrows_from_to(diagram_data, "m3_rect", "panel_batch_rect")
        assert len(arrows) >= 1, (
            "No arrow from 'm3_rect' to 'panel_batch_rect'. "
            "The panel batch must be structurally triggered from M3."
        )

    def test_pragmatist_arrow_feeds_m4(self, diagram_data: dict) -> None:
        """Structural: an arrow from pragmatist_rect to m4_rect encodes that
        Pragmatist synthesis outputs flow into M4."""
        arrows = _arrows_from_to(diagram_data, "pragmatist_rect", "m4_rect")
        assert len(arrows) >= 1, (
            "No arrow from 'pragmatist_rect' to 'm4_rect'. "
            "Pragmatist synthesis must structurally feed M4."
        )

    @pytest.mark.parametrize("panelist_id", _DOMAIN_PANELIST_IDS)
    def test_domain_panelist_converges_into_pragmatist(
        self, diagram_data: dict, panelist_id: str
    ) -> None:
        """Structural: each of the 4 domain panelists has an outbound arrow
        ending at pragmatist_rect — encoding the convergence after deliberation."""
        arrows = _arrows_from_to(diagram_data, panelist_id, "pragmatist_rect")
        assert len(arrows) >= 1, (
            f"No arrow from '{panelist_id}' to 'pragmatist_rect'. "
            "Domain panelist outputs must converge into Pragmatist synthesis."
        )

    def test_brief_output_arrow_bound_to_m5(self, diagram_data: dict) -> None:
        """Structural: an arrow from m5_rect to brief_output_ellipse encodes
        that Brief output is produced at M5, not elsewhere."""
        arrows = _arrows_from_to(diagram_data, "m5_rect", "brief_output_ellipse")
        assert len(arrows) >= 1, (
            "No arrow from 'm5_rect' to 'brief_output_ellipse'. "
            "Brief output must be structurally bound to M5."
        )

    def test_handoff_arrow_bound_to_m6(self, diagram_data: dict) -> None:
        """Structural: an arrow from m6_rect to handoff_rect encodes that
        the pipeline handoff occurs at M6, not elsewhere."""
        arrows = _arrows_from_to(diagram_data, "m6_rect", "handoff_rect")
        assert len(arrows) >= 1, (
            "No arrow from 'm6_rect' to 'handoff_rect'. "
            "Pipeline handoff must be structurally bound to M6."
        )

    @pytest.mark.parametrize("moment_id", _BOUNDARY_MOMENT_IDS)
    def test_standalone_critic_arrow_from_boundary_moment(
        self, diagram_data: dict, moment_id: str
    ) -> None:
        """Structural: M1, M2, M4, and M5 each have an arrow pointing to
        critic_rect — encoding the standalone Critic boundary checks."""
        arrows = _arrows_from_to(diagram_data, moment_id, "critic_rect")
        assert len(arrows) >= 1, (
            f"No arrow from '{moment_id}' to 'critic_rect'. "
            f"Standalone Critic boundary check at {moment_id} must be structurally encoded."
        )

    def test_investigator_mode_connects_to_m1_region(
        self, diagram_data: dict
    ) -> None:
        """Structural: mode_investigator_rect has an arrow to m1_rect, encoding
        that the Investigator mode covers the M1 entry point."""
        arrows = _arrows_from_to(diagram_data, "mode_investigator_rect", "m1_rect")
        assert len(arrows) >= 1, (
            "No arrow from 'mode_investigator_rect' to 'm1_rect'. "
            "Investigator mode must be structurally connected to the M1 region."
        )

    def test_facilitative_mode_connects_to_m4(self, diagram_data: dict) -> None:
        """Structural: mode_facilitative_rect has an arrow to m4_rect, encoding
        that the Facilitative mode covers the M4-M6 region."""
        arrows = _arrows_from_to(diagram_data, "mode_facilitative_rect", "m4_rect")
        assert len(arrows) >= 1, (
            "No arrow from 'mode_facilitative_rect' to 'm4_rect'. "
            "Facilitative mode must be structurally connected to M4."
        )

    def test_timeline_elements_in_left_to_right_order(
        self, diagram_data: dict
    ) -> None:
        """Boundary: Step 0 and M1-M6 elements appear in ascending x-position
        order, matching the documented left-to-right timeline sequence."""
        id_to_x: dict[str, float] = {}
        for elem in diagram_data.get("elements", []):
            if elem.get("id") in _TIMELINE_ELEMENT_IDS:
                id_to_x[elem["id"]] = elem.get("x", 0)
        missing = [eid for eid in _TIMELINE_ELEMENT_IDS if eid not in id_to_x]
        assert not missing, f"Timeline elements not found by ID: {missing}"
        ordered = sorted(id_to_x.items(), key=lambda kv: kv[1])
        ordered_ids = [k for k, _ in ordered]
        assert ordered_ids == _TIMELINE_ELEMENT_IDS, (
            f"Timeline elements not in left-to-right order.\n"
            f"Expected: {_TIMELINE_ELEMENT_IDS}\n"
            f"Got (left→right): {ordered_ids}"
        )


# ===========================================================================
# TestFromAC_IdeationPanelBatchSpatial — AC2 (spatial, strengthened)
# ===========================================================================

_BATCH_CONTAINED_IDS = [
    "architect_rect", "modeler_rect", "enduser_rect",
    "skeptic_rect", "critic_rect", "pragmatist_rect",
]


class TestFromAC_IdeationPanelBatchSpatial:
    """AC2 (spatial): panelists, Critic, and Pragmatist are spatially contained
    within the panel_batch_rect, confirming 'parallel batch between M3 and M4'."""

    def _batch_bounds(self, data: dict) -> tuple[float, float, float, float]:
        elem = _elem_by_id(data, "panel_batch_rect")
        if elem is None:
            pytest.fail("panel_batch_rect element not found in diagram")
        return (elem["x"], elem["y"],
                elem["x"] + elem["width"], elem["y"] + elem["height"])

    @pytest.mark.parametrize("role_id", _BATCH_CONTAINED_IDS)
    def test_role_rect_center_inside_panel_batch_bounds(
        self, diagram_data: dict, role_id: str
    ) -> None:
        """Spatial: center of each role rect falls within panel_batch_rect bounds,
        confirming the element lives inside the batch grouping."""
        xmin, ymin, xmax, ymax = self._batch_bounds(diagram_data)
        elem = _elem_by_id(diagram_data, role_id)
        assert elem is not None, f"Element '{role_id}' not found in diagram"
        cx = elem["x"] + elem.get("width", 0) / 2
        cy = elem["y"] + elem.get("height", 0) / 2
        assert xmin <= cx <= xmax, (
            f"{role_id} center x={cx} is outside panel_batch_rect "
            f"x-range [{xmin}, {xmax}]"
        )
        assert ymin <= cy <= ymax, (
            f"{role_id} center y={cy} is outside panel_batch_rect "
            f"y-range [{ymin}, {ymax}]"
        )


# ===========================================================================
# TestFromAC_IdeationCommittedDocIndex — AC-idx (committed, strengthened)
# ===========================================================================

_DOC_INDEX_PATH = _PROJECT_ROOT / ".owlbear" / "doc-index.md"


class TestFromAC_IdeationCommittedDocIndex:
    """AC-idx (committed): the checked-in .owlbear/doc-index.md contains the
    ideation.excalidraw section with all required describes globs.

    Distinct from TestFromAC_IdeationDocIndexIntegration which tests
    generate_index() in a temp tree — this class tests the committed artifact.
    """

    def _ideation_entry_text(self) -> str:
        assert _DOC_INDEX_PATH.exists(), (
            f"Committed doc-index not found: {_DOC_INDEX_PATH}"
        )
        text = _DOC_INDEX_PATH.read_text()
        assert "## share/diagrams/ideation.excalidraw" in text, (
            "Committed .owlbear/doc-index.md has no entry for "
            "share/diagrams/ideation.excalidraw — doc-index regen was not committed"
        )
        start = text.index("## share/diagrams/ideation.excalidraw")
        nxt = text.find("\n## ", start + 1)
        return text[start:] if nxt == -1 else text[start:nxt]

    def test_committed_doc_index_has_ideation_entry(self) -> None:
        """Regression: the checked-in doc-index contains the ideation.excalidraw
        section header; stale or missing regen would remove it."""
        entry = self._ideation_entry_text()
        assert "## share/diagrams/ideation.excalidraw" in entry

    @pytest.mark.parametrize("glob", _REQUIRED_DESCRIBES_GLOBS)
    def test_committed_doc_index_ideation_entry_contains_glob(
        self, glob: str
    ) -> None:
        """Regression: each required describes glob appears in the committed
        doc-index ideation entry; a stale regen would drop them."""
        entry = self._ideation_entry_text()
        assert glob in entry, (
            f"Required glob '{glob}' not found in committed "
            ".owlbear/doc-index.md ideation entry"
        )
