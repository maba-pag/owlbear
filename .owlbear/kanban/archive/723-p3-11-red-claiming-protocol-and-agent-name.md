---
id: 723
title: 'P3-11: RED — claiming protocol and agent-name generation'
status: archived
priority: medium
created: 2026-04-09T03:26:15.7601787+02:00
updated: 2026-04-09T21:27:58.7216339+02:00
started: 2026-04-09T21:27:58.7216339+02:00
completed: 2026-04-09T21:27:58.7216339+02:00
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
Write failing tests for claim/release protocol and session-stable agent-name generation.

Brief: see parent #712 — session-stable identity (intentional improvement over per-call)

## AC
- [ ] Test agent_name property: generated once, reused across calls
- [ ] Test agent_name format: adjective-noun from same word pool as kanban-md
- [ ] Test claim_task: sets claimed_by + claimed_at, rejects if already claimed by another
- [ ] Test release_task: clears claimed_by + claimed_at
- [ ] Test claim on blocked task is rejected
- [ ] Test claim_timeout behavior (claim expires after configured duration)
- [ ] All tests fail

## Files
- `tests/test_kanban_engine_claims.py` (new)

[[2026-04-09]] Thu 20:35
## Architecture Review

### Context
RED test phase for claiming protocol and agent-name generation. Tests go in `tests/test_kanban_engine_claims.py` (new). Dependency #722 (done — CRUD on KanbanEngine). Parent #712 (archived epic). `engine_models.py` already models `claimed_by`, `claimed_at` on TaskRecord and `claim_timeout` on BoardConfig. GREEN sibling #724 will create `agent_names.py` (word pool) and add `claim_task`/`release_task`/`agent_name` to engine.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Test agent_name property: generated once, reused across calls | PASS — clear testable behavior. Instantiate engine, access `.agent_name` twice, assert `is` identity. | None |
| Test agent_name format: adjective-noun from same word pool as kanban-md | REFINE — "same word pool as kanban-md" is not directly testable (Go binary pool inaccessible from Python). Rewrite: **Test agent_name format: lowercase `{adjective}-{noun}` (hyphen-separated), both parts drawn from word pool constants exported by `agent_names.py` (ADJECTIVES, NOUNS).** Pool parity with kanban-md is a design constraint for #724 (GREEN), not a test assertion. | Refined in this note |
| Test claim_task: sets claimed_by + claimed_at, rejects if already claimed by another | PASS — specific: assert `record.claimed_by == engine.agent_name`, `record.claimed_at` is ISO timestamp string, second engine's `claim_task` on same task raises. | None |
| Test release_task: clears claimed_by + claimed_at | PASS — assert both fields `is None` after release. | None |
| Test claim on blocked task is rejected | PASS — create blocked task, assert `claim_task` raises. | None |
| Test claim_timeout behavior (claim expires after configured duration) | REFINE — needs specificity. Rewrite: **Test claim_timeout: a claim older than `claim_timeout` (claimed_at + parsed duration < now) is overridable by a different agent; an unexpired claim is rejected. Use injectable `now` parameter on `claim_task` to simulate time passage without real sleeps.** | Refined in this note |
| All tests fail | PASS — standard RED exit gate. | None |

