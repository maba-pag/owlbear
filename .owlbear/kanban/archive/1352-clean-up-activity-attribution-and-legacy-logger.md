---
id: 1352
title: Clean up activity attribution and legacy logger
status: archived
priority: medium
created: 2026-05-04T18:45:18.968070+00:00
updated: 2026-05-05T20:23:46.882194+00:00
tags:
- sync-blocker
- kanban
- audit-log
parent:
depends_on:
- 1348
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The kanban package has two activity concepts: the current structured `ActivityEvent` / `activity_store.py` path that uses `source`, and an older `activity_log.py` helper that writes actor-shaped events. Tests explicitly assert that engine events do not include an `actor` field, so the issue is not simply to add actor back. The deployment risk is drift: unused logger code, stale docs/prose, and unclear source attribution across engine, MCP, and Cockpit.

Before sync, the activity/audit story should be one coherent contract: one logger model, one attribution vocabulary, and no legacy module inviting new callers to write incompatible audit rows.

## Acceptance Criteria

1. Confirm the canonical activity schema is `ActivityEvent` with fields `source`/`action`/`task_id`/`detail`/`timestamp`; do not reintroduce an `actor` field unless a decision request changes the contract. (td:0)
2. Delete `serve/kanban/src/owlbear_kanban/activity_log.py`. No production module may import it after this change. (td:1)
3. The source vocabulary is `"engine"` | `"agent"` | `"cockpit"` — document this enum-like set in `activity_store.py` module docstring and in `serve/cockpit/README.md` where the audit-trail section lives. (td:1)
4. Update `serve/cockpit/README.md` audit-trail section: replace `actor: "cockpit"` heading and body text with the `source` contract (source="cockpit" for UI-initiated, source="agent" for agent-initiated, source="engine" for internal operations). (td:1)
5. Backward-compat reading: the session-derivation path in `engine.py` (`list_sessions`) must continue to accept old-format `actor`-keyed JSONL rows when `source` is absent. Do NOT delete the backward-compat logic. Existing tests in `test_engine_activity.py` (AC-C43) and `test_list_sessions.py` that exercise old-format rows must continue to pass. (td:1)
6. A structural import-inspection test asserts no module under `serve/kanban/src/owlbear_kanban/` imports `activity_log` (the deleted module). Pattern: AST walk or `importlib` source scan — follow the style in `tests/test_engine_accessor_migration.py`. (td:2)
7. If any skill or instruction doc mentions `actor` in the context of activity logging, update to `source`. (td:0)

## Key Files

- `serve/kanban/src/owlbear_kanban/activity_log.py` (to be deleted)
- `serve/kanban/src/owlbear_kanban/activity_store.py`
- `serve/kanban/src/owlbear_kanban/models.py` (ActivityEvent)
- `serve/kanban/src/owlbear_kanban/engine.py` (list_sessions backward-compat)
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `serve/cockpit/README.md` (audit-trail section)
- `tests/test_engine_activity_session.py`
- `serve/kanban/tests/test_engine_activity.py`
- `serve/kanban/tests/test_list_sessions.py`

## Builder Guidance

- AC2: Safe to delete — grep confirms zero production imports of `activity_log` module. Only `migrate.py` references the config key name `"activity_log"` (the boolean flag), not the module.
- AC5: The backward-compat read logic lives in engine's session derivation. It tolerates rows missing `source` by inferring from `actor` field. Preserve this — do not touch it.
- AC6: Model on `tests/test_engine_accessor_migration.py` which does AST-based import scanning.
- AC7: `doc-index.md` line 146 references `actor: "cockpit"` — this is auto-generated from README headings, will self-fix when AC4 lands.

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: unify activity attribution contract |
| Interface clarity | PASS | Source vocabulary explicitly enumerated, backward-compat preserved |
| Dependency correctness | PASS | #1348 archived (edit_task semantics finalized) |
| Module layering | PASS | Deletion only, no new dependencies introduced |
| TDD compliance | PASS | AC6 requires new structural test; existing suites cover remaining |
| KISS/YAGNI | PASS | Removes dead code, no new abstractions |
| Premise challenge | PASS | Legacy module genuinely dead (zero imports), stale docs confirmed |
| Pattern consistency | PASS | Import-inspection test follows existing accessor-migration pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban activity subsystem only |

### Challenge Results
- Challenger: reconsider (confidence 0.64)
- Architect response: accepted — refined AC1 field name (kind→action), narrowed AC2 to delete (not quarantine/deprecate), added explicit backward-compat preservation (AC5), specified proof type for import guard (AC6), scoped documentation targets (AC3/AC4)

### Test Depth
- Max depth: 2 (AC6)
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined all 7 AC lines with precise targets, added builder guidance section, moved to todo.

## Source

Meta-audit blind source pass, 2026-05-04.

[[2026-05-05]]
## Architecture Review

