---
id: 1471
title: Add In Scope / Out of Scope sections to all pipeline agent skill files
status: backlog
priority: important
created: 2026-05-09T08:33:41.860392+00:00
updated: 2026-05-09T16:24:26.862379+00:00
tags:
- pipeline
- ws-roles
- scope:agents
- agent
parent: 1403
depends_on:
- 1411
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)
Research: `.owlbear/research/1411-role-boundary-documentation.md`

## Objective

Add `## Scope` sections (with `### In Scope` and `### Out of Scope` subsections) to 7 pipeline agent skill files. Content sourced from the research doc §3.3.

## Target Files

1. `share/skills/w-task-decomposition/SKILL.md` (planner)
2. `share/skills/w-arch-review/SKILL.md` (architect)
3. `share/skills/w-tdd-red/SKILL.md` (test-writer)
4. `share/skills/w-tdd-green/SKILL.md` (builder)
5. `share/skills/w-code-review/SKILL.md` (reviewer)
6. `share/skills/w-task-verification/SKILL.md` (auditor)
7. `share/skills/w-doc-update/SKILL.md` (doc-writer)

## Acceptance Criteria

P1: Each of the 7 skill files contains a `## Scope` section with `### In Scope` and `### Out of Scope` subsections
P2: Section is placed between the skill description paragraph and `## Step 0 — Setup`
P2: Each "Out of Scope" bullet names the responsible agent
P2: Content matches the boundaries defined in `.owlbear/research/1411-role-boundary-documentation.md` §3.3
P3: Verification by artifact inspection of each skill file
[[2026-05-09]]
## Research

