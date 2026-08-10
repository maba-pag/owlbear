# Test Quality — Decisions

## D1: Investment Tier

**Tier:** Shared
**Rationale:** Test infrastructure is foundational to the pipeline. Changes affect every agent, every task, every future project. User considers this significant enough for full-depth treatment.
**Date:** 2026-04-17

## D2: Quality Gate on Promotion

**Decision:** Quality gate in v1 — curator must produce contract-level tests on promotion.
**Rationale:** Mechanical promotion without quality improvement moves noise from task-numbered files to module files without solving the trust problem. End-User and Data panelists argued this convincingly: lifecycle without semantic upgrade is insufficient.
**Trade-off accepted:** Slower to ship, higher complexity in curator design. The curator must judge assertion quality, not just file placement.

## D3: Agent Deletion Authority

**Decision:** Accepted — agents can permanently remove test assertions post-archive.
**Rationale:** The lifecycle cannot function if tests are truly immortal. Post-archive removal with hard gates (green suite + coverage floor) provides sufficient safety. This is a new authorized capability.
**Trade-off accepted:** Silent behavioral assertion loss is possible within maintained coverage. Design must not overclaim preservation guarantees.

## D4: Builder Visibility

**Decision:** In scope — expand builder scoped-runs to include module-level tests.
**Rationale:** Lifecycle cleans the suite but builders still need signal about cross-task impacts during development. Running the module's durable test file alongside task tests is low-cost, high-signal.

## D5: Legacy Bootstrap

**Decision:** Nuclear — delete all existing tests. Start with a clean slate.
**Rationale:** The forward-only approach doesn't deliver trust/speed outcomes while legacy noise persists. Manual triage of 190+ files is pointless. The cleanest path is to start fresh and let the new lifecycle system build the suite correctly from the beginning.
**Implication:** Coverage drops to 0% temporarily. As new tasks touch modules, the test-writer creates task-scoped tests; the curator promotes them to durable module-level files. Coverage rebuilds organically, proportional to active development. The 90% coverage floor applies per curator operation, not as a global invariant during the rebuild period.
