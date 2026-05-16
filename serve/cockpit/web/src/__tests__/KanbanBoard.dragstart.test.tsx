/**
 * Frontend — complete drag-and-drop (call move API on drop).
 *
 * Covers:
 *   AC1 (td:1) — Dragging a card propagates its taskId + updated token into
 *                KanbanBoard drag state (Card.onDragStart interface change)
 *   AC2 (td:2) — Dropping on a valid column fires POST /api/tasks/{id}/move
 *                with {status: targetStatus, updated: storedToken} body
 *   AC3 (td:1) — On 2xx: refetchTasks() called (drag state clearing is unconditional
 *                and unobservable — covered by AC7 td:0)
 *   AC4 (td:2) — On 409: stale-snapshot error displayed via moveError state,
 *                refetchTasks() called to sync fresh updated tokens
 *   AC5 (td:2) — On other error (4xx/5xx/network): error displayed via moveError,
 *                refetchTasks() NOT called (polling handles eventual consistency)
 *   AC6 (td:0) — Invalid drop target does nothing (skipped — td:0)
 *   AC7 (td:0) — Drag state cleared before async move request; browser dragEnd
 *                provides redundant cleanup (skipped — unconditional, unobservable)
 *
 * Harness note: KanbanBoard is prop-driven (task #1227 removed the legacy
 * LegacyKanbanBoard/useBoard fallback). Board and tasks are passed directly as props;
 * refetchTasks is a vi.fn() spy so AC3/AC4/AC5 refetch assertions are direct
 * (no fetch-call counting required).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'

// --- Mock ArchivalModal ------------------------------------------------------
// KanbanBoard imports ArchivalModal; stub it to avoid rendering real component.
vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(() => null),
}))

// --- Fixtures -----------------------------------------------------------------

// Two-column board: backlog -> todo transition exists.
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

const TASKS = [TASK_ONE]

// --- Fetch stub ---------------------------------------------------------------
// Only stubs the /move endpoint — board and tasks come in as props.

type MoveFetchOptions = {
  moveStatus?: number
  moveNetwork?: boolean
}

function stubMoveFetch(opts: MoveFetchOptions = {}) {
  const { moveStatus = 200, moveNetwork = false } = opts
  const mockFetch = vi.fn((url: string) => {
    if (/\/api\/tasks\/\d+\/move/.test(url)) {
      if (moveNetwork) return Promise.reject(new Error('Network failure'))
      return Promise.resolve({
        ok: moveStatus >= 200 && moveStatus < 300,
        status: moveStatus,
        json: () => Promise.resolve({}),
      })
    }
    return Promise.reject(new Error(`Unexpected fetch URL in 1229 suite: ${url}`))
  })
  vi.stubGlobal('fetch', mockFetch)
  return mockFetch
}

// --- Render helper ------------------------------------------------------------
// Passes board + tasks as props; refetchSpy is tracked directly for AC3/AC4/AC5.

function renderBoard(refetchSpy = vi.fn(), onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void) {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard
          board={BOARD}
          tasks={TASKS}
          loading={false}
          error={null}
          refetchTasks={refetchSpy}
          onMutationError={onMutationError}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// --- Drag helpers -------------------------------------------------------------

/** Find card with data-id="7" (board is synchronous -- waitFor resolves in one tick). */
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

// --- Tests -------------------------------------------------------------------

// -- AC1 (td:1): Drag propagates task identity into board state ----------------

describe('TestFromAC_DragStart', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Smoke test: drop on todo sends POST to /api/tasks/7/move, proving that the
  // dragged card's taskId (7) was propagated through Column into KanbanBoard state.
  it('dragging card 7 then dropping on todo column sends POST to /api/tasks/7/move', async () => {
    const mockFetch = stubMoveFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string][]).filter(([url]) =>
        /\/api\/tasks\/7\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
    })
  })
})

// -- AC2 (td:2): Drop calls POST /api/tasks/{id}/move with correct body --------

describe('TestFromAC_DropCallsMoveAPI', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Happy: drop fires POST at all.
  it('dropping on a valid column fires POST /api/tasks/{id}/move', async () => {
    const mockFetch = stubMoveFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string][]).filter(([url]) =>
        /\/api\/tasks\/\d+\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
    })
  })

  // Boundary: POST targets the correct task id in the URL path.
  it('POST URL contains the dragged card task id', async () => {
    const mockFetch = stubMoveFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string][]).filter(([url]) =>
        /\/api\/tasks\/7\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
    })
  })

  // Boundary: POST uses POST method and body contains the target column status.
  it('POST body contains status equal to the drop target column status', async () => {
    const mockFetch = stubMoveFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string, RequestInit][]).filter(([url]) =>
        /\/api\/tasks\/\d+\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
      const [, init] = moveCalls[0]
      expect(init.method).toBe('POST')
      const body = JSON.parse(init.body as string) as Record<string, unknown>
      expect(body.status).toBe('todo')
    })
  })

  // Boundary: POST body contains the exact updated token from the dragged card.
  it('POST body contains the dragged card updated token', async () => {
    const mockFetch = stubMoveFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string, RequestInit][]).filter(([url]) =>
        /\/api\/tasks\/\d+\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
      const [, init] = moveCalls[0]
      const body = JSON.parse(init.body as string) as Record<string, unknown>
      expect(body.updated).toBe(TASK_ONE.updated)
    })
  })

  // Edge: POST body has exactly the two required fields (status, updated) -- no extras.
  it('POST body contains exactly the status and updated fields', async () => {
    const mockFetch = stubMoveFetch()
    const { container } = renderBoard()
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      const moveCalls = (mockFetch.mock.calls as [string, RequestInit][]).filter(([url]) =>
        /\/api\/tasks\/\d+\/move/.test(url),
      )
      expect(moveCalls.length).toBeGreaterThan(0)
      const [, init] = moveCalls[0]
      const body = JSON.parse(init.body as string) as Record<string, unknown>
      expect(Object.keys(body).sort()).toEqual(['status', 'updated'])
    })
  })
})

