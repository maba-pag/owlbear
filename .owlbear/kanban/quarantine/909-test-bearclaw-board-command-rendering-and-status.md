---
id: 909
title: Test bearclaw board command rendering and status age (RED)
status: archived
priority: nice-to-have
created: 2026-03-21T15:28:59.7546598+01:00
updated: 2026-03-22T04:36:25.6512693+01:00
started: 2026-03-22T04:35:43.0379548+01:00
completed: 2026-03-22T04:35:43.0379548+01:00
tags:
    - cli
    - tooling
    - phase-14
    - test
    - type:test
    - scope:cli
class: standard
---

Research follow-up from docs/research/bearclaw-board-command.md. Add failing tests for a new bearclaw board command in tests/test_cli_board.py.

AC:

1. Root bearclaw --help output lists board as a top-level command.
2. bearclaw board renders Rich table sections grouped by status in the configured order from kanban/config.yml, with headers ID, Title, Assignee, Age, Tags.
3. Assignee display prefers assignee, then claimed_by, then --.
4. Age in status comes from the latest kanban-md log --action move --json entry whose destination matches the task's current status, with created fallback when no matching move exists.
5. When kanban-md list --json returns no visible tasks, the command exits 0 and prints a no-tasks message containing No tasks instead of a blank Rich table.
6. Tests use CliRunner and mocked kanban-md JSON subprocess output only; no live kanban binary or temp board files.
7. All new tests fail before implementation.

[[2026-03-21]] Sat 16:58

## Research

See docs/research/bearclaw-board-command-red-gate.md and docs/scratch/909-researcher.md. Created follow-up task #923.

[[2026-03-21]] Sat 17:33

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Precise and aligned with the root Typer help checks already used against bearclaw.cli.app. | Kept |
| 2 | Needed the status-order rule from kanban/config.yml so the RED contract matches the paired GREEN task and research. | Rewritten |
| 3 | Precise assignee fallback already grounded in the board research and kanban list JSON fields. | Kept |
| 4 | Precise age rule aligns with move-log parsing precedent and the parent board research. | Kept |
| 5 | Friendly was subjective; replaced with an exit-code plus No tasks substring requirement that tests can verify mechanically. | Rewritten |
| 6 | Precise test seam; matches existing CliRunner plus subprocess patching patterns in the BearClaw CLI tests. | Kept |
| 7 | Precise RED-gate requirement. | Kept |

### Architecture Notes

- Existing root-command exposure is managed from src/bearclaw/cli.py via app.add_typer(...), so AC #1 should pin the public root help surface instead of an internal helper.
- Existing BearClaw CLI tests use CliRunner against bearclaw.cli.app, patch subprocess.run at the command-module seam, and assert stable substrings or Rich table markers rather than full snapshots. See tests/test_cli.py, tests/test_cli_chat.py, and tests/test_cli_knowledge_source.py.
- Parent research in docs/research/bearclaw-board-command.md and the paired GREEN research in docs/research/bearclaw-board-command-implementation-gate.md both establish two non-optional rules: status grouping follows kanban/config.yml order, and age-in-status is derived from the latest move into the current status with created fallback. The RED task must pin those rules or #910 is under-specified.
- Scope stays in one domain: CLI test coverage for the board command. Failure-mode mapping is not needed because this task adds tests, not runtime behavior.

### Changes Made

- Refined the task body AC so status ordering and empty-state behavior are mechanically verifiable.
- Preserved the existing research note and optional helper follow-up reference.

### Dependencies

- Verified: paired GREEN task #910 exists for the implementation half of the feature.
- Verified: optional helper task #923 remains separate and non-blocking.
- No additional dependencies are required for this RED task.

[[2026-03-21]] Sat 18:09

## Test-Writer Notes\n- Test file: tests/test_cli_board.py\n- Classes: TestFromAC_BoardRegistration, TestFromAC_BoardRendering, TestFromAC_AssigneeDisplay, TestFromAC_AgeInStatus, TestFromAC_EmptyBoard\n- Tests per category: happy 13, edge 4, error 0, boundary 6\n- Total: 23 tests, all FAIL (AssertionError / AttributeError: no attribute board)\n- ruff: clean\n- AC coverage:\n  AC#1 -> test_board_in_main_help, test_board_help_exits_zero\n  AC#2 -> test_renders_id/title/assignee/age/tags_column_header, test_renders_status_as_section_header, test_renders_task_title/id/tags, test_status_order_follows_config_yml, test_tasks_appear_under_their_own_status_section\n  AC#3 -> test_assignee_shown_over_claimed_by, test_claimed_by_shown_when_no_assignee, test_dash_shown_when_neither_assignee_nor_claimed_by\n  AC#4 -> test_age_uses_latest_move_into_current_status, test_age_falls_back_to_created_when_no_matching_move, test_age_uses_latest_move_not_earliest, test_age_ignores_moves_to_different_status\n  AC#5 -> test_empty_board_exits_zero, test_empty_board_prints_no_tasks_message, test_empty_board_output_is_not_blank\n  AC#6 -> all tests use CliRunner + mocked subprocess.run only\n  AC#7 -> verified: 23 failed, 0 passed

