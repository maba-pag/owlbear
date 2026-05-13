---
id: 1518
title: 'P2-02: Implement engine ac/proof_bundle in create_task, edit_task, and search'
status: archived
priority: critical
created: 2026-05-13T02:29:31.968335+00:00
updated: 2026-05-13T06:44:14.055861+00:00
tags:
  - phase-2
  - scope:kanban
  - tdd
  - feature
parent: 1514
depends_on:
  - 1517
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Add ac/proof_bundle params to create_task and edit_task; implement proof_bundle frozenset validation, dual AC mutation (full replacement OR atomic add/remove with mutual exclusion), AC guardrails, search extension
Out of scope: MCP tools, migration, skill files

## Acceptance Criteria
- AC1: `KanbanEngine.create_task()` and `edit_task()` accept `proof_bundle` param; reject values not in `VALID_PROOF_BUNDLES` with `ValidationError(code="ERR_PROOF_BUNDLE_INVALID")` whose `user_message` contains every member of `VALID_PROOF_BUNDLES`
- AC2: `KanbanEngine.edit_task()` supports `ac` (full replacement), `add_ac` (append), and `remove_ac` (exact-match removal); raises `ValidationError` when `ac` and `add_ac`/`remove_ac` are both provided
- AC3: `KanbanEngine.edit_task()` rejects duplicate `add_ac` items with `ValidationError` listing existing duplicates
- AC4: `KanbanEngine.create_task()` and `edit_task()` enforce AC guardrails: max 20 items raises `ValidationError`; item exceeding 500 chars raises `ValidationError`
- AC5: `KanbanEngine.list_tasks(search="keyword")` returns tasks where `keyword` is a case-insensitive substring match in any frontmatter `ac` item

Proof bundle: smoke
Existing proof scope: tests/test_engine_ac_1517.py
Smoke scope: Strengthen `test_create_task_invalid_proof_bundle_user_message_contains_all_valid_bundles` and `test_edit_task_invalid_proof_bundle_user_message_contains_all_valid_bundles` in `tests/test_engine_ac_1518.py` to assert each `VALID_PROOF_BUNDLES` member using `repr(member) in msg` (quoted-token matching) instead of bare `member in msg`, preventing substring false positives where base values (e.g. `smoke`) match modifier variants (e.g. `smoke+challenge`).
2026-05-13T06:07:14+00:00
## Architecture Review (Re-scope)

### Context
Reviewer rejected previous cycle: AC1 proof gap — existing tests assert only error code, not the `user_message` listing valid options. AC2–AC5 confirmed fully covered.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Engine-level ac/proof_bundle CRUD |
| Interface clarity | PASS | AC1 refined: explicit edit_task coverage + oracle removed |
| Dependency correctness | PASS | #1517 archived (confidence 1.00) |
| Module layering | PASS | Engine validates → model normalizes |
| TDD compliance | PASS | Smoke escalation covers the gap |
| KISS/YAGNI | PASS | Minimal change: 2 assertions added |
| Premise challenge | PASS | Implementation verified in engine.py:198-207 |
| Pattern consistency | PASS | Follows existing ValidationError patterns |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | scope:kanban only |

### AC Refinement
- AC1: Expanded to explicitly name both `create_task()` and `edit_task()` (was create_task only). Replaced vague "listing valid options" with precise "`user_message` contains every member of `VALID_PROOF_BUNDLES`".

### Proof-Bundle Validation
- Planner assignment: behavioral (original); existing (first arch-review de-escalation)
- Final bundle: smoke
- Existing proof scope: tests/test_engine_ac_1517.py (42 tests, AC2-AC5 fully proven)
- Smoke scope: 2 `user_message` assertions in existing test methods
- Escalation rationale: Reviewer proved `existing` bundle was insufficient for AC1's "listing valid options" contract. Escalating to `smoke` requires the test-writer to add targeted assertions without full TDD overhead.

### Design Diverge
- Trigger: skipped — single clear approach

### Challenge Results
- Challenger: reconsider (0.64)
- Findings accepted: (1) AC1 scope gap — edit_task not named; (2) "valid options" oracle undefined
- Findings rejected: AC5 ambiguity — challenger misread test_list_tasks_search_ac_does_not_match_title_or_body; test correctly verifies both ac-based and title-based search coexist
- Architect response: Refined AC1 to address both accepted findings; escalated proof bundle
2026-05-13T06:09:54+00:00
## Test-Writer Notes
- Proof bundle: smoke — 2 targeted smoke tests for AC1 `user_message` coverage gap
- Test file: `tests/test_engine_ac_1518.py`
- Class: `TestFromAC_ProofBundleUserMessage`
- Tests written: 2 (smoke category)

