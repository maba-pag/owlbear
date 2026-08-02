---
id: 1517
title: 'P2-01: Tests for engine ac/proof_bundle in create_task, edit_task, and search'
status: archived
priority: medium
created: 2026-05-13T02:29:25.610232+00:00
updated: 2026-05-13T05:35:25.572689+00:00
tags:
  - phase-2
  - scope:kanban
  - tdd
  - feature
parent: 1514
depends_on:
  - 1516
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Unit tests for engine create_task/edit_task ac/proof_bundle params, validation, guardrails, search
Out of scope: MCP tools, migration, skill files

## Acceptance Criteria
- AC1: `KanbanEngine.create_task()` accepts `ac` and `proof_bundle` params; both `create_task()` and `edit_task()` reject `proof_bundle` values not in the engine's `VALID_PROOF_BUNDLES` frozenset with `ValidationError`; the frozenset enumerates bases (`skip`, `existing`, `smoke`, `behavioral`, `critical`) × modifier subsets (`+challenge`, `+reader`)
- AC2: `KanbanEngine.edit_task()` supports `ac` (full replacement), `add_ac` (append preserving existing order and placing new items at the end), and `remove_ac` (exact string-equality removal that does not affect near-collision items sharing a common substring); raises `ValidationError` when `ac` and `add_ac`/`remove_ac` are both provided
- AC3: `KanbanEngine.edit_task()` rejects duplicate `add_ac` items (items already present in the task's `ac` list) with `ValidationError` listing the existing duplicates
- AC4: `KanbanEngine.create_task()` and `edit_task()` enforce AC guardrails: max 20 items raises `ValidationError`; item exceeding 500 chars raises `ValidationError`
- AC5: `KanbanEngine.list_tasks(search="keyword")` returns tasks where `keyword` is a case-insensitive substring match in any frontmatter `ac` item

Proof bundle: behavioral
2026-05-13T04:59:16+00:00
## Architecture Review (Re-review after reviewer rejection)

### AC2 Refinement
Reviewer's second-pass FAIL identified two proof gaps in AC2:
1. `add_ac` "append" semantics unproven — test asserted membership (`in`) not ordering
2. `remove_ac` "exact-match" semantics unproven — no near-collision control item

**Action:** Refined AC2 wording to make proof expectations mechanically unambiguous:
- "append preserving existing order and placing new items at the end" — test-writer must assert positional ordering
- "exact string-equality removal that does not affect near-collision items sharing a common substring" — test-writer must include a control item that shares a substring with the removed item and prove it survives

### Evaluation (delta from prior review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Interface clarity | PASS | AC2 now explicitly defines append ordering and exact-match boundary |

All other criteria unchanged from prior APPROVE (same codebase state, same architecture).

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (focused retry — add 2 targeted tests per refined AC2 wording)

### Challenge Results
- Challenger: SKIPPED — re-review of wording refinement only; no architectural change from prior approved state

### Verdict: APPROVE
Proof bundle: behavioral
2026-05-13T05:10:57+00:00
## Test-Writer Notes
- Test file: tests/test_engine_ac_1517.py
- Classes: TestFromAC_ProofBundleValidation, TestFromAC_EditTaskAcMutation, TestFromAC_EditTaskAddAcDuplicates, TestFromAC_AcGuardrails, TestFromAC_ListTasksAcSearch
- Retry: added 2 tests targeting refined AC2 proof gaps
  - `test_edit_task_add_ac_appends_new_items_at_the_end` — positional ordering assertion (existing items at indices 0..n-1, appended items follow); replaces membership-only `in` check
  - `test_edit_task_remove_ac_exact_match_preserves_near_collision_item` — near-collision control: `"item to remove extended"` shares substring `"item to remove"` with target but must survive removal
- All 42 tests PASS against current implementation (impl is complete)
- ruff: clean
- Builder skip: test-only retry, all tests green — advancing directly to review
2026-05-13T05:29:31+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1517 -> docs | AC mapped to code and evidence sufficient.
- Builder/test-writer evidence reviewed first: task notes recorded `Proof bundle: behavioral`, `All 42 tests PASS against current implementation`, and `ruff: clean`.
- Independent verification was run because retained task notes did not include coverage evidence. `quality-runner` confirmed: 42/42 scoped tests passed, ruff clean on `tests/test_engine_ac_1517.py`, coverage recorded for `owlbear_kanban.engine` at 28%, and no environment/tooling errors.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/kanban/src/owlbear_kanban/engine.py:92-104`, `serve/kanban/src/owlbear_kanban/engine.py:198-207`, `serve/kanban/src/owlbear_kanban/engine.py:1136-1183`, `serve/kanban/src/owlbear_kanban/engine.py:1306-1368` | `tests/test_engine_ac_1517.py:136-216` incl. invalid rejection at `:155-176` and exact bundle-set proof at `:216-228` | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/engine.py:1300-1366` | `tests/test_engine_ac_1517.py:240-339` incl. append-order proof at `:300-313` and near-collision exact-match proof at `:315-338` | PASS |
| AC3 | `serve/kanban/src/owlbear_kanban/engine.py:1352-1359` | `tests/test_engine_ac_1517.py:347-397` incl. multi-duplicate message proof at `:384-397` | PASS |
| AC4 | `serve/kanban/src/owlbear_kanban/engine.py:212-223`, `serve/kanban/src/owlbear_kanban/engine.py:1138-1139`, `serve/kanban/src/owlbear_kanban/engine.py:1309-1311`, `serve/kanban/src/owlbear_kanban/engine.py:1366` | `tests/test_engine_ac_1517.py:409-503` incl. add_ac overflow at `:454-463` and exact-500 positive boundary at `:493-500` | PASS |
| AC5 | `serve/kanban/src/owlbear_kanban/engine.py:833-840` | `tests/test_engine_ac_1517.py:511-617` incl. case-insensitive search at `:524-535` and exclusion proof at `:593-617` | PASS |

- Safety/security check: reviewed paths are local validation and in-memory filtering only; no new injection, credential, or PII exposure surface was introduced in the scoped logic.

## Observations
- Challenger cross-check initially identified missing retained coverage evidence as the only PASS blocker candidate; the scoped `quality-runner` rerun resolved that proof gap without surfacing test or lint failures.
- `code-reader` found no blocking proof-sufficiency issue. Two optional hardening additions remain non-blocking only: one `edit_task()` success case using a modifier-bearing `proof_bundle`, and one `add_ac` success-at-boundary case for easier future review locality.
- `tests/test_engine_ac_1517.py:550` has a slightly misleading name (`test_list_tasks_search_ac_does_not_match_title_or_body`) because the assertions intentionally prove title-only hits still count; behavior is correct.
2026-05-13T05:31:09+00:00
## Docs Gate

- **Review Evidence present:** Yes — full AC table with code/test citations, quality-runner confirmation (42/42 PASS, ruff clean).
- **Item 1 — README Verification:** N/A. Changed file is `tests/test_engine_ac_1517.py` (root-level test only). Convention mapping yields no README target. `serve/kanban/README.md` uses `…` param placeholders — no stale parameter documentation.
- **Item 2 — External Attribution:** N/A — no external sources.
- **Item 3 — Research Doc:** N/A — no research artifact.
- **Item 4 — Deletion Detection:** N/A — no deletions.
- **Scratch cleanup:** No `.owlbear/scratch/1517-*` files found.

No docs impact — test-only task, convention mapping yields no targets.
2026-05-13T05:35:25+00:00
## Audit
### Regression Detection
- quality-runner mode full: pytest 1614 passed / 0 failed, ruff clean, eslint clean
- vitest: 1 failure in `CockpitProvider_1504.test.tsx` (task #1504 frontend provider test) — unrelated domain (React frontend vs Python kanban engine), pre-existing, not caused by #1517
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS — changed files (`engine.py`, `errors.py`, `test_engine_ac_1517.py`) all within `serve/kanban/` domain matching `scope:kanban` tag
- purpose match: PASS — tests cover create_task/edit_task ac/proof_bundle params, validation, guardrails, and search as stated in AC
- extraneous scope: none — `migrate.py` in the diff range belongs to #1522, not this task
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC1–AC5 are specific and mechanically verifiable. AC2 required a refinement pass after reviewer FAIL (membership-only assertion, no ordering/collision proof) — cost one pipeline cycle. Refined wording is precise and drove targeted test additions. Minor upstream gap, clean recovery.

### Commit Integrity
- upstream commit presence: PASS — 4 commits: `a7c645d2` (initial tests), `a3f04e8d` (builder impl), `f8c13d35` (retry gap-fill tests), `182947ff` (AC2 ordering+collision proofs)
- kanban commit packaging: pending (this step)

### Review Evidence
Reviewer section present with full AC mapping table (5/5 PASS), quality-runner confirmation (42/42 tests, ruff clean), code-reader findings, challenger cross-check, and safety/security check. Thorough.

### Deduction Breakdown
No deductions applied:
- Regression: pre-existing vitest failure in unrelated domain — not a #1517 regression
- Intent: clean scope alignment
- Evidence integrity: no concerns
- Lint: clean
- AC quality: 4/5 (above 3 threshold)
- Reviewer evidence: present and detailed

### Confidence: 1.00
### Action: archive