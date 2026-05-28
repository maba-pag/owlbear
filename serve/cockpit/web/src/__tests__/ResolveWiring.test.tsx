/**
 * Task #1857 — P1-07: Cockpit frontend — minimal resolver wiring to new API
 *
 * Smoke tests (one per AC line):
 *   AC1: usePendingDRs (or replacement) fetches from GET /api/requests/pending
 *        (bare JSON array of PendingRequestResponse objects, NOT old
 *        /api/decisions/pending); modal renders title and summary from structured
 *        response fields — does NOT derive them via getDecisionBrief() body-text parsing.
 *   AC2: Resolve submission calls POST /api/requests/{request_id}/resolve with JSON body
 *        {selected_option_id, free_text, kind}; for decision-kind, selected_option_id
 *        is the chosen options[].option_id; on HTTP 200, modal closes (onResolved fired).
 *   AC3: kind==="decision" renders options[].label as selectable controls;
 *        kind==="action" renders a "Complete" button replacing option controls.
 *
 * RED reasons (current failures against existing implementation):
 *   AC1: usePendingDRs polls /api/decisions/pending — assertion on /api/requests/pending fails.
 *   AC2: No option selection controls exist; POST goes to /api/decisions/{id}/resolve with
 *        {response, notes}, not the new payload shape.
 *   AC3: Modal renders approve/reject/needs-info radios, not options[].label selectable
 *        controls; submit button text is "Submit Decision", not "Complete" for action kind.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { renderHook, act, render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import { usePendingDRs } from '../hooks/usePendingDRs'
import ResolveModal from '../components/ResolveModal'

// ─── react-markdown mock ──────────────────────────────────────────────────────
// Prevents JSDOM parse failures; existing tests use this same stub.

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── New response shape from GET /api/requests/pending (introduced in #1856) ─

interface PendingRequestResponse {
  id: string
  task_id: number
  agent: string
  request_type: string
  created: string
  title: string
  summary: string
  kind: 'decision' | 'action'
  options: { option_id: string; label: string }[]
  body: string
  body_preview: string
}

const DR_DECISION: PendingRequestResponse = {
  id: 'req-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-05-25T10:00:00Z',
  title: 'Approve feature X?',
  summary: 'Should we proceed with feature X implementation?',
  kind: 'decision',
  options: [
    { option_id: 'opt-a', label: 'Option A — proceed now' },
    { option_id: 'opt-b', label: 'Option B — defer to Q3' },
  ],
  body: '',
  body_preview: '',
}

const DR_ACTION: PendingRequestResponse = {
  id: 'req-002',
  task_id: 43,
  agent: 'builder',
  request_type: 'action',
  created: '2026-05-25T10:00:00Z',
  title: 'Run the migration',
  summary: 'Execute the pending database migration script.',
  kind: 'action',
  options: [],
  body: '',
  body_preview: '',
}

// ─── Render helper ────────────────────────────────────────────────────────────
// `as any` cast: builder will update ResolveModal props to accept the new
// PendingRequestResponse shape; until then the cast allows DOM assertions to
// run against current rendering and fail on missing new controls.

function renderModal(
  dr: PendingRequestResponse,
  onClose = vi.fn(),
  onResolved = vi.fn(),
) {
  return render(
    <PorscheDesignSystemProvider>
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      <ResolveModal dr={dr as any} onClose={onClose} onResolved={onResolved} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('ResolveWiring', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  // ─── AC1: Hook fetches GET /api/requests/pending ────────────────────────

  describe('AC1: hook endpoint', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })
    afterEach(() => {
      vi.useRealTimers()
    })

    it('smoke: usePendingDRs fetches from GET /api/requests/pending (not /api/decisions/pending)', async () => {
      // RED: current hook polls /api/decisions/pending — this assertion fails on wrong URL.
      const fetchMock = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve([]),
        }),
      )
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePendingDRs())
      await act(async () => {})

      // FAILS: fetchMock is called with '/api/decisions/pending', not '/api/requests/pending'.
      expect(fetchMock).toHaveBeenCalledWith('/api/requests/pending', expect.anything())
    })
  })

  // ─── AC2: Resolve submit calls POST /api/requests/{id}/resolve ───────────

  it('smoke: resolve submit sends selected_option_id and kind to POST /api/requests/{id}/resolve', async () => {
    // RED: (1) no option selection controls exist; (2) POST goes to /api/decisions/{id}/resolve
    // with {response, notes} — neither the endpoint nor the body shape match the new contract.
    const fetchMock = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: DR_DECISION.id }),
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const onResolved = vi.fn()
    const { container } = renderModal(DR_DECISION, vi.fn(), onResolved)

    // Builder must render one selectable control per options[] entry, identified by
    // data-testid="resolve-option-{option_id}".
    const firstOptionControl = container.querySelector(
      `[data-testid="resolve-option-${DR_DECISION.options[0].option_id}"]`,
    )
    // FAILS: current modal renders approve/reject/needs-info radios, not per-option controls.
    expect(firstOptionControl).not.toBeNull()

    fireEvent.click(firstOptionControl!)
    fireEvent.click(container.querySelector('[data-testid="resolve-submit"]') as HTMLElement)

    await waitFor(() => {
      // Endpoint must be the new /api/requests/ path.
      const resolveCall = fetchMock.mock.calls.find((c) =>
        String(c[0]).includes('/resolve'),
      )
      expect(String(resolveCall?.[0])).toContain('/api/requests/')

      // Body must include selected_option_id and kind (new payload shape).
      const body = JSON.parse((resolveCall?.[1] as RequestInit).body as string) as Record<string, unknown>
      expect(body).toMatchObject({
        selected_option_id: DR_DECISION.options[0].option_id,
        kind: 'decision',
      })

      // Modal must close on 200 (onResolved fired).
      expect(onResolved).toHaveBeenCalled()
    })
  })

  // ─── AC3: Decision kind → option labels; action kind → Complete button ────

  it('smoke: decision kind renders options[].label as selectable controls; action kind renders Complete button', () => {
    // Decision kind: modal must render each options[].label as a selectable control
    // identifiable by data-testid^="resolve-option-".
    {
      const { container, unmount } = renderModal(DR_DECISION)
      const optionControls = container.querySelectorAll('[data-testid^="resolve-option-"]')
      // FAILS: current modal renders approve/reject/needs-info radios, not option controls.
      expect(optionControls.length).toBeGreaterThan(0)

      // At least one option label from the fixture must be visible.
      const text = container.textContent ?? ''
      expect(text).toContain(DR_DECISION.options[0].label)

      unmount()
    }

    // Action kind: a "Complete" button must replace option controls.
    {
      const { container } = renderModal(DR_ACTION)
      const completeBtn = Array.from(
        container.querySelectorAll<HTMLElement>('[data-testid="resolve-submit"]'),
      ).find((el) => el.textContent?.includes('Complete'))
      // FAILS: current submit button text is "Submit Decision", not "Complete".
      expect(completeBtn).toBeDefined()
    }
  })

  // ─── Retry-AC1: normalization of bare-array PendingRequestResponse ────────
  // Proves that the hook correctly maps request_id→id and created_at→created
  // from the real backend bare-array shape (PendingRequestResponse with request_id).

  describe('retry-AC1: bare-array PendingRequestResponse normalization', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })
    afterEach(() => {
      vi.useRealTimers()
    })

    it('hook normalizes request_id→id and created_at→created from bare-array backend fixture', async () => {
      const rawItem = {
        request_id: 'req-normalize-001',
        task_id: 42,
        kind: 'decision' as const,
        title: 'Approve approach B?',
        summary: 'Should we proceed with approach B?',
        agent: 'builder',
        created_at: '2026-05-25T10:00:00Z',
        options: [
          { option_id: 'opt-a', label: 'Yes, proceed', confidence: 0.9, recommended: true, rationale: '' },
        ],
        body: 'Full detail text here.',
      }
      const fetchMock = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve([rawItem]),
        }),
      )
      vi.stubGlobal('fetch', fetchMock)

      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})

      expect(result.current.items).toHaveLength(1)
      const item = result.current.items[0]
      // request_id maps to id
      expect(item.id).toBe('req-normalize-001')
      // created_at maps to created
      expect(item.created).toBe('2026-05-25T10:00:00Z')
      // other fields preserved
      expect(item.title).toBe('Approve approach B?')
      expect(item.summary).toBe('Should we proceed with approach B?')
      expect(item.kind).toBe('decision')
    })
  })

  // ─── Retry-AC2: action-kind submit ────────────────────────────────────────
  // Proves POST /api/requests/{id}/resolve is called with kind:"action" and
  // selected_option_id:null when the user clicks "Complete" on an action request.

  it('retry-AC2: action kind Complete button submits POST /api/requests/{id}/resolve with kind:action and selected_option_id:null', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ request_id: DR_ACTION.id }),
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const onResolved = vi.fn()
    const { container } = renderModal(DR_ACTION, vi.fn(), onResolved)

    // Action kind: "Complete" button must be rendered and enabled (no option selection needed)
    const completeBtn = Array.from(
      container.querySelectorAll<HTMLElement>('[data-testid="resolve-submit"]'),
    ).find((el) => el.textContent?.includes('Complete'))
    expect(completeBtn).toBeDefined()

    fireEvent.click(completeBtn!)

    await waitFor(() => {
      const resolveCall = fetchMock.mock.calls.find((c) =>
        String(c[0]).includes('/resolve'),
      )
      expect(String(resolveCall?.[0])).toContain('/api/requests/')
      const body = JSON.parse((resolveCall?.[1] as RequestInit).body as string) as Record<string, unknown>
      expect(body).toMatchObject({
        selected_option_id: null,
        kind: 'action',
      })
      expect(onResolved).toHaveBeenCalled()
    })
  })

  // ─── Retry-AC1b: summary DOM disambiguator (summary ≠ body_preview) ───────
  // Proves [data-testid="resolve-request-summary"] renders the structured
  // `summary` field from the API response, NOT `body_preview`, when the two
  // values differ. A regression that swaps the modal back to body_preview would
  // fail this assertion.

  it('retry-AC1b: modal renders structured summary field — not body_preview — inside [data-testid="resolve-request-summary"]', () => {
    const drWithDistinctSummary: PendingRequestResponse = {
      ...DR_DECISION,
      id: 'req-summary-test',
      summary: 'Structured summary from API response',
      body_preview: 'Body preview text — must NOT appear as summary',
    }

    const { container } = renderModal(drWithDistinctSummary)

    const summarySection = container.querySelector('[data-testid="resolve-request-summary"]')
    expect(summarySection).not.toBeNull()

    const summaryText = summarySection!.textContent ?? ''
    // Must render the structured summary field from the API response
    expect(summaryText).toContain('Structured summary from API response')
    // Must NOT fall back to body_preview when summary is present
    expect(summaryText).not.toContain('Body preview text — must NOT appear as summary')
  })
})
