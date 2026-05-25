---
id: 1857
title: 'P1-07: Cockpit frontend — minimal resolver wiring to new API'
status: review
priority: critical
created: 2026-05-24T20:59:01.793534+02:00
updated: 2026-05-25T13:24:49.636581+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - frontend
parent: 1850
depends_on:
  - 1856
ac:
  - 'AC1: usePendingDRs hook (or replacement) fetches from GET /api/requests/pending
    (bare JSON array of PendingRequestResponse objects); the resolve modal renders
    title and summary from structured response fields in the DOM — does NOT derive
    title or summary via getDecisionBrief() body-text parsing. DecisionsPage list
    continues rendering without runtime errors after the data-source switch (minimal
    field-name mapping only; card redesign is P2-03 scope).'
  - 'AC2: Resolve submission calls POST /api/requests/{request_id}/resolve with JSON
    body {selected_option_id: string|null, free_text: string|null, kind: "decision"|"action"|null};
    for decision-kind, selected_option_id is the user-chosen options[].option_id;
    for action-kind, kind:"action" is sent (backend bare-Complete normalization).
    On HTTP 200, modal closes and pending-list hook refetches.'
  - "AC3: When the request's kind===\"decision\", the modal renders each options[].label
    from the structured response as a selectable control that populates selected_option_id
    on selection. When kind===\"action\", a \"Complete\" button replaces option controls;
    clicking it triggers the resolve submission with kind:\"action\"."
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Adapt existing resolve modal to consume new `/api/requests/pending` response shape
- Submit to new `/api/requests/{id}/resolve` endpoint
- Basic display of structured fields (title, summary, options labels)
- Functional but not polished (Step 2 handles full design)

**Out of scope:**
- Confidence bars, recommended badges (P2-01)
- Full option card design (P2-01)
- List view cards (P2-03)
- Removal of old regex-based title extraction (P2-06)

## Test scope
`npm test` in `serve/cockpit/web/`

[[2026-05-25T12:39:15+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Modal + hook adaptation for one new API; list-page minimal mapping is consequential, not separate concern |
| Interface clarity | PASS (after refinement) | AC now names exact endpoint shapes, payload fields, kind-branching, and observable DOM targets |
| Dependency correctness | PASS | #1856 archived/completed; response shape from routes/requests.py confirmed |
| Module layering | PASS | Frontend consuming backend API; no reverse dependency |
| TDD compliance | PASS | Test scope: npm test in serve/cockpit/web/ (vitest); existing test infra for ResolveModal |
| KISS/YAGNI | PASS | Minimal wiring only; excludes P2 polish features |
| Premise challenge | PASS | New backend API exists (#1856), frontend must consume it |
| Pattern consistency | PASS | Follows existing hooks/api/components pattern |
| Security surface | PASS | No new user input beyond existing patterns; backend validates |
| Single domain | PASS | Cockpit web frontend only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| GET /api/requests/pending fetch | Network/server error | fetch rejection | Yes (existing hook error state) | Empty list + error message |
| POST resolve fetch | Network/server error | fetch rejection | Yes (existing modal error state) | Inline error notification |
| POST resolve 422 (missing option/text) | Client-side validation gap | ApiError | Should be prevented by UI controls | Error notification shown |

### Design Diverge
- Trigger: skipped — single clear approach (adapt shared hook to new API, update modal rendering, minimal list-page field mapping)

### Challenge Results
- Challenger: reconsider (confidence 0.34)
- Findings: (1) shared hook coupling — usePendingDRs feeds both modal and list page, new API has different shape (bare array vs object wrapper) and field names; (2) decisionBrief.ts dependency — modal currently uses regex extraction; (3) AC wording — \"displays\" without observable target, missing kind field; (4) stale frontend tests lock old contract; (5) proof-bundle questioned
- Architect response: Accepted findings 1-3. Refined AC to: (a) explicitly acknowledge list-page minimal adaptation is in-scope, (b) name getDecisionBrief() as the forbidden path for title/summary derivation, (c) specify exact payload shape including kind field, (d) name selectable control and Complete button as DOM targets. Rebutted finding 5 — smoke remains appropriate for frontend wiring with vitest coverage. Finding 4 (stale tests) is test-writer scope, not AC scope.

### Proof-Bundle Validation
- Planner assignment: smoke
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC from 3 original lines to 3 precise lines addressing: (a) shared hook + list-page continuity constraint, (b) exact resolve payload shape with kind field, (c) decision/action branching with named DOM controls, (d) explicit prohibition of getDecisionBrief() for title/summary. Advanced to todo.

[[2026-05-25T12:48:21+02:00]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/ResolveWiring_1857.test.tsx`
- Class: `TestFromAC_ResolveWiring`
- Toolchain: vitest (`npm test` in `serve/cockpit/web/`)
- proof_bundle: smoke — 1 test per AC line

| Test | Category | AC | Failure reason |
|------|----------|----|----------------|
| usePendingDRs fetches from GET /api/requests/pending | happy | AC1 | URL is `/api/decisions/pending`, not `/api/requests/pending` |
| resolve submit sends selected_option_id and kind to POST /api/requests/{id}/resolve | happy | AC2 | No option selection controls exist; assertion `expect(null).not.toBeNull()` fails |
| decision kind renders options[].label as selectable controls; action kind renders Complete button | happy | AC3 | 0 `[data-testid^="resolve-option-"]` controls found; submit text is "Submit Decision" not "Complete" |

- Total: 3 tests, all FAIL (vitest exit 1), lint clean (eslint exit 0)

**AC coverage:**
| AC | Tests |
|----|-------|
| AC1: hook fetches GET /api/requests/pending | 1 (AC1 smoke) |
| AC2: resolve POST /api/requests/{id}/resolve with {selected_option_id, free_text, kind} | 1 (AC2 smoke) |
| AC3: decision kind → option labels; action kind → Complete button | 1 (AC3 smoke) |

[[2026-05-25T13:00:30+02:00]]
## Builder Notes
- Implementation: updated `serve/cockpit/web/src/hooks/usePendingDRs.ts`, `serve/cockpit/web/src/api/decisions.ts`, and `serve/cockpit/web/src/components/ResolveModal.tsx`.
- Approach: switched pending hook to GET `/api/requests/pending` with minimal field mapping to existing `PendingDR` shape; switched resolve client to POST `/api/requests/{id}/resolve` with `{selected_option_id, free_text, kind}`; rewired resolver UI to structured fields (`title`, `summary`, `kind`, `options`) and decision/action branching (`resolve-option-{option_id}` controls for decision, `Complete` submit for action).
- Tests (task smoke): quality-runner scoped run on `serve/cockpit/web/src/__tests__/ResolveWiring_1857.test.tsx` => 3 passed, 0 failed.
- Lint: clean (eslint clean on touched source files + task test file).
- Coverage: smoke bundle verification used; additional coverage run reported module coverage below 90% for this narrow smoke test scope (expected for smoke-only proof).
- Cross-check: module-level legacy tests were sampled and show contract drift against old `/api/decisions/*` expectations; task AC behavior is validated by `ResolveWiring_1857` smoke tests.
- Commit: `65157d0d` (`feat: wire resolver to structured requests API (#1857, builder)`).

[[2026-05-25T13:11:06+02:00]]
## Reviewer Verdict (orchestrator-appended)
FAIL → todo | Implementation aligned but proof insufficient for AC1 (normalization path untested) and AC2 action-branch (no submit test). Test-writer must fix fixtures to use real backend shape and add action-kind submit test.
