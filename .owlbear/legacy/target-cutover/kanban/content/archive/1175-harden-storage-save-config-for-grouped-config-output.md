---
id: 1175
title: Harden storage.save_config for grouped config output
status: archived
priority: medium
created: 2026-04-28T23:07:11.208593+00:00
updated: 2026-04-29T05:31:32.215842+00:00
tags:
- scope:kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

storage.save_config (L236-260) uses a hardcoded legacy-key strip list that will break when BoardConfig gains nested sub-models (#1155). Also silently strips defaults — a key the engine still reads (defaults.priority at engine.py L936).

See `.owlbear/research/1171-config-write-path-audit.md` §4 Step 2.

## Acceptance Criteria

1. Replace hardcoded pop-loop with `model_dump(exclude=...)` denylist of dead-only keys (`board`, `version`); new model fields are emitted automatically without code changes (td:2)
2. Add test proving nested dict values (e.g. `defaults` sub-model) survive save/load round-trip (td:2)
3. Verify frozenset-to-list conversion works at nested depth via recursive walker (td:2)
4. `defaults.priority` and `activity_log` are preserved through a `save_config` → `load_config` cycle (td:1)

## Decision Resolved

**Decision:** A: Retry when GitHub service recovers

**Reasoning:** GitHub service disruptions are transient; the researcher is stateless and can cleanly retry. Retrying when service recovers preserves research context and is the natural path forward.
[[2026-04-29]]

## Research

- Research doc: .owlbear/research/1175-save-config-hardening.md
- Sources: 9 studied, 6 high-relevance (internal); 1 external (Pydantic v2 model_dump — already in sources/overview.md)
- Recommendation: Approach A — model_dump(exclude=_LEGACY_WRITE_EXCLUDE) + recursive frozenset walker (confidence: .75)
- Follow-up tasks created: none — AC is well-specified, single T1 implementation task
- Decision requests: none

## Challenge Results

- Challenger: reconsider (confidence in original: .58)
- Key challenges: activity_log runtime dep confirmed, migration contract divergence acknowledged, confidence lowered from .85 to .75
- Researcher response: accepted — activity_log added to preserved fields, migration divergence documented as acceptable (#1170 synchronization path)

## Validation Pass (2026-04-29)

Verified all findings against current codebase:

- defaults stripped (storage.py L253) → defaults.priority read (engine.py L936) — confirmed
- activity_log stripped (storage.py L253) → config.activity_log read (engine.py L459) — confirmed
- Frozenset top-level only (storage.py L256-257) — confirmed
- migrate._LEGACY_CONFIG_KEYS includes defaults+activity_log (migrate.py L65-72) — confirmed divergence
[[2026-04-29]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single function hardening (save_config) |
| Interface clarity | PASS | AC specifies dead-key denylist, round-trip preservation, recursive walker |
| Dependency correctness | PASS | No deps needed; #1155 benefits from nested handling but doesn't block; #1170 (archived research) is a separate concern |
| Module layering | PASS | Change stays in storage.py; engine.py consumers unchanged |
| TDD compliance | PASS | Will go through test-writer for RED phase |
| KISS/YAGNI | PASS | Recursive walker is ~8 LOC, handles existing frozenset field (archival_reasons) and prepares for nested sub-models in #1155 |
| Premise challenge | PASS | Real bug — defaults.priority and activity_log silently lost after save_config cycle |
| Pattern consistency | PASS | model_dump(exclude=) is standard Pydantic v2 pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | kanban storage domain only |

### Challenge Results

- Challenger: block (confidence 0.43)
- Key concerns: (1) migration contract regression — save_config preserving defaults/activity_log would break _is_config_migrated; (2) stale #1170 reference; (3) AC1 allowlist/denylist ambiguity
- Architect response: (1) REBUTTED — save_config output already fails_is_config_migrated due to tasks_dir/archive_dir (both _LEGACY_CONFIG_KEYS, never stripped). Adding defaults/activity_log doesn't change the outcome. Migration and persistence are separate operations. (2) ACCEPTED — removed stale #1170 reference from AC4. (3) ACCEPTED — refined AC1 to explicitly specify denylist approach with dead keys.

### AC Refinements

- AC1: Replaced vague "model-driven field emission (e.g. model_fields allowlist)" with specific "model_dump(exclude=...) denylist of dead-only keys (board, version)"
- AC4: Removed stale #1170 reference; made explicit that both defaults.priority AND activity_log must survive the cycle
- All AC lines annotated with test depth

### Test Depth

- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE

### Action Taken: Refined AC for clarity, removed stale #1170 ref, advanced to todo

[[2026-04-29]]

## Test-Writer Notes

- Test file: tests/test_storage_1175.py
- Classes: TestFromAC_SaveConfigHardening
- Tests per category: happy 5, edge 3, error 2, boundary 0
- Total: 10 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests | Failure reason |
|----|-------|---------------|
| AC1 (td:2) | test_ac1_defaults_present_in_yaml_output, test_ac1_activity_log_present_in_yaml_output, test_ac1_denylist_limited_to_board_and_version_only | AssertionError — defaults/activity_log absent from YAML (stripped by pop-loop) |
| AC2 (td:2) | test_ac2_defaults_priority_non_default_survives_roundtrip, test_ac2_defaults_status_non_default_survives_roundtrip, test_ac2_defaults_is_dict_with_expected_keys_in_yaml_output | AssertionError — round-tripped values revert to model defaults |
| AC3 (td:2) | test_ac3_nested_frozenset_in_extra_field_saves_without_error, test_ac3_nested_frozenset_converted_to_sorted_list, test_ac3_deeply_nested_frozenset_recursive_conversion | RepresenterError (nested frozensets not converted) or AssertionError |
| AC4 (td:1) | test_ac4_defaults_priority_and_activity_log_preserved_through_cycle | AssertionError — both fields stripped |

### Design notes

- AC3 tests use `__pydantic_extra__` injection to place frozensets at nested depth (extra_section.nested_frozen, level_one.level_two.deep_frozen). These are NOT in the current pop-loop denylist, so model_dump() includes them, triggering ruamel.yaml RepresenterError — clean failure mode.
- test_ac3_nested_frozenset_converted_to_sorted_list uses defaults sub-model injection; fails because defaults is stripped by current code (data["defaults"] is None). After builder fix: defaults preserved + recursive walker converts nested frozenset → passes.
[[2026-04-29]]

## Builder Notes

- Implementation: updated save_config in serve/kanban/src/owlbear_kanban/storage.py to use model_dump(exclude={board,version}) and recursive YAML-safety conversion for nested frozenset values.
- Files changed: serve/kanban/src/owlbear_kanban/storage.py
- Commit: 3b04581e (fix: harden save_config grouped output (#1175, builder))
- Tests (task-scoped): 10 TestFromAC tests passed in tests/test_storage_1175.py (failed before implementation, all green after).
- Lint (scoped): clean (ruff violations: 0) for serve/kanban/src/owlbear_kanban/storage.py and tests/test_storage_1175.py.
- Coverage: scoped quality-runner report for owlbear_kanban.storage = 27% (module-wide metric over large legacy module); task-owned acceptance tests are fully green.
- Durable module baseline check: serve/kanban/tests/test_storage.py remains 2 passed / 9 failed with same pre-existing ConfigError agent_map fixture mismatch signature; no delta introduced by this change.
- Evidence summary: AC1/AC2/AC4 satisfied by preserving defaults and activity_log through save/load; AC3 satisfied by recursive nested frozenset->sorted list conversion in dict/list/tuple structures.
- Fixes applied during verification: adjusted helper annotation from Any to object to satisfy ANN401 lint rule.

## Reflection

- Problems faced: scoped coverage threshold on full storage module is low due to broad untouched code surface.
- Workaround applied: used task-scoped TestFromAC + scoped lint as gate evidence and recorded module-wide coverage context explicitly.
- Pattern discovered: replacing hardcoded drop-lists with denylist + model_dump avoids future schema drift and data loss regressions.
[[2026-04-29]]

## Review Evidence

### Test Results

- pytest: 10 passed, 0 failed (`tests/test_storage_1175.py`)

### Lint

- ruff: clean for `serve/kanban/src/owlbear_kanban/storage.py` and `tests/test_storage_1175.py`

### Coverage

- `owlbear_kanban.storage`: 27%

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: denylist of dead-only keys; new model fields emitted automatically | `test_ac1_defaults_present_in_yaml_output`, `test_ac1_activity_log_present_in_yaml_output`, `test_ac1_denylist_limited_to_board_and_version_only` | Partially. Current assertions in `tests/test_storage_1175.py:103-107` would catch `defaults`/`activity_log` stripping and `board`/`version` leakage, but they would stay green if `save_config()` regressed to a hand-maintained allowlist that still emitted today's fields. Implementation uses `model_dump(exclude=_CONFIG_WRITE_EXCLUDE)` at `serve/kanban/src/owlbear_kanban/storage.py:249`, but the future-proof part of the AC is not executably pinned. | LAX |
| AC2: nested dict values survive round-trip | `test_ac2_defaults_priority_non_default_survives_roundtrip`, `test_ac2_defaults_status_non_default_survives_roundtrip`, `test_ac2_defaults_is_dict_with_expected_keys_in_yaml_output` | Yes. Exact round-trip assertions at `tests/test_storage_1175.py:126` and `tests/test_storage_1175.py:141` would fail if nested defaults values were dropped or reverted. | COVERED |
| AC3: frozenset-to-list conversion works at nested depth via recursive walker | `test_ac3_nested_frozenset_in_extra_field_saves_without_error`, `test_ac3_nested_frozenset_converted_to_sorted_list`, `test_ac3_deeply_nested_frozenset_recursive_conversion` | No for the full recursive-walker contract. The helper adds dict/list/tuple recursion at `serve/kanban/src/owlbear_kanban/storage.py:263-267`, but task tests only inject dict-shaped nested frozensets at `tests/test_storage_1175.py:177`, `tests/test_storage_1175.py:193`, and `tests/test_storage_1175.py:213`. Removing the list or tuple branches at `serve/kanban/src/owlbear_kanban/storage.py:264` or `serve/kanban/src/owlbear_kanban/storage.py:266` would leave the suite green. | MISSING |
| AC4: `defaults.priority` and `activity_log` preserved through cycle | `test_ac4_defaults_priority_and_activity_log_preserved_through_cycle` | Yes. Exact assertions at `tests/test_storage_1175.py:239-240` would fail if either field were lost or defaulted on reload. | COVERED |

#### Security Review

- No issues found. The scoped change is local config serialization in `serve/kanban/src/owlbear_kanban/storage.py:237-267` and introduces no shell, SQL, path, or deserialization sink.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_SaveConfigHardening` | No visible weakening in the current task-owned assertions; current checks remain direct key/equality assertions. Builder-reported scope excludes the test file. | PRESERVED (scoped evidence) |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Direct key presence and exact equality assertions at `tests/test_storage_1175.py:103-107`, `:126`, `:141`, `:197`, `:218`, `:239-240` |
| Negative/error-path coverage | ADEQUATE | `test_ac3_nested_frozenset_in_extra_field_saves_without_error` proves the old RepresenterError symptom no longer occurs (`tests/test_storage_1175.py:163`) |
| Manual mutation reasoning | WEAK | Breaking the new list/tuple recursion branches at `serve/kanban/src/owlbear_kanban/storage.py:264` and `:266` would not fail any current test because every AC3 input is dict-shaped (`tests/test_storage_1175.py:177`, `:193`, `:213`) |
| Test independence | STRONG | Each case provisions a fresh board via `_make_board()` in `tests/test_storage_1175.py:44-51` |
| Descriptive names | STRONG | AC-tagged, behavior-specific test names throughout `tests/test_storage_1175.py:71-224` |

#### Data Safety

- No issues found. Atomic write remains in place at `serve/kanban/src/owlbear_kanban/storage.py:255`, and `_yaml_safe_value()` is a pure value transformer.

#### Implementation-Aware Test Gaps

- Significant untested path: sequence recursion in `_yaml_safe_value()` at `serve/kanban/src/owlbear_kanban/storage.py:264` and `:266`.
- Secondary proof gap: AC1's "new model fields are emitted automatically" clause is implemented by `model_dump(exclude=...)` at `serve/kanban/src/owlbear_kanban/storage.py:249`, but current tests only prove survival of today's known live keys.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/kanban/src/owlbear_kanban/storage.py:206`, `:249`; `tests/test_storage_1175.py:71-107` | AC1 trio | FAIL (proof gap: future-field emission not pinned) |
| AC2 | `serve/kanban/src/owlbear_kanban/storage.py:249`; `tests/test_storage_1175.py:113-157` | AC2 trio | PASS |
| AC3 | `serve/kanban/src/owlbear_kanban/storage.py:258-267`; `tests/test_storage_1175.py:163-218` | AC3 trio | FAIL (list/tuple recursion branches untested) |
| AC4 | `serve/kanban/src/owlbear_kanban/models.py:180-181`; `serve/kanban/src/owlbear_kanban/engine.py:459`; `serve/kanban/src/owlbear_kanban/engine.py:936`; `tests/test_storage_1175.py:224-240` | AC4 test | PASS |

### Deductions

- `-0.08` AC3 branch-specific proof missing for newly added list/tuple recursion paths.
- `-0.05` AC1 future-proof contract is implemented but not executably proven.
- `-0.03` Coverage on touched module remains 27%, which matches the missing helper-branch proof.

### Verdict

- FAIL -> `todo`
- Confidence: 0.84

### Action

- Return to test-writer. Add task-owned proof that nested frozensets inside list and tuple containers are converted correctly by `_yaml_safe_value()`.
- Strengthen AC1 with an executable proof of automatic field emission, e.g. preserving an injected extra field through `save_config()` rather than only checking today's known live keys.

### Reflection

- The implementation itself appears consistent with the AC; the remaining delta is executable proof, not source behavior.
- Low module-level coverage was useful as a signal here because it matched the untested helper branches rather than unrelated lint or suite noise.
- Routing to `todo` preserves the builder's fix and avoids sending a test-only delta back to implementation.
[[2026-04-29]]

## Test-Writer Notes

- Test file: tests/test_storage_1175.py
- Classes: TestFromAC_SaveConfigHardening
- Tests per category: happy 6, edge 4, error 3, boundary 0
- Total: 13 tests, all PASS (retry — builder fix already in place)
- ruff: clean

### Retry changes (reviewer gaps addressed)

| Gap | New Test | Contract pinned |
|-----|----------|-----------------|
| AC3 list branch untested | `test_ac3_frozenset_in_list_container_is_converted` | frozensets inside list elements are recursively sorted; removing list branch → RepresenterError |
| AC3 tuple branch untested | `test_ac3_frozenset_in_tuple_container_is_converted` | frozensets inside tuple elements converted; removing tuple branch → RepresenterError |
| AC1 future-field emission not pinned | `test_ac1_new_field_not_in_denylist_is_emitted_automatically` | extra/unknown field survives save_config via denylist mechanism |

### AC Coverage (updated)

| AC | Tests | Status |
|----|-------|--------|
| AC1 (td:2) | ac1 trio + `test_ac1_new_field_not_in_denylist_is_emitted_automatically` | COVERED — denylist mechanism proved by extra-field survival |
| AC2 (td:2) | ac2 trio | COVERED |
| AC3 (td:2) | ac3 trio + `test_ac3_frozenset_in_list_container_is_converted` + `test_ac3_frozenset_in_tuple_container_is_converted` | COVERED — all three recursive branches (dict/list/tuple) now have explicit proof |
| AC4 (td:1) | ac4 test | COVERED |

### Note on test state

Retry cycle: builder's implementation (commit 3b04581e) was already in place. All 13 tests pass against current code. The 3 new tests would have failed (RepresenterError for AC3; allowlist regression for AC1) against pre-builder code. Builder pass-through expected — no source changes needed.
[[2026-04-29]]

## Builder Notes

- Implementation: no additional source changes required in this retry cycle; existing builder implementation in serve/kanban/src/owlbear_kanban/storage.py satisfies updated AC-proof tests.
- Files changed: none (builder pass-through after test-writer proof expansion).
- Tests: 13 TestFromAC tests passed in tests/test_storage_1175.py.
- Coverage: 27% on owlbear_kanban.storage (module-wide legacy surface; task-scoped acceptance tests are fully green).
- ruff: clean for serve/kanban/src/owlbear_kanban/storage.py and tests/test_storage_1175.py.
- Evidence summary: updated AC1/AC3 proof tests (extra-field emission + list/tuple nested frozenset recursion) now pass against current implementation.

## Reflection

- Problem faced: retry entered GREEN with strengthened tests already passing against existing implementation.
- Workaround applied: performed scoped quality-runner verification and advanced with evidence-only pass-through.
- Pattern discovered: reviewer proof-gap loops can legitimately resolve with test-only deltas; builder should avoid unnecessary source churn.
[[2026-04-29]]

## Review Evidence

### Test Results

- pytest: 13 passed, 0 failed for tests/test_storage_1175.py

### Lint

- ruff: clean for serve/kanban/src/owlbear_kanban/storage.py and tests/test_storage_1175.py

### Coverage

- owlbear_kanban.storage: 27%
- Quality-runner reports the missing lines in broad untouched legacy regions of storage.py outside the reviewed save_config path. The changed save_config logic and each new recursive helper branch are directly pinned by task-owned tests, so the low module-wide percentage is noted but not blocking.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: model_dump(exclude=...) denylist limited to board and version; new fields emitted automatically | test_ac1_defaults_present_in_yaml_output, test_ac1_activity_log_present_in_yaml_output, test_ac1_denylist_limited_to_board_and_version_only, test_ac1_new_field_not_in_denylist_is_emitted_automatically | Yes. The denylist is defined at serve/kanban/src/owlbear_kanban/storage.py:206 and applied at serve/kanban/src/owlbear_kanban/storage.py:249. The canary assertions at tests/test_storage_1175.py:278-279 fail if an allowlist or hardcoded pop loop drops a future field. | COVERED |
| AC2: nested dict values survive save and load round-trip | test_ac2_defaults_priority_non_default_survives_roundtrip, test_ac2_defaults_status_non_default_survives_roundtrip, test_ac2_defaults_is_dict_with_expected_keys_in_yaml_output | Yes. Exact assertions at tests/test_storage_1175.py:126, tests/test_storage_1175.py:141, and the YAML shape check at tests/test_storage_1175.py:155-157 fail if defaults values are dropped or flattened. | COVERED |
| AC3: frozenset to list conversion works at nested depth via recursive walker | test_ac3_nested_frozenset_converted_to_sorted_list, test_ac3_deeply_nested_frozenset_recursive_conversion, test_ac3_frozenset_in_list_container_is_converted, test_ac3_frozenset_in_tuple_container_is_converted | Yes. The helper branches at serve/kanban/src/owlbear_kanban/storage.py:260-266 are each exercised by exact emitted-value assertions at tests/test_storage_1175.py:197, tests/test_storage_1175.py:218, tests/test_storage_1175.py:239, and tests/test_storage_1175.py:260. | COVERED |
| AC4: defaults.priority and activity_log are preserved through the cycle | test_ac4_defaults_priority_and_activity_log_preserved_through_cycle | Yes. Exact round-trip assertions at tests/test_storage_1175.py:300-301 fail if either value is lost. These fields remain live runtime inputs at serve/kanban/src/owlbear_kanban/engine.py:459 and serve/kanban/src/owlbear_kanban/engine.py:936, with the default activity_log declared at serve/kanban/src/owlbear_kanban/models.py:181. | COVERED |

#### Security Review

- No issues found. The reviewed change is local serialization and YAML normalization in serve/kanban/src/owlbear_kanban/storage.py:237-266 and adds no shell, SQL, template, path, or unsafe deserialization sink.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_SaveConfigHardening | Retry cycle strengthened proof with test_ac3_frozenset_in_list_container_is_converted, test_ac3_frozenset_in_tuple_container_is_converted, and test_ac1_new_field_not_in_denylist_is_emitted_automatically. Builder retry notes report no changed files, and current assertions remain exact-value checks. | STRENGTHENED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact equality and exact key-presence assertions at tests/test_storage_1175.py:126, 141, 197, 218, 239, 260, 278-279, 300-301 |
| Negative and error-path coverage | ADEQUATE | test_ac3_nested_frozenset_in_extra_field_saves_without_error covers the prior RepresenterError failure mode, and stronger sibling AC3 tests verify the emitted serialized values |
| Manual mutation reasoning | STRONG | Removing list or tuple recursion at serve/kanban/src/owlbear_kanban/storage.py:264 or :266 now breaks tests/test_storage_1175.py:239 or :260; replacing model_dump exclude logic at :249 breaks tests/test_storage_1175.py:278-279 |
| Test independence | STRONG | Each case provisions a fresh tmp_path board through_make_board() |
| Descriptive names | STRONG | AC-tagged behavior-specific test names throughout tests/test_storage_1175.py |

#### Data Safety

- No issues found. Atomic write remains in place at serve/kanban/src/owlbear_kanban/storage.py:251-255 and the new helper is a pure recursive value transformer.

#### Implementation-Aware Gaps

- No blocking significant path gap remains in the reviewed change. Dict, list, and tuple recursion plus frozenset sorting each have direct executable proof.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL

- One prior review failure is recorded at .owlbear/kanban/tasks/1175-harden-storage-save-config-for-grouped-config-output.md:124. The retry addressed that review's AC1 and AC3 proof gaps directly.
- Module-wide coverage remains low because owlbear_kanban.storage is a large legacy file. In this pass the low percentage no longer correlates to an uncovered branch in the changed save_config logic.
- Current-state integrity is verified from the live test file and task body. No historical diff tool was available in this environment, so integrity is grounded in the current exact assertions plus the retry notes stating builder pass-through.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | serve/kanban/src/owlbear_kanban/storage.py:206, 249; tests/test_storage_1175.py:80, 91, 103-107, 262, 278-279 | AC1 quartet | PASS |
| AC2 | serve/kanban/src/owlbear_kanban/storage.py:249; tests/test_storage_1175.py:126, 141, 155-157 | AC2 trio | PASS |
| AC3 | serve/kanban/src/owlbear_kanban/storage.py:258-266; tests/test_storage_1175.py:197, 218, 239, 260 | AC3 expanded suite | PASS |
| AC4 | serve/kanban/src/owlbear_kanban/engine.py:459, 936; serve/kanban/src/owlbear_kanban/models.py:181; tests/test_storage_1175.py:300-301 | AC4 test | PASS |

### Deductions

- -0.03 module-wide coverage remains 27% on a large untouched legacy surface, though no changed-path gap remains.
- -0.02 test-integrity conclusion is based on current-state assertions plus task-body retry notes rather than a direct historical diff.

### Verdict

- PASS to docs
- Confidence: 0.93

### Action

- Advance to docs.

### Reflection

- The retry closed the original proof gaps instead of adding source churn.
- Low module coverage remained useful as a signal, but it stopped being a blocker once every new helper branch had direct proof.
- Builder pass-through was appropriate in this retry because the delta was test-only.
[[2026-04-29]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/kanban/README.md` has no mention of `save_config` or its serialization behavior; change is internal implementation detail |
| 2 | Module docstrings | Yes | Verified | `save_config` docstring accurate ("Write *config* to config.yml…atomic write…Brief-C new schema format"); `_yaml_safe_value` docstring accurate ("Recursively convert non-YAML-safe values emitted by model_dump()") |
| 3 | External attribution | Yes | Verified | Researcher noted "Pydantic v2 model_dump — already in sources/overview.md"; confirmed entry at line 476 of `sources/overview.md` for prior task #806; same reference, no new row required |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1175-save-config-hardening.md` exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (`describes: serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (`describes: serve/kanban/src/**`) both match `storage.py`; footers updated to `Last verified: 2026-04-29 (af6eb2a1)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in AC or task body |
| 7 | Deletion detection | No | N/A | No deleted files — builder modified `storage.py` only; no orphaned IN-scope docs detected |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/storage.py` | IN (docstrings) | Verified — docstrings accurate |
| `tests/test_storage_1175.py` | OUT (test file) | No action |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated

- `share/diagrams/kanban.excalidraw` — footer commit hash updated
- `share/diagrams/mcp-topology.excalidraw` — footer commit hash updated

### Child Tasks Created

- None

### Scratch Files Cleaned

- None found (no `.owlbear/scratch/1175-*` files existed)
[[2026-04-29]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: model_dump(exclude=...) denylist of dead-only keys; new fields emitted automatically | `storage.py:206` (_CONFIG_WRITE_EXCLUDE = {"board","version"}), `:249` (model_dump call); tests: ac1 quartet incl. `test_ac1_new_field_not_in_denylist_is_emitted_automatically` | PASS |
| AC2: nested dict values survive save/load round-trip | `storage.py:249`; tests: `test_ac2_defaults_priority_non_default_survives_roundtrip`, `test_ac2_defaults_status_non_default_survives_roundtrip`, `test_ac2_defaults_is_dict_with_expected_keys_in_yaml_output` | PASS |
| AC3: frozenset-to-list conversion at nested depth via recursive walker | `storage.py:258-266` (_yaml_safe_value handles dict/list/tuple/frozenset); tests: ac3 suite incl. `test_ac3_frozenset_in_list_container_is_converted`, `test_ac3_frozenset_in_tuple_container_is_converted` | PASS |
| AC4: defaults.priority and activity_log preserved through cycle | `engine.py:459,936` (runtime reads); `models.py:181` (default); `test_ac4_defaults_priority_and_activity_log_preserved_through_cycle` | PASS |

### Test Results

- pytest: 2920 passed, 4 skipped, 107 failed (all pre-existing; 0 in task scope — 13/13 task tests green)
- ruff: 4 violations (all in other packages; 0 in task scope)

### Architect Quality: 4/5

AC was specific and testable with clear test-depth annotations. AC1 was refined during arch review to specify denylist approach; AC4 refined to remove stale reference. Reviewer found test-writer proof gaps (AC1 future-field, AC3 list/tuple branches) — these were test-writer coverage gaps, not architect clarity gaps. Minor: original AC1 wording was slightly ambiguous before refinement.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 4 verified) → 0
- Lint violations in task scope: 0 → 0
- AC quality ≤ 3: no (score 4) → 0
- Missing reviewer evidence: no (detailed two-pass review) → 0
- Full-suite failures in task scope: 0 → 0

### Confidence: 1.00

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a7cc38cf | test | tests/test_storage_1175.py | #1175 |
| 3b04581e | fix | serve/kanban/src/owlbear_kanban/storage.py | #1175 |
| b71994d4 | test | tests/test_storage_1175.py | #1175 |
| 687d89a4 | docs | share/diagrams/kanban.excalidraw, share/diagrams/mcp-topology.excalidraw | #1175 |
| 6678c269 | chore | .owlbear/kanban/tasks/1175-*.md, .owlbear/decisions/resolved/1175-*.md, .owlbear/research/1175-*.md | #1175 |
