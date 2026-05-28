/**
 * Cockpit decision data contract and error-surface regression tests.
 *
 * Covers body-field flow into ResolveModal, required decision fields on the
 * Decisions route, and pending-request polling errors surfaced by Shell.
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

// ─── Helpers ──────────────────────────────────────────────────────────────────

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

// ─── Body field data contract and DR polling error chain ─────────────────────

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

  // AC2: required decision fields flow into the Decisions route; agent attribution
  // is rendered in the primary list row per AC1 structured-field contract.
  it('hook output items render required fields on the Decisions route', async () => {
    const drWithAllFields: PendingDR & { body: string } = {
      id: 'dr-all-fields',
      task_id: 202,
      agent: 'builder',
      kind: 'decision',
      request_type: 'decision',
      created: '2026-05-08T10:00:00Z',
      title: 'Scope boundary decision',
      summary: 'Builder requests scope clarification...',
      options: [],
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
    expect(item.querySelector('[data-testid="dr-primary-meta-dr-all-fields"]')?.textContent).toContain('builder')
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
