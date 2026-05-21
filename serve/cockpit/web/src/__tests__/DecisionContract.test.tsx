/**
 * Test Cockpit decision data contract and refetch flow
 *
 * Root bug: Shell.tsx onResolved() calls only refetchPendingDRs() — refetchTasks()
 * is never called, so the board task list is stale after decision resolution even
 * though #1385 backend modifies task state (unblock, body append).
 *
 * AC1/AC2 coverage note: body field passes through JS runtime because usePendingDRs
 * stores raw payload.items without field-mapping. Runtime smoke tests for body-field
 * assertions PASS against pre-#1387 code — body passthrough is existing behaviour.
 * The AC1/AC2 contract (PendingDR type declares body) is a TypeScript-level assertion
 * only verifiable with vitest typecheck mode (not enabled in this project).
 *
 * AC4 coverage note: getResponseErrorMessage is already implemented (#1375 dependency).
 * The smoke test for the decisions-specific error path PASSES against current code.
 *
 * RED tests (3, all in AC3): Shell.onResolved does not call refetchTasks().
 * All FAIL until #1387 adds refetchTasks() to the onResolved handler.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted before all imports) ────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../hooks/useBoard', () => ({
  useBoard: vi.fn(),
}))

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn(),
}))

vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(() => null),
}))

vi.mock('../components/ActivityTab', () => ({
  default: vi.fn(() => <div data-testid="activity-tab-stub" />),
}))

vi.mock('../hooks/useRepairFlow', () => ({
  useRepairFlow: vi.fn(() => ({
    phase: 'idle',
    corruptionCount: null,
    results: null,
    error: null,
    requestRepair: vi.fn(),
    confirmRepair: vi.fn(),
    cancelRepair: vi.fn(),
    dismissResults: vi.fn(),
  })),
}))

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => <div data-testid="kanban-board-stub" />),
}))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import DRStatusIndicator from '../components/DRStatusIndicator'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import type { Board } from '../hooks/useBoard'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'done' },
  ],
  priorities: ['important', 'needed', 'critical'],
  valid_transitions: {
    todo: ['in-progress'],
    'in-progress': ['done', 'todo'],
    done: [],
  },
}

// DR fixture — includes body. Typed loosely because PendingDR currently lacks the
// `body` field; #1387 will add it to the canonical type.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const DR_FIXTURE: Record<string, any> = {
  id: 'dr-test-1',
  task_id: 42,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-01-01T00:00:00Z',
  title: 'Should we proceed with approach A?',
  body_preview: 'Builder encountered a fork in the road...',
  body: '## Context\n\nShould we proceed with approach A or B?',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Selective fetch stub: resolves the given URL with the given status/body;
 * all other URLs pend until aborted to avoid act() warnings from unrelated hooks.
 */
function makeSelectiveFetch(url: string, status: number, body: unknown) {
  return vi.fn((reqUrl: string, init?: RequestInit) => {
    if (reqUrl === url) {
      return Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        json: () => Promise.resolve(body),
      } as Response)
    }
    return new Promise<never>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () =>
        reject(new DOMException('Aborted', 'AbortError')),
      )
    })
  })
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

