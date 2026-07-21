/**
 * Consolidation test: Cockpit Decisions Tab multi-tab infrastructure (#1649)
 *
 * Durable integration test verifying that routing, nav-rail, entry-path
 * convergence, and post-resolve callbacks all work together after all P1+P2
 * subtasks are complete.
 *
 * AC1: Route rendering — workspace region on /, decisions-page on /decisions,
 *      sidecar [data-region="sidecar"] and [slot="sidebar-end"] absent on both routes
 * AC2: Nav-rail integration — aria-current="page" on active route button,
 *      badge visible when DR count > 0, badge absent when count is 0
 * AC3: Entry path convergence — DecisionsPage list-item click calls
 *      setSelectedDRId(id) → Shell-level ResolveModal renders with targeted DR;
 *      Shell passes updated selectedDR prop when CockpitProvider state mutates
 * AC4: Post-resolve integration — onResolved fires: Shell calls refetchPendingDRs()
 *      (drState.refetch), calls refetchTasks(), calls setSelectedDRId(null) clearing
 *      the modal
 *
 * AC5 (backend full-stack) is in serve/cockpit/tests/test_decisions_integration.py.
 *
 * Note on AC3 snapshot guard: the `useState(() => dr)` snapshot behaviour is
 * tested at unit/integration level by the durable #1647 test file
 * (ResolveModalSnapshot_1647.test.tsx). This file focuses on the route-owned
 * DecisionsPage entry path and the Shell-level prop-passing wiring that delivers
 * the updated selectedDR to ResolveModal after an SSE-driven mutation.
 *
 * Dependencies (all archived): #1639 #1640 #1641 #1642 #1643 #1644 #1645 #1646 #1647 #1648
 */
import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from 'vitest'
import { render, fireEvent, screen, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── Module mocks (hoisted by Vitest before all imports) ──────────────────────

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

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
vi.mock('../hooks/usePendingMemoryCount', () => ({
  usePendingMemoryCount: vi.fn(() => ({ count: 0 })),
}))
vi.mock('../api/errorMessage', () => ({
  getResponseErrorMessage: vi.fn().mockResolvedValue('Task fetch failed'),
}))

// Stub Shell child components not under test
vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => <div data-testid="kanban-board-stub" />),
}))
vi.mock('../components/DetailTab', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ActivityTab', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DecisionViewport', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/RepairPanel', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ThemeToggle', () => ({ default: vi.fn(() => null) }))

// DRStatusIndicator spy: renders clickable buttons calling onItemClick per item
const mockDRStatusIndicator = vi.hoisted(() =>
  vi.fn(
    ({
      count,
      items,
      onItemClick,
    }: {
      count: number
      items: PendingDR[]
      onItemClick: (id: string) => void
    }) => (
      <div data-testid="dr-status-indicator" data-count={count}>
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            data-testid={`dr-indicator-item-${item.id}`}
            onClick={() => onItemClick(item.id)}
          >
            {item.title}
          </button>
        ))}
      </div>
    ),
  ),
)
vi.mock('../components/DRStatusIndicator', () => ({
  default: mockDRStatusIndicator,
}))

// ResolveModal spy: captures props per render so tests can inspect dr and trigger callbacks
const capturedResolveModalProps = vi.hoisted(() => ({
  current: null as {
    dr: PendingDR | null
    onResolved: () => void
    onClose: () => void
  } | null,
}))
vi.mock('../components/ResolveModal', () => ({
  default: vi.fn(
    (props: { dr: PendingDR | null; onResolved: () => void; onClose: () => void }) => {
      capturedResolveModalProps.current = props
      return (
        <div
          data-testid="resolve-modal-stub"
          data-dr-id={props.dr?.id ?? ''}
        />
      )
    },
  ),
}))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import type { Board } from '../hooks/useBoard'

// ─── PDS form-component workaround ───────────────────────────────────────────

beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }, { name: 'done' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: { todo: ['in-progress'], 'in-progress': ['done'], done: [] },
}

