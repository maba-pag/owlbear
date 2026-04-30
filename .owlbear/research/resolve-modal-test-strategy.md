# ResolveModal Component — Test Strategy

> **Owning task:** #1193 — P3-05: Test resolve modal component
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

Task #1193 requires Vitest component tests for a `ResolveModal` — the modal
that lets users resolve pending Decision Requests by choosing a response
(approved/rejected/needs-info) and optionally adding markdown notes. The
question: what test structure, component interface, and data shapes should
the test-writer use?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|:---------:|------|
| S1 | `src/__tests__/RepairPanel_1167.test.tsx` | 1.0 | Dialog pattern: phases, confirm/cancel callbacks, error display |
| S2 | `src/__tests__/DetailTab.test.tsx` | .95 | Fetch mocking (`vi.stubGlobal`), POST assertion, 409 handling |
| S3 | `src/components/ConfirmDialog.tsx` | .90 | Minimal dialog interface: onCancel, onConfirm, data-testid |
| S4 | Brief Phase 3 — Resolve Modal spec | .95 | API contract: POST body `{response, notes}` |
| S5 | #1191 research doc | .85 | `PendingDR` data shape (id, task_id, agent, title, body_preview) |
| S6 | `vitest.setup.ts` | .80 | HTMLDialogElement polyfill, PDS error suppression |
| S7 | Task #1189 AC (sibling) | .85 | API contract for `/api/decisions/{id}/resolve` |

## 3. Analysis

### 3.1 Component Interface (Proposed)

```typescript
interface ResolveModalProps {
  dr: PendingDR | null       // null = modal closed
  onClose: () => void        // cancel/dismiss callback
  onResolved: () => void     // success callback (refresh list)
}
```

The modal renders when `dr` is non-null (conditional rendering pattern, same as
RepairPanel confirm dialog). Full DR body comes from the `PendingDR` shape or a
dedicated fetch for the full body.

### 3.2 Test File

Single file: `src/__tests__/ResolveModal_1193.test.tsx`

### 3.3 Coverage Matrix

| AC line | Test assertion | data-testid |
|---------|---------------|-------------|
| Renders full DR body as markdown | `markdown-body` contains DR body text | `resolve-modal`, `markdown-body` |
| Response selector: approved/rejected/needs-info | 3 radio/button elements with correct values | `response-selector` |
| Optional notes textarea | textarea present, initially empty, accepts input | `resolve-notes` |
| Submit calls POST with response + notes | fetch called with correct URL/method/body | `resolve-submit` |
| Modal closes on successful submission | onClose/onResolved callback invoked | — |
| Error state on failed submission | error message rendered | `resolve-error` |
| Cancel/close without mutating | onClose called, fetch NOT called | `resolve-cancel` |

### 3.4 API Contract (from Brief)

```
POST /api/decisions/{id}/resolve
Body: { "response": "approved"|"rejected"|"needs-info", "notes": "..." }
Response: 200 OK | 4xx/5xx error
```

### 3.5 Fixture Shape

```typescript
const DR_FIXTURE: PendingDR = {
  id: '42-scope-question',
  task_id: 42,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-04-30T14:30:00+02:00',
  title: 'Scope question',
  body: '## Context\n\nShould we include X?\n\n## Options\n\n1. Yes\n2. No',
}
```

### 3.6 Key Patterns to Follow

| Pattern | Source | Application |
|---------|--------|-------------|
| `vi.stubGlobal('fetch', mockFn)` + `vi.unstubAllGlobals()` | S2 | Mock POST endpoint |
| `vi.mock('react-markdown', ...)` factory mock | S2 | Render markdown as testable div |
| `PorscheDesignSystemProvider` wrapper | All | Required for PDS components |
| `waitFor(() => ..., { timeout: 500 })` | S2 | Async fetch assertions |
| `fireEvent.click` + `fireEvent.change` | S1 | User interactions |
| `data-testid` contracts | All | Query selectors |
| `TestFromAC_` describe prefix | S1, S2 | Naming convention |

### 3.7 Feasibility

| Concern | Assessment |
|---------|-----------|
| Markdown rendering mock | Confirmed — DetailTab uses exact same factory mock |
| Dialog/modal in jsdom | Confirmed — RepairPanel uses conditional div with role="dialog" |
| Form interaction testing | Confirmed — radio/select + textarea pattern in DetailTab (priority dropdown) |
| Async fetch assertions | Confirmed — DetailTab save tests use identical waitFor pattern |
| No new dependencies | Confirmed — all tools already in devDependencies |

## 4. Recommendation

**Confidence: 0.90** — Follow RepairPanel + DetailTab patterns. Single test file
with ~12-15 tests covering all 7 AC lines. Component should be prop-driven
(receives full DR object) for test isolation.

Challenge: FALLBACK — trivial T1 pattern replication from existing modal +
fetch-mocking tests. No technology choice to challenge.

## 5. Follow-up Tasks

None needed — this IS the test task. AC is concrete and actionable for the
test-writer. No blockers, no new dependencies, no decision requests.
