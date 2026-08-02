---
id: 479
title: 'GREEN: implement modernized list_tasks (archived, limit, reverse, blocked
  tri-state, lean JSON)'
status: archived
priority: medium
created: 2026-03-31 06:13:51.254161+02:00
updated: 2026-04-01 03:03:08.403964+02:00
started: 2026-04-01 03:03:03.587195+02:00
completed: 2026-04-01 03:03:03.587195+02:00
tags:
- scope:mcp
- ' type:build'
- ' phase-2'
depends_on:
- 478
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Add archived: bool = False parameter; when True pass --archived
- [ ] Add limit: int = 0 parameter; when >0 pass --limit N
- [ ] Add reverse: bool = False parameter; when True pass --reverse
- [ ] Replace block_filter: str with blocked: bool | None = None; True=--blocked, False=--not-blocked, None=no flag
- [ ] Switch output from --compact to --json
- [ ] Parse JSON output, strip body/file/created/updated fields from each task, re-serialize
- [ ] All RED tests from #478 pass (GREEN phase)
- [ ] Update skills/mcp-kanban/SKILL.md parameter table for list_tasks

## Design Notes

Lean JSON: json.loads() on kanban-md output, list comprehension to strip fields, json.dumps() back. ~5 LOC change in list_tasks function.

Breaking change: block_filter -> blocked. Acceptable per project principles (no backwards compat).

See docs/research/modernize-list-tasks.md for full analysis.

[[2026-03-31]] Tue 22:15
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** N/A -- T1 Autonomous (research doc: docs/research/modernize-list-tasks.md, .90 confidence)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add archived: bool = False; when True pass --archived | Precise, verifiable | Keep |
| Add limit: int = 0; when >0 pass --limit N | Precise, verifiable | Keep |
| Add reverse: bool = False; when True pass --reverse | Precise, verifiable | Keep |
| Replace block_filter with blocked: bool or None = None tri-state | Precise, verifiable, types clear | Keep |
| Switch output from --compact to --json | Precise, verifiable | Keep |
| Parse JSON output, strip body/file/created/updated, re-serialize | Precise, verifiable, fields enumerated | Keep |
| All RED tests from #478 pass (GREEN phase) | Precise, verifiable (26 tests in test_mcp_kanban_list_tasks_472.py) | Keep |
| Update skills/mcp-kanban/SKILL.md parameter table | Precise, verifiable | Keep |

### Architecture Notes
**Implementation already complete.** #478's builder implemented all production code changes (server.py: parameters, --json flag, lean JSON strip, output_schema; SKILL.md updated by writer). All 26 tests pass. The builder on #479 should verify tests pass rather than re-implement.

Pattern: follows existing @mcp.tool pattern in server.py. Lean JSON strip uses dict comprehension with _strip set -- consistent with codebase style.

Module layering: changes stay within packages/mcp-kanban/. No cross-package imports.

Security: No new system boundaries. Parameters go to kanban-md subprocess via _run_kanban helper. JSON parse has try/except fallback.

### Changes Made
- Verified #478 dependency: archived (complete)
- Verified all 8 AC lines are precise and verifiable
- Created follow-up task for quality gaps (stale test_server.py _FAKE_STDOUT test, output_schema spec)
- Moved to todo

### Dependencies
- Verified: #478 (RED tests) -- archived, 26 tests passing

### Challenge Results
- Challenger: reconsider
- Confidence in original: .55
- Key challenges: (C1) GREEN code already implemented in RED task #478 -- pipeline no-op; (C2) stale _FAKE_STDOUT test in test_server.py now exercises error fallback; (C3) output_schema monkey-patch uses private FastMCP internals
- Architect response: C1 acknowledged -- noted for builder to verify rather than re-implement. C2/C3 are pre-existing quality gaps outside #479 scope -- created follow-up task. Approve stands: AC is architecturally sound, verifiable, and correctly scoped.

