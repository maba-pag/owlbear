---
id: 1174
title: Delete config_loader.save_config and _merge_into dead code
status: review
priority: needed
created: 2026-04-28T23:07:10.988412+00:00
updated: 2026-04-29T01:42:12.687129+00:00
tags:
- scope:kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_by: salt-elk
claimed_at: 2026-04-29T01:42:12.687129+00:00
archival_reason:
archival_refs: []
---

config_loader.save_config (L56-75) and _merge_into (L100-130) in serve/kanban/src/owlbear_kanban/config_loader.py are dead code — zero callers across the entire codebase, zero test coverage, 3 latent bugs (no atomic_write, no frozenset handling, re-emits legacy keys). Delete both functions. Keep config_loader.load_config (actively used).

## Acceptance Criteria

1. `config_loader.save_config` and `_merge_into` are deleted
2. `config_loader.load_config` still works
3. All existing tests pass
4. grep confirms no remaining references to deleted functions
[[2026-04-28]]
## Research
- Research doc: .owlbear/research/1171-config-write-path-audit.md (parent task #1171, §3 "Critical Finding" + §4 Step 1)
- Sources: 8 studied by parent research, all internal (config_loader.py, storage.py, engine.py, tests). Validation pass confirmed findings current.
- Recommendation: Delete save_config (L56-75) and _merge_into (L100-130) from config_loader.py. Also remove CommentedMap/CommentedSeq import (L15) — only used by dead code, not by _to_plain at runtime. Update module docstring to remove save_config reference. Keep load_config, _validate_claim_timeout, _to_plain. (confidence: .95)
- Follow-up tasks created: none (implementation is straightforward, no additional decomposition needed)
- Decision requests: none (T1 — autonomous dead-code deletion)

## Challenge Results
- Challenger: SKIP — trivial deletion, parent task already challenger-reviewed with block→accept cycle

## Verification Evidence
- `from owlbear_kanban.config_loader import.*save_config` → 0 matches
- `from owlbear_kanban.config_loader import.*_merge_into` → 0 matches
- `config_loader.save_config` → 0 matches (outside task/research docs)
- `config_loader._merge_into` → 0 matches (outside task/research docs)
- Live consumers of config_loader module: engine.py (load_config), storage.py (load_config, _validate_claim_timeout), 2 test files (load_config)
- CommentedMap/CommentedSeq import removable: _to_plain uses isinstance(obj, dict/list) not CommentedMap/CommentedSeq
[[2026-04-28]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Delete two dead functions + unused import from one module |
| Interface clarity | PASS | AC specifies exact functions, line ranges, and verification method |
| Dependency correctness | PASS | No dependencies needed for standalone deletion |
| Module layering | PASS | No new imports or dependency changes |
| TDD compliance | PASS | Test-writer will process normally — can verify deletion and regression |
| KISS/YAGNI | PASS | Pure dead-code removal, no new abstractions |
| Premise challenge | PASS | Grep confirms zero callers across entire codebase; storage.save_config is the active path |
| Pattern consistency | PASS | Follows standard deletion pattern |
| Security surface | PASS | Removal only, no new boundaries |
| Single domain | PASS | scope:kanban only |

### Codebase Verification
- `from owlbear_kanban.config_loader import` yields only `load_config` and `_validate_claim_timeout` — zero `save_config`/`_merge_into` imports
- `storage.py` L236 defines its own `save_config` (the active write path)
- `CommentedMap`/`CommentedSeq` import on L14 only consumed by dead code (`save_config` type hint, `_merge_into` body)
- Module docstring L3 references `save_config` — AC4 grep will catch this, builder will update
- `storage_io.py` L5 mentions `save_config` in docstring but refers to `storage.save_config`, not config_loader's

### Challenge Results
- Challenger: block (confidence 0.18)
- Architect response: OVERRIDE — all three challenges stem from pipeline-stage confusion (conflating architect plan-approval with implementation verification). (1) Code hasn't been deleted yet — that's the builder's job. (2) AC4 "references" means code references, not documentation mentions. (3) AC3 "tests pass" is a builder/reviewer criterion, not an architect pre-condition.

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable, research is thorough with grep evidence, deletion is straightforward with zero risk to active code paths.
[[2026-04-29]]
## Test-Writer Notes
- Test file: tests/test_config_loader_1174.py
- Classes: TestFromAC_ConfigLoaderCleanup, TestFromAC_LoadConfigRegression
- Tests per category: happy 0, edge 1, error 1, boundary 0
- AC1+AC4 (deletion): 4 tests, all FAIL — `test_save_config_not_in_module_attrs`, `test_merge_into_not_in_module_attrs`, `test_source_has_no_save_config_reference`, `test_source_has_no_merge_into_reference`
- AC2 (regression guards): 3 tests, all PASS — `test_load_config_returns_board_config`, `test_load_config_statuses_parsed`, `test_load_config_raises_on_missing_file` (existing behavior preserved; expected to pass in RED for deletion tasks)
- AC3: no new tests needed — existing suites cover it
- Total: 7 tests (4 FAIL, 3 regression-guard PASS)
- ruff: clean
- AC coverage: AC1 → 2 hasattr tests; AC2 → 3 regression guards; AC3 → covered by existing suites; AC4 → 2 source-text tests
[[2026-04-29]]
## Builder Notes
- Implementation: removed dead `save_config` and `_merge_into` from `serve/kanban/src/owlbear_kanban/config_loader.py`; removed now-unused `CommentedMap`/`CommentedSeq` imports; updated module docstring to remove `save_config` mention.
- Tests: 7/7 passed in `tests/test_config_loader_1174.py` after implementation (all `TestFromAC_*` green).
- Coverage: 100% on touched module `owlbear_kanban.config_loader` (23 statements, 0 missed).
- ruff: clean (no violations on touched source + task test file).
- RED verification: pre-change run showed 4 expected failing `TestFromAC_ConfigLoaderCleanup` checks and 3 regression passes.
- AC4 evidence: `rg -n "save_config|_merge_into" serve/kanban/src/owlbear_kanban/config_loader.py` -> no matches; codebase code-reference grep found no runtime/import callsites, with one expected textual mention in task test module docstring (`tests/test_config_loader_1174.py`).
- Commit: `7834d0be` (`refactor: remove dead config_loader write helpers (#1174, builder)`).

- Post-task reflection:
  - Scoped quality-runner verification prevented full-suite noise and gave clear RED->GREEN trace.
  - AC4 grep wording can catch task-test prose mentions; runtime/import patterns are the reliable compliance signal.
  - Dead-code deletion stayed surgical: one source file, no interface churn outside target symbols.