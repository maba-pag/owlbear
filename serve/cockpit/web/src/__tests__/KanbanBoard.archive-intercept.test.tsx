/**
 * handleTransitionClick archive intercept (F3)
 *
 * Covers:
 *   AC1 — clicking → archived opens ArchivalModal; no POST /move fires immediately
 *   AC2 — non-archived transitions (e.g. → todo) remain unaffected; POST still fires
 *   AC3 — ArchivalModal receives taskId, taskStatus, and expectedUpdated props
 *   AC4 — expectedUpdated is frozen at context-menu-open time; not re-read from
 *          a polling-updated task reference after the menu opens
 *
 * KanbanBoard.tsx.
 *
 * Expected KanbanBoard.tsx changes:
 *   - Import ArchivalModal from './components/ArchivalModal'
 *   - handleTransitionClick: when targetStatus === 'archived', open ArchivalModal
 *     instead of POSTing the move
 *   - Pass taskId, taskStatus, expectedUpdated (= contextMenu.taskUpdated) to ArchivalModal
 *
 * ArchivalModal stub (data-testid="archival-modal-stub"):
 *   data-task-id      — taskId prop (stringified)
 *   data-task-status  — taskStatus prop
 *   data-expected-updated — expectedUpdated prop
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'

// ─── Mock ArchivalModal ───────────────────────────────────────────────────────
// Factory mock — ArchivalModal.tsx does not exist yet (built in task #1241).
// Provides a stub that exposes received props as data attributes for assertions.
// Path resolves to src/components/ArchivalModal — same as KanbanBoard.tsx will use
// with './components/ArchivalModal' once F3 is implemented.
vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(
    ({
      taskId,
      taskStatus,
      expectedUpdated,
    }: {
      taskId: number
      taskStatus: string
      expectedUpdated: string
    }) => (
      <div
        data-testid="archival-modal-stub"
        data-task-id={String(taskId)}
        data-task-status={taskStatus}
        data-expected-updated={expectedUpdated}
      />
    ),
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

// Board has `archived` as a valid transition from `done` (F3 target status).
// `backlog → todo` provides a non-archived transition for AC2 regression guard.
const BOARD = {
  statuses: [
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'done' },
  ],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'done'],
    done: ['archived'], // archived is a valid transition from done
  } as Record<string, string[]>,
}

// Task 1: status=done  — can transition to archived (AC1/AC3/AC4 subject)
// Task 2: status=backlog — can transition to todo   (AC2 regression guard)
const TASKS = {
  tasks: [
    {
      id: 1,
      title: 'Completed task',
      status: 'done',
      priority: 'needed',
      updated: '2026-01-01T00:00:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
    {
      id: 2,
      title: 'Backlog task',
      status: 'backlog',
      priority: 'needed',
      updated: '2026-01-02T00:00:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
  ],
  mtime: 1000,
}

// ─── Fetch stub ───────────────────────────────────────────────────────────────

function stubFetch(tasks: typeof TASKS = TASKS) {
  const mockFetch = vi.fn((url: string) => {
    if (url.includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    if (/\/api\/tasks\/\d+\/move/.test(url)) {
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
    }
    if (url.includes('/api/tasks')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(tasks) })
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
        <KanbanBoard
          board={BOARD}
          tasks={TASKS.tasks}
          loading={false}
          error={null}
          refetchTasks={vi.fn()}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Context-menu helper ──────────────────────────────────────────────────────

async function openContextMenuForTask(container: HTMLElement, taskId: number) {
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

describe('TestFromAC_HandleTransitionClickArchive', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── AC1: clicking → archived opens ArchivalModal; no POST fires ───────────

  it('clicking → archived transition renders ArchivalModal instead of firing a move', async () => {
    stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await waitFor(() => {
      expect(container.querySelector('[data-testid="archival-modal-stub"]')).not.toBeNull()
    })
  })

  it('clicking → archived transition does not fire POST /api/tasks/{id}/move', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    // Allow microtasks to settle; a real POST would appear in mockFetch.mock.calls
    await new Promise((resolve) => setTimeout(resolve, 50))
    const moveCalls = mockFetch.mock.calls.filter(([url]: [string]) =>
      /\/api\/tasks\/\d+\/move/.test(url),
    )
    expect(moveCalls).toHaveLength(0)
  })

  // ─── AC2: non-archived transitions remain unaffected (regression guard) ────
  // Combined test: archived click must NOT fire a POST, non-archived click MUST.
  // Currently fails RED because the archived transition fires an immediate POST
  // (no conditional branch exists yet). After F3, only the non-archived click
  // fires a POST, making exactly one move call targeting /api/tasks/2/move.

  it('non-archived transition fires POST while archived transition in the same session fires none', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()

    // Click → archived on task 1 (done) — must NOT fire POST after F3
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    // Allow async settle so any erroneous POST would appear in mock.calls
    await new Promise((resolve) => setTimeout(resolve, 50))

    // Click → todo on task 2 (backlog) — must still fire POST (AC2 regression guard)
    await openContextMenuForTask(container, 2)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
    )

    await waitFor(() => {
      const moveCalls = mockFetch.mock.calls.filter(([url]: [string]) =>
        /\/api\/tasks\/\d+\/move/.test(url),
      )
      // Exactly one POST — the non-archived transition only
      expect(moveCalls).toHaveLength(1)
      expect(moveCalls[0][0]).toContain('/api/tasks/2/move')
    })
  })

  // ─── AC3: ArchivalModal receives correct props ─────────────────────────────

  it('ArchivalModal receives taskId prop matching the task being archived', async () => {
    stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1) // task id=1
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await waitFor(() => {
      const modal = container.querySelector('[data-testid="archival-modal-stub"]')
      expect(modal).not.toBeNull()
      expect(modal?.getAttribute('data-task-id')).toBe('1')
    })
  })

  it('ArchivalModal receives taskStatus prop matching the task status at context-menu-open time', async () => {
    stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1) // task id=1 has status='done'
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await waitFor(() => {
      const modal = container.querySelector('[data-testid="archival-modal-stub"]')
      expect(modal?.getAttribute('data-task-status')).toBe('done')
    })
  })

  it('ArchivalModal receives expectedUpdated prop equal to task.updated at context-menu-open time', async () => {
    stubFetch() // task 1 has updated='2026-01-01T00:00:00+00:00'
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await waitFor(() => {
      const modal = container.querySelector('[data-testid="archival-modal-stub"]')
      expect(modal?.getAttribute('data-expected-updated')).toBe('2026-01-01T00:00:00+00:00')
    })
  })

  // ─── AC4: expectedUpdated is frozen at context-menu-open time ─────────────
  // When polling updates task.updated between menu-open and the click, the
  // expectedUpdated prop must still hold the value captured at menu-open time
  // (i.e. contextMenu.taskUpdated, not tasks.find(...)?.updated).

  it('expectedUpdated is frozen at context-menu-open time and not re-read from a polling-updated task', async () => {
    const FROZEN = '2026-01-01T00:00:00+00:00'
    const POLLED = '2026-02-01T00:00:00+00:00'

    const initialTasks = [
      {
        id: 1,
        title: 'Completed task',
        status: 'done',
        priority: 'needed',
        updated: FROZEN,
        tags: [],
        blocked: false,
        block_reason: null,
        claimed: false,
      },
      {
        id: 2,
        title: 'Backlog task',
        status: 'backlog',
        priority: 'needed',
        updated: '2026-01-02T00:00:00+00:00',
        tags: [],
        blocked: false,
        block_reason: null,
        claimed: false,
      },
    ]

    const updatedTasks = [
      {
        ...initialTasks[0],
        updated: POLLED,
      },
      initialTasks[1],
    ]

    const { container, rerender } = render(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <KanbanBoard
            board={BOARD}
            tasks={initialTasks}
            loading={false}
            error={null}
            refetchTasks={vi.fn()}
          />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    await openContextMenuForTask(container, 1)

    rerender(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <KanbanBoard
            board={BOARD}
            tasks={updatedTasks}
            loading={false}
            error={null}
            refetchTasks={vi.fn()}
          />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )

    await act(async () => {})

    const modal = container.querySelector('[data-testid="archival-modal-stub"]')
    expect(modal).not.toBeNull()
    // Must be FROZEN (captured at menu-open), NOT POLLED (updated props)
    expect(modal?.getAttribute('data-expected-updated')).toBe(FROZEN)
  })

  // ─── Brief F3 timing split: taskStatus at intercept time, expectedUpdated frozen ─
  // When polling updates task.status between menu-open and archived-click,
  // ArchivalModal must receive the LIVE status at click time (not the frozen
  // menu-open snapshot). expectedUpdated must still come from menu-open.
  //
  // This test fails against the current implementation because it passes
  // contextMenu.taskStatus (frozen at menu-open = 'done') instead of reading
  // the live tasks snapshot at intercept time (= 'in-progress' after the poll).
  // brief.md F3 lines 165-170: "taskStatus — task.status at intercept time".

  it('taskStatus passed to ArchivalModal reflects task.status at archived-click time, ' +
    'not context-menu-open time', async () => {
    const FROZEN_UPDATED = '2026-01-01T00:00:00+00:00'
    const POLLED_UPDATED = '2026-02-01T00:00:00+00:00'

    const initialTasks = [
      {
        id: 1,
        title: 'Completed task',
        status: 'done',
        priority: 'needed',
        updated: FROZEN_UPDATED,
        tags: [],
        blocked: false,
        block_reason: null,
        claimed: false,
      },
      {
        id: 2,
        title: 'Backlog task',
        status: 'backlog',
        priority: 'needed',
        updated: '2026-01-02T00:00:00+00:00',
        tags: [],
        blocked: false,
        block_reason: null,
        claimed: false,
      },
    ]

    const updatedTasks = [
      {
        ...initialTasks[0],
        status: 'in-progress',
        updated: POLLED_UPDATED,
      },
      initialTasks[1],
    ]

    const { container, rerender } = render(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <KanbanBoard
            board={BOARD}
            tasks={initialTasks}
            loading={false}
            error={null}
            refetchTasks={vi.fn()}
          />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    await openContextMenuForTask(container, 1)

    rerender(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <KanbanBoard
            board={BOARD}
            tasks={updatedTasks}
            loading={false}
            error={null}
            refetchTasks={vi.fn()}
          />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
    expect(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]'),
    ).not.toBeNull()

    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await act(async () => {})

    const modal = container.querySelector('[data-testid="archival-modal-stub"]')
    expect(modal).not.toBeNull()
    // Must be the LIVE intercept-time status, NOT the frozen menu-open status
    expect(modal?.getAttribute('data-task-status')).toBe('in-progress')
    // expectedUpdated must still be the FROZEN value from menu-open time
    expect(modal?.getAttribute('data-expected-updated')).toBe(FROZEN_UPDATED)
  })
})