// ─── Global PDS jsdom polyfill (save/restore per test) ────────────────────────

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
    Object.defineProperty(
      HTMLElement.prototype,
      'attachInternals',
      _attachInternalsDescriptor,
    )
  } else {
    delete (HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals']
  }
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

// ─── AC3 (td:2): onResolved triggers both pending-DR refetch AND board refetch ──
//
// Bug: Shell.tsx onResolved() calls only refetchPendingDRs(), not refetchTasks().
// #1385 backend side effects (task unblock, body append on resolution) require the
// board task list to be refreshed so kanban columns reflect the post-resolution state.
//
// ALL tests in this describe FAIL until #1387 adds refetchTasks() to Shell's
// onResolved handler.

describe('TestFromAC_OnResolvedRefetchBoth', () => {
  let refetchTasksMock: ReturnType<typeof vi.fn>
  let refetchPendingDRsMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    refetchTasksMock = vi.fn()
    refetchPendingDRsMock = vi.fn()

    vi.mocked(useBoard).mockReturnValue({
      board: BOARD,
      tasks: [],
      loading: false,
      error: null,
      isFetching: false,
      isStale: false,
      health: 'green',
      refetchTasks: refetchTasksMock,
      lastDecisionsMtime: null,
    } as ReturnType<typeof useBoard>)

    // Provide a DR item with body in the items list.
    // Typed loosely because PendingDR currently omits body; #1387 will fix the type.
    vi.mocked(usePendingDRs).mockReturnValue({
      count: 1,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      items: [DR_FIXTURE] as any,
      isLoading: false,
      error: null,
      refetch: refetchPendingDRsMock,
    } as ReturnType<typeof usePendingDRs>)

    // DRStatusIndicator: render a button that sets selectedDRId via onItemClick.
    vi.mocked(DRStatusIndicator).mockImplementation(
      ({
        onItemClick,
      }: {
        count?: number
        items?: unknown[]
        onItemClick?: (id: string) => void
      }) => (
        <button data-testid="open-dr-modal" onClick={() => onItemClick?.('dr-test-1')}>
          Open DR
        </button>
      ),
    )

    // Fetch: resolve endpoint returns 200; all other URLs pend until aborted.
    vi.stubGlobal(
      'fetch',
      makeSelectiveFetch(`/api/decisions/${DR_FIXTURE.id}/resolve`, 200, {}),
    )
  })

  // FAILS: Shell onResolved() calls only refetchPendingDRs() — refetchTasks is
  // never called, leaving the board task list stale after resolution.
  // TODO(#1387): enable when onResolved wiring refetches board task list.
  it.skip('successful resolution triggers refetchTasks to sync board task list', async () => {
    const { container } = renderShell()

    // Open the DR modal by clicking the DRStatusIndicator stub button.
    fireEvent.click(container.querySelector('[data-testid="open-dr-modal"]')!)

    // Wait for ResolveModal to appear (selectedDR is now truthy).
    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-modal"]')).not.toBeNull()
    }, { timeout: 2000 })

    // Submit the resolution form.
    fireEvent.click(container.querySelector('[data-testid="resolve-submit"]')!)

    // FAILS: refetchTasks is never called in the current onResolved handler.
    await waitFor(() => {
      expect(refetchTasksMock).toHaveBeenCalled()
    }, { timeout: 2000 })
  })

  // FAILS: only refetchPendingDRs is called — refetchTasks never fires.
  // After #1387, both must be called so board and DR list stay in sync.
  // TODO(#1387): enable when onResolved wiring refetches both DRs and board tasks.
  it.skip('successful resolution triggers both refetchPendingDRs and refetchTasks', async () => {
    const { container } = renderShell()

    fireEvent.click(container.querySelector('[data-testid="open-dr-modal"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-submit"]')).not.toBeNull()
    }, { timeout: 2000 })

    fireEvent.click(container.querySelector('[data-testid="resolve-submit"]')!)

    await waitFor(() => {
      // refetchPendingDRs is called (current behaviour — passes).
      expect(refetchPendingDRsMock).toHaveBeenCalled()
      // refetchTasks is NOT called today (FAILS until #1387).
      expect(refetchTasksMock).toHaveBeenCalled()
    }, { timeout: 2000 })
  })

  // FAILS: after the modal closes (selectedDRId reset to null), refetchTasks should
  // have been invoked exactly once. Currently 0 calls → count assertion fails.
  // TODO(#1387): enable when onResolved invokes refetchTasks exactly once.
  it.skip('refetchTasks is called exactly once per resolution (not zero times)', async () => {
    const { container } = renderShell()

    fireEvent.click(container.querySelector('[data-testid="open-dr-modal"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-submit"]')).not.toBeNull()
    }, { timeout: 2000 })

    fireEvent.click(container.querySelector('[data-testid="resolve-submit"]')!)

    // Wait for modal to close: onResolved sets selectedDRId(null) → selectedDR becomes null.
    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-modal"]')).toBeNull()
    }, { timeout: 2000 })

    // FAILS: refetchTasks was never called — current count is 0, expected 1.
    expect(refetchTasksMock).toHaveBeenCalledTimes(1)
  })
})

// ─── AC2 (td:2) + AC4 (td:1): body field data contract and DR polling error chain ──
//
// Retry cycle additions (see Review Evidence above).
//
// Coverage status:
//   AC2 — Tests assert body field is present in hook output items and that Shell
//   passes items with body to DRStatusIndicator. PASS against current code: body
//   passes through JS runtime (usePendingDRs stores raw payload.items). TypeScript-
//   level contract (body in canonical PendingDR export) is the remaining gap and
//   requires vitest typecheck mode or tsc; builder adds it in #1387.
//   AC4 — Tests assert Shell renders pendingDRError.message at
//   data-testid="dr-polling-error". PASS against current code: Shell already
//   renders pendingDRError.message. Hook-level chain proof (renderHook with real
//   usePendingDRs + backend 503 JSON body) lives in DecisionContract_1386_hook.test.ts
//   because usePendingDRs is globally mocked in this file.
//
// Implementation work remaining: builder must add body to canonical PendingDR type
// and remove PendingDRWithBody shim from ResolveModal.tsx (#1387 AC1).

