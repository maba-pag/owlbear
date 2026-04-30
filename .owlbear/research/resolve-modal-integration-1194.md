# ResolveModal Integration — Shell Wiring & Data Path

> **Owning task:** #1194 — P3-06: Implement resolve modal
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

Task #1194 requires ResolveModal component + integration with DRPopover item
click. The component itself is already built and passes all 8 tests from #1193.
The question: what remains, and how should the Shell integration work?

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| S1 | `src/components/ResolveModal.tsx` | 1.0 | Complete component — radio selector, POST, error state, cancel |
| S2 | `src/Shell.tsx` (lines 21, 56–60) | 1.0 | `selectedDRId` state + `onItemClick={setSelectedDRId}` handoff from #1192 |
| S3 | `src/__tests__/Shell_1192.test.tsx` AC6 | .95 | Confirms onItemClick wires to setSelectedDRId for #1194 |
| S4 | `decisions.py` `/decisions/pending` endpoint | 1.0 | Returns `body_preview` (200 chars), NOT full `body` |
| S5 | `src/hooks/usePendingDRs.ts` | .95 | `PendingDR` type has `body_preview` only |
| S6 | `src/components/DetailTab.tsx` line 121 | .90 | `ReactMarkdown` + `remarkGfm` + `rehypeSanitize` pattern |
| S7 | `src/__tests__/ResolveModal_1193.test.tsx` | 1.0 | 8/8 tests pass; expects `PendingDRWithBody.body` prop |

## 3. Analysis

### 3.1 Component Status

| AC line | Status | Evidence |
|---------|--------|----------|
| Shows full DR body as markdown | ✅ DONE | ReactMarkdown renders `dr.body` |
| Response selector (3 options) | ✅ DONE | Radio fieldset: approved/rejected/needs-info |
| Notes textarea | ✅ DONE | data-testid="resolve-notes" |
| POST /api/decisions/{id}/resolve | ✅ DONE | fetch call in handleSubmit |
| Close on success | ✅ DONE | onResolved() + onClose() |
| Error on failure | ✅ DONE | data-testid="resolve-error" |
| Cancel without side effects | ✅ DONE | onClose() only, no fetch |
| All #1193 tests pass | ✅ DONE | 8/8 green |

### 3.2 Integration Gap — Data Path

| Option | Approach | Pro | Con |
|--------|----------|-----|-----|
| A: Add `body` to list response | 1-line change in existing `decisions.py` | Minimal, no new route | Slightly larger payloads (negligible: 0–3 DRs) |
| B: New `GET /decisions/{id}` | Proper REST detail endpoint | Lazy-loads on demand | "OUT: backend endpoints" scope conflict; extra round-trip |
| C: Use `body_preview` as `body` | Zero backend change | No dependency | Violates AC1 ("full DR body"); truncated at 200 chars |

**Recommendation: Option A** (confidence: .85). Adding `body` alongside `body_preview`
in the existing list response is a 1-line enrichment, not a new endpoint. The
pending list has ≤3 items typically; full body is <5KB each. The "OUT: backend"
scope note targets new route creation, not payload enrichment.

### 3.3 Integration Approach (Shell wiring)

```
Shell.tsx:
1. Import ResolveModal
2. Derive selectedDR from pendingDRItems.find(i => i.id === selectedDRId)
3. Render <ResolveModal dr={selectedDR} onClose={clear} onResolved={repoll} />
4. onResolved triggers usePendingDRs refresh
```

### 3.4 Plugin Gap

ResolveModal uses bare `<ReactMarkdown>` without `remarkGfm` or `rehypeSanitize`.
DetailTab (the existing pattern) uses both. Builder should add both plugins for
GFM rendering and XSS protection consistency.

## 4. Recommendation

T1 — Autonomous. Straightforward integration with clear patterns established by
#1192 (state handoff) and existing DetailTab (markdown plugins). One backend
enrichment (add `body` to list response) fits within the task's implementation
boundary.

Challenge: SKIP — trivial integration; no architectural decision or trade-off
requiring adversarial review.

Confidence in approach: .85 (small risk: scope interpretation of "OUT: backend"
may require builder to defer the `body` field addition to a follow-up if
reviewer objects; fallback is Option C with a follow-up task).

## 5. Follow-up Tasks

Implementation is the task itself (#1194). No separate follow-ups needed —
all work fits within existing ACs. The builder should:

1. Add `body` to `/api/decisions/pending` response (1 line in `decisions.py`)
2. Update `PendingDR` type to include `body: string`
3. Wire Shell: import ResolveModal, conditional render on `selectedDRId`
4. Add `remarkGfm` + `rehypeSanitize` to ResolveModal's ReactMarkdown
5. Verify all 8 tests from #1193 still pass
