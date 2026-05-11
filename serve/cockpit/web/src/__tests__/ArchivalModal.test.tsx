/**
 * ArchivalModal component (F1 + F2)
 *
 * Covers: ARCHIVAL_REASONS constant ordering, role/aria-modal/aria-labelledby,
 * focus on open, completed-option visibility by taskStatus, refs field visibility
 * by reason, refs-clearing on reason change, submit disabled states, refs hint text,
 * non-numeric client-side error, 422/409 error display, success close+refresh,
 * focus trap (Tab/Shift+Tab), Escape-close without firing a move.
 *
 *
 * Expected component interface:
 *   { taskId: number; taskStatus: string; expectedUpdated: string;
 *     onClose: () => void; onRefresh: () => void }
 *
 * Expected exports:
 *   default ArchivalModal
 *   export const ARCHIVAL_REASONS: string[]
 *
 * Expected data-testids used in assertions:
 *   archival-submit, archival-error
 *
 * Expected submit payload: POST /api/tasks/{taskId}/move
 *   { status: "archived", updated: expectedUpdated, archival_reason: string, archival_refs: number[] }
 */
import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ArchivalModal, { ARCHIVAL_REASONS } from '../components/ArchivalModal'

// Newer jsdom versions expose a partial attachInternals that lacks setFormValue,
// causing PDS Stencil form components (p-select, p-input-text) to throw on mount.
// Unconditionally override so PDS form components render in all jsdom versions.
beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

// ─── Render helper ────────────────────────────────────────────────────────────

interface RenderOpts {
  taskId?: number
  taskStatus?: string
  expectedUpdated?: string
  onClose?: ReturnType<typeof vi.fn>
  onRefresh?: ReturnType<typeof vi.fn>
}

