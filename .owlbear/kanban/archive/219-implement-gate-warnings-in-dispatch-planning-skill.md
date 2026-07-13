---
id: 219
title: Implement gate_warnings in dispatch-planning SKILL.md
status: archived
priority: medium
created: 2026-03-30 15:16:54.620407+02:00
updated: 2026-03-30 21:17:04.108654+02:00
started: 2026-03-30 21:16:12.974056+02:00
completed: 2026-03-30 21:16:12.974056+02:00
tags:
- scope:agents
- quality
- type:config
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add 'Gate failure remediation' section to dispatch-planning SKILL.md after the gate checks section.

## AC
- [ ] New section 'Gate failure remediation' added between 'Gate checks' and 'Filter and prioritize' in Step 2
- [ ] Section instructs planner to collect gate_warnings for tasks excluded by Gate 3 or Gate 4
- [ ] gate_warnings format: array of objects with `id` (int), `gate` (string, one of "Gate 3" or "Gate 4"), `reason` (string, <=120 chars) fields
- [ ] gate_warnings is always emitted (empty array if no failures) — planner stays stateless
- [ ] Step 3 JSON output spec updated: gate_warnings field added as a sibling to dispatch
- [ ] Step 3 rule "Gate names do not appear in the output" amended to: gate names do not appear in dispatch entries; gate failures surface only via gate_warnings
- [ ] Step 3 JSON format example updated to show gate_warnings (both populated and empty-array cases)
- [ ] Gate 5 excluded from gate_warnings (content check, not process check — no false-positive risk)
- [ ] Rejected alternative (auto-move back) documented as a brief note in the new section with rationale (feedback loops, planner read-only constraint)
- [ ] Self-critique checklist updated with a gate_warnings verification item (e.g., "gate_warnings populated for Gate 3/4 exclusions")

## Context
See docs/research/gate-blocked-task-remediation.md S4.
Depends on research from #216 (archived).
Companion task: #220 (orchestration-side tracking, depends_on this task).

[[2026-03-30]] Mon 15:42
## Research
Parent research: docs/research/gate-blocked-task-remediation.md (#216, .85 confidence, 6 sources)

Checklist validated:
1. Theoretical validity: Sound. Extends existing JSON output pattern (retry_hint precedent).
2. Environment audit: N/A, SKILL.md documentation change only.
3. Prior art: Covered by #216 (GitHub stale, GitLab CI, Jenkins, Azure DevOps).
4. Technical feasibility: Confirmed. Skill doc edit reads by LLM.
5. Architecture fit: Extends Step 2 gate checks + Step 3 JSON output. Pairs with #220.
6. Implementation approach: Insert after gate checks, update JSON spec, amend conflicting rule.

Implementation notes for builder:
- Step 3 rule 'Gate names do not appear in the output' MUST be amended to accommodate gate_warnings.
- Self-critique checklist needs a gate_warnings item.
- Insert new section between 'Gate checks' and 'Filter and prioritize' in Step 2.

## Architecture Review
**Verdict:** APPROVED

### AC Refinements Made
- Original AC had 7 lines; refined to 10 for completeness.
- Added explicit types to gate_warnings format (id:int, gate:string, reason:string<=120).
- Split vague "Step 3 updated" into 3 specific lines: add field, amend conflicting rule, update examples.
- Added missing AC for self-critique checklist update (researcher noted but omitted from AC).
- Specified location for rejected-alternative documentation (in the new section itself).

### Architecture Notes
- Extends existing JSON output pattern (retry_hint precedent in Step 3).
- No new system boundaries, no code changes: SKILL.md documentation only.
- type:config tag correct: test-writer pass-through applies.
- Companion #220 (orchestration tracking) has correct depends_on: [219].
- Planner read-only constraint preserved: gate_warnings is output, not mutation.
- The "Gate names do not appear in the output" rule amendment is critical (without it spec contradicts itself).

### Dependencies
- Verified: #216 (parent research) archived.
- Verified: #220 depends_on #219 correct ordering.

[[2026-03-30]] Mon 18:00
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- Passing through to builder.

[[2026-03-30]] Mon 18:27
## Builder Notes
- Files changed: skills/dispatch-planning/SKILL.md
- Non-implementation (type:config) â€” documentation-only changes
- All 10 AC items satisfied
- Commit: a1dcda2

[[2026-03-30]] Mon 20:15
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|--|--|--|--|--|
| 1 | .github/copilot-instructions.md | No | N/A | SKILL.md change only; copilot-instructions.md covers directory table, not dispatch JSON format |
| 2 | Docstrings | No | N/A | No Python files modified; pure SKILL.md documentation |
| 3 | docs/sources/overview.md | No | N/A | No new external patterns; implements findings from #216 research (internal) |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc | No | N/A | Research was produced by #216 (archived), linked in task body; no new research doc for this task |
| 6 | No impact | Yes | Pass | SKILL.md edit only; no external-facing docs changes required |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/219-* files found)

[[2026-03-30]] Mon 21:16
## Audit
### AC Verification
All 10 AC items verified with file evidence (SKILL.md L244-351). Gate failure remediation section placed correctly, gate_warnings format documented with types, always-emitted rule present, Step 3 JSON spec and examples updated, rule amended, Gate 5 excluded, rejected alternative documented, self-critique checklist updated.

### Test Results
- pytest: 1352 passed, 115 failed (all pre-existing, none in task scope), 5 collection errors (pre-existing import issues)
- ruff: N/A (no Python files changed)

### AC Quality: 5/5
Specific, complete AC with exact types, locations, format specs. Architect refinements well-documented.

### Deduction breakdown: none (all 10 AC items verified, no lint issues, AC quality 5, reviewer evidence present, no in-scope test failures)
### Confidence: 1.00
### Action: archived

[[2026-03-30]] Mon 21:16
## Audit
### AC Verification
All 10 AC items verified with file evidence (SKILL.md L244-351). Gate failure remediation section placed correctly, gate_warnings format documented with types, always-emitted rule present, Step 3 JSON spec and examples updated, rule amended, Gate 5 excluded, rejected alternative documented, self-critique checklist updated.

### Test Results
- pytest: 1352 passed, 115 failed (all pre-existing, none in task scope), 5 collection errors (pre-existing import issues)
- ruff: N/A (no Python files changed)

### AC Quality: 5/5
Specific, complete AC with exact types, locations, format specs. Architect refinements well-documented.

### Deduction breakdown: none (all 10 AC items verified, no lint issues, AC quality 5, reviewer evidence present, no in-scope test failures)
### Confidence: 1.00
### Action: archived

[[2026-03-30]] Mon 21:17
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 556f1b3 | chore | kanban/tasks/219-*.md | #219 |
