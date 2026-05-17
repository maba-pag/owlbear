/**
 * KanbanBoard mutation callback wiring (task #1498)
 *
 * Covers:
 *   AC-2 — handleDrop/handleTransitionClick call onMutationError('Move failed', msg, 'error')
 *           on non-2xx responses; data-testid="move-error" plain div removed
 *   AC-6 — handleDrop/handleTransitionClick call onMutationSuccess() after successful 2xx move
 *
 * Expected builder changes:
 *   - Add onMutationError / onMutationSuccess props to KanbanBoardProps
 *   - handleDrop: replace setMoveError(...) with onMutationError?.('Move failed', msg, 'error')
 *   - handleDrop 2xx: call onMutationSuccess?.() after refetchTasks()
 *   - handleTransitionClick: replace setMoveError(...) with onMutationError?.('Move failed', ...)
 *   - handleTransitionClick 2xx: call onMutationSuccess?.()
 *   - Remove <div data-testid="move-error"> from render output
 */
import { describe, it, expect, vi, afterEach, beforeAll } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard, { type KanbanBoardProps } from '../KanbanBoard'

// ─── Mock ArchivalModal ───────────────────────────────────────────────────────

vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(() => null),
}))

// ─── Extended props type (post-implementation shape) ─────────────────────────

interface KanbanBoardTestProps extends KanbanBoardProps {
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
  onMutationSuccess?: () => void
}

const KanbanBoardWithCallbacks = KanbanBoard as React.ComponentType<KanbanBoardTestProps>

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [{ name: 'backlog' }, { name: 'todo' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog'],
  } as Record<string, string[]>,
}

const TASK_ONE = {
  id: 7,
  title: 'Drag this task',
  status: 'backlog',
  priority: 'needed',
  updated: '2026-05-01T12:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

// ─── Fetch helpers ────────────────────────────────────────────────────────────

function stubMoveFetch(opts: { status?: number; network?: boolean } = {}) {
  const { status = 200, network = false } = opts
  const mockFetch = vi.fn((url: string) => {
    if (/\/api\/tasks\/\d+\/move/.test(url)) {
      if (network) return Promise.reject(new Error('Network failure'))
      return Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        json: () => Promise.resolve({ detail: `HTTP ${status}` }),
        text: () => Promise.resolve(`HTTP ${status}`),
      })
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`))
  })
  vi.stubGlobal('fetch', mockFetch)
  return mockFetch
}

// ─── Render helpers ───────────────────────────────────────────────────────────

beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

function renderBoard(
  extraProps: Pick<KanbanBoardTestProps, 'onMutationError' | 'onMutationSuccess'> = {},
) {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoardWithCallbacks
          board={BOARD}
          tasks={[TASK_ONE]}
          loading={false}
          error={null}
          refetchTasks={vi.fn()}
          {...extraProps}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Drag helpers ─────────────────────────────────────────────────────────────

async function dragCard(container: HTMLElement, taskId: number = 7) {
  await waitFor(() => {
    expect(
      container.querySelector(`[data-testid="task-card"][data-id="${taskId}"]`),
    ).not.toBeNull()
  })
  const card = container.querySelector(`[data-testid="task-card"][data-id="${taskId}"]`)!
  fireEvent.dragStart(card)
}

function dropOnColumn(container: HTMLElement, status: string) {
  const col = container.querySelector(`[data-column="${status}"]`)!
  fireEvent.dragOver(col)
  fireEvent.drop(col)
}

async function openContextMenu(container: HTMLElement, taskId: number = 7) {
  await waitFor(() => {
    expect(
      container.querySelector(`[data-testid="task-card"][data-id="${taskId}"]`),
    ).not.toBeNull()
  })
  fireEvent.contextMenu(
    container.querySelector(`[data-testid="task-card"][data-id="${taskId}"]`)!,
  )
  await waitFor(() => {
    expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
  })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_KanbanBoardMutationCallbacks', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── AC-2: handleDrop calls onMutationError on non-2xx ───────────────────

  describe('AC-2: handleDrop calls onMutationError on failure', () => {
    it('handleDrop calls onMutationError with "Move failed" on 500 response', async () => {
      stubMoveFetch({ status: 500 })
      const spy = vi.fn()
      const { container } = renderBoard({ onMutationError: spy })

      await dragCard(container)
      dropOnColumn(container, 'todo')

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
      })
    })

    it('handleDrop calls onMutationError with "Move failed" on 409 response', async () => {
      stubMoveFetch({ status: 409 })
      const spy = vi.fn()
      const { container } = renderBoard({ onMutationError: spy })

      await dragCard(container)
      dropOnColumn(container, 'todo')

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
      })
    })

    it('handleDrop calls onMutationError with "Move failed" on network error', async () => {
      stubMoveFetch({ network: true })
      const spy = vi.fn()
      const { container } = renderBoard({ onMutationError: spy })

      await dragCard(container)
      dropOnColumn(container, 'todo')

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
      })
    })
  })

  // ─── AC-2: handleTransitionClick calls onMutationError on failure ─────────

  describe('AC-2: handleTransitionClick calls onMutationError on failure', () => {
    it('handleTransitionClick calls onMutationError with "Move failed" on 500 response', async () => {
      stubMoveFetch({ status: 500 })
      const spy = vi.fn()
      const { container } = renderBoard({ onMutationError: spy })

      await openContextMenu(container)
      fireEvent.click(
        container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
      )

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
      })
    })

    it('handleTransitionClick calls onMutationError with "Move failed" on 409 response', async () => {
      stubMoveFetch({ status: 409 })
      const spy = vi.fn()
      const { container } = renderBoard({ onMutationError: spy })

      await openContextMenu(container)
      fireEvent.click(
        container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
      )

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
      })
    })

    it('handleTransitionClick calls onMutationError with "Move failed" on network error', async () => {
      stubMoveFetch({ network: true })
      const spy = vi.fn()
      const { container } = renderBoard({ onMutationError: spy })

      await openContextMenu(container)
      fireEvent.click(
        container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
      )

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
      })
    })
  })

  // ─── AC-2: data-testid="move-error" div removed ──────────────────────────

  describe('AC-2: move-error div is removed from DOM', () => {
    it('does not render data-testid="move-error" div after a failed drop', async () => {
      stubMoveFetch({ status: 500 })
      const spy = vi.fn()
      const { container } = renderBoard({ onMutationError: spy })

      await dragCard(container)
      dropOnColumn(container, 'todo')

      // Allow async fetch to settle.
      await waitFor(() => {
        expect(spy).toHaveBeenCalledTimes(1)
      })

      expect(container.querySelector('[data-testid="move-error"]')).toBeNull()
    })

  })

  // ─── AC-6: success calls onMutationSuccess ───────────────────────────────

  describe('AC-6: successful move calls onMutationSuccess', () => {
    it('handleDrop calls onMutationSuccess after 2xx response', async () => {
      stubMoveFetch({ status: 200 })
      const successSpy = vi.fn()
      const { container } = renderBoard({ onMutationSuccess: successSpy })

      await dragCard(container)
      dropOnColumn(container, 'todo')

      await waitFor(() => {
        expect(successSpy).toHaveBeenCalledTimes(1)
      })
    })

    it('handleTransitionClick calls onMutationSuccess after 2xx response', async () => {
      stubMoveFetch({ status: 200 })
      const successSpy = vi.fn()
      const { container } = renderBoard({ onMutationSuccess: successSpy })

      await openContextMenu(container)
      fireEvent.click(
        container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
      )

      await waitFor(() => {
        expect(successSpy).toHaveBeenCalledTimes(1)
      })
    })
  })
})
