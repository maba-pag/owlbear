/**
 * PToast success feedback — task #1624
 *
 * Covers:
 *   AC1 — Successful task-move (drag-drop or context-menu) triggers PToast:
 *          onMutationSuccess called with text containing target status name;
 *          Shell calls useToastManager().addMessage with state='success';
 *          App mounts <PToast /> inside PorscheDesignSystemProvider.
 *   AC3 — Mutation error/warning paths unchanged: PBanner still renders
 *          correctly alongside PToast (no regression).
 *
 * All tests must FAIL until the builder implements PToast wiring.
 */
import { describe, it, expect, vi, afterEach, beforeEach, beforeAll } from 'vitest'
import { render, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── PDS mock — adds PToast + useToastManager stubs ─────────────────────────

const addMessage = vi.fn()

vi.mock('@porsche-design-system/components-react', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@porsche-design-system/components-react')>()
  return {
    ...mod,
    PToast: vi.fn(() => <div data-testid="ptoast-stub" />),
    useToastManager: vi.fn(() => ({ addMessage })),
    PBanner: vi.fn(
      ({
        open = false,
        heading = '',
        description = '',
        state = 'info',
        onDismiss,
      }: {
        open?: boolean
        heading?: string
        description?: string
        state?: string
        onDismiss?: (e: CustomEvent<void>) => void
      }) =>
        open ? (
          <div
            data-testid="pbanner-stub"
            data-heading={heading}
            data-description={description}
            data-state={state}
            onClick={() => onDismiss?.(new CustomEvent('dismiss') as CustomEvent<void>)}
          />
        ) : null,
    ),
    PButton: vi.fn(
      ({
        children,
        onClick,
        ...rest
      }: {
        children?: React.ReactNode
        onClick?: React.MouseEventHandler
        [key: string]: unknown
      }) => (
        <button type="button" onClick={onClick} {...(rest as Record<string, unknown>)}>
          {children}
        </button>
      ),
    ),
  }
})

// ─── Module mocks for Shell/App rendering ────────────────────────────────────

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))

vi.mock('../components/DRStatusIndicator', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/HealthBadge', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/CleanupPanel', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DecisionViewport', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ResolveModal', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ActivityTab', () => ({
  default: vi.fn(() => <div data-testid="activity-tab-stub" />),
}))
vi.mock('../components/DetailTab', () => ({
  default: vi.fn(() => <div data-testid="detail-tab-stub" />),
}))
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))
vi.mock('../components/ArchivalModal', () => ({ default: vi.fn(() => null) }))

// ─── KanbanBoard mock — captures onMutationSuccess/Error callbacks ────────────

let capturedOnMutationSuccess: ((message?: string) => void) | undefined
let capturedOnMutationError:
  | ((heading: string, description: string, state: 'error' | 'warning') => void)
  | undefined

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(
    (props: {
      onMutationSuccess?: (message?: string) => void
      onMutationError?: (h: string, d: string, s: 'error' | 'warning') => void
    }) => {
      capturedOnMutationSuccess = props.onMutationSuccess
      capturedOnMutationError = props.onMutationError
      return <div data-testid="kanban-stub" />
    },
  ),
}))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { useScanPolling } from '../hooks/useScanPolling'
import { usePendingDRs } from '../hooks/usePendingDRs'
import Shell from '../Shell'
import App from '../App'
import { CockpitProvider } from '../hooks/CockpitProvider'
import { type KanbanBoardProps } from '../KanbanBoard'
import type { Board } from '../hooks/useBoard'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [{ name: 'backlog' }, { name: 'todo' }],
  priorities: ['someday', 'needed'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog'],
  },
}

const TASK_ONE = {
  id: 7,
  title: 'Task for move',
  status: 'backlog',
  priority: 'needed',
  updated: '2026-05-01T12:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

function stubHooks() {
  vi.mocked(useBoard).mockReturnValue({
    board: BOARD,
    tasks: [],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks: vi.fn(),
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)
  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof useScanPolling>)
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)
}

function renderShell() {
  capturedOnMutationSuccess = undefined
  capturedOnMutationError = undefined
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// KanbanBoard real render (unmocked) for KanbanBoard-level AC1 tests.
// Requires separate describe block with vi.unmock or a different import path.
// Use a stub fetch for move API calls.

interface KanbanBoardTestProps extends KanbanBoardProps {
  onMutationSuccess?: (message?: string) => void
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
}

// We need the REAL KanbanBoard for the KB-level tests. We restore the mock per
// test group. Since vi.mock is hoisted we use the unmocked real module inline.

// ─── Fetch helper ─────────────────────────────────────────────────────────────

function stubMoveFetchOk() {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (/\/api\/tasks\/\d+\/move/.test(url)) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              ...TASK_ONE,
              status: 'todo',
              updated: '2026-05-01T13:00:00+00:00',
            }),
          text: () => Promise.resolve(''),
        })
      }
      return new Promise<never>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      })
    }),
  )
}

