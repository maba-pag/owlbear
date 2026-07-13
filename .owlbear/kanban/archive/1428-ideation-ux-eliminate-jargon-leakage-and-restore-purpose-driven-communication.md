---
id: 1428
title: 'Ideation UX: eliminate jargon leakage and restore purpose-driven communication'
status: archived
priority: medium
created: 2026-05-08T00:58:29.125370+00:00
updated: 2026-05-09T10:55:46.454893+00:00
tags:
- ideation
- ux
- shared-tier
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Rewrite vocabulary and narration directives in ideation agent instruction files to eliminate jargon leakage and restore purpose-driven communication.

## Brief

Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`

## Acceptance Criteria

- [ ] New \"Communication Patterns\" section in `h-ideation/SKILL.md` with vocabulary table, narration principles, transition patterns, boundary heuristic, depth-control cues
- [ ] 4 narration directives rewritten (3 in mediation, 1 in discovery) with co-located annotations
- [ ] 6 before/after pairs included as behavioral specification
- [ ] One critical_rule line added to both user-facing agent files
- [ ] Verification criteria in both workflow skills updated (\"explains purpose\" not \"names component\")
- [ ] Light \"Panel Output Phrasing\" section added to h-ideation-panel
- [ ] Grep-based check: no protocol codes (M3.5, O15) appear in narration guidance without context
- [ ] All changes are behavioral-equivalent (same information reaches user, different framing)

## Files in Scope

- `share/skills/h-ideation/SKILL.md`
- `share/skills/w-ideation-mediation/SKILL.md`
- `share/skills/w-ideation-discovery/SKILL.md`
- `share/agents/ideation-mediator.agent.md`
- `share/agents/ideation-discoverer.agent.md`
- `share/skills/h-ideation-panel/SKILL.md`

## Context

- Research grounding: `.owlbear/research/thinking-companion-framework.md`
- Prior overhaul: `.owlbear/briefs/draft-ideation-overhaul-2026-04-20/`
- Decisions: `.owlbear/briefs/draft-ideation-ux/decisions.md` (D1-D12)
[[2026-05-08]]
## Planning
### Decomposition: Ideation UX jargon elimination
- Tasks created: 5
- Dependency layers: 2
- Phase: 1

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| #1429 | P1-01: Communication Patterns section + vocabulary table in h-ideation/SKILL.md | critical | — | phase-1, scope:shared, ideation, ux |
| #1430 | P1-02: Directive rewrites in w-ideation-mediation/SKILL.md | needed | #1429 | phase-1, scope:shared, ideation, ux |
| #1431 | P1-03: Directive rewrite + tier presentation in w-ideation-discovery/SKILL.md | needed | #1429 | phase-1, scope:shared, ideation, ux |
| #1432 | P1-04: Agent enforcement lines + verification criteria updates | needed | #1429 | phase-1, scope:shared, ideation, ux |
| #1433 | P1-05: Panel Output Phrasing section in h-ideation-panel/SKILL.md | important | — | phase-1, scope:shared, ideation, ux |

### Dependency Graph
```mermaid
graph TD
  1429[\"#1429 Communication Patterns\"]
  1430[\"#1430 Mediation rewrites\"]
  1431[\"#1431 Discovery rewrite\"]
  1432[\"#1432 Agent enforcement\"]
  1433[\"#1433 Panel phrasing\"]
  1429 --> 1430
  1429 --> 1431
  1429 --> 1432
```

### Notes
- All tasks are markdown prose edits (no code, no traditional tests). Verification via grep-based lint (AC #7 of parent).
- #1429 is the foundation — all directive/enforcement tasks depend on the vocabulary table existing first.
- #1433 is independent (panel phrasing is self-contained, no vocabulary dependency).
- Status set to `todo` (brief provides all source content; no further research needed).
- Skipped backlog column intentionally — content is fully specified in brief.
[[2026-05-08]]
## Architecture Review

### Context
Parent task decomposed by planner into 5 subtasks (#1429–#1433). Planning section present — advancing parent per decomposition-complete path.

### Subtask Status
| ID | Title | Status | Notes |
|----|-------|--------|-------|
| #1429 | Communication Patterns section | Task record absent | Deliverable verified in h-ideation/SKILL.md lines 115–388 (vocabulary table, narration principles, transition patterns, boundary heuristic, depth-control cues) |
| #1430 | Mediation directive rewrites | done | All AC passed. Reviewer confidence .94 |
| #1431 | Discovery directive rewrite | Task record absent | Deliverable verified: purpose-framed narration at w-ideation-discovery/SKILL.md:131, vocabulary cross-ref at line 119 |
| #1432 | Agent enforcement + verification | Task record absent | Deliverable verified: critical_rule in mediator.agent.md:50 and discoverer.agent.md:41; verification criteria in mediation:150 and discovery:156 |
| #1433 | Panel Output Phrasing | backlog | Implementation exists (h-ideation-panel/SKILL.md:197–204), stuck in reviewer loop on test-quality AC2/AC5 refinement — continues independently |

### Parent AC Verification
| AC | Evidence | Status |
|----|----------|--------|
| Communication Patterns section with 5 components | h-ideation/SKILL.md lines 115–388 | MET |
| 4 narration directives rewritten | mediation: Step 1.5 (:97), Step 2 (:115), Disclosure Ladder (:50-70); discovery: handoff (:131) | MET |
| 6 before/after pairs | h-ideation/SKILL.md lines 207–260 (Pairs 1–6) | MET |
| Critical rule in both agent files | mediator.agent.md:50, discoverer.agent.md:41 | MET |
| Verification criteria updated | mediation:150, discovery:156 | MET |
| Panel Output Phrasing | h-ideation-panel/SKILL.md:197–204 (implementation done, #1433 test-quality cycle continues) | MET (impl) |
| Grep: no uncontextualized protocol codes | M3.5/O15 appear only in vocabulary table and "Before" examples — narration guidance uses purpose-driven language | MET |
| Behavioral equivalence | Pairs 1–6 demonstrate same info, different framing | MET |

### Verdict: APPROVE
Decomposition complete. All parent AC deliverables exist in the codebase. Subtask #1433 continues independently for test-quality refinement (implementation already in place).
[[2026-05-09]]
## Test-Writer Notes
- Non-impl pass-through: all AC lines reference only non-Python files (SKILL.md, .agent.md).
- No Python implementation intent keywords (implement, class, module, src/, .py, API) found in AC.
- Step 2a heuristic: config/docs only — no tests applicable.
- Additional signal: architecture review in task body verified all 8 ACs are MET; content-verification tests would pass immediately (RED phase impossible).
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Non-implementation task confirmed from existing `## Test-Writer Notes` section (docs/agent-skill wording only; no source implementation required).
- Code changes: none.
- Tests/lint: not run (pass-through path per workflow for non-implementation tasks).
- Action: advanced task directly to review.
[[2026-05-09]]
## Review Evidence
### Scope
- Effective td:0 documentation and agent-instruction review. No executable source files or task-local tests are in scope.
- Parent task reached review as an aggregate of child deliverables. Changed-file scope reconstructed from the task AC, current workspace files, and archived child task records (#1429 to #1433).

### Test Results
- Not applicable for this task shape. Scope is Markdown and agent instruction content only.
- quality-runner was not dispatched because there is no executable surface and scoped mode requires task test paths.

### Lint Results
- Not applicable. No Python or TypeScript files were changed for this parent review scope.

### Coverage
- Not applicable. No executable module changes in scope.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| New Communication Patterns section in h-ideation/SKILL.md with vocabulary table, narration principles, transition patterns, boundary heuristic, depth-control cues | share/skills/h-ideation/SKILL.md:182, :184, :257, :266, :277, :286 | PASS |
| 4 narration directives rewritten with co-located annotations | share/skills/w-ideation-mediation/SKILL.md:50, :61, :70, :99, :117 and share/skills/w-ideation-discovery/SKILL.md:103 | PASS |
| 6 before/after pairs included as behavioral specification | share/skills/h-ideation/SKILL.md:209, :217, :225, :233, :241, :249 | PASS |
| One critical_rule line added to both user-facing agent files | share/agents/ideation-mediator.agent.md:41 and share/agents/ideation-discoverer.agent.md:39 | PASS |
| Verification criteria in both workflow skills updated to purpose-framed checks | share/skills/w-ideation-mediation/SKILL.md:172 and share/skills/w-ideation-discovery/SKILL.md:146 | PASS |
| Light Panel Output Phrasing section added to h-ideation-panel | share/skills/h-ideation-panel/SKILL.md:197, :200, :201, :203 | PASS |
| Grep-based check: no protocol codes (M3.5, O15) appear in narration guidance without context | Codes appear with context in share/skills/h-ideation/SKILL.md:197, :201, :212, :236. User-facing narration lines in share/skills/w-ideation-mediation/SKILL.md:50, :61, :70, :99, :117 and share/skills/w-ideation-discovery/SKILL.md:103 do not surface raw protocol codes | PASS |
| All changes are behavioral-equivalent (same information reaches user, different framing) | Before/after specification in share/skills/h-ideation/SKILL.md:209-256 aligns with the rewritten purpose-framed narration in mediation and discovery evidence above | PASS |

### Test-Writer Audit
- No TestFromAC classes exist for this task.
- Test-writer pass-through is appropriate for this docs-only scope because the AC targets wording in Markdown and agent files, not executable behavior.

### Informational Findings
- The parent task body contains stale child-status notes. It says task record absent for #1429, #1431, and #1432 at .owlbear/kanban/tasks/1428-ideation-ux-eliminate-jargon-leakage-and-restore-purpose-driven-communication.md:98, :100, :101 and says #1433 is backlog at :102.
- Current board artifacts show those child records archived: .owlbear/kanban/archive/1429-p1-01-communication-patterns-section-vocabulary-table-in-h-ideation-skill-md.md:4, .owlbear/kanban/archive/1431-p1-03-directive-rewrite-tier-presentation-in-w-ideation-discovery-skill-md.md:4, .owlbear/kanban/archive/1432-p1-04-agent-enforcement-lines-verification-criteria-updates.md:4, .owlbear/kanban/archive/1433-p1-05-panel-output-phrasing-section-in-h-ideation-panel-skill-md.md:4.
- This is non-blocking for the parent AC because the live files satisfy the required content changes.

### Deductions
- -0.03: no executable quality-runner evidence applicable to docs-only scope
- -0.02: parent task has no task-local builder commit hash; changed-file ownership reconstructed from scope and archived children
- -0.01: architecture-review subtask table is stale relative to the archive state

### Verdict
- PASS
- Confidence: 0.94
- Action: advance to docs
[[2026-05-09]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are OUT-of-scope agent-executable files (SKILL.md, .agent.md); no IN-scope prose docs reference the ideation agent behavior by name |
| 2 | Module docstrings | No | N/A | No Python files in scope |
| 3 | External attribution | No | N/A | Task uses no new external patterns; AC mentions behavioral rewrites derived from brief |
| 4 | Research doc | No | N/A | `.owlbear/research/thinking-companion-framework.md` referenced as prior art in context section — no new research doc produced by this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/ideation.excalidraw` describes glob covers all 6 changed files; footer updated to `Last verified: 2026-05-09 (3d8a33c4)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/h-ideation/SKILL.md | OUT | N/A (agent-executable) |
| share/skills/w-ideation-mediation/SKILL.md | OUT | N/A (agent-executable) |
| share/skills/w-ideation-discovery/SKILL.md | OUT | N/A (agent-executable) |
| share/agents/ideation-mediator.agent.md | OUT | N/A (agent-executable) |
| share/agents/ideation-discoverer.agent.md | OUT | N/A (agent-executable) |
| share/skills/h-ideation-panel/SKILL.md | OUT | N/A (agent-executable) |
| share/diagrams/ideation.excalidraw | IN | Footer updated |

### Files Updated
- share/diagrams/ideation.excalidraw (footer only: `Last verified: 2026-05-09 (3d8a33c4)`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1428-*` files found)
[[2026-05-09]]
## Audit
### Regression Detection
- quality-runner mode full: 572 Python failures, 28 lint errors — ALL from 3 dirty test files (serve/kanban/tests/test_corruption.py, serve/kanban/tests/test_storage.py, serve/mcp-knowledge/tests/test_server.py) uncommitted by other agents' in-progress work. Individual test files pass in isolation. 9 frontend failures in Shell_1344.test.tsx (flaky waitFor timing). Frontend lint clean. No failures attributable to task #1428 (docs-only scope: SKILL.md and .agent.md files).
- regression verdict: PASS (dirty-tree tolerance per pipeline protocol)

### Intent Verification
- scope alignment: PASS (all changes in ideation skill/agent domain: h-ideation, w-ideation-mediation, w-ideation-discovery, h-ideation-panel, ideation-mediator.agent.md, ideation-discoverer.agent.md, ideation.excalidraw)
- purpose match: PASS (vocabulary table, narration rewrites, enforcement rules, verification criteria — all serve stated objective of eliminating jargon leakage)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
8 AC lines, all specific with file references and clear deliverables. Decomposition into 5 subtasks with proper dependency graph (#1429 as foundation). Minor subjectivity in AC #8 (behavioral equivalence) mitigated by before/after pairs as specification. Well-structured parent task.

### Commit Integrity
- upstream commit presence: PASS (5333441d #1429, 5400d210 #1430, 29341853 #1431, 6b66937a #1432, 771c2962 #1433, b5304b89 doc-writer footer)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied. All regression failures attributed to dirty working tree (3 uncommitted test files from other agents). Docs-only task scope has no executable surface.

### Confidence: 1.00
### Action: archive