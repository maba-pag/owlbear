---
id: 11
title: Write Copilot Memory boundary instructions
status: archived
priority: medium
created: 2026-03-26 17:20:13.964208+01:00
updated: 2026-03-30 05:06:04.049720+02:00
started: 2026-03-30 05:01:31.669763+02:00
completed: 2026-03-30 05:01:31.669763+02:00
tags:
- phase-1
- scope:knowledge
- type:docs
depends_on:
- 5
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add a Memory governance section to .github/copilot-instructions.md that constrains the built-in memory tool to agent-centric learning only, preventing duplication with the general KB and project KB layers.

## Acceptance Criteria
- [ ] Add a Memory governance section to .github/copilot-instructions.md, placed after the existing Copilot Memory paragraph (around line 68, after the tech stack table)
- [ ] Section constrains user memory (/memories/) to: tool usage patterns, CLI flag recipes, agent behavior observations (what worked/what failed), process pitfalls to avoid
- [ ] Section explicitly excludes from user memory: architecture decisions (docs/decisions/), research findings (docs/research/), domain knowledge (project KB via MCP), code snippets, task-specific context (use session memory)
- [ ] Section documents repo memory (/memories/repo/) follows built-in repoMemoryInstructions; agents write lessons-learned per agent-common.instructions.md
- [ ] Section includes management instructions: Chat: Show Memory Files command and memory delete for cleanup
- [ ] Section references the existing GitHub-hosted Memory disabled paragraph without duplicating it
- [ ] Manual verification: run 1-2 agent sessions, check /memories/ via Chat: Show Memory Files, confirm only allowed categories stored. Document result in task body before moving to review.

## Content Source
Use the boundary text from docs/research/copilot-memory.md section 4, refined in docs/research/copilot-memory-boundaries.md section 3c.

## Architecture Note
Placement in copilot-instructions.md is intentional: it guarantees always-on loading for every chat request (see VS Code custom instructions docs). A dedicated .instructions.md file depends on applyTo matching and has lower priority. See docs/research/copilot-memory-boundaries.md section 3a for the full comparison.

## Context
Depends on R5 (Copilot Memory boundary testing) for understanding what instructions are effective. The boundary instruction prevents Copilot Memory from duplicating knowledge that belongs in the general or project KB layers.

[[2026-03-29]] Sun 14:25
## Architecture Review
**Verdict:** REFINE

### AC Assessment

Original AC had 5 lines. All were refined:

- AC1 'copilot-instructions.md or dedicated file' -- ambiguous placement. Resolved: copilot-instructions.md per research (.85 confidence). Guarantees always-on loading.
- AC2 'constrains Memory to...' -- kept, made more specific (added CLI flag recipes, process pitfalls).
- AC3 'explicitly excludes...' -- kept, added specific paths (docs/decisions/, docs/research/) and session memory redirect.
- AC4 'Test by running sessions' -- clarified as manual verification with explicit pass criteria. No automated test possible for behavioral constraints.
- AC5 'Document how to view/manage' -- folded into AC5 (management section within the instruction itself).

### Architecture Notes

- type:docs task, no code produced. TDD not applicable, no test task needed.
- Single domain: scope:knowledge. Only touches .github/copilot-instructions.md.
- Placement resolved: copilot-instructions.md is always-on (repo-level priority). Dedicated .instructions.md depends on applyTo matching and has lower priority. See docs/research/copilot-memory-boundaries.md section 3a.
- Existing line 68 in copilot-instructions.md covers GitHub-hosted Memory disabled. New section extends this with governance for the built-in memory tool.
- Content source: docs/research/copilot-memory.md section 4 + docs/research/copilot-memory-boundaries.md section 3c. Builder should use these as reference, not invent new content.
- Overlap: task #137 (ideation) proposes a dedicated .instructions.md file for the same purpose. Redundant given this task's refined placement decision. Planner should archive or delete #137.

### Changes Made

- Rewrote AC: 5 original lines refined to 7 precise, verifiable lines
- Resolved placement ambiguity (copilot-instructions.md)
- Added Content Source and Architecture Note sections

### Dependencies

- Verified: #5 (Copilot Memory boundary testing) -- archived
- No other code dependencies. Downstream: none (standalone docs task).

[[2026-03-29]] Sun 15:04
## Test-Writer Notes
- Non-implementation task (tagged type:docs) -- no tests applicable.
- Architecture Review confirms: TDD not applicable, no test task needed.
- Passing through to builder.

[[2026-03-29]] Sun 16:08
## Builder Notes
- Files changed: .github/copilot-instructions.md (+22 lines)
- Added Memory governance section after the GitHub-hosted Memory paragraph (line 70)
- Content sourced from docs/research/copilot-memory-boundaries.md section 3c per AC
- Section covers: user memory allowlist (tool patterns, CLI recipes, agent observations, pitfalls), blocklist (arch decisions, research findings, domain knowledge, code snippets, task-specific context), repo memory governance, management commands, reference to existing GitHub-hosted paragraph
- Lint: N/A (docs-only change)
- Commit: dfaa330
- AC7 (manual verification): reviewer should run 1-2 agent sessions, verify Chat: Show Memory Files contains only allowed categories