Refined AC from 5 → 7 lines after challenger reconsider (0.64). Key changes:
- Fixed field name error: `kind` → `action` in AC1
- Narrowed AC2: "delete" (not quarantine/deprecate) — zero production imports confirmed
- Added AC5: explicit backward-compat preservation for old actor-keyed JSONL rows
- Added AC6: structural import-inspection test (AST walk pattern from test_engine_accessor_migration.py)
- Scoped AC3/AC4 to specific files and sections
- Added Builder Guidance section with grep evidence and pattern references

All 10 architecture criteria PASS. Single domain (kanban activity). Dependency #1348 archived/complete.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_activity_attribution_cleanup_1352.py
- Classes: TestFromAC_ActivityLogDeletion, TestFromAC_SourceVocabularyDocumented, TestFromAC_CockpitReadmeAuditTrail, TestFromAC_ImportGuard
- Tests per category: happy 6, edge 0, error 0, boundary 0
- Total: 6 tests, all FAIL
- ruff: clean

## AC Coverage

| AC | Description | Test | Status |
|----|-------------|------|--------|
| AC1 | Canonical schema is ActivityEvent with source/action/task_id/detail/timestamp | (td:0) skip | — |
| AC2 | Delete activity_log.py; no module may import it | test_activity_log_module_not_importable | RED |
| AC3 | Source vocabulary engine\|agent\|cockpit in activity_store docstring | test_source_vocab_{engine,agent,cockpit}_in_docstring | RED (×3) |
| AC4 | Cockpit README audit-trail uses source, not actor | test_audit_trail_no_actor_cockpit_field | RED |
| AC5 | list_sessions accepts old actor-keyed JSONL rows | existing test_ac_c43_legacy_format_events_accepted_by_session_derivation in test_engine_activity.py (currently green — backward-compat already works; test-writer skip) | — |
| AC6 | AST import scan: no module imports activity_log | test_file_deleted_and_no_imports_remain (combined file-existence + AST walk; RED via file-existence guard) | RED |
| AC7 | Skill/instruction docs: actor → source | (td:0) skip | — |

## Failure evidence
- AC2: `Failed: DID NOT RAISE <class 'ImportError'>` (file still exists)
- AC3 ×3: `AssertionError: 'engine'/'agent'/'cockpit' source vocabulary must be documented`
- AC4: `AssertionError: README still contains actor: "cockpit"`
- AC6: `AssertionError: activity_log.py must be deleted`

## Notes
- AC5 covered by existing AC-C43 test in serve/kanban/tests/test_engine_activity.py; backward-compat read path already present in _read_log_entries (no source field required).
- AC6 uses a combined test: file-existence assertion makes it RED; AST scan runs after deletion as an ongoing structural guard (pattern from test_engine_accessor_migration.py).
[[2026-05-05]]
## Builder Notes
- Implementation: updated source attribution documentation in `serve/kanban/src/owlbear_kanban/activity_store.py` module docstring and `serve/cockpit/README.md` audit-trail section; deleted legacy module `serve/kanban/src/owlbear_kanban/activity_log.py`.
- RED verification: quality-runner scoped run on `tests/test_activity_attribution_cleanup_1352.py` showed 6 failing `TestFromAC_*` tests before implementation (AC2/AC3/AC4/AC6).
- GREEN verification: quality-runner scoped run passed with `124 passed, 0 failed` across `tests/test_activity_attribution_cleanup_1352.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_list_sessions.py`, and `serve/kanban/tests/test_activity_store.py`.
- Coverage: `owlbear_kanban.activity_store` at 92% (>=90 target).
- Lint: clean (ruff + markdownlint in scoped verification).
- Backward compatibility: AC5 preserved; existing legacy `actor`-row session derivation tests in `serve/kanban/tests/test_engine_activity.py` and `serve/kanban/tests/test_list_sessions.py` remained green.
- Commit: `c4e97628` (`fix: clean activity attribution contract (#1352, builder)`).

### Post-task Reflection
- `apply_patch` delete reported success while leaving the file on disk; validated filesystem state and used direct `rm` to complete AC2 safely.
- Scoped quality-runner with `test_activity_store` provided a reliable module-level coverage signal (92%) for the touched Python module.
- Keeping the change limited to docstrings/docs plus file deletion avoided any risk to AC5 backward-compat behavior in session derivation.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 124 passed, 0 failed, 0 skipped across tests/test_activity_attribution_cleanup_1352.py, serve/kanban/tests/test_engine_activity.py, serve/kanban/tests/test_list_sessions.py, and serve/kanban/tests/test_activity_store.py.

### Lint Results
- ruff clean on serve/kanban/src/owlbear_kanban/activity_store.py plus the four scoped test files.

### Coverage
- owlbear_kanban.activity_store: 92% line coverage.

### Scope Caveat
- Git diff and git status execution were unavailable in this session, so builder changed-file ownership, TestFromAC immutability, and dirty-tree cleanliness could not be proven from commit c4e97628. Current workspace inspection shows the deleted module is absent and the current task tests remain intact. Small confidence deduction applied.

