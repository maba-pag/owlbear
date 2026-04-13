---
id: 811
title: Tests — actor field in activity log
status: done
priority: needed
created: '2026-04-10T21:21:41.924380+00:00'
updated: '2026-04-12T08:34:52.996278+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify new JSONL entries include `"actor"` field
- Tests verify old entries without `actor` load without error (backward compat)
- Tests verify default actor is `"engine"` when not specified
- Tests verify actor field appears in all action types (create, edit, move, claim, release)
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/811-actor-field-activity-log-tests.md
- Sources: 8 studied, 6 high-relevance (4 codebase, 2 external)
- Recommendation: New test file `test_actor_field_activity_log_811.py` with 4 test classes covering all 5 AC items (confidence: .90)
- Follow-up tasks created: none needed — #812 (GREEN pair) already exists
- Decision requests: none — T1 autonomous (additive field, no arch change)

## Challenge Results
- Challenger: FALLBACK — researcher mode, challenger subagent not available
- Confidence in original: .90
- Key challenges: none raised
- Researcher response: N/A

## Key Findings
1. `log_activity()` currently writes 4-field JSONL (timestamp, action, task_id, detail) — no actor field
2. 11,789 existing entries in live activity.jsonl — all without actor; backward compat is essential
3. No structured reader in `activity_log.py`; consumers (tests via json.loads, w-retro via ConvertFrom-Json) tolerate extra/missing fields
4. Brief synthesis, architect, data, and security voices all agree on `log_activity(actor="engine")` approach
5. Prior art confirms the pattern: PocketPaw uses channel/session_id fields, tundere-ledger uses actor_name parameter
6. Test structure follows existing patterns from test_kanban_engine_activity.py (#727) and test_kanban_engine_activity_wiring_728.py (#728)
7. RED gate assured: tests will call `log_activity()` with `actor` kwarg or assert `"actor" in entry` — both fail against current code
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | RED tests only for actor field — one concern |
| Interface clarity | PASS (with note) | AC lines precise; line 4 parenthetical lists 5 of 7 action types — see builder guidance |
| Dependency correctness | PASS | No deps listed, none needed. #812 correctly depends on #811 |
| Module layering | PASS | Tests import from owlbear_kanban.activity_log and owlbear_kanban.KanbanEngine — matches existing patterns |
| TDD compliance | PASS | This IS the RED task; #812 is the GREEN pair |
| KISS/YAGNI | PASS | Minimal test scope matching feature |
| Premise challenge | PASS | Actor field needed for web GUI prep (brief context) |
| Pattern consistency | PASS | Follows TestFromAC_* class pattern from #727/#728 test files |
| Security surface | PASS | No new system boundaries — test-only task |
| Single domain | PASS | scope:mcp-kanban only |

### Builder Guidance — AC Line 4 Clarification

AC line 4 says "all action types (create, edit, move, claim, release)" but engine.py has **7** call sites to `log_activity()`:

1. create (engine.py:285)
2. block (engine.py:380)
3. unblock (engine.py:382)
4. edit (engine.py:391)
5. move (engine.py:429)
6. claim (engine.py:470)
7. release (engine.py:495)

Existing tests from #727 (test_kanban_engine_activity.py) parametrize all 7 verbs. The test-writer MUST cover all 7 action types including block and unblock, not just the 5 in the parenthetical. The AC wording "all action types" is technically correct — the parenthetical is non-exhaustive.

### Challenge Results

- Challenger: FALLBACK — challenger agent not available
- Architect response: proceeded with approval; AC is substantively sound

### Verdict: APPROVE
### Action Taken: Advanced #811 backlog → todo. Builder guidance added for complete action type coverage (7 verbs, not 5).
[[2026-04-12]]
## Test-Writer Notes

- **Test file:** `tests/test_actor_field_activity_log_811.py`
- **Commit:** `b6d70782`

### Test classes and counts

| Class | Category | Tests |
|-------|----------|-------|
| `TestFromAC_ActorFieldPresent` | Happy / Edge | 5 |
| `TestFromAC_BackwardCompat` | Edge / Boundary | 4 |
| `TestFromAC_DefaultActorEngine` | Happy / Boundary | 5 + 7 parametrized = 12 |
| `TestFromAC_ActorInAllActionTypes` | Happy / Integration | 7 + 7 parametrized + 7 engine = 21 |
| **Total** | | **41** |

### Fail verification

`pytest tests/test_actor_field_activity_log_811.py`: **41 failed, 0 passed** ✓

Failure modes:
1. `TypeError: log_activity() got an unexpected keyword argument 'actor'` — majority (tests passing `actor=` kwarg)
2. `KeyError: 'actor'` / `AssertionError` — AC3 default-actor tests (call without kwarg, assert `entry["actor"] == "engine"`)

### AC coverage

| AC | Tests |
|----|-------|
| AC1: new entries include "actor" field | `TestFromAC_ActorFieldPresent` (5 tests) |
| AC2: old entries without actor load without error | `TestFromAC_BackwardCompat` (4 tests) |
| AC3: default actor is "engine" when not specified | `TestFromAC_DefaultActorEngine` (12 tests inc. 7-verb parametrize) |
| AC4: actor in all 7 action types | `TestFromAC_ActorInAllActionTypes` (21 tests: 14 unit + 7 engine integration) |
| AC5: tests fail RED | Verified — 41/41 FAIL |

Note for builder (#812): all 7 engine call sites covered (create, edit, move, claim, release, block, unblock). AC line 4 parenthetical lists 5 — tests cover all 7 per arch review guidance.
[[2026-04-12]]
## Builder Notes

**Files changed (3):**
- `serve/kanban/src/owlbear_kanban/activity_log.py` — added `actor: str = "engine"` keyword param; included in JSONL entry (5 fields now)
- `serve/kanban/src/owlbear_kanban/engine.py` — updated all 7 call sites (create, block, unblock, edit, move, claim, release) to pass `actor=self._agent_name`
- `tests/test_kanban_engine_activity.py` — updated `test_entry_has_exactly_four_keys` → `test_entry_has_exactly_five_keys` to match new schema

**Test results:** 99 passed (41 from #811 + 19 from #812 + 39 from existing activity tests), 0 failed
**Coverage:** `activity_log.py` 100%, `engine.py` 50% (limited by targeted test scope)
**Lint:** ruff clean — two E501 violations fixed (split long log_activity calls)

**#812 bonus:** All 19 RED tests from #812 also pass GREEN — feature complete, #812 can be advanced.
[[2026-04-12]]
## Review Evidence

### Test Results
- pytest: **80 passed, 0 failed** (41 × test_actor_field_activity_log_811.py + 39 × test_kanban_engine_activity.py)
- Quality-runner required one retry (first run: transient venv/pluggy bytecode error); second run clean.

### Lint: clean (ruff exit 0, 0 violations)

### Coverage
- `owlbear_kanban.activity_log`: **100%** ✅
- `owlbear_kanban.engine`: **49%** ⚠️ (see Pass 2)

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: new entries include "actor" field | `TestFromAC_ActorFieldPresent` (5 tests) — `assert "actor" in entry`, `assert entry["actor"] == "builder"`, set superset check | Yes — KeyError or assertion failure | COVERED |
| AC2: old entries without actor load without error | `TestFromAC_BackwardCompat` (4 tests) — explicit old-format JSON injected, `assert "actor" not in entries[0]`, `.get("actor")` safe access | Yes — exception on missing key would fail | COVERED |
| AC3: default actor is "engine" | `TestFromAC_DefaultActorEngine` (12 tests — 5 direct + 7-verb parametrize) — `assert entry["actor"] == "engine"` exact string | Yes — fails if default is None, "user", or absent | COVERED |
| AC4: actor in all 7 action types | `TestFromAC_ActorInAllActionTypes` (21 tests — 14 unit + 7 engine integration) — each verb has dedicated integration test asserting `entry["actor"] == "test-agent"` | Yes — per-verb filtered search would fail on missing actor | COVERED |
| AC5: tests fail RED | Test-writer notes: 41/41 FAIL confirmed pre-implementation | N/A (verified historical) | COVERED |

#### Security Review
- Hardcoded secrets: none
- Injection: `json.dumps()` in activity_log.py:30 auto-escapes all special chars — safe
- Path traversal: actor is JSONL data, not used in path construction — N/A
- Input validation: `actor` accepts any string (no length/char limits); acceptable for internal engine logging; `_agent_name` sourced from constructor or controlled ADJECTIVES/NOUNS pool
- No new dependencies

No issues.

#### Test Integrity — TestFromAC_* Modifications
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_LogEntryFormat::test_entry_has_exactly_four_keys` (test_kanban_engine_activity.py) | Renamed to `test_entry_has_exactly_five_keys`; assertion updated from `{"timestamp","action","task_id","detail"}` to same set + `"actor"` | PRESERVED — strict `set(entry.keys()) ==` equality maintained; schema evolution intentional; docstring updated to match |

No WEAKENED or REMOVED tests.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact equality (`== "engine"`, `== "builder"`), set equality, isinstance, len — no lazy `assert result` |
| Negative/error-path coverage | ADEQUATE | AC2 backward compat covers missing-field path; no negative actor-value paths needed (internal logging) |
| Manual mutation resistance | STRONG | Flipping default to `"user"` → 12 AC3 tests fail; removing actor from entry → 5 AC1 + 21 AC4 tests fail |
| Test independence | STRONG | Each test uses `tmp_path` fixture; `_reset_log()` helper clears state between sub-ops |
| Descriptive names | STRONG | All names describe exact behavior (e.g., `test_default_actor_is_engine_when_kwarg_omitted`) |

#### Data Safety
- No LLM output persistence, no shared mutable state, no unbounded input to resource operations.
No issues.

#### Implementation-Aware Gaps (engine.py)
All 7 `log_activity()` call sites verified by code-reader:
- create (295), edit (410-412), block (399), unblock (401), move (451-453), claim (495), release (520)
- Every site passes `actor=self._agent_name` ✅
- Each has a dedicated integration test in `TestFromAC_ActorInAllActionTypes` ✅

No significant untested paths for the changed code.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL

- **engine.py coverage 49%** (below 90% threshold): Expected for a targeted actor-field test task. The 49% gap is entirely pre-existing, unmodified engine.py code paths (task lifecycle methods, validation, config). All 7 specifically modified call sites are exercised by integration tests. No action needed.

---

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: new entries include "actor" field | activity_log.py:25 `"actor": actor` in entry dict; test_811.py:103-108 | `TestFromAC_ActorFieldPresent::test_actor_field_present_in_new_entry` | PASS |
| AC2: old entries load without error | test_811.py:155-168 injects 4-field JSON, parses without exception | `TestFromAC_BackwardCompat::test_old_and_new_entries_coexist_in_same_log` | PASS |
| AC3: default actor is "engine" | activity_log.py:14 `actor: str = "engine"`; test_811.py:233-240 `assert entry["actor"] == "engine"` | `TestFromAC_DefaultActorEngine::test_default_actor_is_engine_when_kwarg_omitted` | PASS |
| AC4: actor in all 7 action types | engine.py:295,399,401,410,451,495,520 — all pass `actor=self._agent_name`; test_811.py:320-403 — 7 dedicated integration tests | `TestFromAC_ActorInAllActionTypes::test_engine_{verb}_logs_actor` × 7 | PASS |
| AC5: tests fail RED | Test-writer notes: 41/41 FAIL on pre-implementation commit b6d70782 | All TestFromAC_* classes | PASS |

### Deductions
- engine.py overall coverage 49%: –0.02 (informational; changed paths fully covered)
- quality-runner venv retry: –0.01 (environmental, not code)

### Confidence: .97
### Verdict: PASS
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `log_activity()` gained `actor: str = "engine"` param; `engine.py` passes `actor=self._agent_name` at 7 call sites. `copilot-instructions.md` is 17 lines covering branch structure only — no activity log API documented there. No update needed. |
| 2 | Module docstrings | Yes | Verified | `activity_log.py::log_activity` docstring is accurate — entry format shows all 5 fields `{timestamp, action, task_id, detail, actor}`. `engine.py` class/method docstrings describe operational behavior without enumerating entry fields — all accurate. No stale content. |
| 3 | External attribution | Yes | Verified | `sources/overview.md` already contains `## Actor Field in Activity Log Tests (Task #811)` with 2 entries: PocketPaw (JSONL channel/session fields) and tundere-ledger (actor_name parameter). No additions needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified per builder notes. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/811-actor-field-activity-log-tests.md` exists; linked from task body in `## Research` section. |

### Files Updated
- None

### Scratch Files Cleaned
- None found (no `.owlbear/scratch/811-*` files)
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: new entries include "actor" field | activity_log.py:25 `"actor": actor` in entry dict; TestFromAC_ActorFieldPresent (5 tests) PASS | PASS |
| AC2: old entries without actor load without error | TestFromAC_BackwardCompat (4 tests) — injects 4-field JSON, parses without exception | PASS |
| AC3: default actor is "engine" | activity_log.py:14 `actor: str = "engine"`; TestFromAC_DefaultActorEngine (12 tests) assert `entry["actor"] == "engine"` | PASS |
| AC4: actor in all 7 action types | engine.py 7 call sites pass `actor=self._agent_name`; TestFromAC_ActorInAllActionTypes (21 tests) — 7 integration tests | PASS |
| AC5: tests fail RED | Test-writer commit b6d70782: 41/41 FAIL confirmed | PASS |

### Test Results
- pytest (task scope): 80 passed, 0 failed (41 from #811 + 39 existing activity tests)
- pytest (full suite): 3782 passed, 352 failed, 8 errors — all failures pre-existing, none in #811 scope
- ruff: clean (0 violations in serve/ and tests/)

### Architect Quality: 4/5
AC lines specific and verifiable. Minor gap: AC4 parenthetical listed 5 of 7 action types, but arch review caught and corrected this before test-writer. Good upstream quality.

### Deduction Breakdown
- Builder deliverables uncommitted (activity_log.py, test_kanban_engine_activity.py): -.02
- All 5 AC lines have specific evidence: no deduction
- Reviewer evidence section present and thorough (.97 PASS): no deduction
- No lint violations: no deduction
- No task-scope test failures: no deduction
- AC quality 4/5: no deduction

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| b6d70782 | test | tests/test_actor_field_activity_log_811.py | #811 |
| 6bcd2036 | feat | activity_log.py, test_kanban_engine_activity.py | #811 |