[[2026-03-21]] Sat 23:26

## Builder Notes\n- Files changed: src/bearclaw/commands/board.py (new), src/bearclaw/cli.py\n- Tests: 23 passed, coverage 96% on commands/board.py, 95% on cli.py\n- Lint: ruff clean\n- Evidence: 23 passed in 2.07s; pre-existing test_cli.py failures confirmed unrelated\n- Fixes applied: None

[[2026-03-21]] Sat 23:53

## Review Evidence

## Review: #909 - Test bearclaw board command rendering and status age (RED)

### Test Results

- Command: uv run pytest tests/test_cli_board.py -q --tb=short
- Result: 23 passed, 2 warnings in 2.12s.
- Warning details: optional dependency skips reported from tests/conftest.py for qdrant_client-only tests; no failures in task scope.

### Lint Results

- Command: uv run ruff check src/ tests/
- Result: 451 lint violations reported across the repository baseline.
- Task-scoped command: uv run ruff check src/bearclaw/commands/board.py src/bearclaw/cli.py tests/test_cli_board.py
- Task-scoped result: All checks passed.

### Coverage

- Command: uv run pytest tests/test_cli_board.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- src/bearclaw/commands/board.py: 96%
- src/bearclaw/cli.py: 95%
- TOTAL project coverage from this scoped run: 18% (expected for bare --cov in this repo; touched modules are above 90%).

### Pass 1 - CRITICAL

#### Security Review

- Hardcoded secrets: none found in src/bearclaw/commands/board.py or src/bearclaw/cli.py.
- Injection: subprocess invocations use fixed argument lists and no user-supplied shell content.
- Path traversal: no user-controlled filesystem path composition.
- Insecure deserialization: uses json.loads plus yaml.safe_load (safe loader), no eval/exec/pickle loads.
- Input validation: task data consumed from kanban JSON output; no external user payload persistence.
- Dependency risk: no new dependencies introduced.
- Secret leakage: no credential/PII logging paths introduced.

#### Test Integrity (TestFromAC comparison)

Evidence used: current tests in tests/test_cli_board.py plus builder commit 45ecfde (files changed: src/bearclaw/commands/board.py, src/bearclaw/cli.py only).

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_BoardRegistration::test_board_in_main_help | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRegistration::test_board_help_exits_zero | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_renders_id_column_header | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_renders_title_column_header | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_renders_assignee_column_header | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_renders_age_column_header | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_renders_tags_column_header | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_renders_status_as_section_header | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_renders_task_title | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_renders_task_id | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_renders_task_tags | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_status_order_follows_config_yml | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_BoardRendering::test_tasks_appear_under_their_own_status_section | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_AssigneeDisplay::test_assignee_shown_over_claimed_by | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_AssigneeDisplay::test_claimed_by_shown_when_no_assignee | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_AssigneeDisplay::test_dash_shown_when_neither_assignee_nor_claimed_by | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_AgeInStatus::test_age_uses_latest_move_into_current_status | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_AgeInStatus::test_age_falls_back_to_created_when_no_matching_move | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_AgeInStatus::test_age_uses_latest_move_not_earliest | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_AgeInStatus::test_age_ignores_moves_to_different_status | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_EmptyBoard::test_empty_board_exits_zero | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_EmptyBoard::test_empty_board_prints_no_tasks_message | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |
| TestFromAC_EmptyBoard::test_empty_board_output_is_not_blank | No change detected in current test file; builder commit did not touch tests/test_cli_board.py | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Assertions target concrete output tokens for columns/sections/assignee/age/no-tasks; not purely truthy checks. |
| Negative/error paths | ADEQUATE | Includes fallback and exclusion cases (no matching move, wrong destination status, empty list) for critical AC behavior. |
| Mutation reasoning | STRONG | Key contract mutations (wrong status order, wrong assignee priority, earliest-vs-latest move, empty-board rendering) are explicitly tested. |
| Test independence | STRONG | Each test patches subprocess.run independently and uses isolated fixture builders. |
| Descriptive names | STRONG | Test names clearly encode scenario and expected behavior across all AC items. |

#### Data Safety

- No LLM output persistence paths changed.
- No multi-step state mutation or transactional writes introduced.
- No shared mutable concurrency path added.
- No unbounded expensive operation introduced beyond listing/log parsing already bounded by kanban output size.

