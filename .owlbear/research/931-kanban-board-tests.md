# Kanban Board RED Tests — Research

> **Owning task:** #931 — P2-04: RED — Kanban board surface tests
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Write failing Vitest + RTL tests for the kanban board surface: status columns, task cards, drag-to-move, context menu, and visual indicators. The board component doesn't exist yet — only a `<div>kanban</div>` placeholder in Shell.tsx at route `/`.

**Key questions:** (a) How to test DnD in jsdom? (b) What mocking strategy for API data? (c) Which AC items are testable in jsdom vs requiring E2E? (d) What data gaps exist between the API and AC requirements?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/cockpit/src/owlbear_cockpit/models.py` — API response schemas | 0.95 |
| S2 | `serve/kanban/src/owlbear_kanban/models.py` — engine Task/TaskSummary | 0.95 |
| S3 | `serve/cockpit/web/src/__tests__/Shell.test.tsx` — established test patterns | 0.90 |
| S4 | `.owlbear/research/927-app-shell-tests.md` — prior RED test strategy | 0.85 |
| S5 | `serve/cockpit/web/package.json` — current deps (no DnD lib, no MSW) | 0.90 |
| S6 | RTL docs: MSW recommended for API mocking | 0.80 |
| S7 | `.owlbear/kanban/config.yml` — board config structure | 0.85 |
| S8 | `serve/cockpit/src/owlbear_cockpit/routes/read.py` — endpoint impl | 0.90 |

## 3. Analysis

### 3.1 API Data Gaps

`TaskSummaryOut` (cockpit API) is missing four fields present on the engine's `TaskSummary`:

| Field | Engine `TaskSummary` | Cockpit `TaskSummaryOut` | Needed for AC |
|-------|---------------------|-------------------------|---------------|
| `block_reason` | `str \| None` | **missing** | Block badge tooltip |
| `claimed` | `bool` | **missing** | Running indicator |
| `parent` | `int \| None` | **missing** | Not in board AC |
| `depends_on` | `list[int]` | **missing** | Not in board AC |

RED tests mock the response shape, so missing API fields don't block test authoring. Follow-up task needed to extend `TaskSummaryOut` with `block_reason` and `claimed` before GREEN phase.

### 3.2 jsdom Feasibility Matrix

| AC Item | jsdom? | Strategy |
|---------|--------|----------|
| Columns in board-config order | **Yes** | Query `[data-column]` elements, check DOM order |
| Cards in correct columns, sorted | **Yes** | Check card elements within column containers |
| Card: title, priority border, block badge | **Yes** | Query text, data attributes, aria labels |
| Card: running indicator (claimed) | **Yes** | Data attribute `[data-claimed]` or aria |
| Card density 48-56px | **No** | Defer to E2E — jsdom has no layout engine |
| Drag-to-move highlights | **No** | Defer to E2E — jsdom DnD API is non-functional |
| Context menu with valid transitions | **Yes** | `fireEvent.contextMenu` + menu item queries |
| Column task counts | **Yes** | Text content in column headers |
| Empty column state | **Yes** | Render with no tasks for a status |
| Loading state | **Yes** | Standard async: check skeleton/spinner presence |
| Error state | **Yes** | Mock fetch rejection, check error message |
| Horizontal/vertical scroll | **No** | Defer to E2E — jsdom doesn't compute overflow |

**9 of 12 AC items** testable in jsdom. 3 items (card density, DnD highlights, scroll) require E2E.

### 3.3 Mocking Strategy

| Option | Pros | Cons |
|--------|------|------|
| A. Mock `globalThis.fetch` | Contract tied to backend schema; zero deps | Verbose setup |
| B. Mock future hook (`useBoardData`) | Simple mock signature | Shadow contract; diverges silently |
| C. Install MSW | Most realistic; network-level | New dep; overkill for RED |

**Recommendation: Option A** (confidence .85). Mock `fetch` against `BoardOut` and `TaskListOut` schemas from the backend. The response shapes are already defined — tests validate the data→DOM contract at a real boundary.

### 3.4 Test File Structure

Import `KanbanBoard` standalone (not through Shell). Follows component isolation pattern. The Shell integration (route `/` renders the board) is a separate concern tested in Shell.test.tsx.

```
serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx
  ├─ describe('columns')        — order, counts, empty state
  ├─ describe('cards')          — placement, title, priority, blocked, claimed
  ├─ describe('context menu')   — right-click shows valid transitions
  ├─ describe('loading state')  — skeleton/spinner during fetch
  └─ describe('error state')    — API failure recovery message
```

DnD highlight tests and scroll/density tests belong in a future E2E test file.

### 3.5 AC Item: `claim_status`

No `claim_status` field exists anywhere. The closest is `claimed: bool` on the engine's `TaskSummary`. Tests should use `claimed` as the data source for the "running indicator." Follow-up API task covers exposing this field.

## 4. Recommendation

**Approach:** Write RED tests for 9 jsdom-feasible AC items. Create a separate follow-up task for 3 E2E-only AC items (DnD highlights, card density, scroll behavior). Mock `fetch` against backend contract shapes.

**Confidence:** 0.82

Challenge: `reconsider` — original confidence 0.45. Revised: dropped DnD event testing in jsdom (challenger correctly identified jsdom DnD as non-functional), dropped CSS class density testing (premature specification), switched from hook mocking to fetch-level mocking (real contract boundary), completed field gap enumeration (4 fields, not 2).

## 5. Follow-up Tasks

1. **Extend `TaskSummaryOut`** — add `block_reason` and `claimed` fields to cockpit API model + adapter + tests (GREEN-phase prerequisite)
2. **E2E kanban board tests** — DnD highlights, card density, scroll behavior (requires Playwright or similar)