[[2026-04-01]] Wed 00:12
## Test-Writer Notes
- Pass-through: this is a GREEN phase task where implementation was completed in #478 (builder phase of the RED task).
- Evidence: uv run python -m pytest tests/test_mcp_kanban_list_tasks_472.py -- 26 passed in 0.85s
- All 8 AC lines verified complete (archived, limit, reverse, blocked tri-state, --json, lean JSON strip, 26 RED tests pass, SKILL.md updated).
- Writing new failing tests is not possible -- every contract-level test for this AC passes against the current implementation.
- Passing through to builder for final verification (run tests/test_mcp_kanban_list_tasks_472.py).

[[2026-04-01]] Wed 00:58
## Builder Notes\n- Pass-through: implementation completed in #478 (RED phase builder)\n- Tests: 26 passed (tests/test_mcp_kanban_list_tasks_472.py)\n- Lint: ruff clean on packages/mcp-kanban/\n- No code changes made -- all AC satisfied by #478 implementation\n- Files changed: none

[[2026-04-01]] Wed 01:50
## Review Evidence
### Test Results
- pytest: 26 passed, 0 failed (tests/test_mcp_kanban_list_tasks_472.py)
- Evidence: uv run pytest tests/test_mcp_kanban_list_tasks_472.py -q --tb=short → 26 passed in 0.86s

### Lint Results
- ruff: All checks passed! (packages/mcp-kanban/, tests/test_mcp_kanban_list_tasks_472.py)

### Coverage
- owlbear_mcp_kanban/server.py: 28% overall (expected — only list_tasks exercised by these tests; all AC-specific code paths covered)
- __init__.py: 100%, models.py: 100%

### Pass 1 — CRITICAL

#### Builder Process Quality
- 1 Builder Notes section, no retries → CLEAN

#### Test-Writer AC Coverage
All 8 AC lines have TestFromAC_* coverage. Assessment: COVERED across all items.
- archived param + flag: TestFromAC_ListTasksSignature::test_has_archived_parameter_with_bool_default_false, TestFromAC_ListTasksCliFlags::test_archived_true/false → checks default=False AND flag presence/absence
- limit param + flag: test_has_limit_parameter_with_int_default_zero, test_limit_positive/zero/one → checks value and boundary
- reverse param + flag: test_has_reverse_parameter_with_bool_default_false, test_reverse_true/false → COVERED
- blocked tri-state: test_has_blocked_parameter_with_none_default, test_block_filter_param_no_longer_exists, test_blocked_true/false/none → COVERED
- --json not --compact: test_uses_json_flag_not_compact → asserts both flags
- lean JSON strip: test_stripped_fields_absent + test_lean_json_retains all expected fields + test_lean_json_strips_exactly_four_fields → mutation-resistant (both absence AND presence AND exact count)
- 26 RED tests pass: 26 passed confirmed
- SKILL.md param table: skills/mcp-kanban/SKILL.md shows list_tasks with archived/limit/reverse/blocked in Key parameters column

#### Security Review
- No hardcoded secrets or credentials
- JSON parsing uses json.loads() (safe, not eval/pickle)
- No path traversal in list_tasks
- No new dependencies added
- No secret leakage in error strings
- Status: No security issues found

#### TestFromAC Integrity (builder made no file changes)
- Git log confirms test file last modified in #478 (commit 5103ff0)
- Builder notes: "Files changed: none"
- No TestFromAC modification possible → all tests PRESERVED

#### Test Quality
- Assertion specificity: STRONG — checks exact param defaults, exact flag values (args[limit_idx + 1] == "5"), exact field count (test_lean_json_strips_exactly_four_fields)
- Negative/error paths: ADEQUATE — flag-omission tests (archived=False, blocked=None) covered; missing: rc!=0 error path and JSONDecodeError fallback in list_tasks are untested. Neither produces silent wrong results (both produce obvious output), so not CRITICAL.
- Mutation reasoning: STRONG — TestFromAC_ListTasksLeanJsonPresence added specifically to defeat the [{} for task in tasks] mutation by asserting presence of lean fields
- Test independence: STRONG — all tests use independent mock patches (_patch_run)
- Descriptive names: STRONG — names describe exact scenario and expectation

#### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| archived: bool=False param | server.py archived: bool = False; test_has_archived_parameter_with_bool_default_false PASS | PASS |
| archived=True → --archived | server.py if archived: args.append("--archived"); test_archived_true_passes_archived_flag PASS | PASS |
| limit: int=0 param | server.py limit: int = 0; test_has_limit_parameter_with_int_default_zero PASS | PASS |
| limit>0 → --limit N | server.py if limit > 0: args += ["--limit", str(limit)]; test_limit_positive_passes_limit_flag_and_value PASS | PASS |
| reverse: bool=False param + --reverse | server.py reverse: bool = False + if reverse: args.append("--reverse"); tests PASS | PASS |
| blocked tri-state → --blocked/--not-blocked/nothing | server.py lines 179-182 tri-state; 5 tests PASS | PASS |
| --json not --compact | server.py args: list[str] = ["list", "--json"]; test_uses_json_flag_not_compact PASS | PASS |
| lean JSON strip body/file/created/updated | server.py _strip set + dict comprehension; presence+absence+count tests PASS | PASS |
| 26 RED tests from #478 pass | 26 passed in 0.86s | PASS |
| SKILL.md param table updated | skills/mcp-kanban/SKILL.md: archived/limit/reverse/blocked in list_tasks row | PASS |

### Pass 2 — INFORMATIONAL
- Untested error paths in list_tasks: rc!=0 return and JSONDecodeError fallback. Neither produces silent regressions (obvious error output). Pre-existing from #478. Separate follow-up warranted.
- server.py overall coverage 28% due to other tools untested in this scoped run — out of scope per review suppression rule (code not touched by this task).

### Verdict: PASS
Confidence: .92

[[2026-04-01]] Wed 01:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change -> .github/copilot-instructions.md | No | N/A | copilot-instructions.md covers mcp-kanban at package-level only; parameters not listed there |
| 2 | Module added/changed -> docstrings | Yes | Pass | list_tasks docstring: 'List kanban tasks with optional filters. Returns lean JSON array.' -- accurate, matches single-line convention used by all tools |
| 3 | External inspiration -> docs/sources/overview.md | No | N/A | Sources in research doc (#472) were local binary and standard Python/FastMCP; no novel external pattern adopted in implementation |
| 4 | CLI commands changed -> README.md | No | N/A | MCP tool change only, no CLI surface change |
| 5 | Research doc produced -> archived/linked | Yes | Pass | docs/research/modernize-list-tasks.md exists; task body links it; follow-up tasks #478 (RED) and #479 (GREEN) created |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/479-* files found)

[[2026-04-01]] Wed 03:02
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| archived: bool=False, --archived | server.py L153,L175; test_has_archived_parameter PASS | PASS |
| limit: int=0, --limit N | server.py L154,L177; test_has_limit_parameter PASS | PASS |
| reverse: bool=False, --reverse | server.py L155,L179; test_has_reverse_parameter PASS | PASS |
| blocked tri-state | server.py L156,L181-183; 5 tri-state tests PASS | PASS |
| --json not --compact | server.py L160; test_uses_json_flag_not_compact PASS | PASS |
| lean JSON strip | server.py L187-189 _strip set; presence+absence+count tests PASS | PASS |
| 26 RED tests pass | 26 passed in 0.97s | PASS |
| SKILL.md param table | archived/limit/reverse/blocked in list_tasks row | PASS |

### Test Results
- pytest (task scope): 26 passed, 0 failed
- pytest (mcp-kanban scope): 122 passed, 0 failed
- pytest (full suite): 274 failed, all outside task scope (voice, knowledge, rename, quality-runner, hooks, infra)
- ruff: All checks passed (packages/mcp-kanban/ + test file)

### Architect Quality
- AC specificity: all 8 lines precise and verifiable
- Edge cases: boundary tests for limit=0/1, blocked=None/True/False
- Design direction: correctly noted #478 implemented code, guided builder to verify
- AC quality score: 5/5

### Deduction breakdown: none (all AC verified with evidence, lint clean, AC quality 5, reviewer evidence thorough)
### Confidence: 1.0
### Action: archive
