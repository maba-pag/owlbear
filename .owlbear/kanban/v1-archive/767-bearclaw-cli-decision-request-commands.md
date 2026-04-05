---
id: 767
title: 'BearClaw CLI: decision request commands'
status: archived
priority: nice-to-have
created: 2026-03-13T09:31:49.4231407+01:00
updated: 2026-03-22T19:17:50.2348273+01:00
started: 2026-03-13T11:21:58.0043163+01:00
completed: 2026-03-22T19:17:50.2348273+01:00
tags:
    - cli
    - process
blocked: true
block_reason: 'Stale duplicate: #777/#778 lineage already delivered in git history, and #767 still encodes the legacy status-based decision resolution contract.'
class: standard
---

## Context
The decision-request process (docs/decisions/) is file-based. Add CLI convenience commands for listing and resolving decisions.

## Acceptance Criteria
- [ ] 'bearclaw decisions list'  lists pending decision requests with task ID, title, age, urgency
- [ ] 'bearclaw decisions resolve {id}'  interactive resolution flow (pick option, add notes, move file to resolved/)
- [ ] 'bearclaw decisions show {id}'  display full decision request contents
- [ ] Integration with existing Typer CLI structure

[[2026-03-13]] Fri 11:32
## Research
See docs/research/bearclaw-decision-commands.md for findings.

Key decisions:
- Manual yaml.safe_load (no python-frontmatter dep, matches agent_def.py pattern)
- Interactive resolve flow (Rich Prompt.ask + typer.prompt)
- Hardcoded docs/decisions/ path (KISS)

Follow-up tasks created:
- #777 Implement bearclaw decisions list/show/resolve commands
- #778 Tests for bearclaw decisions commands

[[2026-03-20]] Fri 19:33
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 'bearclaw decisions list' lists pending decision requests with task ID, title, age, urgency | Under-specified for a builder handoff and already delivered in the committed decisions CLI work; the refined child task #777 already tightened this into a concrete Rich Table contract. | Do not dispatch duplicate work from the parent task. |
| 'bearclaw decisions resolve {id}' interactive resolution flow (pick option, add notes, move file to resolved/) | Stale contract. The canonical decision-request workflow now uses approved/decision/notes frontmatter fields and planner-owned moves to resolved/, while this task and its research still describe legacy status: resolved plus direct file moves. The repository also already contains the older implementation and tests. | Block stale duplicate work; if contract alignment is needed, create a new follow-up task instead of advancing #767. |
| 'bearclaw decisions show {id}' display full decision request contents | Clear intent, but the command already exists in src/bearclaw/commands/decisions.py and is covered by committed tests. | Do not dispatch duplicate work. |
| Integration with existing Typer CLI structure | Too vague for a backlog implementation contract and already satisfied by the existing import/add_typer pattern in src/bearclaw/cli.py. | Do not dispatch duplicate work. |

### Architecture Notes
- Board lineage: #767 already spawned #777 (implementation) and #778 (tests). #778 has already been pushed back to ideation and blocked as a duplicate of delivered work.
- Repository evidence: src/bearclaw/commands/decisions.py, tests/test_cli_decisions.py, and the decisions_app registration in src/bearclaw/cli.py are present today.
- Git evidence: the decisions workstream was already committed in 1c17456 (test: add failing tests for bearclaw decisions CLI (#777, test-writer)) and db69329 (feat: implement bearclaw decisions list/show/resolve commands (#777, builder)).
- Contract evidence: .github/instructions/decision-requests.instructions.md and docs/decisions/README.md define the current decision-request workflow around approved/decision/notes metadata and planner-driven file moves. This task's research doc still encodes the older status: resolved plus ## Resolution pattern.
- Architectural decision: do not approve or refine the stale parent task. Parking it in ideation with a block keeps it out of dispatch rotation until planner/auditor cleanup or a separate correction task reconciles the CLI contract with the current instructions.

### Changes Made
- Appended this architecture review with board, repository, and git-history evidence.
- No child tasks created: #777 and #778 already exist as the decomposed implementation/test pair.
- Next board action will move #767 from backlog to ideation and block it as a stale duplicate.

### Dependencies
- Verified: docs/research/bearclaw-decision-commands.md
- Verified: .github/instructions/decision-requests.instructions.md
- Verified: docs/decisions/README.md
- Verified: src/bearclaw/cli.py, src/bearclaw/commands/decisions.py, tests/test_cli_decisions.py
- Verified: related tasks #777 and #778
- Verified: git commits 1c17456 and db69329
