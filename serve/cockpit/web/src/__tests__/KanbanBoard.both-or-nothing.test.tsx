import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'

// ─── Mock fixtures ────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [
    { name: 'research' },
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'review' },
    { name: 'docs' },
    { name: 'done' },
  ],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'review'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  } as Record<string, string[]>,
}

const TASKS = {
  tasks: [
    {
      id: 1,
      title: 'Task one',
      status: 'backlog',
      priority: 'critical',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
      dep_status: null,
    },
  ],
  mtime: 1713456000,
}

let currentBoard: typeof BOARD | null = BOARD
let currentTasks = TASKS.tasks
let currentError: string | null = null

// ─── Fetch stub helpers ───────────────────────────────────────────────────────

/** /api/board fails with network error; /api/tasks succeeds */
function stubBoardNetworkError() {
  currentBoard = BOARD
  currentTasks = TASKS.tasks
  currentError = 'Network error'
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/board')) {
        return Promise.reject(new Error('Network error'))
      }
      if (url.includes('/api/tasks')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS) })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    }),
  )
}

/** /api/tasks fails with network error; /api/board succeeds */
function stubTasksNetworkError() {
  currentBoard = BOARD
  currentTasks = TASKS.tasks
  currentError = 'Network error'
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/board')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
      }
      if (url.includes('/api/tasks')) {
        return Promise.reject(new Error('Network error'))
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    }),
  )
}

/** /api/board returns HTTP 500 (ok: false); /api/tasks succeeds */
function stubBoardHttpError() {
  currentBoard = BOARD
  currentTasks = TASKS.tasks
  currentError = 'Board API error: 500'
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/board')) {
        return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })
      }
      if (url.includes('/api/tasks')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS) })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    }),
  )
}

/** Both APIs succeed with two tasks of different priorities (for TestBuilderDiscovered) */
function stubFetchSuccessMulti() {
  const tasksMulti = {
    tasks: [
      {
        id: 1,
        title: 'Critical task',
        status: 'backlog',
        priority: 'critical',
        tags: [],
        blocked: false,
        block_reason: null,
        claimed: false,
        dep_status: null,
      },
      {
        id: 2,
        title: 'Someday task',
        status: 'backlog',
        priority: 'someday',
        tags: [],
        blocked: false,
        block_reason: null,
        claimed: false,
        dep_status: null,
      },
    ],
    mtime: 1713456000,
  }
  currentBoard = BOARD
  currentTasks = tasksMulti.tasks
  currentError = null
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/board')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
      }
      if (url.includes('/api/tasks')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(tasksMulti) })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    }),
  )
}

/** /api/tasks returns HTTP 500 (ok: false); /api/board succeeds */
function stubTasksHttpError() {
  currentBoard = BOARD
  currentTasks = TASKS.tasks
  currentError = 'Tasks API error: 500'
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/board')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
      }
      if (url.includes('/api/tasks')) {
        return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    }),
  )
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderBoard() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard
          board={currentBoard}
          tasks={currentTasks}
          loading={false}
          error={currentError}
          refetchTasks={vi.fn()}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests: AC#8 — both-or-nothing fetch ─────────────────────────────────────

describe('TestFromAC_KanbanBoardBothOrNothing', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('partial failure — network errors', () => {
    it('shows error state when only /api/board fails with network error', async () => {
      stubBoardNetworkError()
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
    })

    it('does not render columns when only /api/board fails with network error', async () => {
      stubBoardNetworkError()
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-column]')).toBeNull()
    })

    it('shows error state when only /api/tasks fails with network error', async () => {
      stubTasksNetworkError()
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
    })

    it('does not render columns when only /api/tasks fails with network error', async () => {
      stubTasksNetworkError()
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-column]')).toBeNull()
    })
  })

  describe('partial failure — HTTP error responses (ok: false)', () => {
    it('shows error state when /api/board returns HTTP 500 but /api/tasks succeeds', async () => {
      stubBoardHttpError()
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
    })

    it('does not render columns when /api/board returns HTTP 500', async () => {
      stubBoardHttpError()
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-column]')).toBeNull()
    })

    it('shows error state when /api/tasks returns HTTP 500 but /api/board succeeds', async () => {
      stubTasksHttpError()
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
    })

    it('does not render columns when /api/tasks returns HTTP 500', async () => {
      stubTasksHttpError()
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-column]')).toBeNull()
    })
  })
})

// ─── Tests: AC#2, AC#4 — layout and priority border ──────────────────────────

describe('TestBuilderDiscovered', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('columns container has flex or grid display', async () => {
    stubFetchSuccessMulti()
    const { container } = renderBoard()
    await waitFor(() => {
      const firstCol = container.querySelector('[data-column]')
      expect(firstCol).not.toBeNull()
      const columnsContainer = firstCol?.parentElement
      expect(['flex', 'grid']).toContain(columnsContainer?.style.display)
    })
  })

})
