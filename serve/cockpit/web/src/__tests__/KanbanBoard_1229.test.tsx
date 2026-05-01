/**
 * RED phase tests for #1229: Frontend — complete drag-and-drop (call move API on drop).
 *
 * Covers:
 *   AC1 (td:1) — Dragging a card propagates its taskId + updated token into
 *                KanbanBoard drag state (Card.onDragStart interface change)
 *   AC2 (td:2) — Dropping on a valid column fires POST /api/tasks/{id}/move
 *                with {status: targetStatus, updated: storedToken} body
 *   AC3 (td:1) — On 2xx: refetchTasks() called and drag state cleared
 *   AC4 (td:2) — On 409: stale-snapshot error displayed via moveError state,
 *                refetchTasks() called to sync fresh updated tokens
 *   AC5 (td:1) — On other error (4xx/5xx/network): error displayed via moveError,
 *                no immediate refetch
 *   AC6 (td:0) — Invalid drop target does nothing (skipped — td:0)
 *
 * All tests are RED until the builder:
 *   - Changes Card.onDragStart to pass (taskId, updated) through Column → Board
 *   - Adds onDrop prop to Column, wired from Board
 *   - Adds drag state {taskId, updated} to KanbanBoard
 *   - Implements drop handler with 409-specific branching (refetch on stale)
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'

// ─── Mock ArchivalModal ───────────────────────────────────────────────────────
// KanbanBoard imports ArchivalModal; stub it to avoid rendering real component.
vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(() => null),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

// Two-column board: backlog → todo transition exists.
const BOARD = {
  statuses: [{ name: 'backlog' }, { name: 'todo' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog'],
  } as Record<string, string[]>,
}

// Single task in backlog with a known identity (id=7, specific updated token).
const TASK_ONE = {
  id: 7,
  title: 'Drag this task',
  status: 'backlog',
  priority: 'needed',
  updated: '2026-04-30T12:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASKS = { tasks: [TASK_ONE], mtime: 1000 }

// ─── Fetch stub ───────────────────────────────────────────────────────────────

type FetchStubOptions = {
  moveStatus?: number
  moveNetwork?: boolean
}

function stubFetch(opts: FetchStubOptions = {}) {
  const { moveStatus = 200, moveNetwork = false } = opts
  const mockFetch = vi.fn((url: string, init?: RequestInit) => {
    if (url.includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    if (/\/api\/tasks\/\d+\/move/.test(url)) {
      if (moveNetwork) return Promise.reject(new Error('Network failure'))
      return Promise.resolve({
        ok: moveStatus >= 200 && moveStatus < 300,
        status: moveStatus,
        json: () => Promise.resolve({}),
      })
    }
    if (url.includes('/api/tasks')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS) })
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`))
  })
  vi.stubGlobal('fetch', mockFetch)
  return mockFetch
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderBoard() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Drag helpers ─────────────────────────────────────────────────────────────

/** Wait for the board to load, then fire dragStart on card with data-id="7". */
async function waitAndDragCard(container: HTMLElement) {
  await waitFor(() => {
    expect(
      container.querySelector('[data-testid="task-card"][data-id="7"]'),
    ).not.toBeNull()
  })
  const card = container.querySelector('[data-testid="task-card"][data-id="7"]')!
  fireEvent.dragStart(card)
  return card
}

/** Fire dragOver then drop on the todo column. */
function dropOnTodo(container: HTMLElement) {
  const col = container.querySelector('[data-column="todo"]')!
  fireEvent.dragOver(col)
  fireEvent.drop(col)
  return col
}

/** Count calls to /api/tasks (excluding /move calls). */
function countTaskFetches(mockFetch: ReturnType<typeof vi.fn>) {
  return (mockFetch.mock.calls as [string, RequestInit?][]).filter(
    ([url]) => url.includes('/api/tasks') && !/\/move/.test(url),
  ).length
}

// ─── Tests ────────────────────────────────────────────────────────────────────

// ── AC1 (td:1): Drag propagates task identity into board state ────────────────

describe('TestFromAC_DragStart', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Smoke test: drop on todo sends POST to /api/tasks/7/move, proving that the
  // dragged card's taskId (7) was propagated through Column into KanbanBoard state.
  // Currently FAILS: Column.onDrop does not call any API callback.
  it('dragging card 7 then dropping on todo column sends POST to /api/tasks/7/move', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string, RequestInit?][]).filter(
        ([url]) => /\/api\/tasks\/7\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
    })
  })
})

// ── AC2 (td:2): Drop calls POST /api/tasks/{id}/move with correct body ─────────

describe('TestFromAC_DropCallsMoveAPI', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Happy: drop fires POST at all.
  // Currently FAILS: Column.onDrop has no API callback.
  it('dropping on a valid column fires POST /api/tasks/{id}/move', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string, RequestInit?][]).filter(
        ([url]) => /\/api\/tasks\/\d+\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
    })
  })

  // Boundary: POST targets the correct task id in the URL path.
  // Currently FAILS: no POST fired at all.
  it('POST URL contains the dragged card task id', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string, RequestInit?][]).filter(
        ([url]) => /\/api\/tasks\/7\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
    })
  })

  // Boundary: POST body contains the target column status.
  // Currently FAILS: no POST fired.
  it('POST body contains status equal to the drop target column status', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string, RequestInit?][]).filter(
        ([url]) => /\/api\/tasks\/\d+\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
      const [, init] = moveCalls[0] as [string, RequestInit]
      const body = JSON.parse(init.body as string) as Record<string, unknown>
      expect(body.status).toBe('todo')
    })
  })

  // Boundary: POST body contains the exact updated token from the dragged card.
  // Currently FAILS: no POST fired.
  it('POST body contains the dragged card updated token', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string, RequestInit?][]).filter(
        ([url]) => /\/api\/tasks\/\d+\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
      const [, init] = moveCalls[0] as [string, RequestInit]
      const body = JSON.parse(init.body as string) as Record<string, unknown>
      expect(body.updated).toBe(TASK_ONE.updated)
    })
  })

  // Edge: POST body has exactly the two required fields (status, updated) — no extras.
  // Currently FAILS: no POST fired.
  it('POST body contains exactly the status and updated fields', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string, RequestInit?][]).filter(
        ([url]) => /\/api\/tasks\/\d+\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
      const [, init] = moveCalls[0] as [string, RequestInit]
      const body = JSON.parse(init.body as string) as Record<string, unknown>
      expect(Object.keys(body).sort()).toEqual(['status', 'updated'])
    })
  })
})