function renderModal({
  taskId = 42,
  taskStatus = 'in-progress',
  expectedUpdated = '2026-05-01T10:00:00+00:00',
  onClose = vi.fn(),
  onRefresh = vi.fn(),
}: RenderOpts = {}) {
  const utils = render(
    <PorscheDesignSystemProvider>
      <ArchivalModal
        taskId={taskId}
        taskStatus={taskStatus}
        expectedUpdated={expectedUpdated}
        onClose={onClose}
        onRefresh={onRefresh}
      />
    </PorscheDesignSystemProvider>,
  )
  return { ...utils, onClose, onRefresh }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getSelect(container: HTMLElement): HTMLElement {
  const el = container.querySelector('p-select') as HTMLElement | null
  if (!el) throw new Error('reason p-select not found')
  return el
}

function getRefsInput(container: HTMLElement): HTMLElement {
  const el = container.querySelector('p-input-text') as HTMLElement | null
  if (!el) throw new Error('refs p-input-text not found')
  return el
}

function getSubmitBtn(container: HTMLElement): HTMLElement {
  const el = container.querySelector('[data-testid="archival-submit"]') as HTMLElement | null
  if (!el) throw new Error('submit button not found')
  return el
}

function changeRefsInput(container: HTMLElement, value: string): void {
  fireEvent(getRefsInput(container), new CustomEvent('change', { detail: { value }, bubbles: true }))
}

function selectReason(container: HTMLElement, reason: string): void {
  fireEvent(getSelect(container), new CustomEvent('change', { detail: { value: reason }, bubbles: true }))
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ArchivalModal', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  // ─── AC1: ARCHIVAL_REASONS constant ───────────────────────────────────────

  describe('AC1: ARCHIVAL_REASONS constant exported with correct order', () => {
    it('exports ARCHIVAL_REASONS as an array of exactly 5 reasons in the specified order', () => {
      expect(ARCHIVAL_REASONS).toEqual([
        'completed',
        'dropped',
        'wontfix',
        'deprecated',
        'duplicate',
      ])
    })

    it('ARCHIVAL_REASONS starts with completed (positive resolution first)', () => {
      expect(ARCHIVAL_REASONS[0]).toBe('completed')
    })

    it('ARCHIVAL_REASONS ends with duplicate (refs-requiring reasons last)', () => {
      expect(ARCHIVAL_REASONS[ARCHIVAL_REASONS.length - 1]).toBe('duplicate')
    })
  })

  // ─── AC2: Modal accessibility attributes ──────────────────────────────────

  describe('AC2: modal renders with role="dialog", aria-modal="true", aria-labelledby', () => {
    it('renders an element with role="dialog"', () => {
      const { container } = renderModal()
      const modal = container.querySelector('[role="dialog"]')
      expect(modal).not.toBeNull()
    })

    it('the dialog element has aria-modal="true"', () => {
      const { container } = renderModal()
      const modal = container.querySelector('[role="dialog"]')
      expect(modal?.getAttribute('aria-modal')).toBe('true')
    })

    it('aria-labelledby exactly matches the id of the visible p-heading title element', () => {
      const { container } = renderModal()
      const modal = container.querySelector('[role="dialog"]')
      const labelledById = modal?.getAttribute('aria-labelledby')
      expect(labelledById).toBeTruthy()
      const titleHeading = container.querySelector('p-heading')
      expect(titleHeading).not.toBeNull()
      expect(labelledById).toBe(titleHeading?.id)
    })
  })

  // ─── AC3: Focus on reason select when modal opens ─────────────────────────

  describe('AC3: focus placed on reason select when modal opens', () => {
    it('document.activeElement is the reason p-select immediately after mount', () => {
      // PDS custom elements may not update document.activeElement in jsdom;
      // verify the component CALLS .focus() on the p-select ref instead.
      const focusCalls: HTMLElement[] = []
      const origFocus = HTMLElement.prototype.focus
      HTMLElement.prototype.focus = function (this: HTMLElement) {
        focusCalls.push(this)
        return origFocus.call(this)
      }
      try {
        const { container } = renderModal()
        const pSelect = container.querySelector('p-select') as HTMLElement | null
        expect(pSelect).not.toBeNull()
        // Component calls .focus() on reasonSelectRef (the p-select) in useEffect
        expect(focusCalls.some((el) => el === pSelect)).toBe(true)
      } finally {
        HTMLElement.prototype.focus = origFocus
      }
    })
  })

  // ─── AC4: completed option visibility by taskStatus ───────────────────────

  describe('AC4: completed option hidden when taskStatus !== "done"; shown when === "done"', () => {
    it('hides the completed option when taskStatus is "in-progress"', () => {
      const { container } = renderModal({ taskStatus: 'in-progress' })
      const pSelect = container.querySelector('p-select')
      const opts = Array.from(pSelect?.querySelectorAll('option') ?? []) as HTMLOptionElement[]
      const completedOpt = opts.find((o) => o.value === 'completed')
      // Option must be absent or hidden
      expect(completedOpt === undefined || completedOpt.hidden).toBe(true)
    })

    it('shows the completed option when taskStatus is "done"', () => {
      const { container } = renderModal({ taskStatus: 'done' })
      const pSelect = container.querySelector('p-select')
      const opts = Array.from(pSelect?.querySelectorAll('option') ?? []) as HTMLOptionElement[]
      const completedOpt = opts.find((o) => o.value === 'completed')
      expect(completedOpt).not.toBeUndefined()
      expect(completedOpt?.hidden).toBe(false)
    })

    it('hides the completed option when taskStatus is "todo" (boundary: non-done status)', () => {
      const { container } = renderModal({ taskStatus: 'todo' })
      const pSelect = container.querySelector('p-select')
      const opts = Array.from(pSelect?.querySelectorAll('option') ?? []) as HTMLOptionElement[]
      const completedOpt = opts.find((o) => o.value === 'completed')
      expect(completedOpt === undefined || completedOpt.hidden).toBe(true)
    })
  })

  // ─── AC5: Refs input visibility by reason ────────────────────────────────

  describe('AC5: refs input visible for deprecated/duplicate; hidden for all other reasons', () => {
    it('shows refs input when reason is "deprecated"', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      expect(container.querySelector('p-input-text')).not.toBeNull()
    })

    it('shows refs input when reason is "duplicate"', () => {
      const { container } = renderModal()
      selectReason(container, 'duplicate')
      expect(container.querySelector('p-input-text')).not.toBeNull()
    })

    it('hides refs input when reason is "completed"', () => {
      const { container } = renderModal({ taskStatus: 'done' })
      selectReason(container, 'completed')
      expect(container.querySelector('p-input-text')).toBeNull()
    })

    it('hides refs input when reason is "dropped"', () => {
      const { container } = renderModal()
      selectReason(container, 'dropped')
      expect(container.querySelector('p-input-text')).toBeNull()
    })

    it('hides refs input when reason is "wontfix"', () => {
      const { container } = renderModal()
      selectReason(container, 'wontfix')
      expect(container.querySelector('p-input-text')).toBeNull()
    })

    it('hides refs input in initial state (no reason selected)', () => {
      const { container } = renderModal()
      expect(container.querySelector('p-input-text')).toBeNull()
    })
  })

  // ─── AC6: refs state clears when switching from refs-requiring reason ─────

  describe('AC6: refs state clears to "" when switching from refs-requiring to other reason', () => {
    it('clears refs when switching from deprecated to dropped', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      changeRefsInput(container, '1230, 1229')

      selectReason(container, 'dropped')
      // refs cleared — submit still disabled (refs required but empty)
      selectReason(container, 'deprecated')
      expect((getSubmitBtn(container) as HTMLButtonElement).disabled).toBe(true)
    })

    it('clears refs when switching from duplicate to wontfix', () => {
      const { container } = renderModal()
      selectReason(container, 'duplicate')
      changeRefsInput(container, '1230')

      selectReason(container, 'wontfix')
      // Switch back to verify the value was cleared — refs empty → submit still disabled
      selectReason(container, 'duplicate')
      // refs cleared — submit still disabled (refs required but empty)
      expect((getSubmitBtn(container) as HTMLButtonElement).disabled).toBe(true)
    })
  })

  // ─── AC7: Submit disabled when no reason selected ─────────────────────────

  describe('AC7: submit disabled when no reason selected', () => {
    it('submit button is disabled in the initial state (no reason selected)', () => {
      const { container } = renderModal()
      const submitBtn = getSubmitBtn(container)
      // PDS PButton exposes disabled as a JS property (React 19 sets it as property on custom element)
      expect((submitBtn as HTMLButtonElement).disabled).toBe(true)
    })
  })

  // ─── AC8: Submit disabled when refs required and refs empty ───────────────

  describe('AC8: submit disabled when reason requires refs and refs field is empty', () => {
    it('submit disabled when reason is "deprecated" and refs is empty', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      expect((getSubmitBtn(container) as HTMLButtonElement).disabled).toBe(true)
    })

    it('submit disabled when reason is "duplicate" and refs is empty', () => {
      const { container } = renderModal()
      selectReason(container, 'duplicate')
      expect((getSubmitBtn(container) as HTMLButtonElement).disabled).toBe(true)
    })

    it('submit enabled when reason is "deprecated" and refs has content', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      changeRefsInput(container, '1230')
      expect((getSubmitBtn(container) as HTMLButtonElement).disabled).toBe(false)
    })

    it('submit enabled when reason is "dropped" (no refs required)', () => {
      const { container } = renderModal()
      selectReason(container, 'dropped')
      expect((getSubmitBtn(container) as HTMLButtonElement).disabled).toBe(false)
    })
  })

  // ─── AC9: Submit disabled while isSubmitting ──────────────────────────────

  describe('AC9: submit disabled while isSubmitting === true', () => {
    it('disables submit button while a request is in-flight', async () => {
      let resolveRequest!: (v: unknown) => void
      vi.stubGlobal(
        'fetch',
        vi.fn(() => new Promise((res) => { resolveRequest = res })),
      )

      const { container } = renderModal()
      selectReason(container, 'dropped')

      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        expect((getSubmitBtn(container) as HTMLButtonElement).disabled).toBe(true)
      })

      // Resolve to clean up dangling promise
      resolveRequest({ ok: true, json: () => Promise.resolve({}) })
    })
  })

  // ─── AC10: Refs hint text shown when refs field is visible ────────────────

  describe('AC10: hint text "Required \u2014 enter at least one task ID" shown with refs field', () => {
    it('shows hint text when reason is "deprecated"', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      expect(container.textContent).toContain('Required \u2014 enter at least one task ID')
    })

    it('shows hint text when reason is "duplicate"', () => {
      const { container } = renderModal()
      selectReason(container, 'duplicate')
      expect(container.textContent).toContain('Required \u2014 enter at least one task ID')
    })

    it('does not show hint text when reason is "dropped" (refs not visible)', () => {
      const { container } = renderModal()
      selectReason(container, 'dropped')
      expect(container.textContent).not.toContain('Required \u2014 enter at least one task ID')
    })

    it('does not show hint text in initial state (no reason selected)', () => {
      const { container } = renderModal()
      expect(container.textContent).not.toContain('Required \u2014 enter at least one task ID')
    })
  })

  // ─── AC11: Non-numeric refs token → client-side error, no HTTP request ────

  describe('AC11: non-numeric refs token produces client-side error; no HTTP request fired', () => {
    it('shows inline error and does not call fetch when refs contains only letters', async () => {
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal()
      selectReason(container, 'deprecated')
      changeRefsInput(container, 'abc')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const errorEl = container.querySelector('[data-testid="archival-error"]')
        expect(errorEl).not.toBeNull()
        expect(errorEl?.textContent?.trim().length).toBeGreaterThan(0)
      })

      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('shows inline error and does not call fetch when refs contains mixed valid/invalid tokens', async () => {
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal()
      selectReason(container, 'deprecated')
      changeRefsInput(container, '1230, abc, 1229')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const errorEl = container.querySelector('[data-testid="archival-error"]')
        expect(errorEl).not.toBeNull()
      })

      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('calls fetch when refs contains only numeric tokens (boundary: all valid)', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })),
      )

      const { container } = renderModal()
      selectReason(container, 'deprecated')
      changeRefsInput(container, '1230, 1229')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        expect(vi.mocked(global.fetch)).toHaveBeenCalled()
      })
    })
  })

  // ─── AC12: On 422: modal stays open, error.detail shown verbatim ──────────

  describe('AC12: 422 response — modal stays open and error.detail shown verbatim', () => {
    it('keeps modal open and displays error.detail text verbatim on 422', async () => {
      const errorDetail = 'ERR_ARCHIVAL_REFS_FORBIDDEN: refs not allowed for dropped'
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
            status: 422,
            json: () => Promise.resolve({ detail: errorDetail }),
          }),
        ),
      )

      const { container, onClose } = renderModal()
      selectReason(container, 'dropped')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const errorEl = container.querySelector('[data-testid="archival-error"]')
        expect(errorEl).not.toBeNull()
        expect(errorEl?.textContent).toBe(errorDetail)
      })

      expect(onClose).not.toHaveBeenCalled()
    })
  })

  // ─── AC13: On 409: modal stays open, stale-snapshot error shown ───────────

  describe('AC13: 409 response — modal stays open with modal-local stale-snapshot message', () => {
    it('keeps modal open and shows an error message on 409', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
            status: 409,
            json: () => Promise.resolve({ detail: 'conflict' }),
          }),
        ),
      )

      const { container, onClose } = renderModal()
      selectReason(container, 'dropped')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const errorEl = container.querySelector('[data-testid="archival-error"]')
        expect(errorEl).not.toBeNull()
        expect(errorEl?.textContent).toBe('Task snapshot is stale; refresh and try again.')
      })

      expect(onClose).not.toHaveBeenCalled()
    })

    it('409 error message is exactly the stale-snapshot string (no keyword guessing)', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
            status: 409,
            json: () => Promise.resolve({ detail: 'conflict' }),
          }),
        ),
      )

      const { container } = renderModal()
      selectReason(container, 'dropped')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const errorEl = container.querySelector('[data-testid="archival-error"]')
        expect(errorEl).not.toBeNull()
        expect(errorEl?.textContent).toBe('Task snapshot is stale; refresh and try again.')
      })
    })
  })

  // ─── AC14: On success: modal closes, board refreshes ─────────────────────

  describe('AC14: success — onClose and onRefresh called after successful archival', () => {
    it('calls onClose and onRefresh after a 200 OK response', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })),
      )

      const { container, onClose, onRefresh } = renderModal()
      selectReason(container, 'dropped')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledOnce()
        expect(onRefresh).toHaveBeenCalledOnce()
      })
    })

    it('sends status="archived", updated=expectedUpdated, archival_reason, ' +
      'archival_refs=[] for non-refs reason', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
      )
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal({ taskId: 99, expectedUpdated: '2026-05-01T12:00:00+00:00' })
      selectReason(container, 'dropped')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining('/api/tasks/99/move'),
          expect.objectContaining({ method: 'POST' }),
        )
        const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload['status']).toBe('archived')
        expect(payload['updated']).toBe('2026-05-01T12:00:00+00:00')
        expect(payload['archival_reason']).toBe('dropped')
        expect(payload['archival_refs']).toEqual([])
      })
    })

    it('sends archival_refs as parsed integer array for deprecated reason', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
      )
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal({ taskId: 42, expectedUpdated: '2026-05-01T12:00:00+00:00' })
      selectReason(container, 'deprecated')
      changeRefsInput(container, '1230, 1229')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload['archival_reason']).toBe('deprecated')
        expect(payload['archival_refs']).toEqual([1230, 1229])
      })
    })
  })

  // ─── AC15: Focus trap — Tab/Shift+Tab cycle within modal ─────────────────

  describe('AC15: focus trap — Tab and Shift+Tab cycle within modal only', () => {
    it('Tab on the last focusable element wraps focus to the first focusable element', () => {
      const { container } = renderModal()
      selectReason(container, 'dropped')

      const modal = container.querySelector('[role="dialog"]') as HTMLElement
      const focusable = modal.querySelectorAll<HTMLElement>(
        'p-button:not([disabled]), p-input-text:not([disabled]), p-select:not([disabled]), ' +
          'p-textarea:not([disabled]), button:not([disabled]), [href], input:not([disabled]), ' +
          'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )
      expect(focusable.length).toBeGreaterThan(1)

      const lastEl = focusable[focusable.length - 1]
      const firstEl = focusable[0]

      // PDS custom elements need explicit tabIndex to be focusable in jsdom.
      // We use a spy on firstEl.focus() to verify the trap redirects there.
      const firstFocusSpy = vi.spyOn(firstEl, 'focus')
      lastEl.setAttribute('tabindex', '0')
      lastEl.focus()

      fireEvent.keyDown(lastEl, { key: 'Tab', shiftKey: false })

      expect(firstFocusSpy).toHaveBeenCalled()
    })

    it('Shift+Tab on the first focusable element wraps focus to the last focusable element', () => {
      const { container } = renderModal()
      selectReason(container, 'dropped')

      const modal = container.querySelector('[role="dialog"]') as HTMLElement
      const focusable = modal.querySelectorAll<HTMLElement>(
        'p-button:not([disabled]), p-input-text:not([disabled]), p-select:not([disabled]), ' +
          'p-textarea:not([disabled]), button:not([disabled]), [href], input:not([disabled]), ' +
          'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )
      expect(focusable.length).toBeGreaterThan(1)

      const firstEl = focusable[0]
      const lastEl = focusable[focusable.length - 1]

      // PDS custom elements need explicit tabIndex to be focusable in jsdom.
      // We use a spy on lastEl.focus() to verify the trap redirects there.
      const lastFocusSpy = vi.spyOn(lastEl, 'focus')
      firstEl.setAttribute('tabindex', '0')
      firstEl.focus()

      fireEvent.keyDown(firstEl, { key: 'Tab', shiftKey: true })

      expect(lastFocusSpy).toHaveBeenCalled()
    })
  })

  // ─── AC16: Escape closes modal without firing move request ───────────────

  describe('AC16: Escape key closes modal without firing a move request', () => {
    it('calls onClose when Escape is pressed on the modal', () => {
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)

      const { container, onClose } = renderModal()
      const modal = container.querySelector('[role="dialog"]') as HTMLElement
      fireEvent.keyDown(modal, { key: 'Escape' })

      expect(onClose).toHaveBeenCalledOnce()
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('does not fire a move request when Escape is pressed with a reason already selected', () => {
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal()
      selectReason(container, 'dropped')

      const modal = container.querySelector('[role="dialog"]') as HTMLElement
      fireEvent.keyDown(modal, { key: 'Escape' })

      expect(fetchMock).not.toHaveBeenCalled()
    })
  })

  // ─── AC-Addendum: Comma-and-whitespace refs tokenization ─────────────────

  describe('AC-Addendum: whitespace and mixed separators are accepted and parse to numeric refs', () => {
    it('accepts whitespace-only separated refs ("1230 1229") and sends them as numeric array', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
      )
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal({ taskId: 42, expectedUpdated: '2026-05-01T12:00:00+00:00' })
      selectReason(container, 'deprecated')
      changeRefsInput(container, '1230 1229')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload['archival_refs']).toEqual([1230, 1229])
      })
    })

    it('accepts mixed comma-and-whitespace separators ("1230, 1229") and sends numeric refs', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
      )
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal({ taskId: 42, expectedUpdated: '2026-05-01T12:00:00+00:00' })
      selectReason(container, 'deprecated')
      changeRefsInput(container, '1230, 1229')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload['archival_refs']).toEqual([1230, 1229])
      })
    })

    it('accepts consecutive separators ("1230  1229") — empty tokens filtered — sends numeric refs', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
      )
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal({ taskId: 42, expectedUpdated: '2026-05-01T12:00:00+00:00' })
      selectReason(container, 'duplicate')
      changeRefsInput(container, '1230  1229')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload['archival_refs']).toEqual([1230, 1229])
      })
    })
  })

  // ─── AC-Addendum: Non-422/409 HTTP error display ─────────────────────────

  describe('AC-Addendum: non-422/409 HTTP error — modal stays open, generic error displayed', () => {
    it('shows generic error message on 404, keeps modal open, resets isSubmitting', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
            status: 404,
            json: () => Promise.resolve({}),
          }),
        ),
      )

      const { container, onClose } = renderModal()
      selectReason(container, 'dropped')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const errorEl = container.querySelector('[data-testid="archival-error"]')
        expect(errorEl).not.toBeNull()
        expect(errorEl?.textContent).toBe('Archival failed (404).')
      })

      expect(onClose).not.toHaveBeenCalled()
      // isSubmitting resets — submit button is re-enabled
      expect((getSubmitBtn(container) as HTMLButtonElement).disabled).toBe(false)
    })
  })

  // ─── AC-Addendum: Network failure error display ───────────────────────────

  describe('AC-Addendum: network failure (fetch throws) — modal stays open, generic error displayed', () => {
    it('shows generic error message when fetch throws, keeps modal open, resets isSubmitting', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.reject(new Error('Network error'))),
      )

      const { container, onClose } = renderModal()
      selectReason(container, 'dropped')
      fireEvent.click(getSubmitBtn(container))

      await waitFor(() => {
        const errorEl = container.querySelector('[data-testid="archival-error"]')
        expect(errorEl).not.toBeNull()
        expect(errorEl?.textContent).toBe('Archival failed due to network error.')
      })

      expect(onClose).not.toHaveBeenCalled()
      // isSubmitting resets — submit button is re-enabled
      expect((getSubmitBtn(container) as HTMLButtonElement).disabled).toBe(false)
    })
  })
})

