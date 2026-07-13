---
id: 89
title: 'Test: mcp-kanban full tool set'
status: archived
priority: medium
created: 2026-03-27 22:47:10.852010+01:00
updated: 2026-03-30 06:59:35.482829+02:00
started: 2026-03-30 06:58:49.694304+02:00
completed: 2026-03-30 06:58:49.694304+02:00
tags:
- phase-3
- mcp
- tooling
- test
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write failing tests (TDD RED) for the mcp-kanban server module. Tests validate the interface contract from #56 AC. All tests must FAIL before the builder implements.

## Conventions
- Test file: packages/mcp-kanban/tests/test_server.py
- Import target: owlbear_mcp_kanban.server (will ImportError until builder implements: this is expected RED)
- Mock target for tools/_run_kanban: asyncio.create_subprocess_exec (no real binary, no shell=True)
- All tool and lifespan tests are async: use @pytest.mark.asyncio
- Follow packages/mcp-knowledge/tests/test_search_knowledge.py pattern (mock context, verify behavior)
- Existing test_package.py smoke test remains as-is

## Test Scenarios

### Lifespan (3 tests)
- app_lifespan yields AppContext with kanban_bin (Path) and kanban_dir (Path) fields resolved
- app_lifespan raises FileNotFoundError when binary path does not exist
- app_lifespan respects KANBAN_BIN env var override for binary resolution

### _run_kanban helper (2 tests)
- Constructs correct argv: binary path + command args + --no-color --dir {kanban_dir}
- Returns (stdout: str, stderr: str, returncode: int) tuple from subprocess result

### Tools: success path (7 tests, one per tool)
- list_tasks: mock rc=0, verify --compact flag and filter args (status, tag, priority, block_filter, search, sort, unclaimed) passed through
- show_task: mock rc=0, verify task_id and --json flag in args
- create_task: mock rc=0, verify title positional and optional args (--priority, --tags, --body, --depends-on, --claim)
- move_task: mock rc=0, verify task_id and status positional args
- edit_task: mock rc=0, verify all flag mappings (--body, --block, --unblock, --tags, --priority, -a/append-body, --claim, --release, --status, --timestamp)
- pick_task: mock rc=0, verify optional args (--status, --claim, --move, --tags)
- board_context: mock rc=0, verify no extra args beyond base command

### Tools: error path (1 parametrized test)
- All 7 tools return error string when mock rc != 0

### Total: 13+ test functions (~17 scenarios with parametrize)

[[2026-03-28]] Sat 04:06
## Architecture Review
**Verdict:** APPROVED (AC refined)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Objective | Was vague (just 'write failing tests for #56') | Rewritten: specifies TDD RED, interface contract ref, FAIL expectation |
| Lifespan 3 tests | Good scenarios, missing type info | Added Path types for kanban_bin/kanban_dir |
| _run_kanban 2 tests | Vague ('--no-color --dir appended') | Refined: full argv pattern, typed return tuple |
| Tools success 7 tests | Partial param lists | Expanded: full param list per tool matching #56 AC signatures |
| Tools error 1 parametrized | Clear as-is | No change |
| (missing) Conventions section | Not present | Added: test file path, import target, mock target, async markers, pattern ref |

