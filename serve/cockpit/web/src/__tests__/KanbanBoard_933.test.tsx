import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
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
    },
  ],
  mtime: 1713456000,
}

// ─── Fetch stub helpers ───────────────────────────────────────────────────────

/** /api/board fails with network error; /api/tasks succeeds */
function stubBoardNetworkError() {
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

/** /api/tasks returns HTTP 500 (ok: false); /api/board succeeds */
function stubTasksHttpError() {
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
        <KanbanBoard />
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
