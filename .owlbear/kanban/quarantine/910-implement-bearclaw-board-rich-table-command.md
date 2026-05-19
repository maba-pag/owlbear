---
id: 910
title: Implement bearclaw board Rich table command
status: archived
priority: nice-to-have
created: 2026-03-21T15:29:00.698892+01:00
updated: 2026-03-23T01:43:48.9345163+01:00
started: 2026-03-23T01:43:44.7504822+01:00
completed: 2026-03-23T01:43:44.7504822+01:00
tags:
    - cli
    - tooling
    - phase-14
    - type:build
    - scope:cli
depends_on:
    - 909
class: standard
---

Research follow-up from docs/research/bearclaw-board-command.md. Implement a top-level bearclaw board command in src/bearclaw/commands/board.py and wire it from src/bearclaw/cli.py.

AC:
(1) register a dedicated board Typer app in src/bearclaw/commands/board.py and wire it from src/bearclaw/cli.py so bearclaw --help exposes a top-level board command.
(2) invoke kanban-md list --json exactly once to load visible tasks and kanban-md log --action move --json exactly once to load move history for age calculation.
(3) render a Rich table grouped in the order defined by kanban/config.yml statuses, with columns ID, Title, Assignee, Age, Tags.
(4) assignee display prefers assignee, then claimed_by, then --.
(5) age is derived from the most recent move into the current status, falling back to the task created timestamp when no matching move exists.
(6) when no visible tasks are returned, print a friendly no-tasks message instead of a blank table.
(7) follow existing Rich/Typer/subprocess patterns only, add no new dependencies, and keep task-local helpers in src/bearclaw/commands/board.py.
(8) tests from #909 pass.

[[2026-03-21]] Sat 16:45

## Research

Doc: docs/research/bearclaw-board-command-implementation-gate.md

Summary: Live kanban-md JSON and current BearClaw CLI patterns confirm the existing #910 MVP: one list --json call, one log --action move --json call, a dedicated src/bearclaw/commands/board.py wired via app.add_typer(), config-driven status order, assignee fallback assignee -> claimed_by -> --, and age from the latest move into the current status with created fallback. Keep broader failure hardening and tui.age_threshold styling out of this task.

Follow-up created:

- #920 Harden bearclaw board command failures and JSON parsing
- #921 Honor kanban age thresholds in bearclaw board Rich output

Commands executed:

- kanban\kanban-md.exe create 'Harden bearclaw board command failures and JSON parsing' --priority important --status ideation --tags 'cli,tooling,phase-14,type:build,scope:cli' --body 'Research follow-up from docs/research/bearclaw-board-command-implementation-gate.md. Add explicit user-facing failure handling to bearclaw board after the MVP happy-path task lands. AC: (1) board routes missing kanban-md, non-zero kanban-md list/log exits, and invalid JSON responses through bearclaw.commands._cli_error instead of raw tracebacks; (2) error messages distinguish task-list load failures from move-log load failures and mention kanban-md; (3) existing happy-path board tests stay green and CLI failure-path tests cover each failure class; (4) scope stays in src/bearclaw/commands/board.py and tests/test_cli_board.py.' -> #920
- kanban\kanban-md.exe create 'Honor kanban age thresholds in bearclaw board Rich output' --priority nice-to-have --status ideation --tags 'cli,tooling,phase-14,type:build,scope:cli' --body 'Research follow-up from docs/research/bearclaw-board-command-implementation-gate.md. Align bearclaw board age styling with the existing kanban TUI thresholds. AC: (1) board reads tui.age_thresholds from kanban/config.yml and maps the configured thresholds to Rich styles for the Age column; (2) status order and underlying age values remain unchanged; (3) malformed or missing thresholds fall back to unstyled age text rather than breaking the command; (4) CLI tests cover at least one threshold boundary and one malformed-config fallback; (5) no new dependencies are added and scope remains in src/bearclaw/commands/board.py and tests/test_cli_board.py.' -> #921

