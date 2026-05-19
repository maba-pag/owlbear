---
id: 905
title: 'bearclaw board: Rich table view of kanban tasks by status and assignee'
status: archived
priority: nice-to-have
created: 2026-03-21T15:00:02.2164944+01:00
updated: 2026-03-26T16:07:16.0447033+01:00
tags:
    - cli
    - tooling
    - phase-14
class: standard
---

Add 'bearclaw board' CLI command that renders a Rich table grouped by status with columns: ID, title, assignee, age (days in status), tags. Target ~120 LOC in src/bearclaw/. No new deps (Rich is already transitive). See docs/research/kanban-replacement-options.md sections 5 and 6.

## Research

Research doc: docs/research/bearclaw-board-command.md

Key findings:

- Existing kanban-md board output is assignee summary only; it does not provide task rows.
- Recommended seam: kanban-md list JSON for task rows plus kanban-md move log JSON for status age.
- Age should use the latest move into the current status, with created as the fallback.
- Implementation should stay in src/bearclaw/commands/board.py with tests in tests/test_cli_board.py.

Follow-up tasks created:

- #909 Test bearclaw board command rendering and status age (RED)
- #910 Implement bearclaw board Rich table command

Follow-up create commands:

- `kanban\kanban-md.exe create "Test bearclaw board command rendering and status age (RED)" --status ideation --priority nice-to-have --tags "cli,tooling,phase-14,test,type:test,scope:cli" --body "Research follow-up from docs/research/bearclaw-board-command.md. Add failing tests for a new bearclaw board command in tests/test_cli_board.py. AC: (1) help output exposes a top-level board command; (2) command renders a Rich table grouped by status with columns ID, Title, Assignee, Age, Tags; (3) assignee column prefers assignee, then claimed_by, then --; (4) age in status comes from the latest kanban-md move log entry into the current status, with created timestamp fallback when no move exists; (5) empty result prints a friendly no-tasks message; (6) tests use CliRunner and mocked kanban-md JSON subprocess output only; (7) all new tests fail before implementation."`
- `kanban\kanban-md.exe create "Implement bearclaw board Rich table command" --status ideation --priority nice-to-have --tags "cli,tooling,phase-14,type:build,scope:cli" --body "Research follow-up from docs/research/bearclaw-board-command.md. Implement a top-level bearclaw board command in src/bearclaw/commands/board.py and wire it from src/bearclaw/cli.py. AC: (1) invoke kanban-md list --json once to load visible tasks and kanban-md log --action move --json to load move history; (2) render a Rich table grouped by configured status order with columns ID, Title, Assignee, Age, Tags; (3) assignee display prefers assignee, then claimed_by, then --; (4) age uses the most recent move into the current status, falling back to created when no move exists; (5) use existing Rich/Typer patterns only, no new dependencies; (6) task-local helpers stay in src/bearclaw/commands/board.py; (7) tests from the paired RED task pass."`

Attribution updated:

- docs/sources/overview.md

Scheduling note:

- #905 now serves as the research umbrella. The architect should either schedule the #909 and #910 split or consolidate it back into #905 before implementation.

[[2026-03-21]] Sat 16:39

## Architecture Review

See docs/scratch/905-architect.md for full review.

[[2026-03-21]] Sat 17:24

## Architecture Review

**Verdict:** SPLIT -> #909, #910

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add 'bearclaw board' CLI command that renders a Rich table grouped by status with columns: ID, title, assignee, age (days in status), tags. | Valid user-facing feature, but this umbrella no longer carries an executable contract: the RED and GREEN pair already exists as #909 and #910, and implementing directly from #905 would bypass the test-first split. | Keep #905 as the blocked parent; route execution through #909 then #910. |
| Target ~120 LOC in src/bearclaw/. | LOC is not a verifiable acceptance criterion and should not drive dispatch. | Treat as a sizing hint only; do not use it as a gate. |
| No new deps (Rich is already transitive). | Valid constraint, but it belongs on the implementation child task, not the umbrella parent. | Preserve on #910's contract; no dependency work from #905. |
| See docs/research/kanban-replacement-options.md sections 5 and 6. | Source reference, not an executable acceptance criterion. | Keep as context only. |
| Scheduling note: #905 now serves as the research umbrella. The architect should either schedule the #909 and #910 split or consolidate it back into #905 before implementation. | The split is the correct shape. Consolidating would mix RED and GREEN again and duplicate the already-created child tasks. | Confirm split into #909 and #910; block direct execution of #905. |

### Architecture Notes

- Existing CLI composition in src/bearclaw/cli.py uses dedicated Typer modules added via app.add_typer(...); a new board command belongs in its own src/bearclaw/commands/board.py module, not in core toolsets or a monolithic cli.py edit.
- Existing Rich-table patterns live in src/bearclaw/commands/project.py and src/bearclaw/commands/decisions.py, with CliRunner coverage in tests/test_cli_project.py and tests/test_cli_decisions.py. The split child tasks already target that pattern correctly.
- The age column should stay anchored to kanban move history, not generic updated timestamps. The research recommendation aligns with move-detail parsing already used in src/owlbear/core/retrospective_hook.py and with status ordering in kanban/config.yml.
- No new system boundary is introduced beyond local kanban-md subprocess calls; keep the work CLI-local and avoid expanding scope into owlbear toolsets or configuration in this parent card.
- TDD rule: #905 itself must not advance as an implementation task because the concrete RED predecessor exists separately as #909. The executable path is #909 (tests) -> #910 (build). If #910 is reviewed later without an explicit dependency on #909, tighten that in #910 rather than reopening #905.

### Changes Made

- Appended this architecture review with codebase evidence from the existing BearClaw CLI and kanban patterns.
- Blocked #905 as a superseded umbrella so it does not get dispatched as a direct implementation card.
- No child tasks created; verified #909 and #910 already exist as the intended split.

### Dependencies

- Verified: docs/research/bearclaw-board-command.md
- Verified: src/bearclaw/cli.py, src/bearclaw/commands/project.py, src/bearclaw/commands/decisions.py
- Verified: tests/test_cli_project.py, tests/test_cli_decisions.py
- Verified: src/owlbear/core/retrospective_hook.py, kanban/config.yml
- Verified: related tasks #909 and #910

[[2026-03-26]] Thu 16:07

## Architecture Review

**Verdict:** Approve (completed umbrella tracker)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| All original AC (Rich table, status grouping, age column, etc.) | Fully delivered through child tasks #909 (RED tests, archived) and #910 (implementation, archived). | No further work needed on this parent. |

### Architecture Notes

- Both child tasks #909 and #910 have been archived, confirming the full TDD cycle completed successfully.
- #905 is a research umbrella tracker that was correctly split and blocked. It carries no executable contract of its own.
- Advancing to todo so the downstream pipeline gates (reviewer, writer, auditor) can close it out as a completed tracker.

### Changes Made

- Unblocked #905 (children are done).
- Advanced to todo for pipeline pass-through.

### Dependencies

- Verified: #909 (RED tests) is archived.
- Verified: #910 (implementation, depends on #909) is archived.
- No outstanding child work remains.
