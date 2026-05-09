---
id: 1477
title: Normalize stale durable config test identifiers
status: in-progress
priority: nice-to-have
created: 2026-05-09T14:12:06.498671+00:00
updated: 2026-05-09T15:56:25.221295+00:00
tags:
- phase-4
- topology
- type:test
- quality
parent: 1473
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Scope

Rename contradictory pytest-visible class/test identifiers and any remaining AC-labeled headings/docstrings in `tests/test_config_loader.py`, `tests/test_config_authority.py`, and `tests/test_config_schema.py` so they match the current topology-constant contract.

## Acceptance Criteria

1. The durable config tests no longer use names/headings that claim vendor preservation, missing-file exceptions, grouped save emission, or root status/priority persistence when the bodies assert omission or next_id-only behavior.
2. The scoped command `uv run pytest tests/test_config_loader.py tests/test_config_authority.py tests/test_config_schema.py tests/test_config_grouped.py` still exits 0 after the rename-only cleanup.
[[2026-05-09]]


## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: rename stale pytest-visible identifiers across 3 durable test files |
| Interface clarity | PASS | AC1 identifies 4 categories of stale naming; AC2 is a clear green-gate |
| Dependency correctness | PASS | No deps. Parent #1473 is done. |
| Module layering | N/A | Test-only changes. |
| TDD compliance | PASS | `type:test` + `quality` tag — test-writer pass-through. No new assertions needed. |
| KISS/YAGNI | PASS | Minimal scope — rename identifiers only, no logic changes. |
| Premise challenge | PASS | Stale identifiers are genuine traceability debt flagged by #1473 reviewer. |
| Pattern consistency | PASS | Standard test-name alignment. |
| Security surface | N/A | No new system boundaries. |
| Single domain | PASS | kanban test alignment only. |
| Failure Mode Map | N/A | Rename-only changes, no new codepaths. |
| Decision-request verification | N/A | No research doc referenced. |
| User-action detection | SKIP | Counter-signal C3 (tagged `type:test`). |

### Stale Identifiers Catalog (from codebase inspection)

**tests/test_config_loader.py:**
- `test_load_config_preserves_grouped_vendor_field_at_root` — says "preserves" but asserts `None` (vendor is NOT preserved)
- `test_load_config_preserves_grouped_tui_section_at_root` — says "preserves" but asserts `None` (tui is NOT preserved)
- `test_load_config_raises_on_missing_file` — says "raises" but body returns default `BoardConfig`

**tests/test_config_authority.py:**
- Section header `AC4 -- save_config writes statuses/priorities at root only` — save_config writes only `next_id`, not statuses/priorities
- `test_save_config_has_root_statuses` — says "has root statuses" but asserts only `{"next_id"}` keys
- `test_save_config_has_root_priorities` — says "has root priorities" but asserts `raw == {"next_id": ...}`
- `test_save_config_pipeline_has_no_statuses` — technically true but misleading; whole output is next_id-only
- `test_save_config_pipeline_has_no_priorities` — same issue

**tests/test_config_schema.py:**
- Section header `ACs 8-9 — save_config emits grouped format` — save_config emits next_id only
- `TestFromAC_SaveConfigGrouped` class + docstring: "emits schema: grouped" — emits only next_id
- `test_save_config_emits_schema_grouped_field` — says "emits schema grouped" but asserts `{"next_id": ...}`
- `test_save_config_emits_paths_sub_section` — says "emits paths" but asserts `"paths" not in data`
- `test_save_config_emits_pipeline_sub_section` — says "emits pipeline" but asserts `"pipeline" not in data`
- `test_save_config_emits_agents_and_policy_sub_sections` — says "emits" but asserts not in data

### Test Depth
- AC1: td:0 (mechanical rename of identifiers/headings; no new logic)
- AC2: td:0 (existing suite validates green-gate)
- Max depth: td:0
- Test-writer: SKIP

### Design Diverge
- Skipped — single approach (rename to match asserted behavior). No competing alternatives.

### Challenge
- Skipped — all AC lines are td:0.

### Verdict: APPROVE
### Action Taken: Added stale-identifiers catalog as builder guidance. Advanced to todo.
[[2026-05-09]]
Architecture review complete. AC is clear and verifiable — 4 categories of stale naming identified across 3 files, with a detailed catalog of 15 specific identifiers/headings for builder guidance. All td:0 (mechanical rename), challenger skipped. All 13 Step 2 criteria evaluated — all PASS/N/A/SKIP.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`, `quality`) — no new tests applicable.
- Task is a mechanical rename of stale pytest-visible identifiers in 3 existing test files (test_config_loader.py, test_config_authority.py, test_config_schema.py).
- Architecture review confirmed: all AC lines td:0, Test-writer: SKIP.
- AC2 green-gate (`uv run pytest` exits 0) verified by existing suite — no new assertions needed.
- Passing through to builder.