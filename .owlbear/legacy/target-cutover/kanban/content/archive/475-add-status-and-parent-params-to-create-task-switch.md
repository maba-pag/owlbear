---
id: 475
title: Add status and parent params to create_task, switch to JSON output
status: archived
priority: medium
created: 2026-03-31 06:06:12.578276+02:00
updated: 2026-03-31 16:36:30.687084+02:00
started: 2026-03-31 16:36:30.117568+02:00
completed: 2026-03-31 16:36:30.117568+02:00
tags:
- scope:mcp
- ' type:build'
- ' phase-2'
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] `create_task` accepts `status: str = ""` parameter; when non-empty, appends `--status {value}` to args
- [ ] `create_task` accepts `parent: int = 0` parameter; when > 0, appends `--parent {value}` to args
- [ ] `create_task` appends `--json` to args unconditionally
- [ ] `create_task` returns the raw JSON stdout from kanban-md (JSON task object with id, title, status, priority, created, updated, parent, class, file)
- [ ] Unit tests: `--status backlog` in args when status="backlog"; no `--status` when empty; `--parent 42` in args when parent=42; no `--parent` when parent=0; `--json` always present
- [ ] Integration test: create with status override + show roundtrip confirms correct status
- [ ] Integration test: create with parent + show roundtrip confirms parent field
- [ ] skills/mcp-kanban/SKILL.md `create_task` row updated to include `status` and `parent` parameters
- [ ] ruff clean

## Architecture Notes

- File: packages/mcp-kanban/src/owlbear_mcp_kanban/server.py, create_task function (~L148-180)
- Pattern: follow existing optional-param style (priority, tags, body, depends_on, claim guards)
- --json precedent: show_task at L141 already appends --json unconditionally
- parent: int with 0 sentinel matches CLI --parent int
- outputSchema/structuredContent deferred to #495 (KanbanTask model task, separate concern)
- Research doc: docs/research/create-task-status-parent-json.md

[[2026-03-31]] Tue 08:09
## Architecture Review
**Verdict:** APPROVED (after merge+refine)
**DR Verification:** N/A -- T1 autonomous (adding params to existing tool following established patterns, .95 confidence)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| status param | Clear, testable, follows existing pattern | Kept |
| parent param | Clear, testable, int+0 sentinel matches CLI | Kept |
| --json unconditional | Clear, follows show_task precedent | Kept |
| JSON return format | Clear, schema verified in research | Kept |
| Unit tests | Refined: specific cases enumerated | Rewritten |
| Integration tests | Refined: roundtrip scenarios specified | Rewritten |
| SKILL.md update | Clear, testable | Kept |
| ruff clean | Added standard gate | Added |
| outputSchema/structuredContent | Out of scope, depends on #495 | Removed |
| Umbrella note | Pipeline does not support umbrellas | Removed |

### Architecture Notes
Single-file change (~6 LOC) in server.py create_task function. Follows existing optional-param guards (priority, tags, body, depends_on, claim). --json follows show_task precedent at L141. No new dependencies, no layering violations, no security surface. outputSchema deferred to #495 after KanbanTask model lands.

### Changes Made
- Rewrote body with clean, precise AC (removed outputSchema scope creep and umbrella note)
- Removed depends_on #482 (circular self-reference)
- Deleted #482 (redundant subtask, merged into #475)
- Approved to todo

[[2026-03-31]] Tue 11:34
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_create_task_475.py
- Classes: TestFromAC_CreateTaskSignature, TestFromAC_CreateTaskArgs, TestFromAC_CreateTaskReturn, TestFromAC_CreateTaskStatusIntegration, TestFromAC_CreateTaskSkillDoc
- Tests per category: happy 6, edge 3, error 1, boundary 1, integration 4, doc 2
- Total: 17 tests, all FAIL
- ruff: clean
- AC coverage: all 9 AC lines covered (status param, parent param, --json unconditional, raw JSON return, unit flag tests, status integration roundtrip, parent integration roundtrip, SKILL.md status, SKILL.md parent)

[[2026-03-31]] Tue 14:34
## Builder Notes
- Files changed: packages/mcp-kanban/src/owlbear_mcp_kanban/server.py, skills/mcp-kanban/SKILL.md
- Tests: 17 passed (all TestFromAC classes green)
- Lint: ruff clean
- Evidence: 17 FAIL then PASS; commit f0c51f6
- Fixes applied: added status/parent params, --json unconditional, raw JSON return, SKILL.md row updated

[[2026-03-31]] Tue 15:16
## Review Evidence

### Test Results
- pytest: 17 passed, 0 failed (tests/test_mcp_kanban_create_task_475.py)

### Lint Results
- ruff: All checks passed (server.py + test file)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| status: str="" param | inspect.signature confirms default="" -- test_has_status_parameter_with_str_default_empty PASSES | PASS |
| parent: int=0 param | inspect.signature confirms default=0 -- test_has_parent_parameter_with_int_default_zero PASSES | PASS |
| --json unconditional | test_json_flag_always_present_with_title_only + with_all_params PASS | PASS |
| Returns raw JSON stdout | test_returns_raw_json_stdout_on_success: result == _SAMPLE_TASK_JSON exact match | PASS |
| Unit --status backlog | test_status_non_empty_appends_status_flag: call_args[idx+1]=='backlog' exact | PASS |
| Unit no --status when empty | test_status_empty_does_not_append_status_flag PASSES | PASS |
| Unit --parent 42 | test_parent_positive_appends_parent_flag: call_args[idx+1]=='42' exact | PASS |
| Unit no --parent when 0 | test_parent_zero_does_not_append_parent_flag PASSES | PASS |
| Integration status roundtrip | test_status_override_roundtrip: task['status']=='backlog' | PASS |
| Integration parent roundtrip | test_parent_roundtrip: task['parent']==42 | PASS |
| SKILL.md status param | test_skill_md_create_task_row_includes_status PASSES; line 21 confirmed | PASS |
| SKILL.md parent param | test_skill_md_create_task_row_includes_parent PASSES | PASS |
| ruff clean | All checks passed | PASS |

### Security
_run_kanban uses asyncio.create_subprocess_exec (not shell=True) -- no injection risk. CLEAN.

### TestFromAC Comparison
test_mcp_kanban_create_task_475.py not in builder's changed files list. All TestFromAC tests: PRESERVED.

### Test Quality
- Assertion specificity: STRONG (exact positional arg checks, exact string match on return)
- Negative/error paths: STRONG (empty status, zero parent, negative parent, rc!=0)
- Mutation resistance: STRONG

### Builder Process Quality: CLEAN (1 attempt, no retries)

### Verdict: PASS (confidence .97)

[[2026-03-31]] Tue 15:39
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | mcp-kanban section documents server existence only; SKILL.md is canonical for tool params |
| 2 | Docstrings | Yes | Pass | create_task docstring remains accurate; brief style matches show_task and other tools |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used; changes follow internal kanban-md CLI conventions |
| 4 | README.md | No | N/A | No user-facing CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/create-task-status-parent-json.md exists; linked in task body Architecture Notes |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/475-* files found)
