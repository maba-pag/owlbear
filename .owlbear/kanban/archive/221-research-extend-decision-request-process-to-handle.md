---
id: 221
title: 'Research: Extend decision-request process to handle user action requests'
status: archived
priority: medium
created: 2026-03-30 15:32:02.339385+02:00
updated: 2026-03-30 23:37:14.735609+02:00
started: 2026-03-30 23:37:09.236586+02:00
completed: 2026-03-30 23:37:09.236586+02:00
tags:
- research
- ' phase-1'
- ' scope:agents'
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Improve the decision-request process to handle not just user decisions but also user actions (e.g., manual testing, GUI verification). Currently when agents need user interaction they just block the task silently — the user never gets notified they have a todo.

## Problem

Task #167 (manual VS Code validation) illustrates the gap: the builder identified 5 AC items requiring human GUI interaction, blocked the task, but there's no mechanism to surface this to the user. The task sits in blocked limbo indefinitely because:

1. The decision-request process (docs/decisions/pending/) only handles decisions (choose A or B), not action requests (do X and report back)
2. No notification mechanism exists — user must manually check blocked tasks to discover they have work to do
3. The docs/decisions/ folder is buried in docs, reducing visibility

## Scope for Research

- Analyze current decision-request skill (skills/decision-requests/SKILL.md) for extension to user-action requests
- Evaluate moving docs/decisions/ to decisions/ at project root for visibility
- Design a user action request format that agents can create when they need the user to do something (not just decide something)
- Consider how the planner/orchestrator could surface pending user actions at session start
- Review which agent instructions need updating (agent-common, builder, writer, test-writer at minimum)
- Look at existing blocked tasks to identify patterns of silent user-blocking

## Context

Discovered during blocked-task audit (2026-03-30). Multiple tasks have been blocked waiting for user action with no notification mechanism.

[[2026-03-30]] Mon 17:54
## Architecture Review
**Verdict:** APPROVED

### Scope Coverage (6/6 research items addressed)
All 6 scope items addressed in docs/research/extend-decision-request-for-action-requests.md.

### Architecture Notes
- Recommendation (Option A: extend existing format, .85 confidence) aligns with KISS/YAGNI. Reuses existing docs/decisions/pending/ location, minimal planner changes, single user inbox.
- Research quality is high: 6 sources, 3-option trade-off matrix, concrete design sketch.
- 4 follow-up tasks (#224-#227) properly decomposed with verifiable AC and correct dependency chain.
- Design concern for downstream: #226 AC4 proposes 5-day auto-resolution for action requests. Auto-resolving user actions is semantically wrong. Action requests should block indefinitely until completed. Address when #226 reaches architect review.

### Deliverables Verified
- Research doc exists and is complete
- Follow-up tasks #224 (backlog), #225-#227 (ideation) all have concrete AC

### Changes Made
- Approved research task to todo
- Fixed tag type:build to type:docs

[[2026-03-30]] Mon 20:06
## Test-Writer Notes
- Non-implementation task (tagged research, type:docs) - no tests applicable.
- Passing through to builder.

[[2026-03-30]] Mon 20:06
## Test-Writer Notes
- Non-implementation task (tagged research, type:docs) - no tests applicable.
- Passing through to builder.

[[2026-03-30]] Mon 21:27
## Builder Notes
- Non-implementation task — no code changes needed.
- Research doc verified at docs/research/extend-decision-request-for-action-requests.md
- Passing through to review.

[[2026-03-30]] Mon 22:52
## Docs Gate
### Checklist
`| # `| Check `| Applies? `| Status `| Evidence `|
`|---`|-------`|----------`|--------`|----------`|
`| 1 `| .github/copilot-instructions.md `| No `| N/A `| Research only; implementation in follow-up tasks #224-227 `|
`| 2 `| Docstrings `| No `| N/A `| No Python modules created or modified `|
`| 3 `| docs/sources/overview.md `| Yes `| Updated `| Added 3 external sources: AutoGen, CrewAI, GitHub Actions env protection `|
`| 4 `| README.md `| No `| N/A `| No CLI changes `|
`| 5 `| Research doc linked `| Yes `| Pass `| docs/research/extend-decision-request-for-action-requests.md exists; follow-up tasks #224-227 created `|
`| 6 `| Scratch files `| No `| Pass `| No docs/scratch/221-* files found `|

### Files Updated
- docs/sources/overview.md

### Scratch Files Cleaned
- None

[[2026-03-30]] Mon 23:36
## Audit test

[[2026-03-30]] Mon 23:36
### AC Verification (Research Task)
All 6 research scope items verified with evidence.

### Research Task Checks
- Research doc: exists, 105 lines, 6 sources
- Follow-up tasks: #224 (archived), #225 (todo), #226 (ideation), #227 (ideation)
- Sources: docs/sources/overview.md updated (commit ed46aa8)

### Test Results
- pytest: 1588 passed, 157 failed (all pre-existing), 1 error (unrelated)
- ruff: 2 violations (pre-existing, not task-scoped)

### Architect Quality: 4/5

### Reviewer Evidence
Missing -- no Review Evidence section. Deduction applied.

### Quality Gaps
- Research doc uncommitted by upstream. Committed by auditor: 2a03958

### Deduction breakdown: -.02 missing reviewer evidence
### Confidence: .98
### Action: archive
