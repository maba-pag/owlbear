/**
 * Workflow behavior tests1375: P1-12 Implement Cockpit frontend error-contract adoption
 *
 * KanbanBoard.tsx gaps — handleDrop and handleTransitionClick both hardcode
 * status-only error strings without reading the response body:
 *   - handleDrop:           setMoveError(`Move failed: ${res.status}`)
 *   - handleTransitionClick: setMoveError(`Move failed: ${res.status}`)
 *
 * After #1375, both handlers adopt getResponseErrorMessage() so the body
 * message/detail field appears in the move-error element.
 *
 * All tests FAIL until #1375 replaces the status-only fallback strings with
 * getResponseErrorMessage() calls.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'
import { useBoard } from '../hooks/useBoard'

// ─── Module mocks (hoisted) ────────────────────────────────────────────────────

// ArchivalModal is not under test here — stub it to avoid PDS mount side-effects
// when the context menu is never opened for archived transitions.
vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(() => null),
  ARCHIVAL_REASONS: ['completed', 'dropped', 'wontfix', 'deprecated', 'duplicate'],
}))

// EventSourceProvider mock — required for AC7 tests that render via useBoard().
// The existing renderBoard() tests pass props directly and never call useSSEEvent,
// so this mock has no effect on them.
vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ mtime: null, status: 'connecting' })),
}))

// ─── PDS jsdom polyfill ────────────────────────────────────────────────────────

let _attachInternalsDescriptor: PropertyDescriptor | undefined

beforeEach(() => {
  _attachInternalsDescriptor = Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    'attachInternals',
  )
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

afterEach(() => {
  if (_attachInternalsDescriptor !== undefined) {
    Object.defineProperty(HTMLElement.prototype, 'attachInternals', _attachInternalsDescriptor)
  } else {
    delete (HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals']
  }
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

// ─── Fixtures ──────────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [{ name: 'backlog' }, { name: 'todo' }, { name: 'in-progress' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['in-progress'],
    'in-progress': ['todo'],
  } as Record<string, string[]>,
}

const TASK_BACKLOG = {
  id: 1,
  title: 'Alpha Task',
  status: 'backlog',
  priority: 'needed',
  updated: '2026-05-01T10:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASK_TODO = {
  id: 2,
  title: 'Beta Task',
  status: 'todo',
  priority: 'needed',
  updated: '2026-05-01T11:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeJsonFetch(status: number, body: unknown) {
  return vi.fn(() =>
    Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    } as Response),
  )
}

function renderBoard() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard
          board={BOARD}
          tasks={[TASK_BACKLOG, TASK_TODO]}
          loading={false}
          error={null}
          refetchTasks={vi.fn()}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── AC1/AC2/AC3: handleDrop body extraction ──────────────────────────────────
//
// CURRENT: handleDrop sets `Move failed: ${res.status}` — no body parsing.
// EXPECTED: getResponseErrorMessage() is called; move-error includes body text.

describe('TestFromAC_KanbanBoardDragDropErrorBodyParsing', () => {
  // FAILS: move-error text is "Move failed: 500" — body message field never read.
  // After fix, text contains "move failed: quota exceeded" from response body.
  it('handleDrop non-ok {code,message}: move-error contains response body message field', async () => {
    const errorBody = { code: 'QUOTA_ERROR', message: 'move failed: quota exceeded' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const { container } = renderBoard()

    const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
    fireEvent.dragStart(card)

    const todoCol = container.querySelector('[data-column="todo"]')!
    fireEvent.drop(todoCol)

    await waitFor(
      () => {
        const err = container.querySelector('[data-testid="move-error"]')
        expect(err).not.toBeNull()
        expect(err!.textContent).toContain('move failed: quota exceeded')
      },
      { timeout: 1000 },
    )
  })

  // FAILS: same root cause — status-only error discards {detail} body shape.
  // After fix, text contains "task lock expired during move" from response body.
  it('handleDrop non-ok {detail}: move-error contains response body detail field', async () => {
    const errorBody = { detail: 'task lock expired during move' }
    vi.stubGlobal('fetch', makeJsonFetch(422, errorBody))

    const { container } = renderBoard()

    const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
    fireEvent.dragStart(card)

    const todoCol = container.querySelector('[data-column="todo"]')!
    fireEvent.drop(todoCol)

    await waitFor(
      () => {
        const err = container.querySelector('[data-testid="move-error"]')
        expect(err).not.toBeNull()
        expect(err!.textContent).toContain('task lock expired during move')
      },
      { timeout: 1000 },
    )
  })

  // FAILS: move-error text IS the status-only string "Move failed: 500".
  // not.toBe fails because current text exactly equals the status-only fallback.
  // After fix, text includes the body message appended to (or replacing) the fallback.
  it('handleDrop non-ok: move-error text is not the bare status-only fallback string', async () => {
    const errorBody = { code: 'ENGINE_LOCK', message: 'engine lock held by builder' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const { container } = renderBoard()

    const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
    fireEvent.dragStart(card)

    const todoCol = container.querySelector('[data-column="todo"]')!
    fireEvent.drop(todoCol)

    await waitFor(
      () => {
        const err = container.querySelector('[data-testid="move-error"]')
        expect(err).not.toBeNull()
        // FAILS: current text is exactly "Move failed: 500"
        expect(err!.textContent).not.toBe('Move failed: 500')
      },
      { timeout: 1000 },
    )
  })
})

// ─── AC1/AC2/AC3: handleTransitionClick body extraction ──────────────────────
//
// CURRENT: handleTransitionClick sets `Move failed: ${res.status}` — no body parsing.
// EXPECTED: getResponseErrorMessage() is called; move-error includes body text.

describe('TestFromAC_KanbanBoardContextMenuErrorBodyParsing', () => {
  // FAILS: move-error text is "Move failed: 500" — body message never read.
  // After fix, text contains "transition blocked: reviewer lock active" from body.
  it('handleTransitionClick non-ok {code,message}: move-error contains response body message field', async () => {
    const errorBody = { code: 'LOCK_ERROR', message: 'transition blocked: reviewer lock active' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const { container } = renderBoard()

    // Open context menu on the todo task (has in-progress transition)
    const card = container.querySelector('[data-testid="task-card"][data-id="2"]')!
    fireEvent.contextMenu(card)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
    })

    // Click the in-progress transition item
    const transItem = container.querySelector(
      '[data-testid="transition-item"][data-status="in-progress"]',
    )!
    fireEvent.click(transItem)

    await waitFor(
      () => {
        const err = container.querySelector('[data-testid="move-error"]')
        expect(err).not.toBeNull()
        expect(err!.textContent).toContain('transition blocked: reviewer lock active')
      },
      { timeout: 1000 },
    )
  })

  // FAILS: status-only error discards {detail} body shape.
  // After fix, text contains "concurrent modification: task updated elsewhere" from body.
  it('handleTransitionClick non-ok {detail}: move-error contains response body detail field', async () => {
    const errorBody = { detail: 'concurrent modification: task updated elsewhere' }
    vi.stubGlobal('fetch', makeJsonFetch(422, errorBody))

    const { container } = renderBoard()

    const card = container.querySelector('[data-testid="task-card"][data-id="2"]')!
    fireEvent.contextMenu(card)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
    })

    const transItem = container.querySelector(
      '[data-testid="transition-item"][data-status="in-progress"]',
    )!
    fireEvent.click(transItem)

    await waitFor(
      () => {
        const err = container.querySelector('[data-testid="move-error"]')
        expect(err).not.toBeNull()
        expect(err!.textContent).toContain('concurrent modification: task updated elsewhere')
      },
      { timeout: 1000 },
    )
  })

  // FAILS: move-error text IS "Move failed: 500" — not.toBe fails because
  // current text exactly equals the status-only fallback.
  // After fix, text includes the body message from getResponseErrorMessage().
  it('handleTransitionClick non-ok: move-error text is not the bare status-only fallback string', async () => {
    const errorBody = { code: 'INTERNAL', message: 'engine timeout on move' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const { container } = renderBoard()

    const card = container.querySelector('[data-testid="task-card"][data-id="2"]')!
    fireEvent.contextMenu(card)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
    })

    const transItem = container.querySelector(
      '[data-testid="transition-item"][data-status="in-progress"]',
    )!
    fireEvent.click(transItem)

    await waitFor(
      () => {
        const err = container.querySelector('[data-testid="move-error"]')
        expect(err).not.toBeNull()
        // FAILS: current text is exactly "Move failed: 500"
        expect(err!.textContent).not.toBe('Move failed: 500')
      },
      { timeout: 1000 },
    )
  })
})

// ─── AC5: Health behavior from #1373 preserved (td:1 smoke test) ──────────────
//
// The health scan false-OK guard lives in Shell/useScanPolling — KanbanBoard has
// no health state. This smoke test confirms that KanbanBoard move error handling
// is independent of health state: the board renders correctly AND move-error
// body parsing works (the body-parsing assertion is what makes this FAIL now).

describe('TestFromAC_HealthPreservation', () => {
  // FAILS: move-error text does not include body message (status-only fallback).
  // The health-independence claim holds structurally; the body-parsing half fails.
  it('KanbanBoard move error is independent of health scan; move-error contains body text', async () => {
    const errorBody = { code: 'MOVE_FAIL', message: 'board move rejected: index locked' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const { container } = renderBoard()

    // Board renders without a health indicator (health is Shell-level, not KanbanBoard-level)
    expect(container.querySelector('[data-health]')).toBeNull()

    // Trigger a drag-drop move that fails
    const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
    fireEvent.dragStart(card)

    const todoCol = container.querySelector('[data-column="todo"]')!
    fireEvent.drop(todoCol)

    await waitFor(
      () => {
        const err = container.querySelector('[data-testid="move-error"]')
        expect(err).not.toBeNull()
        // FAILS: current text is "Move failed: 500" — body field not parsed
        expect(err!.textContent).toContain('board move rejected: index locked')
      },
      { timeout: 1000 },
    )
  })
})

// ─── AC7: Board-load error body discrimination (td:2) ─────────────────────────
//
// PROOF GAP identified by reviewer (2nd pass): no executed test asserts that the
// body message text from a non-ok /api/board response reaches the rendered
// error-message element. Existing renderBoard() tests pass error={null} and
// bypass the board-load path entirely.
//
// These tests render via the real useBoard() hook so the full path is exercised:
//   fetch /api/board → useBoard.getResponseErrorMessage() → error state →
//   KanbanBoard error prop → <div data-testid="error-message">{error}</div>
//
// Expected: PASS against current code (implementation confirmed correct by two
// reviewer code-path inspections — see ## Review Evidence in task body).

function BoardViaHook() {
  const { board, tasks, loading, error, refetchTasks } = useBoard()
  return (
    <KanbanBoard
      board={board}
      tasks={tasks}
      loading={loading}
      error={error}
      refetchTasks={refetchTasks}
    />
  )
}

describe('TestFromAC_BoardLoadErrorBodyDiscrimination', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // EXPECTED TO PASS: useBoard parses {code,message} body via getResponseErrorMessage(),
  // sets error state, and KanbanBoard renders it in the error-message element.
  // If this fails, the board-load path does NOT discriminate body text from generic fallbacks.
  it('board-load non-ok {code,message}: error-message contains response body message field', async () => {
    const errorBody = { code: 'BOARD_ERR', message: 'board scan failed: index corrupted' }
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/api/board')) {
          return Promise.resolve({
            ok: false,
            status: 500,
            json: () => Promise.resolve(errorBody),
          } as Response)
        }
        // /api/tasks — return ok with empty tasks to prevent task-error interference
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ tasks: [], mtime: 1 }),
        } as Response)
      }),
    )

    const { container } = render(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <BoardViaHook />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    await waitFor(
      () => {
        const err = container.querySelector('[data-testid="error-message"]')
        expect(err).not.toBeNull()
        expect(err!.textContent).toContain('board scan failed: index corrupted')
      },
      { timeout: 2000 },
    )
  })

  // EXPECTED TO PASS: same path but {detail} body shape — proves both envelope
  // shapes are handled by getResponseErrorMessage() and reach the rendered element.
  it('board-load non-ok {detail}: error-message contains response body detail field', async () => {
    const errorBody = { detail: 'board scan failed: detail shape' }
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/api/board')) {
          return Promise.resolve({
            ok: false,
            status: 503,
            json: () => Promise.resolve(errorBody),
          } as Response)
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ tasks: [], mtime: 1 }),
        } as Response)
      }),
    )

    const { container } = render(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <BoardViaHook />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    await waitFor(
      () => {
        const err = container.querySelector('[data-testid="error-message"]')
        expect(err).not.toBeNull()
        expect(err!.textContent).toContain('board scan failed: detail shape')
      },
      { timeout: 2000 },
    )
  })
})
