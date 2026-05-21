/**
 * Task #1647 — P2-02: ResolveModal integration + modal snapshot SSE guard
 *
 * AC1: Clicking a DR list item in DecisionsPage calls setSelectedDRId with the
 *      item's id, which opens the Shell-level ResolveModal with that DR's data —
 *      same ResolveModal instance used by DRStatusIndicator
 * AC2: DR data is copied into modal-local state when ResolveModal opens; subsequent
 *      SSE-triggered useDRState() refetches do not update the data displayed in the
 *      open modal
 * AC3: Closing and reopening the modal for the same DR picks up any data changes
 *      that occurred while the modal was closed
 *
 * RED reasons:
 *   — ResolveModal has no snapshot guard. Title and body are read directly from the
 *     `dr` prop on each render:
 *       <PHeading ref={setHeadingTagAttr} tag="h2">{dr.title}</PHeading>
 *       <ReactMarkdown ...>{dr.body ?? ''}</ReactMarkdown>
 *     When the `dr` prop changes (SSE refetch → new pendingDRItems → new selectedDR),
 *     React re-renders the modal with updated data, violating AC2.
 *   — AC2 unit tests: rerender with updated dr prop → modal shows new data → FAILS
 *     (assertions expect original title/body to remain displayed).
 *   — AC1 Shell integration tests: after DecisionsPage click opens modal, a simulated
 *     SSE update (mock change + rerender) updates selectedDR → modal re-renders with
 *     new data → FAILS (assertions expect original data to remain visible).
 *   — AC3 tests: close + reopen shows updated data — passes with current code because
 *     fresh mount reads fresh prop; retained as regression guard against any
 *     implementation that shares snapshot state across mounts.
 */
import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, act, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── Module mocks (hoisted by Vitest before all imports) ──────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// Shell hook dependencies — controlled to isolate DR flow
vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))
vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: vi.fn() }))
vi.mock('../hooks/usePendingMemoryCount', () => ({
  usePendingMemoryCount: vi.fn(() => ({ count: 0, isLoading: false, error: null, refetch: vi.fn() })),
}))
vi.mock('../api/errorMessage', () => ({
  getResponseErrorMessage: vi.fn().mockResolvedValue('Task fetch failed'),
}))

// Stub Shell child components not under test
vi.mock('../KanbanBoard', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DetailTab', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ActivityTab', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/HealthBadge', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DecisionViewport', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/CleanupPanel', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DRStatusIndicator', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/RepairPanel', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ThemeToggle', () => ({ default: vi.fn(() => null) }))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import ResolveModal from '../components/ResolveModal'
import type { PendingDRWithBody } from '../components/ResolveModal'
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
  statuses: [{ name: 'todo' }],
  priorities: ['needed'],
  valid_transitions: { todo: [] },
}

// Shell-level fixtures: PendingDR items returned by usePendingDRs mock
const DR_A: PendingDR = {
  id: 'dr-a-001',
  task_id: 100,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 30 * 60_000).toISOString(),
  title: 'Original scope decision title A',
  body: '## Context\n\nOriginal body content for DR A.',
  body_preview: 'Original preview for DR A.',
}

const DR_A_UPDATED: PendingDR = {
  ...DR_A,
  title: 'SSE-updated scope decision title A',
  body: '## Context\n\nSSE-updated body content for DR A.',
}

// Unit test fixtures: PendingDRWithBody for direct ResolveModal rendering
const DR_V1: PendingDRWithBody = {
  id: 'dr-unit-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: '2026-05-01T10:00:00Z',
  title: 'V1 modal title before SSE',
  body: 'V1 modal body before SSE',
  body_preview: 'V1 preview',
}

const DR_V2: PendingDRWithBody = {
  ...DR_V1,
  title: 'V2 SSE-updated modal title',
  body: 'V2 SSE-updated modal body',
}

const DR_V3: PendingDRWithBody = {
  ...DR_V1,
  title: 'V3 third SSE update title',
  body: 'V3 third SSE update body',
}

