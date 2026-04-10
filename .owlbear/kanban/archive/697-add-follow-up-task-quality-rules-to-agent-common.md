---
id: 697
title: Add follow-up task quality rules to agent-common.instructions.md
status: archived
priority: needed
created: 2026-03-08T17:11:47.7456591+01:00
updated: 2026-03-09T11:14:23.5144976+01:00
started: 2026-03-08T18:32:25.8990111+01:00
completed: 2026-03-09T11:14:23.5144976+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

Add new section 'Follow-up task quality' to agent-common.instructions.md:\n- Rule 1: Every follow-up task requires AC (acceptance criteria)\n- Rule 2: Single-responsibility  one concern per task, affected files listed\n- Rule 3: Target backlog status  follow-up tasks from non-planner agents always go to backlog so architect gate applies\n- Note: only the kanban-planner may create tasks at ideation; all other agents create at backlog\n\nAC:\n- [ ] agent-common has 'Follow-up task quality' section with 3 rules\n- [ ] Section explicitly states follow-ups go to backlog\n- [ ] No new rule exceeds 2 sentences (token budget conscious per #686)

[[2026-03-08]] Sun 18:06
## Architecture Review

### AC Assessment

| AC Line | Assessment | Verdict |
|---------|-----------|---------|
| agent-common has section with 3 rules | Verifiable: count rules in section | Pass |
| Section explicitly states backlog | Verifiable: grep for 'backlog' | Pass |
| No rule exceeds 2 sentences | Verifiable: count sentences per rule | Pass |

### Architecture Notes

- **Placement:** Insert after 'Self-defense against orchestrator degradation' (line 37) and before 'Post-task reflection' (line 39). Groups task-quality rules near task-discipline.
- **Consistency with pipeline:** copilot-instructions.md defines Planner role as entry to ideation. This rule codifies that non-planner agents skip ideation (they already have context) and target backlog so the architect gate still applies. Consistent.
- **No conflict with researcher:** researcher.agent.md critical rule 'Never execute kanban create commands' is more restrictive and agent-specific. agent-common rule is general floor. No contradiction.
- **No TDD needed:** instructions file edit, not source code.
- **Token impact:** 3 rules at <=2 sentences each is ~80 tokens. Acceptable per #686 analysis (agent-common is ~8K chars, this adds ~400 chars = ~5% growth).

[[2026-03-08]] Sun 18:19
## Builder Notes
- Files changed: .github/instructions/agent-common.instructions.md
- Inserted 'Follow-up task quality' section (lines 39-44) between 'Self-defense' and 'Post-task reflection'
- 3 rules, each <=2 sentences, explicitly targets backlog
- No tests needed (instructions file, not Python)

[[2026-03-08]] Sun 18:27
## Review Evidence
### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| agent-common has 'Follow-up task quality' section with 3 rules | Section header at line 39, 3 numbered rules at lines 41-43 | PASS |
| Section explicitly states follow-ups go to backlog | Line 43: 'Non-planner agents always create follow-up tasks at backlog status so the architect gate applies' | PASS |
| No new rule exceeds 2 sentences | Rule 1: 1 sentence, Rule 2: 1 sentence, Rule 3: 2 sentences | PASS |

### Placement Verified
After 'Self-defense against orchestrator degradation' (ends ~line 37), before 'Post-task reflection' (line 45). Correct.

### Test Quality
N/A -- instructions file edit, no Python code.

### Security: No issues -- documentation file only.
### Verdict: PASS confidence .95

[[2026-03-08]] Sun 18:32
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Agent dispatch rule, no behavior/API/convention change |
| 2 | Docstrings | No | N/A | No Python modules changed |
| 3 | sources.md | No | N/A | Original conventions, no external patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase |
| 6 | No impact | Yes | Pass | Instructions file only, no docs artifacts needed |

### Files Updated
- None

### Scratch Files Cleaned
- None (no scratch files for #697)

[[2026-03-09]] Mon 04:57
Wave 4, agent: auditor

[[2026-03-09]] Mon 11:13
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| agent-common has 'Follow-up task quality' section with 3 rules | Section header at L78, 3 numbered rules L80-82 | PASS |
| Section explicitly states follow-ups go to backlog | L82: 'Non-planner agents always create follow-up tasks at backlog status' | PASS |
| No new rule exceeds 2 sentences | Rule 1: 1 sentence, Rule 2: 1 sentence, Rule 3: 2 sentences | PASS |

### Test Results
- pytest: 1271 passed, 1 failed (pre-existing slack_sdk env issue), 20 skipped
- ruff: 3 pre-existing errors (screenshot.py E501, test_bootstrap_structure.py I001 x2), none from #697

### Confidence: .97
### Action: archive

[[2026-03-09]] Mon 11:14
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| agent-common has 'Follow-up task quality' section with 3 rules | Section header at L78, 3 numbered rules L80-82 | PASS |
| Section explicitly states follow-ups go to backlog | L82: 'Non-planner agents always create follow-up tasks at backlog status' | PASS |
| No new rule exceeds 2 sentences | Rule 1: 1 sent, Rule 2: 1 sent, Rule 3: 2 sent | PASS |

### Test Results
- pytest: 1271 passed, 1 failed (pre-existing slack_sdk env issue), 20 skipped
- ruff: 3 pre-existing errors (screenshot.py, test_bootstrap_structure.py), none from #697

### Confidence: .97
### Action: archive