| Test | AC | Category |
|---|---|---|
| `test_create_task_invalid_proof_bundle_user_message_contains_all_valid_bundles` | AC1 | smoke |
| `test_edit_task_invalid_proof_bundle_user_message_contains_all_valid_bundles` | AC1 | smoke |

- AC coverage: AC1 fully covered (both `create_task` and `edit_task` `user_message` assertions)
- Quality-runner result: 2 passed, 0 failed, lint clean
- Builder skip: all smoke tests GREEN — implementation already satisfies the `user_message` contract (engine.py:207). Advancing directly to review.
2026-05-13T06:20:53+00:00
## Review Evidence
- Verdict: FAIL
- FAIL route: backlog — AC1 proof remains insufficient on this second review cycle.
- Builder/test-writer evidence reviewed first: task notes record `Proof bundle: smoke`, `Quality-runner result: 2 passed, 0 failed, lint clean`, and builder skip because the implementation already satisfied the contract.
- Existing proof reuse check: archived task #1517 already mapped AC2–AC5 to code and independently verified that proof surface (42/42 scoped tests passed, ruff clean, coverage recorded for `owlbear_kanban.engine`). This retry only needed to close the AC1 `user_message` oracle gap.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/kanban/src/owlbear_kanban/engine.py:173-207`, `serve/kanban/src/owlbear_kanban/engine.py:1086-1184`, `serve/kanban/src/owlbear_kanban/engine.py:1228-1370` | `tests/test_engine_ac_1517.py:155-176`, `tests/test_engine_ac_1517.py:216-228`, `tests/test_engine_ac_1518.py:109-136` | FAIL |
| AC2 | `serve/kanban/src/owlbear_kanban/engine.py:1228-1370` | `tests/test_engine_ac_1517.py:237-343` | PASS |
| AC3 | `serve/kanban/src/owlbear_kanban/engine.py:1352-1359` | `tests/test_engine_ac_1517.py:344-405` | PASS |
| AC4 | `serve/kanban/src/owlbear_kanban/engine.py:212-223`, `serve/kanban/src/owlbear_kanban/engine.py:1086-1184`, `serve/kanban/src/owlbear_kanban/engine.py:1228-1370` | `tests/test_engine_ac_1517.py:406-507` | PASS |
| AC5 | `serve/kanban/src/owlbear_kanban/engine.py:833-840` | `tests/test_engine_ac_1517.py:508-609` | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC1 | The new smoke tests use raw substring assertions (`assert member in msg`) for each proof-bundle member. That is not a strong oracle for "contains every member" because base values such as `skip`, `existing`, `smoke`, `behavioral`, and `critical` are substrings of modifier variants such as `smoke+challenge` and `critical+reader`. The tests can stay green even if the `user_message` omits the standalone base entries, so the reopened proof gap is not actually closed. | `tests/test_engine_ac_1518.py:121`, `tests/test_engine_ac_1518.py:135`, `serve/kanban/src/owlbear_kanban/engine.py:207`, `.owlbear/kanban/tasks/1518-p2-02-implement-engine-ac-proof-bundle-in-create-task-edit-task-and-search.md:37`, `.owlbear/kanban/tasks/1518-p2-02-implement-engine-ac-proof-bundle-in-create-task-edit-task-and-search.md:42`, `.owlbear/kanban/tasks/1518-p2-02-implement-engine-ac-proof-bundle-in-create-task-edit-task-and-search.md:65`, `.owlbear/kanban/tasks/1518-p2-02-implement-engine-ac-proof-bundle-in-create-task-edit-task-and-search.md:92` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC1 smoke-proof wording to require exact per-entry validation for each `VALID_PROOF_BUNDLES` value in `user_message` (for example, quoted-token assertions or parsed-list equality), then re-dispatch test-writer for a targeted retry without reopening AC2–AC5. | `.owlbear/kanban/tasks/1518-p2-02-implement-engine-ac-proof-bundle-in-create-task-edit-task-and-search.md`, `tests/test_engine_ac_1518.py` | `tests/test_engine_ac_1518.py:121`, `tests/test_engine_ac_1518.py:135`, `serve/kanban/src/owlbear_kanban/engine.py:207` |

