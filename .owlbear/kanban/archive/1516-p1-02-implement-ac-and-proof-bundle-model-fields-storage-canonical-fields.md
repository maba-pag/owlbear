---
id: 1516
title: 'P1-02: Implement ac and proof_bundle model fields + storage canonical fields'
status: archived
priority: medium
created: 2026-05-13T02:29:16.772741+00:00
updated: 2026-05-13T03:47:54.901280+00:00
tags:
  - phase-1
  - scope:kanban
  - tdd
  - feature
parent: 1514
depends_on:
  - 1515
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Add ac/proof_bundle fields to Task, TaskSummary, TaskFull, DispatchEntry; add proof_bundle normalizing validator; update _CANONICAL_FIELDS
Out of scope: Engine behavior, MCP tools, migration

## Acceptance Criteria
- AC1: `Task(...)` constructor accepts `ac: list[str]` (default `[]`) and `proof_bundle: str | None` (default `None`); both round-trip through model serialization
- AC2: `TaskSummary` and `DispatchEntry` include `proof_bundle` but NOT `ac`; `TaskFull` inherits `proof_bundle` from `TaskSummary` and adds `ac: list[str]`
- AC3: `Task.proof_bundle` field_validator normalizes `"Behavioral+Challenge"` → `"behavioral+challenge"` and sorts modifiers alphabetically (`"critical+reader+challenge"` → `"critical+challenge+reader"`)
- AC4: `storage._CANONICAL_FIELDS` includes `"ac"` and `"proof_bundle"` positioned after `"depends_on"`

Proof bundle: existing
Existing proof scope: tests/test_model_fields_1515.py, serve/kanban/tests/test_engine_models.py, serve/kanban/tests/test_storage.py
2026-05-13T03:34:06+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Model fields + storage ordering only |
| Interface clarity | PASS | Exact types, defaults, normalization rules specified |
| Dependency correctness | PASS | #1515 (archived/completed) — dep_status ok |
| Module layering | PASS | models.py fields + storage.py canonical list — no upward imports |
| TDD compliance | PASS | Tests exist in `tests/test_model_fields_1515.py` (28 tests, all green) from TDD pair #1515 |
| KISS/YAGNI | PASS | Minimal: 2 fields + 1 validator + 1 list update |
| Premise challenge | PASS (de-escalated) | Implementation already committed via #1515's builder (commit 546b4f93). Task exists as dependency gate for #1517, #1522, #1524 — must advance to unblock downstream |
| Pattern consistency | PASS | Pydantic v2 field_validator, Field(default_factory=list), str | None pattern matches existing model conventions |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | scope:kanban only |

