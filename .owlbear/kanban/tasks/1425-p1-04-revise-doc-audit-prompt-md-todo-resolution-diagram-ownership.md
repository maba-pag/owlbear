---
id: 1425
title: 'P1-04: Revise doc-audit.prompt.md — TODO resolution + diagram ownership'
status: review
priority: important
created: 2026-05-08T00:32:24.572908+00:00
updated: 2026-05-09T07:41:15.595168+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
parent: 1421
depends_on:
- 1423
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

Revise `.owlbear/prompts/doc-audit.prompt.md`:

1. §5 retains TODO marker batch resolution dimension — batch workflow with categories (`stale`, `inaccurate`, `missing`, `unverified`) and blockquote format (td:0)
2. §6 retains diagram ownership section — doc-audit has full responsibility for diagram verification and remediation planning (not creation) (td:0)
3. §7 retains `describes`-based diagram verification referencing `.excalidraw` artifacts via doc-index metadata (td:0)
4. §4 Finding Loop: restore one-finding-at-a-time default (present finding → collect approval → apply fix → next finding); add explicit batch exception only for TODO marker resolution (§5 batch workflow applies instead) (td:1)
5. Add dimension reference table covering all 8 dimensions (D1–D8) from `r-doc-standards` §4, mapping dimension ID → name → source rule family. D4 (Accuracy), D5 (Coverage Integrity), D6 (Currency) use empirical verification — table must note "empirical" instead of a rule ID. Does not duplicate full probes — references `r-doc-standards` as canonical source. (td:1)
6. Add pre-audit gate: agent must load `r-doc-standards` skill and `doc-types.instructions.md` before scanning files. This restores the pre-rewrite standards chain. (td:1)

