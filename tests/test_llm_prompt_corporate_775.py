"""Failing tests for LLM_EXTRACTION_PROMPT corporate entity/relation guidance.

Tests assert that LLM_EXTRACTION_PROMPT contains descriptive classification
hints and contrastive guidance for corporate entity types and relation types
BEYOND the bare comma-separated enum-value listings.

Task: #766 (parent: #751)
ALL tests must fail RED against the current prompt — the prompt only contains
comma-separated enum-value lists with no descriptive/contrastive text.
"""

from __future__ import annotations

import pytest

from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT
from owlbear_knowledge.models import EntityType, RelationType

# ---------------------------------------------------------------------------
# Reference strings — computed the same way as llm_extractor internals so
# tests can strip enum listings and inspect remaining prompt content.
# ---------------------------------------------------------------------------

_ENTITY_LIST = ", ".join(e.value for e in EntityType)
_RELATION_LIST = ", ".join(r.value for r in RelationType)

_CORPORATE_ENTITY_TYPES = [
    EntityType.REQUIREMENT.value,
    EntityType.SOLUTION.value,
    EntityType.PROCEDURE.value,
    EntityType.POLICY.value,
    EntityType.STANDARD.value,
]


def _strip_entity_list(prompt: str) -> str:
    """Remove all occurrences of the entity-value list substring from *prompt*."""
    return prompt.replace(_ENTITY_LIST, "")


def _strip_relation_list(prompt: str) -> str:
    """Remove all occurrences of the relation-value list substring from *prompt*."""
    return prompt.replace(_RELATION_LIST, "")


# ---------------------------------------------------------------------------
# AC1 — Corporate entity types have descriptive guidance beyond the enum listing.
# Technique: strip _ENTITY_LIST from prompt; assert each corporate type remains.
# RED: after stripping, corporate types vanish (they only appear in the enum list).
# ---------------------------------------------------------------------------


class TestFromAC_CorpEntityDescriptiveHints:
    """AC1: LLM_EXTRACTION_PROMPT has a descriptive/classification hint for each
    corporate entity type beyond the bare comma-separated _ENTITY_LIST."""

    def test_requirement_has_descriptive_text_beyond_enum_list(self) -> None:
        """After stripping _ENTITY_LIST, 'requirement' still appears as guidance."""
        stripped = _strip_entity_list(LLM_EXTRACTION_PROMPT)
        assert "requirement" in stripped.lower(), (
            "After removing the entity-value list, 'requirement' must still appear "
            "as a descriptive/classification hint — not only in the enum listing."
        )

    def test_solution_has_descriptive_text_beyond_enum_list(self) -> None:
        """After stripping _ENTITY_LIST, 'solution' still appears as guidance."""
        stripped = _strip_entity_list(LLM_EXTRACTION_PROMPT)
        assert "solution" in stripped.lower(), (
            "After removing the entity-value list, 'solution' must still appear "
            "as a descriptive/classification hint — not only in the enum listing."
        )

    def test_procedure_has_descriptive_text_beyond_enum_list(self) -> None:
        """After stripping _ENTITY_LIST, 'procedure' still appears as guidance."""
        stripped = _strip_entity_list(LLM_EXTRACTION_PROMPT)
        assert "procedure" in stripped.lower(), (
            "After removing the entity-value list, 'procedure' must still appear "
            "as a descriptive/classification hint — not only in the enum listing."
        )

    def test_policy_has_descriptive_text_beyond_enum_list(self) -> None:
        """After stripping _ENTITY_LIST, 'policy' still appears as guidance."""
        stripped = _strip_entity_list(LLM_EXTRACTION_PROMPT)
        assert "policy" in stripped.lower(), (
            "After removing the entity-value list, 'policy' must still appear "
            "as a descriptive/classification hint — not only in the enum listing."
        )

    def test_standard_has_descriptive_text_beyond_enum_list(self) -> None:
        """After stripping _ENTITY_LIST, 'standard' still appears as guidance."""
        stripped = _strip_entity_list(LLM_EXTRACTION_PROMPT)
        assert "standard" in stripped.lower(), (
            "After removing the entity-value list, 'standard' must still appear "
            "as a descriptive/classification hint — not only in the enum listing."
        )


