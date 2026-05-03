"""Task-scoped tests for #1299: pipeline diagram orchestrator supervisory role assertion.

AC7: The pipeline diagram still visually represents the orchestrator in a
supervisory/auxiliary role (test assertion confirms).

Retry: strengthens the assertion in the module-level test that only checked
for the word "orchestrator" — this file asserts the exact supervisory/auxiliary
role label text.
"""

from __future__ import annotations

import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_DIAGRAM_PATH = _PROJECT_ROOT / "share" / "diagrams" / "pipeline.excalidraw"


def _all_element_texts(data: dict) -> list[str]:
    """Return all text strings from all Excalidraw elements (original case)."""
    parts: list[str] = []
    for elem in data.get("elements", []):
        if isinstance(elem.get("text"), str):
            parts.append(elem["text"])
        label = elem.get("label")
        if isinstance(label, dict) and isinstance(label.get("text"), str):
            parts.append(label["text"])
    return parts


class TestFromAC_OrchestratorSupervisoryRole:
    """AC7: pipeline diagram represents orchestrator in supervisory/auxiliary role."""

    def test_orchestrator_supervisory_label_exact_text_present(self) -> None:
        """The diagram must contain the exact label 'orchestrator: supervisory layer (auxiliary)'.

        The existing test_orchestrator_appears_as_auxiliary_annotation only
        checks that 'orchestrator' appears somewhere — it would still pass if
        the supervisory/auxiliary qualifier were removed. This test is
        discriminating: it fails unless the full role label is present.
        """
        data = json.loads(_DIAGRAM_PATH.read_text())
        texts = _all_element_texts(data)
        expected = "orchestrator: supervisory layer (auxiliary)"
        assert any(
            expected in t for t in texts
        ), (
            f"No element contains the supervisory/auxiliary role label.\n"
            f"Expected substring: {expected!r}\n"
            f"Element texts found: {texts}"
        )

    def test_orchestrator_label_not_just_plain_name(self) -> None:
        """The orchestrator must not appear as a bare name without its role qualifier.

        A plain 'orchestrator' text element (without the supervisory qualifier)
        would satisfy the weaker existing assertion but NOT satisfy AC7.
        This test confirms that every element whose text contains 'orchestrator'
        also contains at least one role qualifier ('supervisory' or 'auxiliary').
        """
        data = json.loads(_DIAGRAM_PATH.read_text())
        texts = _all_element_texts(data)
        orchestrator_texts = [
            t for t in texts
            if "orchestrator" in t.lower() and "stage" not in t.lower()
        ]
        assert orchestrator_texts, (
            "No elements containing 'orchestrator' found — diagram is missing the element."
        )
        bare_entries = [
            t for t in orchestrator_texts
            if "supervisory" not in t.lower() and "auxiliary" not in t.lower()
        ]
        assert not bare_entries, (
            "Orchestrator element(s) lack supervisory/auxiliary role qualifier:\n"
            + "\n".join(f"  - {t!r}" for t in bare_entries)
        )
