---
id: 433
title: Add structured tool-error handling guidance to agent instructions
status: archived
priority: medium
created: 2026-03-30 21:37:50.654922+02:00
updated: 2026-03-31 15:54:36.838789+02:00
started: 2026-03-31 15:54:31.921818+02:00
completed: 2026-03-31 15:54:31.921818+02:00
tags:
- research
- scope:agents
- phase-2
depends_on:
- 435
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Adopt deer-flow's tool error resilience pattern: when a tool fails, agents should produce structured error context rather than crashing or retrying blindly. Currently agents have no explicit guidance on tool failure handling across different tool types.

See docs/research/tool-error-handling-guidance.md for full analysis.

**Relation to #435:** #435 consolidates loop detection and retry discipline (escalation tiers, retry limits). This task covers the complementary concern: structured error capture and tool-type-specific recovery. Do NOT duplicate retry limit content -- cross-reference #435's section instead.

## Acceptance Criteria
- [ ] New section 'Tool failure handling' in agent-common.instructions.md, placed after 'Skill authority' and before 'Self-defense against orchestrator degradation'
- [ ] Section includes 3-step error protocol subsection: Capture (read error message, note tool name and inputs), Diagnose (identify root cause before retrying), Adapt (choose alternative approach per tool type)
- [ ] Section includes 'Recovery by tool type' table covering: terminal commands, file operations (read/create/edit), search tools (grep/semantic/file_search), and MCP tools -- each with common failures and recovery action
- [ ] Section includes 'Structured error context for handoff' subsection specifying what to record when escalating: tool name + inputs, abbreviated error message, alternatives attempted, likely root cause
- [ ] Retry limits are NOT duplicated -- section cross-references the 'Loop detection and retry discipline' section (#435) for retry counts and escalation tiers
- [ ] Existing 'Skill authority' bullet ('If a command fails, re-read your skill') is preserved unchanged -- new section extends it, not replaces it

[[2026-03-30]] Mon 22:41
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| New 'Tool failure handling' section in agent-common.instructions.md | Clear, verifiable -- section exists or doesn't | Keep |
| Placed after 'Skill authority', before 'Self-defense...' | Specific placement -- verifiable by line number | Keep |
| 3-step error protocol (Capture/Diagnose/Adapt) | Concrete steps with parenthetical definitions -- testable | Keep |
| Recovery by tool type table (4 tool categories) | Each category named with required columns -- mechanically verifiable | Keep |
| Structured error context for handoff subsection | 4 required fields listed -- content-checkable | Keep |
| Cross-reference #435 for retry limits | Verifiable: no duplicate retry numbers, xref present | Keep |
| Preserve existing 'Skill authority' bullet | Verifiable: line ~123 unchanged after edit | Keep |

### Architecture Notes
Instruction-file-only change (agent-common.instructions.md). No code, no module layering concerns, no security surface changes.

Existing scattered guidance verified at:
- Line 123: Skill authority, 'If a command fails, re-read your skill'
- Line 204: Red flags, 'max 2 retries'
- Line 249: Terminal discipline, 'No brute-force retries'

New section fills the gap for non-terminal tool types (file ops, search, MCP) that have no recovery guidance today. Complements #435 (loop detection consolidation) without overlapping.

Dependency on #435 added to ensure the builder sees the loop detection section before adding tool failure handling. Both target the same file region.

Single domain: agents/instructions. KISS-aligned: instruction text only, no middleware or code.

### TDD Note
No test task needed -- markdown instruction file edit, not application code. Reviewer verifies content directly.

### Dependencies
- Added: depends_on #435 (loop detection consolidation must land first to avoid merge conflicts)
- Verified: #432 (loop detection) is archived -- no conflict

[[2026-03-30]] Mon 22:41
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| New 'Tool failure handling' section in agent-common.instructions.md | Clear, verifiable -- section exists or doesn't | Keep |
| Placed after 'Skill authority', before 'Self-defense...' | Specific placement -- verifiable by line number | Keep |
| 3-step error protocol (Capture/Diagnose/Adapt) | Concrete steps with parenthetical definitions -- testable | Keep |
| Recovery by tool type table (4 tool categories) | Each category named with required columns -- mechanically verifiable | Keep |
| Structured error context for handoff subsection | 4 required fields listed -- content-checkable | Keep |
| Cross-reference #435 for retry limits | Verifiable: no duplicate retry numbers, xref present | Keep |
| Preserve existing 'Skill authority' bullet | Verifiable: line ~123 unchanged after edit | Keep |

### Architecture Notes
Instruction-file-only change (agent-common.instructions.md). No code, no module layering concerns, no security surface changes.

Existing scattered guidance verified at:
- Line 123: Skill authority, 'If a command fails, re-read your skill'
- Line 204: Red flags, 'max 2 retries'
- Line 249: Terminal discipline, 'No brute-force retries'

New section fills the gap for non-terminal tool types (file ops, search, MCP) that have no recovery guidance today. Complements #435 (loop detection consolidation) without overlapping.

Dependency on #435 added to ensure the builder sees the loop detection section before adding tool failure handling. Both target the same file region.

Single domain: agents/instructions. KISS-aligned: instruction text only, no middleware or code.

### TDD Note
No test task needed -- markdown instruction file edit, not application code. Reviewer verifies content directly.

### Dependencies
- Added: depends_on #435 (loop detection consolidation must land first to avoid merge conflicts)
- Verified: #432 (loop detection) is archived -- no conflict

[[2026-03-31]] Tue 06:09
## Test-Writer Notes
- Non-implementation task (tagged research) -- markdown instruction file edit, not application code.
- Architect noted: No test task needed. Reviewer verifies content directly.
- Passing through to builder.

[[2026-03-31]] Tue 07:17
## Builder Notes
- Files changed: instructions/agent-common.instructions.md (28 lines inserted)
- Section placed after "Skill authority", before "Self-defense against orchestrator degradation" (lines 155-181)
- 3-step protocol: Capture/Diagnose/Adapt
- Recovery table: 4 tool types (terminal, file ops, search, MCP) with common failures + recovery actions
- Structured error context for handoff: 4 fields (tool name+inputs, error msg, alternatives, root cause)
- Retry limits: cross-referenced "Loop detection and retry discipline" -- no duplication
- Skill authority bullet preserved unchanged
- Commit: 1e4dfc1

[[2026-03-31]] Tue 15:10
## Docs Gate - all 6 checklist items evaluated, no docs files needed updating, content verified

[[2026-03-31]] Tue 15:54
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| New 'Tool failure handling' section | Found at L155 of agent-common.instructions.md | PASS |
| Placed after 'Skill authority', before 'Self-defense' | Skill authority L150, Tool failure L155, Self-defense L189 | PASS |
| 3-step error protocol (Capture/Diagnose/Adapt) | Lines 159-161, all three steps present with definitions | PASS |
| Recovery by tool type table (4 categories) | Lines 165-170: terminal, file ops, search, MCP -- each with failures + recovery | PASS |
| Structured error context for handoff | Lines 174-179: 4 fields (tool+inputs, error msg, alternatives, root cause) | PASS |
| Cross-references Loop detection, no retry duplication | L172 references section, no retry numbers duplicated | PASS |
| Skill authority bullet preserved unchanged | Lines 151-152 unchanged from pre-task state | PASS |

### Test Results
- pytest: 1918 passed, 141 failed (all pre-existing, none in task scope -- markdown-only change)
- ruff: 2 violations in unrelated file (test_necessity_check_196.py) -- not in scope

### AC Quality: 5/5
AC was specific, mechanically verifiable, and led to clean implementation with no builder improvisation needed.

### Research verification
- Research doc exists: docs/research/tool-error-handling-guidance.md
- This task IS the follow-up implementation from that research
- Task body links to research doc

### Deduction breakdown
- -.02 Missing reviewer evidence section in task body

### Confidence: .98
### Action: archive
