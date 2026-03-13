---
id: 684
title: Codify two-channel communication protocol in agent-common.instructions.md
status: archived
priority: needed
created: 2026-03-08T15:45:29.5631845+01:00
updated: 2026-03-09T10:42:55.0252611+01:00
started: 2026-03-08T16:07:09.3139995+01:00
completed: 2026-03-09T10:42:55.0252611+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

## Context

Currently every subagent returns a full prose report that the orchestrator accumulates in context. This causes context overflow. Two consumers need different data: the orchestrator needs routing signals (pass/fail, next status); the next-pipeline agent needs rich context (evidence, tables, findings).

Research complete: see docs/research/inter-agent-communication-protocol.md for the full design, including per-agent signal formats, body section headers, and field-by-field audit.

## Acceptance Criteria

- [ ] New `## Inter-agent communication protocol` section added to agent-common.instructions.md
- [ ] Section defines Channel A (routing signal): max 2 lines, format `{VERDICT} #{id} -> {target_status} | {one-line evidence}`, verdict tokens listed per agent type
- [ ] Section defines Channel B (task body section): agents write rich context to task body via `kanban-md edit ID -a "## {Section}\n{content}" -t` before returning
- [ ] Per-agent summary table: each agent mapped to its signal format and body section header (## Builder Notes, ## Review Evidence, ## Docs Gate, ## Audit, ## Architecture Review, ## Research, ## Planning, ## Curation)
- [ ] File-reference threshold rule: any single agent section exceeding 1500 tokens uses a file reference (`See docs/scratch/{task-id}-{agent}.md`) instead. Rationale: 4 agents x 750 avg = 3000 total, well under 4% of 128K context
- [ ] PowerShell escaping guidance: pipe characters in markdown tables must be backtick-escaped; complex body content should be written to temp file first
- [ ] Explicit rule: orchestrator/evaluator reads ONLY routing signals from subagent return text, never task body content. Planner/reviewer/next-pipeline agents read task bodies via `kanban-md show`
- [ ] No implementation of per-agent output_format rewrites (those are separate tasks)

## Notes

- This is a specification-writing task, not a code task. No TDD required.
- The research doc (docs/research/inter-agent-communication-protocol.md) is the authoritative design reference. This task codifies it as agent-facing instructions.
- Keep the section concise: agents already have large context loads (see #686). Target < 60 lines.

[[2026-03-08]] Sun 23:51
Wave 4, agent: auditor

[[2026-03-09]] Mon 04:57
Wave 2, agent: auditor

[[2026-03-09]] Mon 10:42
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Inter-agent protocol section added | ## Inter-agent communication protocol present ~L165 | PASS |
| Channel A defined (max 2 lines, format, verdicts) | ### Channel A subsection with format + per-agent tokens | PASS |
| Channel B defined (task body via kanban-md edit) | ### Channel B subsection with command pattern | PASS |
| Per-agent summary table | 9 agents mapped with verdicts, examples, body section headers | PASS |
| File-reference threshold (1500 tokens) | ### File-reference threshold with rule + rationale | PASS |
| PowerShell escaping guidance | ### PowerShell escaping with backtick + temp file patterns | PASS |
| Orchestrator reads only routing signals | ### Reading rules with explicit separation | PASS |
| No per-agent output_format rewrites | Protocol spec only; rewrites in #687 | PASS |

### Test Results
- pytest: 260 passed, 6 deselected (spec-only task, no Python code changed)
- ruff: 3 pre-existing issues (screenshot.py L22, test_bootstrap_structure.py imports) unrelated to #684

### Confidence: .97
### Action: archive

[[2026-03-09]] Mon 10:42
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Inter-agent protocol section added | ## Inter-agent communication protocol present ~L165 | PASS |
| Channel A defined (max 2 lines, format, verdicts) | ### Channel A subsection with format + per-agent tokens | PASS |
| Channel B defined (task body via kanban-md edit) | ### Channel B subsection with command pattern | PASS |
| Per-agent summary table | 9 agents mapped with verdicts, examples, body section headers | PASS |
| File-reference threshold (1500 tokens) | ### File-reference threshold with rule + rationale | PASS |
| PowerShell escaping guidance | ### PowerShell escaping with backtick + temp file patterns | PASS |
| Orchestrator reads only routing signals | ### Reading rules with explicit separation | PASS |
| No per-agent output_format rewrites | Protocol spec only; rewrites in #687 | PASS |

### Test Results
- pytest: 260 passed, 6 deselected (spec-only task, no Python code changed)
- ruff: 3 pre-existing issues (screenshot.py L22, test_bootstrap_structure.py imports) unrelated to #684

### Confidence: .97
### Action: archive
