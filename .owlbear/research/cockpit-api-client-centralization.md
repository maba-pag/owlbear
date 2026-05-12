# Cockpit: Centralize API Client (Tasks + Decisions)

> **Owning task:** #1493 — Cockpit: Centralize API client (tasks + decisions)
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

The cockpit frontend has 8+ raw `fetch()` calls spread across 5 components/hooks targeting `/api/tasks/*` and `/api/decisions/*` endpoints. Each duplicates error envelope parsing, Content-Type headers, and response type assertions. The question: what's the right centralization pattern?

**Current state:** `api/` directory already has `errorMessage.ts` (shared utility), `repair.ts`, and `cleanup.ts` — both use plain async functions wrapping fetch + `getResponseErrorMessage`. This is the established in-repo pattern.

**Raw fetch sites to extract:**

| Component | Endpoint | Method |
|-----------|----------|--------|
| Shell.tsx | `/api/tasks/{id}` | GET |
| KanbanBoard.tsx (×2) | `/api/tasks/{id}/move` | POST |
| DetailTab.tsx (runMutation) | arbitrary URL passed in | POST |
| DetailTab.tsx (409 handler) | `/api/tasks/{id}` | GET |
| ArchivalModal.tsx | `/api/tasks/{id}/move` | POST |
| ResolveModal.tsx | `/api/decisions/{id}/resolve` | POST |
| useBoard.ts | `/api/board` | GET (via usePollingFetch) |

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | Existing `api/repair.ts` and `api/cleanup.ts` in-repo | 1.0 — proven pattern in this codebase |
| 2 | Kent C. Dodds "Replace axios with a simple custom fetch wrapper" | 0.8 — validates plain function approach for same-origin SPAs |
| 3 | dev.to "Building a Type-Safe API Client in TypeScript" (2025) | 0.7 — shows typed wrapper functions eliminate duplication |
| 4 | TanStack Query docs | 0.5 — evaluated as alternative, rejected for KISS/YAGNI |

## 3. Analysis

### Option Comparison

| Criterion | A: Plain async functions | B: TanStack Query | C: Class-based client |
|-----------|--------------------------|-------------------|-----------------------|
| KISS alignment | ✅ Minimal | ❌ 42KB dep, paradigm shift | ⚠️ Unnecessary abstraction |
| Consistency with existing code | ✅ Same pattern as repair.ts | ❌ Replaces usePollingFetch/SSE | ⚠️ Different paradigm |
| Tree-shakeable | ✅ Yes | ✅ Yes | ❌ Monolithic |
| Test isolation | ✅ Mock fetch per-function | ⚠️ Need query provider | ✅ Mock class |
| New dependencies | 0 | 1 major (+ devtools) | 0 |
| Lines of code (estimated) | ~80 LOC (tasks) + ~25 LOC (decisions) | ~200 LOC (hooks + config) | ~120 LOC |
| Handles conflict/state | ❌ Components keep UI state | ✅ Built-in | ❌ Same as A |
| Risk | Low | High (architectural) | Medium |

### Key Design Insight

`DetailTab.tsx`'s `runMutation()` has **UI-coupled conflict resolution** (409 → refetch → show conflict modal, 404 → clear task, 422 → show validation). This state management stays in the component. The API layer handles only: construct request → parse response → return typed data or throw.

**Error contract:** Functions throw on non-OK responses. Return typed data on success. Components decide how to render errors. This matches `repair.ts` exactly.

### Proposed API Surface

```typescript
// api/tasks.ts
export async function getTask(id: number, signal?: AbortSignal): Promise<TaskDetail>
export async function moveTask(id: number, payload: MoveTaskPayload): Promise<TaskDetail>
export async function editTask(id: number, payload: EditTaskPayload): Promise<TaskDetail>
export async function releaseTask(id: number, payload: ReleaseTaskPayload): Promise<TaskDetail>

// api/decisions.ts
export async function resolveDR(id: string, payload: ResolveDRPayload): Promise<void>
```

Each function: constructs fetch, checks `response.ok`, parses body, returns or throws with `getResponseErrorMessage`. Components handle status-specific branching (409, 404, 422) via caught error properties or raw response access.

**Refinement for DetailTab:** The `runMutation` pattern needs response access (status codes). Two options:
- (a) Return `{ data, response }` tuple — caller checks status
- (b) Throw a typed `ApiError` with `.status` property — caller catches and branches

Option (b) is cleaner: `catch (e) { if (e instanceof ApiError && e.status === 409) ... }`.

## 4. Recommendation

**Option A: Plain async functions** with a thin `ApiError` class for status-aware error handling.

Confidence: **0.90**

Rationale: Zero new deps, follows the pattern already established in `repair.ts`/`cleanup.ts`, KISS-aligned, easy to test. The only addition beyond the existing pattern is an `ApiError` class to carry HTTP status for conflict/validation branching.

Challenge: Skipped — trivial T1 refactoring, no architectural decision, follows existing in-repo precedent.

## 5. Follow-up Tasks

1. **Implement `api/tasks.ts`** — `getTask`, `moveTask`, `editTask`, `releaseTask` + `ApiError` class + types
2. **Implement `api/decisions.ts`** — `resolveDR` + types
3. **Migrate consumers** — KanbanBoard, DetailTab, ArchivalModal, ResolveModal, Shell to use new functions
