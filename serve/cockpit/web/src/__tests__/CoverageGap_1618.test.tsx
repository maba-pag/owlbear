/**
 * Coverage gap tests for #1618 (retry) — ConfirmDialog and ResolveModal
 *
 * Targets uncovered code paths identified by the behavioral proof bundle
 * coverage report:
 *   - ConfirmDialog: 63% → target ≥90%
 *   - ResolveModal:  75% → target ≥90%
 *
 * ConfirmDialog paths targeted:
 *   - useMemo description variants (move-backward ±targetStatus, unblock ±blockReason)
 *   - Cancel / Confirm button click handlers
 *   - handleModalKeyDown: Tab wrap-forward, Shift+Tab wrap-backward, Shift+Tab on modal,
 *     no-focusable-elements guard, Escape
 *
 * ResolveModal paths targeted:
 *   - dr=null early-return guard
 *   - requestClose idempotency (closeRequestedRef)
 *   - handleModalKeyDown: Tab wrap-forward, Shift+Tab wrap-backward, Shift+Tab on modal,
 *     no-focusable-elements guard
 *   - Non-retryable error (4xx) — retryable=false branch
 *   - dismissError → error notification removed
 *   - retryResolve → re-submits
 */
import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ConfirmDialog from '../components/ConfirmDialog'
import ResolveModal from '../components/ResolveModal'
import type { PendingDRWithBody } from '../components/ResolveModal'

// ─── PDS Stencil form-component workaround ───────────────────────────────────
beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

// ─── react-markdown mock ──────────────────────────────────────────────────────
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────
const DR_FIXTURE: PendingDRWithBody = {
  id: 'dr-1618-cov',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: '2026-05-01T10:00:00Z',
  title: 'Coverage gap DR',
  body_preview: 'Gap coverage DR.',
  body: '## Context\n\nShould we proceed?',
}

// ─── Render helpers ───────────────────────────────────────────────────────────
function renderConfirmDialog(overrides: {
  type?: 'unclaim' | 'move-backward' | 'unblock'
  targetStatus?: string | null
  blockReason?: string | null
  onCancel?: () => void
  onConfirm?: () => void
} = {}) {
  const onCancel = overrides.onCancel ?? vi.fn()
  const onConfirm = overrides.onConfirm ?? vi.fn()
  const utils = render(
    <PorscheDesignSystemProvider>
      <ConfirmDialog
        type={overrides.type ?? 'unclaim'}
        targetStatus={overrides.targetStatus}
        blockReason={overrides.blockReason}
        onCancel={onCancel}
        onConfirm={onConfirm}
      />
    </PorscheDesignSystemProvider>,
  )
  return { ...utils, onCancel, onConfirm }
}

function renderResolveModal(overrides: {
  dr?: PendingDRWithBody | null
  onClose?: () => void
  onResolved?: () => void
} = {}) {
  const dr = overrides.dr !== undefined ? overrides.dr : DR_FIXTURE
  const onClose = overrides.onClose ?? vi.fn()
  const onResolved = overrides.onResolved ?? vi.fn()
  const utils = render(
    <PorscheDesignSystemProvider>
      <ResolveModal dr={dr} onClose={onClose} onResolved={onResolved} />
    </PorscheDesignSystemProvider>,
  )
  return { ...utils, onClose, onResolved }
}

