---
id: 1467
title: 'E2a-B2: Merge cockpit_decisions_api task tests into durable'
status: archived
priority: medium
created: 2026-05-09T07:21:35.670259+00:00
updated: 2026-05-09T16:07:37.695620+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
- quality
parent: 1415
depends_on:
- 1466
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Research: `.owlbear/research/1463-python-root-test-cleanup.md` §5b
Supersedes: #1463 (partial)

## Scope

Merge 6 task-scoped files (72 tests) into existing `test_cockpit_decisions_api.py` (10 tests), then delete sources.

### Source files

| File | Tests |
|------|:-----:|
| test_cockpit_decisions_api_1189.py | 8 |
| test_cockpit_decisions_api_1190.py | 26 |
| test_cockpit_decisions_api_1194.py | 3 |
| test_cockpit_decisions_api_1345.py | 5 |
| test_cockpit_decisions_api_1384.py | 23 |
| test_cockpit_decisions_api_1385.py | 7 |

**Target:** `test_cockpit_decisions_api.py` (existing durable, 10 tests pre-merge)

### Two fixture/helper patterns

**Pattern A** (target, 1189, 1190, 1194, 1345): `decisions_dir` is a standalone directory. `engine(tmp_path)` creates a board without decisions dirs. `client(engine, decisions_dir)` overrides both `get_engine` and `get_decisions_dir`. Helpers: `_make_board(base_dir)`, `_write_pending_dr(decisions_dir, ...)`, `_parse_frontmatter`, `_find_dr_file`. All identical across these files — deduplicate to target's version.

**Pattern B** (1384, 1385): decisions live inside `board_dir/decisions/`. `_make_board(board_dir)` also creates decisions subdirs. `_write_pending_dr(board_dir, ...)` writes to `board_dir/decisions/pending/`. `client(engine)` overrides only `get_engine` (no `decisions_dir`). Unique helpers: `_write_resolved_dr`, `_create_blocked_task`, `_read_task_body`, `_is_task_blocked`.

## AC

