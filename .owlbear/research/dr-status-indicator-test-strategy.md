# DR Status Indicator + Popover — Test Strategy

> **Owning task:** #1191 — P3-03: Test DR status indicator + popover components
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

Task #1191 requires Vitest component tests for a `StatusBarIndicator` and
`DRPopover` that surface pending Decision Requests in the Cockpit Shell status
bar. The question: what test structure, patterns, and data shapes should the
test-writer use?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|:---------:|------|
| S1 | `src/components/HealthBadge.tsx` | 1.0 | Identical structural pattern: indicator + click → popover + item list |
| S2 | `src/__tests__/HealthBadge.test.tsx` | 1.0 | Test conventions: TestFromAC naming, PDS provider wrap, data-testid, fireEvent |
| S3 | `src/hooks/useScanPolling.ts` | .95 | Polling hook pattern: interval, inFlightRef, abort, error state |
| S4 | `src/__tests__/useScanPolling_1157.test.ts` | .95 | Hook test pattern: vi.useFakeTimers, vi.stubGlobal('fetch'), renderHook, act |
| S5 | Task #1189 AC (sibling) | .90 | API contract: `GET /api/decisions/pending` → `{ count, items: [{id, task_id, agent, request_type, created, title, body_preview}] }` |
| S6 | `src/hooks/useBoard.ts` | .85 | Reference pattern per #1192 AC: abort controller, mtime check, pendingPoll dedup |
| S7 | `src/Shell.tsx` | .80 | Status bar structure: indicators rendered as siblings in `.shell__status-bar` |

## 3. Analysis

### 3.1 Test File Structure

| Test file | Target | Pattern source |
|-----------|--------|----------------|
| `src/__tests__/DRStatusIndicator_1191.test.tsx` | `StatusBarIndicator` + `DRPopover` components | S1, S2 |
| `src/__tests__/usePendingDRs_1191.test.ts` | `usePendingDRs` polling hook | S3, S4 |

### 3.2 Component Test Coverage Matrix

| AC line | Test assertion | data-testid |
|---------|---------------|-------------|
| Renders pending DR count | Text content matches count from prop/hook | `dr-indicator` |
| Attention color when count > 0 | `data-status="attention"` attribute | `dr-indicator` |
| Dormant when count = 0 | `data-status="dormant"` attribute | `dr-indicator` |
| Click opens popover | `dr-popover` appears after fireEvent.click | `dr-popover` |
| Popover renders DR items | title, agent, task_id, age text present | `dr-popover` |
| Item click triggers action | onClick callback invoked with DR id | `dr-item-{id}` |
| Empty state | dormant indicator, no popover content | `dr-indicator` |

### 3.3 Hook Test Coverage Matrix

| AC line | Test assertion |
|---------|---------------|
| Fetches `/api/decisions/pending` on mount | fetch called once with correct URL |
| Polls on interval | fetch called ≥2 after interval elapses |
| Returns `{ count, items, isLoading, error }` | State shape matches contract |
| Handles empty response | count=0, items=[] |
| Handles fetch error | error set, items stays [] |
| Cleans up interval on unmount | clearInterval called |

### 3.4 API Data Shape (from #1189)

```typescript
interface PendingDR {
  id: string
  task_id: number
  agent: string
  request_type: string
  created: string  // ISO timestamp
  title: string
  body_preview: string
}

interface PendingDRsResponse {
  count: number
  items: PendingDR[]
}
```

### 3.5 Feasibility

| Concern | Assessment |
|---------|-----------|
| PDS provider compatibility | Confirmed — HealthBadge tests work identically |
| Popover testing in jsdom | Confirmed — HealthBadge uses same conditional render pattern |
| Polling hook testing | Confirmed — useScanPolling tests demonstrate fake timers + stubGlobal |
| Navigation/modal trigger | Mock callback prop — same pattern as RepairPanel's onSuccess |

## 4. Recommendation

**Confidence: 0.92** — Follow HealthBadge + useScanPolling patterns exactly.

Two test files, ~60 tests total. The component test should use prop-driven
rendering (pass items directly) for isolation from the hook. The hook test should
use the useScanPolling timer/stub pattern. No new dependencies needed.

Challenge: FALLBACK — trivial T1 test-pattern replication, no technology choice.

## 5. Follow-up Tasks

This task IS the test task — no further decomposition needed. The AC is already
concrete and actionable for the test-writer. After research completes, this task
advances to backlog for architecture review, then the test-writer writes the tests.