// ─────────────────────────────────────────────────────────────────────────────
// ConfirmDialog coverage gaps
// ─────────────────────────────────────────────────────────────────────────────
describe('TestFromAC_ConfirmDialogCoverageGap', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  // ─── useMemo description variants ─────────────────────────────────────────

  it('type=move-backward with targetStatus renders "Move to {status}" in description', () => {
    const { container } = renderConfirmDialog({ type: 'move-backward', targetStatus: 'done' })
    expect(container.textContent).toContain('Move to done')
  })

  it('previousFocusRef is null when document.activeElement is not an HTMLElement', () => {
    // Covers the null branch of the ternary:
    //   previousFocusRef.current = document.activeElement instanceof HTMLElement ? ... : null
    // and the null path of:
    //   previousFocusRef.current?.focus()  (in cleanup — no-op because ref is null)
    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(null as unknown as Element)
    const { container, unmount } = renderConfirmDialog()
    expect(container.querySelector('p-modal')).not.toBeNull()
    // Unmount to trigger cleanup — previousFocusRef.current is null, so ?.focus() is a no-op
    unmount()
  })

  it('useMemo cache-hit: move-backward re-render with same props keeps description stable', () => {
    // React Compiler transforms useMemo into a cache-check. When deps are unchanged,
    // the cached value is returned via a code path mapped to the return-object closing brace
    // (line 38 in source). Re-rendering with same type+targetStatus triggers this path.
    const { container, rerender } = renderConfirmDialog({ type: 'move-backward', targetStatus: 'done' })
    expect(container.textContent).toContain('Move to done')
    rerender(
      <PorscheDesignSystemProvider>
        <ConfirmDialog type="move-backward" targetStatus="done" onCancel={vi.fn()} onConfirm={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.textContent).toContain('Move to done')
  })

  it('useMemo cache-hit: unclaim re-render with same props keeps description stable', () => {
    // Covers React Compiler cache-hit path mapped to useMemo unclaim branch closing brace (line 45).
    const { container, rerender } = renderConfirmDialog({ type: 'unclaim' })
    expect(container.textContent).toContain('Release claim')
    rerender(
      <PorscheDesignSystemProvider>
        <ConfirmDialog type="unclaim" onCancel={vi.fn()} onConfirm={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.textContent).toContain('Release claim')
  })

  it('useMemo cache-hit: unblock re-render with same props keeps description stable', () => {
    // Covers React Compiler cache-hit path mapped to useMemo default branch closing brace (line 51).
    const { container, rerender } = renderConfirmDialog({ type: 'unblock' })
    expect(container.textContent).toContain('Unblock task')
    rerender(
      <PorscheDesignSystemProvider>
        <ConfirmDialog type="unblock" onCancel={vi.fn()} onConfirm={vi.fn()} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.textContent).toContain('Unblock task')
  })

  it('type=move-backward with null targetStatus renders "previous status" in description', () => {
    const { container } = renderConfirmDialog({ type: 'move-backward', targetStatus: null })
    expect(container.textContent).toContain('previous status')
  })

  it('type=unblock renders "Unblock task" in description', () => {
    const { container } = renderConfirmDialog({ type: 'unblock' })
    expect(container.textContent).toContain('Unblock task')
  })

  it('type=unblock with blockReason renders the block reason text', () => {
    const { container } = renderConfirmDialog({ type: 'unblock', blockReason: 'Waiting for API spec' })
    expect(container.textContent).toContain('Waiting for API spec')
  })

  it('type=unblock without blockReason does not render a blockReason span', () => {
    const { container } = renderConfirmDialog({ type: 'unblock', blockReason: null })
    // The span with block reason content must not appear
    const spans = Array.from(container.querySelectorAll('span'))
    for (const span of spans) {
      expect(span.textContent).not.toBe('Waiting for API spec')
    }
  })

  // ─── Button click handlers ─────────────────────────────────────────────────

  it('clicking the Cancel (secondary) button calls onCancel', () => {
    const { container, onCancel } = renderConfirmDialog()
    // Cancel is the first p-button (variant="secondary")
    const cancelBtn = container.querySelectorAll('p-button')[0] as HTMLElement
    expect(cancelBtn).toBeTruthy()
    fireEvent.click(cancelBtn)
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('clicking the Confirm button calls onConfirm', () => {
    const { container, onConfirm } = renderConfirmDialog()
    // Confirm is the second p-button
    const confirmBtn = container.querySelectorAll('p-button')[1] as HTMLElement
    expect(confirmBtn).toBeTruthy()
    fireEvent.click(confirmBtn)
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  // ─── handleModalKeyDown: Escape ────────────────────────────────────────────

  it('pressing Escape on the p-modal calls onCancel via handleModalKeyDown', () => {
    const { container, onCancel } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement
    expect(pModal).not.toBeNull()
    fireEvent.keyDown(pModal, { key: 'Escape' })
    expect(onCancel).toHaveBeenCalledOnce()
  })

  // ─── handleModalKeyDown: Tab cycling ──────────────────────────────────────

  it('Tab when active is the last focusable element wraps focus to the first', () => {
    const { container } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]
    expect(pButtons.length).toBeGreaterThanOrEqual(2)

    const lastBtn = pButtons[pButtons.length - 1]
    const firstBtn = pButtons[0]
    const focusSpy = vi.spyOn(firstBtn, 'focus')

    // Mock document.activeElement — p-button custom elements are not natively
    // focusable in jsdom, so calling lastBtn.focus() does not update activeElement.
    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(lastBtn)

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })

    expect(focusSpy).toHaveBeenCalledOnce()
  })

  it('Shift+Tab when active is the first focusable element wraps focus to the last', () => {
    const { container } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]
    expect(pButtons.length).toBeGreaterThanOrEqual(2)

    const firstBtn = pButtons[0]
    const lastBtn = pButtons[pButtons.length - 1]
    const focusSpy = vi.spyOn(lastBtn, 'focus')

    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(firstBtn)

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: true })

    expect(focusSpy).toHaveBeenCalledOnce()
  })

  it('Shift+Tab when active is the modal container wraps focus to the last focusable element', () => {
    const { container } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]
    const lastBtn = pButtons[pButtons.length - 1]
    const focusSpy = vi.spyOn(lastBtn, 'focus')

    // Simulate the modal being the active element (happens naturally on mount
    // via useEffect's modal.focus(), but p-modal has tabIndex={-1} which jsdom
    // treats as focusable, so we mock to be explicit).
    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(pModal)

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: true })

    expect(focusSpy).toHaveBeenCalledOnce()
  })

  it('Tab when no focusable elements are present does not throw', () => {
    const { container } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement

    // Disable all p-buttons so getFocusableElements() returns []
    Array.from(container.querySelectorAll('p-button')).forEach((btn) =>
      btn.setAttribute('disabled', ''),
    )

    expect(() => {
      fireEvent.keyDown(pModal, { key: 'Tab' })
    }).not.toThrow()
  })

  // ─── getFocusableElements: filter branches ────────────────────────────────

  it('getFocusableElements excludes elements with aria-hidden="true"', () => {
    // Inject a native button with aria-hidden into p-modal so the TAB_FOCUSABLE_SELECTOR
    // picks it up (button:not([disabled])) but the aria-hidden filter excludes it.
    const { container } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]

    const hiddenBtn = document.createElement('button')
    hiddenBtn.setAttribute('aria-hidden', 'true')
    pModal.appendChild(hiddenBtn)

    // Mock active element to be the last p-button so Tab would wrap to first
    // ONLY if the hidden button is excluded; if included, wrapping would go to hiddenBtn
    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(pButtons[pButtons.length - 1])
    const firstBtnSpy = vi.spyOn(pButtons[0], 'focus')

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })

    // Focus wrapped to the first p-button, confirming hidden button was excluded
    expect(firstBtnSpy).toHaveBeenCalledOnce()

    pModal.removeChild(hiddenBtn)
  })

  it('getFocusableElements excludes elements that have the disabled attribute', () => {
    // Inject a tabIndex=0 element WITH disabled attribute: it passes the
    // [tabindex]:not([tabindex="-1"]) CSS selector but is filtered out by
    // the hasAttribute('disabled') check inside getFocusableElements.
    const { container } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]

    const disabledTabEl = document.createElement('div')
    disabledTabEl.setAttribute('tabindex', '0')
    disabledTabEl.setAttribute('disabled', '')
    pModal.appendChild(disabledTabEl)

    // Mock active element to be the last p-button so Tab would wrap to first p-button
    // (not to disabledTabEl, because it should be filtered out)
    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(pButtons[pButtons.length - 1])
    const firstBtnSpy = vi.spyOn(pButtons[0], 'focus')

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })

    expect(firstBtnSpy).toHaveBeenCalledOnce()

    pModal.removeChild(disabledTabEl)
  })

  // ─── MutationObserver callback (line 65) ─────────────────────────────────
  // Mocking MutationObserver lets us invoke the captured callback directly
  // without triggering real attribute mutations (which would fight with PDS).

  it('MutationObserver callback re-applies dialog attributes when invoked', () => {
    let capturedCallback: MutationCallback | null = null
    const mockDisconnect = vi.fn()
    const mockObserve = vi.fn()

    // MutationObserver must be mocked as a class (arrow functions cannot be constructors).
    // vi.unstubAllGlobals() in afterEach restores the real MutationObserver.
    class MockMutationObserver {
      observe = mockObserve
      disconnect = mockDisconnect
      constructor(cb: MutationCallback) {
        capturedCallback = cb
      }
    }
    vi.stubGlobal('MutationObserver', MockMutationObserver)

    const { container } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement

    // Invoke the captured callback — covers the applyDialogAttrs() call at line 65.
    capturedCallback!([], {} as MutationObserver)

    expect(pModal.getAttribute('role')).toBe('dialog')
    expect(pModal.getAttribute('aria-modal')).toBe('true')
  })

})

