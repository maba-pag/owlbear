---
id: 1134
title: Fix edit route to pass expected_updated to engine and handle 
  ConcurrencyError
status: todo
priority: important
created: 2026-04-26T16:00:44.066635+00:00
updated: 2026-04-26T16:25:10.681031+00:00
tags:
- cockpit
parent:
depends_on:
- 1131
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

Objective: Close the TOCTOU gap in the cockpit edit route by engaging the engine's CAS mechanism.

Context: The edit route in `mutation.py` does a string-comparison precheck (`req.updated != task.updated` → 409) but does NOT pass `expected_updated` to `engine.edit_task()`. The engine CAS is never engaged through the HTTP API. Additionally, `ConcurrencyError` is not imported or handled — it would propagate as 500 if CAS were engaged.

Acceptance Criteria:
- [ ] AC1: `engine.edit_task(str(task_id), expected_updated=req.updated, **kwargs)` — route passes `expected_updated` to engine call
- [ ] AC2: `from owlbear_kanban.models import ConcurrencyError` added as runtime import (not under `TYPE_CHECKING`); `except ConcurrencyError` handler maps to `HTTPException(409, detail="Task was modified since your last load (stale snapshot)")`
- [ ] AC3: All existing tests in `test_cockpit_mutation_api.py` pass unchanged
- [ ] AC4: Edit TOCTOU characterization test in `test_cockpit_mutation_race_1131.py` updated to assert `expected_updated` IS present in captured engine call kwargs (inverts the gap proof from #1131 AC1, proving the CAS path is now engaged)

Likely files:
- serve/cockpit/src/owlbear_cockpit/routes/mutation.py
- tests/test_cockpit_mutation_race_1131.py (update characterization test)
- tests/test_cockpit_mutation_api.py (regression only, no changes expected)

## Builder Guidance
- The route-level precheck (L195-199) may be kept as a fast-fail optimization or removed — engine CAS is sufficient either way. If kept, ensure both precheck and CAS handler use the identical 409 detail string to avoid drift.
- Reference pattern for passing the CAS token: `CockpitView.edit_task` at `engine.py:3134` passes `expected_updated` to the engine. Note: CockpitView does NOT catch `ConcurrencyError` (it propagates to the MCP layer), so the route handler is novel — use the same `except ConcurrencyError → HTTPException(409)` pattern as the precheck.
- The 409 detail string `"Task was modified since your last load (stale snapshot)"` is already established at mutation.py:198. Reuse the same literal.

See: .owlbear/research/1131-cockpit-mutation-race-tests.md § G1
See: .owlbear/research/1134-edit-route-cas-gap.md

[[2026-04-26]]
## Research
- Research doc: .owlbear/research/1134-edit-route-cas-gap.md
- Sources: 7 studied, 4 high-relevance
- Recommendation: Option A — add engine CAS (`expected_updated=req.updated`) + keep route precheck as fast-fail + catch `ConcurrencyError` → 409 (confidence: 0.90)
- Follow-up tasks created: none (task #1134 is itself the implementation task)
- Decision requests: none (T1 autonomous bug fix)

## Challenge Results
- Challenger: skipped — trivial single-option fix with clear prior analysis in #1131
- Confidence in original: 0.90

Key findings:
1. Route needs `from owlbear_kanban.models import ConcurrencyError` (runtime import)
2. Pass `expected_updated=req.updated` to `engine.edit_task()` 
3. Add `except ConcurrencyError` → HTTPException(409) with same detail string as precheck
4. ~8 LOC change total
[[2026-04-26]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One fix: close TOCTOU gap in edit route by engaging engine CAS |
| Interface clarity | PASS (after refinement) | Rewrote 5 AC → 4 precise lines; removed untestable builder-discretion AC; specified exact import, handler, and detail string |
| Dependency correctness | PASS (after fix) | Added depends_on: [1131] — characterization test file must exist before #1134 updates it |
| Module layering | PASS | `ConcurrencyError` runtime import from `owlbear_kanban.models` is consistent with existing `owlbear_kanban.KanbanEngine` DI dependency |
| TDD compliance | PASS | #1131 provides characterization tests (RED); #1134 is the GREEN fix that updates the test to prove CAS engagement |
| KISS/YAGNI | PASS | ~8 LOC production change + test update |
| Premise challenge | PASS | Gap confirmed: mutation.py L195-199 precheck only, L207 engine call without expected_updated, no ConcurrencyError import |
| Pattern consistency | PASS | Follows engine CAS kwarg pattern (engine.py:959 `expected_updated: str | None = None`); CockpitView.edit_task:3134 shows token forwarding |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit mutation routes only |

### Challenge Results
- Challenger: block (confidence: 0.34)
- Six concerns raised: (1) CockpitView reference pattern overstated — CockpitView passes token but doesn't catch ConcurrencyError; (2) AC5 contradicts #1131 characterization test; (3) AC3 not testable; (4) existing tests don't prove CAS engagement; (5) route-vs-view duplication risk; (6) detail string drift
- Architect response: accepted concerns 1-4, addressed via AC refinement — rewrote AC (5→4 lines), added depends_on: [1131], moved precheck discretion to builder guidance, corrected reference pattern description, specified test update to prove CAS path. Concern 5 noted but not actioned (existing architecture, not a #1134 issue). Concern 6 addressed in builder guidance (reuse identical literal).

### AC Refinement Summary
- Original AC3 ("may be kept or removed") was builder discretion → moved to Builder Guidance section
- Original AC5 ("race test passes with fix") contradicted #1131 AC1 gap proof → rewritten as AC4: update characterization test to assert `expected_updated` IS present (inverts gap proof)
- Added dependency on #1131 (test file must exist)
- AC2 now specifies exact import path and exception handler pattern
- Builder Guidance section added: precheck discretion, reference pattern correction, detail string reuse

### Verdict: APPROVE (after refinement)
### Action Taken: Rewrote AC (5→4 lines), added depends_on [1131], added Builder Guidance section, advanced to todo