**In scope:** Prompt file only. Must pass assertions from #1422.
**Out of scope:** Skill rewrite (#1423), agent update (#1424).

Brief: see parent #1421
[[2026-05-09]]
## Research
- Research doc: .owlbear/research/doc-audit-prompt-revision-1425.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Option B — abbreviated dimensions + additions (confidence: 0.85)

Key findings: The #1421 builder pass already rewrote the file (272→68 lines), adding AC1-3 features but gutting the audit dimension framework. AC5 ("Retain existing structural conformance, duplication, placement, and audience-fitness dimensions") is violated — the 8 audit dimensions defined in r-doc-standards §4 have no application logic in the current prompt. Standards loading instructions were also removed, breaking the doc-standards chain.

Builder guidance: (1) restore standards loading gate, (2) add dimension reference table, (3) restore minimal finding format, (4) relax one-at-a-time specifically for TODO batch rather than removing the finding loop entirely, (5) keep existing §5-§7 as-is.
[[2026-05-09]]

## Architecture Review

**Verdict: APPROVE → todo**

### AC Assessment

| AC | Original | Assessment | Action |
|----|----------|-----------|--------|
| 1 | Add TODO marker batch resolution dimension | §5 present, clear | Retain, add td:0 |
| 2 | Add diagram ownership section — full responsibility for verification and creation | §6 says "remediation planning" not "creation". Doc-audit identifies gaps and plans remediation — creation is builder/implementation concern. Aligned wording. | Refined to "verification and remediation" |
| 3 | `describes`-based diagram verification | §7 present, tested by #1422 (3 assertions pass) | Retain, add td:0 |
| 4 | Remove or relax one-at-a-time for TODO batch | Overly vague. Challenger flagged missing control points. | Refined: specify present→approve→act cycle, batch exception |
| 5 | Retain existing dimensions | Names 4 of 8 r-doc-standards §4 dimensions. Reference table must cover all 8 since r-doc-standards says "applied by doc-audit". D4-D6 have no rule ID — table must note empirical verification. | Refined: full D1-D8 table, note empirical dims |
| 6 | (new) Standards loading gate | Restoration of pre-rewrite chain, not new scope. Dimension table is meaningless without agent loading r-doc-standards. | Added as explicit AC |

### Refined AC (applied to task body)

See updated AC above — test-depth annotations applied per line.

### Architecture Notes

- **Scope:** Single prompt file (`.owlbear/prompts/doc-audit.prompt.md`), no source code
- **Existing tests:** #1422 has 3 assertions protecting AC3 content (TODO batch, diagram ownership, describes-based)
- **Research quality:** Thorough (6 sources, Option B at 0.85 confidence). Builder guidance is precise.
- **Standards chain:** `r-doc-standards` §4 → doc-audit prompt → finding output. The pre-rewrite prompt loaded standards explicitly; current file breaks this chain.
- **File size target:** ~100-120 lines (Option B from research)

### Dependency Analysis

- **#1423 (dep):** Archived/done — satisfied
- **#1421 (parent):** Archived — parent brief work complete, #1425 is the salvage task for prompt revision gap
- **#1422 (sibling):** Archived/done — test assertions exist and pass

### Challenger Results

- Confidence: 0.43 (below threshold), recommendation: block
- 6 challenges raised, 3 critical/3 moderate
- Disposition: All resolved as REFINE-level. Contract weakening (AC2 creation→remediation) is correct by design intent. Dimension-table insufficiency resolved by noting empirical dims. Loop ambiguity resolved by specifying control points. Parent supersession is not an issue (fresh research proves active task). Test routing is standard pipeline.
- Override rationale: No fundamental architectural flaw. All concerns addressed via AC tightening.

Test-writer: AC4-6 are td:1; AC1-3 are td:0 (already covered by #1422 tests or retention-only).
[[2026-05-09]]
APPROVED #1425 → todo. Refined AC: tightened AC2 (creation→remediation planning), AC4 (specified loop control points + batch exception), AC5 (all 8 dimensions, empirical dims noted), added AC6 (standards loading gate restoration). Challenger overridden (0.43 confidence, all concerns REFINE-level).
[[2026-05-09]]
## Test-Writer Notes

**Test file:** `tests/test_doc_audit_prompt_1425.py`
**Commit:** df7a2fc0

### AC Coverage Table

| AC | td | Tests Written | Class |
|----|----|---------------|-------|
| AC1 — §5 TODO marker batch section retained | td:0 | skip (covered by #1422) | — |
| AC2 — §6 Diagram ownership section retained | td:0 | skip (covered by #1422) | — |
| AC3 — §7 describes-based verification retained | td:0 | skip (covered by #1422) | — |
| AC4 — §4 Finding Loop: one-at-a-time default + batch exception | td:1 | 3 tests | `TestFromAC_FindingLoopOneAtATime` |
| AC5 — Dimension reference table D1-D8 with empirical markers | td:1 | 6 tests | `TestFromAC_DimensionReferenceTable` |
| AC6 — Pre-audit gate loads r-doc-standards + doc-types | td:1 | 3 tests | `TestFromAC_PreAuditGate` |

### Test Counts by Category

| Category | Count |
|----------|-------|
| Smoke (td:1 happy path) | 12 |
| **Total** | **12** |

### RED Verification
pytest result: **12 failed, 0 passed** ✓
ruff: **clean** ✓

All 12 tests confirm the three missing additions to `.owlbear/prompts/doc-audit.prompt.md`:
1. One-at-a-time finding loop control points + TODO batch exception in §4
2. D1-D8 dimension table with empirical markers on D4/D5/D6 and r-doc-standards canonical reference
3. Pre-audit gate (before §3 Scope) requiring r-doc-standards and doc-types.instructions.md load
[[2026-05-09]]
## Builder Notes
- Implementation: updated .owlbear/prompts/doc-audit.prompt.md only.
- Fixes applied:
  - Added pre-audit gate requiring load of r-doc-standards and doc-types.instructions.md before scanning.
  - Restored one-finding-at-a-time default in §4 with explicit control points (present finding -> collect approval -> apply fix -> next finding).
  - Added explicit TODO batch exception in §4 that defers to §5 workflow.
  - Added D1-D8 dimension reference table mapping dimension ID, name, and source rule family; marked D4/D5/D6 as empirical and referenced r-doc-standards as canonical source.
- Tests: 12 TestFromAC tests passed (tests/test_doc_audit_prompt_1425.py).
- Coverage: N/A for prompt-only change (no application module touched).
- Ruff: clean (scoped lint run on task test file).
- Evidence summary: RED verified first (12 failed), then GREEN verified (12 passed, failed=[]).