### AC Compliance
| AC | Evidence | Status |
|---|---|---|
| 1 | Direct artifact proof only. serve/kanban/src/owlbear_kanban/models.py:525-535 defines ActivityEvent with timestamp, task_id, action, source, detail. Durable checks in serve/kanban/tests/test_engine_activity.py:174-236 assert required keys on fresh JSONL rows and assert no actor attribute on fresh parsed events. | PASS |
| 2 | serve/kanban/src/owlbear_kanban/activity_log.py is absent from the workspace. tests/test_activity_attribution_cleanup_1352.py:74-83 and 159-178 provide importability and file-deletion plus AST-guard coverage. | PASS |
| 3 | Current artifact is correct at serve/kanban/src/owlbear_kanban/activity_store.py:1-11, but task-local proof is weak: tests/test_activity_attribution_cleanup_1352.py:87-129 only checks substring presence for engine, agent, and cockpit. That would still pass on incidental wording that does not document the canonical source vocabulary contract. | FAIL |
| 4 | Current artifact is correct at serve/cockpit/README.md:84-86, but task-local proof is weak: tests/test_activity_attribution_cleanup_1352.py:134-148 only asserts that the stale phrase actor: "cockpit" is absent. It would still pass if the audit-trail section were removed or if one or more required source mappings were wrong or missing. | FAIL |
| 5 | Durable backward-compat proof remains green. serve/kanban/tests/test_engine_activity.py:468-500 writes old actor-keyed rows with no source and still derives one completed session. serve/kanban/tests/test_list_sessions.py:88-103 and 972-1006 preserve actor-keyed legacy fixtures and assert session.agent comes from detail, not actor. | PASS |
| 6 | Deletion plus structural guard are present in tests/test_activity_attribution_cleanup_1352.py:159-178, and current source inspection found no production import statements for activity_log under serve/kanban/src/owlbear_kanban. | PASS |
| 7 | Word-boundary search across share/skills, share/instructions, and .owlbear/instructions found no activity-logging actor references. The remaining actor hits are unrelated diagram or table terminology, not activity logging guidance. | PASS |

### Test Quality
| Dimension | Assessment | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC3 tests at tests/test_activity_attribution_cleanup_1352.py:87-129 only assert engine, agent, and cockpit substrings. AC4 at tests/test_activity_attribution_cleanup_1352.py:134-148 only bans one stale phrase. |
| Manual mutation resistance | WEAK | README proof would false-green if the section were present but incomplete. Docstring proof would false-green if the three words appeared incidentally without documenting the source contract. |
| Independence | ADEQUATE | Import cache is cleared before the ImportError assertion, and the file-deletion check is separated from the AST scan. |
| Naming | ADEQUATE | Test names are descriptive and mapped to the intended AC lines. |

### Security, Data Safety, Necessity
- No security, data-safety, or necessity defects found in the changed production scope.

### Deductions
- 0.04: AC3 proof is lax.
- 0.04: AC4 proof is lax.
- 0.02: Git diff or status unavailable for ownership and contamination verification.

### Verdict
- FAIL
- Confidence: 0.87
- Action: reject to todo for proof strengthening. Current implementation satisfies the contract on direct inspection, but the task-local proof is not strong enough for AC3 and AC4.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC3 assertions so the task test proves the activity_store module docstring documents the canonical source vocabulary contract, not just incidental word presence | tests/test_activity_attribution_cleanup_1352.py | tests/test_activity_attribution_cleanup_1352.py:87-129 and serve/kanban/src/owlbear_kanban/activity_store.py:1-11 |
| 2 | test-writer | Strengthen AC4 assertions so the task test proves the audit-trail section remains present and contains all three required source mappings for cockpit, agent, and engine | tests/test_activity_attribution_cleanup_1352.py, serve/cockpit/README.md | tests/test_activity_attribution_cleanup_1352.py:134-148 and serve/cockpit/README.md:84-86 |
[[2026-05-05]]
## Test-Writer Notes (retry)

**Step 1b.1 — Direct-to-Review Advance**

Reviewer Required Follow-up contained only test-proof gaps; no implementation fixes needed. All new tests PASS against current implementation — builder phase is unnecessary.

### Changes
- File: tests/test_activity_attribution_cleanup_1352.py
- Added 8 new tests to existing `TestFromAC_` classes (no existing tests touched)
- Commit: `8483fd3e`

### AC3 Strengthening (4 new tests)
- `test_source_vocab_docstring_has_vocabulary_section` — asserts "source vocabulary" header exists in docstring (structural proof of canonical contract, not incidental word)
- `test_source_vocab_engine_purpose_documented` — asserts "engine" + "internal" both present (purpose pairing)
- `test_source_vocab_agent_purpose_documented` — asserts "agent" + "agent-initiated" both present (purpose pairing)
- `test_source_vocab_cockpit_purpose_documented` — asserts "cockpit" + "ui" both present (purpose pairing)

### AC4 Strengthening (4 new tests)
- `test_audit_trail_section_present` — asserts "## Audit Trail" heading exists (section cannot be deleted and leave AC4 tests green)
- `test_audit_trail_source_cockpit_mapping_present` — asserts `source="cockpit"` appears in README
- `test_audit_trail_source_agent_mapping_present` — asserts `source="agent"` appears in README
- `test_audit_trail_source_engine_mapping_present` — asserts `source="engine"` appears in README

