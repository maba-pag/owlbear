/**
 * ResolveModal component
 *
 * Covers: markdown DR body rendering, 3-option response selector,
 * optional notes textarea, POST submit payload assertion, modal close
 * on success, error state on failure, and cancel-without-mutation guard.
 *
 * Component interface: { dr: PendingDRWithBody | null; onClose: () => void; onResolved: () => void }
 * API contract:  POST /api/decisions/{id}/resolve  body: { response, notes }
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ResolveModal from '../components/ResolveModal'

// ─── react-markdown mock ──────────────────────────────────────────────────────
// Factory mock works before the real package is installed and prevents
// JSDOM parse failures from complex markdown rendering.

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────
// DR fixture includes `body` (full text), not `body_preview`, per builder guidance.

interface PendingDRWithBody {
  id: string
  task_id: number
  agent: string
  request_type: string
  created: string
  title: string
  body_preview: string
  body: string
}

const DR_FIXTURE: PendingDRWithBody = {
  id: '42-scope-question',
  task_id: 42,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-04-30T14:30:00+02:00',
  title: 'Scope question',
  body_preview: 'Context: Should we include X?',
  body: '## Context\n\nShould we include X?\n\n## Options\n\n1. Yes\n2. No',
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderModal(
  dr: PendingDRWithBody | null = DR_FIXTURE,
  onClose = vi.fn(),
  onResolved = vi.fn(),
) {
  return render(
    <PorscheDesignSystemProvider>
      <ResolveModal dr={dr} onClose={onClose} onResolved={onResolved} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ResolveModal', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  // ─── AC1: Renders full DR body as markdown ────────────────────────────────

  describe('AC1: renders full DR body as markdown', () => {
    it('renders a markdown-body element containing the DR body text', () => {
      const { container } = renderModal()
      const el = container.querySelector('[data-testid="markdown-body"]')
      expect(el).not.toBeNull()
      // Assert content unique to full `body` — NOT present in `body_preview`
      expect(el?.textContent).toContain('## Options')
      expect(el?.textContent).toContain('1. Yes')
    })
  })

  // ─── AC2: Response selector offers approved, rejected, needs-info ─────────

  describe('AC2: response selector offers approved, rejected, needs-info', () => {
    it('renders a response-selector with all three resolution options visible', () => {
      const { container } = renderModal()
      const selector = container.querySelector('[data-testid="response-selector"]')
      expect(selector).not.toBeNull()
      const text = selector?.textContent?.toLowerCase() ?? ''
      expect(text).toContain('approve')
      expect(text).toContain('reject')
      expect(text).toContain('needs info')
    })

    it('response-selector contains exactly three options and does not include completed', () => {
      const { container } = renderModal()
      const selector = container.querySelector('[data-testid="response-selector"]')
      expect(selector).not.toBeNull()
      // Check radio inputs — completed must not appear as an option
      const radios = selector?.querySelectorAll('input[type="radio"]')
      const values = Array.from(radios ?? []).map((r) => (r as HTMLInputElement).value)
      expect(values).not.toContain('completed')
      // Selector text must not include the word 'completed' as an option label
      const text = selector?.textContent?.toLowerCase() ?? ''
      expect(text).not.toContain('completed')
      // Exactly 3 choices offered
      if (radios && radios.length > 0) {
        expect(radios).toHaveLength(3)
      }
    })
  })

  describe('AC2b: decision metadata hierarchy', () => {
    it('moves agent out of the modal header and into decision metadata', () => {
      const { container } = renderModal()
      const headerMeta = container.querySelector('[data-testid="resolve-header-meta"]')
      const metadata = container.querySelector('[data-testid="resolve-decision-metadata"]')

      expect(headerMeta).not.toBeNull()
      expect(headerMeta?.textContent).toContain('Task #42')
      expect(headerMeta?.textContent).toContain('Decision')
      expect(headerMeta?.textContent).not.toContain(DR_FIXTURE.agent)

      expect(metadata).not.toBeNull()
      expect(metadata?.className).toContain('border')
      expect(metadata?.textContent).toContain('Metadata')
      expect(metadata?.querySelector('dl')?.className).toContain('text-sm')
      expect(metadata?.querySelector('dl')?.className).not.toContain('border-t')
      expect(container.querySelector('[data-testid="resolve-metadata-agent"]')?.textContent).toContain(DR_FIXTURE.agent)
      expect(container.querySelector('[data-testid="resolve-metadata-source"]')?.textContent).toContain(DR_FIXTURE.id)
      expect(container.querySelector('[data-testid="resolve-metadata-created"]')?.textContent).toContain(DR_FIXTURE.created)
    })
  })

  // ─── AC3: Optional notes textarea accepts freeform markdown ──────────────

  describe('AC3: optional notes textarea accepts freeform markdown', () => {
    it('renders an initially-empty notes textarea', () => {
      const { container } = renderModal()
      const notes = container.querySelector('[data-testid="resolve-notes"]') as HTMLTextAreaElement | null
      expect(notes).not.toBeNull()
      expect(notes?.value).toBe('')
    })
  })

  // ─── AC4: Submit calls POST /api/decisions/{id}/resolve with payload ──────

  describe('AC4: submit calls POST /api/decisions/{id}/resolve with response + notes', () => {
    it('clicking submit sends POST to /api/decisions/{id}/resolve with response and notes in the body', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderModal()

      // Select a NON-default response option to prove the selected value is transmitted
      const radio = container.querySelector(
        '[data-testid="response-selector"] input[value="rejected"]',
      ) as HTMLInputElement | null
      const selectEl = container.querySelector(
        '[data-testid="response-selector"] select',
      ) as HTMLSelectElement | null
      if (radio) {
        fireEvent.click(radio)
      } else if (selectEl) {
        fireEvent.change(selectEl, { target: { value: 'rejected' } })
      }

      // Enter notes
      const notes = container.querySelector('[data-testid="resolve-notes"]') as HTMLTextAreaElement | null
      expect(notes).not.toBeNull()
      fireEvent.change(notes!, { target: { value: 'Looks good to me.' } })

      const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement | null
      expect(submitBtn).not.toBeNull()
      fireEvent.click(submitBtn!)

      await waitFor(
        () => {
          expect(fetchMock).toHaveBeenCalledWith(
            expect.stringContaining('/api/decisions/42-scope-question/resolve'),
            expect.objectContaining({ method: 'POST' }),
          )
          const [, opts] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const payload = JSON.parse(opts.body as string) as Record<string, unknown>
          // Exact value proof — hardcoding 'approved' (default) would fail this assertion
          expect(payload.response).toBe('rejected')
          expect(payload).toHaveProperty('notes', 'Looks good to me.')
        },
        { timeout: 500 },
      )
    })
  })

  // ─── AC5: Modal closes on successful submission ───────────────────────────

  describe('AC5: modal closes on successful submission', () => {
    it('calls onResolved and onClose after a successful POST', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })),
      )
      const onClose = vi.fn()
      const onResolved = vi.fn()
      const { container } = renderModal(DR_FIXTURE, onClose, onResolved)

      const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement | null
      expect(submitBtn).not.toBeNull()
      fireEvent.click(submitBtn!)

      await waitFor(
        () => {
          expect(onResolved).toHaveBeenCalledOnce()
          expect(onClose).toHaveBeenCalledOnce()
        },
        { timeout: 500 },
      )
    })
  })

  // ─── AC6: Error state shown on failed submission ──────────────────────────

  describe('AC6: error state shown on failed submission', () => {
    it('renders a resolve-error element when fetch throws a network error (catch branch)', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.reject(new Error('Network error'))),
      )
      const { container } = renderModal()

      const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement | null
      expect(submitBtn).not.toBeNull()
      fireEvent.click(submitBtn!)

      await waitFor(
        () => {
          expect(
            container.querySelector('p-inline-notification[data-testid="resolve-error"]'),
          ).not.toBeNull()
        },
        { timeout: 500 },
      )
    })

    it('renders a resolve-error element when the POST response is not ok', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }),
        ),
      )
      const { container } = renderModal()

      const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement | null
      expect(submitBtn).not.toBeNull()
      fireEvent.click(submitBtn!)

      await waitFor(
        () => {
          expect(
            container.querySelector('p-inline-notification[data-testid="resolve-error"]'),
          ).not.toBeNull()
        },
        { timeout: 500 },
      )
    })
  })

  // ─── AC7: Cancel/close without submitting does not mutate ────────────────

  describe('AC7: cancel/close without submitting does not mutate', () => {
    it('clicking cancel calls onClose and does NOT call fetch', () => {
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)
      const onClose = vi.fn()
      const { container } = renderModal(DR_FIXTURE, onClose)

      const cancelBtn = container.querySelector('[data-testid="resolve-cancel"]') as HTMLElement | null
      expect(cancelBtn).not.toBeNull()
      fireEvent.click(cancelBtn!)

      expect(onClose).toHaveBeenCalledOnce()
      expect(fetchMock).not.toHaveBeenCalled()
    })
  })
})