Attribution updated: docs/sources/overview.md

[[2026-03-21]] Sat 17:34

## Architecture Review

See docs/scratch/910-architect.md for full review.

[[2026-03-22]] Sun 22:25

## Test-Writer Notes

- No new tests written — pre-implementation pass-through.
- Implementation (src/bearclaw/commands/board.py) was built during the #909 builder cycle before this RED phase ran.
- AC8 explicitly delegates test coverage to #909's suite (tests/test_cli_board.py).
- AC coverage (28 existing tests, all PASS against current board.py):
  - AC1: TestFromAC_BoardRegistration (2 tests) -- --help + board --help
  - AC2: PARTIAL -- subprocess.run call count is not asserted; dispatch logic confirms list/log receive correct args but no explicit assert call_count==2. Builder must verify explicitly.
  - AC3: TestFromAC_BoardRendering (11 tests) -- all 5 columns + status order + task content
  - AC4: TestFromAC_AssigneeDisplay (3 tests) -- assignee > claimed_by > --
  - AC5: TestFromAC_AgeInStatus (4 tests) -- latest move, created fallback, wrong-dest exclusion
  - AC6: TestFromAC_EmptyBoard (3 tests) -- exit 0 + No tasks message
  - AC7: Not directly testable (code style constraint)
  - AC8: All 28 tests pass (uv run pytest tests/test_cli_board.py -q)
- Additional 5 tests from #924 (TestFromAC_BoardFailurePaths) also present.
- No new test file created; no source files touched.

[[2026-03-22]] Sun 23:38

## Builder Notes

