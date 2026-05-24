# ResolveModal Snapshot Guard — Integration Research

> **Owning task:** #1647 — P2-02: ResolveModal integration + modal snapshot SSE guard
> **Date:** 2026-05-20 **Status:** Complete

## 1. Context and Question

ResolveModal currently receives `dr` as a live prop derived from `useDRState().selectedDR`. This value re-derives on every SSE `decisions-changed` refetch (`pendingDRItems.find(...)`). If an agent modifies the DR file while a user has the modal open with a partially-filled form, the rendered title/body could change and `notes`/`response` context becomes stale. The task asks: how should we implement a snapshot guard to decouple the open modal from live data updates?

## 2. Sources Studied

| Source | URL/Path | Relevance |
|--------|----------|-----------|
| React docs — useState lazy initializer | react.dev/reference/react/useState | 1.0 |
| Stack Overflow — modal data via State Hook | stackoverflow.com/questions/74123582 | 0.8 |
| Codebase — Shell conditional rendering | `serve/cockpit/web/src/Shell.tsx` L748-758 | 1.0 |
| Codebase — CockpitProvider selectedDR derivation | `hooks/CockpitProvider.tsx` L196 | 1.0 |
| Codebase — ResolveModal component | `components/ResolveModal.tsx` | 1.0 |
| Brief — Architecture decisions | `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md` | 0.9 |

## 3. Analysis

### Current Data Flow

```
SSE → refetchPendingDRs() → pendingDRItems updates
→ selectedDR = items.find(id === selectedDRId)
→ Shell passes dr={selectedDR} to ResolveModal
→ ResolveModal re-renders with new dr.title / dr.body
```

### Implementation Options

| Criteria | A: useState initializer (modal-local) | B: Provider-level snapshot state | C: useRef to freeze |
|----------|---------------------------------------|----------------------------------|---------------------|
| LOC change | ~5 (ResolveModal only) | ~15 (Provider + Shell + modal) | ~8 (ResolveModal) |
| Scope | Component-local | Cross-component | Component-local |
| Complexity | Trivial — idiomatic React | Couples snapshot to provider | Ref semantics, no re-render trigger |
| Unmount = reset | Yes (natural) | Must manually clear | Yes but needs careful null handling |
| Brief alignment | "snapshot is modal-local state management" | Contradicts brief | Acceptable but less idiomatic |
| AC3 (reopen freshness) | Automatic — remount = fresh init | Requires explicit wiring | Automatic |
| Testability | Standard prop/render assertion | Requires provider mock changes | Harder — ref is opaque |

**Recommendation: Option A** — confidence: 0.92

### Why Option A Works

Shell renders ResolveModal only when `selectedDR !== null`:
```tsx
{selectedDR ? <ResolveModal dr={selectedDR} ... /> : null}
```

This means:
- **Mount** = modal opens (dr guaranteed non-null)
- **Unmount** = modal closes (selectedDR becomes null)

The snapshot pattern:
```tsx
const [snapshotDR] = useState<PendingDRWithBody>(() => dr!)
// Use snapshotDR instead of dr for rendering
```

- AC2 satisfied: `snapshotDR` never updates after mount, regardless of prop changes
- AC3 satisfied: closing unmounts the component; reopening remounts with fresh `dr` → fresh initializer

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| DR removed from list during editing → modal unmounts | Low | Acceptable per brief (no draft persistence) |
| TypeScript non-null assertion on `dr` in initializer | Negligible | Shell guarantees non-null via conditional render |
| `handleSubmit` uses snapshot ID vs live ID | None | ID doesn't change for same DR; submit targets snapshot.id |

### AC1 Status: Already Implemented

DecisionsPage already calls `drState.setSelectedDRId(item.id)` on click (line 39). Shell renders the shared ResolveModal at L748. Both DRStatusIndicator (via `onItemClick={setSelectedDRId}`) and DecisionsPage share the same instance. No work needed for AC1.

## 4. Recommendation

**Implement Option A** — `useState` lazy initializer inside ResolveModal. Replace all render references to `dr` with `snapshotDR`. ~5 LOC net change in one file.

Challenge: FALLBACK — trivial implementation, single established React pattern, no architectural trade-off warrants adversarial review.

Confidence: 0.92 — only uncertainty is whether `handleSubmit`'s `dr` reference needs updating (it does, trivially).

## 5. Follow-up Tasks

Task advances directly to backlog — AC1 is complete, AC2/AC3 require only the snapshot implementation (~5 LOC in ResolveModal.tsx). Single atomic task, no decomposition needed.
