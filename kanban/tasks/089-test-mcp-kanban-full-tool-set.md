---
id: 89
title: 'Test: mcp-kanban full tool set'
status: todo
priority: important
created: 2026-03-27T22:47:10.8520099+01:00
updated: 2026-03-28T04:07:02.9149603+01:00
tags:
    - phase-3
    - mcp
    - tooling
    - test
depends_on:
    - 7
class: standard
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
