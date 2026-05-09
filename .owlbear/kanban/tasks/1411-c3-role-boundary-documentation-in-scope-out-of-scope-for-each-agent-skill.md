---
id: 1411
title: 'C3: Role boundary documentation — in-scope/out-of-scope for each agent skill'
status: review
priority: important
created: 2026-05-07T23:16:25.269760+00:00
updated: 2026-05-09T09:55:08.132459+00:00
tags:
- pipeline
- ws-roles
- scope:agents
parent: 1403
depends_on:
- 1405
- 1406
- 1407
- 1409
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: Each pipeline agent skill file contains an explicit "In Scope / Out of Scope" section
P2: Agents covered: planner, architect/challenger, test-writer, builder, reviewer, auditor, doc-writer
P2: Boundaries are consistent across agents — no overlapping mandates, no uncovered gaps
P2: Boundaries reflect the post-rethink division of responsibilities (A2, A3, B1, C1 changes incorporated)
P3: Verification by artifact inspection of each agent's skill file; cross-reference check for consistency

## Scope

**In scope:** Adding boundary sections to all pipeline agent skills
**Out of scope:** Changing agent behavior (already done in A2, A3, B1, C1)
[[2026-05-09]]
## Planning

Created follow-up task #1471 "Add In Scope / Out of Scope sections to all pipeline agent skill files" at research status.

- Parent: #1403
- Depends on: #1411
- Tags: pipeline, ws-roles, scope:agents
- Priority: important
- 7 target skill files, P2-tier AC, content sourced from research doc §3.3
[[2026-05-09]]
## Research
- Research doc: .owlbear/research/1411-role-boundary-documentation.md
- Sources: 10 studied (all internal), 10 high-relevance
- Recommendation: Add ## Scope sections (In Scope / Out of Scope) to all 7 pipeline agent skill files using proposed format and content (confidence: .90)
- Follow-up: #1471 created at research (add boundary sections to skill files)
- Overlap analysis: zero overlapping mandates found across 6 boundary pairs
- Gap analysis: zero uncovered gaps; security scanning transitional gap documented (D2 dependency)
[[2026-05-09]]
## Test-Writer Notes

- **Test file:** `tests/test_agent_scope_boundaries_1411.py`
- **Commit:** `90edd62c` — test: add scope-boundary tests for pipeline agent skills (#1411, test-writer)

### Test Classes

| Class | Category | Tests |
|-------|----------|-------|
| `TestFromAC_ScopeSection` | Structure | 3 × 7 = 21 (parametrized per agent) |
| `TestFromAC_AgentCoverage` | Coverage | 7 (parametrized per agent) |
| `TestFromAC_ScopeContent` | Content quality | 4 × 7 = 28 (parametrized; 14 skip when sections absent) |
| `TestFromAC_ScopePosition` | Placement | 7 (parametrized per agent) |
| `TestFromAC_BoundaryConsistency` | Consistency/cross-ref | 10 (non-parametrized) |

**Total: 59 FAIL, 0 PASS, 14 skipped (skip-when-no-bullets, correctly skipped in RED) — ruff clean**

### AC Coverage

| AC | Tests |
|----|-------|
| P1: Each skill has explicit In Scope / Out of Scope section | `test_has_top_level_scope_heading`, `test_has_in_scope_subsection`, `test_has_out_of_scope_subsection` (all 7 agents) |
| P2: Agents covered — planner, architect, test-writer, builder, reviewer, auditor, doc-writer | `TestFromAC_AgentCoverage::test_agent_skill_has_scope_section` (parametrized × 7) |
| P2: Consistent boundaries — no overlapping mandates | `TestFromAC_BoundaryConsistency` — 10 targeted cross-ref checks (AC quality, test writing, implementation, full-suite, docs, code review all assigned exactly once) |
| P2: Out-of-scope items name the responsible agent (em-dash convention) | `test_out_of_scope_bullets_have_em_dash_attribution`, `test_out_of_scope_attributions_name_known_agents` |
| P2: Post-rethink responsibilities reflected (A2/A3/B1/C1) | `TestFromAC_BoundaryConsistency` — specific agent/responsibility assertions match research §3.3 tables |
| P3: Scope section placement before Step 0 | `TestFromAC_ScopePosition::test_scope_precedes_first_workflow_step` (× 7) |

Agents covered: planner (w-task-decomposition), architect (w-arch-review), test-writer (w-tdd-red), builder (w-tdd-green), reviewer (w-code-review), auditor (w-task-verification), doc-writer (w-doc-update).
[[2026-05-09]]
## Builder Notes
- Implementation: Added explicit `## Scope` sections with `### In Scope` and `### Out of Scope` bullets to all required pipeline skill files:
  - `share/skills/w-task-decomposition/SKILL.md`
  - `share/skills/w-arch-review/SKILL.md`
  - `share/skills/w-tdd-red/SKILL.md`
  - `share/skills/w-tdd-green/SKILL.md`
  - `share/skills/w-code-review/SKILL.md`
  - `share/skills/w-task-verification/SKILL.md`
  - `share/skills/w-doc-update/SKILL.md`
- Scope wording ensures out-of-scope bullet attribution uses em-dash owner format and known role labels (e.g., test-writer, builder, reviewer, auditor, doc-writer).
- Tests: `tests/test_agent_scope_boundaries_1411.py` via quality-runner — 73 passed, 0 failed, 0 skipped.
- Coverage: N/A for this docs-only skill-file update (task test suite is assertion-based over markdown artifacts).
- ruff: clean (no violations in scoped lint run).
- Evidence summary: RED was verified first (59 failed, 14 skipped pre-change), then GREEN confirmed after edits (73 passed).
- Commit: `550f69de` — docs: add role scope boundaries to pipeline skills (#1411, builder).