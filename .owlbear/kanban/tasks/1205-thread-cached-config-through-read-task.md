---
id: 1205
title: Thread cached config through read_task
status: in-progress
priority: important
created: 2026-04-30 15:29:06.208450+00:00
updated: 2026-05-02T02:45:18.154695+00:00
tags:
- audit-kanban
- performance
parent:
depends_on:
- 1204
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Avoid redundant config disk reads in read_task hot path.

## Files
- storage.py (read_task function)
- engine.py (callers of read_task)

## Change
Add optional `config: BoardConfig | None = None` parameter to `read_task()`. When provided, use it for corruption detection instead of calling `load_config()` from disk. When `config` is provided, skip the `config_path.exists()` guard (config is already available — corruption detection always runs). When `config=None` (default), preserve existing behavior: check config_path.exists(), load from disk, detect corruption.

Engine passes its cached `self._config`. Standalone callers still load from disk.

## AC
- [ ] `read_task(path, *, config=None)` accepts keyword-only `BoardConfig | None`; when provided, uses it for `detect_corruption()` without calling `load_config()` (td:1)
- [ ] When `config` is passed, corruption detection runs unconditionally (skips the `config_path.exists()` guard since config is already resolved) (td:2)
- [ ] When `config=None`, existing behavior unchanged: `config_path.exists()` guard, `load_config()` from disk, corruption detection (td:1)
- [ ] All engine `read_task()` call sites pass `self._config` as keyword arg (td:1)
- [ ] `write_task_if_unchanged` in storage.py — standalone, does NOT pass config (keeps disk authority for concurrency checks) (td:0)
- [ ] No existing tests break (td:0)

## Finding: 5.1

## Architecture Review

**Verdict:** APPROVED → todo

**AC assessment:**

| AC line | Assessment | Action |
|---------|-----------|--------|
| Original "read_task accepts optional config parameter" | Too vague — doesn't specify keyword-only, type, or behavior change | Rewritten: keyword-only `BoardConfig \| None` with explicit semantics |
| Original "Engine callers pass cached config" | Doesn't enumerate call sites or specify keyword | Rewritten: all engine call sites, keyword arg |
| Original "Standalone callers still work without passing config" | Acceptable but incomplete | Split into: default-None preserves existing behavior + write_task_if_unchanged explicitly standalone |
| Original "No behavior change; performance improvement" | Not directly testable, slightly misleading (config authority shifts for engine callers) | Replaced with testable td:2 line for when-config-passed semantics |

**Architecture notes:**
- Pattern is consistent with `detect_corruption(path, config)` in corruption.py which already accepts config as parameter
- Semantic note: threading cached config means engine corruption checks use the engine's config snapshot rather than live disk state. This is already the case for `list_tasks` and `release_expired_claims` which call `detect_corruption(path, self._config)` directly. This change aligns `read_task` with that existing authority model.
- `write_task_if_unchanged` in storage.py is a standalone caller that should NOT receive engine config — it needs disk-authoritative concurrency checks
- The `config_path.exists()` gate skip when config is passed is intentional: the engine has already resolved config, no need to probe the filesystem

**Dependency analysis:**
- #1204 (Remove _validate_engine_config) — archived/done ✓
- No downstream dependents found

**Challenger results:**
- Challenger recommended `reconsider` (confidence 0.63) citing config staleness risk, public API contract gap, and weak performance proof
- Config staleness: addressed — engine already uses cached config for its own detect_corruption calls; this aligns read_task with existing authority model. Explicit AC line for when-config-passed semantics added.
- Public API gap: addressed — config.yml existence gate behavior specified per AC line 2 and 3
- Performance proof: acknowledged that warm caches bypass read_task; optimization targets cold paths (N tasks = N eliminated config loads). Proportional benefit.
- Architect retains APPROVE after addressing concerns in refined AC

[[2026-05-02]]
Architecture review complete. Refined 4 vague AC lines into 6 testable lines with td annotations. Challenger concerns (config staleness, public API gate, performance proof) addressed through explicit when-config-passed/when-None semantics and write_task_if_unchanged carve-out.
[[2026-05-02]]
## Test-Writer Notes
- Test file: tests/test_storage_1205.py
- Classes: TestFromAC_ReadTaskCachedConfig
- Tests per category:
  - AC1 (happy/boundary): 3 tests — accepts config= kwarg, skips load_config when provided, keyword-only enforcement
  - AC2 (happy/edge/error/boundary): 4 tests — valid task no config.yml, corrupt task no config.yml, corrupt task with config.yml, boundary guard bypassed
  - AC3 (happy): 2 tests — config=None returns task, config=None calls load_config
  - AC4 (static): 1 test — AST inspection of engine.py for all call sites
- Total: 10 tests, all FAIL ✓
- Failure modes: 9× TypeError (unexpected keyword argument 'config'), 1× AssertionError (12 engine.py call sites missing config= at lines 632, 665, 791, 802, 808, 812, 957, 1061, 1152, 1270, 1434, 1520)
- Lint: clean (ruff 0 violations)
- AC coverage:
  | AC line | Tests |
  |---------|-------|
  | AC1: accepts keyword-only BoardConfig\|None, skips load_config when provided | test_ac1_accepts_config_keyword_arg, test_ac1_config_provided_skips_load_config_call, test_ac1_config_param_is_keyword_only |
  | AC2: detection runs unconditionally when config provided | test_ac2_happy_valid_task_no_config_yml_config_provided, test_ac2_edge_corrupt_task_no_config_yml_config_provided_raises, test_ac2_error_corrupt_task_config_yml_present_config_provided_raises, test_ac2_boundary_detection_runs_even_when_config_yml_absent |
  | AC3: config=None preserves existing behavior | test_ac3_explicit_none_returns_task, test_ac3_explicit_none_calls_load_config |
  | AC4: all engine call sites pass self._config | test_ac4_engine_all_call_sites_pass_config |
  | AC5 (td:0): write_task_if_unchanged standalone | skipped — td:0 |
  | AC6 (td:0): no existing tests break | skipped — td:0 |