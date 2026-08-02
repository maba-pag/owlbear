---
id: 1662
title: 'P2-01: IdeasPage core — edit mode, API client, save, dirty state'
status: archived
priority: medium
created: 2026-05-18T17:42:08.330672+02:00
updated: 2026-05-20T15:46:48.325599+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1658
depends_on:
  - 1638
  - 1660
ac:
  - IdeasPage renders a loading indicator while GET `/api/ideas` is pending; 
    textarea is not present in DOM
  - IdeasPage renders a focused textarea populated with content from successful 
    GET `/api/ideas` response
  - IdeasPage save button sends PUT `/api/ideas` with textarea value; disabled 
    when textarea value equals last-saved baseline
  - IdeasPage dirty indicator visible when textarea value differs from 
    last-saved baseline; hidden after successful PUT
  - IdeasPage textarea renders placeholder 'Capture ideas here...' when content 
    is empty string
  - Cmd+S / Ctrl+S shortcut in IdeasPage sends PUT `/api/ideas` when content is 
    dirty; no-op when content matches baseline
  - IdeasPage renders error state when GET `/api/ideas` returns non-2xx; PUT 
    failure preserves textarea content, re-enables save button, and subsequent 
    button click or Cmd/Ctrl+S issues a new PUT `/api/ideas`
  - 'Route config entry in routes.ts: path `/ideas`, label `Ideas`, icon `ideas`,
    component lazy-loaded IdeasPage'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Includes creating the API client module at `serve/cockpit/web/src/api/ideas.ts` with `fetchIdeas()` and `saveIdeas()` functions using the existing `ApiError` pattern.

Page state is 100% local — no CockpitProvider extension required.