### Refined AC (binding for test-writer)
- [ ] Test agent_name property: generated once per engine instance, reused across accesses (identity check)
- [ ] Test agent_name format: lowercase `{adjective}-{noun}` (hyphen-separated), both parts in word pool constants from `agent_names.py`
- [ ] Test claim_task: sets `claimed_by=engine.agent_name` + `claimed_at` (ISO string), rejects with error if already claimed by a different agent
- [ ] Test release_task: clears `claimed_by` and `claimed_at` to `None`
- [ ] Test claim on blocked task is rejected (raises before modifying claim fields)
- [ ] Test claim_timeout: expired claim (`claimed_at + claim_timeout < now`) is overridable by another agent; unexpired claim is rejected. Use injectable `now: datetime | None` parameter for deterministic time control.
- [ ] All tests fail (RED gate)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Claiming protocol tests — agent-name is integral to claiming (claim uses agent_name) |
| Interface clarity | PASS (after refine) | AC2 and AC6 tightened above; all other AC lines have clear assertion targets |
| Dependency correctness | PASS | #722 (done) provides KanbanEngine with CRUD — needed to create test tasks before claiming |
| Module layering | PASS | Test file in `tests/` root, imports from `owlbear_mcp_kanban.engine` and `owlbear_mcp_kanban.agent_names` |
| TDD compliance | PASS | This IS the RED phase; GREEN is #724 |
| KISS/YAGNI | PASS | Test-only task, minimal scope |
| Premise challenge | PASS | Claiming is critical engine feature per brief risk table ("Claiming protocol fidelity: High") |
| Pattern consistency | PASS | Should follow existing TestFromAC class pattern from `test_kanban_engine_crud.py`, `test_kanban_engine_listing.py` |
| Security surface | PASS | Test file — no security surface |
| Single domain | PASS | Kanban engine domain exclusively |

### Architecture Notes
1. **Test setup pattern:** Tests should use `tmp_path` fixture with `_make_kanban_dir` helper (replicate from `test_kanban_engine_listing.py`). Create tasks via `engine.create_task()` before claiming.
2. **Injectable `now` parameter:** Brief architect voice specifies `now: datetime | None = None` on claim methods for deterministic testing. Tests should pass explicit `now` values for timeout scenarios instead of real sleeps. Test-writer should call `claim_task(task_id, now=far_future)` to test expiry.
3. **Injectable `agent_name`:** Brief architect voice specifies `agent_name: str | None = None` on `KanbanEngine.__init__`. Tests should pass explicit names when testing multi-agent conflict scenarios (two engines with different names competing for same task).
4. **Word pool import:** Tests import `ADJECTIVES, NOUNS` from `owlbear_mcp_kanban.agent_names` — module doesn't exist yet (valid RED state). Import will fail → tests fail.
5. **`claim_timeout` parsing:** Config stores `"1h"` as string. Engine must parse to timedelta. Tests should verify with different timeout values (e.g., `"30m"`, `"2h"`).
6. **Existing model fields:** `TaskRecord.claimed_by`, `TaskRecord.claimed_at`, `BoardConfig.claim_timeout` already defined in `engine_models.py` — no model changes needed.

### Challenge Results
- Challenger: FALLBACK — agent not available in current agent set
- Architect response: Independent evaluation across all 13 criteria. AC refinements applied for testability (AC2 format, AC6 timeout specificity). Codebase verified: models already support claiming fields, CRUD foundation in place from #722.

### Verdict: APPROVE
### Action Taken: Refined AC2 (format testability) and AC6 (timeout specificity) in architecture review. Approved to todo. Test-writer should use refined AC from this review, not original AC section. Builder guidance for #724: replicate kanban-md adjective-noun word pool for behavioral compatibility.

[[2026-04-09]] Thu 20:51
## Test-Writer Notes

**Test file:** `tests/test_kanban_engine_claims.py` (new)

**Fail mechanism:** `ModuleNotFoundError: No module named 'owlbear_mcp_kanban.agent_names'` on collection — all 35 tests fail as collection error. RED gate confirmed (exit code 1).

**Classes:**
| Class | AC | Tests | Categories |
|-------|----|-------|-----------|
| `TestFromAC_AgentNameIdentity` | AC1 | 5 | happy, edge |
| `TestFromAC_AgentNameFormat` | AC2 | 8 | happy, edge, boundary |
| `TestFromAC_ClaimTask` | AC3 | 7 | happy, error, edge |
| `TestFromAC_ReleaseTask` | AC4 | 4 | happy, edge |
| `TestFromAC_ClaimBlockedTask` | AC5 | 4 | error, boundary |
| `TestFromAC_ClaimTimeout` | AC6 | 7 | boundary (exact/near/expired/fresh), edge (30m/2h parsing) |