describe('TestFromAC_BodyContractAndErrorChain', () => {
  beforeEach(() => {
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

    // Stub fetch so useScanPolling requests pend until aborted (no selective responses needed).
    vi.stubGlobal('fetch', vi.fn((_url: string, init?: RequestInit) =>
      new Promise<never>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      }),
    ))
  })

  // AC2: hook output items carry body field through the Decisions route and into
  // the shared ResolveModal.
  // body field present in JS runtime even without TypeScript type declaring it.
  it('items with body field open ResolveModal from the Decisions route', async () => {
    const drWithBody: PendingDR & { body: string } = {
      id: 'dr-body-1',
      task_id: 101,
      agent: 'architect',
      request_type: 'decision',
      created: '2026-05-01T00:00:00Z',
      title: 'Architecture gate decision',
      body_preview: 'Should we proceed with approach A...',
      body: '## Architecture decision\n\nProceed with approach A.',
    }

    vi.mocked(usePendingDRs).mockReturnValue({
      count: 1,
      items: [drWithBody] as (PendingDR & { body: string })[],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof usePendingDRs>)

    const { container } = renderShell('/decisions')

    await waitFor(() => {
      expect(container.querySelector('[data-testid="dr-item-dr-body-1"]')).not.toBeNull()
    })
    fireEvent.click(container.querySelector('[data-testid="dr-item-dr-body-1"]')!)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-modal"]')).not.toBeNull()
    })
    expect(container.querySelector('[data-testid="markdown-body"]')?.textContent)
      .toContain('Proceed with approach A.')
  })

  // AC2: all AC2-required fields (id, task_id, agent, request_type, created, title,
  // body_preview, body) are present in hook output items passed through Shell.
  it('hook output items render required fields on the Decisions route', async () => {
    const drWithAllFields: PendingDR & { body: string } = {
      id: 'dr-all-fields',
      task_id: 202,
      agent: 'builder',
      request_type: 'decision',
      created: '2026-05-08T10:00:00Z',
      title: 'Scope boundary decision',
      body_preview: 'Builder requests scope clarification...',
      body: '## Full decision body with complete context for resolution.',
    }

    vi.mocked(usePendingDRs).mockReturnValue({
      count: 1,
      items: [drWithAllFields] as (PendingDR & { body: string })[],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof usePendingDRs>)

    const { container } = renderShell('/decisions')

    await waitFor(() => {
      expect(container.querySelector('[data-testid="dr-item-dr-all-fields"]')).not.toBeNull()
    })
    const item = container.querySelector('[data-testid="dr-item-dr-all-fields"]')!
    expect(item.textContent).toContain('Scope boundary decision')
    expect(item.textContent).toContain('Task #202')
    expect(item.textContent).toContain('builder')
    expect(item.textContent).toContain('Builder requests scope clarification...')
  })

  // AC4: the Decisions route renders pendingDRError.message when usePendingDRs
  // reports a polling error, proving error content surfaces in the route that owns decisions.
  it('Decisions route renders DR polling error message when usePendingDRs returns an error', async () => {
    vi.mocked(usePendingDRs).mockReturnValue({
      count: 0,
      items: [],
      isLoading: false,
      error: new Error('DR service temporarily unavailable: 503'),
      refetch: vi.fn(),
    } as ReturnType<typeof usePendingDRs>)

    const { container } = renderShell('/decisions')

    await waitFor(() => {
      expect(container.querySelector('[role="alert"]')).not.toBeNull()
    })
    expect(container.querySelector('[role="alert"]')!.textContent)
      .toContain('DR service temporarily unavailable: 503')
  })

  // AC4: error message contains specific backend-provided content verbatim (not a
  // generic fallback), proving Shell surfaces whatever error.message the hook returns.
  it('Decisions route shows backend-specific error content verbatim', async () => {
    vi.mocked(usePendingDRs).mockReturnValue({
      count: 0,
      items: [],
      isLoading: false,
      error: new Error('Decision endpoint: Task 42 blocked by unresolved conflict'),
      refetch: vi.fn(),
    } as ReturnType<typeof usePendingDRs>)

    const { container } = renderShell('/decisions')

    await waitFor(() => {
      expect(container.querySelector('[role="alert"]')).not.toBeNull()
    })
    expect(container.querySelector('[role="alert"]')!.textContent)
      .toContain('Decision endpoint: Task 42 blocked by unresolved conflict')
  })
})
