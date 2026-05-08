# Doc-Writer Quality Test Tightening — False-Green Analysis

> **Owning task:** #1422 — P1-01: Test — verify doc-writer quality redesign AC
> **Date:** 2026-05-08  **Status:** Complete

## 1. Context and Question

Task #1422 was previously built, but the reviewer (on parent #1421) rejected the chain at confidence 0.72. The core failure: the test suite asserts `len(items) == 4` without verifying *which* 4 items — allowing the builder to implement wrong items and still pass green.

**Question:** What additional test assertions are needed to prevent the false-green scenario?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `.owlbear/briefs/draft-doc-writer-quality/brief.md` (lines 38-46) — binding 4-item checklist | 1.0 |
| 2 | `share/skills/w-doc-update/SKILL.md` (lines 36-60) — current (wrong) implementation | 1.0 |
| 3 | Parent #1421 body — Review Evidence section, AC Compliance table | 1.0 |
| 4 | `tests/test_doc_writer_quality_1422.py` — current test file | 1.0 |

## 3. Analysis

### Brief vs Implementation Mismatch

| # | Brief-Defined Item | Implemented Item | Match? |
|---|-------------------|------------------|--------|
| 1 | README Verification | Prose Accuracy | DIVERGED — renamed and broadened |
| 2 | External Attribution | Docstrings | WRONG — docstrings are explicitly out of scope |
| 3 | Research Doc | Attribution and Research Linkage | WRONG — merged items 2+3, lost Research Doc as distinct |
| 4 | Deletion Detection | TODO Marker and Gate Review | WRONG — Deletion Detection dropped entirely |

### Root Cause of False Green

The test `test_checklist_has_exactly_four_items` uses:
```python
items = re.findall(r"### Item \d+", content)
assert len(items) == 4
```

This asserts **count only**, not identity. Any 4 `### Item N` headings pass. The reviewer's manual mutation test confirmed: replacing all 4 items with arbitrary content stays green.

### Test Gaps Identified

| Gap | Severity | Fix |
|-----|----------|-----|
| No assertion on Item 1 identity ("README Verification") | HIGH | Assert `### Item 1: README Verification` present |
| No assertion on Item 2 identity ("External Attribution") | HIGH | Assert `### Item 2: External Attribution` present |
| No assertion on Item 3 identity ("Research Doc") | HIGH | Assert `### Item 3: Research Doc` present |
| No assertion on Item 4 identity ("Deletion Detection") | HIGH | Assert `### Item 4: Deletion Detection` present |
| No assertion that docstrings are absent (out of scope) | HIGH | Assert "Docstrings" not in checklist items |
| No assertion that Deletion Detection behavior exists | MEDIUM | Assert child-task + DR protocol language present |

### Out-of-Scope Docstrings

Brief line 21: `Out of scope: Module docstrings (ruff D100 — separate backlog item)`. The builder's implementation added `### Item 2: Docstrings` directly contradicting this constraint. Tests must assert its absence.

## 4. Recommendation

**Tighten the test suite** with 6 additional/modified assertions that pin item identity, not just count. This is the minimum change to prevent the false-green scenario.

The existing tests for Layer 1/2 verification, TODO markers, gate rules, diagram absence, and doc-audit content are adequate (reviewer rated them COVERED). Only the AC1 checklist identity assertions need strengthening.

Challenge: SKIP — trivial fix-scope research, no recommendation trade-off to challenge.

Confidence: **0.92** — the brief is unambiguous, the mismatch is mechanically verifiable, and the fix is additive (new assertions, no removals).

## 5. Follow-up Tasks

No new tasks needed — existing #1422 returns to test-writer with tightened scope. The implementation tasks (#1423–#1425) already exist and will consume the corrected tests.

**Action for test-writer pass:** Add identity assertions for the 4 brief-defined checklist items and a negative assertion for docstrings. The builder will then fix the skill to match.