### Results
- 14 passed, 0 failed (was 14 passed pre-change; 6 original tests still green, 8 new tests green)
- ruff: clean
- All new tests PASS against current code → **builder has no work; advance directly to review**

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1 | (td:0) skip | — |
| AC2 | test_activity_log_module_not_importable | PASS |
| AC3 | 6 tests (3 original + 4 new, 1 overlap) | PASS (strengthened) |
| AC4 | 5 tests (1 original + 4 new) | PASS (strengthened) |
| AC5 | existing suites | PASS |
| AC6 | test_file_deleted_and_no_imports_remain | PASS |
| AC7 | (td:0) skip | — |
[[2026-05-05]]
## Builder Notes
- No implementation changes were required in this cycle.
- Reason: this is a test-only retry after reviewer feedback; test-writer strengthened proof assertions and reported builder-skip.
- Verification (quality-runner scoped): 132 passed, 0 failed, 0 skipped across:
  - tests/test_activity_attribution_cleanup_1352.py
  - serve/kanban/tests/test_engine_activity.py
  - serve/kanban/tests/test_list_sessions.py
  - serve/kanban/tests/test_activity_store.py
- Coverage: owlbear_kanban.activity_store = 92% (>=90 target).
- Lint: ruff clean on scoped paths.
- Files changed by builder: none.

### Post-task Reflection
- Builder-skip retries benefit from fresh quality-runner confirmation before advance, even when no source edits are needed.
- Scoped verification kept turnaround fast while still revalidating AC5 backward-compat regression risk.
- No additional risks observed; task is ready for reviewer validation.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 132 passed, 0 failed, 0 skipped across tests/test_activity_attribution_cleanup_1352.py, serve/kanban/tests/test_engine_activity.py, serve/kanban/tests/test_list_sessions.py, and serve/kanban/tests/test_activity_store.py.

### Lint: clean
- Ruff reported no violations on serve/kanban/src/owlbear_kanban/activity_store.py, tests/test_activity_attribution_cleanup_1352.py, serve/kanban/tests/test_engine_activity.py, serve/kanban/tests/test_list_sessions.py, and serve/kanban/tests/test_activity_store.py.

### Coverage
- owlbear_kanban.activity_store: 92%.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 (td:0) canonical ActivityEvent schema / no actor reintroduction | td:0 skip; verified in AC Compliance with direct artifact evidence and durable activity tests | N/A | SKIP |
| AC2 delete activity_log.py and keep it unimported | tests/test_activity_attribution_cleanup_1352.py:74 and tests/test_activity_attribution_cleanup_1352.py:275 | Yes | COVERED |
| AC3 document the engine/agent/cockpit source vocabulary in activity_store.py | tests/test_activity_attribution_cleanup_1352.py:132, 146, 163, 180 | No. A docstring with swapped source-to-purpose meanings would still satisfy these token and cue-word checks. | LAX |
| AC4 document the cockpit/agent/engine source mappings in the Cockpit Audit Trail section | tests/test_activity_attribution_cleanup_1352.py:217, 233, 245, 256 | No. A README with swapped or relocated source mappings would still satisfy the heading and token-presence checks. | LAX |
| AC5 preserve source-absent actor-keyed session derivation | serve/kanban/tests/test_engine_activity.py:468 and serve/kanban/tests/test_list_sessions.py:980 | Yes | COVERED |
| AC6 structural import-inspection guard for activity_log | tests/test_activity_attribution_cleanup_1352.py:275 | Yes | COVERED |
| AC7 (td:0) no activity-logging actor wording in skills/instructions | td:0 skip; verified by scoped searches in AC Compliance | N/A | SKIP |

#### Security Review
- No issues found in the changed production scope.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_SourceVocabularyDocumented | Added vocabulary-section and purpose-word assertions at tests/test_activity_attribution_cleanup_1352.py:132, 146, 163, 180 | STRENGTHENED |
| TestFromAC_CockpitReadmeAuditTrail | Added section-presence and exact source token assertions at tests/test_activity_attribution_cleanup_1352.py:217, 233, 245, 256 | STRENGTHENED |
| TestFromAC_ActivityLogDeletion / TestFromAC_ImportGuard | No weakening or removal visible in current artifacts | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC3 tests at tests/test_activity_attribution_cleanup_1352.py:132, 146, 163, 180 and AC4 tests at tests/test_activity_attribution_cleanup_1352.py:217, 233, 245, 256 assert section and token presence, but they do not bind each source value to its required meaning. |
| Negative or error-path coverage | ADEQUATE | The retry closes the prior section-removal and stale actor wording false-green. Deletion and legacy actor-row paths remain covered by existing structural and durable tests. |
| Manual mutation reasoning | WEAK | Swapping the cockpit/agent/engine explanatory clauses while keeping the same source tokens would leave the retry green for both AC3 and AC4. |
| Test independence | STRONG | The retry additions are pure file inspections. Durable AC5 coverage uses isolated tmp_path boards and explicit legacy JSONL fixtures. |
| Descriptive naming | STRONG | The retry method names and docstrings map directly to the intended AC lines. |