- Files changed: tests/test_cli_board.py (added TestBuilderDiscovered; board.py already committed in #909/#924)
- Tests: 30 passed (28 TestFromAC + 2 TestBuilderDiscovered), coverage 99% on board.py
- Lint: ruff clean on src/bearclaw/commands/board.py + tests/test_cli_board.py
- Evidence: 30 passed, 2 warnings in 2.41s (all TestFromAC_ pass); ruff All checks passed
- Fixes applied: Added TestBuilderDiscovered with 2 AC2 call-count tests (subprocess.run called exactly 2x with tasks, 1x empty board); fixed PT018 compound assertions

[[2026-03-23]] Mon 00:10

## Review Evidence

### Test Results

- pytest tests/test_cli_board.py -q --tb=short: 30 passed, 0 failed, 2 warnings.

- pytest AC8 subset (-k TestFromAC_BoardRegistration or TestFromAC_BoardRendering or TestFromAC_AssigneeDisplay or TestFromAC_AgeInStatus or TestFromAC_EmptyBoard): 23 passed, 7 deselected, 0 failed, 2 warnings.

### Lint Results

- ruff check src/bearclaw/commands/board.py src/bearclaw/cli.py tests/test_cli_board.py: All checks passed.

### Coverage

- coverage report src/bearclaw/commands/board.py src/bearclaw/cli.py: board.py 99% (line 66 miss), cli.py 95% (lines 69-70 miss), total 97%.

### Pass 1 - CRITICAL

- Test-writer AC coverage: AC1/3/4/5/6/8 covered by TestFromAC classes; AC2 was LAX in TestFromAC (no exact call-count assertion) but compensated by builder tests at tests/test_cli_board.py lines 551-572; AC7 verified by code/commit inspection.

- Security review: no hardcoded secrets; subprocess uses argv list with no shell=True at src/bearclaw/commands/board.py line 44; no eval/exec/pickle usage; no dependency manifest changes in #909/#924/#910 commit scopes.

- Test integrity: #910 commit d76b504 appends TestBuilderDiscovered only; no TestFromAC_* method changes, no weakened/removed assertions.

- Test quality ratings: assertion specificity ADEQUATE, negative/error-path coverage STRONG, mutation resistance STRONG, independence STRONG, naming STRONG; no WEAK dimensions.

- Data safety: no persistent writes, no shared mutable concurrency, no atomicity risks in scoped command flow.

- Implementation-aware gaps: no significant untested behavioral paths for MVP scope; _run_kanban failure branches and _age_in_status branch logic are covered.

### AC Compliance

- AC1 PASS: board Typer app in src/bearclaw/commands/board.py lines 18 and 95, wired in src/bearclaw/cli.py lines 18 and 56; validated by tests/test_cli_board.py lines 103 and 108.

- AC2 PASS: list and move-log calls implemented at src/bearclaw/commands/board.py lines 97 and 104 with empty-board short-circuit at lines 99-101; exact call-count and args validated by tests/test_cli_board.py lines 551-572.

- AC3 PASS: status-order grouping at src/bearclaw/commands/board.py lines 103 and 111-112, columns ID/Title/Assignee/Age/Tags at lines 119-123; verified by tests/test_cli_board.py lines 122-150 and 185.

- AC4 PASS: assignee fallback (assignee then claimed_by then --) at src/bearclaw/commands/board.py line 59; verified by tests/test_cli_board.py lines 224, 233, 241.

- AC5 PASS: age uses latest move into current status with created fallback at src/bearclaw/commands/board.py lines 74-89; verified by tests/test_cli_board.py lines 258, 287, 307, 337.

- AC6 PASS: friendly no-tasks message at src/bearclaw/commands/board.py lines 99-101; verified by tests/test_cli_board.py line 382 and related empty-board tests.

- AC7 PASS: helpers remain task-local in src/bearclaw/commands/board.py lines 26-91 and commit scopes (#909, #924, #910) show no dependency-manifest changes.

- AC8 PASS: #909 TestFromAC classes pass (23 passed, 0 failed, 7 deselected) in focused pytest subset run.

### Pass 2 - INFORMATIONAL

- Non-blocking: _age_in_status currently compares ISO timestamp strings via max(); parsing datetime before max would be more defensive for mixed-offset inputs.

### Verdict

- PASS with confidence .94

### Action Taken

- Next command executed: kanban\\kanban-md.exe edit 910 --status docs --release

[[2026-03-23]] Mon 01:43

## Audit

### AC Verification

| AC | Evidence | Status |
|-----|----------|--------|
| AC1 board app wired | board.py L18 app=typer.Typer(); cli.py L17+L56 add_typer(board_app) | PASS |
| AC2 two kanban-md calls | board.py L97 list --json; L104 log --action move --json | PASS |
| AC3 Rich table grouped | board.py L103-135: config-driven status order, columns ID/Title/Assignee/Age/Tags | PASS |
| AC4 assignee fallback | board.py L59: assignee > claimed_by > -- | PASS |
| AC5 age from move/created | board.py L74-92: latest move match + created fallback | PASS |
| AC6 empty board msg | board.py L99-101: typer.echo no-tasks | PASS |
| AC7 no new deps, local helpers | All helpers in board.py, no pyproject changes | PASS |
| AC8 #909 tests pass | 30 passed, 0 failed (uv run pytest tests/test_cli_board.py) | PASS |

### Test Results

- pytest (scoped): 30 passed, 0 failed, 2 warnings (2.40s)
- pytest (full suite): 3774 passed, 93 failed (pre-existing numpy/import issues unrelated to #910), 20 skipped
- ruff (scoped): All checks passed
- ruff (global): pre-existing baseline violations in unrelated files

### Architect Quality

- AC specificity: 8 items, each specific and verifiable
- Edge-case coverage: AC4 (assignee chain), AC5 (age fallback), AC6 (empty board)
- Design direction: research doc led to clean MVP with hardening (#920) and styling (#921) follow-ups
- AC quality score: 4 (adequate; AC2 could have been explicit about subprocess call-count for test verification)

### Confidence: .96

### Action: archive