const DR_A: PendingDR = {
  id: 'dr-a-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 30 * 60_000).toISOString(),
  title: 'Should we refactor the cache layer?',
  body: '## Context\n\nCache is growing complex.',
  body_preview: 'Cache is growing complex.',
}

const DR_A_UPDATED: PendingDR = {
  ...DR_A,
  title: 'UPDATED: SSE-driven title change for DR A',
  body: '## Context\n\nSSE-updated body for DR A.',
  body_preview: 'SSE-updated body.',
}

// ─── Stub helpers ─────────────────────────────────────────────────────────────

function stubBoard(overrides?: { refetchTasks?: ReturnType<typeof vi.fn> }) {
  const refetchTasks = overrides?.refetchTasks ?? vi.fn()
  vi.mocked(useBoard).mockReturnValue({
    board: BOARD,
    tasks: [],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks,
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)
  return refetchTasks
}

function stubPendingDRs(partial?: Partial<ReturnType<typeof usePendingDRs>>) {
  const refetch = partial?.refetch ?? vi.fn()
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch,
    ...partial,
  } as ReturnType<typeof usePendingDRs>)
  return refetch
}

function buildShellTree(route = '/') {
  return (
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>
  )
}

function renderShell(route = '/') {
  return render(buildShellTree(route))
}

// ─── Shared fetch stub setup ──────────────────────────────────────────────────

function stubFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn((_url: string, init?: RequestInit) =>
      new Promise<never>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      }),
    ),
  )
}

// ─── AC1: Route rendering + sidecar retirement ───────────────────────────────