## Observations
- AC2–AC5 remain sufficiently proven via archived task #1517; the retry should stay narrowly scoped to the AC1 proof oracle.
- Safety/security review found no new injection, credential, or PII surface in the reviewed validation and in-memory search logic.
2026-05-13T06:30:43+00:00
## Architecture Review (Cycle 3 — Oracle Refinement)

### Context
Reviewer rejected cycle 2: AC1 smoke tests use bare `member in msg` substring assertions — weak oracle where base values (e.g. `smoke`) are substrings of modifier variants (e.g. `smoke+challenge`). AC2–AC5 remain proven via #1517.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Narrowly scoped oracle fix |
| Interface clarity | PASS | AC1-AC5 unchanged; Smoke scope refined |
| Dependency correctness | PASS | #1517 archived/completed |
| Module layering | PASS | No structural change |
| TDD compliance | PASS | Smoke scope prescribes specific oracle |
| KISS/YAGNI | PASS | 2 assertion changes, no new abstractions |
| Premise challenge | PASS | Verified `sorted(VALID_PROOF_BUNDLES)` produces Python list repr with quoted elements; `repr(member)` is distinct per entry |
| Pattern consistency | PASS | repr-based assertions follow Python testing conventions |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:kanban only |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 | B3: "every" used with exhaustive enumeration (`VALID_PROOF_BUNDLES` frozenset) — passes exception | Smoke scope refined: `repr(member) in msg` |
| AC2 | PASS — proven via #1517 | None |
| AC3 | PASS — proven via #1517, narrow reading (already-in-task) codified in impl+tests | None |
| AC4 | PASS — proven via #1517 | None |
| AC5 | PASS — proven via #1517 | None |

### Smoke Scope Refinement
- Previous: bare `member in msg` — weak oracle, substring false positives possible
- Refined: `repr(member) in msg` — quoted-token matching (`'smoke'` is NOT a substring of `'smoke+challenge'` because after `e` comes `+` not `'`)
- Scope: tests/test_engine_ac_1518.py, 2 existing test methods, assertion change only

### Proof-Bundle Validation
- Planner assignment: behavioral (original)
- Final bundle: smoke
- Existing proof scope: tests/test_engine_ac_1517.py (42 tests, AC2-AC5)
- Smoke scope: `repr(member) in msg` assertions in 2 existing tests
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single assertion fix, no alternative approaches

