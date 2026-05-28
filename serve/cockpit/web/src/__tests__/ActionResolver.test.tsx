/**
 * Task #1859 — P2-02: Action resolver UI with Complete button (behavioral)
 *
 * AC1: When the resolver opens for a request with kind==='action':
 *   (a) the request's markdown body is rendered as directly visible content
 *       inside [data-testid='resolve-action-body'] (NOT inside a collapsed
 *       <details> element);
 *   (b) title appears in the modal heading;
 *   (c) summary is visible in [data-testid='resolve-request-summary'];
 *   (d) no option cards ([data-testid^='resolve-option-']) are present;
 *   (e) the 'Complete' button ([data-testid='resolve-submit']) is enabled
 *       without requiring user input.
 *
 * AC2: Clicking 'Complete' calls POST /api/requests/{id}/resolve with body
 *   {selected_option_id: null, free_text: null, kind: 'action'}.
 *   When the free_text textarea ([data-testid='resolve-notes']) contains text
 *   before clicking, that trimmed value is sent as free_text instead of null.
 *
 * AC3: After the resolve POST returns HTTP 200, the resolved action's entry
 *   disappears from the rendered pending-request list without a full page
 *   navigation (onResolved refetch removes it from state).
 *
 * RED reasons (current failures):
 *   AC1(a): [data-testid='resolve-action-body'] does not exist in ResolveModal.
 *           Body is placed inside <details data-testid="resolve-full-request">
 *           for ALL request kinds — not directly visible for action kind.
 *   AC1(b-e): Partially implemented — included as compound assertion guards but
 *             behaviour may already be present.
 *   AC2: Payload shape already wired; free_text trimming already implemented —
 *        included as explicit behavioural assertions.
 *   AC3: Shell onResolved wiring already calls refetchPendingDRs; integration
 *        test verifies item removal from rendered list end-to-end.
 */
import { describe, it, expect, vi, afterEach, beforeEach, beforeAll } from 'vitest'
import { render, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── react-markdown mock ──────────────────────────────────────────────────────
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Module mocks for integration tests (AC3) ────────────────────────────────
vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))
vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: vi.fn() }))
vi.mock('../hooks/usePendingMemoryCount', () => ({
  usePendingMemoryCount: vi.fn(() => ({ count: 0 })),
}))
vi.mock('../api/errorMessage', () => ({
  getResponseErrorMessage: vi.fn().mockResolvedValue('Fetch failed'),
}))

// Stub Shell child components not under test
vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => <div data-testid="kanban-board-stub" />),
}))
vi.mock('../components/DetailTab', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ActivityTab', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/HealthBadge', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DecisionViewport', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/CleanupPanel', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/RepairPanel', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ThemeToggle', () => ({ default: vi.fn(() => null) }))

// ─── Imports (after mocks) ────────────────────────────────────────────────────
import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import ResolveModal from '../components/ResolveModal'
import type { Board } from '../hooks/useBoard'

// ─── PDS web-component workaround ────────────────────────────────────────────
beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const DR_ACTION: PendingDR = {
  id: 'req-action-1859',
  task_id: 99,
  agent: 'builder',
  request_type: 'action',
  created: '2026-05-25T12:00:00Z',
  title: 'Run the migration script',
  summary: 'Execute the pending database migration.',
  kind: 'action',
  options: [],
  body: '## Context\n\nThe migration script must be executed before deployment.\n\n## Steps\n\n1. Back up database\n2. Run migration',
  body_preview: 'Execute the pending database migration.',
}

const DR_DECISION: PendingDR = {
  id: 'req-decision-1859',
  task_id: 100,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-05-25T12:00:00Z',
  title: 'Choose approach A or B?',
  summary: 'Which approach should we adopt?',
  kind: 'decision',
  options: [
    { option_id: 'opt-a', label: 'Approach A — fast but risky', confidence: 0.7, recommended: true, rationale: '' },
    { option_id: 'opt-b', label: 'Approach B — safe but slow', confidence: 0.8, recommended: false, rationale: '' },
  ],
  body: '## Decision\n\nChoose approach A or B.',
  body_preview: 'Which approach should we adopt?',
}

const BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }, { name: 'done' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: { todo: ['in-progress'], 'in-progress': ['done'], done: [] },
}

// ─── Unit render helper ───────────────────────────────────────────────────────

