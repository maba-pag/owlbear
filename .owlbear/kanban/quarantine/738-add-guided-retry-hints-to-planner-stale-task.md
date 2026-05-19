---
id: 738
title: Add guided retry hints to planner stale-task detection
status: archived
priority: nice-to-have
created: 2026-03-10T21:03:29.8172176+01:00
updated: 2026-03-11T22:33:13.9293954+01:00
started: 2026-03-11T22:22:50.1772971+01:00
completed: 2026-03-11T22:33:13.9293954+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
    - type:config
claimed_by: writer
claimed_at: 2026-03-11T22:22:50.1772971+01:00
class: standard
---

## Context

The only unique value from the evaluator research (#681) was guided retry hints (Reflexion pattern). When the planner detects a stale task (in-progress too long or failed previously), it could read the task body for prior failure notes and include a retry_hint in the dispatch prompt. See docs/research/evaluator-agent-final-disposition.md section 3.4.

## Acceptance Criteria

- [ ] wave-planning SKILL.md Step 1: when failure context identifies stale tasks, planner reads task body and extracts the last agent note section (## Builder Notes, ## Review Evidence, ## Test-Writer Notes, ## Audit, or ## Handoff)
- [ ] wave-planning SKILL.md Step 6: dispatch JSON schema updated -- dispatch objects gain optional retry_hint string field: {id, agent, retry_hint?}; hint is a single line <=120 chars summarizing the prior failure
- [ ] wave-planning SKILL.md Step 1: first-stale task (status unchanged from prior dispatch) is re-dispatched with retry_hint, not blocked. Orchestration SKILL.md Step 1: failure context format expanded from crash-only to include stale_retried IDs: `Previous cycle: #48 crashed twice; #52 stale, retried with hint`. If a task appears in stale_retried from the prior cycle AND is stale again now, planner blocks it.
- [ ] orchestration SKILL.md Step 2: when dispatch entry has retry_hint, append `\nRetry context: {retry_hint}` to the dispatch prompt after the task ID line
- [ ] orchestrator.agent.md: context_budget expanded -- stale_retried IDs persist alongside crash failures; retry_hint documented as the one exception to the ID-only dispatch rule; stale-task example updated
- [ ] planner.agent.md: one good_example added showing dispatch JSON with retry_hint
- [ ] No new agent or agent file created -- planner enhancement only

## Files to Modify

1. .github/skills/wave-planning/SKILL.md -- Step 1 (stale detection reads body), Step 6 (JSON schema)
2. .github/skills/orchestration/SKILL.md -- Step 1 (failure context format), Step 2 (dispatch prompt includes retry_hint)
3. .github/agents/orchestrator.agent.md -- context_budget (stale_retried tracking), dispatch rules, examples
4. .github/agents/planner.agent.md -- stale-task workflow, examples

[[2026-03-11]] Wed 16:38

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| wave-planning Step 1: read last agent note section | Clear -- lists 5 specific section headings | Kept |
| wave-planning Step 6: retry_hint optional field | Clear -- JSON schema change, <=120 char constraint | Kept |
| First-stale retry vs second-stale block | Prior version vague on statefulness mechanism | Rewritten: orchestrator tracks stale_retried IDs in failure context |
| orchestration Step 2: append retry context | Clear -- format specified as Retry context line | Kept |
| orchestrator context_budget expansion | Clear -- stale_retried alongside crash failures | Added |
| planner good_example with retry_hint | Clear -- verifiable | Kept |
| No new agent file | Clear -- verifiable | Kept |

### Architecture Notes

Two stale-task systems exist: daemon Python code (detect_stale_tasks + reconcile_tasks in daemon.py) and agent orchestration (SKILL files). Task targets agent orchestration only -- no conflict.

Key refinement: AC 3 required state tracking. The orchestrator already persists crash_failure IDs across cycles in its failure context. Expanding this to include stale_retried IDs is a natural extension -- minimal change to context budget invariant. Planner reads this to distinguish first-stale (retry with hint) from second-stale (block).

Dispatch prompt exception: retry_hint breaks the ID-only dispatch rule. AC 5 requires documenting this as the single exception in orchestrator.agent.md context_budget and dispatch rules.

Added type:config tag -- all 4 files are markdown config, no Python code. Test-writer will pass through.

### Changes Made

- Refined AC 3: spelled out statefulness mechanism (orchestrator stale_retried IDs in failure context)
- Added AC 5: orchestrator context_budget expansion requirement
- Added orchestration SKILL.md Step 1 to files-to-modify (failure context format)
- Added type:config tag

### Dependencies

None -- standalone enhancement. No depends_on tasks.

[[2026-03-11]] Wed 17:10

## Test-Writer Notes

Non-implementation task (tagged type:config) -- all changes are to .agent.md and SKILL.md markdown files. No testable Python code. Passing through to builder.

[[2026-03-11]] Wed 19:28

## Builder Notes

- Files changed: .github/skills/wave-planning/SKILL.md, .github/skills/orchestration/SKILL.md, .github/agents/orchestrator.agent.md, .github/agents/planner.agent.md
- Type: config-only (markdown), no Python code
- AC1: wave-planning Step 1 expanded with stale-task body reading + retry hint extraction from 5 note sections
- AC2: wave-planning Step 6 dispatch schema updated with optional retry_hint field, JSON example updated
- AC3: wave-planning Step 1 first-stale/second-stale logic; orchestration Step 1 failure context format with stale_retried
- AC4: orchestration Step 2 retry_hint -> Retry context line in dispatch prompt, example updated
- AC5: orchestrator context_budget stale_retried tracking, dispatch rule exception documented, stale example added
- AC6: planner good_example with retry_hint dispatch JSON added
- AC7: No new agent files created
- Checklists updated in all 4 files

[[2026-03-11]] Wed 21:11

## Test-Writer Notes (cycle 2)

Non-implementation task (tagged type:config) -- all changes are to .agent.md and SKILL.md markdown files. No testable Python code. Passing through to builder.

[[2026-03-11]] Wed 22:05

## Builder Notes (cycle 2)

- Files changed: .github/skills/wave-planning/SKILL.md, .github/skills/orchestration/SKILL.md, .github/agents/orchestrator.agent.md, .github/agents/planner.agent.md
- Type: config-only (markdown), no Python code
- AC1: wave-planning Step 1 expanded with stale-task body reading + retry hint extraction from 5 note sections
- AC2: wave-planning Step 6 dispatch schema updated with optional retry_hint field, JSON example updated
- AC3: wave-planning Step 1 first-stale/second-stale logic; orchestration Step 1 failure context format with stale_retried
- AC4: orchestration Step 2 retry_hint -> Retry context line in dispatch prompt, example added
- AC5: orchestration SKILL context_budget stale_retried tracking + orchestrator.agent.md dispatch rule exception documented + stale example added
- AC6: planner.agent.md good_example with retry_hint dispatch JSON added
- AC7: No new agent files created
- Also fixed: planner.agent.md workflow section updated to reference guided retry (was stale = block only)

-t

[[2026-03-11]] Wed 22:15

## Review Evidence (reviewer, 2026-03-11)

### Task Type

Config-only (4 markdown files). No Python code, no tests, no coverage applicable.

### Files Changed

- wave-planning/SKILL.md: Step 1 + Step 6 + checklist
- orchestration/SKILL.md: context_budget + Step 1 + Step 2 + checklist
- orchestrator.agent.md: boundaries + stale example
- planner.agent.md: workflow + good_example

### AC Compliance

AC1 PASS: wave-planning Step 1 lines 57-67 reads body, lists 5 headings
AC2 PASS: wave-planning Step 6 lines 176,183-186 retry_hint optional field
AC3 PASS: wave-planning lines 50-71 first/second-stale; orchestration lines 61-73 failure context
AC4 PASS: orchestration lines 98-106 Retry context line in dispatch prompt
AC5 PASS: orchestration lines 18-20 context_budget; orchestrator.agent.md line 103 exception + lines 189-207 example
AC6 PASS: planner.agent.md lines 141-143 good_example with retry_hint
AC7 PASS: git diff --name-only shows only 4 modified files, no new agent files

### Consistency: All files internally consistent on stale_retried lifecycle

### Security: No issues (markdown only)

### Confidence: .93

### Verdict: PASS

-t

[[2026-03-11]] Wed 22:22

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Config-only changes to agent/skill .md files |
| 2 | Docstrings | No | N/A | No Python modules changed (type:config) |
| 3 | sources/overview.md | No | N/A | Reflexion already attributed (line 986) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | evaluator-agent-final-disposition.md exists |
| 6 | No impact (1-4) | Yes | Pass | Config-only markdown task |

### Files Updated

- None

### Scratch Files Cleaned

- None