Route config entry for the tab system (#1638): path `/ideas`, lazy-loaded `IdeasPage`, nav-rail label "Ideas".

## In Scope

- `IdeasPage` component with textarea and save button
- API client module (`fetchIdeas`, `saveIdeas`)
- Dirty-state tracking (`content !== lastSavedContent`)
- Route config entry in #1638's route config array
- Loading state during initial fetch

## Out of Scope

- Preview toggle (separate task)
- Unsaved-changes guard (separate task)
- External-edit awareness (separate task)
- CockpitProvider modifications

[[2026-05-20T13:45:16+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Frontend page core only — textarea, save, dirty state, route entry. Preview/guard/external-edit in separate tasks |
| Interface clarity | PASS | All AC lines name IdeasPage or routes.ts target, specify input→output pairs |
| Dependency correctness | PASS | #1638 (tab system) archived, #1660 (backend API) archived — both satisfied |
| Module layering | PASS | Page in `src/pages/`, API client in `src/api/`, route entry in `src/routes.ts` — follows DecisionsPage/MemoryTab precedent |
| TDD compliance | PASS | Proof bundle behavioral → full TDD precedes implementation |
| KISS/YAGNI | PASS | Minimal features: textarea + save + dirty indicator + keyboard shortcut. No extras |
| Premise challenge | PASS | Cockpit needs Ideas tab per Brief; no existing alternative |
| Pattern consistency | PASS | Lazy-loaded route entry, dedicated API module (like api/tasks.ts, api/decisions.ts), page component with loading/error/content states |
| Security surface | PASS | Localhost API, fixed path via backend DI, textarea content is freeform markdown (no XSS risk since no HTML rendering in this task) |
| Single domain | PASS | Cockpit frontend (scope:cockpit-web) only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| GET /api/ideas network failure | fetch rejects / non-2xx | ApiError | Yes (AC7 requires error state) | Error message shown |
| PUT /api/ideas save failure | non-2xx response | ApiError | Yes (AC7 requires content preserved, button re-enabled) | Error feedback, no data loss |

### Design Diverge
- Trigger: skipped — single approach matches established cockpit page patterns

### Challenge Results
- Challenger: reconsider (confidence 0.58)
- Issues raised: (1) B1 precision — generic UI nouns without IdeasPage prefix; (2) AC4 literal ambiguity with \"e.g.\"; (3) AC5 missing observable output; (4) AC6 missing icon field; (5) No error-state coverage; (6) PDS textarea vs raw textarea ambiguity; (7) API module vs inline-fetch pattern precedent
- Architect response: ACCEPTED findings 1–5, REFINE applied. For (6): Brief does not mandate PDS textarea — builder decides based on UX needs; AC specifies behavior not implementation element. For (7): task body explicitly scopes API client module creation at `src/api/ideas.ts` — this is architectural direction from planner/Brief, not AC scope.

### AC Refinement Applied
- Original AC1 split into AC1 (loading) + AC2 (loaded state)
- All lines now explicitly name `IdeasPage` or `routes.ts` target (B1 compliance)
- AC5 placeholder locked to exact literal (no \"e.g.\")
- AC6 specifies observable output (PUT request + no-op condition)
- AC7 added for error handling (fetch failure + save failure)
- AC8 added for route config with icon field

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Observations
- Sibling tasks #1663, #1664, #1665 depend on #1638 but not on #1662. Since they modify IdeasPage, they logically depend on this task completing first. This is a planner dependency gap — those tasks will hit missing-component errors if scheduled before #1662 completes. Not blocking for this review (will surface during their arch reviews).
- Consolidation test #1666 exists under parent #1658, covering all implementation siblings. No gap.

### Verdict: APPROVE
### Action Taken: Refined AC from 5 to 8 lines addressing challenger findings. Advanced to todo.

[[2026-05-20T13:51:24+02:00]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx`

**Class names:**
- `TestFromAC_IdeasPageRoute` — AC8 route config
- `TestFromAC_IdeasPageLoading` — AC1 loading state
- `TestFromAC_IdeasPageLoaded` — AC2 textarea with content
- `TestFromAC_IdeasPageSave` — AC3 save button / PUT
- `TestFromAC_IdeasPageDirtyState` — AC4 dirty indicator
- `TestFromAC_IdeasPagePlaceholder` — AC5 placeholder text
- `TestFromAC_IdeasPageKeyboardShortcut` — AC6 Cmd+S / Ctrl+S
- `TestFromAC_IdeasPageError` — AC7 GET/PUT error states

**Tests per category:**
- Happy path: 13
- Edge cases: 3
- Error paths: 4
- Boundary conditions: 3
- Total: **23 tests, all FAIL** (vitest exit 1 — module load failure: `src/pages/IdeasPage.tsx` does not exist)

**AC coverage:**
| AC | Tests |
|----|-------|
| AC1 loading | 3 |
| AC2 loaded/focused | 3 |
| AC3 save/PUT/disabled | 4 |
| AC4 dirty indicator | 3 |
| AC5 placeholder | 2 |
| AC6 Cmd+S/Ctrl+S | 3 |
| AC7 GET/PUT errors | 4 |
| AC8 route config | 4 |

**RED phase confirmation:** vitest exit code 1. Suite load error: `Failed to resolve import "../pages/IdeasPage"`. Lint: clean (eslint exit 0).

**Builder targets needed:**
- `src/pages/IdeasPage.tsx` with `data-testid`: `ideas-loading`, `ideas-error`, `ideas-dirty`, `ideas-save`
- `src/api/ideas.ts` with `fetchIdeas()` / `saveIdeas()` using existing `ApiError` pattern
- `routes.ts` entry: `{ path: '/ideas', label: 'Ideas', icon: 'ideas', component: lazy(...IdeasPage) }`

[[2026-05-20T14:00:47+02:00]]
## Builder Notes

### Files Changed
- serve/cockpit/web/src/api/ideas.ts
- serve/cockpit/web/src/pages/IdeasPage.tsx
- serve/cockpit/web/src/routes.ts

### Implementation Summary
- Added ideas API client module with `fetchIdeas()` (GET `/api/ideas`) and `saveIdeas(content)` (PUT `/api/ideas`) using the existing `ApiError` + `getResponseErrorMessage` pattern.
- Implemented `IdeasPage` core behavior with local page state only:
  - initial loading state (`data-testid="ideas-loading"`),
  - loaded textarea state with autofocus and fetched content,
  - save button (`data-testid="ideas-save"`) disabled when clean / enabled when dirty,
  - dirty indicator (`data-testid="ideas-dirty"`) while `content !== lastSavedContent`,
  - placeholder literal `Capture ideas here...`,
  - Cmd+S / Ctrl+S keyboard save when dirty and no-op when clean,
  - GET/PUT error handling preserving edited content after failed PUT and re-enabling save.
- Added `/ideas` lazy route entry in `routeConfig` with label `Ideas`, icon `ideas`, component `IdeasPage`.

### Quality Evidence (quality-runner)
- RED verification before implementation:
  - Tests: failed due to missing module import (`../pages/IdeasPage` not found)
  - Exit codes: vitest 1, eslint 0
- GREEN verification after implementation:
  - Tests: 26 passed, 0 failed, 0 skipped
  - Lint: clean (0 violations)
  - Coverage overall: 93%
  - Coverage modules:
    - `src/pages/IdeasPage.tsx`: 93%
    - `src/api/ideas.ts`: 100%
    - `src/routes.ts`: 57% (existing shared route table module; task-scoped behavioral suite still met overall >=90% target)

### Module-Level Durable Test Check
- No module-level durable `IdeasPage` test file exists outside task-scoped `IdeasPage_1662.test.tsx`; skipped per workflow rule.

### Commit
- `56e2602c` — `feat: implement IdeasPage core for #1662 (builder)`

### Confidence
- 0.95

[[2026-05-20T14:18:55+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: todo
- Builder evidence reviewed: 26 tests passed, lint clean, coverage 93%. I did not rerun quality-runner because the packet was sufficient to assess proof quality.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1, AC2, AC3, AC6, AC7 | Task-scoped tests do not prove the required /api/ideas request path. Mock helpers discard request URLs and the positive assertions only count PUT calls by method or inspect a body chosen by method, so the suite would still pass if GET or PUT targeted the wrong endpoint. | serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx:33-77, 217-266, 349-390; source wiring only in serve/cockpit/web/src/api/ideas.ts:9-30 | todo |
| 2 | AC8 | Task-scoped route proof only checks that /ideas uses some React.lazy wrapper, not that it lazy-loads IdeasPage specifically. The suite would still pass if /ideas pointed at the wrong lazy component. | serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx:144-148; compare stronger precedent in serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx:35; current source wiring in serve/cockpit/web/src/routes.ts:5, 34-37 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen task-scoped GET and PUT assertions so the suite fails when IdeasPage or its API client targets any endpoint other than /api/ideas. | serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx | Finding 1 |
| 2 | test-writer | Add discriminating AC8 proof that /ideas lazy-loads IdeasPage specifically, not just any React.lazy component. | serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx | Finding 2 |

## Observations
- Source inspection suggests the implementation itself is otherwise aligned with the current AC: serve/cockpit/web/src/api/ideas.ts hard-codes GET and PUT /api/ideas, and serve/cockpit/web/src/routes.ts lazy-imports IdeasPage and wires it to /ideas.
- Non-blocking risk: after a failed PUT, IdeasPage sets errorMessage and re-enables the button, but handleSave returns early while errorMessage is set and textarea edits do not clear that state. Evidence: serve/cockpit/web/src/pages/IdeasPage.tsx:54-65, 123-124, 134. I did not route on this because AC7 does not explicitly require retry-after-failure behavior.

[[2026-05-20T14:23:06+02:00]]
## Test-Writer Notes
- Retry: added 3 tests addressing reviewer gaps. All pass against current implementation.
- Builder skip: test-only retry, all tests green — direct-to-review advance.

**New tests added to `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx`:**
- `ac2 happy: GET fetch targets exactly /api/ideas (not another endpoint)` — captures first GET call URL, asserts `/api/ideas` (Finding 1)
- `ac3 happy: PUT fetch targets exactly /api/ideas (not another endpoint)` — captures PUT call URL from save button click, asserts `/api/ideas` (Finding 1)
- `ac8 happy: /ideas route specifically lazy-loads IdeasPage (source assertion)` — reads `routes.ts` source, asserts `lazy(() => import('./pages/IdeasPage'))` regex (Finding 2)

**Quality evidence:** 29 passed, 0 failed, eslint clean. Commit `3ef4b930`.

[[2026-05-20T14:32:47+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: backlog
- Review cycle: second review cycle. Per reviewer workflow, a remaining blocking finding on this cycle routes back to backlog.
- Builder evidence reviewed first: builder packet reported 26 passed, 0 failed, lint clean, 93% coverage; test-writer retry packet reported 29 passed, 0 failed, eslint clean. I did not rerun quality-runner because the combined packet was sufficient to assess proof quality.
- AC packet: AC1-AC7 remain sufficiently mapped after direct source and task-suite review. The prior endpoint-path gap is closed by exact-path assertions at `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx:222` and `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx:311`, matching source wiring at `serve/cockpit/web/src/api/ideas.ts:9` and `serve/cockpit/web/src/api/ideas.ts:25`.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC8 | The retry still does not provide discriminating proof that the `/ideas` route entry uses the `IdeasPage` lazy import specifically. The suite proves only that `/ideas` has some `React.lazy` component and that `routes.ts` contains an `IdeasPage` lazy import somewhere, so it would false-green if `/ideas` pointed at a different lazy component while an unused `IdeasPage` lazy import remained in the file. | `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx:150-163`; `serve/cockpit/web/src/routes.ts:5`; `serve/cockpit/web/src/routes.ts:34-37` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope AC8 proof for a second-cycle retry and re-dispatch a task that binds the `/ideas` route entry to `IdeasPage` specifically rather than accepting separate `React.lazy` and source-regex assertions. | `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx`, `serve/cockpit/web/src/routes.ts` | Finding 1 |

## Observations
- Direct source inspection still shows the live route wiring is correct today: `const IdeasPage = lazy(() => import('./pages/IdeasPage'))` and the `/ideas` entry uses `component: IdeasPage` at `serve/cockpit/web/src/routes.ts:5` and `serve/cockpit/web/src/routes.ts:34-37`. The blocker is proof sufficiency, not current source behavior.
- Challenger cross-check returned `reconsider` at 0.42 confidence because the source currently satisfies AC8. I am overruling that recommendation because reviewer gate criteria require discriminating test-to-AC proof, and the retry only partially closes the prior AC8 finding.
- Non-blocking product risk: after a failed PUT, `handleSave` returns early while `errorMessage` remains set, and textarea edits do not clear that state, so the visible re-enabled button is functionally inert until reload. Evidence: `serve/cockpit/web/src/pages/IdeasPage.tsx:54-65` and `serve/cockpit/web/src/pages/IdeasPage.tsx:124`. I did not route on this because AC7 only requires preserved content and a re-enabled button.

[[2026-05-20T15:10:00+02:00]]
## Architecture Review (second-cycle re-scope)

### Context
Reviewer returned this task to backlog with one blocking finding: AC8 proof is non-discriminating. The current AC8 tests independently prove (a) `/ideas` route has a React.lazy component, and (b) routes.ts source contains an `IdeasPage` lazy import — but nothing binds these two facts together.

### AC8 Proof Gap Resolution
AC8 wording is sufficient as-is: "component lazy-loaded IdeasPage" clearly requires that the component on the `/ideas` entry IS IdeasPage. The issue is test strategy, not AC language.

**Required test approach for AC8:** Render `routeConfig.find(e => e.path === '/ideas').component` inside a `<Suspense>` boundary (with mocked fetch returning 200 / pending) and assert the resulting DOM contains IdeasPage-specific output (e.g. `data-testid="ideas-loading"` or a textarea with fetched content). This proves the route entry's component resolves to IdeasPage behavior — not just that both things exist separately.

The existing 3 non-render AC8 tests (label, icon, React.lazy check) remain valid but are insufficient alone. Replace the source-regex test with the render-based binding proof.

### Prior Tests to Remove
- `ac8 happy: /ideas route specifically lazy-loads IdeasPage (source assertion)` — source-regex is not discriminating; replaced by render proof.

### Verdict: APPROVE (re-dispatch)
### Action Taken: Added proof-strategy guidance for test-writer. Advancing to todo for test-writer retry.

[[2026-05-20T14:35:07+02:00]]
## Architecture Review (second-cycle re-scope)

Reviewer returned to backlog with AC8 proof gap: tests independently prove React.lazy at /ideas and IdeasPage import in source, but don't bind them. Implementation source is confirmed correct.

AC8 wording unchanged — sufficient as-is. Added test-writer guidance: render the route entry's component inside Suspense with mocked fetch and assert IdeasPage-specific DOM output (data-testid="ideas-loading"). This discriminates the binding. Source-regex assertion to be replaced.

Proof bundle: behavioral (unchanged)
Challenger: SKIPPED — narrow proof-strategy re-scope, no design decision
Verdict: APPROVE

[[2026-05-20T14:40:53+02:00]]
## Test-Writer Notes (second-cycle retry)

**Test file:** `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx`

**Change:** Replaced non-discriminating AC8 source-regex test with render-based binding proof per architect guidance.

**Removed:**
- `ac8 happy: /ideas route specifically lazy-loads IdeasPage (source assertion)` — source-regex proved IdeasPage lazy import exists in routes.ts and /ideas uses React.lazy, but did not bind them together

**Added:**
- `ac8 happy: /ideas route component renders IdeasPage-specific DOM when rendered (binding proof)` — renders `routeConfig.find(e => e.path === '/ideas').component` inside `<Suspense>` with pending fetch, asserts `data-testid=\"ideas-loading\"` in DOM. Fails if /ideas is wired to any component other than IdeasPage.

**Cleanup:** Removed `readFileSync`, `resolve`, `dirname`, `fileURLToPath` imports (no longer needed); added `Suspense`, `ComponentType` from react. Added `afterEach` to route describe block for fetch stub cleanup.

**Quality evidence:** 29 passed, 0 failed, eslint clean. Commit `a68fe44f`.

[[2026-05-20T14:43:53+02:00]]
## Builder Notes

### Scope
Validation-only builder pass for second-cycle retry evidence on task #1662 (`proof_bundle: behavioral`).
No source or test edits were required in this pass.

### Files Changed
- None

### Verification Evidence (quality-runner)
- Mode: `scoped`
- Task-scoped test file: `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx`
- Results: **29 passed, 0 failed, 0 skipped**
- Failed list: `[]`
- Lint paths: `serve/cockpit/web/src/`, `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx`
- Lint status: **clean** (`eslint` exit 0; no scoped violations)
- Coverage focus:
  - `serve/cockpit/web/src/pages/IdeasPage.tsx`: **93.33%**
  - `serve/cockpit/web/src/api/ideas.ts`: **100%**

### AC/Behavior Evidence Summary
- AC8 discriminating proof now exists in test suite: `/ideas` route component is rendered under `Suspense` and asserts `data-testid="ideas-loading"`, binding route entry behavior to IdeasPage-specific DOM output.
- API path proof remains discriminating for both GET and PUT (`/api/ideas`) in task-scoped tests.

### Module-Level Durable Test Check
- No additional durable IdeasPage module test file exists outside `IdeasPage_1662.test.tsx`; skipped per workflow.

### Confidence
- 0.96

[[2026-05-20T15:04:50+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: backlog
- Review cycle: third review cycle. Per reviewer loop-breaker, a blocking finding on this cycle routes to backlog.
- Builder evidence reviewed first: builder validation packet reports 29 passed, 0 failed, 0 skipped; scoped eslint clean; coverage focus 93.33% for IdeasPage and 100% for the ideas API client. I did not rerun quality-runner because the packet was sufficient to assess proof quality.
- AC packet: AC1-AC5 and AC8 are sufficiently mapped after direct source and task-suite review. The prior AC8 route-binding gap is closed by the render-based proof at [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L157-L171), matching the live route wiring at [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L5-L5) and [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L34-L37). Exact endpoint proof also remains discriminating at [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L233-L249) and [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L322-L345) against [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L9-L10) and [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L25-L30).
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC6, AC7 | The failed-save boundary is still broken. After a PUT failure, IdeasPage keeps the content dirty and visually re-enables the save button, but both button clicks and Cmd/Ctrl+S saves return early while `errorMessage` is set, so the page becomes dirty but unsaveable until reload or source changes. The task-scoped suite only proves preserved content and `disabled === false`; it never proves that retry remains operable after the failed PUT state. | Source: [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L54-L65), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L73-L80), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L124-L134). Tests: [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L459-L475), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L506-L540) | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope the dirty-after-failed-save boundary for AC6 and AC7 and re-dispatch implementation plus proof so a failed PUT leaves IdeasPage genuinely retryable by button and Cmd/Ctrl+S, with task-scoped assertions that a second save attempt actually issues PUT `/api/ideas`. | serve/cockpit/web/src/pages/IdeasPage.tsx; serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx | Finding 1 |

## Observations
- Challenger cross-check returned `reconsider` at 0.46 confidence because prior reviews had treated the same save-retry trap as non-blocking. I am overruling that recommendation because AC6 and AC7 together make the dirty-after-failed-save boundary in-scope, and the current suite still false-greens there.
- No additional safety or security issue found in the scoped files. The API client remains fixed-path same-origin fetch logic at [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L9-L30), and the `/ideas` route remains statically lazy-wired to IdeasPage at [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L5-L37).

[[2026-05-20T15:15:23+02:00]]
## Architecture Review (third-cycle re-scope)

### Context
Reviewer returned this task from third review cycle with one blocking finding: after a failed PUT, `handleSave` guards on `errorMessage` (line 54 of IdeasPage.tsx), making the save button and Cmd/Ctrl+S inert despite appearing enabled. Tests only prove content preservation and button `disabled === false`; they never prove a second PUT is issued.

### AC7 Refinement
AC7 now reads: "…PUT failure preserves textarea content, re-enables save button, **and subsequent button click or Cmd/Ctrl+S issues a new PUT `/api/ideas`**"

This closes the retry specification gap that caused three review cycles of interpretation drift.

### Builder Guidance (source fix)
The ONLY compliant fix is removing `|| errorMessage` from the `handleSave` guard at `serve/cockpit/web/src/pages/IdeasPage.tsx:54`. This provides immediate retry semantics. Do NOT use "clear errorMessage on content change" — that requires an edit before retry, which is a different behavior than what AC7 specifies. The GET-failure case is already naturally guarded by `!isDirty` (content = lastSavedContent = '' → not dirty → returns early).

### Test-Writer Guidance (retry proof)
Add discriminating tests in `TestFromAC_IdeasPageError`:
1. `ac7 retry: button click after failed PUT issues a second PUT /api/ideas` — first PUT fails (500), then click save again, assert 2 total PUT calls to `/api/ideas`
2. `ac7 retry: Cmd+S after failed PUT issues a second PUT /api/ideas` — first PUT fails, then Cmd+S, assert 2 total PUT calls to `/api/ideas`

Both tests must verify the PUT call count AND the target URL to be discriminating. Remove or update any existing tests that assert the button is re-enabled after failed PUT without testing actual retry.

### Challenge Results
- Challenger: block (confidence 0.44)
- Issues: (1) remedy mismatch — only removing errorMessage guard provides immediate retry; (2) AC6/AC7 both affected; (3) AC7 bundles multiple concerns
- Architect response: ACCEPTED findings 1-2, added explicit builder guidance restricting fix to guard removal. REBUTTED block recommendation — architecture review advances to todo so pipeline agents can fix and prove. AC7 bundling retained (test-writer already structures sub-behaviors within describe block; splitting at cycle 3 adds churn).

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (add retry tests, fix source, re-verify)

### Prior Tests to Remove
- None (prior non-discriminating AC8 test was already replaced in cycle 2)

### Verdict: APPROVE (re-dispatch)
### Action Taken: Refined AC7 to require retry capability. Added builder/test-writer guidance. Advanced to todo for test-writer + builder retry.

[[2026-05-20T15:19:30+02:00]]
## Test-Writer Notes
- Retry (third cycle): added 2 discriminating tests for AC7 retry-after-failure requirement.
- Test file: `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx`
- Class: `TestFromAC_IdeasPageError`
- New tests (both FAIL — `AssertionError: expected 1 to be 2`):
  - `ac7 retry: button click after failed PUT issues a second PUT /api/ideas`
  - `ac7 retry: Cmd+S after failed PUT issues a second PUT /api/ideas`
- Root cause proven: `handleSave` guard `|| errorMessage` at `IdeasPage.tsx:54` blocks the second PUT — only 1 PUT issued instead of 2.
- Existing 29 tests: all still pass.
- Total: 31 tests, 2 FAIL, lint clean.
- AC7 header comment updated to reflect refined wording.
- Commit: `e36c61a0`

[[2026-05-20T15:26:09+02:00]]
## Builder Notes
- Implementation: removed retry-blocking guard in `serve/cockpit/web/src/pages/IdeasPage.tsx` so `handleSave` no longer exits when `errorMessage` is set after a failed PUT.
- Files changed: `serve/cockpit/web/src/pages/IdeasPage.tsx`
- Tests: 31 task-scoped tests passed (`serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx`), 0 failed, 0 skipped.
- Coverage: 94.2% overall for scoped run; `src/pages/IdeasPage.tsx` 93.33%, `src/api/ideas.ts` 100%.
- Lint: clean (`eslint` clean: true, no violations).
- Approach: minimal AC7-compliant fix per architecture guidance by allowing immediate retry after failed save via button and Cmd/Ctrl+S without requiring intermediate edits.
- Commit: `1bffed6c` — `fix: allow IdeasPage retry after failed save (#1662, builder)`
- Confidence: 0.98

[[2026-05-20T15:39:31+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1662 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: latest builder packet reports 31 passed, 0 failed, 0 skipped; scoped eslint clean; scoped coverage 94.2% overall with 93.33% for [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L1) and 100% for [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L1). I did not rerun quality-runner because the packet was sufficient and internally consistent.
- Blocking findings: none.
- AC evidence map:
| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L92) | [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L185), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L194) | PASS |
| AC2 | [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L24), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L49) | [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L221), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L228), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L234) | PASS |
| AC3 | [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L25), [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L30), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L54), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L60), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L61), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L130) | [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L283), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L310), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L323) | PASS |
| AC4 | [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L61), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L119) | [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L362), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L367) | PASS |
| AC5 | [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L126) | [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L395) | PASS |
| AC6 | [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L54), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L73), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L79) | [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L416), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L438), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L460) | PASS |
| AC7 | [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L32), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L54), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L65), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L102), [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L130), [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L9), [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L25) | [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L487), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L497), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L507), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L528), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L549), [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L580) | PASS |
| AC8 | [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L5), [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L34), [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L35), [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L36), [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L37) | [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L158) | PASS |
- Proof sufficiency: the earlier false-green risks are closed by exact endpoint assertions at [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L234) and [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L323), render-based route binding proof at [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L158), and retry-after-failure assertions at [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L549) and [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L580) against the shared save path at [serve/cockpit/web/src/pages/IdeasPage.tsx](serve/cockpit/web/src/pages/IdeasPage.tsx#L54).

## Observations
- Challenger returned `reconsider` on two narrower points: a literal reading of AC6 "no-op" and the absence of a Ctrl+S-after-failed-PUT retry test. I am overruling that challenge. In this task, AC6/AC7 are scoped to save-side effects, the packet already proves the Ctrl branch on the dirty path at [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L438), and the failed-save regression that caused the last rejection lived in the shared [handleSave guard](serve/cockpit/web/src/pages/IdeasPage.tsx#L54) now exercised by both retry paths at [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L549) and [serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx](serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx#L580).
- No additional safety issues found in scoped files; the API client remains fixed-path same-origin fetch logic at [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L9) and [serve/cockpit/web/src/api/ideas.ts](serve/cockpit/web/src/api/ideas.ts#L25).

[[2026-05-20T15:43:36+02:00]]
## Docs Gate

### Checklist

**Item 1 — README Verification**
Convention mapping: `serve/cockpit/web/src/**` → `serve/cockpit/README.md`.
Changed files: `src/api/ideas.ts` (new), `src/pages/IdeasPage.tsx` (new), `src/routes.ts` (modified).
Finding: No #1662 entry existed in the README changelog section. The backend Ideas API section (lines 632–641, added by #1660) was present but the frontend page was undocumented.
Fix: Added `- #1662 adds the Ideas tab at /ideas.` entry between #1648 and #1671. Entry documents `src/api/ideas.ts` API client, `IdeasPage.tsx` behaviors (loading/error/dirty/save/placeholder/keyboard/retry), route entry shape, and test count (31 tests).
Layer-1 grep: `#1662` confirmed present at line 485.
Layer-2 editorial: entry is coherent, accurate against source files, no contradictions with adjacent content.
Commit: `f7f64448` — `docs: document IdeasPage tab in cockpit README (#1662, doc-writer)`

**Item 2 — External Attribution**
N/A — no external sources influenced implementation per builder notes.

**Item 3 — Research Doc**
N/A — no research artifact for this task.

**Item 4 — Deletion Detection**
No source files were deleted. Only additions (`ideas.ts`, `IdeasPage.tsx`) and a modification (`routes.ts`). No orphaned references.

**Scratch cleanup:** No `.owlbear/scratch/1662-*` files found — already clean.

[[2026-05-20T15:46:48+02:00]]
## Audit

### Regression Detection
Quality-runner full-suite: 2276 passed, 0 failed, 11 skipped. One ESLint violation in `SidecarUX.test.tsx` (unrelated background debt — `@typescript-eslint/no-unused-vars`). No task-scope regressions.

### Intent Verification
Changed files (`src/api/ideas.ts`, `src/pages/IdeasPage.tsx`, `src/routes.ts`, `src/__tests__/IdeasPage_1662.test.tsx`, `serve/cockpit/README.md`) all within cockpit-web domain. Implementation matches stated purpose: IdeasPage core with textarea, API client, save, dirty state, keyboard shortcut, error handling with retry, and lazy-loaded route entry. No extraneous scope.

### Architect Quality
Score: 4/5. AC refined from 5 to 8 lines through challenger process. Specificity high — each line names IdeasPage or routes.ts with input→output pairs. One significant gap: retry-after-failure semantics not specified until cycle 3 escalation, causing three review cycles. Architect responded effectively once escalated.

### Commit Integrity
7 commits verified in git history:
- `585edb64` test: add IdeasPage tests (test-writer, RED)
- `56e2602c` feat: implement IdeasPage core (builder, GREEN)
- `3ef4b930` test: add retry URL/route identity tests (test-writer)
- `a68fe44f` test: replace AC8 source-regex with render proof (test-writer)
- `e36c61a0` test: add retry tests for error recovery (test-writer)
- `1bffed6c` fix: allow IdeasPage retry after failed save (builder)
- `f7f64448` docs: document IdeasPage tab in cockpit README (doc-writer)

All commits reference #1662, use correct types, and carry agent attribution.

### Deduction Breakdown
| Criterion | Deduction |
|-----------|----------|
| Regression failures | 0 |
| Intent mismatch | 0 |
| Evidence integrity concern | 0 |
| Lint violations | 0 |
| AC quality ≤ 3 | 0 (score=4) |
| Missing reviewer evidence | 0 |

### Confidence: 1.00
### Action: ARCHIVE
