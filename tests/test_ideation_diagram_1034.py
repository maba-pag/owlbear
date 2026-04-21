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
  AC6: h-excalidraw-diagram conventions — all element IDs unique,
       text elements have fontSize >= 16, arrows have at least one binding
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
    """AC6: h-excalidraw-diagram conventions — unique IDs, fontSize >= 16, bound arrows."""

    def test_all_elements_have_unique_ids(self, diagram_data: dict) -> None:
        """Boundary: every element has an 'id' field and no two IDs are the same."""
        elements = diagram_data.get("elements", [])
        ids = [e.get("id") for e in elements]
        missing = [i for i, eid in enumerate(ids) if eid is None]
        assert not missing, f"Elements at indices {missing} are missing 'id'"
        duplicates = {eid for eid in ids if ids.count(eid) > 1}
        assert not duplicates, f"Duplicate element IDs found: {duplicates}"

    def test_text_elements_font_size_at_least_16(
        self, diagram_data: dict
    ) -> None:
        """Boundary: no text element has fontSize < 16px (per h-excalidraw-diagram)."""
        elements = diagram_data.get("elements", [])
        violators = [
            e.get("id", f"idx:{i}")
            for i, e in enumerate(elements)
            if e.get("type") == "text"
            and isinstance(e.get("fontSize"), (int, float))
            and e["fontSize"] < 16
        ]
        assert not violators, (
            f"Text elements with fontSize < 16px: {violators}"
        )

    def test_arrow_elements_present(self, diagram_data: dict) -> None:
        """Happy: the diagram contains arrow elements connecting stages."""
        elements = diagram_data.get("elements", [])
        arrows = [e for e in elements if e.get("type") == "arrow"]
        assert len(arrows) > 0, "Diagram has no arrow elements — stages must be connected"

    def test_arrow_elements_have_at_least_one_binding(
        self, diagram_data: dict
    ) -> None:
        """Boundary: all arrow elements must have at least one binding (start or end)
        — floating arrows violate h-excalidraw-diagram conventions."""
        elements = diagram_data.get("elements", [])
        arrows = [e for e in elements if e.get("type") == "arrow"]
        floating = [
            e.get("id", f"idx:{i}")
            for i, e in enumerate(arrows)
            if not e.get("startBinding") and not e.get("endBinding")
        ]
        assert not floating, (
            f"Arrow elements with no bindings (floating): {floating}"
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