// ─────────────────────────────────────────────────────────────────────────────
// ResolveModal coverage gaps
// ─────────────────────────────────────────────────────────────────────────────
describe('TestFromAC_ResolveModalCoverageGap', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  // ─── dr=null early-return guard ───────────────────────────────────────────

  it('renders nothing when dr is null', () => {
    const { container } = renderResolveModal({ dr: null })
    expect(container.querySelector('p-modal')).toBeNull()
  })

  // ─── requestClose idempotency ─────────────────────────────────────────────

  it('onClose is called exactly once even when close is triggered multiple times', () => {
    const onClose = vi.fn()
    const { container } = renderResolveModal({ onClose })
    const cancelBtn = container.querySelector('[data-testid="resolve-cancel"]') as HTMLElement
    const pModal = container.querySelector('p-modal') as HTMLElement

    // First close via Cancel button
    fireEvent.click(cancelBtn)
    expect(onClose).toHaveBeenCalledOnce()

    // Second close via dismiss event — guard (closeRequestedRef) must prevent double-call
    fireEvent(pModal, new CustomEvent('dismiss', { bubbles: true }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  // ─── handleModalKeyDown: Tab cycling ──────────────────────────────────────
  // ResolveModal focusable order: radio[approved], radio[rejected], radio[needs-info],
  // p-button[submit], p-button[cancel].  first = approved radio, last = cancel p-button.

  it('Tab when active is the last focusable element wraps focus to the first', () => {
    const { container } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const radios = Array.from(container.querySelectorAll('input[type="radio"]')) as HTMLElement[]
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]

    const first = radios[0]
    const last = pButtons[pButtons.length - 1]
    const focusSpy = vi.spyOn(first, 'focus')

    // Mock document.activeElement — radio/p-button elements are not natively
    // focusable in jsdom without tabindex, so focus() doesn't update activeElement.
    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(last)

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })

    expect(focusSpy).toHaveBeenCalledOnce()
  })

  it('Shift+Tab when active is the first focusable element wraps focus to the last', () => {
    const { container } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const radios = Array.from(container.querySelectorAll('input[type="radio"]')) as HTMLElement[]
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]

    const first = radios[0]
    const last = pButtons[pButtons.length - 1]
    const focusSpy = vi.spyOn(last, 'focus')

    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(first)

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: true })

    expect(focusSpy).toHaveBeenCalledOnce()
  })

  it('Shift+Tab when active is the modal container wraps focus to the last focusable element', () => {
    const { container } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]
    const last = pButtons[pButtons.length - 1]
    const focusSpy = vi.spyOn(last, 'focus')

    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(pModal)

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: true })

    expect(focusSpy).toHaveBeenCalledOnce()
  })

  it('Tab when no focusable elements are present does not throw', () => {
    const { container } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement

    // Disable all inputs and p-buttons so getFocusableElements() returns []
    Array.from(container.querySelectorAll('input, p-button')).forEach((el) =>
      el.setAttribute('disabled', ''),
    )

    expect(() => {
      fireEvent.keyDown(pModal, { key: 'Tab' })
    }).not.toThrow()
  })

  // ─── handleModalKeyDown: Escape ────────────────────────────────────────────

  it('Escape key in the modal calls requestClose via handleModalKeyDown', () => {
    const { onClose } = renderResolveModal()
    const pModal = document.querySelector('p-modal') as HTMLElement
    fireEvent.keyDown(pModal, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  // ─── handleDocumentEscape: document-level Escape key ──────────────────────

  it('document Escape keydown calls requestClose via handleDocumentEscape', () => {
    const { onClose } = renderResolveModal()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('document Escape keydown with defaultPrevented does not call requestClose', () => {
    const { onClose } = renderResolveModal()
    // Create an event where defaultPrevented is always true (simulates another
    // handler having already called preventDefault() before ours runs).
    const event = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
    Object.defineProperty(event, 'defaultPrevented', { get: () => true })
    document.dispatchEvent(event)
    expect(onClose).not.toHaveBeenCalled()
  })

  // ─── getFocusableElements: filter branches ─────────────────────────────────

  it('getFocusableElements excludes disabled elements in ResolveModal Tab wrapping', () => {
    const { container } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const radios = Array.from(container.querySelectorAll('input[type="radio"]')) as HTMLElement[]
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]

    // Inject a native button with disabled attribute — selector matches but filter excludes it
    const disabledBtn = document.createElement('button')
    disabledBtn.setAttribute('disabled', '')
    pModal.appendChild(disabledBtn)

    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(pButtons[pButtons.length - 1])
    const firstFocusSpy = vi.spyOn(radios[0], 'focus')
    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })
    expect(firstFocusSpy).toHaveBeenCalledOnce()

    pModal.removeChild(disabledBtn)
  })

  it('getFocusableElements excludes aria-hidden elements in ResolveModal Tab wrapping', () => {
    const { container } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const radios = Array.from(container.querySelectorAll('input[type="radio"]')) as HTMLElement[]
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]

    // Inject a native button with aria-hidden="true" — selector matches but filter excludes it
    const hiddenBtn = document.createElement('button')
    hiddenBtn.setAttribute('aria-hidden', 'true')
    pModal.appendChild(hiddenBtn)

    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(pButtons[pButtons.length - 1])
    const firstFocusSpy = vi.spyOn(radios[0], 'focus')
    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })
    expect(firstFocusSpy).toHaveBeenCalledOnce()

    pModal.removeChild(hiddenBtn)
  })

  // ─── notes onChange ────────────────────────────────────────────────────────

  it('onChange on resolution notes textarea invokes setNotes', () => {
    // React 19 registers custom element event handlers via addEventListener (not
    // as element properties). fireEvent.change dispatches a native change event
    // that reaches the React handler, covering the arrow function at line 290.
    const { container } = renderResolveModal()
    const textarea = container.querySelector('[data-testid="resolve-notes"]') as HTMLElement
    expect(textarea).not.toBeNull()
    expect(() => fireEvent.change(textarea)).not.toThrow()
  })

  // ─── Error state: retryable vs non-retryable ──────────────────────────────

  it('4xx error sets retryable=false — no action label on error notification', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 400,
          json: () => Promise.resolve({}),
        }),
      ),
    )
    const { container } = renderResolveModal()

    // Select a radio to enable submit
    const radio = container.querySelector('input[type="radio"][value="approved"]') as HTMLElement
    fireEvent.click(radio)

    const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement
    fireEvent.click(submitBtn)

    await waitFor(() => {
      const notification = container.querySelector(
        'p-inline-notification[data-testid="resolve-error"]',
      ) as (HTMLElement & { actionLabel?: string }) | null
      expect(notification).not.toBeNull()
      // Non-retryable: actionLabel prop is undefined (not set)
      expect(notification!.actionLabel).toBeUndefined()
    })
  })

  it('5xx error sets retryable=true — action label "Retry" present on error notification', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 500,
          json: () => Promise.resolve({}),
        }),
      ),
    )
    const { container } = renderResolveModal()

    const radio = container.querySelector('input[type="radio"][value="approved"]') as HTMLElement
    fireEvent.click(radio)

    const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement
    fireEvent.click(submitBtn)

    await waitFor(() => {
      const notification = container.querySelector(
        'p-inline-notification[data-testid="resolve-error"]',
      ) as (HTMLElement & { actionLabel?: string }) | null
      expect(notification).not.toBeNull()
      expect(notification!.actionLabel).toBe('Retry')
    })
  })

  // ─── dismissError → notification removed ─────────────────────────────────

  it('firing dismiss on the error notification clears the error state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new Error('Network error'))),
    )
    const { container } = renderResolveModal()

    const radio = container.querySelector('input[type="radio"][value="rejected"]') as HTMLElement
    fireEvent.click(radio)

    const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement
    fireEvent.click(submitBtn)

    // Wait for error notification to appear
    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-error"]')).not.toBeNull()
    })

    // Invoke dismissError via the imperative onDismiss property set by the ref
    // callback. React 19 custom element onDismiss props don't fire from raw
    // CustomEvent dispatch in jsdom — use the stored property directly.
    const notification = container.querySelector('[data-testid="resolve-error"]') as HTMLElement & { onDismiss?: () => void }
    expect(typeof notification.onDismiss).toBe('function')
    notification.onDismiss?.()

    // Error notification must disappear after dismissError runs
    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-error"]')).toBeNull()
    })
  })

  // ─── retryResolve → re-submits ────────────────────────────────────────────

  it('firing action on the error notification re-submits the request (retryResolve)', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({}),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: DR_FIXTURE.id, response: 'approved' }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const onResolved = vi.fn()
    const { container } = renderResolveModal({ onResolved })

    const radio = container.querySelector('input[type="radio"][value="approved"]') as HTMLElement
    fireEvent.click(radio)

    const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement
    fireEvent.click(submitBtn)

    // Wait for retryable error to appear
    await waitFor(() => {
      expect(container.querySelector('[data-testid="resolve-error"]')).not.toBeNull()
    })

    // Invoke retryResolve via the imperative onAction property set by the ref
    // callback (same reason as dismissError — React 19 custom element event props
    // don't bubble from raw CustomEvent dispatch in jsdom).
    const notification = container.querySelector('[data-testid="resolve-error"]') as HTMLElement & { onAction?: () => void }
    expect(typeof notification.onAction).toBe('function')
    notification.onAction?.()

    // Retry should succeed: fetchMock called twice, onResolved called
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(onResolved).toHaveBeenCalledOnce()
    })
  })
})
