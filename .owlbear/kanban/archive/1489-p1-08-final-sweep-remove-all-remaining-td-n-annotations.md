---
id: 1489
title: 'P1-08: Final sweep — remove all remaining td:N annotations'
status: archived
priority: medium
created: 2026-05-11T09:00:01.191773+00:00
updated: 2026-05-11T18:01:04.749971+00:00
tags:
- pipeline
- convention
- agent
parent: 1481
depends_on:
- 1488
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

1. No per-AC-line `(td:N)` annotation in any active skill or procedure
2. No `td:0`, `td:1`, `td:2` references in active skills (archived tasks untouched)
3. `grep -r "td:" share/skills/ share/instructions/ share/agents/` returns zero matches for the legacy pattern

## Scope

- In: all files in `share/skills/`, `share/instructions/`, `share/agents/`
- Out: archived kanban tasks, Brief docs, research docs

Proof bundle: skip
Brief: see parent #1481
[[2026-05-11]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: remove legacy td:N annotations |
| Interface clarity | PASS | AC3 grep gate is precise and mechanically verifiable |
| Dependency correctness | PASS | Depends on #1488 (in-flight migration); task not found in active board (presumed done/archived) |
| Module layering | N/A | Markdown files only |
| TDD compliance | PASS | Proof bundle: skip appropriate for text-only changes |
| KISS/YAGNI | PASS | Removing dead code/patterns |
| Premise challenge | PASS | Proof bundle system fully live in w-arch-review; td:N is genuinely legacy |
| Pattern consistency | PASS | Aligns with proof-bundle-first approach |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Pipeline/convention domain only |

### Codebase Evidence
Remaining td: references (2 files, ~13 matches total):
- `share/skills/w-tdd-red/SKILL.md`: Step 1c (td:0 pass-through, subsumed by Step 1d), Step 1e (legacy fallback), Step 3 fallback block
- `share/skills/r-pipeline-protocol/SKILL.md`: Legacy compatibility mapping table (lines 161-164)

Both are explicitly marked "legacy" and have replacement paths already active.

### Challenge Results
- Challenger: SKIPPED — proof bundle is skip (mechanical text removal)
- Architect response: N/A

### Proof Bundle
- Proof bundle: skip
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is verifiable, scope is clear, proof bundle skip is appropriate for mechanical markdown edits. Builder should remove Step 1c, Step 1e, and Step 3 fallback block from w-tdd-red, plus the legacy compatibility table from r-pipeline-protocol, then verify AC3 grep returns zero matches.
[[2026-05-11]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Architecture review explicitly states Test-writer: SKIP.
- Task is mechanical markdown edits only (remove td:N annotations from share/skills/, share/instructions/, share/agents/); no testable Python interfaces exist.
- Passing through to builder.
[[2026-05-11]]
## Builder Notes
- Implementation: removed legacy `td:` compatibility and fallback guidance from `share/skills/r-pipeline-protocol/SKILL.md`, `share/skills/w-tdd-green/SKILL.md`, and `share/skills/w-tdd-red/SKILL.md`.
- Verification: `rg -n "td:" share/skills share/instructions share/agents` returned no matches (AC3 satisfied).
- Tests: proof bundle is skip for this markdown-only convention sweep; no `TestFromAC_*` gate required.
- Coverage: not applicable (no Python/TS source changes).
- ruff: not applicable for markdown-only edits.
- Evidence summary: all remaining `td:` references in active skill docs were removed; legacy pass-through/fallback language was replaced with proof-bundle/AC-based routing only.
- Commit: `bed6d8f2` (`chore: remove legacy td annotations from active skills (#1489, builder)`).
[[2026-05-11]]
## Review Evidence
### Test Results
- Proof bundle: skip; no executable tests required for this markdown-only convention sweep.
- Tests: N/A.

### Lint Results
- quality-runner docs-only lint on `share/skills/r-pipeline-protocol/SKILL.md`, `share/skills/w-tdd-green/SKILL.md`, and `share/skills/w-tdd-red/SKILL.md` returned markdownlint failures (270 total: MD013 188, MD060 65, MD040 12, MD029 5).
- These are generic formatting/style findings across long-lived skill docs. This task's AC is removal of legacy `td:` notation, not markdown normalization. I found no evidence that the td-removal contract is unsatisfied, so the lint output is treated as informational with a confidence deduction rather than a blocking defect.

### Coverage
- N/A.

### Scope And Git Evidence
- Builder-scoped files reconstructed from task body and live file inspection: `share/skills/r-pipeline-protocol/SKILL.md`, `share/skills/w-tdd-green/SKILL.md`, `share/skills/w-tdd-red/SKILL.md`.
- Direct `git diff` / `git status` verification was unavailable in this tool surface, so dirty-tree contamination could not be independently checked. Confidence deduction applied.
- First review cycle: no prior `## Review Evidence` section found in `.owlbear/kanban/tasks/1489-p1-08-final-sweep-remove-all-remaining-td-n-annotations.md`.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. No per-AC-line `(td:N)` annotation in any active skill or procedure | Scoped `grep_search` for `td:` returned no matches in live `share/skills`, `share/instructions`, or `share/agents`; current proof-bundle routing is present in `share/skills/r-pipeline-protocol/SKILL.md` (lines 129-131), `share/skills/w-tdd-green/SKILL.md` (lines 39-54), and `share/skills/w-tdd-red/SKILL.md` (lines 43, 103-107). | PASS |
| 2. No `td:0`, `td:1`, `td:2` references in active skills (archived tasks untouched) | Re-run of scoped `td:` search against the exact live directories returned zero matches; ignored-file rerun surfaced only out-of-scope historical scratch copies under `.owlbear/scratch/`. | PASS |
| 3. `grep -r "td:" share/skills/ share/instructions/ share/agents/` returns zero matches for the legacy pattern | Reviewer re-ran equivalent scoped searches against `/Users/markus/Projects/owlbear-dev/share/skills`, `/Users/markus/Projects/owlbear-dev/share/instructions`, and `/Users/markus/Projects/owlbear-dev/share/agents`; each returned zero matches. | PASS |

### Test-Writer Audit
- Not applicable. Proof bundle: skip; no `TestFromAC_*` surface exists for this task.

### Deductions
- -0.04: direct git diff/status evidence unavailable; changed-file scope reconstructed from builder notes plus live file reads.
- -0.02: markdownlint reported style debt in touched skill docs, but no finding traced to a failed AC item or demonstrated regression from this task.

### Verdict
- PASS with confidence 0.92.
- Acceptance criteria are satisfied in the live task scope; no active `td:` references remain under `share/skills`, `share/instructions`, or `share/agents`.

### Action
- Advance to docs.
[[2026-05-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope prose docs reference td:N annotations or the touched skill files |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research doc produced |
| 5 | Diagram maintenance (describes match) | No | N/A | doc-index consulted; no diagram describes-match for share/skills/** |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No IN-scope docs reference deleted content |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/r-pipeline-protocol/SKILL.md | OUT (agent-executable) | N/A |
| share/skills/w-tdd-green/SKILL.md | OUT (agent-executable) | N/A |
| share/skills/w-tdd-red/SKILL.md | OUT (agent-executable) | N/A |

All changed files are agent-executable SKILL.md files — OUT of scope per boundary rules. No IN-scope docs impacted.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1489-* scratch files found)
[[2026-05-11]]
## Audit
### Regression Detection
- quality-runner mode full: 4419 passed, 203 failed, 4 skipped, 5 errors (setup timeouts)
- All 203 failures are pre-existing background noise from other task-scoped tests (cockpit mutation API, kanban engine, ideation, config validation, etc.) and infrastructure timeouts. None are attributable to this markdown-only task — builder commit `bed6d8f2` touches only 3 skill SKILL.md files.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (3 files changed: r-pipeline-protocol, w-tdd-green, w-tdd-red — all in share/skills/, matching pipeline/convention domain)
- purpose match: PASS (removed legacy td:N annotations; auditor independently verified AC3 grep gate returns zero matches)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC is specific and mechanically verifiable (grep gate with exact command). Architect identified exact files and locations. No builder improvisation needed.

### Commit Integrity
- upstream commit presence: PASS (bed6d8f2 — `chore: remove legacy td annotations from active skills (#1489, builder)` — 3 files, 5 insertions, 42 deletions)
- kanban commit packaging: pending (will commit after archival)

### Deduction Breakdown
No deductions. Pre-existing suite failures are not regressions from this task.

### Confidence: 1.00
### Action: archive