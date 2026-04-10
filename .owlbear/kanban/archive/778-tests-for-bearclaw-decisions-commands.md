---
id: 778
title: Tests for bearclaw decisions commands
status: archived
priority: nice-to-have
created: 2026-03-13T11:32:08.6438877+01:00
updated: 2026-03-22T19:17:52.7221136+01:00
started: 2026-03-13T12:28:36.4671799+01:00
completed: 2026-03-22T19:17:52.7221136+01:00
tags:
    - cli
    - process
    - test
blocked: true
block_reason: Duplicate of committed decisions CLI tests and implementation already present in the repository (see commits 1c17456 and db69329). Do not dispatch to test-writer or builder.
class: standard
---

## Context
TDD tests for the decisions CLI subcommands.
See docs/research/bearclaw-decision-commands.md for research.

## Acceptance Criteria
- [ ] tests/test_cli_decisions.py using CliRunner + tmp_path fixtures
- [ ] Test list with 0, 1, 2+ pending decisions
- [ ] Test show by task_id (found + not found)
- [ ] Test resolve interactive flow with CliRunner input= mocking
- [ ] Test resolve moves file from pending/ to resolved/
- [ ] Test malformed frontmatter graceful error
- [ ] Coverage >= 90%% for decisions.py

[[2026-03-13]] Fri 12:33
## Research
See docs/research/bearclaw-decision-tests.md for full findings.

Key testing decisions:
- Fixture strategy: tmp_path + _make_decision_file() helper (matches test_cli_project.py)
- Interactive resolve: prefer typer.prompt() over Rich Prompt.ask() for CliRunner input= compat
- Monkeypatch DECISIONS_DIR constant to redirect to tmp_path
- 7 test classes mapping 1:1 to AC items

Recommendation for #777 builder: use typer.prompt(choices=...) not Rich Prompt.ask() for testability.

[[2026-03-20]] Fri 19:29
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| tests/test_cli_decisions.py using CliRunner + tmp_path fixtures | Already satisfied in the current workspace by tests/test_cli_decisions.py, and git history shows the decisions CLI test work was already committed. | Do not dispatch duplicate RED work. |
| Test list with 0, 1, 2+ pending decisions | Already covered in the committed test file. | No new implementation handoff. |
| Test show by task_id (found + not found) | Already covered in the committed test file, including frontmatter-based lookup behavior. | No new implementation handoff. |
| Test resolve interactive flow with CliRunner input= mocking | Already covered and aligned with the approved typer.prompt()/typer.confirm() interface. | No new implementation handoff. |
| Test resolve moves file from pending/ to resolved/ | Already covered in the committed tests and paired implementation. | No new implementation handoff. |
| Test malformed frontmatter graceful error | Already covered by the committed test suite. | No new implementation handoff. |
| Coverage >= 90% for decisions.py | Not a valid backlog driver here because the entire decisions CLI/test workstream is already committed in git history. | Treat as stale duplicate rather than advance. |

### Architecture Notes
- Current workspace evidence: src/bearclaw/commands/decisions.py and tests/test_cli_decisions.py already exist and implement the researched interface.
- Commit evidence: git history for those files already contains 1c17456 (test: add failing tests for bearclaw decisions CLI (#777, test-writer)) and db69329 (feat: implement bearclaw decisions list/show/resolve commands (#777, builder)).
- Pattern evidence: src/bearclaw/cli.py already imports and registers decisions_app, and tests/test_cli_decisions.py already follows the repo's CliRunner/tmp_path and input= patterns from tests/test_cli_project.py and tests/test_cli_chat.py.
- Board evidence: kanban/tasks/777-implement-bearclaw-decisions-list-show-resolve.md still depends_on [778], but the repository state already exceeds that board state. This is stale board metadata, not missing architecture work.
- Approving #778 would route another agent into already-committed work and duplicate the #777 lineage. This task is a stale backlog duplicate, not an executable handoff.

### Changes Made
- Appended this architecture review with current code, board, and git-history evidence.
- Moved #778 from backlog to ideation and blocked it as duplicate work already delivered in the repository.
- Released the claim.

### Dependencies
- Verified: docs/research/bearclaw-decision-commands.md
- Verified: docs/research/bearclaw-decision-tests.md
- Verified: src/bearclaw/cli.py, src/bearclaw/commands/decisions.py, tests/test_cli_project.py, tests/test_cli_chat.py, tests/test_cli_decisions.py
- Verified: git history for src/bearclaw/commands/decisions.py and tests/test_cli_decisions.py already contains committed RED/GREEN work under #777