### Challenge Results
- Challenger: reconsider (0.74)
- Accepted: oracle refinement needed in Smoke scope (1 finding)
- Rejected: AC3 ambiguity (already resolved in #1517), evidence-chain overstatement (#1517 confirmed via show_task), AC5 test naming (not in scope)
- Override justification: B3 "every" passes the exhaustive-enumeration exception (VALID_PROOF_BUNDLES is a defined 20-member frozenset); AC3/AC5 concerns re-open closed review cycles

### Verdict: APPROVE
### Action Taken: Refined Smoke scope to prescribe `repr(member) in msg` quoted-token oracle. AC text unchanged. Advanced to todo.
2026-05-13T06:34:13+00:00
## Test-Writer Notes
- Retry: strengthened 2 smoke assertions in `tests/test_engine_ac_1518.py` — `member in msg` → `repr(member) in msg` (quoted-token oracle)
- Test file: `tests/test_engine_ac_1518.py`
- Class: `TestFromAC_ProofBundleUserMessage`
- Tests: 2 modified (smoke category), 0 new

| Test | AC | Change |
|---|---|---|
| `test_create_task_invalid_proof_bundle_user_message_contains_all_valid_bundles` | AC1 | `member in msg` → `repr(member) in msg` |
| `test_edit_task_invalid_proof_bundle_user_message_contains_all_valid_bundles` | AC1 | `member in msg` → `repr(member) in msg` |

- Quality-runner result: 2 passed, 0 failed, ruff clean
- Builder skip: test-only retry, all tests GREEN — `sorted(VALID_PROOF_BUNDLES)` already emits Python list repr with per-member quoted tokens; `repr(member)` assertions (`'smoke'` vs `'smoke+challenge'`) correctly resolve the false-positive oracle gap and pass against current implementation.
- Advancing directly to review (Step 1b.1).
2026-05-13T06:38:00+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1518 to docs | AC mapped to code and evidence sufficient.
- Builder/test-writer evidence reviewed first: task notes record `Proof bundle: smoke`, `2 passed, 0 failed`, `ruff clean`, and builder skip on a test-only retry. I did not rerun quality-runner because that smoke packet is complete and internally consistent for the only reopened proof gap.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/kanban/src/owlbear_kanban/engine.py:92`, `serve/kanban/src/owlbear_kanban/engine.py:204-207`, `serve/kanban/src/owlbear_kanban/engine.py:1139`, `serve/kanban/src/owlbear_kanban/engine.py:1306` | `tests/test_engine_ac_1517.py:155`, `tests/test_engine_ac_1517.py:171`, `tests/test_engine_ac_1517.py:216`, `tests/test_engine_ac_1518.py:121`, `tests/test_engine_ac_1518.py:135` | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/engine.py:1300-1366` | `tests/test_engine_ac_1517.py:300`, `tests/test_engine_ac_1517.py:315` | PASS |
| AC3 | `serve/kanban/src/owlbear_kanban/engine.py:1352-1359` | `tests/test_engine_ac_1517.py:384` | PASS |
| AC4 | `serve/kanban/src/owlbear_kanban/engine.py:212-223`, `serve/kanban/src/owlbear_kanban/engine.py:1138`, `serve/kanban/src/owlbear_kanban/engine.py:1309-1311`, `serve/kanban/src/owlbear_kanban/engine.py:1366` | `tests/test_engine_ac_1517.py:454`, `tests/test_engine_ac_1517.py:493` | PASS |
| AC5 | `serve/kanban/src/owlbear_kanban/engine.py:833-840` | `tests/test_engine_ac_1517.py:524`, `tests/test_engine_ac_1517.py:593` | PASS |

- Safety/security check: reviewed paths are local validation and in-memory search only; no new injection, credential, or PII exposure surface was introduced in the scoped logic.

## Observations
- The reopened AC1 proof gap is closed. `serve/kanban/src/owlbear_kanban/engine.py:207` renders `sorted(VALID_PROOF_BUNDLES)` as Python string-list repr, and the strengthened assertions at `tests/test_engine_ac_1518.py:121` and `tests/test_engine_ac_1518.py:135` now require each standalone quoted token via `repr(member) in msg`, which removes the prior substring false-positive risk for base values such as `smoke` versus modifier variants such as `smoke+challenge`.
- Existing proof reuse from archived task #1517 remains sufficient for AC2-AC5; this cycle correctly stayed limited to the AC1 oracle fix.
2026-05-13T06:39:41+00:00
## Docs Gate

**Verdict: DONE — no docs impact**

**Changed files:** `tests/test_engine_ac_1518.py` only (2 assertion-line oracle strengthening: `member in msg` → `repr(member) in msg`).

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A | Test-only change; workspace-root `tests/` has no convention-mapping README target; no public API/CLI/config change |
| External Attribution | N/A | No external sources; Python stdlib `repr()` only |
| Research Doc | N/A | No research artifact for this task |
| Deletion Detection | N/A | No files deleted |

Scratch cleanup: no `.owlbear/scratch/1518-*` files present.
2026-05-13T06:44:14+00:00
## Audit
### Regression Detection
- quality-runner mode full: 4482 passed, 214+ failed (all pre-existing in unrelated modules: test_ideation_diagram, test_cockpit_view, test_server, test_engine_accessor_migration), lint clean
- Task-scoped: 44 passed (42 from #1517 + 2 from #1518), 0 failed, ruff clean
- No regressions introduced by #1518
- Regression verdict: PASS

### Intent Verification
- Scope alignment: PASS (changed files: tests/test_engine_ac_1518.py only, within scope:kanban domain)
- Purpose match: PASS (assertion oracle strengthening closes AC1 user_message proof gap via repr-based assertions)
- Extraneous scope: none (git diff confirms only test file + kanban state files changed)
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC1 was specific (error code, user_message content requirement), but needed 3 architect cycles to specify the oracle tightly enough. Final cycle 3 refinement (repr-based quoted-token assertions) was clean and precise. AC2-AC5 correctly not reopened; proven in #1517.

### Commit Integrity
- Upstream commit presence: PASS (87a8dff7 and 84e3c986, both tagged #1518 test-writer)
- Kanban commit packaging: pending (this archival)

### Deduction Breakdown
No deductions. Pre-existing suite failures confirmed unrelated to task scope. Reviewer evidence section present and detailed with PASS verdict. Lint clean. AC quality 4/5.

### Confidence: 1.00
### Action: archive