- Research doc: .owlbear/research/1411-role-boundary-documentation.md (from parent #1411, still current)
- Sources: 10 internal (7 skill files + research doc + brief + pipeline protocol), 0 external
- Validation finding: All 7 target files already have `## Scope` / `### In Scope` / `### Out of Scope` sections in the correct position (after description, before Step 0). Structural AC (P1) is satisfied.
- Content delta: Current sections are condensed (2–3 bullets per subsection) vs. §3.3 tables (5–6 items each). Missing items include pass-through variants, dispatch patterns (code-reader, challenger), scoring duties, consolidation-test backstops, and specific routing responsibilities. Whether the condensed form satisfies AC P2 ("Content matches §3.3") is an architect/builder decision — no new research needed.
- Recommendation: Expand In Scope bullets to include workflow-specific mechanisms (pass-through, dispatch, reject routing) and expand Out of Scope to cover all §3.3 cross-references. Estimated delta: ~5 additional bullets per file. Confidence: .85
- No follow-up tasks created — the implementation task IS this task; architect should evaluate the content delta against AC P2 and adjust scope if needed.
[[2026-05-09]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: expand scope sections in 7 skill files |
| Interface clarity | PASS | AC references specific §3.3 tables as content source; "matches" is unambiguous given the tabular reference |
| Dependency correctness | PASS | #1411 archived (done); research doc exists at expected path |
| Module layering | N/A | No code — markdown skill files only |
| TDD compliance | N/A | Non-impl task, tagged `agent` for pass-through |
| KISS/YAGNI | PASS | Straightforward content expansion, no new abstractions |
| Premise challenge | PASS | Brief #1403 mandated scope sections; §3.3 provides authoritative content; condensed existing sections need expanding |
| Pattern consistency | PASS | Follows existing skill file structure (## Scope already present in all 7 files) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | All agent/skill domain |

### Failure Mode Map
N/A — no codepaths.

### Design Diverge
- Trigger: skipped — single approach (expand bullets to match §3.3 tables), no competing alternatives.

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0 (non-impl markdown edits)

### Test Depth
- All AC lines: td:0 (markdown content changes, no testable Python interface)
- Max depth: 0
- Test-writer: SKIP

### Codebase Verification
- Confirmed all 7 target files already have `## Scope` sections in correct position (after description, before Step 0)
- Current state: 2 In Scope + 3 Out of Scope bullets per file (condensed)
- §3.3 target: 5–6 items per subsection per agent
- Delta: ~3 additional In Scope + ~2-3 additional Out of Scope bullets per file
- Missing items confirmed: pass-through variants, dispatch patterns (code-reader, challenger), scoring duties, consolidation-test backstops, routing responsibilities
- Non-impl tag `agent` added for test-writer pass-through

### AC Annotations
- P1: structural presence (td:0)
- P2: placement (td:0)
- P2: attribution format (td:0)
- P2: content match to §3.3 (td:0)
- P3: artifact inspection (td:0)

### Verdict: APPROVE
### Action Taken: Tagged `agent` for non-impl pass-through. AC validated against codebase and research doc. All td:0. Advanced to todo.
[[2026-05-09]]
Architecture review complete. All criteria pass. Non-impl task (markdown skill file edits only) — tagged `agent` for test-writer pass-through. All AC lines td:0, challenger skipped. Dependency #1411 confirmed done. Codebase verified: sections exist in condensed form, builder expands to match §3.3 tables.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All 7 AC lines annotated td:0 by architect (markdown-only changes to skill files).
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Validation: Task body contains Test-Writer pass-through note indicating markdown-only scope documentation update task.
- Files changed: none.
- Tests: not applicable (non-implementation pass-through).
- Coverage: not applicable.
- ruff: not applicable.
- Passing through to review.
[[2026-05-09]]
## Review Evidence
### Test Results
- Quality-runner skipped. All AC lines are td:0 and this task is verified by markdown artifact inspection, not executable tests.

### Lint Results
- N/A. Review scope is limited to seven SKILL.md files.

### Coverage
- N/A. No executable code path is in scope.

### Builder Evidence Assessment
- Builder notes say "Files changed: none" and "no code changes needed".
- Direct artifact inspection contradicts that report. The live Scope sections are still condensed summaries and do not carry the full boundary content bound by .owlbear/research/1411-role-boundary-documentation.md section 3.3.

### Blocking Findings
1. AC P2 (content match to section 3.3) is not satisfied.
   - Planner Scope remains a 2-in / 3-out summary at share/skills/w-task-decomposition/SKILL.md:13-24 and omits required section 3.3 rows such as "Draft AC using h-ac-quality rules" and "Moving tasks to todo - architect" from .owlbear/research/1411-role-boundary-documentation.md:62-65.
   - Architect Scope remains a 2-in / 3-out summary at share/skills/w-arch-review/SKILL.md:13-24 and omits required section 3.3 rows such as "Validate AC quality via challenger dispatch", "Approve backlog to todo", and "Design diverge when 2 or more valid approaches exist" from .owlbear/research/1411-role-boundary-documentation.md:71-76.
   - Test-writer Scope remains a 2-in / 3-out summary at share/skills/w-tdd-red/SKILL.md:13-24 and omits required section 3.3 rows such as "Non-impl pass-through (tag-based)", "Depth-zero pass-through", and "Direct-to-review advance" from .owlbear/research/1411-role-boundary-documentation.md:83-86.
   - Builder Scope remains a 2-in / 3-out summary at share/skills/w-tdd-green/SKILL.md:13-24 and omits required section 3.3 rows such as "Non-impl pass-through" and "Reject to test-writer (wrong interface) or architect (wrong AC)" from .owlbear/research/1411-role-boundary-documentation.md:94-95.
   - Reviewer Scope remains a 2-in / 3-out summary at share/skills/w-code-review/SKILL.md:15-26 and omits required section 3.3 rows such as "Builder evidence consistency check" and "PASS confirmation statement for auditor traceability" from .owlbear/research/1411-role-boundary-documentation.md:106-107.
   - Doc-writer Scope remains a 2-in / 3-out summary at share/skills/w-doc-update/SKILL.md:14-25 and omits required section 3.3 rows such as "Research doc linkage verification" and "Deletion detection (orphaned references)" from .owlbear/research/1411-role-boundary-documentation.md:115-116.
   - Auditor Scope remains a 2-in / 3-out summary at share/skills/w-task-verification/SKILL.md:13-24 and omits required section 3.3 rows such as "Architect quality scoring (1-5)" and "Commit kanban/decision files after archival" from .owlbear/research/1411-role-boundary-documentation.md:125-128.
2. A direct retry to in-progress would dead-loop.
   - The task file is tagged agent at .owlbear/kanban/tasks/1471-add-in-scope-out-of-scope-sections-to-all-pipeline-agent-skill-files.md:8-12, the architecture note explicitly added that tag for pass-through at .owlbear/kanban/tasks/1471-add-in-scope-out-of-scope-sections-to-all-pipeline-agent-skill-files.md:95-107, and the current Test-Writer note says "Non-implementation task" at .owlbear/kanban/tasks/1471-add-in-scope-out-of-scope-sections-to-all-pipeline-agent-skill-files.md:110.
   - Builder Step 0a auto-skips any task whose Test-Writer note contains "Non-implementation task" or "non-impl pass-through" at share/skills/w-tdd-green/SKILL.md:34-38.
   - The td:0 pass-through path in share/skills/w-tdd-red/SKILL.md:99-103 would still skip test writing without triggering builder auto-skip, but the current non-implementation path at share/skills/w-tdd-red/SKILL.md:48 is what is recorded in the task body.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| P1: Each of the 7 skill files contains a Scope section with In Scope and Out of Scope subsections | share/skills/w-task-decomposition/SKILL.md:13-20; share/skills/w-arch-review/SKILL.md:13-20; share/skills/w-tdd-red/SKILL.md:13-20; share/skills/w-tdd-green/SKILL.md:13-20; share/skills/w-code-review/SKILL.md:15-22; share/skills/w-task-verification/SKILL.md:13-20; share/skills/w-doc-update/SKILL.md:14-21 | PASS |
| P2: Section is placed between the description paragraph and Step 0 | Scope sections end immediately before Step 0 at share/skills/w-task-decomposition/SKILL.md:26; share/skills/w-arch-review/SKILL.md:26; share/skills/w-tdd-red/SKILL.md:26; share/skills/w-tdd-green/SKILL.md:26; share/skills/w-code-review/SKILL.md:28; share/skills/w-task-verification/SKILL.md:26; share/skills/w-doc-update/SKILL.md:27 | PASS |
| P2: Each Out of Scope bullet names the responsible agent | Out of Scope bullets at share/skills/w-task-decomposition/SKILL.md:22-24; share/skills/w-arch-review/SKILL.md:22-24; share/skills/w-tdd-red/SKILL.md:22-24; share/skills/w-tdd-green/SKILL.md:22-24; share/skills/w-code-review/SKILL.md:24-26; share/skills/w-task-verification/SKILL.md:22-24; share/skills/w-doc-update/SKILL.md:23-25 all name a specific downstream owner | PASS |
| P2: Content matches the boundaries defined in .owlbear/research/1411-role-boundary-documentation.md section 3.3 | Research rows at .owlbear/research/1411-role-boundary-documentation.md:62-128 remain only in the research doc; the seven Scope sections above still contain condensed 2-in / 3-out summaries and omit required rows | FAIL |
| P3: Verification by artifact inspection of each skill file | Reviewer inspected all seven target skill files, the research doc, the parent brief, and the task file | PASS |

### Deductions
| Reason | Deduction |
|---|---|
| Bound section 3.3 content not propagated into the seven Scope sections | -0.45 |
| Builder evidence contradicted by live artifact inspection | -0.10 |
| Direct builder retry would repeat the same skip because of current pass-through tagging and notes | -0.15 |

### Verdict
- Confidence: 0.30
- Verdict: FAIL
- Action: Reject to backlog for architect reclassification and AC/routing refinement before another build cycle.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Remove the non-implementation pass-through classification from this task and keep it on the td:0 no-test route only, so the builder does not auto-skip again | .owlbear/kanban/tasks/1471-add-in-scope-out-of-scope-sections-to-all-pipeline-agent-skill-files.md; share/skills/w-tdd-red/SKILL.md; share/skills/w-tdd-green/SKILL.md | agent tag and non-implementation notes at the task file lines 8-12, 95-110; builder auto-skip rule at share/skills/w-tdd-green/SKILL.md:34-38; td:0 pass-through alternative at share/skills/w-tdd-red/SKILL.md:99-103 |
| 2 | architect | Refine the task guidance so the next builder cycle must expand all seven Scope sections to include the missing section 3.3 boundary rows before the task returns to todo | .owlbear/kanban/tasks/1471-add-in-scope-out-of-scope-sections-to-all-pipeline-agent-skill-files.md; share/skills/w-task-decomposition/SKILL.md; share/skills/w-arch-review/SKILL.md; share/skills/w-tdd-red/SKILL.md; share/skills/w-tdd-green/SKILL.md; share/skills/w-code-review/SKILL.md; share/skills/w-task-verification/SKILL.md; share/skills/w-doc-update/SKILL.md; .owlbear/research/1411-role-boundary-documentation.md | live Scope sections remain condensed at the cited line ranges while the bound section 3.3 rows remain only in the research doc at lines 62-128 |

### Observations
- P1, placement, and responsible-agent attribution are already satisfied. The failure is limited to the bound section 3.3 content omission plus the current pass-through routing defect.