function renderModal(
  dr: PendingDR = DR_ACTION,
  onClose = vi.fn(),
  onResolved = vi.fn(),
) {
  return render(
    <PorscheDesignSystemProvider>
      <ResolveModal dr={dr} onClose={onClose} onResolved={onResolved} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Integration helpers (AC3) ───────────────────────────────────────────────

function stubBoard() {
  const refetchTasks = vi.fn()
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

function stubPendingDRs(overrides?: Partial<ReturnType<typeof usePendingDRs>>) {
  const refetch = overrides?.refetch ?? vi.fn()
  vi.mocked(usePendingDRs).mockReturnValue({
    count: overrides?.items?.length ?? 0,
    items: [],
    isLoading: false,
    error: null,
    refetch,
    ...overrides,
  } as ReturnType<typeof usePendingDRs>)
  return refetch
}

function stubScan() {
  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof useScanPolling>)
}

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

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('ActionResolver', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── AC1: Action kind body rendered at resolve-action-body ─────────────────

  describe('AC1: action kind renders body at resolve-action-body (not in details)', () => {
    it('ac1(a) happy: resolve-action-body element is present in the DOM for action kind', () => {
      const { container } = renderModal(DR_ACTION)
      // RED: [data-testid='resolve-action-body'] does not exist; body is inside
      // <details data-testid="resolve-full-request"> for all kinds.
      const bodyEl = container.querySelector('[data-testid="resolve-action-body"]')
      expect(bodyEl).not.toBeNull()
    })

    it('ac1(a) happy: resolve-action-body contains the DR markdown body text', () => {
      const { container } = renderModal(DR_ACTION)
      // RED: element missing; body content not accessible via this testid.
      const bodyEl = container.querySelector('[data-testid="resolve-action-body"]')
      expect(bodyEl).not.toBeNull()
      // Body must contain the request's full markdown body text (rendered via MarkdownPreview).
      // Using the mocked react-markdown, content appears as plain text in data-testid="markdown-body".
      const markdownEl = bodyEl?.querySelector('[data-testid="markdown-body"]') ?? bodyEl
      expect(markdownEl?.textContent).toContain('migration script must be executed')
    })

    it('ac1(a) edge: resolve-action-body is NOT a descendant of any <details> element', () => {
      const { container } = renderModal(DR_ACTION)
      // RED: body is currently inside <details data-testid="resolve-full-request">.
      // After fix, body must be directly visible (not inside a collapsible <details>).
      const bodyEl = container.querySelector('[data-testid="resolve-action-body"]')
      expect(bodyEl).not.toBeNull()
      // Walk ancestors — none should be a <details> element.
      let ancestor = bodyEl?.parentElement
      while (ancestor) {
        expect(ancestor.tagName.toLowerCase()).not.toBe('details')
        ancestor = ancestor.parentElement
      }
    })

    it('ac1(a) decision-nonregression: resolve-action-body absent for decision kind — action body section is action-specific', () => {
      // Decision kind must NOT get the action body section.
      // RED: passes currently (testid missing for both kinds).
      // After builder's change, still passes — body section must only render for action kind.
      const { container } = renderModal(DR_DECISION)
      const bodyEl = container.querySelector('[data-testid="resolve-action-body"]')
      expect(bodyEl).toBeNull()
    })

    it('ac1(b-e) compound: action kind shows resolve-action-body with title, summary, Complete enabled, no option cards', () => {
      // Compound assertion: all AC1 sub-items together — fails when resolve-action-body missing.
      // RED: fails at (a) assertion — [data-testid='resolve-action-body'] does not exist.
      const { container } = renderModal(DR_ACTION)

      // (a) body element must be present
      const bodyEl = container.querySelector('[data-testid="resolve-action-body"]')
      expect(bodyEl).not.toBeNull()

      // (b) title visible in modal surface heading
      const surface = container.querySelector('[data-testid="resolve-modal-surface"]')
      expect(surface?.textContent).toContain(DR_ACTION.title)

      // (c) summary visible
      const summarySection = container.querySelector('[data-testid="resolve-request-summary"]')
      expect(summarySection).not.toBeNull()
      expect(summarySection?.textContent).toContain(DR_ACTION.summary)

      // (d) no option cards
      const optionCards = container.querySelectorAll('[data-testid^="resolve-option-"]')
      expect(optionCards.length).toBe(0)

      // (e) Complete button enabled
      const submitBtn = container.querySelector('[data-testid="resolve-submit"]')
      expect(submitBtn).not.toBeNull()
      expect(submitBtn?.textContent).toContain('Complete')
      expect(submitBtn?.hasAttribute('disabled')).toBe(false)
    })
  })

  // ─── AC2: Complete button POST payload ─────────────────────────────────────

  describe('AC2: Complete button sends correct POST payload', () => {
    it('ac2 happy: in the action resolver (body visible at resolve-action-body), Complete sends {selected_option_id:null, free_text:null, kind:"action"} when textarea is empty', async () => {
      // Compound: requires resolve-action-body to be present before submission test.
      // RED: fails at resolve-action-body assertion — testid missing.
      const fetchMock = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ request_id: DR_ACTION.id }),
        }),
      )
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal(DR_ACTION)

      // Precondition: action body must be directly visible (AC1a)
      const bodyEl = container.querySelector('[data-testid="resolve-action-body"]')
      expect(bodyEl).not.toBeNull()

      const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement | null
      expect(submitBtn).not.toBeNull()
      fireEvent.click(submitBtn!)

      await waitFor(() => {
        const resolveCall = fetchMock.mock.calls.find((c) =>
          String(c[0]).includes('/resolve'),
        )
        expect(resolveCall).toBeDefined()
        expect(String(resolveCall![0])).toBe(`/api/requests/${DR_ACTION.id}/resolve`)

        const body = JSON.parse(
          (resolveCall![1] as RequestInit).body as string,
        ) as Record<string, unknown>
        // Exact payload shape required by AC2.
        expect(body.selected_option_id).toBeNull()
        expect(body.free_text).toBeNull()
        expect(body.kind).toBe('action')
      })
    })

    it('ac2 edge: free_text sends trimmed value when textarea contains whitespace-padded text', async () => {
      // Compound: requires resolve-action-body to be present before interaction test.
      // RED: fails at resolve-action-body assertion — testid missing.
      const fetchMock = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ request_id: DR_ACTION.id }),
        }),
      )
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal(DR_ACTION)

      // Precondition: action body must be directly visible (AC1a)
      const bodyEl = container.querySelector('[data-testid="resolve-action-body"]')
      expect(bodyEl).not.toBeNull()

      // Enter notes via PDS CustomEvent detail.value path (p-textarea web component contract).
      const notesEl = container.querySelector('[data-testid="resolve-notes"]') as HTMLElement | null
      expect(notesEl).not.toBeNull()
      fireEvent(
        notesEl!,
        new CustomEvent('change', { detail: { value: '  migration complete  ' }, bubbles: true }),
      )

      const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement | null
      expect(submitBtn).not.toBeNull()
      fireEvent.click(submitBtn!)

      await waitFor(() => {
        const resolveCall = fetchMock.mock.calls.find((c) =>
          String(c[0]).includes('/resolve'),
        )
        expect(resolveCall).toBeDefined()
        const body = JSON.parse(
          (resolveCall![1] as RequestInit).body as string,
        ) as Record<string, unknown>
        // Trimmed value must be sent, not null.
        expect(body.free_text).toBe('migration complete')
        expect(body.kind).toBe('action')
        expect(body.selected_option_id).toBeNull()
      })
    })
  })

  // ─── AC3: Resolved action disappears from pending list ─────────────────────

  describe('AC3: resolved action entry removed from list after HTTP 200', () => {
    beforeEach(() => {
      // Stub fetch for task detail (used by Shell internally)
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
      stubBoard()
      stubScan()
    })

    it('ac3 integration: resolved action card [dr-item-{id}] removed from list; resolve-action-body visible before submit', async () => {
      // Compound: opens the resolver, verifies resolve-action-body is present (AC1a)
      // before submitting, then verifies the item disappears from the list (AC3).
      // RED: fails when ResolveModal renders without [data-testid='resolve-action-body'].
      const refetch = vi.fn()
      stubPendingDRs({ items: [DR_ACTION], count: 1, refetch })

      const { container, rerender } = render(buildShellTree('/decisions'))

      // The action item must appear as a list card in DecisionsPage.
      await waitFor(() => {
        expect(
          container.querySelector(`[data-testid="dr-item-${DR_ACTION.id}"]`),
        ).not.toBeNull()
      })

      // Open the resolver by clicking the item card.
      fireEvent.click(
        container.querySelector(`[data-testid="dr-item-${DR_ACTION.id}"]`) as HTMLElement,
      )

      // Wait for the ResolveModal to appear.
      await waitFor(() => {
        expect(container.querySelector('[data-testid="resolve-submit"]')).not.toBeNull()
      })

      // AC1a precondition: resolve-action-body must be directly visible (not in <details>).
      // RED: this assertion fails — [data-testid='resolve-action-body'] does not exist.
      const bodyEl = container.querySelector('[data-testid="resolve-action-body"]')
      expect(bodyEl).not.toBeNull()

      // Stub fetch to return HTTP 200 for the POST /api/requests/{id}/resolve call.
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ request_id: DR_ACTION.id }),
          }),
        ),
      )

      // Click Complete in the resolver modal.
      fireEvent.click(
        container.querySelector('[data-testid="resolve-submit"]') as HTMLElement,
      )

      // After POST 200, onResolved fires → refetchPendingDRs called.
      await waitFor(() => {
        expect(refetch).toHaveBeenCalled()
      })

      // Update the mock to reflect the state after refetch (item removed by backend).
      stubPendingDRs({ items: [], count: 0, refetch })
      await act(async () => {
        rerender(buildShellTree('/decisions'))
      })

      // The resolved action's card must no longer appear in the list.
      expect(
        container.querySelector(`[data-testid="dr-item-${DR_ACTION.id}"]`),
      ).toBeNull()
    })
  })
})