#### Data Safety
- No issues found in the changed production scope.

#### Implementation-Aware Gaps
- No significant untested changed-source paths found beyond the proof-quality issue above. Current production artifacts are correct on direct inspection; the blocking issue is that the task-local AC3 and AC4 assertions are still non-discriminating.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Commit presence is confirmed in .git/logs for builder commit c4e97628 and test-writer retry commit 8483fd3e.
- Git diff and git status were not available in this tool surface, so changed-file ownership and dirty-tree cleanliness could not be fully proven. Small confidence deduction applied.
- ActivityEvent still uses ConfigDict(extra="allow") at serve/kanban/src/owlbear_kanban/models.py:528, but the current canonical write path in serve/kanban/src/owlbear_kanban/engine.py:1837-1844 constructs ActivityEvent with explicit source/action/task_id/detail/timestamp fields only. I am treating that as residual robustness debt rather than an AC failure in this task.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | serve/kanban/src/owlbear_kanban/models.py:525-534 defines ActivityEvent with timestamp, task_id, action, source, and detail. serve/kanban/src/owlbear_kanban/engine.py:1837-1844 is the canonical write path and constructs ActivityEvent with those fields. Durable proofs in serve/kanban/tests/test_engine_activity.py:174-232 assert emitted events include source and do not expose actor on fresh writes. | serve/kanban/tests/test_engine_activity.py:174-232 | PASS |
| AC2 | serve/kanban/src/owlbear_kanban/activity_log.py is absent from the package directory, tests/test_activity_attribution_cleanup_1352.py:74 rejects importing it, and the structural guard at tests/test_activity_attribution_cleanup_1352.py:275 remains green. | tests/test_activity_attribution_cleanup_1352.py:74 and 275 | PASS |
| AC3 | The live artifact is correct at serve/kanban/src/owlbear_kanban/activity_store.py:8-11, but tests/test_activity_attribution_cleanup_1352.py:132, 146, 163, 180 only prove vocabulary-section and cue-word presence. They would still pass if the source values were documented with swapped meanings. | tests/test_activity_attribution_cleanup_1352.py:132, 146, 163, 180 | FAIL |
| AC4 | The live artifact is correct at serve/cockpit/README.md:84-86, but tests/test_activity_attribution_cleanup_1352.py:217, 233, 245, 256 only prove heading and source-token presence. They would still pass if the source meanings were swapped or the tokens moved outside the Audit Trail section. | tests/test_activity_attribution_cleanup_1352.py:217, 233, 245, 256 | FAIL |
| AC5 | serve/kanban/tests/test_engine_activity.py:468-500 proves source-absent actor-keyed rows still derive a session. serve/kanban/tests/test_list_sessions.py:88-105 and 955-1006 prove legacy rows are still accepted and session.agent is derived from detail rather than actor. serve/kanban/src/owlbear_kanban/engine.py:1911-1923 preserves the source-absent read path. | serve/kanban/tests/test_engine_activity.py:468-500 and serve/kanban/tests/test_list_sessions.py:88-105, 955-1006 | PASS |
| AC6 | tests/test_activity_attribution_cleanup_1352.py:275 performs the file-deletion and AST-walk guard, and a scoped source search found no `import` or `from ... import activity_log` matches under serve/kanban/src/owlbear_kanban. | tests/test_activity_attribution_cleanup_1352.py:275 | PASS |
| AC7 | Scoped searches across share/skills, share/instructions, and .owlbear/instructions found no activity-logging guidance that still uses actor terminology. The remaining actor hits are unrelated diagram or table terminology. | scoped search evidence | PASS |

### Confidence: 0.88
### Verdict: FAIL
- Action: reject to backlog. This is the second consecutive review failure on AC3 and AC4 proof quality, so the loop-breaker rule applies even though the live implementation is currently correct.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC3 proof requirements so the retry tests must bind each documented source value to its required purpose in activity_store.py, not just assert token presence anywhere in the docstring | tests/test_activity_attribution_cleanup_1352.py, serve/kanban/src/owlbear_kanban/activity_store.py | AC3 finding: tests/test_activity_attribution_cleanup_1352.py:132, 146, 163, 180 remain false-green under swapped mappings |
| 2 | architect | Refine AC4 proof requirements so the retry tests assert the cockpit, agent, and engine mappings inside the Audit Trail section with their correct UI, agent, and internal meanings | tests/test_activity_attribution_cleanup_1352.py, serve/cockpit/README.md | AC4 finding: tests/test_activity_attribution_cleanup_1352.py:217, 233, 245, 256 remain false-green under swapped or relocated mappings |
[[2026-05-05]]

## Architecture Refinement (AC3/AC4 proof requirements)

**Problem:** Two consecutive review cycles failed AC3 and AC4 because tests check independent token presence rather than binding each source value to its required purpose. Swapping the meanings of source values would leave all tests green.

