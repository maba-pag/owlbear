---
id: 1204
title: Remove _validate_engine_config — trust model validator
status: in-progress
priority: needed
created: 2026-04-30 15:29:06.178965+00:00
updated: 2026-05-01T22:04:19.948170+00:00
tags:
- audit-kanban
- dry
parent:
depends_on:
- 1200
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Remove redundant _validate_engine_config; trust model validator.

## Files
- serve/kanban/src/owlbear_kanban/engine.py (KanbanEngine.__init__, _validate_engine_config)
- serve/kanban/tests/test_engine_coverage_1068.py (tests directly invoking _validate_engine_config)

## Change
Delete `_validate_engine_config()` function. Remove its call from `KanbanEngine.__init__()`. BoardConfig._validate_semantics (model_validator mode="after") already covers all the same checks. Remove tests that directly invoke the deleted function.

Note: `_parse_duration` and `_DURATION_RE` must remain in engine.py — they are used by `KanbanEngine._parse_claim_timeout` (line 1817).

## AC
- [ ] `_validate_engine_config` function deleted from engine.py (td:1)
- [ ] No call to `_validate_engine_config` in `KanbanEngine.__init__` (td:0)
- [ ] Tests in `serve/kanban/tests/test_engine_coverage_1068.py` that directly invoke `_validate_engine_config` are removed (td:0)
- [ ] `_parse_duration` and `_DURATION_RE` remain in engine.py (td:0)
- [ ] BoardConfig._validate_semantics still rejects: empty statuses, empty priorities, invalid entry_status, invalid terminal_status, invalid claim_timeout, non-list compatibility, asymmetric compatibility — verified by existing model-level test suite (td:1)
- [ ] All tests pass (td:0)

## Finding: 1.2

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One function removal, one concern |
| Interface clarity | PASS | Delete + remove call — no ambiguity |
| Dependency correctness | PASS | #1200 archived (done) |
| Module layering | PASS | Removes engine-level duplication of model-level validation |
| TDD compliance | PASS | Existing model-level tests cover all validation paths |
| KISS/YAGNI | PASS | Removing redundancy = simpler |
| Premise challenge | PASS | Confirmed: _validate_semantics calls identical helpers with same error codes |
| Pattern consistency | PASS | refresh_config() already trusts model-level validation alone |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Kanban engine only |

### Challenge Results
- Challenger: reconsider (0.68)
- Concerns: state-surface mismatch (synthetic test mutations), overclaimed scope, validator-path confusion
- Architect response: rebutted — refresh_config already omits the helper (proving engine doesn't depend on it post-construction), other redundancies tracked in #1206, mode="after" vs mode="before" clarified

### Test Depth
- Max depth: 1
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC with test file scope, _parse_duration retention note, and test-depth annotations. Advanced to todo.

[[2026-05-01]]
Architecture review complete. Confirmed full redundancy between _validate_engine_config (engine.py:114-167) and BoardConfig._validate_semantics (models.py:403-413) — identical checks, same error codes. refresh_config() already trusts model-level validation alone. AC refined with test file scope and _parse_duration retention note. Challenger rebutted (state-surface concern invalid — no production mutation path exists).
[[2026-05-01]]
## Test-Writer Notes
- Test file: tests/test_engine_dead_code_1204.py
- Classes: TestFromAC_RemoveValidateEngineConfig
- Tests per category: happy 0, edge 0, error 2, boundary 0
- Total: 2 tests, all FAIL
- ruff: clean

AC coverage:
| AC line | td | Test |
|---|---|---|
| `_validate_engine_config` deleted from engine.py | 1 | `test_function_not_in_engine_module` (AssertionError) |
| `_validate_engine_config` not importable from engine | 1 | `test_function_not_importable_from_engine` (DID NOT RAISE) |
| No call in `__init__` | 0 | skipped |
| Tests invoking it removed from 1068 | 0 | skipped |
| `_parse_duration` / `_DURATION_RE` remain | 0 | skipped |
| `_validate_semantics` still rejects invalid configs | 1 | No new test — any smoke test passes now; behavior covered by existing `test_engine_init_1068.py::TestFromAC_BoardConfigSemanticValidation`. Per w-tdd-red: passing tests are removed. |
| All tests pass | 0 | skipped |