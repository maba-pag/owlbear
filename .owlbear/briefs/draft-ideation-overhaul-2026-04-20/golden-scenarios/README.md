# Golden Scenarios

These are repo-side worked validation fixtures for the ideation overhaul in `owlbear-dev`.

They are intended to prove the artifact shapes, phase boundaries, and review points required by the overhaul brief before live validation on the main-consuming runtime. They are not runtime transcripts and they do not replace later live validation.

## Scenario Classes

| Scenario | Class | Primary Checks |
|---|---|---|
| `01-net-new-work` | net-new work | project type recorded early, narrow research bridge, explicit Phase 1 handoff |
| `02-existing-feature-refactor` | existing-feature/refactor | fresh-context Phase 2 start, late-panel synthesis, full-brief walkthrough readiness |
| `03-overscoped-request` | overscoped request | early simplification before Phase 2, conditional denoise, O15 classification under stress |
| `04-expectation-fidelity` | expectation fidelity | expectation signal preserved, passable-but-wrong version rejected, Brief remains binding through planning |

## Coverage Map

- `01-net-new-work` covers AC 10, 11, 13, and 17.
- `02-existing-feature-refactor` covers AC 10, 11, 12, and 16.
- `03-overscoped-request` covers AC 10, 11, 14, and 15.
- `04-expectation-fidelity` covers the expectation-fidelity contract added after AC 17: target expectation, First Useful Step as sequencing, Brief binding, and planner non-deletion.

## Qualitative Review

Human review was applied to `02-existing-feature-refactor` after the fixture set was assembled. Result: the phase handoff is explicit, the fresh-context Phase 2 start is understandable, and the artifact trail is readable without reopening the whole conversation. Residual risk: live routing and runtime behavior on the main-consuming surface are still unvalidated.

## Limitation

Live validation on the main-consuming runtime is still required before claiming full brief acceptance.