function stubNeverResolvingFetch() {
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

// ─── Tests ────────────────────────────────────────────────────────────────────

// ════════════════════════════════════════════════════════════════════════════
// TestFromAC_KanbanBoardMoveMessage
// AC1: KanbanBoard calls onMutationSuccess with a string containing the target
//      status name after a successful move (drag-drop and context-menu paths).
// ════════════════════════════════════════════════════════════════════════════

describe('TestFromAC_KanbanBoardMoveMessage', () => {
  // For this group we render the real KanbanBoard, not the mock.
  // vi.mock('../KanbanBoard') is hoisted but we import KanbanBoard above and
  // the mock replaces it. We need to render the ACTUAL component.
  // Strategy: import the REAL module before the mock via a dynamic unmock workaround.
  // We use a separate import alias to access the real component internals via
  // the mock-captured factory. Instead, we test the contract via a real render
  // by temporarily re-implementing a real-like stub for this describe block.

  // Alternative: render the actual KanbanBoard by importing directly while
  // the mock intercepts the default export at the module level. To test the
  // real KanbanBoard we need to bypass the mock.
  // We achieve this by importing the real module with vi.importActual.

  let RealKanbanBoard: React.ComponentType<KanbanBoardTestProps>

  beforeAll(async () => {
    // Load the real KanbanBoard implementation (bypasses vi.mock).
    const real = await vi.importActual<{ default: React.ComponentType<KanbanBoardTestProps> }>(
      '../KanbanBoard',
    )
    RealKanbanBoard = real.default
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function renderRealBoard(
    extraProps: Pick<KanbanBoardTestProps, 'onMutationSuccess' | 'onMutationError'> = {},
  ) {
    return render(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <RealKanbanBoard
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

  async function dragCard(container: HTMLElement) {
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="task-card"][data-id="7"]'),
      ).not.toBeNull()
    })
    const card = container.querySelector('[data-testid="task-card"][data-id="7"]')!
    fireEvent.dragStart(card)
  }

  function dropOnColumn(container: HTMLElement, status: string) {
    const col = container.querySelector(`[data-column="${status}"]`)!
    fireEvent.dragOver(col)
    fireEvent.drop(col)
  }

  async function openContextMenuAndClickTransition(
    container: HTMLElement,
    targetStatus: string,
  ) {
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="task-card"][data-id="7"]'),
      ).not.toBeNull()
    })
    fireEvent.contextMenu(
      container.querySelector('[data-testid="task-card"][data-id="7"]')!,
    )
    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
    })
    const item = container.querySelector(
      `[data-testid="transition-item"][data-status="${targetStatus}"]`,
    )!
    fireEvent.click(item)
  }

  it('drag-drop move calls onMutationSuccess with string containing target status', async () => {
    stubMoveFetchOk()
    const spy = vi.fn()
    const { container } = renderRealBoard({ onMutationSuccess: spy })

    await dragCard(container)
    dropOnColumn(container, 'todo')

    // Fails RED: currently called as onMutationSuccess?.() with no arguments.
    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('todo'))
    })
  })

  it('context-menu transition calls onMutationSuccess with string containing target status', async () => {
    stubMoveFetchOk()
    const spy = vi.fn()
    const { container } = renderRealBoard({ onMutationSuccess: spy })

    await openContextMenuAndClickTransition(container, 'todo')

    // Fails RED: currently called as onMutationSuccess?.() with no arguments.
    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('todo'))
    })
  })
})

// ════════════════════════════════════════════════════════════════════════════
// TestFromAC_ShellToastFeedback
// AC1: Shell wires onMutationSuccess to useToastManager().addMessage with
//      state='success' and message text containing the target status.
// ════════════════════════════════════════════════════════════════════════════

