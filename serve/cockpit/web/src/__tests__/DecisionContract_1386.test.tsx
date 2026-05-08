/**
 * RED phase tests for #1386: P2-11 Test Cockpit decision data contract and refetch flow
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
import type { Board } from '../hooks/useBoard'

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

function renderShell() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <Shell />
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
  it('successful resolution triggers refetchTasks to sync board task list', async () => {
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
  it('successful resolution triggers both refetchPendingDRs and refetchTasks', async () => {
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
  it('refetchTasks is called exactly once per resolution (not zero times)', async () => {
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
