import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { useEffect, useState } from 'react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'
import type { Board, Task } from '../hooks/useBoard'

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
      updated: '2026-04-27T10:00:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
      dep_status: null,
    },
    {
      id: 2,
      title: 'Blocked task',
      status: 'todo',
      priority: 'needed',
      updated: '2026-04-27T10:01:00+00:00',
      tags: ['bug'],
      blocked: true,
      block_reason: 'Waiting for API',
      claimed: false,
      dep_status: null,
    },
    {
      id: 3,
      title: 'Active task',
      status: 'in-progress',
      priority: 'important',
      updated: '2026-04-27T10:02:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: true,
      dep_status: null,
    },
    {
      id: 4,
      title: 'Low priority task',
      status: 'backlog',
      priority: 'someday',
      updated: '2026-04-27T10:03:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
      dep_status: null,
    },
    {
      id: 5,
      title: 'Completed task',
      status: 'done',
      priority: 'nice-to-have',
      updated: '2026-04-27T10:04:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
      dep_status: null,
    },
  ],
  mtime: 1713456000,
}

function makeRect(left: number, right: number): DOMRect {
  return {
    x: left,
    y: 0,
    left,
    right,
    top: 0,
    bottom: 800,
    width: right - left,
    height: 800,
    toJSON: () => ({}),
  } as DOMRect
}

// ─── Fetch stub helpers ───────────────────────────────────────────────────────

function stubFetchSuccess() {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/board')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
      }
      if (url.includes('/api/tasks')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS) })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    }),
  )
}

// ─── Render helper ────────────────────────────────────────────────────────────

interface RenderBoardOptions {
  board?: Board | null
  tasks?: Task[]
  loading?: boolean
  error?: string | null
  fetchOnMount?: boolean
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
}

