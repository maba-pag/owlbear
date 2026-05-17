# Data Quality Stance — Cockpit Decisions Tab

## Position Summary

The data layer is structurally sound for V1: the response shape covers list + detail rendering, SSE reactivity is wired, and the resolve flow has optimistic concurrency via ERR_STALE. Three genuine data quality gaps need attention before the tab ships. Two structural observations matter for the fast-follow (resolved DRs).

## Gap Analysis

### G1 — Modal state loss on SSE refetch (Critical)

When another actor resolves a DR while the user has the ResolveModal open, the SSE `decisions-changed` event triggers `refetchPendingDRs()`. The resolved DR disappears from `pendingDRItems`. Since `selectedDR` is derived live (`pendingDRItems.find(item => item.id === selectedDRId) ?? null`), it becomes `null`, and the modal closes — discarding the user's in-progress response selection and notes.

**Evidence:**
- `selectedDR` derivation: `CockpitProvider.tsx` line ~196
- SSE refetch trigger: `CockpitProvider.tsx` line ~77
- Modal renders only when `selectedDR` exists: `Shell.tsx` lines ~520–522

**Recommendation:** Snapshot the DR data into modal-local state on open. The modal should hold its own copy of the DR, not derive it from the live pending list. If the DR disappears from the list mid-edit, the modal can still submit (the backend handles the race via ERR_STALE/404), and the user doesn't lose work.

### G2 — No Pydantic response model on pending list items (High)

The `GET /api/decisions/pending` handler reads raw YAML frontmatter via `meta.get()` and forwards untyped values directly into the response dict. `task_id` could be any YAML-parsed type (string, int, null, list). `created` could be a `datetime.date` object (YAML implicit typing) rather than the expected string. No Pydantic response model validates item shape before serialization.

**Evidence:**
- Raw meta forwarding: `routes/decisions.py` lines ~96–99 (`meta.get("task_id")`, `meta.get("agent", "")`, etc.)
- No `response_model` on the route decorator
- Parse returns raw dict: `decisions.py` `parse_dr()` line ~56

**Recommendation:** Add a Pydantic response model for list items. Coerce `task_id` to `int`, `created` to `str`, and fail explicitly on type mismatch rather than forwarding arbitrary YAML values to the frontend. This catches malformed DR files at the API boundary instead of propagating garbage into the TypeScript layer.

### G3 — SSE event pipeline is structurally pending-only (Structural)

The file watcher, event classifier, and test contracts are hard-wired to `decisions/pending/*.md` only. Adding resolved DR support later requires:
- Extending `_build_watch_filter` to include `decisions/resolved/`
- Extending `_classify_path` to emit events for resolved paths (possibly a new event type)
- Updating test contracts that explicitly reject resolved paths

**Evidence:**
- Watch filter: `events.py` line ~58 — only `decisions/pending`
- Classifier: `events.py` line ~76 — only emits `decisions-changed` for pending
- Test contracts: `test_cockpit_events.py` lines ~1066–1073 — resolved paths explicitly rejected

**Impact:** Not a V1 blocker — V1 is pending-only. But this is the real extensibility constraint for the resolved-DR fast-follow, not the TypeScript type name (`PendingDR`). The type rename is cosmetic; the event pipeline change is structural.

## Schema and Validation Reasoning

### Response shape is sufficient for V1

The `GET /api/decisions/pending` response includes `body` (full markdown) and `body_preview` (200-char truncation) alongside all metadata fields. The full-page list view can render previews from `body_preview` and the detail/modal view can render from `body`. No additional fields or endpoints needed.

### Resolve flow validation is adequate

The backend validates: decision ID regex → file existence → pending status → Pydantic request body. Two distinct "already resolved" paths exist:
- **External resolution** (agent CLI): 409 ERR_STALE with message "already resolved"
- **Duplicate cockpit submission** (file already moved to resolved/): 404 "not found"

The frontend correctly treats both as non-retryable (only status >= 500 triggers retry). The error message from the backend is preserved in the notification. This is acceptable for V1.

### Separate count endpoint is unnecessary

The count is derived from `len(items)` on the backend and returned alongside items. With 1–5 DRs, a separate lightweight endpoint adds complexity for no measurable gain. The nav-rail badge reads count from the same `usePendingDRs` hook that powers the list.

### Optimistic updates are unnecessary

With 1–5 items and SSE-driven refetch (sub-second latency), waiting for server confirmation is correct. Optimistic removal introduces reconciliation complexity for a list that refreshes almost instantly. The modal closes on API success; the list updates on the next refetch cycle.

### Stale-data risk is low

Dual refresh: SSE events trigger immediate refetch; polling continues at 60s as fallback. If SSE drops, stall detection fires at 15s and retry at 30s. Worst-case staleness during SSE outage: ~60s (one poll interval). Acceptable for a list of 1–5 operational DRs.

## Key Trade-offs

| Decision | Trade-off | Recommendation |
|----------|-----------|----------------|
| Modal snapshot vs. live derivation | Snapshot adds local state but prevents data loss | Snapshot — the alternative is user-hostile |
| Pydantic response model vs. raw dict | Model adds a class but catches type drift at the boundary | Model — schema is the contract |
| Frontend schema validation | Runtime checks add code but catch backend drift | Defer to V2 — Pydantic model on backend is the higher-leverage fix |
| Polling asymmetry (decisions always poll, tasks pause on SSE) | Belt-and-suspenders vs. consistency | Accept for V1 — negligible load with 1–5 items |

## Warnings

1. **Do not add resolved DRs by extending `GET /api/decisions/pending`.** The endpoint name, response shape, hook name, and SSE pipeline all assume pending-only. The fast-follow should use a separate endpoint (`GET /api/decisions/resolved` or `GET /api/decisions?status=resolved`).
2. **`body_preview` truncation is not word-boundary aware.** The backend slices at 200 chars, potentially mid-word. Cosmetic issue — not a blocker, but worth a note for polish.
3. **`created` is date-only (`YYYY-MM-DD`), not datetime.** Age display granularity is limited to "today = 0–23h ago depending on timezone." The `formatAge()` function handles this gracefully (guards against NaN, floors to 1m minimum), but sub-day precision is lost.

## Confidence

**0.82** — High confidence on G1 (modal state loss) and G2 (missing response model) as genuine pre-ship gaps. G3 (event pipeline) is structural analysis for the fast-follow, not a V1 blocker. Remaining uncertainty: whether the modal snapshot approach introduces its own edge cases (e.g., stale DR body displayed after external edit-without-resolve).
