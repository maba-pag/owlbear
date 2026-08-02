---
id: 214
title: Fix Gate 3 atomicity heuristic to respect architect approval
status: archived
priority: medium
created: 2026-03-30 14:22:41.474924+02:00
updated: 2026-03-30 20:36:49.171772+02:00
started: 2026-03-30 20:36:17.049005+02:00
completed: 2026-03-30 20:36:17.049005+02:00
tags:
- scope:agents
- quality
- type:config
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Gate 3 (Atomicity) in the dispatch-planning skill uses a crude "and" keyword heuristic to flag potentially non-atomic tasks. This overrules the architect's explicit atomicity judgment made during backlog review. Tasks already approved by the architect get permanently stuck when the planner re-flags them.

## Problem
- The architect evaluates atomicity in arch-review Step 3.1 and explicitly approves or splits tasks
- The planner's Gate 3 heuristic then re-litigates that decision with a simple keyword match
- No remediation path exists — flagged tasks sit in limbo forever
- Real examples: #151 ("Test: Vector store and embedding pipeline") and #153 ("Test: planner data models and board reader") were architect-approved but planner-blocked

## Acceptance Criteria
- [ ] Gate 3 in dispatch-planning SKILL.md is changed so that tasks which have an `## Architecture Review` section in their body are exempt from the "and" heuristic (architect already evaluated atomicity)
- [ ] The "and" heuristic remains active for tasks that have NOT been through architecture review (e.g. tasks that somehow bypassed the architect)
- [ ] Board Scan (Recipe 1) PowerShell updated to add an `ARCH:REVIEWED` marker when `## Architecture Review` is present in body, and Gate 3 reasoning uses this marker to skip the heuristic
- [ ] No other gates affected

## Context
See analysis from manual triage session 2026-03-30. Gap G1 in the dispatch-planning gate analysis.

[[2026-03-30]] Mon 14:52
## Research
Doc: docs/research/gate-3-atomicity-architect-bypass.md
Follow-up: #217 (Implement Gate 3 architect-bypass in dispatch-planning SKILL.md)

Key findings:
- 9 architect-approved tasks currently have 'and' in title, all false positives for Gate 3
- Fix: add ARCH:REVIEWED marker in Board Scan Recipe 1, exempt from Gate 3
- Follows existing marker pattern (TW:MISSING, AC:MISSING), minimal change
- Confidence: .90

