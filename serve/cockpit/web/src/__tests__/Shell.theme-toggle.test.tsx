/**
 * Task #1548 — P3-06: impl — theme toggle UI: status bar button
 * Covers: AC-4 (Shell.tsx renders ThemeToggle after DRStatusIndicator)
 *
 * RED phase: Shell.tsx does not import or render ThemeToggle yet.
 * Tests fail with AssertionError (element not found / wrong DOM order).
 *
 * ThemeToggle is mocked here so Shell integration failures are isolated to
 * AC-4 placement logic, not the missing component file.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import type { Board, Task } from '../hooks/useBoard'

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => <div data-testid="kb-stub" />),
}))

// Stub ThemeToggle so that when Shell renders it the element is identifiable.
// The test verifies Shell imports and places the stub — Shell currently does NOT
// do so, so the assertions below will fail (RED).
vi.mock('../components/ThemeToggle', () => ({
  default: vi.fn(() => <button data-testid="theme-toggle-stub" type="button">Theme</button>),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }, { name: 'done' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: { todo: ['in-progress'], 'in-progress': ['done'], done: [] },
}

const MOCK_TASKS: Task[] = [
  {
    id: 1,
    title: 'Task one',
    status: 'todo',
    priority: 'needed',
    updated: '2026-01-01T00:00:00Z',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

function stubShellHooks() {
  vi.mocked(useBoard).mockReturnValue({
    board: MOCK_BOARD,
    tasks: MOCK_TASKS,
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks: vi.fn(),
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)

  vi.mocked(usePendingDRs).mockReturnValue({
    count: 1,
    items: [{ id: 'dr-1', title: 'DR one', created: '2026-01-01T00:00:00Z' }],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)

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

// ─── AC-4: Shell places ThemeToggle after workspace status ──────────────────

describe('TestFromAC_ShellThemeTogglePlacement_1548', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    stubShellHooks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('AC-4 happy: Shell status bar renders ThemeToggle', () => {
    const { container } = renderShell()
    const statusBar = container.querySelector('[data-region="status-bar"]')

    expect(statusBar, 'status-bar region must exist').not.toBeNull()
    expect(
      within(statusBar as HTMLElement).getByTestId('theme-toggle-stub'),
      'ThemeToggle must be rendered inside the status bar',
    ).toBeInTheDocument()
  })

  it('AC-4 happy: ThemeToggle appears after workspace status in DOM order', () => {
    const { container } = renderShell()
    const statusBar = container.querySelector('[data-region="status-bar"]')

    expect(statusBar, 'status-bar region must exist').not.toBeNull()
    const bar = statusBar as HTMLElement
    const workspaceStatus = within(bar).getByTestId('workspace-status')
    const themeToggle = within(bar).getByTestId('theme-toggle-stub')

    // DOCUMENT_POSITION_FOLLOWING (4) = themeToggle is a later sibling/descendant
    const position = workspaceStatus.compareDocumentPosition(themeToggle)
    expect(
      position & Node.DOCUMENT_POSITION_FOLLOWING,
      'ThemeToggle must follow workspace status in DOM order',
    ).toBeTruthy()
  })
})