**Refined AC3 proof requirement:**
> For each source value (`engine`, `agent`, `cockpit`), extract the single line from the `activity_store.__doc__` docstring that contains that value. Assert that the SAME LINE also contains the required purpose keyword: `engine` line must contain `"internal"`, `agent` line must contain `"agent-initiated"`, `cockpit` line must contain one of `"UI"` or `"ui"`. This prevents false-greens from swapped or misattributed mappings.

**Refined AC4 proof requirement:**
> Extract the text between the `## Audit Trail` heading and the next `##` heading in `serve/cockpit/README.md`. Within that section text only (not the whole file), assert each binding on the same line or within ≤80 characters: `source="cockpit"` must co-occur with `"UI-initiated"` (case-insensitive), `source="agent"` must co-occur with `"agent-initiated"`, `source="engine"` must co-occur with `"internal"`. The section heading assertion (already present) is retained.

**Test-writer instructions:** Replace the current independent token-presence assertions in `TestFromAC_SourceVocabularyDocumented` and `TestFromAC_CockpitReadmeAuditTrail` with per-line or per-proximity binding assertions as specified above. The existing tests that check section presence and stale-actor absence remain valid — only the positive binding proofs need rewriting.

**Builder:** No implementation changes needed — artifacts already satisfy the refined proof. This is test-only.

[[2026-05-05]]
## Architecture Review (AC3/AC4 refinement pass)

Refined AC3 and AC4 proof requirements to eliminate the false-green vulnerability identified in two consecutive review cycles. The underlying issue: tests asserted independent token presence rather than binding each source value to its purpose on the same line/proximity. Swapping source→purpose mappings would have left all tests green.

### Changes
- AC3: proof method now requires extracting the docstring line containing each source value and asserting the purpose keyword appears on that SAME line (engine→internal, agent→agent-initiated, cockpit→UI)
- AC4: proof method now requires extracting the Audit Trail section text and asserting each `source="X"` co-occurs with its purpose within ≤80 chars on the same line

### Rationale
No implementation changes needed — current artifacts (`activity_store.py` docstring lines 8-11, `serve/cockpit/README.md` line 84) already structure the mappings as per-line bindings. The test-writer only needs to rewrite the assertion strategy from independent token checks to per-line binding assertions.

### Verdict: APPROVE (refinement)
All 10 architecture criteria remain PASS from original review. This is a test-proof-quality refinement only — no architectural changes.
[[2026-05-05]]
## Test-Writer Notes (binding-assertion retry)

**Step 1b.2 — Direct-to-Review Advance**

Architect refinement pass (AC3/AC4 proof requirements) specified per-line binding assertions. Implementation artifacts already satisfy the refined proof — builder phase unnecessary. All new tests PASS against current code.

### Changes
- File: tests/test_activity_attribution_cleanup_1352.py
- Commit: `3f8643f6`
- Added `import re` + `_extract_audit_trail_section()` module-level helper
- **Replaced** 6 weak independent-token tests with per-line binding versions

### AC3 binding (3 tests replaced)
- `test_source_vocab_engine_purpose_documented` — finds lines with `"``engine``"`, asserts `"internal"` on the **same line** (prevents engine→agent-initiated swap)
- `test_source_vocab_agent_purpose_documented` — finds lines with `"``agent``"`, asserts `"agent-initiated"` on the same line (prevents agent→internal swap)
- `test_source_vocab_cockpit_purpose_documented` — finds lines with `"``cockpit``"`, asserts `"ui"` on the same line (prevents cockpit→engine swap)

### AC4 binding (3 tests replaced)
- `test_audit_trail_source_cockpit_mapping_present` — extracts Audit Trail section body only, finds lines with `source="cockpit"`, asserts `"ui-initiated"` on the same line
- `test_audit_trail_source_agent_mapping_present` — section-scoped, asserts `"agent-initiated"` co-occurs with `source="agent"` on the same line
- `test_audit_trail_source_engine_mapping_present` — section-scoped, asserts `"internal"` co-occurs with `source="engine"` on the same line

### Why these resist swaps
- Purpose swap (engine↔agent): `"``engine``"` line check + `"internal"` on same line fails when engine's line reads "agent-initiated"
- Cross-section relocation: `_extract_audit_trail_section()` scopes to section body only — tokens in other README sections do not satisfy assertions

### Results
- 14 passed, 0 failed (all 14 tests green — current implementation satisfies refined proof)
- ruff: clean

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1 | (td:0) skip | — |
| AC2 | test_activity_log_module_not_importable | PASS |
| AC3 | 7 tests (4 original + 3 binding replacements) | PASS (binding) |
| AC4 | 5 tests (2 original + 3 section-scoped binding replacements) | PASS (binding) |
| AC5 | existing suites | PASS |
| AC6 | test_file_deleted_and_no_imports_remain | PASS |
| AC7 | (td:0) skip | — |

