# Sidecar (Detail + Activity tabs) + Polling Tests — RED Phase

> **Owning task:** #935 — P2-06: RED — Sidecar (Detail + Activity tabs) + polling tests
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #935 requires writing failing Vitest + RTL tests for 4 new modules: DetailTab, ActivityTab, usePolling hook, and optimistic UI. These cover the sidecar panel (task editing, conflict detection, history, sessions, filtering), polling infrastructure (mtime-based 3s interval, health states), and optimistic state management.

**Key questions:** (a) How should RED tests import non-existent components? (b) What mocking strategy for `react-markdown`? (c) How to test a polling hook with fake timers? (d) Should optimistic UI tests be hook tests or pure function tests?

## 2. Sources Studied

| # | Source | Relevance | What was used |
|---|--------|-----------|---------------|
| S1 | `src/__tests__/KanbanBoard.test.tsx` — existing RED test patterns | 1.0 | fetch stub pattern, fixture structure, PDS+Router wrapping, `data-testid` queries |
| S2 | `src/__tests__/KanbanBoard_963.test.tsx` — named export verification | 0.95 | Pattern for testing non-existent exports (resolves to `undefined`) |
| S3 | `src/__tests__/Shell.test.tsx` — sidecar region, tab structure | 0.90 | Sidecar DOM structure: `data-region="sidecar"`, `p-tabs`, `data-tab-content` |
| S4 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — edit endpoint | 1.0 | 409 conflict detection via `updated` snapshot, `EditRequest` fields, allowlist |
| S5 | `serve/cockpit/src/owlbear_cockpit/routes/read.py` — sessions endpoint | 0.95 | `GET /api/sessions?filter=active`, `SessionOut` fields |
| S6 | `serve/cockpit/src/owlbear_cockpit/models.py` — response schemas | 0.95 | `TaskDetailOut`, `SessionOut`, `SessionListOut` field contracts |
| S7 | `vitest.setup.ts` — test environment config | 0.85 | jsdom, PDS polyfill, HTMLDialogElement.showModal polyfill |
| S8 | react-markdown npm docs (v10.1.0) | 0.80 | Safe by default (no dangerouslySetInnerHTML), `skipHtml` option |
| S9 | Vitest mocking guide — fake timers, `vi.useFakeTimers()` | 0.85 | `advanceTimersByTime`, `vi.stubGlobal('fetch')` for polling tests |
| S10 | `@testing-library/react` v16 — `renderHook` API | 0.80 | Hook testing without wrapper component for usePolling |
| S11 | `.owlbear/research/933-kanban-board-green.md` — architecture decisions | 0.85 | Plain fetch hook, TanStack Query deferred, mtime for polling |

## 3. Analysis

### 3.1 RED Phase Import Strategy

Tests must compile and run (then fail). Two patterns exist in codebase:

| Pattern | Example | Works when module doesn't exist? |
|---------|---------|----------------------------------|
| A. Import existing file, check named exports | KanbanBoard_963.test.tsx | Yes — undefined exports, not import error |
| B. Import non-existent file directly | N/A | No — Vitest throws MODULE_NOT_FOUND |

**For #935:** All 4 target files are new (`DetailTab.tsx`, `ActivityTab.tsx`, `usePolling.ts`, `optimistic.ts`). Pattern B would error, not fail. The test-writer must create minimal stub files (empty component/hook that returns null/empty state) so tests compile, then fail on behavior assertions. This is standard TDD RED-phase practice.

### 3.2 react-markdown Mocking

react-markdown is not in `package.json` yet. Two options:

| Option | Pros | Cons |
|--------|------|------|
| A. Install react-markdown, test rendered output | Real integration | Adds dependency before GREEN phase |
| B. Mock react-markdown in tests | No new deps, tests are self-contained | Mock may diverge from real behavior |

**Recommendation: Option B** (confidence: 0.85). RED tests should mock react-markdown with a simple passthrough component (`vi.mock('react-markdown', () => ({ default: ({ children }) => <div data-testid="markdown-body">{children}</div> }))`). The real dependency is installed during GREEN phase. This matches the YAGNI principle — no production deps until needed.