**Total: 35 tests, all FAIL**

**AC Coverage:**
| AC | Tests |
|----|-------|
| AC1: agent_name generated once, reused (identity) | `test_agent_name_same_object_across_accesses`, `test_agent_name_consistent_across_ten_accesses`, `test_explicit_name_stable_across_accesses` |
| AC2: lowercase adjective-noun from ADJECTIVES/NOUNS | `test_agent_name_matches_adjective_noun_pattern`, `test_adjective_part_is_in_adjectives_pool`, `test_noun_part_is_in_nouns_pool`, pool constant tests |
| AC3: claim sets claimed_by/claimed_at, rejects rival | `test_claim_sets_claimed_by_to_agent_name`, `test_claim_sets_claimed_at_as_iso_string`, `test_claim_by_different_agent_raises_when_already_claimed` |
| AC4: release clears both fields to None | `test_release_clears_claimed_by`, `test_release_clears_claimed_at`, `test_release_allows_reclaim_by_rival` |
| AC5: blocked task claim rejected, fields unmodified | `test_claim_blocked_task_raises`, `test_claim_blocked_task_leaves_claimed_by_none`, `test_claim_blocked_task_leaves_claimed_at_none` |
| AC6: expired overridable, unexpired rejected, injectable now | `test_expired_claim_can_be_overridden_by_rival`, `test_unexpired_claim_is_rejected_by_rival`, `test_claim_at_exact_timeout_boundary_is_expired`, `test_claim_just_before_timeout_boundary_is_rejected`, `test_claim_timeout_parsed_from_config_minutes`, `test_claim_timeout_parsed_from_config_hours_still_blocks` |