function renderBoard(options: RenderBoardOptions = {}) {
  const {
    board = BOARD,
    tasks = TASKS.tasks,
    loading = false,
    error = null,
    fetchOnMount = true,
    onMutationError,
  } = options

  function Harness() {
    const [localTasks, setLocalTasks] = useState<Task[]>(tasks)

    useEffect(() => {
      if (!fetchOnMount) {
        return
      }

      void (async () => {
        try {
          const response = await fetch('/api/tasks')
          if (!response.ok) {
            return
          }
          const payload = (await response.json()) as { tasks: Task[] }
          setLocalTasks(payload.tasks)
        } catch {
          // Keep initial fixture data for non-network assertions.
        }
      })()
    }, [])

    const refetchTasks = () => {
      void (async () => {
        try {
          const response = await fetch('/api/tasks')
          if (!response.ok) {
            return
          }
          const payload = (await response.json()) as { tasks: Task[] }
          setLocalTasks(payload.tasks)
        } catch {
          // Keep previous data on refetch failures; component-level move errors are asserted separately.
        }
      })()
    }

    return (
      <KanbanBoard
        board={board}
        tasks={localTasks}
        loading={loading}
        error={error}
        refetchTasks={refetchTasks}
        onMutationError={onMutationError}
      />
    )
  }

  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <Harness />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_KanbanBoard', () => {
  beforeEach(() => {
    stubFetchSuccess()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('workspace header', () => {
    it('shows task count and filters without the low-value lane count', async () => {
      const { container } = renderBoard({ fetchOnMount: false })

      await waitFor(() => {
        const summary = container.querySelector('[data-testid="workspace-header-summary"]')
        expect(summary?.textContent).toContain(String(TASKS.tasks.length))
        expect(summary?.textContent).toContain('tasks')
        expect(summary?.textContent).not.toContain('lanes')
        expect(container.querySelector('[data-testid="filter-toggle"]')).not.toBeNull()
      })
    })
  })

  // ─── AC #2, #8, #9 — columns ─────────────────────────────────────────────

  describe('columns', () => {
    it('renders all 7 status columns from board config', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const columns = container.querySelectorAll('[data-column]')
        expect(columns.length).toBe(7)
      })
    })

    it('renders columns in board-config order', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const columns = Array.from(container.querySelectorAll('[data-column]'))
        const names = columns.map(col => col.getAttribute('data-column'))
        expect(names).toEqual([
          'research',
          'backlog',
          'todo',
          'in-progress',
          'review',
          'docs',
          'done',
        ])
      })
    })

    it('shows correct task count in column header', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const backlogCol = container.querySelector('[data-column="backlog"]')
        const count = backlogCol?.querySelector('[data-testid="column-count"]')
        expect(count).not.toBeNull()
        expect(count?.textContent).toBe('2')
      })
    })

    it('empty column renders designed empty state (not blank)', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        // 'research' has no tasks in the mock data
        const researchCol = container.querySelector('[data-column="research"]')
        expect(researchCol?.querySelector('[data-testid="empty-column"]')).not.toBeNull()
      })
    })

    it('empty column empty-state content is non-blank text', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const researchCol = container.querySelector('[data-column="research"]')
        const emptyState = researchCol?.querySelector('[data-testid="empty-column"]')
        expect(emptyState?.textContent?.trim().length).toBeGreaterThan(0)
      })
    })

    it('auto-aligns the strip to the first non-empty column when leading columns are empty', async () => {
      const doneOnlyTask = { ...TASKS.tasks[4], id: 99, status: 'done' }
      const scrollTo = vi.fn()
      const scrollToDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollTo')
      const scrollWidthDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollWidth')
      const clientWidthDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth')
      const originalGetBoundingClientRect = HTMLElement.prototype.getBoundingClientRect
      const rectSpy = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function getMockRect() {
        const element = this as HTMLElement
        if (element.getAttribute('data-testid') === 'kanban-column-strip') {
          return makeRect(0, 700)
        }

        const status = element.getAttribute('data-column')
        const statusIndex = BOARD.statuses.findIndex(({ name }) => name === status)
        if (statusIndex >= 0) {
          const left = statusIndex * 300
          return makeRect(left, left + 280)
        }

        return originalGetBoundingClientRect.call(this)
      })

      Object.defineProperty(HTMLElement.prototype, 'scrollTo', { configurable: true, value: scrollTo })
      Object.defineProperty(HTMLElement.prototype, 'scrollWidth', {
        configurable: true,
        get() {
          return (this as HTMLElement).getAttribute('data-testid') === 'kanban-column-strip' ? 2200 : 0
        },
      })
      Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
        configurable: true,
        get() {
          return (this as HTMLElement).getAttribute('data-testid') === 'kanban-column-strip' ? 700 : 0
        },
      })

      try {
        renderBoard({ tasks: [doneOnlyTask], fetchOnMount: false })

        await waitFor(() => {
          expect(scrollTo).toHaveBeenCalled()
        })
        expect(scrollTo).toHaveBeenCalledWith(expect.objectContaining({ behavior: 'auto' }))
        expect((scrollTo.mock.calls[0][0] as ScrollToOptions).left).toBeGreaterThan(0)
      } finally {
        rectSpy.mockRestore()
        if (scrollToDescriptor) {
          Object.defineProperty(HTMLElement.prototype, 'scrollTo', scrollToDescriptor)
        } else {
          delete (HTMLElement.prototype as Partial<HTMLElement>).scrollTo
        }
        if (scrollWidthDescriptor) {
          Object.defineProperty(HTMLElement.prototype, 'scrollWidth', scrollWidthDescriptor)
        } else {
          delete (HTMLElement.prototype as Partial<HTMLElement>).scrollWidth
        }
        if (clientWidthDescriptor) {
          Object.defineProperty(HTMLElement.prototype, 'clientWidth', clientWidthDescriptor)
        } else {
          delete (HTMLElement.prototype as Partial<HTMLElement>).clientWidth
        }
      }
    })
  })

  // ─── AC #3, #4, #5, #6 — cards ───────────────────────────────────────────

  describe('cards', () => {
    it('renders cards within their correct status column', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const backlogCol = container.querySelector('[data-column="backlog"]')
        const cards = backlogCol?.querySelectorAll('[data-testid="task-card"]')
        expect(cards?.length).toBe(2)
      })
    })

    it('card is absent from a column it does not belong to', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        // 'research' column has no tasks in the mock data
        const researchCol = container.querySelector('[data-column="research"]')
        const cards = researchCol?.querySelectorAll('[data-testid="task-card"]')
        expect(cards?.length ?? 0).toBe(0)
      })
    })

    it('sorts cards within a column by priority descending (critical first)', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const backlogCol = container.querySelector('[data-column="backlog"]')
        const cards = Array.from(backlogCol?.querySelectorAll('[data-testid="task-card"]') ?? [])
        expect(cards.length).toBe(2)
        // id=1 is critical, id=4 is someday — critical must come first
        expect(cards[0].getAttribute('data-priority')).toBe('critical')
        expect(cards[1].getAttribute('data-priority')).toBe('someday')
      })
    })

    it('card renders task title text', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const card = container.querySelector('[data-testid="task-card"][data-id="1"]')
        expect(card?.textContent).toContain('Task one')
      })
    })

    it('card title element has full title in title attribute for truncation tooltip', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const card = container.querySelector('[data-testid="task-card"][data-id="1"]')
        const titleEl = card?.querySelector('[data-testid="card-title"]')
        expect(titleEl?.getAttribute('title')).toBe('Task one')
      })
    })

    it('card has data-priority attribute matching task priority', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const card = container.querySelector('[data-testid="task-card"][data-id="1"]')
        expect(card?.getAttribute('data-priority')).toBe('critical')
      })
    })

    it('blocked card has data-signal set to "blocked"', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const card = container.querySelector('[data-testid="task-card"][data-id="2"]')
        expect(card?.getAttribute('data-signal')).toBe('blocked')
      })
    })

    it('blocked card does not render a block-badge element (AC-3: badge removed)', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const card = container.querySelector('[data-testid="task-card"][data-id="2"]')
        expect(card?.querySelector('[data-testid="block-badge"]')).toBeNull()
      })
    })

    it('unblocked card has no block badge', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const card = container.querySelector('[data-testid="task-card"][data-id="1"]')
        expect(card?.querySelector('[data-testid="block-badge"]')).toBeNull()
      })
    })

    it('claimed card has data-signal set to "claimed"', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const card = container.querySelector('[data-testid="task-card"][data-id="3"]')
        expect(card?.getAttribute('data-signal')).toBe('claimed')
      })
    })

    it('unclaimed card has no running indicator', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const card = container.querySelector('[data-testid="task-card"][data-id="1"]')
        expect(card?.querySelector('[data-testid="running-indicator"]')).toBeNull()
      })
    })
  })

  // ─── AC #7 — context menu ────────────────────────────────────────────────

  describe('context menu', () => {
    it('right-clicking a card opens a context menu', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      })
      const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
      fireEvent.contextMenu(card)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
      })
    })

    it('context menu contains all valid transition items for card status', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      })
      // Card id=1 is in 'backlog'; valid_transitions['backlog'] = ['research', 'todo']
      const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
      fireEvent.contextMenu(card)
      await waitFor(() => {
        const menu = container.querySelector('[data-testid="context-menu"]')
        const items = Array.from(menu?.querySelectorAll('[data-testid="transition-item"]') ?? [])
        const statuses = items.map(i => i.getAttribute('data-status'))
        expect(statuses).toContain('todo')
        expect(statuses).toContain('research')
      })
    })

    it('context menu does not contain invalid transition targets', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      })
      // 'done' and 'in-progress' are not reachable from 'backlog'
      const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
      fireEvent.contextMenu(card)
      await waitFor(() => {
        const menu = container.querySelector('[data-testid="context-menu"]')
        const items = Array.from(menu?.querySelectorAll('[data-testid="transition-item"]') ?? [])
        const statuses = items.map(i => i.getAttribute('data-status'))
        expect(statuses).not.toContain('done')
        expect(statuses).not.toContain('in-progress')
      })
    })

    it('context menu contains exactly as many items as valid transitions', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      })
      // Card id=1 in 'backlog'; valid_transitions['backlog'] = ['research', 'todo'] => 2 items
      const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
      fireEvent.contextMenu(card)
      await waitFor(() => {
        const menu = container.querySelector('[data-testid="context-menu"]')
        const items = menu?.querySelectorAll('[data-testid="transition-item"]')
        expect(items?.length).toBe(2)
      })
    })

    it('orders context menu transitions by board lane order', async () => {
      const board = {
        ...BOARD,
        valid_transitions: {
          ...BOARD.valid_transitions,
          backlog: ['todo', 'research'],
        },
      }
      const { container } = renderBoard({ board, fetchOnMount: false })
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      })
      const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
      fireEvent.contextMenu(card)
      await waitFor(() => {
        const menu = container.querySelector('[data-testid="context-menu"]')
        const statuses = Array.from(menu?.querySelectorAll('[data-testid="transition-item"]') ?? [])
          .map((item) => item.getAttribute('data-status'))
        expect(statuses).toEqual(['research', 'todo'])
      })
    })

    it('labels configured archive transitions as Archive', async () => {
      const board = {
        ...BOARD,
        valid_transitions: {
          ...BOARD.valid_transitions,
          backlog: ['todo', 'archived'],
        },
      }
      const { container } = renderBoard({ board, fetchOnMount: false })
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      })
      const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
      fireEvent.contextMenu(card)
      await waitFor(() => {
        const archiveItem = container.querySelector('[data-testid="transition-item"][data-status="archived"]')
        expect(archiveItem?.textContent?.trim()).toBe('Archive')
        expect(archiveItem?.className).toContain('text-error')
      })
    })
  })

  // ─── AC #962 — dismiss and accessibility ──────────────────────────────────

  describe('dismiss and accessibility', () => {
    it('clicking outside context menu dismisses it', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      })
      const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
      fireEvent.contextMenu(card)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
      })
      fireEvent.mouseDown(document.body)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="context-menu"]')).toBeNull()
      })
    })

    it('pressing Escape key dismisses context menu', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      })
      const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
      fireEvent.contextMenu(card)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
      })
      fireEvent.keyDown(document, { key: 'Escape' })
      await waitFor(() => {
        expect(container.querySelector('[data-testid="context-menu"]')).toBeNull()
      })
    })

    it('context menu has role="menu" and transition items have role="menuitem"', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      })
      const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
      fireEvent.contextMenu(card)
      await waitFor(() => {
        const menu = container.querySelector('[data-testid="context-menu"]')
        expect(menu?.getAttribute('role')).toBe('menu')
        const items = Array.from(menu?.querySelectorAll('[data-testid="transition-item"]') ?? [])
        expect(items.length).toBeGreaterThan(0)
        items.forEach(item => {
          expect(item.getAttribute('role')).toBe('menuitem')
        })
      })
    })

    it('right-clicking a done-status card shows an archive-only context menu', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-card"][data-id="5"]')).not.toBeNull()
      })
      const doneCard = container.querySelector('[data-testid="task-card"][data-id="5"]')!
      fireEvent.contextMenu(doneCard)
      await waitFor(() => {
        const menu = container.querySelector('[data-testid="context-menu"]')
        expect(menu).not.toBeNull()
        const items = Array.from(menu?.querySelectorAll('[role="menuitem"]') ?? [])
        expect(items.map((item) => item.textContent?.trim())).toEqual(['Archive'])
      })
    })
  })

  // ─── AC #10 — loading state ───────────────────────────────────────────────

  describe('loading state', () => {
    it('renders loading indicator while data is being fetched', () => {
      const { container } = renderBoard({ loading: true, fetchOnMount: false })
      expect(
        container.querySelector('[data-testid="loading-indicator"]') ??
          container.querySelector('[data-testid="skeleton"]'),
      ).not.toBeNull()
    })

    it('loading indicator is not shown after data has loaded', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        // Columns visible means data has loaded
        expect(container.querySelector('[data-column]')).not.toBeNull()
      })
      expect(
        container.querySelector('[data-testid="loading-indicator"]') ??
          container.querySelector('[data-testid="skeleton"]'),
      ).toBeNull()
    })
  })

  // ─── AC #11 — error state ─────────────────────────────────────────────────

  describe('error state', () => {
    it('renders error message element when API call fails', async () => {
      const { container } = renderBoard({ board: null, error: 'Network error', fetchOnMount: false })
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
    })

    it('error message contains non-empty recovery text', async () => {
      const { container } = renderBoard({ board: null, error: 'Network error', fetchOnMount: false })
      await waitFor(() => {
        const errorEl = container.querySelector('[data-testid="error-message"]')
        expect(errorEl?.textContent?.trim().length).toBeGreaterThan(0)
      })
    })

    it('board columns are not rendered in error state', async () => {
      const { container } = renderBoard({ board: null, error: 'Network error', fetchOnMount: false })
      await waitFor(() => {
        expect(container.querySelector('[data-testid="error-message"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-column]')).toBeNull()
    })
  })
})

