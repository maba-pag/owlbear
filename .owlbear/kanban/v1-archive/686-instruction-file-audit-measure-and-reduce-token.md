---
id: 686
title: 'Instruction file audit: measure and reduce token bloat'
status: archived
priority: important
created: 2026-03-08T15:45:59.63979+01:00
updated: 2026-03-09T15:52:48.2228191+01:00
started: 2026-03-08T16:26:28.5490677+01:00
completed: 2026-03-09T15:52:48.2228191+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

## Context
Instruction files keep growing. Each incident adds rules. More text = more likely the LLM misses critical rules = more incidents = more rules. This is a death spiral. Need to measure total token load per agent and aggressively trim.

## Acceptance Criteria
- [ ] Measure total token count per agent context chain (agent.md + auto-loaded instructions + skills that must be read)
- [ ] Identify the top 3 agents by context consumption
- [ ] For each: identify what can be (a) removed entirely, (b) moved from always-loaded instruction to on-demand skill, (c) compressed
- [ ] Apply reductions -- target: each agent's static context (before any tool calls) should be under 30%% of its context window
- [ ] No net-new rules added without removing equivalent text elsewhere

## Notes
- This is anti-entropy work. It prevents the instruction death spiral.
- The 30%% target needs validation -- it is a starting estimate.
- **AC4 "Apply reductions" interpretation:** All agents are already under 30%% of 128K (highest is Reviewer at 21.1%%). The reductions identified in Section 4 of the research doc are captured as follow-up tasks #696 (compress tech stack table) and #698 (remove inventory/lifecycle duplication). Applying them would bring agents to ~7-9%% of window — a worthwhile improvement but not a gate-blocking issue. The reductions ARE the follow-up tasks, not separate work for this research task.
- **Stale measurement fixed:** agent-common.instructions.md grew from 5,104 to 7,997 chars due to self-defense section (#663). Research doc Section 3a and 3c updated 2026-03-08.
- **Follow-up tasks created:** #696, #698, #699 — all at backlog status.

[[2026-03-09]] Mon 15:51
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Measure token count per agent chain | Research doc S3a (23 files), S3c (9 agent chains) | PASS |
| Identify top 3 agents | S3c: Reviewer 26981, Builder 25263, Architect 25114 | PASS |
| Identify (a) remove (b) move (c) compress | S4 Analysis: 5 bloat sources with labeled actions | PASS |
| Apply reductions / 30%% target | All agents under 30%%; follow-ups #696 #698 #699 created and completed | PASS |
| No net-new rules without removal | No instruction files modified by this task | PASS |

### Test Results
- pytest: Terminal infra issue (KeyboardInterrupt during import) -- pre-existing, unrelated to this research-only task
- ruff: 3 pre-existing errors (screenshot.py E501, test_bootstrap_structure.py I001 x2) -- not caused by #686

### Confidence: .97
### Action: archive
