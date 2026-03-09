---
id: 687
title: Rewrite pipeline agent output_formats to two-channel model (builder, reviewer, writer, auditor)
status: archived
priority: needed
created: 2026-03-08T16:35:29.6332222+01:00
updated: 2026-03-09T10:47:12.2728269+01:00
started: 2026-03-08T17:52:58.3537159+01:00
completed: 2026-03-09T10:47:12.2728269+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
depends_on:
    - 684
class: standard
---

## Acceptance Criteria

- [ ] builder.agent.md output_format rewritten: routing signal = `DONE #{id} -> review | {test_count} passed, ruff {status}` (or `BLOCKED #{id} -> todo | {reason}`). Files changed, coverage %, fixes, evidence details moved to task body section `## Builder Notes` via kanban-md edit -a -t
- [ ] reviewer.agent.md output_format rewritten: routing signal = `PASS #{id} -> docs | confidence {.XX}` (or `FAIL #{id} -> {status} | {reason}`). AC compliance table, test quality matrix, security findings, rejection details moved to task body section `## Review Evidence` via kanban-md edit -a -t
- [ ] writer.agent.md output_format rewritten: routing signal = `DONE #{id} -> done | docs gate passed` (or `REJECTED #{id} -> review | {reason}`). Checklist table, files updated, scratch cleaned moved to task body section `## Docs Gate` via kanban-md edit -a -t
- [ ] auditor.agent.md output_format rewritten: routing signal = `ARCHIVED #{id} | confidence {.XX}` (or `REJECTED #{id} -> {status} | {reason}`). Audit report table, commit log moved to task body section `## Audit` via kanban-md edit -a -t
- [ ] Each agent's output_format includes explicit instruction: write body section FIRST, then return ONLY the routing signal line
- [ ] Signal formats match the protocol defined in agent-common.instructions.md (from #684)

## Notes

- These 4 agents form the core build pipeline (builder -> reviewer -> writer -> auditor). Their outputs are the most context-heavy and benefit most from the split.
- No TDD required -- these are .agent.md file edits.
- Reference: docs/inter-agent-communication-protocol-research.md sections 3.3, 3.4, 3.5

[[2026-03-08]] Sun 17:50
## Review Evidence
### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| builder output_format rewritten | DONE/BLOCKED signals + ## Builder Notes body section present in builder.agent.md output_format | PASS |
| reviewer output_format rewritten | PASS/FAIL signals + ## Review Evidence body section present in reviewer.agent.md output_format | PASS |
| writer output_format rewritten | DONE/REJECTED signals + ## Docs Gate body section present in writer.agent.md output_format | PASS |
| auditor output_format rewritten | ARCHIVED/REJECTED signals + ## Audit body section present in auditor.agent.md output_format | PASS |
| Explicit write-body-first instruction | All 4 agents have 'write Channel B first, then return only Channel A' preamble | PASS |
| Signal formats match agent-common protocol | All verdict tokens, signal examples, and body section names match the per-agent table in agent-common.instructions.md | PASS |

### Test Quality
N/A -- .agent.md file edits, no Python code, no tests required per task notes.

### Security
No issues -- instruction files only, no executable code, no secrets, no injection vectors.

### Verdict: PASS confidence .95

[[2026-03-08]] Sun 17:53
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Task changed output_format sections in .agent.md files only. Agent inventory roles/patterns unchanged. Two-channel protocol already referenced in instruction file inventory (line 262). |
| 2 | Docstrings | No | N/A | No Python modules changed  .agent.md files only |
| 3 | sources.md | No | N/A | External sources (LangGraph, Swarm, Blackboard, CrewAI) already attributed under Task #684 section. No new sources introduced. |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/inter-agent-communication-protocol-research.md referenced in task notes |
| 6 | No impact catch-all | N/A | N/A | Items 1-5 evaluated individually |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/687-* files found)

[[2026-03-09]] Mon 04:57
Wave 2, agent: auditor

[[2026-03-09]] Mon 10:46
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| builder output_format rewritten | builder.agent.md: DONE/BLOCKED signals + ## Builder Notes body section in output_format | PASS |
| reviewer output_format rewritten | reviewer.agent.md: PASS/FAIL signals + ## Review Evidence body section in output_format | PASS |
| writer output_format rewritten | writer.agent.md: DONE/REJECTED signals + ## Docs Gate body section in output_format | PASS |
| auditor output_format rewritten | auditor.agent.md: ARCHIVED/REJECTED signals + ## Audit body section in output_format | PASS |
| Write-body-first instruction | All 4 agents have 'Write Channel B first, then return only Channel A' preamble + 'Return only the signal line' | PASS |
| Signal formats match agent-common protocol | All verdict tokens, signal examples, body section names match per-agent table in agent-common.instructions.md | PASS |

### Test Results
- pytest: 1271 passed, 20 skipped, 0 failed (1 pre-existing slack_sdk env issue excluded)
- ruff: 3 pre-existing issues (E501, 2x I001) unrelated to task -- no Python files changed

### Confidence: .97
### Action: archive

[[2026-03-09]] Mon 10:47
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| builder output_format rewritten | builder.agent.md: DONE/BLOCKED signals + ## Builder Notes body section in output_format | PASS |
| reviewer output_format rewritten | reviewer.agent.md: PASS/FAIL signals + ## Review Evidence body section in output_format | PASS |
| writer output_format rewritten | writer.agent.md: DONE/REJECTED signals + ## Docs Gate body section in output_format | PASS |
| auditor output_format rewritten | auditor.agent.md: ARCHIVED/REJECTED signals + ## Audit body section in output_format | PASS |
| Write-body-first instruction | All 4 agents have 'Write Channel B first, then return only Channel A' preamble + 'Return only the signal line' | PASS |
| Signal formats match agent-common protocol | All verdict tokens, signal examples, body section names match per-agent table in agent-common.instructions.md | PASS |

### Test Results
- pytest: 1271 passed, 20 skipped, 0 failed (1 pre-existing slack_sdk env issue excluded)
- ruff: 3 pre-existing issues (E501, 2x I001) unrelated to task -- no Python files changed

### Confidence: .97
### Action: archive