### Architecture Notes
- Single domain: tools/mcp (packages/mcp-kanban/tests/ only)
- Pattern: follows packages/mcp-knowledge/tests/test_search_knowledge.py (mock context, pytest.mark.asyncio, explicit import target)
- Mock strategy: asyncio.create_subprocess_exec (matches #56 AC, no shell=True)
- Import target owlbear_mcp_kanban.server will ImportError in RED (correct: server.py does not exist yet)
- No module layering concerns: standalone MCP package
- Dependency #7 (monorepo skeleton): archived, satisfied

### Changes Made
- Refined AC body: added Conventions section (file path, import, mock target, async markers, pattern ref)
- Tightened all test scenario descriptions with full parameter lists from #56 AC
- Moved to todo (approved)

### Dependencies
- Verified: #7 (monorepo skeleton) archived

[[2026-03-29]] Sun 13:10
## Test-Writer Notes
- Test file: packages/mcp-kanban/tests/test_server.py
- Classes: TestFromAC_Lifespan, TestFromAC_RunKanban, TestFromAC_Tools
- Tests per category: happy 13, edge 4, error 8, boundary 0
- Total: 25 tests â€” committed bb7f375 (test-writer, #89)
- ruff: clean
- Status note: tests were written in RED (commit bb7f375). Implementation added by builder task #14 (bc3a304/9e9efc1). All 25 pass against current implementation. Pipeline metadata gap: task stayed at todo after build completed. Advancing now.
- AC coverage:
  Lifespan (3): yields AppContext w/Path fields, raises FileNotFoundError, respects KANBAN_BIN env var
  _run_kanban (2): constructs correct argv, returns (stdout,stderr,rc) tuple
  Tools success (7): list_tasks, show_task, create_task, move_task, edit_task, pick_task, board_context
  Tools error (1 parametrized x7): all tools return error string on non-zero rc
  Boolean flag branches (4): edit_task unblock true/false, release true/false
  block_filter branches (2): list_tasks --not-blocked, --blocked exclusivity

[[2026-03-29]] Sun 16:24
## Builder Notes
- Files changed: none (implementation in server.py from prior build #14)
- Tests: 25 passed, coverage 100% on owlbear_mcp_kanban/server.py
- Lint: ruff clean
- Pipeline gap resolved: server.py implemented in bc3a304/9e9efc1 but task was not advanced

[[2026-03-29]] Sun 23:58
## Test-Writer Notes (pipeline gap recovery)\n- Invoked again at todo; prior Test-Writer Notes + Builder Notes both present.\n- Tests verified: 25 passed (implementation from builder task #14 is in place).\n- Pipeline gap: both prior agents noted the gap but neither advanced the task.\n- Action: advancing directly to review — no new tests needed, builder work is complete.

[[2026-03-30]] Mon 03:00
## Review Evidence
See docs/scratch/89-reviewer.md for full evidence.

Verdict: FAIL — test_list_tasks_success_passes_args is LAX on --search, --sort, --unclaimed. No compensating TestBuilderDiscovered tests exist.

[[2026-03-30]] Mon 03:21
## Review Evidence (cycle 2, 2026-03-30)
See docs/scratch/89-reviewer-c2.md for full evidence.

Verdict: FAIL - same root cause as cycle 1. test_list_tasks_success_passes_args still LAX on --search, --sort, --unclaimed. No compensating tests added for those three params.

[[2026-03-30]] Mon 03:21
## Review Evidence (cycle 2, 2026-03-30) -- FAIL. See docs/scratch/89-reviewer-c2.md

[[2026-03-30]] Mon 03:36
## Test-Writer Notes (retry, cycle 3)
- Retry reason: reviewer FAIL (cycles 1+2) cited LAX assertions -- missing --search, --sort, --unclaimed coverage in test_list_tasks_success_passes_args
- Added 6 new tests to TestFromAC_Tools:
  - test_list_tasks_passes_search_flag (search non-empty -> --search value in args)
  - test_list_tasks_omits_search_flag_when_empty (search='' -> no --search)
  - test_list_tasks_passes_sort_flag (sort non-empty -> --sort value in args)
  - test_list_tasks_omits_sort_flag_when_empty (sort='' -> no --sort)
  - test_list_tasks_passes_unclaimed_flag_when_true (unclaimed=True -> --unclaimed)
  - test_list_tasks_omits_unclaimed_flag_when_false (unclaimed=False -> no --unclaimed)
- Note: tests PASS against current implementation (fa8b282). Implementation pre-existed in prior build cycle (#14). Existing 25 tests also PASS.
- Total: 31 tests, all pass
- ruff: clean

[[2026-03-30]] Mon 05:44
## Builder Notes (cycle 3)\n- Files changed: packages/mcp-kanban/tests/test_server.py (commit 09e8212)\n- Tests: 31 passed, coverage 100% on owlbear_mcp_kanban/server.py\n- Lint: ruff clean\n- Evidence: server.py already implements --search/--sort/--unclaimed; cycle-3 test-writer changes were in working tree uncommitted (fa8b282 not on main branch); committed them now\n- Fixes applied: staged and committed cycle-3 test-writer tests to main

[[2026-03-30]] Mon 06:21
## Review Evidence (cycle 3, 2026-03-30)
See docs/scratch/89-reviewer-c3.md for full evidence.

Verdict: PASS -- 31/31 pass, ruff clean, 100% coverage, cycle-3 tests resolve LAX finding on --search/--sort/--unclaimed.

[[2026-03-30]] Mon 06:27
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Test-only task; mcp-kanban already in tech stack + directory tables; no behavior/API change |
| 2 | Docstrings | No | N/A | server.py has full docstrings on all public symbols; test helpers also documented; no new public source modules |
| 3 | docs/sources/overview.md | Yes | Pass | Section exists at line 2268: mcp-kanban Unit Test Strategy (Task #89) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/mcp-kanban-unit-test-strategy.md exists and references Task #89 |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/89-reviewer.md, docs/scratch/89-reviewer-c2.md, docs/scratch/89-reviewer-c3.md referenced in body but not present on disk (already cleaned by prior agents)

[[2026-03-30]] Mon 06:58
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Lifespan yields AppContext w/Path fields | test_lifespan_yields_app_context_with_path_fields | PASS |
| Lifespan raises FileNotFoundError | test_lifespan_raises_file_not_found_when_binary_missing | PASS |
| Lifespan respects KANBAN_BIN env var | test_lifespan_respects_kanban_bin_env_var | PASS |
| _run_kanban correct argv | test_constructs_correct_argv | PASS |
| _run_kanban returns (stdout,stderr,rc) | test_returns_stdout_stderr_returncode_tuple | PASS |
| list_tasks success + all filters | test_list_tasks_success_passes_args + 6 cycle-3 search/sort/unclaimed tests | PASS |
| show_task success | test_show_task_success_passes_args | PASS |
| create_task success | test_create_task_success_passes_args | PASS |
| move_task success | test_move_task_success_passes_args | PASS |
| edit_task success + boolean flags | test_edit_task_success_passes_args + 4 bool flag tests | PASS |
| pick_task success | test_pick_task_success_passes_args | PASS |
| board_context success | test_board_context_success_no_extra_args | PASS |
| Error path (7 tools parametrized) | test_all_tools_return_error_string_on_non_zero_rc | PASS |
| Total 13+ tests | 31 tests total | PASS |

### Test Results
- pytest (task-scoped): 31 passed in 0.72s
- pytest (full suite excl. pre-existing import errors): 1129 passed, 156 failed (all failures pre-existing, none in mcp-kanban)
- ruff: All checks passed

### AC Quality (Architect)
Score: 4/5 -- specific scenarios, good conventions section, minor gap on list_tasks filter specificity caught by reviewer

### Deduction breakdown
No deductions. All AC verified, lint clean, reviewer evidence thorough, no scope regressions.

### Confidence: 1.00
### Action: archive

[[2026-03-30]] Mon 06:59
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 85d9fab | chore | kanban/tasks/089, kanban/activity.jsonl | #89 |