// -- AC3 (td:1): On 2xx -- refetchTasks() called ------------------------------

describe('TestFromAC_DropSuccess', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Smoke: 2xx -> refetchTasks() spy is called.
  it('on 2xx response, refetchTasks() is called', async () => {
    stubMoveFetch({ moveStatus: 200 })
    const refetchSpy = vi.fn()
    const { container } = renderBoard(refetchSpy)
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(refetchSpy).toHaveBeenCalled()
    })
  })
})

// -- AC4 (td:2): On 409 -- stale-snapshot error displayed, refetchTasks called -

describe('TestFromAC_Drop409', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Happy (error condition): 409 -> onMutationError called.
  it('on 409 response, calls onMutationError with error state', async () => {
    stubMoveFetch({ moveStatus: 409 })
    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(vi.fn(), mutationErrorSpy)
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(mutationErrorSpy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
    })
  })

  // Edge: 409 triggers onMutationError (conflict is shown via PBanner callback contract).
  it('on 409 response, onMutationError is called (conflict shown via Shell PBanner)', async () => {
    stubMoveFetch({ moveStatus: 409 })
    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(vi.fn(), mutationErrorSpy)
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(mutationErrorSpy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
    })
  })

  // Boundary: 409 triggers refetchTasks() to sync fresh updated tokens.
  // This is the 409-specific behaviour -- other errors (AC5) do NOT refetch.
  it('on 409 response, refetchTasks() is called to sync fresh tokens', async () => {
    stubMoveFetch({ moveStatus: 409 })
    const refetchSpy = vi.fn()
    const { container } = renderBoard(refetchSpy)
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(refetchSpy).toHaveBeenCalled()
    })
  })

  // Boundary: 422 (non-409 non-ok) must NOT trigger refetchTasks() -- the 409
  // branch is intentionally distinct from generic error handling (AC5 contract).
  // Direct spy assertion: stronger than a timing-window fetch-count check and
  // catches early (pre-error-render) refetch calls that a baseline approach would miss.
  it('on 422 response, calls onMutationError but does NOT call refetchTasks() (unlike 409)', async () => {
    stubMoveFetch({ moveStatus: 422 })
    const refetchSpy = vi.fn()
    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(refetchSpy, mutationErrorSpy)
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(mutationErrorSpy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
    })

    // Allow extra ticks; refetchTasks() must never be called for a 422.
    await new Promise<void>((resolve) => setTimeout(resolve, 80))
    expect(refetchSpy).not.toHaveBeenCalled()
  })
})

// -- AC5 (td:2): On other error -- moveError shown, refetchTasks() NOT called --

describe('TestFromAC_DropOtherError', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Smoke: 500 -> onMutationError called.
  it('on 500 response, calls onMutationError with error state', async () => {
    stubMoveFetch({ moveStatus: 500 })
    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(vi.fn(), mutationErrorSpy)
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(mutationErrorSpy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
    })
  })

  // Error: network failure -> onMutationError called; refetchTasks() NOT called.
  it('on network failure, calls onMutationError and does NOT call refetchTasks()', async () => {
    stubMoveFetch({ moveNetwork: true })
    const refetchSpy = vi.fn()
    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(refetchSpy, mutationErrorSpy)
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(mutationErrorSpy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
    })

    // Allow extra ticks; refetchTasks() must never be called for a network error.
    await new Promise<void>((resolve) => setTimeout(resolve, 80))
    expect(refetchSpy).not.toHaveBeenCalled()
  })

  // Boundary: 500 must NOT trigger refetchTasks() -- polling handles eventual
  // consistency. Direct spy assertion catches early refetch calls that a
  // timing-window fetch-count baseline approach would miss.
  it('on 500 response, calls onMutationError and does NOT call refetchTasks()', async () => {
    stubMoveFetch({ moveStatus: 500 })
    const refetchSpy = vi.fn()
    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(refetchSpy, mutationErrorSpy)
    await waitAndDragCard(container)
    dropOnTodo(container)

    await waitFor(() => {
      expect(mutationErrorSpy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
    })

    // Allow extra ticks; refetchTasks() must never be called for a 500.
    await new Promise<void>((resolve) => setTimeout(resolve, 80))
    expect(refetchSpy).not.toHaveBeenCalled()
  })
})
