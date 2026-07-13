---
id: 727
title: 'P3-15: RED — activity.jsonl logging'
status: archived
priority: medium
created: 2026-04-09T03:27:45.3139969+02:00
updated: 2026-04-09T21:36:42.9077916+02:00
started: 2026-04-09T21:36:42.9077916+02:00
completed: 2026-04-09T21:36:42.9077916+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 722
class: standard
---

## Objective
Write failing tests for append-only activity.jsonl logging.

Brief: see parent #712 — action vocabulary: create, edit, move, claim, release, block, unblock, archive

## AC
- [ ] Test log entry format: {"timestamp":"<ISO>","action":"<verb>","task_id":<int>,"detail":"<string>"}
- [ ] Test each action verb produces correct log entry
- [ ] Test append-only semantics (new entries appended, existing entries untouched)
- [ ] Test log file created if missing
- [ ] All tests fail

## Files
- `tests/test_kanban_engine_activity.py` (new)

[[2026-04-09]] Thu 20:39
## Architecture Review

### Context
RED phase task — write failing tests for `log_activity()` in `owlbear_mcp_kanban.activity_log` (module does not exist yet). Parent #712 (archived epic). Dependency #722 (done — CRUD operations). GREEN counterpart #728. Import: `from owlbear_mcp_kanban.activity_log import log_activity  # type: ignore[import-not-found]`.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Test log entry format: `{"timestamp":"<ISO>","action":"<verb>","task_id":<int>,"detail":"<string>"}` | PASS — exact JSON schema | None |
| Test each action verb produces correct log entry | PASS after refinement — see vocabulary resolution below | Refined: explicit verb list |
| Test append-only semantics (new entries appended, existing untouched) | PASS — clear behavioral contract | None |
| Test log file created if missing | PASS — clear | None |
| All tests fail | PASS — standard RED gate | None |

### Vocabulary Resolution (AC2 refinement)

The task objective lists 8 verbs: create, edit, move, claim, release, block, unblock, archive. However, the brief's synthesis (`.owlbear/briefs/draft-kanban-native/synthesis.md` L27) and the Data Person's corrected position (after critic-challenge debate) explicitly state: **no `archive` action verb — archive operations log as `move` with detail `"<status> -> archived"`.** Per D4 ("replace only"), the native engine matches Go binary behavior.

**Authoritative verb list for RED tests (7 verbs):** `create`, `edit`, `move`, `claim`, `release`, `block`, `unblock`.

Test-writer: test `log_activity(log_path, verb, task_id, detail)` for each of these 7 verbs. Do NOT test an `archive` verb — #728 (GREEN) will wire archive operations to log as `action="move"`.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for activity.jsonl logging only |
| Interface clarity | PASS | Log format specified exactly; verbs now explicit |
| Dependency correctness | PASS | #722 (done) provides engine infrastructure for fixtures. `activity_log.py` intentionally absent — ImportError is valid RED failure. |
| Module layering | PASS | Test in `tests/`, module in `serve/mcp-kanban/src/owlbear_mcp_kanban/` |
| TDD compliance | PASS | This IS the RED phase; GREEN is #728 |
| KISS/YAGNI | PASS | 5 AC items, minimal scope |
| Premise challenge | PASS | Activity logging is a core brief requirement |
| Pattern consistency | PASS | Follows established TestFromAC_ pattern, `type: ignore[import-not-found]`, `_BASE_CONFIG_YAML` fixture from test_kanban_engine_crud.py and siblings |
| Security surface | PASS | Test file only, no system boundaries |
| Single domain | PASS | Kanban engine domain |

