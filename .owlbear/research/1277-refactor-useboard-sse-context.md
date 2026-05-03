# Refactor useBoard to Consume EventSourceProvider Context

> **Owning task:** #1277 — Refactor useBoard to consume EventSourceProvider context
> **Date:** 2026-05-02 **Status:** Complete

## 1. Context and Question

`useBoard` currently calls `useEventSource('/api/events', { eventTypes: ['tasks-changed', 'decisions-changed'] })` to create its own EventSource instance. Meanwhile, `EventSourceProvider` (from #1276) is already mounted in `App.tsx` wrapping Shell, creating a **duplicate** SSE connection. The question: what's the minimal refactoring to eliminate the duplicate and have `useBoard` consume the shared context?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `hooks/useBoard.ts` (L1-145) — current SSE wiring via `useEventSource` | 1.0 |
| 2 | `hooks/EventSourceProvider.tsx` (L1-185) — context + `useSSEEvent` | 1.0 |
| 3 | `App.tsx` — already wraps Shell with `<EventSourceProvider url="/api/events">` | 1.0 |
| 4 | `Shell.tsx` — consumes `useBoard().lastDecisionsMtime` for DR refetch | 0.9 |
| 5 | `.owlbear/research/1264-activity-tab-sse-wiring.md` — parent research | 0.8 |
| 6 | `__tests__/useBoard_1261.test.ts` — 12 tests with MockEventSource | 0.9 |
| 7 | `__tests__/useBoard_1263.test.ts` — decisions-changed wiring tests | 0.9 |

## 3. Analysis

### 3.1 Current State (Duplicate Connection)

```
App.tsx → EventSourceProvider(/api/events)  ← connection #1 (unused by useBoard)
Shell  → useBoard() → useEventSource('/api/events') ← connection #2 (active)
```

Two concurrent EventSource connections hit the same `/api/events` endpoint, each spawning a server-side `awatch` thread.

### 3.2 Target State

```
App.tsx → EventSourceProvider(/api/events)  ← single connection
Shell  → useBoard() → useSSEEvent('tasks-changed')   ← reads from context
                     → useSSEEvent('decisions-changed') ← reads from context
```

### 3.3 Implementation Approach

| Step | Change | LOC delta |
|------|--------|-----------|
| 1 | Replace `import { useEventSource }` with `import { useSSEEvent }` in `useBoard.ts` | ~2 |
| 2 | Replace `useEventSource(...)` call with two `useSSEEvent()` calls | ~5 (net reduction) |
| 3 | Derive `sseStatus` and mtime values from context return | ~3 |
| 4 | Remove `useEventSource` import; keep `useConnectionHealth` for polling-fallback health | 0 |
| 5 | Update `useBoard_1261.test.ts` — wrap `renderHook` in `EventSourceProvider` context; replace `MockEventSource.simulateOpen/simulateEvent` with context value manipulation | ~40 |
| 6 | Update `useBoard_1263.test.ts` — same pattern | ~20 |

**Key design decision:** `lastDecisionsMtime` stays on `useBoard`'s return type (minimal API breakage). It reads from `useSSEEvent('decisions-changed').mtime`.

### 3.4 Test Migration Pattern

Current tests use `vi.stubGlobal('EventSource', MockEventSource)` and simulate events via `MockEventSource.instances[0].simulateOpen()`. After refactoring, `useBoard` doesn't touch `EventSource` directly — tests must provide context values.

**Option A — Mock `useSSEEvent` at module level:**
```typescript
vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn()
}))
```
Pro: Simple, isolated. Con: Tests don't exercise real context behavior.

**Option B — Render with EventSourceProvider + MockEventSource:**
```typescript
const wrapper = ({ children }) => (
  <EventSourceProvider url="/api/events">{children}</EventSourceProvider>
)
// Still use MockEventSource to simulate events flowing through the provider
```
Pro: Integration-level confidence. Con: Tests couple to provider internals.

**Recommendation: Option A for useBoard unit tests** (they test useBoard logic, not the provider). Provider integration is already tested in `EventSourceProvider_1276.test.tsx`.

### 3.5 `useEventSource` Hook Disposition

After this refactor, `useEventSource` has **zero production imports** — only test files reference it. Two options:
- Delete now (clean, but bigger diff)
- Leave and create a follow-up cleanup task

**Recommendation:** Leave + follow-up task. Minimizes scope per KISS.

### 3.6 Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| `useSSEEvent` called outside provider in tests | Test crash | Wrapper or mock |
| `lastDecisionsMtime` timing change | DR refetch delay | Same mtime propagation path |
| `health` computation drift | Wrong traffic-light color | Map context `status` → health identically |
| `useEventSource` tests (`_1260`, `_1263`) break | False failures | These test the hook directly — unaffected |

## 4. Recommendation

**Proceed with the refactoring as described.** Confidence: **0.88**

The implementation is small (~10 LOC net change in production code, ~60 LOC test updates), risk is low (provider already works, tested in #1276), and the benefit is immediate (eliminate duplicate SSE connection + align with context architecture).

Tier: **T1 — Autonomous** (refactor of existing code, no new capability, no architectural change).

Challenge: not invoked (trivial refactor with no competing approaches at close confidence).

## 5. Follow-up Tasks

1. **#1277 itself → backlog** — implementation task (this research completes the gate)
2. **New: Remove dead `useEventSource` hook after useBoard migration** — cleanup of `hooks/useEventSource.ts` and its test files once no production code imports it. Status: `research`.