For the XSS/sanitization AC, test that raw HTML in markdown input does not appear as HTML in DOM output. The mock can simulate this by stripping HTML tags.

### 3.3 Polling Hook Testing

| Technique | Use case | Vitest API |
|-----------|----------|------------|
| Fake timers | Control 3s interval | `vi.useFakeTimers()`, `vi.advanceTimersByTime(3000)` |
| `renderHook` | Test hook lifecycle | `import { renderHook, act } from '@testing-library/react'` |
| Fetch count tracking | Verify poll count, skip cycle | `vi.fn()` call count on fetch mock |
| Mtime change detection | Poll only fetches when mtime changes | Mock fetch returns varying `mtime` values |

Connection health states map to poll timing:

| State | Condition | data-testid |
|-------|-----------|-------------|
| green | Last successful poll within threshold (~6s) | `health-green` |
| yellow | Last poll OK but lagging (>6s, <15s) | `health-yellow` |
| red | No successful poll for >15s | `health-red` |

### 3.4 Optimistic UI Pattern

| Option | Pattern | Testing approach |
|--------|---------|------------------|
| A. Custom hook (`useOptimistic`) | Hook wraps state + rollback | `renderHook` + `act()` |
| B. Pure functions | `applyOptimistic(state, mutation)` + `rollback(state, snapshot)` | Direct function call assertions |
| C. Reducer pattern | `dispatch({ type: 'optimistic', payload })` | Reducer unit tests |

**Recommendation: Option A** (confidence: 0.80). Hook tests with `renderHook` align with existing codebase patterns (useBoard hook). Test: mutate → verify immediate state → simulate API error → verify rollback to snapshot.

### 3.5 Detail Tab — API Contract Mapping

From `EditRequest` (mutation.py) and `TaskDetailOut` (models.py):

| Field | Editable | Control type | Test approach |
|-------|----------|-------------|---------------|
| title | ✅ | text input | Type, verify value change |
| tags | ✅ | chip/multi-select | Add/remove chip, verify |
| priority | ✅ | dropdown | Select option, verify |
| depends_on | ✅ | number list | Add/remove, verify |
| parent | ✅ | number input | Type, verify |
| block_reason | ✅ | text input | Type, verify; null = unblock |
| body | ✅ | markdown editor | Toggle edit mode, type, verify |
| id | ❌ read-only | text | No edit affordance in DOM |
| created | ❌ read-only | text | No edit affordance in DOM |
| claimed | ❌ read-only | text | No edit affordance in DOM |
| status | ❌ read-only | text | No edit affordance in DOM |

### 3.6 Trade-off: Test Granularity

| Approach | # tests | Maintainability | Signal quality |
|----------|---------|-----------------|----------------|
| A. Fine-grained (1 assertion per test) | ~60-80 | High — easy to pinpoint failures | High |
| B. Grouped (3-5 assertions per describe) | ~30-40 | Medium | Medium |
| C. Large integration tests | ~10-15 | Low — hard to diagnose | Low |

**Recommendation: Option A** (confidence: 0.85). Matches existing codebase pattern (KanbanBoard.test.tsx uses 1-2 assertions per `it` block).

## 4. Recommendation

Write 4 test files per the AC with these patterns:

1. **Stub files first** — create minimal empty exports for DetailTab, ActivityTab, usePolling, optimistic so tests compile.
2. **Mock react-markdown** — passthrough component in test, no npm install.
3. **Fake timers for polling** — `vi.useFakeTimers()` + `renderHook` for usePolling.
4. **Hook-based optimistic tests** — `renderHook` for useOptimistic.
5. **fetch stubs follow existing pattern** — `vi.stubGlobal('fetch', vi.fn(...))`.
6. **Fine-grained tests** — 1-2 assertions per `it` block, organized by AC section.

**Confidence: 0.85**

Challenge: skipped — testing patterns are well-established in codebase, no competing architectural approaches. All decisions follow prior art from #927, #931, #933 research.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #935 itself is the follow-up from the Phase 2 decomposition (#920). The test-writer should proceed with implementation.
