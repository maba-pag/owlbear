# Doc-Audit Prompt Revision — Gap Analysis

> **Owning task:** #1425 — P1-04: Revise doc-audit.prompt.md — TODO resolution + diagram ownership
> **Date:** 2026-05-09  **Status:** Complete

## 1. Context and Question

Task #1425 requires revising `.owlbear/prompts/doc-audit.prompt.md` to add TODO marker batch resolution, diagram ownership, and `describes`-based verification while retaining existing audit dimensions.

The parent #1421's builder pass (commit `4404082c`) already rewrote the file from 272 lines to 68 lines, adding the three new features but gutting the existing audit framework. The #1422 tests (3 assertions for AC3 content) pass on the current file.

**Question:** Does the current file satisfy all 5 AC items, and what implementation approach should the builder take?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `.owlbear/prompts/doc-audit.prompt.md` (current, 68 lines) | 1.0 |
| 2 | Pre-rewrite version (commit `4404082c~1`, 272 lines) | 1.0 |
| 3 | `.owlbear/briefs/draft-doc-writer-quality/brief.md` — binding spec | 1.0 |
| 4 | `tests/test_doc_writer_quality_1422.py` — AC3 test assertions | 1.0 |
| 5 | `share/skills/r-doc-standards/SKILL.md` §4 — dimension definitions | 0.9 |
| 6 | `share/instructions/doc-standards.instructions.md` — routing chain | 0.7 |

## 3. Analysis

### AC Compliance

| AC | Requirement | Current State | Satisfied? |
|----|-------------|---------------|------------|
| 1 | TODO marker batch resolution dimension | §5 present: batch workflow, categories, format | YES |
| 2 | Diagram ownership section | §6 present: full responsibility assigned | YES |
| 3 | `describes`-based diagram verification | §7 present: glob matching, gap reporting | YES |
| 4 | Relax one-at-a-time for TODO batch | Old constraint removed entirely (behavioral contract deleted) | OVER-REMOVED |
| 5 | Retain structural conformance, duplication, placement, audience-fitness dimensions | YAML description mentions them; no explicit sections remain | **NO** |

### Test Coverage vs AC Gap

The #1422 test class `TestFromAC_DocAuditPromptContent` has 3 assertions — all pass. But AC5 ("Retain existing ... dimensions") is untested. The builder's pass satisfies tests while violating AC5.

### What Was Lost in the Rewrite

The pre-rewrite prompt had:

| Feature | Old (272 lines) | Current (68 lines) | AC5 Required? |
|---------|-----------------|---------------------|---------------|
| 8 audit dimensions (D1-D8) with probes | Full sections per dimension | Gone | YES (4 of 8 named) |
| Standards loading instruction | Explicit `r-doc-standards` + `doc-types` load | Gone | Implicit (supports dimensions) |
| Behavioral contract (trust signals, confidence) | Full contract | Gone | Not in AC |
| Finding card format (severity, evidence, rule ID) | Detailed template | Bare list in §4 | Not in AC |
| Out-of-scope file handling | Routing rules | Gone | Not in AC |
| Phase-break rules, re-scan cap | Detailed flow | Gone | Not in AC |

**Critical gap:** `r-doc-standards` §4 says "These eight dimensions are applied by doc-audit" — but the current prompt has no dimension application logic. The chain is broken.

### Implementation Approach Options

| Option | Description | Lines | Confidence |
|--------|-------------|-------|------------|
| A — Full restore + additions | Bring back D1-D8 probes, behavioral contract, finding format. Add new sections. | ~180-200 | 0.65 |
| B — Abbreviated dimensions + additions | Reference table for 8 dimensions (no full probes). Restore standards loading + finding format. Keep new sections. | ~100-120 | **0.85** |
| C — Minimal + dimension reference | Keep current 68-line structure, add one-liner dimension reference to r-doc-standards. | ~75 | 0.45 |

## 4. Recommendation

**Option B — Abbreviated dimensions + additions.** Confidence: **0.85**.

Rationale:
- **AC5 requires** retaining 4 named dimensions. A dimension reference table satisfies this without repeating the full probe methodology already documented in `r-doc-standards`.
- **Standards loading** must be restored — the prompt needs to instruct the agent to load `r-doc-standards` and `doc-types.instructions.md` before auditing.
- **Finding loop** should be kept but simplified. The one-at-a-time constraint should be relaxed specifically for TODO batch (AC4), not removed entirely.
- **KISS-aligned:** The `r-doc-standards` skill is the canonical dimension definition. The prompt should reference, not duplicate.

Key implementation points for builder:
1. Add explicit standards loading instruction (pre-audit gate)
2. Add dimension reference table (8 rows, mapping DIM-ID → name → rule source)
3. Restore finding format minimum (severity + evidence + rule ID)
4. Adjust §4 finding loop: default one-at-a-time, explicit batch exception for TODO markers
5. Retain §5-§7 (TODO batch, diagram ownership, describes-based) as-is

Challenge: SKIP — implementation approach analysis, no controversial trade-off.

## 5. Follow-up Tasks

No new tasks needed. #1425 proceeds to builder with this implementation guidance. Sibling #1424 (agent update) is already in backlog.