// ── AC3 (td:1): On 2xx — refetchTasks called, drag state cleared ──────────────

describe('TestFromAC_DropSuccess', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Smoke: after 2xx, GET /api/tasks is called again (refetchTasks).
  // Currently FAILS: no drop→API→refetch chain exists.
  it('on 2xx response, GET /api/tasks is called again (refetchTasks)', async () => {
    const mockFetch = stubFetch({ moveStatus: 200 })
    const { container } = renderBoard()
    await waitAndDragCard(container)
    const taskFetchesBefore = countTaskFetches(mockFetch)

    dropOnTodo(container)

    await waitFor(() => {
      expect(countTaskFetches(mockFetch)).toBeGreaterThan(taskFetchesBefore)
    })
  })
})

// ── AC4 (td:2): On 409 — stale-snapshot error displayed, refetchTasks called ──

describe('TestFromAC_Drop409', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Happy (error condition): 409 → moveError element appears.
  // Currently FAILS: no drop handler → no POST → no error state.
  it('on 409 response, displays a move-error message', async () => {
    stubFetch({ moveStatus: 409 })
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const errorEl = container.querySelector('[data-testid="move-error"]')
      expect(errorEl).not.toBeNull()
      expect((errorEl?.textContent ?? '').length).toBeGreaterThan(0)
    })
  })

  // Edge: 409 error message specifically indicates a stale / snapshot / conflict
  // condition — not a generic error. Currently FAILS: no error appears.
  it('on 409 response, error text indicates a stale-snapshot conflict', async () => {
    stubFetch({ moveStatus: 409 })
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const errorEl = container.querySelector('[data-testid="move-error"]')
      expect(errorEl).not.toBeNull()
      const text = (errorEl?.textContent ?? '').toLowerCase()
      expect(
        text.includes('stale') ||
          text.includes('snapshot') ||
          text.includes('outdated') ||
          text.includes('conflict') ||
          text.includes('409'),
      ).toBe(true)
    })
  })

  // Boundary: 409 triggers refetchTasks to sync fresh updated tokens.
  // This is the 409-specific behaviour — other errors (AC5) do NOT refetch.
  // Currently FAILS: no drop handler.
  it('on 409 response, GET /api/tasks is called again to sync fresh tokens', async () => {
    const mockFetch = stubFetch({ moveStatus: 409 })
    const { container } = renderBoard()
    await waitAndDragCard(container)
    const taskFetchesBefore = countTaskFetches(mockFetch)

    dropOnTodo(container)

    await waitFor(() => {
      expect(countTaskFetches(mockFetch)).toBeGreaterThan(taskFetchesBefore)
    })
  })

  // Boundary: 422 (non-409 non-ok) must NOT trigger a refetch — the 409 branch
  // is intentionally distinct from generic error handling (AC5 contract).
  // Currently FAILS: no drop → move-error appears (first assertion fails).
  it('on 422 response, displays error but does NOT trigger a refetch (unlike 409)', async () => {
    const mockFetch = stubFetch({ moveStatus: 422 })
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    // Error must appear (currently no drop handler → this assertion fails RED).
    await waitFor(() => {
      expect(container.querySelector('[data-testid="move-error"]')).not.toBeNull()
    })

    // Refetch must NOT happen for a 422.
    const taskFetchesBefore = countTaskFetches(mockFetch)
    await new Promise<void>((resolve) => setTimeout(resolve, 80))
    expect(countTaskFetches(mockFetch)).toBe(taskFetchesBefore)
  })
})

// ── AC5 (td:1): On other error — moveError shown, no immediate refetch ─────────

describe('TestFromAC_DropOtherError', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Smoke: 500 → moveError element appears.
  // Currently FAILS: no drop handler.
  it('on 500 response, displays a move-error message', async () => {
    stubFetch({ moveStatus: 500 })
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="move-error"]')).not.toBeNull()
    })
  })

  // Error: network failure → moveError element appears.
  // Currently FAILS: no drop handler.
  it('on network failure, displays a move-error message', async () => {
    stubFetch({ moveNetwork: true })
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="move-error"]')).not.toBeNull()
    })
  })

  // Boundary: 500 must NOT trigger an immediate refetch (polling handles eventual
  // consistency). Currently FAILS: no drop → move-error (first waitFor fails).
  it('on 500 response, displays error and does NOT trigger an additional refetch', async () => {
    const mockFetch = stubFetch({ moveStatus: 500 })
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    // Error must appear (fails RED — no drop handling).
    await waitFor(() => {
      expect(container.querySelector('[data-testid="move-error"]')).not.toBeNull()
    })

    // No extra refetch after the error.
    const taskFetchesBefore = countTaskFetches(mockFetch)
    await new Promise<void>((resolve) => setTimeout(resolve, 80))
    expect(countTaskFetches(mockFetch)).toBe(taskFetchesBefore)
  })
})