### Pass 2 - INFORMATIONAL

- Global lint baseline is currently noisy (451 repo-wide violations), but task-scoped lint for #909 files is clean.
- Coverage command reports broad-project totals due required bare --cov behavior; touched files for #909 are still >=90%.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Root help lists board | src/bearclaw/cli.py line 56 adds board typer; pytest passed | test_board_in_main_help, test_board_help_exits_zero | PASS |
| 2. Renders grouped status sections in config order with ID/Title/Assignee/Age/Tags headers | src/bearclaw/commands/board.py lines 24, 102, 110, 115, 118-122; kanban/config.yml lines 8-9; pytest passed | test_renders_id_column_header, test_renders_title_column_header, test_renders_assignee_column_header, test_renders_age_column_header, test_renders_tags_column_header, test_status_order_follows_config_yml, test_tasks_appear_under_their_own_status_section | PASS |
| 3. Assignee fallback assignee -> claimed_by -> -- | src/bearclaw/commands/board.py line 58; pytest passed | test_assignee_shown_over_claimed_by, test_claimed_by_shown_when_no_assignee, test_dash_shown_when_neither_assignee_nor_claimed_by | PASS |
| 4. Age uses latest matching move into current status with created fallback | src/bearclaw/commands/board.py lines 68-90; pytest passed | test_age_uses_latest_move_into_current_status, test_age_falls_back_to_created_when_no_matching_move, test_age_uses_latest_move_not_earliest, test_age_ignores_moves_to_different_status | PASS |
| 5. Empty list exits 0 and prints No tasks message | src/bearclaw/commands/board.py line 99; pytest passed | test_empty_board_exits_zero, test_empty_board_prints_no_tasks_message, test_empty_board_output_is_not_blank | PASS |
| 6. Tests use CliRunner + mocked subprocess output only | tests/test_cli_board.py line 24 (CliRunner) and repeated @patch on subprocess.run at lines 121+; no live binary invocation in tests | All board command execution tests in tests/test_cli_board.py | PASS |
| 7. All new tests fail before implementation | Task body Test-Writer Notes records 23 failing tests before implementation; builder commit 45ecfde introduces implementation files only and current run shows 23 passing | TestFromAC_* suite (23 tests) | PASS |

### Verdict: PASS

### Action Taken

- Pending status transition to docs.

[[2026-03-22]] Sun 00:20

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | BearClaw notes describe CLI generically; no behavior or convention change needed |
| 2 | Docstrings | Yes | Pass | All public functions in board.py have accurate docstrings. cli.py module and _RichGroup docstrings intact. |
| 3 | sources/overview.md | Yes | Pass | Already updated by researcher: kanban-md, Rich Tables, Typer Commands, Typer Testing logged under Task #905 section |
| 4 | README.md | Yes | Updated | Added bearclaw board command line to CLI section |
| 5 | Research doc | Yes | Pass | docs/research/bearclaw-board-command.md and docs/research/bearclaw-board-command-red-gate.md both exist

### Files Updated

- README.md (added bearclaw board to CLI command list)

### Scratch Files Cleaned

- docs/scratch/909-researcher.md: deletion blocked by terminal policy; file is ephemeral and gitignored

[[2026-03-22]] Sun 04:36

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Root help lists board | cli.py L18+L56 registers board_app; 2 tests PASS | PASS |
| 2. Rich table grouped by config status order | board.py L94-L130 reads config, groups, renders Rich table with ID/Title/Assignee/Age/Tags | PASS |
| 3. Assignee priority assignee>claimed_by>-- | board.py L58 _assignee_display(); 3 tests PASS | PASS |
| 4. Age from latest matching move with created fallback | board.py L68-90 _age_in_status(); 4 tests PASS | PASS |
| 5. Empty board exits 0 with No tasks | board.py L99  yper.echo; 3 tests PASS | PASS |
| 6. Tests use CliRunner + mocked subprocess only | All tests patch earclaw.commands.board.subprocess.run | PASS |
| 7. All new tests fail before implementation | Test-writer notes: 23 failed; builder commit 45ecfde adds impl only | PASS |

### Test Results

- pytest (scoped): 28 passed in 2.09s (23 original + 5 failure-path from #924)
- pytest (full suite): 3751 passed, 97 failed (all pre-existing: numpy compat, bootstrap unpacking, AgentRegistry signature)
- ruff (scoped): All checks passed

### Architect Quality: 4/5

AC was specific and mechanically verifiable after architect refinement. Two AC lines rewritten for precision (status order, exit code). Clean result.

### Confidence: .97

### Action: archive

[[2026-03-22]] Sun 04:36

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| cce68c6 | docs | README.md | #909 |
