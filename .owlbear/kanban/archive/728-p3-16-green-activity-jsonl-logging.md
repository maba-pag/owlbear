---
id: 728
title: 'P3-16: GREEN — activity.jsonl logging'
status: archived
priority: medium
created: 2026-04-09T03:28:26.0758289+02:00
updated: 2026-04-09T22:27:42.8340411+02:00
started: 2026-04-09T22:27:42.8340411+02:00
completed: 2026-04-09T22:27:42.8340411+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 727
class: standard
---

## Objective
Implement activity.jsonl logging and wire it into CRUD and compound operations.

Brief: see parent #712

## AC
- [ ] `log_activity(action, task_id, detail)` appends JSON line to activity.jsonl
- [ ] Wired into create_task, edit_task, move_task, claim, release, block, unblock, archive operations
- [ ] Log file created on first write if missing
- [ ] All #727 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/activity_log.py` (new)
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (edit — wire activity logging)

[[2026-04-09]] Thu 21:25
## Architecture Review

### Context
GREEN phase — wire `log_activity()` (from `activity_log.py`, created in #727 builder) into KanbanEngine CRUD and compound operations. Parent #712 (archived epic). Dependency #727 (done — 39 tests pass, `activity_log.py` exists with `log_activity(log_path, action, task_id, detail)`).

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `log_activity(action, task_id, detail)` appends JSON line | PASS (function exists from #727 builder) — but AC omits `log_path` param | Refined: updated signature |
| Wired into create_task, edit_task, move_task, claim, release, block, unblock, archive | PASS after refinement — block/unblock are `edit_task(blocked=…)` transitions, not separate methods; archive uses `move` verb | Refined: added detection spec |
| Log file created on first write if missing | PASS — `open("a")` handles this | None |
| All #727 tests pass | PASS — already pass (test standalone function) | None |

### Refined AC

```
- [ ] `log_activity(log_path, action, task_id, detail)` appends JSON line to activity.jsonl (already implemented in #727 builder — verify unchanged)
- [ ] Engine.__init__ stores `self._activity_log_path = kanban_dir / "activity.jsonl"`
- [ ] Wired into engine operations with these verbs and detail patterns:
      - create_task → action="create", detail=title
      - edit_task → action="edit", detail=summary of changed fields
      - move_task (non-archive) → action="move", detail="{old_status} -> {new_status}"
      - move_task (status="archived") → action="move", detail="{old_status} -> archived" (NO archive verb)
      - claim_task → action="claim", detail=agent_name
      - release_task → action="release", detail=agent_name
      - edit_task (blocked False→True) → action="block", detail=block_reason or ""
      - edit_task (blocked True→False) → action="unblock", detail=""
- [ ] Block/unblock detection: read old blocked state before mutation; emit block/unblock INSTEAD of edit when blocked state transitions
- [ ] Log file created on first write if missing
- [ ] All #727 tests pass
```

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Activity logging wiring only |
| Interface clarity | PASS after refinement | Block/unblock detection logic specified; archive verb clarified |
| Dependency correctness | PASS | #727 done. `activity_log.py` exists. `engine.py` is the edit target. |
| Module layering | PASS | `engine.py` imports `activity_log.log_activity` — same package, no upward import |
| TDD compliance | PASS | #727 RED has 39 tests covering `log_activity()` function |
| KISS/YAGNI | PASS | Direct `log_activity()` calls in each method — no observer/hook abstraction |
| Premise challenge | PASS | Activity logging is a core brief requirement; Go binary had it |
| Pattern consistency | PASS | First cross-cutting concern in engine — simple inline calls, no new pattern needed |
| Security surface | PASS | Append-only file write, no user input to path, `json.dumps` injection-safe |
| Single domain | PASS | Kanban engine domain |

### Architecture Notes
1. **Block/unblock detection:** Builder must read `record.blocked` before mutation in `edit_task()`, then compare after to determine which verb to emit: `block` (False→True), `unblock` (True→False), or `edit` (no transition).
2. **Archive vocab:** Per #727 arch review synthesis — archive ops use `action="move"`, NOT `action="archive"`. This is a behavioral contract from the Go binary.
3. **Wiring test coverage:** #727 tests verify `log_activity()` standalone. Wiring verification is the reviewer's responsibility (code inspection that each engine method calls `log_activity()` with correct args). No separate integration test task exists — acceptable for GREEN scope.
4. **`log_path` derivation:** `self._activity_log_path = kanban_dir / "activity.jsonl"` in `__init__`, passed to each `log_activity()` call.

### Challenge Results
- Challenger: RECONSIDER (confidence 0.40) — flagged signature omission, block/unblock detection gap, archive verb clarity, no wiring tests, detail format vagueness
- Architect response: Accepted 3 of 5 concerns. Refined AC with explicit block/unblock detection logic, archive verb clarification, and detail format patterns per verb. Rebutted wiring test concern (reviewer scope, not GREEN AC). Rebutted detail format severity (now specified per verb in refined AC).

### Verdict: APPROVE (with AC refinement)
### Action Taken: Refined AC to specify block/unblock detection logic, archive→move verb mapping, detail format per verb, and correct function signature. Approved to todo.

[[2026-04-09]] Thu 21:45
## Test-Writer Notes
- Test file: tests/test_kanban_engine_activity_wiring_728.py
- Classes: TestFromAC_ActivityLogPath, TestFromAC_CreateTaskLogging, TestFromAC_EditTaskLogging, TestFromAC_MoveTaskLogging, TestFromAC_ClaimTaskLogging, TestFromAC_ReleaseTaskLogging, TestFromAC_BlockUnblockDetection, TestFromAC_LogFileCreation
- Tests per category: happy 18, edge 8, error 0, boundary 11
- Total: 37 tests, all FAIL (AssertionError)
- ruff: clean

AC coverage:
| Refined AC Line | Tests |
|---|---|
| Engine.__init__ stores _activity_log_path | test_engine_has_activity_log_path_attribute, test_activity_log_path_points_to_jsonl_in_kanban_dir |
| create_task → action="create", detail=title | test_create_task_writes_log_entry, test_create_task_log_action_is_create, test_create_task_log_detail_equals_title, test_create_task_log_task_id_matches_record, test_two_creates_append_two_entries |
| edit_task → action="edit", detail=changed fields | test_edit_task_writes_log_entry, test_edit_task_log_action_is_edit, test_edit_task_log_task_id_matches, test_edit_task_log_detail_is_non_empty_string |
| move_task (non-archive) → action="move", detail="{old} -> {new}" | test_move_task_writes_log_entry, test_move_task_log_action_is_move, test_move_task_detail_shows_status_transition, test_move_task_log_task_id_matches |
| move_task (archived) → action="move", detail="{old} -> archived" | test_archive_uses_move_verb_not_archive, test_archive_detail_shows_archived_destination |
| claim_task → action="claim", detail=agent_name | test_claim_task_writes_log_entry, test_claim_task_log_action_is_claim, test_claim_task_log_detail_is_agent_name, test_claim_task_log_task_id_matches |
| release_task → action="release", detail=agent_name | test_release_task_writes_log_entry, test_release_task_log_action_is_release, test_release_task_log_detail_is_agent_name, test_release_task_log_task_id_matches |
| edit_task(blocked F→T) → action="block", detail=reason or "" | test_false_to_true_transition_emits_block, test_block_detail_equals_block_reason, test_block_without_reason_uses_empty_detail, test_block_emits_block_not_edit, test_block_transition_with_simultaneous_field_change_still_emits_block, test_block_log_task_id_matches |
| edit_task(blocked T→F) → action="unblock", detail="" | test_true_to_false_transition_emits_unblock, test_unblock_detail_is_empty_string, test_unblock_emits_unblock_not_edit |
| No transition → emit "edit" | test_no_blocked_transition_emits_edit |
| Log file created on first write if missing | test_log_file_created_by_first_create_task, test_log_file_created_by_first_move_task |

[[2026-04-09]] Thu 21:57
## Builder Notes

### Files changed
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` — wired `log_activity()` into all mutating methods

### Implementation summary
- Added `from owlbear_mcp_kanban.activity_log import log_activity` import
- Added `self._activity_log_path = kanban_dir / "activity.jsonl"` to `__init__`
- `create_task` → `log_activity(..., "create", record.id, record.title)` after write
- `edit_task` → captures `old_blocked` before mutation; emits "block" (F→T), "unblock" (T→F), or "edit" (no transition); detail=block_reason/""/changed-field-names respectively
- `move_task` → captures `old_status` before mutation; emits "move" with `"{old} -> {new}"` detail (archive uses "move" verb per Go binary contract)
- `claim_task` → `log_activity(..., "claim", record.id, self._agent_name)` after write
- `release_task` → `log_activity(..., "release", record.id, self._agent_name)` after write

### Test results
- `test_kanban_engine_activity_wiring_728.py`: 37/37 passed
- Combined engine test suite (6 files): 195/195 passed

### Coverage
- `engine.py`: 96.8% (187/191 statements, 85/90 branches) — 4 uncovered lines pre-existing
- `activity_log.py`: 100%

### Lint
- ruff: clean

### Commit
`7d55f93` — feat: wire activity.jsonl logging into KanbanEngine operations (#728)

[[2026-04-09]] Thu 22:03
## Review Evidence

### Test Results
- pytest (activity scope: 2 files): 76 passed, 0 failed
- pytest (full engine suite: 7 files): 274 passed, 0 failed

### Lint
clean

### Coverage
- `owlbear_mcp_kanban.engine`: 98% (full suite)
- `owlbear_mcp_kanban.activity_log`: 100%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `Engine.__init__` stores `_activity_log_path` | `test_activity_log_path_points_to_jsonl_in_kanban_dir` | Yes — asserts exact path `kanban_dir / "activity.jsonl"` | COVERED |
| `create_task` → action="create", detail=title | `test_create_task_log_action_is_create`, `test_create_task_log_detail_equals_title` | Yes — exact string comparison | COVERED |
| `edit_task` → action="edit", detail=changed fields | `test_edit_task_log_action_is_edit`, `test_edit_task_log_detail_is_non_empty_string` | Yes — action == "edit", detail non-empty | COVERED |
| `move_task` (non-archive) → action="move", detail="{old} -> {new}" | `test_move_task_log_action_is_move`, `test_move_task_detail_shows_status_transition` | Yes — exact format validated | COVERED |
| `move_task` (archive) → action="move", NOT "archive" | `test_archive_uses_move_verb_not_archive` | Yes — asserts action != "archive" and == "move" | COVERED |
| `claim_task` → action="claim", detail=agent_name | `test_claim_task_log_action_is_claim`, `test_claim_task_log_detail_is_agent_name` | Yes — exact values | COVERED |
| `release_task` → action="release", detail=agent_name | `test_release_task_log_action_is_release`, `test_release_task_log_detail_is_agent_name` | Yes — exact values | COVERED |
| `edit_task` (F→T) → action="block", detail=reason or "" | `test_false_to_true_transition_emits_block`, `test_block_detail_equals_block_reason`, `test_block_without_reason_uses_empty_detail` | Yes — transitions tested, exact detail verified | COVERED |
| `edit_task` (T→F) → action="unblock", detail="" | `test_true_to_false_transition_emits_unblock`, `test_unblock_detail_is_empty_string` | Yes — exact empty string assertion | COVERED |
| Block/unblock INSTEAD OF edit | `test_block_emits_block_not_edit`, `test_unblock_emits_unblock_not_edit` | Yes — asserts action != "edit" | COVERED |
| Simultaneous field change with block → block wins | `test_block_transition_with_simultaneous_field_change_still_emits_block` | Yes | COVERED |
| No blocked transition → emit "edit" | `test_no_blocked_transition_emits_edit` | Yes | COVERED |
| Log file created on first write | `test_log_file_created_by_first_create_task`, `test_log_file_created_by_first_move_task` | Yes — file existence asserted | COVERED |
| All #727 tests pass | Full engine suite 274/274 | — | COVERED |

#### Security Review
- No hardcoded secrets. No injection vectors (`json.dumps` safe, `log_path` derived from internal `kanban_dir`, not user input). No path traversal. No insecure deserialization. No credential/PII leakage in log entries (action, task_id, title, agent_name only). No new dependencies.

#### Test Integrity — TestFromAC_ Comparison
All 8 `TestFromAC_*` classes present and unmodified by builder. Activity wiring tests not present in #727 (new file), so no modification risk. None removed, none weakened.

| Class | Tests | Assessment |
|-------|-------|------------|
| TestFromAC_ActivityLogPath | 2 | PRESERVED |
| TestFromAC_CreateTaskLogging | 5 | PRESERVED |
| TestFromAC_EditTaskLogging | 4 | PRESERVED |
| TestFromAC_MoveTaskLogging | 6 | PRESERVED |
| TestFromAC_ClaimTaskLogging | 4 | PRESERVED |
| TestFromAC_ReleaseTaskLogging | 4 | PRESERVED |
| TestFromAC_BlockUnblockDetection | 10 | PRESERVED |
| TestFromAC_LogFileCreation | 2 | PRESERVED |

#### Test Quality
- **Assertion specificity**: STRONG — all assertions use exact string/value comparisons (`action == "create"`, `detail == "research -> todo"`, `task_id == record.id`, `len(entries) == 1`)
- **Negative/error-path**: ADEQUATE — `test_block_emits_block_not_edit`, `test_archive_uses_move_verb_not_archive` guard against incorrect verbs; no error paths exist in this append-only wiring
- **Mutation resistance**: STRONG — flipping "block" to "edit" verb fails `test_block_emits_block_not_edit`; swapping action to "archive" fails `test_archive_uses_move_verb_not_archive`; detail format tested exactly
- **Test independence**: STRONG — each test uses fresh tmp_path fixture
- **Naming**: STRONG — all names are descriptive and precise

#### Data Safety
No issues. Append-only file, no shared mutable state, no LLM output persisted.

#### Implementation-Aware Test Gap Analysis
All significant branches in the new wiring code covered: `old_blocked != record.blocked` condition (both sides tested), `"a"` mode creates file on first write (tested), simultaneous block+field-change (tested), no-transition path (tested).

#### Builder Process Quality
Single `## Builder Notes` section. No retries. CLEAN.

### AC Compliance Table
| Refined AC Line | Evidence | Status |
|---------|----------|--------|
| `Engine.__init__` stores `_activity_log_path` | engine.py:57 | PASS |
| `create_task` → action="create", detail=title | engine.py:223 | PASS |
| `edit_task` → action="edit", detail=changed fields | engine.py:328 | PASS |
| `move_task` → action="move", detail="{old} -> {new}" | engine.py:365 | PASS |
| Archive uses "move" not "archive" | engine.py:365 | PASS |
| `claim_task` → action="claim", detail=agent_name | engine.py:405 | PASS |
| `release_task` → action="release", detail=agent_name | engine.py:429 | PASS |
| `edit_task` (F→T) → action="block" | engine.py:315-317 | PASS |
| `edit_task` (T→F) → action="unblock" | engine.py:318-319 | PASS |
| `old_blocked` captured before mutation | engine.py:273 | PASS |
| Block/unblock INSTEAD-OF edit | engine.py:315-319 | PASS |
| Log file created on first write | activity_log.py:18 (open "a") | PASS |
| `activity_log.py` signature unchanged from #727 | activity_log.py:13 | PASS |
| All #727 tests pass | 274/274 pass (full suite) | PASS |

### Deductions
None.

### Verdict
confidence: .97 → PASS #728 -> docs

[[2026-04-09]] Thu 22:07
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` covers project topology only; no public API signatures changed |
| 2 | Module docstrings | Yes | Updated | `KanbanEngine` class docstring updated to document `activity.jsonl` side effect on all mutating operations. `activity_log.py` module/function docstrings verified accurate. All other method docstrings (`create_task`, `edit_task`, `move_task`, `claim_task`, `release_task`) verified accurate against implementation. |
| 3 | External attribution | No | N/A | "Go binary contract" is internal project history, not an external source |
| 4 | CLI changes | No | N/A | No CLI entry points modified |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc for this task; arch review is inline in task body |

### Files Updated
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` — added activity.jsonl side-effect note to `KanbanEngine` class docstring

### Commit
`b72707a` — docs: update KanbanEngine docstring for activity.jsonl side effect (#728, doc-writer)

### Scratch Files
None found matching `728-*`.

[[2026-04-09]] Thu 22:27
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `log_activity(log_path, action, task_id, detail)` appends JSON line | activity_log.py:13-29 — unchanged from #727 | PASS |
| Wired into create, edit, move, claim, release, block, unblock | engine.py — 7 call sites at L229, L323, L325, L334, L371, L411, L435 | PASS |
| Engine.__init__ stores `_activity_log_path` | engine.py:57 | PASS |
| Block/unblock detection (INSTEAD-OF edit) | engine.py:275 old_blocked captured; L322-325 conditional emit | PASS |
| Log file created on first write | activity_log.py:28 open("a") | PASS |
| All #727 tests pass | 76/76 passed (both activity files) | PASS |

### Test Results
- pytest (task scope): 76 passed, 0 failed
- pytest (full suite): 3109 passed, 130 failed — all failures in unrelated files (orchestrator_loop, planner_gates, analysis, knowledge_foundation, lint_guard, scaffold)
- ruff: clean

### Architect Quality: 4/5
AC was adequate. Missed `log_path` param and block/unblock detection initially, but architect caught and refined before builder started.

### Deduction Breakdown
- AC lines without evidence: 0 (-.00)
- Lint violations: 0 (-.00)
- AC quality ≤ 3: no (-.00)
- Missing reviewer evidence: no (-.00)
- Full-suite failures in task scope: 0 (-.00)

### Confidence: 1.00
### Action: archive

### Commits Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 1a6d986 | test | test_kanban_engine_activity_wiring_728.py | #728 |
| 7d55f93 | feat | engine.py | #728 |
| b72707a | docs | engine.py | #728 |
