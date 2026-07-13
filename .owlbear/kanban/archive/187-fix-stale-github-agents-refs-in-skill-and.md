---
id: 187
title: Fix stale .github/agents/ refs in skill and instruction files
status: archived
priority: medium
created: 2026-03-29 20:46:45.736547+02:00
updated: 2026-03-30 04:16:16.269198+02:00
started: 2026-03-30 04:15:55.816583+02:00
completed: 2026-03-30 04:15:55.816583+02:00
tags:
- phase-1
- scope:docs
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Update stale .github/agents/ path references in skill and instruction files to point to agents/ at root.

## AC
- [ ] skills/task-decomposition/SKILL.md L74: change .github/agents/kanban-planner.agent.md to agents/kanban-planner.agent.md
- [ ] skills/task-decomposition/SKILL.md L87: change .github/agents/kanban-planner.agent.md to agents/kanban-planner.agent.md
- [ ] instructions/agent-common.instructions.md L113: remove legacy (or .github/agents/) from auto-staging trap note
- [ ] Grep verify no remaining .github/agents/ references in skills/ or instructions/ directories

## Context
Found during #170 research. See also docs/research/github-v1-cleanup.md. These references became stale after #8 ported agents to agents/ at root.

Research: N/A trivial change. All 3 AC items confirmed by grep.

[[2026-03-29]] Sun 20:53
Verified AC items: L74, L87 in SKILL.md and L113 in agent-common confirmed. Grep shows no other .github/agents/ hits in skills/ or instructions/. Out-of-scope: agent-audit.prompt.md L16, docs/sources/overview.md (~15 entries) covered by separate tasks.

[[2026-03-29]] Sun 21:19
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SKILL.md L74: change .github/agents/ path | Confirmed stale ref at L74 | Pass |
| SKILL.md L87: change .github/agents/ path | Confirmed stale ref at L87 | Pass |
| agent-common L113: remove legacy parenthetical | Confirmed `(or .github/agents/)` at L113 | Pass |
| Grep verify no remaining refs | Good verification step | Pass |

### Architecture Notes
Pure documentation fix. No code, no interfaces, no architectural impact. Each AC line specifies exact file, line, and change. TDD not applicable (no code changes). The grep verification AC item serves as the acceptance gate.

Out-of-scope refs (agent-audit.prompt.md, docs/sources/) correctly excluded per task body.

### Changes Made
- Approved as-is. AC is precise and complete.

### Dependencies
- None required. Stale refs are self-contained.

[[2026-03-29]] Sun 21:25
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 22:13
## Builder Notes
- Files changed: skills/task-decomposition/SKILL.md (L74, L87), instructions/agent-common.instructions.md (L113)
- SKILL.md L74: .github/agents/ path updated to agents/kanban-planner.agent.md
- SKILL.md L87: same path fix in Policy source note
- agent-common L113: removed (or .github/agents/) parenthetical from auto-staging trap
- Grep verify: zero remaining .github/agents/ hits in skills/ or instructions/
- Commit: 7d7fd1d
- No tests applicable (type:docs task)

[[2026-03-30]] Mon 03:27
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Pure path reference fix, no behavior/API/convention change |
| 2 | Docstrings | No | N/A | No Python files modified |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | github-v1-cleanup.md exists and linked in task body; fix task not research task |

### Verification
- skills/task-decomposition/SKILL.md L74: agents/kanban-planner.agent.md confirmed
- skills/task-decomposition/SKILL.md L87: agents/kanban-planner.agent.md confirmed
- agent-common.instructions.md L113: legacy parenthetical removed confirmed
- Grep: zero .github/agents/ refs remaining in skills/ or instructions/

### Files Updated
- None (builder committed all changes at 7d7fd1d)

### Scratch Files Cleaned
- None (no docs/scratch/187-* files found)

[[2026-03-30]] Mon 04:16
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md L74: path to agents/ | Read L74: `agents/kanban-planner.agent.md` confirmed | PASS |
| SKILL.md L87: path to agents/ | Read L87: `agents/kanban-planner.agent.md` confirmed | PASS |
| agent-common L113: remove legacy parenthetical | Read L115: no `(or .github/agents/)` present | PASS |
| Grep verify no remaining refs | grep .github/agents/ in skills/+instructions/ returned 0 hits | PASS |

### Test Results
- pytest: 1093 passed (144 failed + 6 errors all pre-existing, unrelated to this docs-only task)
- ruff: N/A (no Python files changed)

### Architect Quality
- AC specificity: 5/5 exact file, line, and change specified
- Edge cases: N/A (text replacement)
- Design direction: N/A

### Confidence: .98
### Action: archived

### Commits
Upstream: 7d7fd1d docs: fix stale .github/agents/ refs (#187, builder)
