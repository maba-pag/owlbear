"""Durable tests for the pipeline diagram file.

Promoted from archived task #1033 during test curation.

AC coverage:
  AC1: file exists at share/diagrams/pipeline.excalidraw, valid JSON, "source": "owlbear"
  AC2: all 8 pipeline stages present, 7 stage-transition agents labelled,
       planner/orchestrator appear as auxiliary annotations (not stage owners)
  AC3: top-level "describes" field is a list containing the 3 required globs;
       volatile .owlbear/kanban/** glob is absent
  AC4: footer text element with "Last verified: YYYY-MM-DD (commit-hash)" format
  AC6: h-excalidraw-diagram conventions — all element IDs unique,
       text elements have fontSize >= 16
  AC7: uv run doc-index produces a "describes:" entry for pipeline.excalidraw
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from owlbear_tools.doc_index import generate_index

# Promoted from archived task #1033.

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_DIAGRAM_PATH = _PROJECT_ROOT / "share" / "diagrams" / "pipeline.excalidraw"

_REQUIRED_STAGES = [
    "research",
    "backlog",
    "todo",
    "in-progress",
    "review",
    "docs",
    "done",
    "archived",
]

_STAGE_AGENTS = [
    "researcher",
    "architect",
    "test-writer",
    "builder",
    "reviewer",
    "doc-writer",
    "auditor",
]

_REQUIRED_DESCRIBES_GLOBS = [
    "share/instructions/owlbear-system.instructions.md",
    "share/skills/r-pipeline-protocol/**",
    "share/agents/*.agent.md",
]

_VOLATILE_GLOB = ".owlbear/kanban/**"
_FOOTER_RE = re.compile(r"last verified: \d{4}-\d{2}-\d{2} \([0-9a-f]+\)")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def diagram_data() -> dict:
    """Parse pipeline.excalidraw and return the top-level dict."""
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


def _all_element_texts(data: dict) -> list[str]:
    """Return all text strings from Excalidraw elements with original casing."""
    parts: list[str] = []
    for elem in data.get("elements", []):
        if isinstance(elem.get("text"), str):
            parts.append(elem["text"])
        label = elem.get("label")
        if isinstance(label, dict) and isinstance(label.get("text"), str):
            parts.append(label["text"])
    return parts


class TestFromAC_PipelineDiagramFile:
    """AC1: file exists, is valid JSON, has required top-level fields."""

    def test_file_exists_at_expected_path(self) -> None:
        assert _DIAGRAM_PATH.exists(), f"Diagram not found: {_DIAGRAM_PATH}"

    def test_file_is_valid_json(self) -> None:
        text = _DIAGRAM_PATH.read_text()
        data = json.loads(text)
        assert isinstance(data, dict)

    def test_json_source_field_is_owlbear(self, diagram_data: dict) -> None:
        assert diagram_data.get("source") == "owlbear"

    def test_json_has_elements_list(self, diagram_data: dict) -> None:
        elements = diagram_data.get("elements")
        assert isinstance(elements, list)
        assert len(elements) > 0, "Diagram has no elements"

    def test_json_type_is_excalidraw(self, diagram_data: dict) -> None:
        assert diagram_data.get("type") == "excalidraw"


class TestFromAC_PipelineStagesAndAgents:
    """AC2: all 8 stages, 7 stage-transition agents, planner/orchestrator auxiliary."""

    @pytest.mark.parametrize("stage", _REQUIRED_STAGES)
    def test_pipeline_stage_label_present(self, diagram_data: dict, stage: str) -> None:
        all_text = _all_element_text(diagram_data)
        assert stage in all_text, f"Stage '{stage}' not found in diagram text"

    @pytest.mark.parametrize("agent", _STAGE_AGENTS)
    def test_stage_transition_agent_label_present(self, diagram_data: dict, agent: str) -> None:
        all_text = _all_element_text(diagram_data)
        assert agent in all_text, f"Agent '{agent}' not found in diagram text"

    def test_planner_appears_as_auxiliary_annotation(self, diagram_data: dict) -> None:
        all_text = _all_element_text(diagram_data)
        assert "planner" in all_text, (
            "planner must appear as an auxiliary annotation (backlog→todo decomposition), not be absent"
        )

    def test_orchestrator_appears_as_auxiliary_annotation(self, diagram_data: dict) -> None:
        all_text = _all_element_text(diagram_data)
        assert "orchestrator" in all_text, (
            "orchestrator must appear as an auxiliary supervisory annotation, not be absent"
        )

    def test_stage_order_left_to_right(self, diagram_data: dict) -> None:
        elements = diagram_data.get("elements", [])
        stage_positions: dict[str, float] = {}
        for elem in elements:
            text = (elem.get("text") or "").lower().strip()
            if text in _REQUIRED_STAGES:
                stage_positions[text] = elem.get("x", 0)
        missing = [stage for stage in _REQUIRED_STAGES if stage not in stage_positions]
        assert not missing, f"Stages not found as element text: {missing}"
        ordered = sorted(stage_positions.items(), key=lambda kv: kv[1])
        ordered_stages = [key for key, _ in ordered]
        assert ordered_stages == _REQUIRED_STAGES, (
            f"Stage elements not in pipeline order.\nExpected: {_REQUIRED_STAGES}\nGot (left→right): {ordered_stages}"
        )


class TestFromAC_DescribesField:
    """AC3: 'describes' is a list of file-path globs; volatile glob absent."""

    def test_describes_field_exists(self, diagram_data: dict) -> None:
        assert "describes" in diagram_data, "Missing 'describes' field"

    def test_describes_is_a_list(self, diagram_data: dict) -> None:
        assert isinstance(diagram_data.get("describes"), list)

    def test_describes_is_not_empty(self, diagram_data: dict) -> None:
        assert len(diagram_data.get("describes", [])) > 0

    @pytest.mark.parametrize("glob", _REQUIRED_DESCRIBES_GLOBS)
    def test_required_glob_present_in_describes(self, diagram_data: dict, glob: str) -> None:
        describes: list = diagram_data.get("describes", [])
        assert glob in describes, f"Required glob '{glob}' not found in describes: {describes}"

    def test_volatile_kanban_glob_absent(self, diagram_data: dict) -> None:
        describes: list = diagram_data.get("describes", [])
        assert _VOLATILE_GLOB not in describes, f"Volatile glob '{_VOLATILE_GLOB}' must be excluded from describes"


class TestFromAC_FooterElement:
    """AC4: footer text element with 'Last verified: YYYY-MM-DD (commit-hash)' format."""

    def test_footer_element_contains_last_verified(self, diagram_data: dict) -> None:
        all_text = _all_element_text(diagram_data)
        assert "last verified:" in all_text, "No element contains 'Last verified:' — footer element missing"

    def test_footer_text_matches_date_hash_pattern(self, diagram_data: dict) -> None:
        all_text = _all_element_text(diagram_data)
        assert _FOOTER_RE.search(all_text), (
            f"Footer does not match pattern {_FOOTER_RE.pattern!r}.\nAll diagram text (lowercased): {all_text[:400]}"
        )


class TestFromAC_ExcalidrawConventions:
    """AC6: h-excalidraw-diagram conventions — unique IDs, fontSize >= 16."""

    def test_all_elements_have_unique_ids(self, diagram_data: dict) -> None:
        elements = diagram_data.get("elements", [])
        ids = [elem.get("id") for elem in elements]
        missing = [index for index, element_id in enumerate(ids) if element_id is None]
        assert not missing, f"Elements at indices {missing} are missing 'id'"
        duplicates = {element_id for element_id in ids if ids.count(element_id) > 1}
        assert not duplicates, f"Duplicate element IDs found: {duplicates}"

    def test_text_elements_font_size_at_least_16(self, diagram_data: dict) -> None:
        elements = diagram_data.get("elements", [])
        violators = [
            elem.get("id", f"idx:{index}")
            for index, elem in enumerate(elements)
            if elem.get("type") == "text" and isinstance(elem.get("fontSize"), (int, float)) and elem["fontSize"] < 16
        ]
        assert not violators, f"Text elements with fontSize < 16px: {violators}"

    def test_arrow_elements_have_bindings(self, diagram_data: dict) -> None:
        elements = diagram_data.get("elements", [])
        arrows = [elem for elem in elements if elem.get("type") == "arrow"]
        assert len(arrows) > 0, "Diagram has no arrow elements — stages must be connected"
        floating = [
            elem.get("id", f"idx:{index}")
            for index, elem in enumerate(arrows)
            if not elem.get("startBinding") and not elem.get("endBinding")
        ]
        assert not floating, f"Arrow elements with no bindings (floating): {floating}"


class TestFromAC_DocIndexIntegration:
    """AC7: uv run doc-index includes a describes entry for pipeline.excalidraw."""

    def test_doc_index_entry_includes_describes_line(self, tmp_path: Path) -> None:
        dest = tmp_path / "share" / "diagrams" / "pipeline.excalidraw"
        dest.parent.mkdir(parents=True)
        shutil.copy(_DIAGRAM_PATH, dest)

        index_path = tmp_path / "doc-index.md"
        generate_index(tmp_path, index_path)
        text = index_path.read_text()

        assert "## share/diagrams/pipeline.excalidraw" in text, (
            "pipeline.excalidraw entry not found in doc-index output"
        )
        entry_start = text.index("## share/diagrams/pipeline.excalidraw")
        next_entry = text.find("\n## ", entry_start + 1)
        entry_text = text[entry_start:] if next_entry == -1 else text[entry_start:next_entry]
        assert "describes:" in entry_text, "No 'describes:' line in pipeline.excalidraw doc-index entry"

    def test_doc_index_entry_includes_all_required_globs(self, tmp_path: Path) -> None:
        dest = tmp_path / "share" / "diagrams" / "pipeline.excalidraw"
        dest.parent.mkdir(parents=True)
        shutil.copy(_DIAGRAM_PATH, dest)

        index_path = tmp_path / "doc-index.md"
        generate_index(tmp_path, index_path)
        text = index_path.read_text()

        entry_start = text.index("## share/diagrams/pipeline.excalidraw")
        next_entry = text.find("\n## ", entry_start + 1)
        entry_text = text[entry_start:] if next_entry == -1 else text[entry_start:next_entry]
        for glob in _REQUIRED_DESCRIBES_GLOBS:
            assert glob in entry_text, f"Required glob '{glob}' not found in doc-index entry"


class TestFromAC_OrchestratorSupervisoryRole1299:
    """Promoted unique orchestrator supervisory-role assertions from #1299."""

    def test_orchestrator_supervisory_label_exact_text_present(self) -> None:
        """Diagram contains exact supervisory role label for orchestrator."""
        data = json.loads(_DIAGRAM_PATH.read_text())
        texts = _all_element_texts(data)
        expected = "orchestrator: supervisory layer (auxiliary)"
        assert any(expected in text for text in texts), (
            "No element contains the supervisory/auxiliary role label.\n"
            f"Expected substring: {expected!r}\n"
            f"Element texts found: {texts}"
        )

    def test_orchestrator_label_not_just_plain_name(self) -> None:
        """Any orchestrator text includes a supervisory/auxiliary qualifier."""
        data = json.loads(_DIAGRAM_PATH.read_text())
        texts = _all_element_texts(data)
        orchestrator_texts = [text for text in texts if "orchestrator" in text.lower() and "stage" not in text.lower()]
        assert orchestrator_texts, "No elements containing 'orchestrator' found — diagram is missing the element."
        bare_entries = [
            text for text in orchestrator_texts if "supervisory" not in text.lower() and "auxiliary" not in text.lower()
        ]
        assert not bare_entries, "Orchestrator element(s) lack supervisory/auxiliary role qualifier:\n" + "\n".join(
            f"  - {text!r}" for text in bare_entries
        )