const DR_DIFFERENT_ID: PendingDRWithBody = {
  ...DR_V1,
  id: 'dr-different-999',
  title: 'Different-id DR after SSE swap',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function stubShellHooks(pendingDRItems: PendingDR[] = []) {
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

  vi.mocked(usePendingDRs).mockReturnValue({
    count: pendingDRItems.length,
    items: pendingDRItems,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)

  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof useScanPolling>)
}

/** Returns the JSX tree for Shell at a given route (used for initial render + rerender). */
function buildShellTree(route = '/decisions') {
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

function renderModal(dr: PendingDRWithBody | null, onClose = vi.fn(), onResolved = vi.fn()) {
  return render(
    <PorscheDesignSystemProvider>
      <ResolveModal dr={dr} onClose={onClose} onResolved={onResolved} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── AC1 + AC2: TestFromAC_DecisionsPageModalIntegration ─────────────────────
//
// Shell integration tests that exercise the full flow:
//   DecisionsPage item click → setSelectedDRId → Shell renders ResolveModal
//
// The combined AC1+AC2 tests additionally simulate an SSE update (change mock +
// rerender), which updates selectedDR in CockpitProvider and passes a new `dr`
// prop to ResolveModal. Without a snapshot guard, ResolveModal re-renders with
// the new data — causing the "original data must remain" assertions to FAIL.

describe('TestFromAC_DecisionsPageModalIntegration', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('ac1+ac2 edge: modal keeps original DR title after SSE-driven pendingDRItems update', async () => {
    stubShellHooks([DR_A])
    const { container, rerender } = render(buildShellTree())

    // Wait for lazy-loaded DecisionsPage to render with DR_A's item
    await waitFor(() => {
      expect(container.querySelector('[data-testid="dr-item-dr-a-001"]')).not.toBeNull()
    })

    // Click the DR item → triggers setSelectedDRId('dr-a-001') in DecisionsPage
    await act(async () => {
      fireEvent.click(container.querySelector('[data-testid="dr-item-dr-a-001"]')!)
    })

    // AC1: Shell must have rendered ResolveModal with the DR's data
    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-modal"]')).not.toBeNull()
    })
    expect(container.textContent).toContain(DR_A.title)

    // Simulate SSE: pendingDRItems now contains DR_A_UPDATED (same id, different title)
    vi.mocked(usePendingDRs).mockReturnValue({
      count: 1,
      items: [DR_A_UPDATED],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof usePendingDRs>)

    // Trigger CockpitProvider re-render (mimics SSE-driven state update in real app)
    await act(async () => {
      rerender(buildShellTree())
    })

    // AC2: modal must NOT display the SSE-updated title — snapshot guard required.
    // The route list behind the modal may refresh; scope this contract to the modal.
    const modal = container.querySelector('[data-testid="resolve-modal"]')
    expect(modal?.textContent).not.toContain(DR_A_UPDATED.title)
    expect(modal?.textContent).toContain(DR_A.title)
  })

  it('ac1+ac2 edge: modal keeps original DR body after SSE-driven pendingDRItems update', async () => {
    stubShellHooks([DR_A])
    const { container, rerender } = render(buildShellTree())

    await waitFor(() => {
      expect(container.querySelector('[data-testid="dr-item-dr-a-001"]')).not.toBeNull()
    })

    await act(async () => {
      fireEvent.click(container.querySelector('[data-testid="dr-item-dr-a-001"]')!)
    })

    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-modal"]')).not.toBeNull()
    })

    // Simulate SSE update
    vi.mocked(usePendingDRs).mockReturnValue({
      count: 1,
      items: [DR_A_UPDATED],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as ReturnType<typeof usePendingDRs>)

    await act(async () => {
      rerender(buildShellTree())
    })

    // AC2: markdown-body must retain original body, not SSE-updated body.
    // FAILS: without snapshot, ReactMarkdown receives DR_A_UPDATED.body.
    const markdownBody = container.querySelector('[data-testid="markdown-body"]')
    expect(markdownBody).not.toBeNull()
    expect(markdownBody!.textContent).not.toContain('SSE-updated body content')
    expect(markdownBody!.textContent).toContain('Original body content for DR A')
  })
})

// ─── AC2: TestFromAC_ModalSnapshotGuard ──────────────────────────────────────
//
// Direct unit tests of ResolveModal's snapshot-guard contract. The `rerender`
// call simulates what happens when the Shell's selectedDR reference updates due
// to a SSE-triggered refetch of pendingDRItems.
//
// All assertions that expect the original data to remain FAIL because
// ResolveModal reads `dr.title` and `dr.body` directly from props — there is no
// `useState(() => dr!)` lazy initializer to capture the data at mount time.

describe('TestFromAC_ModalSnapshotGuard', () => {
  afterEach(() => {
    vi.resetAllMocks()
    vi.unstubAllGlobals()
  })

  it('ac2 edge: displayed title does not change when dr prop is updated (SSE guard)', () => {
    const { container, rerender } = renderModal(DR_V1)

    // Simulate SSE prop update: Shell receives updated selectedDR and passes new dr prop
    rerender(
      <PorscheDesignSystemProvider>
        <ResolveModal dr={DR_V2} onClose={vi.fn()} onResolved={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )

    // Must still display V1 title (snapshot guard captures at mount time).
    // FAILS: without snapshot, dr.title re-renders to DR_V2.title.
    expect(container.textContent).toContain(DR_V1.title)
    expect(container.textContent).not.toContain(DR_V2.title)
  })

  it('ac2 edge: displayed body does not change when dr prop is updated (SSE guard)', () => {
    const { container, rerender } = renderModal(DR_V1)

    rerender(
      <PorscheDesignSystemProvider>
        <ResolveModal dr={DR_V2} onClose={vi.fn()} onResolved={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )

    const markdownBody = container.querySelector('[data-testid="markdown-body"]')
    expect(markdownBody).not.toBeNull()
    // Must still display V1 body (snapshot guard).
    // FAILS: without snapshot, ReactMarkdown receives DR_V2.body.
    expect(markdownBody!.textContent).toContain(DR_V1.body)
    expect(markdownBody!.textContent).not.toContain(DR_V2.body)
  })

  it('ac2 boundary: three consecutive SSE prop updates do not change displayed title', () => {
    // Three rapid SSE events (e.g., concurrent agents updating the DR) — none
    // must overwrite the data captured at modal-open time.
    // FAILS: each rerender overwrites dr.title in the DOM (no snapshot).
    const { container, rerender } = renderModal(DR_V1)

    rerender(
      <PorscheDesignSystemProvider>
        <ResolveModal dr={DR_V2} onClose={vi.fn()} onResolved={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )
    rerender(
      <PorscheDesignSystemProvider>
        <ResolveModal dr={DR_V3} onClose={vi.fn()} onResolved={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )
    rerender(
      <PorscheDesignSystemProvider>
        <ResolveModal dr={DR_V2} onClose={vi.fn()} onResolved={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )

    // Must still show original V1 title after all three updates.
    // FAILS: shows V2.title (the last rerender's value, no snapshot).
    expect(container.textContent).toContain(DR_V1.title)
    expect(container.textContent).not.toContain(DR_V2.title)
    expect(container.textContent).not.toContain(DR_V3.title)
  })

  it('ac2 error: snapshotted id is preserved when prop is swapped to a different-id DR', () => {
    // Builder guidance: ALL dr prop reads — including resolveDR(dr.id, ...) in
    // handleSubmit — must use snapshotDR. If the prop is swapped to a DR with a
    // different id, the displayed title must still reflect the original DR.
    // FAILS: without snapshot, modal re-renders with DR_DIFFERENT_ID.title.
    const { container, rerender } = renderModal(DR_V1)

    rerender(
      <PorscheDesignSystemProvider>
        <ResolveModal dr={DR_DIFFERENT_ID} onClose={vi.fn()} onResolved={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )

    // Must still show original V1 title (captured at mount).
    // FAILS: shows DR_DIFFERENT_ID.title because no snapshot.
    expect(container.textContent).toContain(DR_V1.title)
    expect(container.textContent).not.toContain(DR_DIFFERENT_ID.title)
  })
})

// ─── AC3: TestFromAC_ReopenPicksUpChanges ────────────────────────────────────
//
// AC3 contract: closing and reopening the modal picks up data changes that
// occurred while the modal was closed. This is satisfied by the snapshot being
// per-mount (useState lazy initializer creates fresh state on each mount).
//
// NOTE: AC3 tests passed against the pre-snapshot implementation (fresh mount
// reads the fresh prop naturally). Removed per RED-phase rule: tests that pass
// test existing behavior and are not valid RED tests. The builder's snapshot
// guard (useState lazy initializer) satisfies AC3 as a structural property —
// each remount creates a new snapshot from the current prop.

describe('TestFromAC_ReopenPicksUpChanges', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('ac3 boundary: snapshot is per-mount — reopened modal does not show stale data from previous open', () => {
    // Open modal with V1, close it, reopen with V2, then simulate SSE update with V3.
    // The second open should show V2 (captured at second mount), not V1 (first mount)
    // and not V3 (post-mount SSE). This distinguishes correct per-mount snapshots from
    // incorrectly-shared state.
    // FAILS: without snapshot, the rerender with V3 updates displayed content to V3.
    const { container: c1, unmount: unmount1 } = renderModal(DR_V1)
    expect(c1.textContent).toContain(DR_V1.title)
    unmount1()

    // Second open with V2
    const { container: c2, rerender } = renderModal(DR_V2)
    expect(c2.textContent).toContain(DR_V2.title)

    // Now simulate SSE update (prop changes to V3 while modal is open the second time)
    rerender(
      <PorscheDesignSystemProvider>
        <ResolveModal dr={DR_V3} onClose={vi.fn()} onResolved={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )

    // Must still show V2 (snapshot from second mount), not V1 or V3.
    // FAILS: without snapshot, shows V3.title after the rerender.
    expect(c2.textContent).toContain(DR_V2.title)
    expect(c2.textContent).not.toContain(DR_V3.title)
    expect(c2.textContent).not.toContain(DR_V1.title)
  })
})