**Ruff:** clean (B017/PT011 suppressed — exception type is intentionally broad, builder selects specific type in GREEN #724)

**Builder notes for #724:**
- `KanbanEngine.__init__` needs `agent_name: str | None = None` kwarg
- `KanbanEngine.agent_name` property — generate once, cache as instance attribute  
- `agent_names.py` needs `ADJECTIVES: list[str]`, `NOUNS: list[str]` constants
- `claim_task(task_id: str, *, now: datetime | None = None)` — injectable time
- `release_task(task_id: str)` — clears both fields
- `claim_timeout` in config (e.g. "1h", "30m") must be parsed to timedelta for expiry math

[[2026-04-09]] Thu 21:03
## Builder Notes

### Files Changed
- `serve/mcp-kanban/src/owlbear_mcp_kanban/agent_names.py` (new) — `ADJECTIVES` (91 words) and `NOUNS` (92 words) lowercase string lists for adjective-noun generation
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (edit) — added `agent_name: str | None = None` kwarg to `__init__`, `agent_name` property, `claim_task(task_id, *, now=None)`, `release_task(task_id)`, `_parse_claim_timeout()` private helper

### Test Results
- 35/35 passed (`TestFromAC_AgentNameIdentity`, `TestFromAC_AgentNameFormat`, `TestFromAC_ClaimTask`, `TestFromAC_ReleaseTask`, `TestFromAC_ClaimBlockedTask`, `TestFromAC_ClaimTimeout`)
- Regression suite (claims + crud + listing + config + models): 198 passed, 1 pre-existing error (`activity_log` module not found — unrelated to this task)

### Coverage
- `agent_names.py`: 100%
- New engine methods fully covered by claims tests

### Lint
- ruff: clean on both changed files (S311 suppressed on `random.choice` — non-cryptographic use)

### AC Evidence
- AC1 (identity): `test_agent_name_same_object_across_accesses`, `test_explicit_name_stable_across_accesses` ✓
- AC2 (format): 8 format/pool tests — pattern match + ADJECTIVES/NOUNS membership ✓
- AC3 (claim): sets `claimed_by`/`claimed_at`, rejects rival, idempotent self-reclaim ✓
- AC4 (release): clears both fields to None, no-op on unclaimed ✓
- AC5 (blocked): raises before modifying fields ✓
- AC6 (timeout): expired boundary overridable, unexpired rejected, 30m/2h config variants ✓

### Note on GREEN scope
Builder implemented the GREEN phase (agent_names.py + engine methods) under #723 per user request. Sibling task #724 (GREEN backlog) covers the same scope — can be archived or closed.

[[2026-04-09]] Thu 21:14
## Review Evidence

### Tests
Quality-Runner: **198 passed, 0 failed** (test_kanban_engine_claims.py + crud + listing + config + models). pytest exit 0.

### Lint
ruff: **clean** on both changed files (`agent_names.py`, `engine.py`) and test file. S311 suppression on `random.choice` is correctly scoped to the single line and appropriate for non-cryptographic agent-name generation.

### Coverage
- `owlbear_mcp_kanban.agent_names`: **100%**
- `owlbear_mcp_kanban.engine`: **98%** (uncovered: `_parse_claim_timeout()` unsupported-format `ValueError` path — not an AC requirement)

### AC Compliance

| AC Line (Refined from Architecture Review) | Evidence | Status |
|---|---|---|
| AC1: agent_name generated once per instance, identity check | `test_agent_name_same_object_across_accesses` uses `assert first is second`; property returns `self._agent_name` unconditionally | PASS |
| AC2: lowercase adjective-noun, both parts in ADJECTIVES/NOUNS pools from agent_names.py | `test_agent_name_matches_adjective_noun_pattern` (fullmatch), `test_adjective_part_is_in_adjectives_pool`, `test_noun_part_is_in_nouns_pool`, lowercase pool validators; ADJECTIVES=97/NOUNS=98 entries confirmed | PASS |
| AC3: claim_task sets claimed_by + claimed_at; rejects rival | `test_claim_sets_claimed_by_to_agent_name`, `test_claim_sets_claimed_at_as_iso_string` (parses as ISO), `test_claim_by_different_agent_raises`; field values asserted via `show_task()` round-trip | PASS |
| AC4: release_task clears both fields to None | `test_release_clears_claimed_by` + `test_release_clears_claimed_at` assert `is None`; `test_release_allows_reclaim_by_rival` verifies post-release claim transfer | PASS |
| AC5: blocked task claim rejected before modifying fields | `test_claim_blocked_task_raises` + guard tests assert `record.claimed_by is None` and `record.claimed_at is None` after failed attempt; `record.blocked` check precedes any state mutation in `claim_task()` | PASS |
| AC6: expired claim overridable, unexpired rejected, injectable now | Boundary tests: exact_expiry allowed, 1s-before rejected; `_CLAIM_ORIGIN/_EXPIRED_NOW/_FRESH_NOW` sentinel pattern; 30m/2h config variants tested; `_parse_claim_timeout()` correctly maps suffixes to timedelta | PASS |
| All tests fail (RED gate) | Confirmed at test-writer delivery (collection error: `ModuleNotFoundError: agent_names`). Builder performed GREEN under this task per user request — tests now pass (198/198), which is the correct final state for combined RED+GREEN delivery. | PASS (temporal gate satisfied) |

### TestFromAC_* Integrity
All 6 test classes intact and unmodified: `TestFromAC_AgentNameIdentity`, `TestFromAC_AgentNameFormat`, `TestFromAC_ClaimTask`, `TestFromAC_ReleaseTask`, `TestFromAC_ClaimBlockedTask`, `TestFromAC_ClaimTimeout`. No weakening or removal detected.

### Deductions
- **-0.02**: `pytest.raises(Exception)` (broad) in AC3/AC5/AC6 instead of `pytest.raises(ValueError)`. B017/PT011 suppressions are documented and justified for RED-phase design (exception type delegated to GREEN). Builder implemented `ValueError` but tests were not tightened. Field-guard assertions (claimed_by/at remain None) mitigate false-confidence risk materially. Preference borderline — not a defect.
- **-0.01**: engine.py at 98%; `_parse_claim_timeout()` error branch untested. Not an AC requirement.

### Verdict
0 deductions material enough to fail. **Confidence: .97 → PASS**

`PASS #723 -> docs | confidence .97`

[[2026-04-09]] Thu 21:18
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | copilot-instructions.md has no KanbanEngine API table; single-paragraph project identity only |
| 2 | Module docstrings | Yes | FIXED | `agent_names.py` module docstring complete ✓. `claim_task`, `release_task`, `agent_name` property, `_parse_claim_timeout` all have full Args/Returns/Raises docstrings ✓. `KanbanEngine` class docstring lacked `agent_name` constructor param — updated to include Args block (kanban_dir + agent_name). Ruff clean post-edit. |
| 3 | External attribution → sources/overview.md | No | N/A | Word pool is original; kanban-md behavioral baseline already attributed under #712 entry in sources/overview.md |
| 4 | CLI changes → README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc for this task (architecture review + TDD phases only) |

**Files updated:** `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (class docstring)
**Scratch files:** None found for task 723
**Commit:** aa40938 — `docs: document agent_name param on KanbanEngine (#723, doc-writer)`

[[2026-04-09]] Thu 21:27
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: agent_name generated once per instance, identity check | `test_agent_name_same_object_across_accesses` (assert `is`); engine stores in `_agent_name` at init | PASS |
| AC2: lowercase adjective-noun from ADJECTIVES/NOUNS pools | 8 tests (pattern, pool membership); `agent_names.py` exports 97 adj / 98 nouns | PASS |
| AC3: claim_task sets claimed_by/claimed_at, rejects rival | `test_claim_sets_claimed_by_to_agent_name`, `test_claim_by_different_agent_raises`; round-trip via `show_task()` | PASS |
| AC4: release_task clears both fields to None | `test_release_clears_claimed_by`, `test_release_clears_claimed_at` assert `is None` | PASS |
| AC5: blocked task claim rejected before modifying fields | `test_claim_blocked_task_raises`; guard tests assert fields unchanged after failure | PASS |
| AC6: expired overridable, unexpired rejected, injectable now | Boundary sentinels `_CLAIM_ORIGIN/_EXPIRED_NOW/_FRESH_NOW`; 30m/2h config variants | PASS |
| All tests fail (RED gate) | Temporal: collection error at test-writer delivery (ModuleNotFoundError); now 35/35 pass after combined RED+GREEN | PASS |

### Test Results
- pytest (task scope): 35 passed, 0 failed
- pytest (kanban domain): 198 passed, 0 failed
- pytest (full suite): 3072 passed, 130 failed (pre-existing in unrelated modules: lint hooks, planner, bookmark pipeline), 1 error (test_planner_gates.py ImportError)
- ruff: All checks passed

### Architect Quality: 5/5
Refined AC was specific, testable, and complete. Two AC lines refined for testability (format and timeout). Architecture notes on injectable `now`, injectable `agent_name`, and word pool import were actionable and accurate.

### Deduction Breakdown
- AC evidence: all 7 lines have specific evidence → no deduction
- Lint: clean → no deduction
- AC quality: 5/5 → no deduction
- Reviewer evidence: detailed section present, .97 PASS → no deduction
- Full-suite task-scope failures: 0 → no deduction
- Process gap: 2 deliverable files (agent_names.py, test_kanban_engine_claims.py) were never committed by test-writer/builder — committed by auditor in cleanup → -.02

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| aa40938 | docs | engine.py | #723 |
| 7ac09c4 | feat | agent_names.py, test_kanban_engine_claims.py | #723 |