### Dependency Analysis
- #1515 (dep): archived/completed — implementation committed
- Downstream blockers: #1517 (engine tests), #1522 (migration tests), #1524 (consolidation test) all depend on #1516
- `migrate._CANONICAL_FIELDS` (migrate.py:31) still lacks `ac`/`proof_bundle` — correctly scoped to migration tasks #1522/#1523, not this task

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing (de-escalated — implementation and tests already complete from #1515's pipeline cycle; no new code to write)
- Existing proof scope: tests/test_model_fields_1515.py, serve/kanban/tests/test_engine_models.py, serve/kanban/tests/test_storage.py
- Test-writer: SKIP

### Design Diverge
- Trigger: skipped — single established approach, no alternatives to evaluate

### Challenge Results
- Challenger: SKIPPED — proof bundle `existing` (challenger column = skip per bundle table)

### Verdict: APPROVE
### Action Taken: De-escalated proof bundle from `behavioral` to `existing` (implementation already committed in #1515 cycle). Advanced #1516 → todo to unblock downstream dependency chain.
2026-05-13T03:35:25+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Architect noted "Test-writer: SKIP"; implementation committed in #1515 cycle.
- Existing proof scope: tests/test_model_fields_1515.py, serve/kanban/tests/test_engine_models.py, serve/kanban/tests/test_storage.py
- Passing through to builder.
2026-05-13T03:37:02+00:00
## Builder Notes
- Files changed: none (pass-through; implementation already present from dependency cycle)
- Proof bundle routing: existing
- Required existing proof executed via quality-runner on:
  - tests/test_model_fields_1515.py
  - serve/kanban/tests/test_engine_models.py
  - serve/kanban/tests/test_storage.py
- Test results: 259 passed, 0 failed, 0 skipped
- Lint status: ruff clean (no violations)
- Coverage evidence from proof run:
  - owlbear_kanban.models: 87%
  - owlbear_kanban.storage: 92%
- Fixes applied: none (no implementation delta required for this task)
- Evidence summary: AC behavior is already implemented and validated by existing proof bundle; task advanced as dependency-gate pass-through.
2026-05-13T03:42:02+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1516 -> docs | AC mapped to code and existing-proof evidence sufficient.
- Builder evidence reviewed first: pass-through task correctly points to archived implementation from #1515 (commit `546b4f93`); builder reran the named existing-proof scope `tests/test_model_fields_1515.py`, `serve/kanban/tests/test_engine_models.py`, and `serve/kanban/tests/test_storage.py` via quality-runner -> 259 passed, 0 failed, 0 skipped; `ruff` clean; coverage `owlbear_kanban.models` 87% and `owlbear_kanban.storage` 92%.
- AC evidence map:
| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `Task.ac` and `Task.proof_bundle` are declared on `Task` at `serve/kanban/src/owlbear_kanban/models.py:449-450`. | `tests/test_model_fields_1515.py:57`, `:61`, `:65`, `:70`, `:75`, `:82`, `:89`, and `:100` prove declaration, defaults, model_dump presence, and round-trip preservation. | PASS |
| AC2 | `TaskSummary.proof_bundle` is present at `serve/kanban/src/owlbear_kanban/models.py:499-525`; `TaskFull(TaskSummary)` adds `ac` at `serve/kanban/src/owlbear_kanban/models.py:622-628`; `DispatchEntry.proof_bundle` is present at `serve/kanban/src/owlbear_kanban/models.py:631-641`. | `tests/test_model_fields_1515.py:120`, `:124`, `:128`, `:132`, `:136`, `:141`, `:146`, `:155`, and `:163` prove `proof_bundle` inclusion on summary/dispatch/full, `ac` inclusion on `TaskFull`, and `ac` exclusion from `TaskSummary` / `DispatchEntry`. | PASS |
| AC3 | `Task._normalize_proof_bundle` normalizes casing and canonical modifier order at `serve/kanban/src/owlbear_kanban/models.py:472-491`. | `tests/test_model_fields_1515.py:180`, `:185`, and `:205` prove lowercase normalization and alphabetical modifier ordering for the AC examples and boundary case. | PASS |
| AC4 | `_CANONICAL_FIELDS` contains `depends_on`, `ac`, `proof_bundle`, `blocked` in order at `serve/kanban/src/owlbear_kanban/storage.py:212-230`. | `tests/test_model_fields_1515.py:219`, `:223`, `:227`, `:232`, `:237`, and `:242` prove presence and exact ordering. | PASS |
- Safety/security: no new path, shell, auth, secret, or external-input surface is introduced; the change is limited to model schema and canonical storage ordering.

## Observations
- `serve/kanban/tests/test_storage.py:62-76` and `serve/kanban/tests/test_storage.py:1150-1164` still encode the legacy written-frontmatter order without `ac` / `proof_bundle`; combined with `write_task()` omitting default `ac=[]` and `proof_bundle=None` at `serve/kanban/src/owlbear_kanban/storage.py:415-418`, that durable suite serves as regression coverage for default-field omission rather than direct proof of AC4. The direct AC4 proof for this task is correctly carried by `tests/test_model_fields_1515.py`.
- No blocking implementation mismatch or weak-assertion gap remains in the named proof bundle for this task.
2026-05-13T03:43:24+00:00
## Docs Gate

**Verdict: PASS — no docs impact**

**Convention mapping:** `serve/kanban/src/owlbear_kanban/models.py` + `serve/kanban/src/owlbear_kanban/storage.py` → `serve/kanban/README.md`

**Checklist:**

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A | `serve/kanban/README.md` documents engine methods and product topology only; no field-level model table exists for `Task`, `TaskSummary`, `TaskFull`, `DispatchEntry`, or `_CANONICAL_FIELDS`. New `ac`/`proof_bundle` fields don't create drift — existing fields (`blocked`, `depends_on`) are also absent from the README at that level. No update required. |
| External Attribution | N/A | No external sources referenced; pure internal model schema change. |
| Research Doc | N/A | No research artifact referenced in task body. |
| Deletion Detection | N/A | Pass-through task; no files deleted, no orphaned references. |

**Files updated:** None

**Scratch cleanup:** No `1516-*` scratch files found.
2026-05-13T03:47:54+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 4412 passed, 20 failed, 14 skipped\n- All 20 failures verified pre-existing and unrelated (test_ideation_diagram, test_cockpit_view FileNotFoundError, test_server NoneType, test_engine_accessor_migration accessor paths) — none reference owlbear_kanban.models or storage\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (pass-through dependency gate; implementation in #1515 commit 546b4f93; files models.py + storage.py in scope:kanban)\n- purpose match: PASS (adds ac/proof_bundle fields as dependency for downstream #1517, #1522, #1524)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 5/5\nACs specify exact types, defaults, normalization rules, and field ordering. De-escalation from behavioral to existing proof was appropriate given implementation was already committed in dependency #1515.\n\n### Commit Integrity\n- upstream commit presence: PASS (546b4f93 — feat: implement ac/proof_bundle model fields and canonical order #1515, builder)\n- kanban commit packaging: pending (will commit after end_work)\n\n### Deduction Breakdown\nNo deductions applied.\n\n### Confidence: 1.00\n### Action: archive