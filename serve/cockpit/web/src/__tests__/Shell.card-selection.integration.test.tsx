/**
 * live-component proofs for AC1 and AC2.
 *
 * Supplements Shell_1228.test.tsx with reviewer-required live-component evidence:
 *   AC1 (td:2) — clicking a real [data-testid="task-card"] sets data-selected="true"
 *                and selection moves to a second card when clicked
 *   AC2 (td:2) — DetailTab local state re-initialises from the new task on
 *                selection change (key remount delivers fresh editor values)
 *
 * This file intentionally does NOT mock KanbanBoard or DetailTab.
 * useBoard is mocked at the hook level so cards render without real polling.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted) ──────────────────────────────────────────────────
// KanbanBoard and DetailTab are intentionally NOT mocked in this file.

vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))
vi.mock('../hooks/useWorkspaceHealth', () => ({
  useWorkspaceHealth: vi.fn(() => ({
    health: { status: 'healthy', modules: {} },
    connectionError: null,
    isFetching: false,
    receipt: null,
    refresh: vi.fn(),
    refreshAfterMutation: vi.fn(),
    mergeRepair: vi.fn(),
    dismissReceipt: vi.fn(),
  })),
}))

vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(() => null),
}))

// ActivityTab self-fetches /api/sessions on mount; mock to keep fetch surface clean.
vi.mock('../components/ActivityTab', () => ({
  default: vi.fn(() => <div data-testid="activity-tab-stub" />),
}))

// react-markdown — mocked to avoid ESM/plugin issues in JSDOM.
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import type { Board, Task } from '../hooks/useBoard'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'backlog' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    todo: ['backlog'],
    backlog: ['todo'],
  },
}

const TASK_42: Task = {
  id: 42,
  title: 'Task Forty-Two',
  status: 'todo',
  priority: 'needed',
  updated: '2026-01-01T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASK_99: Task = {
  id: 99,
  title: 'Task Ninety-Nine',
  status: 'todo',
  priority: 'important',
  updated: '2026-01-01T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

// Full TaskDetail objects returned by /api/tasks/{id}.
const TASK_42_DETAIL = {
  ...TASK_42,
  body: '',
  created: '2026-01-01T00:00:00+00:00',
  parent: null,
  depends_on: [],
}

const TASK_99_DETAIL = {
  ...TASK_99,
  body: '',
  created: '2026-01-01T00:00:00+00:00',
  parent: null,
  depends_on: [],
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function stubHooks() {
  vi.mocked(useBoard).mockReturnValue({
    board: BOARD,
    tasks: [TASK_42, TASK_99],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks: vi.fn(),
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)
}

function stubFetch(taskMap: Record<number, object> = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const match = /\/api\/tasks\/(\d+)$/.exec(url)
      if (match) {
        const id = parseInt(match[1], 10)
        const data = taskMap[id]
        if (data) {
          return { ok: true, json: async () => data } as Response
        }
      }
      // Non-matched URLs pend until aborted — prevents act() warnings.
      return new Promise<never>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      })
    }),
  )
  return vi.mocked(fetch)
}

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

function findDialogAction(dialog: Element, pattern: RegExp): HTMLElement | undefined {
  return Array.from(dialog.querySelectorAll<HTMLElement>('button, p-button'))
    .find((button) => pattern.test(button.textContent ?? ''))
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_CardSelection_Integration', () => {
  beforeEach(() => {
    stubHooks()
    stubFetch()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC1 integration happy: clicking a real task card sets data-selected="true"

  it('clicking a real task card sets data-selected="true" on that card', async () => {
    const { container } = renderShell()

    // Real KanbanBoard must render real cards from the mocked board state.
    await waitFor(() => {
      expect(container.querySelector('[data-testid="task-card"][data-id="42"]')).not.toBeNull()
    })

    const card42 = container.querySelector('[data-testid="task-card"][data-id="42"]')!
    // Before click: all cards unselected.
    expect(card42.getAttribute('data-selected')).toBe('false')

    fireEvent.click(card42)

    // After click: card 42 selected, card 99 not selected.
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="task-card"][data-id="42"]')!.getAttribute('data-selected'),
      ).toBe('true')
      expect(
        container.querySelector('[data-testid="task-card"][data-id="99"]')!.getAttribute('data-selected'),
      ).toBe('false')
    })
  })

  // AC1 integration edge: clicking a second card moves selection

  it('clicking a second real task card moves data-selected from first card to second', async () => {
    const { container } = renderShell()

    await waitFor(() => {
      expect(container.querySelector('[data-testid="task-card"][data-id="42"]')).not.toBeNull()
    })

    // Select card 42 first.
    fireEvent.click(container.querySelector('[data-testid="task-card"][data-id="42"]')!)
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="task-card"][data-id="42"]')!.getAttribute('data-selected'),
      ).toBe('true')
    })

    // Now click card 99 — selection must move.
    fireEvent.click(container.querySelector('[data-testid="task-card"][data-id="99"]')!)
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="task-card"][data-id="99"]')!.getAttribute('data-selected'),
      ).toBe('true')
      expect(
        container.querySelector('[data-testid="task-card"][data-id="42"]')!.getAttribute('data-selected'),
      ).toBe('false')
    })
  })
})

describe('TestFromAC_TaskDetailReinit_Integration', () => {
  beforeEach(() => {
    stubHooks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC2 integration: dirty edits ask before switching; confirmed switch reinitialises from the new task

  it('dirty task detail asks before switching, then re-initialises from the new task after Leave', async () => {
    stubFetch({ 42: TASK_42_DETAIL, 99: TASK_99_DETAIL })
    const { container } = renderShell()

    // Wait for real KanbanBoard to render cards.
    await waitFor(() => {
      expect(container.querySelector('[data-testid="task-card"][data-id="42"]')).not.toBeNull()
    })

    // Click card 42, wait for fetch to resolve and DetailTab to show task 42's title.
    fireEvent.click(container.querySelector('[data-testid="task-card"][data-id="42"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="edit-details-button"]')).not.toBeNull()
    })
    fireEvent.click(container.querySelector('[data-testid="edit-details-button"]')!)
    await waitFor(() => {
      const editForm = container.querySelector('[data-region="task-detail-edit-form"]') as HTMLElement | null
      const titleInput = container.querySelector<HTMLInputElement>('[data-field="title"]')
      expect(editForm?.hasAttribute('hidden')).toBe(false)
      expect(titleInput).not.toBeNull()
      expect(titleInput!.value).toBe('Task Forty-Two')
    })

    // Simulate user editing the title — mutates DetailTab's local state.
    const titleInput = container.querySelector<HTMLInputElement>('[data-field="title"]')!
    fireEvent(titleInput, new CustomEvent('input', {
      detail: { value: 'STALE EDITED VALUE' },
      bubbles: true,
    }))
    expect(titleInput.value).toBe('STALE EDITED VALUE')

    await waitFor(() => {
      expect(container.querySelector('[data-testid="dirty-indicator"]')).not.toBeNull()
    })

    // Switch selection to task 99 — Shell must ask before discarding local edits.
    fireEvent.click(container.querySelector('[data-testid="task-card"][data-id="99"]')!)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="task-detail-unsaved-dialog"]')).not.toBeNull()
    })
    expect(container.querySelector<HTMLInputElement>('[data-field="title"]')?.value).toBe('STALE EDITED VALUE')

    const dialog = container.querySelector('[data-testid="task-detail-unsaved-dialog"]')!
    const leave = findDialogAction(dialog, /leave/i)
    expect(leave).not.toBeUndefined()
    fireEvent.click(leave!)

    await waitFor(() => {
      const newTitleInput = container.querySelector<HTMLInputElement>('[data-field="title"]')
      expect(newTitleInput).not.toBeNull()
      expect(newTitleInput!.value).toBe('Task Ninety-Nine')
    })
  })

  // AC2 integration boundary: switching tasks clears the stale title before new task loads

  it('title input does not show previous task title while new task is loading', async () => {
    // Only task 42 resolves immediately; task 99 remains pending to observe the in-between state.
    stubFetch({ 42: TASK_42_DETAIL })
    const { container } = renderShell()

    await waitFor(() => {
      expect(container.querySelector('[data-testid="task-card"][data-id="42"]')).not.toBeNull()
    })

    // Select task 42 and wait for form to render.
    fireEvent.click(container.querySelector('[data-testid="task-card"][data-id="42"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-field="title"]')).not.toBeNull()
    })

    // Switch to task 99 (fetch will pend) — the stale title must not be visible.
    fireEvent.click(container.querySelector('[data-testid="task-card"][data-id="99"]')!)
    await waitFor(() => {
      // DetailTab with key=99 and task=null returns null — form must not be present.
      const titleInput = container.querySelector<HTMLInputElement>('[data-field="title"]')
      expect(titleInput).toBeNull()
    })
  })
})

describe('TestFromAC_HelloRouteRemoval_Integration', () => {
  beforeEach(() => {
    stubHooks()
    stubFetch()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC6 positive control: root route renders real KanbanBoard

  it('root route "/" renders the real kanban board', async () => {
    const { container } = renderShell('/')
    await waitFor(() => {
      const workspace = container.querySelector('[data-region="workspace"]')
      expect(workspace).not.toBeNull()
      // Real KanbanBoard renders data-testid="kanban-board" when board+tasks are loaded.
      expect(workspace!.querySelector('[data-testid="kanban-board"]')).not.toBeNull()
    })
  })

  // AC6 integration tight: /hello route is absent — workspace has no children

  it('navigating to /hello results in an empty workspace because no route matches', async () => {
    const { container } = renderShell('/hello')
    const workspace = container.querySelector('[data-region="workspace"]')
    expect(workspace).not.toBeNull()
    // If the /hello route existed it would render at least one child element.
    // An empty workspace proves the route was removed, not merely that hello text is absent.
    expect(workspace!.childElementCount).toBe(0)
  })
})