// ─── Fixture: task 1 moved from backlog → todo ────────────────────────────────

const TASKS_AFTER_MOVE = {
  tasks: [
    {
      id: 1,
      title: 'Task one',
      status: 'todo',
      priority: 'critical',
      updated: '2026-04-27T10:05:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
    {
      id: 2,
      title: 'Blocked task',
      status: 'todo',
      priority: 'needed',
      updated: '2026-04-27T10:01:00+00:00',
      tags: ['bug'],
      blocked: true,
      block_reason: 'Waiting for API',
      claimed: false,
    },
    {
      id: 3,
      title: 'Active task',
      status: 'in-progress',
      priority: 'important',
      updated: '2026-04-27T10:02:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: true,
    },
    {
      id: 4,
      title: 'Low priority task',
      status: 'backlog',
      priority: 'someday',
      updated: '2026-04-27T10:03:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
  ],
  mtime: 1713456001,
}

// ─── Fetch stubs for move tests ───────────────────────────────────────────────

function stubFetchWithMoveSuccess(tasksAfterMove: typeof TASKS = TASKS) {
  let tasksCallCount = 0
  const mockFetch = vi.fn((url: string) => {
    if (url.includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    if (/\/api\/tasks\/\d+\/move/.test(url)) {
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
    }
    if (url.includes('/api/tasks')) {
      tasksCallCount += 1
      const data = tasksCallCount === 1 ? TASKS : tasksAfterMove
      return Promise.resolve({ ok: true, json: () => Promise.resolve(data) })
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`))
  })
  vi.stubGlobal('fetch', mockFetch)
  return mockFetch
}

function stubFetchWithMoveError(errorMode: '422' | 'network') {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/board')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
      }
      if (/\/api\/tasks\/\d+\/move/.test(url)) {
        if (errorMode === '422') {
          return Promise.resolve({
            ok: false,
            status: 422,
            json: () => Promise.resolve({ detail: 'Invalid transition' }),
          })
        }
        return Promise.reject(new Error('Network error'))
      }
      if (url.includes('/api/tasks')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS) })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    }),
  )
}

// ─── Tests: context menu → move action wiring ────────────────────────────────

describe('TestFromAC_ContextMenuMove', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  async function openContextMenuForCard1(container: HTMLElement) {
    await waitFor(() => {
      expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
    })
    fireEvent.contextMenu(container.querySelector('[data-testid="task-card"][data-id="1"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
    })
  }

  // ─── AC1: POST /move called with task ID from data-id and target status ───

  it('clicking transition item sends POST /api/tasks/{id}/move with correct status', async () => {
    const mockFetch = stubFetchWithMoveSuccess()
    const { container } = renderBoard()
    await openContextMenuForCard1(container)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
    )
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/tasks/1/move',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ status: 'todo', updated: '2026-04-27T10:00:00+00:00' }),
        }),
      )
    })
  })

  // ─── AC2: board refreshes — task appears in new column ───────────────────

  it('board refreshes and task appears in new column after successful move', async () => {
    stubFetchWithMoveSuccess(TASKS_AFTER_MOVE)
    const { container } = renderBoard()
    await openContextMenuForCard1(container)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
    )
    await waitFor(() => {
      const todoCol = container.querySelector('[data-column="todo"]')
      expect(todoCol?.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
    })
  })

  // ─── AC3: onMutationError called on HTTP 422 ──────────────────────────────

  it('calls onMutationError when POST /move returns HTTP 422', async () => {
    stubFetchWithMoveError('422')
    const onMutationError = vi.fn()
    const { container } = renderBoard({ onMutationError })
    await openContextMenuForCard1(container)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
    )
    await waitFor(() => {
      expect(onMutationError).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
    })
  })

  // ─── AC4: onMutationError called on network failure ───────────────────────

  it('calls onMutationError when POST /move fails with network error', async () => {
    stubFetchWithMoveError('network')
    const onMutationError = vi.fn()
    const { container } = renderBoard({ onMutationError })
    await openContextMenuForCard1(container)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
    )
    await waitFor(() => {
      expect(onMutationError).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
    })
  })

  // ─── AC5: context menu dismisses after transition click ──────────────────

  it('context menu is no longer visible after clicking a transition item', async () => {
    stubFetchWithMoveSuccess()
    const { container } = renderBoard()
    await openContextMenuForCard1(container)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
    )
    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).toBeNull()
    })
  })
})

// ─── Builder-discovered: re-right-click replaces menu ────────────────────────

describe('TestBuilderDiscovered', () => {
  beforeEach(() => {
    stubFetchSuccess()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('right-clicking a second card replaces the context menu with transitions for the new card', async () => {
    const { container } = renderBoard()
    await waitFor(() => {
      expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
    })

    // Open menu for card id=1 (backlog → transitions: research, todo)
    const card1 = container.querySelector('[data-testid="task-card"][data-id="1"]')!
    fireEvent.contextMenu(card1)
    await waitFor(() => {
      const menu = container.querySelector('[data-testid="context-menu"]')
      expect(menu).not.toBeNull()
      const statuses = Array.from(menu!.querySelectorAll('[data-testid="transition-item"]')).map(
        (el) => el.getAttribute('data-status'),
      )
      expect(statuses).toContain('research')
      expect(statuses).toContain('todo')
    })

    // Right-click card id=3 (in-progress → transitions: todo, review)
    const card3 = container.querySelector('[data-testid="task-card"][data-id="3"]')!
    fireEvent.contextMenu(card3)
    await waitFor(() => {
      const menu = container.querySelector('[data-testid="context-menu"]')
      expect(menu).not.toBeNull()
      const statuses = Array.from(menu!.querySelectorAll('[data-testid="transition-item"]')).map(
        (el) => el.getAttribute('data-status'),
      )
      expect(statuses).toContain('todo')
      expect(statuses).toContain('review')
      // Old backlog transitions must be gone
      expect(statuses).not.toContain('research')
    })
  })
})