describe('DecisionsTabRoutesDurable', () => {
  beforeEach(() => {
    stubFetch()
    stubBoard()
    stubPendingDRs()
    capturedResolveModalProps.current = null
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('ac1 happy: Shell at / renders workspace region', () => {
    const { container } = renderShell('/')
    expect(container.querySelector('[data-region="workspace"]')).not.toBeNull()
  })

  it('ac1 happy: Shell at / renders KanbanBoard inside workspace region', () => {
    const { container } = renderShell('/')
    const workspace = container.querySelector('[data-region="workspace"]')
    expect(workspace?.querySelector('[data-testid="kanban-board-stub"]')).not.toBeNull()
  })

  it('ac1 happy: Shell at /decisions renders decisions-page testid (lazy-load verified)', async () => {
    await act(async () => {
      renderShell('/decisions')
    })
    await waitFor(() => {
      expect(screen.queryByTestId('decisions-page')).not.toBeNull()
    })
  })

  it('ac1 happy: sidecar [data-region="sidecar"] absent at / (retirement invariant)', () => {
    const { container } = renderShell('/')
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
  })

  it('ac1 happy: sidecar [data-region="sidecar"] absent at /decisions (retirement invariant)', async () => {
    let container!: HTMLElement
    await act(async () => {
      ;({ container } = renderShell('/decisions'))
    })
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
  })

  it('ac1 happy: slot="sidebar-end" absent at / route (retirement invariant)', () => {
    const { container } = renderShell('/')
    expect(container.querySelector('[slot="sidebar-end"]')).toBeNull()
  })

  it('ac1 happy: slot="sidebar-end" absent at /decisions route (retirement invariant)', async () => {
    let container!: HTMLElement
    await act(async () => {
      ;({ container } = renderShell('/decisions'))
    })
    expect(container.querySelector('[slot="sidebar-end"]')).toBeNull()
  })
})

// ─── AC2: Nav-rail aria-current + decisions badge integration ─────────────────

describe('DecisionsTabNavBadgeDurable', () => {
  beforeEach(() => {
    stubFetch()
    stubBoard()
    stubPendingDRs()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('ac2 happy: decisions nav button has aria-current="page" when at /decisions', () => {
    const { container } = renderShell('/decisions')
    const btn = container.querySelector<HTMLElement>('[data-surface="decisions"]')
    expect(btn?.getAttribute('aria-current')).toBe('page')
  })

  it('ac2 happy: kanban nav button has aria-current="page" when at /', () => {
    const { container } = renderShell('/')
    const btn = container.querySelector<HTMLElement>('[data-surface="kanban"]')
    expect(btn?.getAttribute('aria-current')).toBe('page')
  })

  it('ac2 happy: decisions button has no aria-current when at / route', () => {
    const { container } = renderShell('/')
    const btn = container.querySelector<HTMLElement>('[data-surface="decisions"]')
    expect(btn?.hasAttribute('aria-current')).toBe(false)
  })

  it('ac2 happy: nav badge [data-testid="nav-badge"] present on decisions button when count > 0', () => {
    stubPendingDRs({ count: 3, items: [DR_A], isLoading: false })
    const { container } = renderShell('/')
    const decisionsBtn = container.querySelector('[data-surface="decisions"]')
    expect(decisionsBtn?.querySelector('[data-testid="nav-badge"]')).not.toBeNull()
  })

  it('ac2 happy: nav badge text matches pending DR count', () => {
    stubPendingDRs({ count: 3, items: [DR_A], isLoading: false })
    const { container } = renderShell('/')
    const badge = container.querySelector(
      '[data-surface="decisions"] [data-testid="nav-badge"]',
    )
    expect(badge?.textContent).toBe('3')
  })

  it('ac2 happy: nav badge absent when DR count is 0', () => {
    stubPendingDRs({ count: 0, items: [], isLoading: false })
    const { container } = renderShell('/')
    const decisionsBtn = container.querySelector('[data-surface="decisions"]')
    expect(decisionsBtn?.querySelector('[data-testid="nav-badge"]')).toBeNull()
  })
})

// ─── AC3: Entry path convergence ─────────────────────────────────────────────

describe('DecisionsTabEntryPathDurable', () => {
  beforeEach(() => {
    stubFetch()
    stubBoard()
    stubPendingDRs({ count: 1, items: [DR_A], isLoading: false })
    capturedResolveModalProps.current = null
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('ac3 happy: route-owned DecisionsPage item click passes full DR data', async () => {
    await act(async () => {
      renderShell('/decisions')
    })
    await waitFor(() => {
      expect(screen.queryByTestId('decisions-page')).not.toBeNull()
    })
    fireEvent.click(screen.getByTestId(`dr-item-${DR_A.id}`))
    expect(capturedResolveModalProps.current?.dr).toMatchObject({
      id: DR_A.id,
      task_id: DR_A.task_id,
      agent: DR_A.agent,
    })
  })

  it('ac3 happy: DecisionsPage list-item click opens Shell-level ResolveModal', async () => {
    await act(async () => {
      renderShell('/decisions')
    })
    await waitFor(() => {
      expect(screen.queryByTestId('decisions-page')).not.toBeNull()
    })
    fireEvent.click(screen.getByTestId(`dr-item-${DR_A.id}`))
    expect(screen.queryByTestId('resolve-modal-stub')).not.toBeNull()
  })

  it('ac3 happy: DecisionsPage list-item click passes correct DR to ResolveModal', async () => {
    await act(async () => {
      renderShell('/decisions')
    })
    await waitFor(() => {
      expect(screen.queryByTestId('decisions-page')).not.toBeNull()
    })
    fireEvent.click(screen.getByTestId(`dr-item-${DR_A.id}`))
    expect(capturedResolveModalProps.current?.dr?.id).toBe(DR_A.id)
  })

  it('ac3 happy: Shell passes updated selectedDR prop when CockpitProvider state mutates (SSE wiring)', async () => {
    // Verifies the Shell-level prop-passing wiring: when CockpitProvider's selectedDR
    // mutates (e.g. due to an SSE-driven usePendingDRs refresh), Shell passes the new
    // DR as the `dr` prop to ResolveModal. The snapshot guard inside ResolveModal
    // (useState(() => dr)) is what prevents the displayed content from changing — that
    // guard is individually verified by the durable #1647 test file.
    const { rerender } = renderShell('/decisions')

    // Open modal
    await waitFor(() => expect(screen.queryByTestId(`dr-item-${DR_A.id}`)).not.toBeNull())
    fireEvent.click(screen.getByTestId(`dr-item-${DR_A.id}`))
    expect(capturedResolveModalProps.current?.dr?.title).toBe(DR_A.title)

    // Simulate SSE: usePendingDRs now returns updated data for the same DR id
    vi.mocked(usePendingDRs).mockReturnValue({
      count: 1,
      items: [DR_A_UPDATED],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof usePendingDRs>)

    rerender(buildShellTree('/decisions'))

    // Shell re-derives selectedDR from the updated pendingDRItems array and passes
    // DR_A_UPDATED as the new `dr` prop — the snapshot guard prevents display update.
    expect(capturedResolveModalProps.current?.dr?.title).toBe(DR_A_UPDATED.title)
  })
})

// ─── AC4: Post-resolve integration ───────────────────────────────────────────

describe('DecisionsTabPostResolveDurable', () => {
  beforeEach(() => {
    stubFetch()
    stubBoard()
    stubPendingDRs({ count: 1, items: [DR_A], isLoading: false })
    capturedResolveModalProps.current = null
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('ac4 happy: onResolved calls refetchPendingDRs (drState.refetch)', async () => {
    const refetch = vi.fn()
    stubPendingDRs({ count: 1, items: [DR_A], refetch })
    renderShell('/decisions')

    // Open modal then trigger onResolved
    await waitFor(() => expect(screen.queryByTestId(`dr-item-${DR_A.id}`)).not.toBeNull())
    fireEvent.click(screen.getByTestId(`dr-item-${DR_A.id}`))
    expect(capturedResolveModalProps.current).not.toBeNull()
    act(() => {
      capturedResolveModalProps.current!.onResolved()
    })
    expect(refetch).toHaveBeenCalled()
  })

  it('ac4 happy: onResolved calls refetchTasks (boardState.refetchTasks)', async () => {
    const refetchTasks = vi.fn()
    stubBoard({ refetchTasks })
    renderShell('/decisions')

    await waitFor(() => expect(screen.queryByTestId(`dr-item-${DR_A.id}`)).not.toBeNull())
    fireEvent.click(screen.getByTestId(`dr-item-${DR_A.id}`))
    expect(capturedResolveModalProps.current).not.toBeNull()
    act(() => {
      capturedResolveModalProps.current!.onResolved()
    })
    expect(refetchTasks).toHaveBeenCalled()
  })

  it('ac4 happy: onResolved clears modal by setting selectedDRId to null', async () => {
    const { container } = renderShell('/decisions')

    // Open modal
    await waitFor(() => expect(screen.queryByTestId(`dr-item-${DR_A.id}`)).not.toBeNull())
    fireEvent.click(screen.getByTestId(`dr-item-${DR_A.id}`))
    expect(container.querySelector('[data-testid="resolve-modal-stub"]')).not.toBeNull()

    // Trigger onResolved → setSelectedDRId(null) → modal unmounts
    act(() => {
      capturedResolveModalProps.current!.onResolved()
    })
    expect(container.querySelector('[data-testid="resolve-modal-stub"]')).toBeNull()
  })

  it('ac4 happy: onClose clears modal without triggering refetch callbacks', async () => {
    const refetch = vi.fn()
    const refetchTasks = vi.fn()
    stubBoard({ refetchTasks })
    stubPendingDRs({ count: 1, items: [DR_A], refetch })
    const { container } = renderShell('/decisions')

    await waitFor(() => expect(screen.queryByTestId(`dr-item-${DR_A.id}`)).not.toBeNull())
    fireEvent.click(screen.getByTestId(`dr-item-${DR_A.id}`))
    expect(container.querySelector('[data-testid="resolve-modal-stub"]')).not.toBeNull()

    // onClose should clear modal without calling refetch callbacks
    act(() => {
      capturedResolveModalProps.current!.onClose()
    })
    expect(container.querySelector('[data-testid="resolve-modal-stub"]')).toBeNull()
    expect(refetch).not.toHaveBeenCalled()
    expect(refetchTasks).not.toHaveBeenCalled()
  })
})