**Builder: pass-through to review — no implementation changes needed.**
[[2026-05-05]]
## Builder Notes
- No implementation changes were required in this cycle.
- Reason: this is a test-only retry after architecture/test-proof refinement; implementation artifacts already satisfy the refined AC3/AC4 binding requirements.
- Verification (quality-runner scoped): 132 passed, 0 failed, 0 skipped across:
  - tests/test_activity_attribution_cleanup_1352.py
  - serve/kanban/tests/test_engine_activity.py
  - serve/kanban/tests/test_list_sessions.py
  - serve/kanban/tests/test_activity_store.py
- Coverage: owlbear_kanban.activity_store = 92% (>=90 target).
- Lint: ruff clean on scoped paths.
- Files changed by builder: none.

### Post-task Reflection
- Fresh scoped verification remains valuable for builder-skip retries because it reconfirms AC5 legacy-path safety with current workspace state.
- No source edits reduced risk of unintended regression while still producing objective gate evidence.
- Scoped quality-runner evidence was sufficient to advance confidently without running broad-suite checks.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 132 passed, 0 failed, 0 errors across `tests/test_activity_attribution_cleanup_1352.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_list_sessions.py`, and `serve/kanban/tests/test_activity_store.py`.

### Lint Results
- Ruff clean on `serve/kanban/src/owlbear_kanban/activity_store.py` and the four scoped test files.

### Coverage
- `owlbear_kanban.activity_store`: 92% line coverage.

### Scope Caveat
- Commit presence is confirmed in `.git/logs` for builder commit `c4e97628` and test-writer retry commits `8483fd3e` and `3f8643f6`.
- `git diff` / `git status` were not available in this tool surface, so dirty-tree cleanliness and diff-level TestFromAC immutability could not be fully proven. Small confidence deduction applied.

### Pass 1 — Critical Checks
- Code-reader found no blocking security, data-safety, necessity, or implementation-gap issues in the current scope.
- The prior AC3/AC4 false-green is now closed: the task tests bind each source value to its required meaning on the same line, and the README checks are scoped to the Audit Trail section.
- AC6 structural proof is adequate for the current package layout: `serve/kanban/src/owlbear_kanban/` is a flat module directory, so the AST helper's top-level `*.py` scan covers the live module set.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/kanban/src/owlbear_kanban/models.py:525-534` defines `ActivityEvent` with `timestamp`, `task_id`, `action`, `source`, and `detail`; `serve/kanban/src/owlbear_kanban/engine.py:1837-1844` writes those fields on the canonical path. Durable checks at `serve/kanban/tests/test_engine_activity.py:174`, `:189`, and `:214` confirm fresh activity rows carry `source` and do not reintroduce legacy actor-shaped fresh writes. | `serve/kanban/tests/test_engine_activity.py:174`, `:189`, `:214` | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/activity_log.py` is absent. Task tests reject importing the deleted module at `tests/test_activity_attribution_cleanup_1352.py:95` and enforce deletion plus no surviving imports at `:343`. Scoped source search under `serve/kanban/src/owlbear_kanban/` found no production import of `activity_log`. | `tests/test_activity_attribution_cleanup_1352.py:95`, `:343` | PASS |
| AC3 | The canonical source vocabulary is documented directly in `serve/kanban/src/owlbear_kanban/activity_store.py:8-11`. The retry tests now prove the per-value binding: `tests/test_activity_attribution_cleanup_1352.py:167` (`engine` + `internal` same line), `:189` (`agent` + `agent-initiated`), and `:211` (`cockpit` + UI marker). | `tests/test_activity_attribution_cleanup_1352.py:167`, `:189`, `:211` | PASS |
| AC4 | The Audit Trail contract is documented in `serve/cockpit/README.md:84-86`. The retry tests scope to the Audit Trail section and bind each source token to its required meaning at `tests/test_activity_attribution_cleanup_1352.py:267` (`source="cockpit"` + UI-initiated), `:291` (`source="agent"` + agent-initiated), and `:313` (`source="engine"` + internal). | `tests/test_activity_attribution_cleanup_1352.py:267`, `:291`, `:313` | PASS |
| AC5 | Backward-compatible reads remain intact. `serve/kanban/src/owlbear_kanban/engine.py:1907-1928` still accepts rows that only contain `action`, `task_id`, `detail`, and `timestamp`, so `source` remains optional on read. Durable proof stays green in `serve/kanban/tests/test_engine_activity.py:468` and in actor-keyed list-sessions fixtures at `serve/kanban/tests/test_list_sessions.py:89`, with `detail`-over-actor derivation asserted at `:955` and `:980`. | `serve/kanban/tests/test_engine_activity.py:468`; `serve/kanban/tests/test_list_sessions.py:89`, `:955`, `:980` | PASS |
| AC6 | `tests/test_activity_attribution_cleanup_1352.py:343` performs the two-phase file-deletion plus AST-walk guard. Current package layout inspection shows no nested subpackages under `serve/kanban/src/owlbear_kanban/`, so the helper's `glob("*.py")` scan covers all live production modules. | `tests/test_activity_attribution_cleanup_1352.py:343` | PASS |
| AC7 | Scoped searches across `share/skills/**`, `share/instructions/**`, and `.owlbear/instructions/**` found no activity-logging guidance that still uses `actor` terminology. Remaining `actor` hits are unrelated words such as `refactor`, diagram terminology, or `factories`, not activity logging guidance. | scoped search evidence | PASS |

