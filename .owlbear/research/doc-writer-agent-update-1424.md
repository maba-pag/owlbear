# Doc-Writer Agent Update — Diagram Removal & Critical Rules Alignment

> **Owning task:** #1424 — P1-03: Update doc-writer.agent.md — remove diagram responsibility
> **Date:** 2026-05-09  **Status:** Complete

## 1. Context and Question

Task #1424 requires updating `share/agents/doc-writer.agent.md` to (1) remove all diagram/Excalidraw references, (2) align `critical_rules` with the new `w-doc-update` v3 behavior, (3) keep the fact-checking persona, and (4) avoid functional regressions.

**Question:** What is the current gap between the agent file and the required state?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `share/agents/doc-writer.agent.md` — current agent definition | 1.0 |
| 2 | `share/skills/w-doc-update/SKILL.md` — already-shipped v3 skill | 1.0 |
| 3 | `.owlbear/briefs/draft-doc-writer-quality/brief.md` — binding design | 0.9 |
| 4 | `tests/test_doc_writer_quality_1422.py` — 56 passing assertions | 0.9 |

## 3. Analysis

### AC-by-AC Gap Assessment

| AC | Required | Current State | Gap? |
|----|----------|---------------|------|
| 1 — Remove diagrams | Zero diagram/excalidraw/`.excalidraw` refs | Zero found (grep-verified) | No |
| 2 — Align critical_rules | Reference 4-item checklist, convention mapping, TODO markers, gate-blocking | Generic "checklist" mention, no specifics | **Yes** |
| 3 — Persona | Fact-checking/verification, no diagram editor | Correct — "technical editor at regulated-industry publisher" | No |
| 4 — No regressions | tools, pipeline_position, agents, output_format intact | All present, structurally sound | No |

### AC #2 — Required Critical Rules Changes

Current `critical_rules` (6 items):
1. Follow w-doc-update skill ✅ (adequate — delegates to skill)
2. Read r-pipeline-protocol ✅
3. Reject if upstream review evidence missing ✅
4. Never modify application logic ✅
5. Every checklist item needs evidence — **too vague**, should name the 4 items
6. Clean scratch files ✅

**Needed additions/changes to item 5 or new rules:**
- Name the 4 checklist items: README Verification, External Attribution, Research Doc, Deletion Detection
- Reference convention-based mapping (`serve/{pkg}/src/**` → `serve/{pkg}/README.md`)
- Reference TODO marker insertion for pre-existing issues
- Reference gate-blocking: task-caused unverified content blocks, pre-existing passes

### Implementation Complexity

Surgical edit to `critical_rules` section only — ~6 lines changed/added. No structural changes. Existing tests will continue to pass (they test for diagram absence, not critical_rules content).

## 4. Recommendation

Builder should update `critical_rules` to replace the generic "Every checklist item needs evidence" with specific rules naming the 4-item checklist, convention mapping, TODO markers, and gate-blocking behavior. Keep the existing 5 rules intact; expand/replace item 5.

Challenge: SKIP — trivial scope, single-file edit with unambiguous AC, no trade-off to challenge.

Confidence: **0.95** — AC is explicit, gap is mechanical, dependency (w-doc-update v3) is already shipped and passing tests.

## 5. Follow-up Tasks

No new tasks needed. #1424 itself is the implementation task — advances to backlog for architect review. Sibling #1425 (doc-audit prompt revision) already exists.