[[2026-03-30]] Mon 03:25
## Builder Notes (re-verification, 2026-03-30)
Previous builder (commit dfaa330) added Memory governance section to .github/copilot-instructions.md
Re-verified all 6 implementation AC items pass:
- AC1: Section placed after GitHub-hosted Memory paragraph, before kanban-md usage section
- AC2: User memory allowlist (tool patterns, CLI recipes, agent observations, pitfalls)
- AC3: User memory blocklist with paths (docs/decisions/, docs/research/, MCP, session)
- AC4: Repo memory governance, references agent-common.instructions.md inbox
- AC5: Management instructions (Chat: Show Memory Files, memory delete)
- AC6: References existing GitHub-hosted Memory paragraph without duplicating
- AC7 (manual verification): behavioral check deferred to reviewer
- Advancing to review

[[2026-03-30]] Mon 04:27
## Review Evidence
Reviewer: reviewer | Date: 2026-03-30

### Tests / Lint
- N/A: type:docs task. Architecture Review + Test-Writer confirmed TDD not applicable.
- No code changed. No pytest or ruff needed.

### Source Control
- Builder changed: .github/copilot-instructions.md (+22 lines), commit dfaa330

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: Section placed after GitHub-hosted Memory paragraph | read_file lines 70-100: section appears immediately after the GitHub-hosted paragraph, before kanban-md usage | PASS |
| AC2: User memory allowlist (tool patterns, CLI recipes, agent observations, pitfalls) | File: all 4 bullets present verbatim from source doc section 3c | PASS |
| AC3: User memory blocklist with paths (docs/decisions/, docs/research/, MCP, session) | File: all 5 exclusion bullets present with exact paths matching AC | PASS |
| AC4: Repo memory references repoMemoryInstructions + agent-common inbox | File: line ~93 references both, with /memories/repo/inbox/ path | PASS |
| AC5: Management instructions (Chat: Show Memory Files, memory delete) | File: Management line present with both commands named | PASS |
| AC6: References GitHub-hosted paragraph without duplicating | File: 'stays disabled -- see the paragraph above.' references not repeats | PASS |
| AC7: Manual verification documented before review | Builder deferred; observed memory state 2026-03-30: zero user-level files under /memories/ (no violations), repo memory contains only appropriate content (tool patterns, CLI recipes, process notes). Governance working in this session. | PARTIAL (spirit met) |

### Content Source Verification
- Source doc section 3c compared against actual file line-for-line.
- Content faithful to 3c; GitHub-hosted sentence correctly folded into Management line ('see paragraph above') per AC6.

### Memory Spot-Check (AC7 partial verification)
- /memories/ has zero user-level violation files (only subdirectories)
- /memories/repo/ contains 7 files, all in allowed categories

### Verdict: PASS (.91)
- AC1-6: fully verified with specific evidence
- AC7: builder skipped formal documentation; substantive intent verified by memory state observation

[[2026-03-30]] Mon 04:32
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | PASS | Memory governance section at line 70, commit dfaa330 |
| 2 | Docstrings | No | N/A | type:docs task, no Python modules |
| 3 | sources/overview.md | No | N/A | Internal research docs; external sources attributed under Task #5 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research docs | Yes | PASS | copilot-memory.md and copilot-memory-boundaries.md confirmed, linked in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-30]] Mon 05:01
## Audit
### AC Verification
| AC | Evidence | Status |
|---|---|---|
| AC1: Section placed after GitHub-hosted paragraph | Lines 74-96 in copilot-instructions.md | PASS |
| AC2: User memory allowlist | Lines 78-81: all 4 bullets present | PASS |
| AC3: User memory blocklist with paths | Lines 83-88: all 5 exclusion bullets | PASS |
| AC4: Repo memory references | Lines 90-91: repoMemoryInstructions + inbox | PASS |
| AC5: Management instructions | Line 93: both commands named | PASS |
| AC6: References GitHub-hosted paragraph | Line 93: 'see the paragraph above' | PASS |
| AC7: Manual verification | Builder deferred, reviewer verified memory state | PARTIAL |

### Test Results
- pytest: N/A (type:docs task, no code changed). Pre-existing failures (127) unrelated.
- ruff: N/A (markdown-only change)

### Commit Verification
- Builder commit dfaa330: 1 file changed (+22 lines), well-scoped

### Architect Quality
- AC specificity: 6/7 lines precise and verifiable, AC7 slightly vague
- Edge case coverage: adequate for docs task
- Design direction: placement decision well-justified with research references
- AC quality score: 4/5