# ---------------------------------------------------------------------------
# AC2 — Prompt explicitly differentiates corporate entity types from CONCEPT.
# RED: current prompt has no paragraph that pairs a corporate type with 'concept'
# outside the stripped enum list — let alone with contrastive language.
# ---------------------------------------------------------------------------


class TestFromAC_CorpEntityContrastiveConcept:
    """AC2: LLM_EXTRACTION_PROMPT contains explicit contrastive text differentiating
    at least one corporate entity type from CONCEPT (prevents LLM collapse per F3)."""

    def test_corporate_type_and_concept_coreference_in_stripped_prompt(self) -> None:
        """After stripping the entity-value list, at least one paragraph co-references
        a corporate entity type and 'concept' as proximity guidance."""
        stripped = _strip_entity_list(LLM_EXTRACTION_PROMPT)
        paragraphs = [p.lower() for p in stripped.split("\n\n")]
        for para in paragraphs:
            if "concept" in para and any(t in para for t in _CORPORATE_ENTITY_TYPES):
                return
        pytest.fail(
            "LLM_EXTRACTION_PROMPT has no paragraph co-referencing a corporate entity type "
            "('requirement', 'solution', 'procedure', 'policy', or 'standard') alongside "
            "'concept' after stripping the entity-value list. A guideline block is required "
            "to distinguish corporate types from CONCEPT."
        )

    def test_contrastive_language_between_corporate_type_and_concept(self) -> None:
        """After stripping the entity-value list, at least one paragraph contains a
        corporate entity type, 'concept', and a contrastive keyword (e.g. 'not',
        'unlike', 'distinct', 'distinguish', 'contrast', 'vs', 'whereas')."""
        stripped = _strip_entity_list(LLM_EXTRACTION_PROMPT)
        contrastive_keywords = [
            "not ", "unlike", "distinct", "vs.", "vs ",
            "distinguish", "contrast", "whereas", "rather than", "instead of",
        ]
        paragraphs = [p.lower() for p in stripped.split("\n\n")]
        for para in paragraphs:
            has_corp = any(t in para for t in _CORPORATE_ENTITY_TYPES)
            has_concept = "concept" in para
            has_contrast = any(kw in para for kw in contrastive_keywords)
            if has_corp and has_concept and has_contrast:
                return
        pytest.fail(
            "LLM_EXTRACTION_PROMPT has no paragraph containing a corporate entity type, "
            "'concept', and contrastive language after stripping the entity-value list. "
            "Add differentiation guidance to prevent LLM collapse (per F3 research)."
        )


# ---------------------------------------------------------------------------
# AC3 — GOVERNS and SUPERSEDES_VERSION have descriptive guidance beyond the
# relation-value listing.
# Technique: strip _RELATION_LIST from prompt; assert each relation type remains.
# RED: after stripping, both types vanish (they only appear in the relation list).
# ---------------------------------------------------------------------------


class TestFromAC_RelationTypeDescriptiveGuidance:
    """AC3: LLM_EXTRACTION_PROMPT has descriptive guidance for GOVERNS and
    SUPERSEDES_VERSION beyond the bare comma-separated _RELATION_LIST."""

    def test_governs_has_descriptive_text_beyond_relation_list(self) -> None:
        """After stripping _RELATION_LIST, 'governs' still appears as guidance."""
        stripped = _strip_relation_list(LLM_EXTRACTION_PROMPT)
        assert "governs" in stripped.lower(), (
            "After removing the relation-value list, 'governs' must still appear "
            "as descriptive guidance — not only in the relation listing."
        )

    def test_supersedes_version_has_descriptive_text_beyond_relation_list(self) -> None:
        """After stripping _RELATION_LIST, 'supersedes_version' still appears as guidance."""
        stripped = _strip_relation_list(LLM_EXTRACTION_PROMPT)
        assert "supersedes_version" in stripped.lower(), (
            "After removing the relation-value list, 'supersedes_version' must still appear "
            "as descriptive guidance — not only in the relation listing."
        )