### Informational
- `tests/test_activity_attribution_cleanup_1352.py` still imports `importlib.util` even though the current file state does not use it. Ruff did not flag this in the scoped run, so this is non-blocking.
- The AC6 AST helper is sufficient for today's flat package layout. If `owlbear_kanban` grows subpackages later, making the scan recursive would future-proof the guard.

### Deductions
- 0.05: no `git diff` / `git status` visibility in this tool surface; commit presence is proven, but dirty-tree and diff-level immutability are not.

### Verdict
- PASS
- Confidence: 0.95
- Action: advance to docs.
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified | `serve/cockpit/README.md:84-86` has correct `## Audit Trail — source Attribution Contract` heading and all three source mappings. `activity_store.py:1-11` module docstring verified accurate with canonical vocabulary. |
| 2 | Module docstrings | Yes | Verified | `serve/kanban/src/owlbear_kanban/activity_store.py` module docstring documents all three source values (engine/agent/cockpit) with purposes. No new public classes/functions were added. |
| 3 | External attribution | No | N/A | No external patterns referenced in builder notes. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (also describes `serve/kanban/src/**`) — footers updated from `(89641691)` → `2026-05-05 (60168ef3)`. Doc-index regenerated: heading updated from `actor: "cockpit"` to `source Attribution Contract`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | Yes | N/A | `activity_log.py` deleted. Scanned all IN-scope docs (all `serve/*/README.md`, root `README.md`, `SECURITY.md`) — zero references to `activity_log` found. No orphaned IN-scope doc requires child task. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/src/owlbear_kanban/activity_store.py | IN | Docstring verified accurate |
| serve/kanban/src/owlbear_kanban/activity_log.py | IN (deleted) | No IN-scope doc references it |
| serve/cockpit/README.md | IN | Prose verified accurate |
| share/diagrams/kanban.excalidraw | IN | Footer updated |
| share/diagrams/mcp-topology.excalidraw | IN | Footer updated |
| .owlbear/doc-index.md | IN | Regenerated |
| tests/test_activity_attribution_cleanup_1352.py | OUT | Test file |
| serve/kanban/tests/ (3 files) | OUT | Test files |

### Files Updated
- share/diagrams/kanban.excalidraw (footer: 89641691 → 60168ef3)
- share/diagrams/mcp-topology.excalidraw (footer: 89641691 → 60168ef3)
- .owlbear/doc-index.md (regenerated; Audit Trail heading updated)
- Commit: 4fa209ad

### Child Tasks Created
- None

### Scratch Files Cleaned
- .owlbear/scratch/1352-pytest-run.txt
- .owlbear/scratch/1352-pytest-scoped.log
- .owlbear/scratch/1352-pytest.log
- .owlbear/scratch/1352-pytest.txt
- .owlbear/scratch/1352-ruff.json
- .owlbear/scratch/1352-ruff.log
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | models.py:525-534 defines ActivityEvent with source/action/task_id/detail/timestamp. Durable tests in test_engine_activity.py assert no actor on fresh writes. | PASS |
| AC2 | activity_log.py absent from filesystem. Task tests at :95 and :343 enforce deletion + no imports. | PASS |
| AC3 | activity_store.py:8-11 documents source vocabulary with per-line bindings. Tests at :167/:189/:211 assert each source value co-occurs with its purpose on the same line. | PASS |
| AC4 | cockpit README:84-86 has Audit Trail section with correct source contract. Tests at :267/:291/:313 scope to section and bind each source to purpose. | PASS |
| AC5 | engine.py:1907-1928 preserves source-absent read path. Durable tests in test_engine_activity.py:468 and test_list_sessions.py:89/:955/:980 prove legacy actor-keyed rows still derive sessions. | PASS |
| AC6 | test_activity_attribution_cleanup_1352.py:343 file-deletion + AST-walk guard green. No production imports of activity_log found in flat package. | PASS |
| AC7 | Scoped searches across share/skills, share/instructions, .owlbear/instructions found no activity-logging actor references. | PASS |

### Test Results
- Task-scoped: 132 passed, 0 failed
- Full suite: 4590 passed, 213 failed (all failures in unrelated modules: test_migrate, test_corruption, test_engine_coverage_1068, etc.)
- Lint (ruff): clean on task scope

### Architect Quality: 4/5
Good specificity after refinement pass. Minor gap: original AC3/AC4 proof requirements were too weak (required 2 review cycles to fix), but architect responded promptly with binding-assertion refinement.

### Deduction Breakdown
- 0.00: all AC lines have specific evidence
- 0.00: lint clean
- 0.00: AC quality 4/5 (no deduction)
- 0.00: reviewer evidence present and detailed
- 0.00: no full-suite failures in task scope
- -0.02: git diff/status unavailable for dirty-tree verification (carried from reviewer)

### Confidence: 0.98
### Action: archive