### Architecture Notes
1. **Import path:** `from owlbear_mcp_kanban.activity_log import log_activity` — module created in #728 GREEN at `serve/mcp-kanban/src/owlbear_mcp_kanban/activity_log.py`.
2. **Function signature:** `log_activity(log_path: Path, action: str, task_id: int, detail: str)` — function needs a file path parameter (GREEN #728 will wire `kanban_dir / "activity.jsonl"`). Test-writer should use `tmp_path / "activity.jsonl"` in fixtures.
3. **Detail field:** Freeform text per brief. Tests should pass representative strings; exact detail semantics per verb are a #728 wiring concern.
4. **Vocab note for #728 architect:** The GREEN task #728 AC says "Wired into...archive operations" — when reviewing #728, ensure the `move_task("archived")` codepath logs with `action="move"` and `detail="<status> -> archived"`, not `action="archive"`.

### Challenge Results
- Challenger: reconsider (confidence 0.55) — vocabulary conflict, AC2 vagueness, detail field underspecified
- Architect response: Accepted vocabulary concern. Refined AC2 with explicit 7-verb list, resolving the brief vs. synthesis conflict in favor of the synthesis (deliberated outcome). Rebutted other concerns: detail field is intentionally freeform per brief (tests pass representative strings); dependency #722 is correctly done (activity_log.py absence is expected RED state); retro workflow compatibility is a #728 concern.

### Verdict: APPROVE (with AC2 refinement)
### Action Taken: Resolved action vocabulary conflict per brief synthesis — 7 verbs (no `archive`). Approved to todo. Test-writer: follow vocabulary resolution above.

[[2026-04-09]] Thu 20:50
## Test-Writer Notes
- Test file: tests/test_kanban_engine_activity.py
- Classes: TestFromAC_LogEntryFormat, TestFromAC_ActionVerbs, TestFromAC_AppendOnlySemantics, TestFromAC_LogFileMissing, TestFromAC_BoundaryConditions
- Tests per category: happy 21, edge 6, error 0, boundary 4 (+7 parametrized verb checks within AC2 class)
- Total: 39 test instances (7 from @pytest.mark.parametrize across 7 authorised verbs), all FAIL via ImportError at collection — `owlbear_mcp_kanban.activity_log` module does not exist
- ruff: clean

### AC coverage

| AC Line | Class | Tests |
|---------|-------|-------|
| Log entry format: exact {timestamp, action, task_id, detail} JSON schema | TestFromAC_LogEntryFormat | 11 |
| Each action verb (create, edit, move, claim, release, block, unblock) produces correct log entry | TestFromAC_ActionVerbs | 14 (7 parametrized + 7 named) |
| Append-only semantics — new entries appended, existing untouched | TestFromAC_AppendOnlySemantics | 6 |
| Log file created if missing | TestFromAC_LogFileMissing | 4 |
| All tests fail | Verified — 1 collection ERROR (ImportError), 0 tests collected | — |

### Vocab note for #728 (GREEN)
Arch review resolved: no `archive` verb. Archive ops must log `action="move"` with `detail="<status> -> archived"`. Verify this in the GREEN codepath.

Commit: 92341cd - "test: add failing tests for activity.jsonl logging (#727, test-writer)"

[[2026-04-09]] Thu 21:10
## Builder Notes

### Files Changed
- `serve/mcp-kanban/src/owlbear_mcp_kanban/activity_log.py` (new — 28 lines)

### Implementation
`log_activity(log_path, action, task_id, detail)` — appends one JSONL entry per call. Uses `open("a")` (creates if missing, never truncates). Entry format: `{"timestamp":"<ISO+TZ>","action":"<verb>","task_id":<int>,"detail":"<str>"}`. Timestamp: `datetime.now(tz=UTC).isoformat()` (Python 3.12, ISO 8601 parseable).

### Test Results
- RED verified: 0 collected (ImportError) before implementation
- GREEN: **39 passed, 0 failed** (test_kanban_engine_activity.py)

### Coverage
- `activity_log.py`: **100%** (8 statements, 0 missed)

### Lint
- ruff: **clean** (0 violations — TC003 fixed via TYPE_CHECKING guard, UP017 fixed via `datetime.UTC`)

### Builder-Discovered Tests
None — TestFromAC_* classes covered all edge cases (empty detail, large task_id, JSON special chars, task_id=0).

### Evidence
RED: `No module named 'owlbear_mcp_kanban.activity_log'` — 1 collection error  
GREEN: 39 passed, ruff clean, 100% coverage on target module

[[2026-04-09]] Thu 21:13
## Review Evidence

### Test Results (independent run)
pytest: **39 passed, 0 failed, 0 skipped** — exit code 0
Scope: `tests/test_kanban_engine_activity.py`

### Lint
ruff: **clean** (0 violations) — `activity_log.py` + `test_kanban_engine_activity.py`

### Coverage
`owlbear_mcp_kanban.activity_log`: **100%** (8 statements, 0 missed)

### Changed Files
Builder changed exactly one file: `serve/mcp-kanban/src/owlbear_mcp_kanban/activity_log.py` (new, 28 lines). No TestFromAC_* modifications detected — test file committed in prior test-writer commit (`92341cd`), no diff against test file in current changeset.

---

### AC Compliance Table

| AC Line | Mapped Tests | Would Fail If Violated? | Status |
|---------|-------------|------------------------|--------|
| Log entry format: `{timestamp, action, task_id, detail}` JSON schema | `TestFromAC_LogEntryFormat` (11 tests) — `set(entry.keys()) == {"timestamp","action","task_id","detail"}`, type checks, exact value checks | Yes — exact key-set assertion catches missing/extra keys; type/value assertions catch field-level violations | COVERED |
| Each action verb produces correct log entry (7 verbs: create, edit, move, claim, release, block, unblock) | `TestFromAC_ActionVerbs` (14 tests) — 7 parametrized `entry["action"] == verb` + 7 named with action + task_id checks | Yes — parametrized test per verb, exact equality | COVERED |
| Append-only semantics — new entries appended, existing untouched | `TestFromAC_AppendOnlySemantics` (6 tests) — count checks, insertion order, identity of first entry after second write, 10-call sequence | Yes — count + positional content checks catch truncation | COVERED |
| Log file created if missing | `TestFromAC_LogFileMissing` (4 tests) — existence check before/after, 1-line count after first write, all-verbs create-file loop, existing-file-not-truncated | Yes — `assert not log_path.exists()` then `assert log_path.exists()` | COVERED |
| All tests fail (RED gate) | Test-writer confirmed: 1 collection error (ImportError), 0 collected — valid RED state | Builder report + pattern confirm RED was established before GREEN implementation | COVERED |

### TestFromAC Modification Check
No TestFromAC_* changes by builder. Builder only added `activity_log.py`. Test classes TestFromAC_LogEntryFormat, TestFromAC_ActionVerbs, TestFromAC_AppendOnlySemantics, TestFromAC_LogFileMissing, TestFromAC_BoundaryConditions: all preserved and unmodified. Assertion strength is unchanged.

### Assertion Quality Assessment
- `test_entry_has_exactly_four_keys`: `set(entry.keys()) == {"timestamp","action","task_id","detail"}` — catches both extra and missing keys. Strong.
- `test_entry_timestamp_is_iso_parseable`: `datetime.fromisoformat()` must not raise — truly discriminating (would catch non-ISO timestamps).
- `test_entries_in_insertion_order` + `test_first_entry_untouched_after_second_append`: check actual `entry["detail"]` content — catches truncation and overwrite bugs.
- All parametrized verb tests use `assert entry["action"] == verb` — would fail on a stored-wrong-verb implementation.

No weak assertions found.

### Security Review
- `json.dumps()` serializes `action`, `task_id`, `detail` — injection-safe.
- `log_path.open("a", encoding="utf-8")` — append-only, no truncation. No shell, no SQL, no eval.
- `TYPE_CHECKING` guard on `Path` import — correct Python practice, no runtime concern.
- `datetime.UTC` (UP017 compliant) — no timezone pitfalls.

### Deductions
None.

**Confidence: 1.00 − 0.00 = 1.00 → PASS**

---

### Verdict
PASS #727 -> docs | confidence 1.00

[[2026-04-09]] Thu 21:16
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.github/copilot-instructions.md` has only project-identity and branch sections — no tech stack or module-API table. New `activity_log.py` module does not require a copilot-instructions update. |
| 2 | Module docstrings | Yes | Verified | `activity_log.py` — accurate module docstring present; `log_activity()` has complete docstring with entry-format schema. No changes needed. |
| 3 | External attribution | No | N/A | Only stdlib used (`json`, `datetime`, `pathlib`). No external patterns. |
| 4 | CLI changes | No | N/A | No CLI changes. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc produced for this task. |

### Files Updated
None — docstrings already accurate; no other docs impact.

### Scratch Files
None found — no `.owlbear/scratch/727-*` files exist.

### Verdict
Docs gate passed. No impact items requiring update.

[[2026-04-09]] Thu 21:36
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test log entry format: exact JSON schema | TestFromAC_LogEntryFormat (11 tests) — `set(entry.keys()) == {"timestamp","action","task_id","detail"}`, type/value checks | PASS |
| Each action verb produces correct log entry (7 verbs) | TestFromAC_ActionVerbs (14 tests) — 7 parametrized + 7 named, exact verb equality | PASS |
| Append-only semantics | TestFromAC_AppendOnlySemantics (6 tests) — insertion order, untouched first entry, 10-call sequence | PASS |
| Log file created if missing | TestFromAC_LogFileMissing (4 tests) — existence before/after, per-verb creation, no truncation | PASS |
| All tests fail (RED gate) | Test-writer confirmed: 1 collection error (ImportError), 0 collected. Builder then passed 39/39 | PASS |

### Test Results
- pytest: 3,073 passed, 129 failed, 1 error, 18 skipped — **0 failures in task scope** (test_kanban_engine_activity.py: 39/39 passed). Pre-existing failures: missing lint-changed.ps1 (~23), qdrant-client (~2), various analysis/kanban/orchestrator mismatches.
- ruff: clean (0 violations)

### Architect Quality: 4/5
AC was specific with exact JSON schema. Minor gap: AC2 said "each action verb" without enumerating — architect review resolved this with explicit 7-verb vocabulary from the brief synthesis. Good upstream quality.

### Deduction Breakdown
- AC lines without evidence: 0 (−.00)
- Lint violations: 0 (−.00)
- AC quality ≤ 3: no (4/5) (−.00)
- Missing reviewer section: no — thorough, confidence 1.00 (−.00)
- Full-suite failures in task scope: 0 (−.00)
- Note: builder did not commit `activity_log.py` (untracked `??`). Committed as orphaned deliverable in auditor step.

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 92341cd | test | tests/test_kanban_engine_activity.py | #727 |
| 04ca90b | feat | activity_log.py, 727 task, activity.jsonl | #727 |