describe('TestFromAC_ShellToastFeedback', () => {
  beforeEach(() => {
    stubHooks()
    stubNeverResolvingFetch()
    addMessage.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('Shell calls useToastManager addMessage with state=success when onMutationSuccess triggered', async () => {
    renderShell()

    await act(async () => {
      // Simulate KanbanBoard calling onMutationSuccess with a move message.
      capturedOnMutationSuccess?.('Task moved to in-progress')
    })

    // Fails RED: Shell's onMutationSuccess only calls setBannerError(null);
    // it does not call useToastManager().addMessage at all.
    expect(addMessage).toHaveBeenCalledWith(
      expect.objectContaining({ state: 'success' }),
    )
  })

  it('addMessage text contains the target status passed from KanbanBoard', async () => {
    renderShell()

    await act(async () => {
      capturedOnMutationSuccess?.('Task moved to review')
    })

    // Fails RED: addMessage never called.
    expect(addMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        state: 'success',
        text: expect.stringContaining('review'),
      }),
    )
  })

  it('addMessage is NOT called when onMutationSuccess is triggered without a message', async () => {
    // After implementation: no message = no toast (only banner-clear).
    // This test pairs with the positive tests — if addMessage fires without
    // a message it would be a false positive. Currently fails because any
    // call to addMessage at all does not happen.
    // Structure: assert addMessage called 0 times, then assert it IS called
    // when a message is provided.
    renderShell()

    await act(async () => {
      capturedOnMutationSuccess?.()   // no message
    })

    // addMessage must not fire with undefined/empty message.
    expect(addMessage).not.toHaveBeenCalled()

    // Now trigger with a message — it must fire.
    await act(async () => {
      capturedOnMutationSuccess?.('Task moved to todo')
    })

    // Fails RED: addMessage still never called.
    expect(addMessage).toHaveBeenCalledWith(
      expect.objectContaining({ state: 'success' }),
    )
  })
})

// ════════════════════════════════════════════════════════════════════════════
// TestFromAC_PToastMount
// AC1: App.tsx mounts <PToast /> inside PorscheDesignSystemProvider.
// ════════════════════════════════════════════════════════════════════════════

describe('TestFromAC_PToastMount', () => {
  beforeEach(() => {
    stubHooks()
    stubNeverResolvingFetch()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('App renders ptoast-stub element (PToast mounted inside provider)', () => {
    // KanbanBoard mock is active — Shell renders without real board logic.
    // Fails RED: App.tsx does not import or render PToast.
    const { container } = render(<App />)
    expect(container.querySelector('[data-testid="ptoast-stub"]')).not.toBeNull()
  })

  it('PToast stub is present before any mutations occur', () => {
    // PToast must be mounted at app boot — not conditionally after first success.
    // Fails RED: PToast not in App.tsx.
    const { container } = render(<App />)
    const stub = container.querySelector('[data-testid="ptoast-stub"]')
    expect(stub).not.toBeNull()
    // Confirm no success message has been dispatched yet.
    expect(addMessage).not.toHaveBeenCalled()
  })
})

// ════════════════════════════════════════════════════════════════════════════
// TestFromAC_PBannerNoRegression
// AC3: p-banner[state=error] and p-banner[state=warning] still render after
//      PToast is added. Tests confirm PBanner coexists with the PToast stub.
// ════════════════════════════════════════════════════════════════════════════

describe('TestFromAC_PBannerNoRegression', () => {
  beforeEach(() => {
    stubHooks()
    stubNeverResolvingFetch()
    addMessage.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('PToast is mounted AND p-banner[state=error] renders after mutation error', async () => {
    const { container } = renderShell()

    // PToast must already be present in DOM (AC1 prerequisite for AC3).
    // Fails RED: PToast not in Shell/App tree.
    expect(container.querySelector('[data-testid="ptoast-stub"]')).not.toBeNull()

    await act(async () => {
      capturedOnMutationError?.('Move failed', 'Server error', 'error')
    })

    const banner = container.querySelector('[data-testid="pbanner-stub"]')
    expect(banner).not.toBeNull()
    expect(banner?.getAttribute('data-state')).toBe('error')
  })

  it('PToast is mounted AND p-banner[state=warning] renders after mutation warning', async () => {
    const { container } = renderShell()

    // Fails RED: PToast not in Shell tree.
    expect(container.querySelector('[data-testid="ptoast-stub"]')).not.toBeNull()

    await act(async () => {
      capturedOnMutationError?.('Edit failed', 'Validation error', 'warning')
    })

    const banner = container.querySelector('[data-testid="pbanner-stub"]')
    expect(banner).not.toBeNull()
    expect(banner?.getAttribute('data-state')).toBe('warning')
  })

  it('both PToast addMessage and PBanner clear happen when onMutationSuccess fires after an error', async () => {
    const { container } = renderShell()

    // Set an error state first.
    await act(async () => {
      capturedOnMutationError?.('Move failed', 'Network error', 'error')
    })
    expect(container.querySelector('[data-testid="pbanner-stub"]')).not.toBeNull()

    // Move success clears banner AND triggers toast.
    await act(async () => {
      capturedOnMutationSuccess?.('Task moved to todo')
    })

    // Banner cleared (already implemented — passes now).
    await waitFor(() => {
      expect(container.querySelector('[data-testid="pbanner-stub"]')).toBeNull()
    })

    // Fails RED: addMessage not called by Shell.
    expect(addMessage).toHaveBeenCalledWith(
      expect.objectContaining({ state: 'success' }),
    )
  })
})