- [ ] All unique `def test_*` from 6 source files present in `test_cockpit_decisions_api.py` (td:0)
- [ ] 3 test name collisions resolved by appending source task ID: `test_pending_empty_returns_zero_and_empty_items_1189`, `test_resolve_returns_404_for_unknown_decision_id_1189`, `test_resolve_rejects_invalid_response_enum_1189` (td:0)
- [ ] Two fixture patterns coexist without name collision: (a) target's Pattern A fixtures remain as module-level defaults; (b) 1384/1385's Pattern B fixtures renamed or class-scoped to avoid shadowing (td:0)
- [ ] Pattern B's unique helpers (`_write_resolved_dr`, `_create_blocked_task`, `_read_task_body`, `_is_task_blocked`) and its different `_make_board`/`_write_pending_dr` signatures added with distinct names (td:0)
- [ ] Pattern A helpers from source files dropped (identical to target's existing versions) (td:0)
- [ ] All 6 source files deleted after merge (td:0)
- [ ] Per-target checkpoint: `uv run pytest tests/test_cockpit_decisions_api.py --collect-only -q` collects ≥ 82 items (td:0)
- [ ] Post-cleanup failure count ≤ pre-task baseline failure count (capture baseline with `uv run pytest tests/ -q` before any changes) (td:0)
- [ ] Full suite: `uv run pytest tests/ --collect-only -q` count does not decrease vs pre-task baseline (td:0)
- [ ] `test_kanban_topology_1439.py` untouched (td:0)

## Out of scope

- Other merge targets (mutation_api, mcp_kanban, read_api, pipeline_diagram)
- Renames — handled in #1466

## Architecture Review

### Verdict: APPROVE

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| All unique tests present | Clear, verifiable mechanically | None |
| 3 collision renames | Identified exact 3 collisions from codebase; source-ID suffix for traceability | Rewrote from generic `_1467` to specific `_1189` |
| Two fixture patterns | Codebase confirms structural difference (separate decisions_dir vs board-integrated) | Added Pattern A/B documentation and merge guidance |
| Pattern B unique helpers | Identified 4 unique helpers + 2 with different signatures | Added specific helper inventory |
| Pattern A dedup | Verified all 5 Pattern A files share identical helpers with target | Simplified to "drop source copies" |
| 6 source files deleted | Clear | None |
| Collect ≥ 82 | 10 target + 72 source = 82 unique methods; parametrize may yield more collected items | Kept as lower bound |
| Delta failure count | Replaces brittle `pytest -x` per AC Correction | Integrated |
| Suite count stable | Clear | None |
| topology_1439 untouched | Guard rail | None |

### Architecture Notes

- **Dependency #1466** (E2a-B1: renames + safe ops) is archived/done — prerequisite satisfied.
- **Single responsibility:** PASS — one concern (merge decisions_api task tests into durable).
- **Module layering:** N/A — test files only, no production code changes.
- **KISS/YAGNI:** PASS — mechanical merge, no new abstractions.
- **Pattern consistency:** PASS — follows existing durable test conventions.
- **Test depth:** All td:0 — mechanical merge requires no new tests.

### Challenge Results

- Challenger: SKIPPED — all AC lines td:0 (mechanical merge, no architectural decisions)

### Test-writer: SKIP
[[2026-05-09]]
APPROVED #1467 → todo. Refined AC: identified exact 3 test name collisions (all between target and 1189), documented two structurally different fixture/helper patterns (Pattern A: separate decisions_dir, Pattern B: board-integrated decisions), specified collision rename convention (source task ID suffix), replaced brittle `pytest -x` gates with delta-based verification, added helper inventory for Pattern B's unique utilities. All AC td:0 — Test-writer: SKIP. Challenger: SKIPPED (all td:0).
[[2026-05-09]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Implementation: merged all unique `test_*` cases from six task-scoped decisions API files into durable `tests/test_cockpit_decisions_api.py`; added Pattern B helpers/fixtures with distinct `_pattern_b` names so Pattern A defaults remain unshadowed.
- Collision handling: renamed the 3 required collisions to `test_pending_empty_returns_zero_and_empty_items_1189`, `test_resolve_returns_404_for_unknown_decision_id_1189`, and `test_resolve_rejects_invalid_response_enum_1189`.
- Helper handling: Pattern A duplicate helpers from source files were not reintroduced; Pattern B unique helpers were added as distinct names: `_write_resolved_dr_pattern_b`, `_create_blocked_task_pattern_b`, `_read_task_body_pattern_b`, `_is_task_blocked_pattern_b`, plus Pattern B board/write helpers.
- Source cleanup: deleted `tests/test_cockpit_decisions_api_1189.py`, `tests/test_cockpit_decisions_api_1190.py`, `tests/test_cockpit_decisions_api_1194.py`, `tests/test_cockpit_decisions_api_1345.py`, `tests/test_cockpit_decisions_api_1384.py`, `tests/test_cockpit_decisions_api_1385.py`.
- Commit: `cef978f4` (`test: merge durable decisions API suite (#1467, builder)`).

- Baseline (pre-change): `uv run pytest tests/ -q --tb=short` => 3156 passed, 214 failed, 5 errors; `uv run pytest tests/ --collect-only -q` => 3379 collected.
- Checkpoint (target collect-only): `uv run pytest tests/test_cockpit_decisions_api.py --collect-only -q` => 88 collected (>= 82 AC gate).
- Post-cleanup: `uv run pytest tests/ -q --tb=short` => 3162 passed, 208 failed, 5 errors (failure count not increased vs baseline).
- Post-cleanup collect-only: `uv run pytest tests/ --collect-only -q` => 3379 collected (not decreased vs baseline).
- Quality-runner (scoped): 88 passed, 0 failed; ruff clean; coverage modules included `owlbear_cockpit.routes.decisions` at 96%.

- Guardrail check: `tests/test_kanban_topology_1439.py` untouched.
[[2026-05-09]]
## Review Evidence
### Scope
- First review cycle: no prior `## Review Evidence` section found in `.owlbear/kanban/tasks/1467-e2a-b2-merge-cockpit-decisions-api-task-tests-into-durable.md`.
- Builder commit presence confirmed in `.git/logs/HEAD:2469` and `.git/logs/refs/heads/dev:2279` for `cef978f43f4713bbea1cea5f5c182bb7604e7941`.
- Review scope reconstructed as `tests/test_cockpit_decisions_api.py` plus deletion of `tests/test_cockpit_decisions_api_1189.py`, `tests/test_cockpit_decisions_api_1190.py`, `tests/test_cockpit_decisions_api_1194.py`, `tests/test_cockpit_decisions_api_1345.py`, `tests/test_cockpit_decisions_api_1384.py`, and `tests/test_cockpit_decisions_api_1385.py` from task lines 107-117. Explore subagent found no uncommitted overlap with that scope.
- Builder process quality: one `## Builder Notes` section, no loop pattern.

### Test Results
- Quality-runner scoped pass on `tests/test_cockpit_decisions_api.py`: 88 passed, 0 failed, 0 skipped.
- Full root `tests/` check at current HEAD: 3379 collected; 3153 passed, 217 failed, 5 errors, 4 skipped.
- `get_errors` on `tests/test_cockpit_decisions_api.py`: no diagnostics.

### Lint Results
- Quality-runner: ruff clean for `tests/test_cockpit_decisions_api.py`.

### Coverage
- Quality-runner: `owlbear_cockpit.routes.decisions` at 96% statement coverage (102 stmts, 4 missing). Informational only for this td:0 mechanical merge.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| All unique `def test_*` from 6 source files present in `test_cockpit_decisions_api.py` | `grep "def test_"` found exactly 82 test definitions in `tests/test_cockpit_decisions_api.py`; Explore completeness check matched the six deleted source suites into the durable file; promotion markers present at `tests/test_cockpit_decisions_api.py:3`, `:514`, `:592`, `:1284`, `:1373`, `:1459`, `:1507`, `:1577`, `:1630`, `:1651`, `:1661`, `:1675`, `:1695`. | PASS |
| 3 collision renames resolved with source task ID suffix | Original durable names remain at `tests/test_cockpit_decisions_api.py:363`, `:482`, `:501`; merged collision variants exist at `:581`, `:657`, `:667` with `_1189` suffix exactly as required. | PASS |
| Two fixture patterns coexist without name collision | Pattern A module-level fixtures remain at `tests/test_cockpit_decisions_api.py:190`, `:199`, `:205`; Pattern B fixtures are distinct at `:225`, `:233`, `:241`. | PASS |
| Pattern B unique helpers and distinct `_make_board` / `_write_pending_dr` signatures added | Pattern B helpers present at `tests/test_cockpit_decisions_api.py:129`, `:139`, `:164`, `:254`, `:262`, `:268`. | PASS |
| Pattern A helpers from source files dropped | Only one Pattern A helper set is present: `_make_board` `:25`, `_write_pending_dr` `:43`, `_parse_frontmatter` `:67`, `_find_dr_file` `:78`; no duplicate Pattern A helper surface found. | PASS |
| All 6 source files deleted after merge | `file_search` for `tests/test_cockpit_decisions_api_*.py` returned no matches; task body lines 107-117 list the six deleted source files. | PASS |
| Per-target checkpoint collects ≥ 82 items | Scoped quality-runner executed 88 tests from `tests/test_cockpit_decisions_api.py`, clearing the `>= 82` gate. | PASS |
| Post-cleanup failure count ≤ pre-task baseline failure count | Task body records baseline `214 failed` at line 114 and post-cleanup `208 failed` at line 116. Reviewer broad rerun at current HEAD produced a different total (`217 failed`), but current workspace also contains unrelated dirty root-test changes outside #1467 scope, so the live broad count is not attributable to this task. No task-scoped regression signal found. | PASS |
| Full suite collect-only count does not decrease vs pre-task baseline | Reviewer broad rerun collected `3379` tests, matching the task body baseline/post-cleanup counts at lines 114 and 117. | PASS |
| `test_kanban_topology_1439.py` untouched | `tests/test_kanban_topology_1439.py` exists in HEAD; Explore diff reconstruction found no overlap with commit `cef978f4` and no current overlap with #1467 scope. | PASS |

### Deductions
- `-0.04` Direct pre/post commit diff for `cef978f4` was not available through reviewer tools, so `TestFromAC_*` immutability is verified from current file shape and scope reconstruction rather than a precise commit diff.
- `-0.03` Current broad root-suite failure totals are noisy because unrelated dirty root tests exist outside #1467 scope; broad rerun used as context, not as sole gating evidence.

### Verdict
- PASS
- Confidence: 0.91
- Action: advance to `docs`.

### Summary
Task #1467 satisfies the mechanical merge contract. The durable suite now contains the full 82-test surface with the exact three required `_1189` renames, distinct Pattern B helpers/fixtures, deleted source-file cleanup, clean scoped execution/lint, and stable root-suite collection count.
[[2026-05-09]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Test-only task; no behavior, API, CLI, config, or package structure changed. No IN-scope prose docs reference test internals. |
| 2 | Module docstrings | No | N/A | No production Python modules created or modified — only test files. |
| 3 | External attribution | No | N/A | Mechanical merge of existing tests; no external patterns, repos, or articles used. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1463-python-root-test-cleanup.md` exists on disk and is linked in task body (§5b). |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index contains no `describes` glob matching `tests/test_cockpit_decisions_api*.py`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | 6 deleted files are test files; no IN-scope descriptive doc references any of them. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| tests/test_cockpit_decisions_api.py | OUT | Test file — no doc edit |
| tests/test_cockpit_decisions_api_1189.py (deleted) | OUT | Test file — no IN-scope doc references it |
| tests/test_cockpit_decisions_api_1190.py (deleted) | OUT | Test file — no IN-scope doc references it |
| tests/test_cockpit_decisions_api_1194.py (deleted) | OUT | Test file — no IN-scope doc references it |
| tests/test_cockpit_decisions_api_1345.py (deleted) | OUT | Test file — no IN-scope doc references it |
| tests/test_cockpit_decisions_api_1384.py (deleted) | OUT | Test file — no IN-scope doc references it |
| tests/test_cockpit_decisions_api_1385.py (deleted) | OUT | Test file — no IN-scope doc references it |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1467-*` files found)
[[2026-05-09]]
## Audit
### Regression Detection
- quality-runner mode full: 4891 passed, 267 failed, 11 errors, 4 skipped
- All failures pre-existing (engine accessor migration, memory model, PDS build compat, role gating); zero failures in test_cockpit_decisions_api.py (88/88 pass per reviewer scoped run)
- Lint: 12 violations, all outside task scope (serve/knowledge, serve/tools)
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (commit cef978f4 touches exactly 7 files: 1 merged target + 6 deleted sources, all in tests/ domain)
- purpose match: PASS (mechanical merge of task-scoped test files into durable, matching stated purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC lines are specific and mechanically verifiable: exact collision names with _1189 suffix, two fixture patterns (A/B) documented with structural rationale, numeric gates (82 items, baseline delta), explicit guardrail (topology file). Minor improvement possible on "coexist without name collision" specificity but overall clear.

### Commit Integrity
- upstream commit presence: PASS (cef978f4 "test: merge durable decisions API suite (#1467, builder)" confirmed via git log)
- kanban commit packaging: pending (will commit after archival)

### Deduction Breakdown
No deductions applied:
- No regression failures attributable to task
- No intent mismatch
- No lint violations in task scope
- AC quality 4/5 (above 3 threshold)
- Review evidence section present and thorough (0.91 confidence, 10 AC lines verified with line numbers)
- Commit integrity clean

### Confidence: 1.00
### Action: archive