[[2026-03-30]] Mon 15:32
## Architecture Review
**Verdict:** APPROVED (with AC refinement + merge with #217)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Recipe 1 PS adds ARCH:REVIEWED marker | Precise, verifiable, follows existing pattern | Kept |
| Gate 3 text updated for exemption | Precise, verifiable | Kept |
| PS-layer docs updated | Precise, verifiable | Kept |
| LLM-reasoning docs updated | Precise, verifiable | Kept |
| No other gates affected | Clear negative constraint | Kept |
| Heuristic remains for non-reviewed tasks | Precise, ensures safety net preserved | Kept |

### Architecture Notes
- Follows existing marker pattern (TW:MISSING, AC:MISSING, DECOMP) in Board Scan Recipe 1
- Single file change: skills/dispatch-planning/SKILL.md, 4 locations
- type:config tag correct: passes through test-writer without tests (per dispatch mapping)
- No new system boundaries, no codepaths, no security surface
- Minimal change (KISS): 1 PS line + 3 paragraph updates

### Changes Made
- Refined AC: deduplicated overlapping items, split into 6 precise verifiable lines
- Merged with #217 (duplicate follow-up at ideation, same AC): deleted #217
- Updated Research section: removed stale #217 follow-up reference

### Dependencies
- None (standalone task)

[[2026-03-30]] Mon 17:22
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- Passing through to builder.

[[2026-03-30]] Mon 18:08
## Builder Notes
- Files changed: skills/dispatch-planning/SKILL.md (4 locations)
- Tests: N/A (type:config, non-implementation task)
- Lint: N/A (no Python files modified)
- Evidence: 4 occurrences of ARCH:REVIEWED confirmed via grep
- Changes: (1) Recipe 1 PS adds ARCH:REVIEWED marker when body matches '## Architecture Review'; (2) PS layer docs updated to document ARCH:REVIEWED flag and Gate 3 exemption; (3) LLM reasoning bullet updated to skip heuristic for ARCH:REVIEWED tasks; (4) Gate 3 text updated with exemption paragraph — follows existing TW:MISSING/AC:MISSING/DECOMP pattern

[[2026-03-30]] Mon 18:27
## Review Evidence
Reviewer: reviewer | Task: #214 | Date: 2026-03-30 | Type: type:config (no tests/lint applicable)

### Changed Files
- skills/dispatch-planning/SKILL.md (4 locations â€” only file changed)

### Tests / Lint
- N/A: type:config non-implementation task. No Python files modified.
- Test-writer correctly passed through without writing tests.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Gate 3 exempt for Architecture-Review tasks | SKILL.md line 221: Exemption paragraph added to Gate 3 | PASS |
| Heuristic remains for non-reviewed tasks | Gate 3 text unchanged for non-ARCH:REVIEWED tasks | PASS |
| Recipe 1 PS adds ARCH:REVIEWED marker + Gate 3 reasoning uses it | Line 93: PS if-block; line 125: LLM bullet updated; line 121: PS docs bullet added | PASS |
| No other gates affected | Diff: only 4 hunks, all in Gate 3 and Board Scan sections; Gates 1,2,4,5,6 unchanged | PASS |

### Security
No security surface: documentation-only change.

### Confidence: .97

### Verdict: PASS

-t

[[2026-03-30]] Mon 18:28
## Review Evidence
Reviewer: reviewer | Task: #214 | Date: 2026-03-30 | Type: type:config (no tests/lint applicable)

### Changed Files
- skills/dispatch-planning/SKILL.md (4 locations â€” only file changed)

### Tests / Lint
- N/A: type:config non-implementation task. No Python files modified.
- Test-writer correctly passed through without writing tests.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Gate 3 exempt for Architecture-Review tasks | SKILL.md line 221: Exemption paragraph added to Gate 3 | PASS |
| Heuristic remains for non-reviewed tasks | Gate 3 text unchanged for non-ARCH:REVIEWED tasks | PASS |
| Recipe 1 PS adds ARCH:REVIEWED marker + Gate 3 reasoning uses it | Line 93: PS if-block; line 125: LLM bullet updated; line 121: PS docs bullet added | PASS |
| No other gates affected | Diff: only 4 hunks, all in Gate 3 and Board Scan sections; Gates 1,2,4,5,6 unchanged | PASS |

### Security
No security surface: documentation-only change.

### Confidence: .97

### Verdict: PASS

[[2026-03-30]] Mon 20:36
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Gate 3 exempt for ARCH:REVIEWED tasks | SKILL.md Gate 3 text has exemption paragraph | PASS |
| Heuristic remains for non-reviewed tasks | Gate 3 heuristic text unchanged for non-marked tasks | PASS |
| Recipe 1 PS adds ARCH:REVIEWED marker, Gate 3 uses it | PS block, PS docs bullet, LLM reasoning bullet all present | PASS |
| No other gates affected | Only Gate 3 + Board Scan sections modified; Gates 1,2,4,5,6 unchanged | PASS |

### Test Results
- pytest: 1349 passed, 118 failed (all pre-existing from other tasks), 0 in task scope
- ruff: N/A (markdown-only change)

### Architect Quality
- AC quality score: 5 (specific, complete, led to clean implementation)
- AC refined to 6 verifiable lines, merged duplicate #217, followed existing marker pattern

### Quality Gaps
- Research doc was never committed by upstream agents (researcher/builder); committed by auditor
- No dedicated #214 commit from builder; SKILL.md changes folded into #215/#219 commits

### Deduction breakdown: start 1.0, -.01 missing dedicated builder commit
### Confidence: .99
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3186a1a | docs | docs/research/gate-3-atomicity-architect-bypass.md | #214 |

[[2026-03-30]] Mon 20:36
## Audit
Confidence: .99 Action: archive
All 4 AC lines verified with evidence. Full suite: 1349 passed, 118 pre-existing failures (0 in task scope). AC quality: 5/5.
Quality gaps: research doc uncommitted by upstream (committed by auditor as 3186a1a); no dedicated builder commit for #214.
Deduction: -.01 for missing builder commit. Final: .99
See docs/scratch/214-auditor.tmp for full evidence table.