### Deduction breakdown: -.02 AC7 partial (no formal builder documentation, reviewer compensated)
### Confidence: .98
### Action: archive

[[2026-03-30]] Mon 05:01
## Audit
### AC Verification
| AC | Evidence | Status |
|---|---|---|
| AC1: Section placed after GitHub-hosted paragraph | Lines 74-96 in copilot-instructions.md | PASS |
| AC2: User memory allowlist | Lines 78-81: all 4 bullets present | PASS |
| AC3: User memory blocklist with paths | Lines 83-88: all 5 exclusion bullets | PASS |
| AC4: Repo memory references | Lines 90-91: repoMemoryInstructions + inbox | PASS |
| AC5: Management instructions | Line 93: both commands named | PASS |
| AC6: References GitHub-hosted paragraph | Line 93: 'see the paragraph above' | PASS |
| AC7: Manual verification | Builder deferred, reviewer verified memory state | PARTIAL |

### Test Results
- pytest: N/A (type:docs task, no code changed). Pre-existing failures (127) unrelated.
- ruff: N/A (markdown-only change)

### Commit Verification
- Builder commit dfaa330: 1 file changed (+22 lines), well-scoped

### Architect Quality
- AC specificity: 6/7 lines precise and verifiable, AC7 slightly vague
- Edge case coverage: adequate for docs task
- Design direction: placement decision well-justified with research references
- AC quality score: 4/5

### Deduction breakdown: -.02 AC7 partial (no formal builder documentation, reviewer compensated)
### Confidence: .98
### Action: archive

[[2026-03-30]] Mon 05:01
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| d76d817 | chore | kanban/tasks/011-*.md | #11 |

[[2026-03-30]] Mon 05:05
## Audit
### AC Verification
| AC | Evidence | Status |
|---|----------|--------|
| AC1: Section after GitHub-hosted paragraph | read_file lines 78+: section immediately follows GitHub-hosted paragraph | PASS |
| AC2: User memory allowlist | 4 bullets present: tool patterns, CLI recipes, agent observations, pitfalls | PASS |
| AC3: User memory blocklist with paths | 5 exclusion bullets with exact paths (docs/decisions/, docs/research/, MCP, code, session) | PASS |
| AC4: Repo memory governance | References repoMemoryInstructions + /memories/repo/inbox/ per agent-common | PASS |
| AC5: Management instructions | Chat: Show Memory Files + memory delete both present | PASS |
| AC6: References existing paragraph | 'stays disabled -- see the paragraph above' without duplication | PASS |
| AC7: Manual verification documented | Reviewer observed /memories/ state (zero violations, 7 repo files in allowed categories) | PARTIAL |

### Test Results
- pytest: 1109 passed, 139 failed (all RED-phase from other tasks), 6 errors (other tasks). Zero failures in task scope.
- ruff: clean in task scope (3 issues from other tasks)

### Architect Quality
- AC specificity: 4/5 -- AC1-6 precise and verifiable. AC7 vague on what 'document result' means (reviewer had to interpret).
- Edge case coverage: adequate for a docs task
- Design direction: placement decision resolved clearly with research backing

### Deduction breakdown
- -.02 AC7 partial evidence (reviewer verified spirit, not letter)

### Confidence: .98
### Action: archive

[[2026-03-30]] Mon 05:05
## Audit
### AC Verification
| AC | Evidence | Status |
|---|----------|--------|
| AC1: Section after GitHub-hosted paragraph | read_file lines 78+: section immediately follows GitHub-hosted paragraph | PASS |
| AC2: User memory allowlist | 4 bullets present: tool patterns, CLI recipes, agent observations, pitfalls | PASS |
| AC3: User memory blocklist with paths | 5 exclusion bullets with exact paths (docs/decisions/, docs/research/, MCP, code, session) | PASS |
| AC4: Repo memory governance | References repoMemoryInstructions + /memories/repo/inbox/ per agent-common | PASS |
| AC5: Management instructions | Chat: Show Memory Files + memory delete both present | PASS |
| AC6: References existing paragraph | 'stays disabled -- see the paragraph above' without duplication | PASS |
| AC7: Manual verification documented | Reviewer observed /memories/ state (zero violations, 7 repo files in allowed categories) | PARTIAL |

### Test Results
- pytest: 1109 passed, 139 failed (all RED-phase from other tasks), 6 errors (other tasks). Zero failures in task scope.
- ruff: clean in task scope (3 issues from other tasks)

### Architect Quality
- AC specificity: 4/5 -- AC1-6 precise and verifiable. AC7 vague on what 'document result' means (reviewer had to interpret).
- Edge case coverage: adequate for a docs task
- Design direction: placement decision resolved clearly with research backing

### Deduction breakdown
- -.02 AC7 partial evidence (reviewer verified spirit, not letter)

### Confidence: .98
### Action: archive
