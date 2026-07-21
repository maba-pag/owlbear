/**
 * Implement Cockpit frontend error-contract adoption
 *
 * KanbanBoard.tsx gaps — handleTransitionClick hardcoded status-only error
 * strings without reading the response body:
 *   - handleTransitionClick: setMoveError(`Move failed: ${res.status}`)
 *
 * After #1375, the move handler adopts getResponseErrorMessage() so the body
 * message/detail field appears in the move-error element.
 *
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

function renderBoard(onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void) {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard
          board={BOARD}
          tasks={[TASK_BACKLOG, TASK_TODO]}
          loading={false}
          error={null}
          refetchTasks={vi.fn()}
          onMutationError={onMutationError}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── AC1/AC2/AC3: handleTransitionClick body extraction ──────────────────────
//
// CURRENT: handleTransitionClick sets `Move failed: ${res.status}` — no body parsing.
// EXPECTED: getResponseErrorMessage() is called; move-error includes body text.

describe('TestFromAC_KanbanBoardContextMenuErrorBodyParsing', () => {
  // FAILS: move-error DOM element no longer exists; onMutationError not called with body text.
  // After fix, onMutationError is called with description containing body message.
  it('handleTransitionClick non-ok {code,message}: onMutationError called with response body message field', async () => {
    const errorBody = { code: 'LOCK_ERROR', message: 'transition blocked: reviewer lock active' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(mutationErrorSpy)

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
        expect(mutationErrorSpy).toHaveBeenCalledWith(
          'Move failed',
          expect.stringContaining('transition blocked: reviewer lock active'),
          'error',
        )
      },
      { timeout: 1000 },
    )
  })

  // FAILS: same root cause — onMutationError not called with detail field.
  // After fix, description contains 'concurrent modification: task updated elsewhere'.
  it('handleTransitionClick non-ok {detail}: onMutationError called with response body detail field', async () => {
    const errorBody = { detail: 'concurrent modification: task updated elsewhere' }
    vi.stubGlobal('fetch', makeJsonFetch(422, errorBody))

    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(mutationErrorSpy)

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
        expect(mutationErrorSpy).toHaveBeenCalledWith(
          'Move failed',
          expect.stringContaining('concurrent modification: task updated elsewhere'),
          'error',
        )
      },
      { timeout: 1000 },
    )
  })

  // FAILS: onMutationError not called; no body parsing.
  // After fix, description is not the bare status-only fallback string.
  it('handleTransitionClick non-ok: onMutationError description is not the bare status-only fallback string', async () => {
    const errorBody = { code: 'INTERNAL', message: 'engine timeout on move' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(mutationErrorSpy)

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
        expect(mutationErrorSpy).toHaveBeenCalled()
        const [[, description]] = mutationErrorSpy.mock.calls as [[string, string, string]]
        expect(description).not.toBe('Move failed: 500')
      },
      { timeout: 1000 },
    )
  })
})

// ─── AC5: Health behavior from #1373 preserved (td:1 smoke test) ──────────────
//
// The aggregate health false-OK guard lives in WorkspaceStatus — KanbanBoard has
// no health state. This smoke test confirms that KanbanBoard move error handling
// is independent of health state: the board renders correctly AND move-error
// body parsing works (the body-parsing assertion is what makes this FAIL now).

describe('TestFromAC_HealthPreservation', () => {
  // FAILS: move-error DOM element no longer exists; onMutationError not called with body text.
  // After fix, onMutationError is called with description containing body message field.
  it('KanbanBoard move error is independent of health scan; onMutationError called with body text', async () => {
    const errorBody = { code: 'MOVE_FAIL', message: 'board move rejected: index locked' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const mutationErrorSpy = vi.fn()
    const { container } = renderBoard(mutationErrorSpy)

    // Board renders without a health indicator (health is Shell-level, not KanbanBoard-level)
    expect(container.querySelector('[data-health]')).toBeNull()

    // Trigger an explicit context-menu move that fails.
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
        expect(mutationErrorSpy).toHaveBeenCalledWith(
          'Move failed',
          expect.stringContaining('board move rejected: index locked'),
          'error',
        )
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
