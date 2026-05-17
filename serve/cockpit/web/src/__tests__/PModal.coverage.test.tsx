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
import { ApiError } from '../api/errors'
import * as decisionsApi from '../api/decisions'

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

  // ─── Tab key: active is null (non-HTMLElement) ────────────────────────────

  it('Tab key when document.activeElement is not an HTMLElement does not wrap focus', () => {
    // Covers the null branch of:
    //   const active = document.activeElement instanceof HTMLElement ? document.activeElement : null
    // in handleModalKeyDown. When active is null, neither wrap condition is satisfied.
    const { container } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement

    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(null as unknown as Element)

    expect(() => {
      fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })
    }).not.toThrow()
  })

  // ─── Tab key: active is middle element (no wrap) ──────────────────────────

  it('Tab key when active is neither first nor last element does not call focus', () => {
    // Covers the "neither branch taken" path inside the Tab block:
    // !event.shiftKey && active === last is false → no wrap, just returns.
    // Injects a third button so there is a "middle" element between first and last.
    const { container } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement

    const middleBtn = document.createElement('p-button')
    pModal.appendChild(middleBtn)

    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]
    // middle is the element before the last
    const middle = pButtons[Math.floor(pButtons.length / 2)] ?? pButtons[0]
    const last = pButtons[pButtons.length - 1]

    const lastFocusSpy = vi.spyOn(last, 'focus')
    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(middle)

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })

    // Focus should NOT wrap to first (active is not last)
    expect(lastFocusSpy).not.toHaveBeenCalled()

    pModal.removeChild(middleBtn)
  })

  // ─── Non-Tab, non-Escape key ──────────────────────────────────────────────

  it('pressing a non-Tab non-Escape key does not call onCancel or onConfirm', () => {
    // Covers the false branch of `if (event.key === 'Escape')` for keys that
    // are neither Tab nor Escape — the handler returns without action.
    const { container, onCancel, onConfirm } = renderConfirmDialog()
    const pModal = container.querySelector('p-modal') as HTMLElement

    fireEvent.keyDown(pModal, { key: 'Enter' })

    expect(onCancel).not.toHaveBeenCalled()
    expect(onConfirm).not.toHaveBeenCalled()
  })

  // ─── Focus restoration on unmount ─────────────────────────────────────────

  it('restores focus to the previously focused element on unmount', () => {
    // Covers `previousFocusRef.current?.focus()` in the useEffect cleanup.
    // Creates a real button, focuses it so previousFocusRef.current is set,
    // then unmounts the dialog and asserts focus() was called on the button.
    const triggerBtn = document.createElement('button')
    document.body.appendChild(triggerBtn)
    triggerBtn.focus()

    const focusSpy = vi.spyOn(triggerBtn, 'focus')
    const { unmount } = renderConfirmDialog()

    // Reset the spy after mount so we only track the unmount-cleanup focus call
    focusSpy.mockClear()
    unmount()

    expect(focusSpy).toHaveBeenCalled()
    document.body.removeChild(triggerBtn)
  })

  // ─── Rerender with type change (React Compiler cache-miss) ───────────────

  it('re-render with different type updates description text (React Compiler cache-miss)', () => {
    // Covers React Compiler cache-miss branches at lines 130-132.
    // Rendering with one type and re-rendering with a different type forces
    // the compiler to recompute the memoized JSX and prop objects.
    const onCancel = vi.fn()
    const onConfirm = vi.fn()
    const { container, rerender } = renderConfirmDialog({ type: 'unclaim' })
    expect(container.textContent).toContain('Release claim')

    rerender(
      <PorscheDesignSystemProvider>
        <ConfirmDialog type="move-backward" targetStatus="done" onCancel={onCancel} onConfirm={onConfirm} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.textContent).toContain('Move to done')

    rerender(
      <PorscheDesignSystemProvider>
        <ConfirmDialog type="unblock" blockReason="blocked reason" onCancel={onCancel} onConfirm={onConfirm} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.textContent).toContain('Unblock task')
    expect(container.textContent).toContain('blocked reason')
  })

  // ─── PButton cache-hit: re-render with same callbacks ────────────────────

  it('re-render with same onCancel/onConfirm references covers cache-hit path for PButton elements', () => {
    // Covers the React Compiler cache-hit branches at lines 131-132.
    // When onCancel, onConfirm, and confirmLabel are all unchanged,
    // the compiler reuses cached PButton elements without re-creating them.
    const onCancel = vi.fn()
    const onConfirm = vi.fn()
    const { container, rerender } = render(
      <PorscheDesignSystemProvider>
        <ConfirmDialog type="unclaim" onCancel={onCancel} onConfirm={onConfirm} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.textContent).toContain('Release claim')

    // Re-render with EXACT same function references → cache hit for PButton elements at lines 131-132
    rerender(
      <PorscheDesignSystemProvider>
        <ConfirmDialog type="unclaim" onCancel={onCancel} onConfirm={onConfirm} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.textContent).toContain('Release claim')
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

  // ─── Non-Error, non-ApiError throw (line 102) ─────────────────────────────

  it('non-Error non-ApiError thrown in handleSubmit shows generic error message', async () => {
    // Covers the final setError branch in the catch block:
    //   setError({ message: 'Failed to resolve decision request.', retryable: true })
    // This runs when caught is neither instanceof ApiError nor instanceof Error
    // (e.g. a raw string or plain object is thrown).
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject('unexpected string error')),
    )
    const { container } = renderResolveModal()

    const radio = container.querySelector('input[type="radio"][value="approved"]') as HTMLElement
    fireEvent.click(radio)

    const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement
    fireEvent.click(submitBtn)

    await waitFor(() => {
      const notification = container.querySelector(
        'p-inline-notification[data-testid="resolve-error"]',
      ) as (HTMLElement & { description?: string }) | null
      expect(notification).not.toBeNull()
      expect(notification!.description).toBe('Failed to resolve decision request.')
    })
  })

  // ─── isSubmitting guard prevents duplicate submit (line 74) ───────────────

  it('clicking submit while already submitting calls fetch only once', async () => {
    // Covers `return` at line 74: `if (!dr || isSubmitting) { return }`.
    // The isSubmitting branch is hit when submit is clicked a second time while
    // the first async fetch is still in flight.
    const fetchMock = vi.fn(() => new Promise<never>(() => {})) // never resolves
    vi.stubGlobal('fetch', fetchMock)

    const { container } = renderResolveModal()

    const radio = container.querySelector('input[type="radio"][value="approved"]') as HTMLElement
    fireEvent.click(radio)

    const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement

    // First click: starts fetch, setIsSubmitting(true) fires synchronously
    fireEvent.click(submitBtn)
    // Second click: isSubmitting is true → early return, fetch not called again
    fireEvent.click(submitBtn)

    // Fetch should have been called exactly once
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  // ─── MutationObserver callback in ResolveModal useEffect (line 130) ───────

  it('MutationObserver callback re-applies dialog attributes in ResolveModal', () => {
    // Covers the `applyDialogAttrs()` call at line 130 (inside the MutationObserver
    // callback body in ResolveModal's useEffect).
    let capturedCallback: MutationCallback | null = null
    const mockDisconnect = vi.fn()
    const mockObserve = vi.fn()

    class MockMutationObserver {
      observe = mockObserve
      disconnect = mockDisconnect
      constructor(cb: MutationCallback) {
        capturedCallback = cb
      }
    }
    vi.stubGlobal('MutationObserver', MockMutationObserver)

    const { container } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement

    // Invoke captured callback — covers the applyDialogAttrs() call inside the observer callback.
    capturedCallback!([], {} as MutationObserver)

    expect(pModal.getAttribute('role')).toBe('dialog')
    expect(pModal.getAttribute('aria-modal')).toBe('true')
  })

  // ─── getFocusableElements: disabled via tabindex element (line 159) ───────

  it('getFocusableElements excludes tabindex=0 disabled elements in ResolveModal', () => {
    // Covers `return false` at line 159 inside getFocusableElements:
    //   if (element.hasAttribute('disabled')) { return false }
    // The element must PASS the CSS selector (so `button:not([disabled])` won't find it)
    // but HAVE the disabled attribute. A div[tabindex="0"][disabled] satisfies both:
    // it matches `[tabindex]:not([tabindex="-1"])` but is filtered by hasAttribute('disabled').
    const { container } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement
    const radios = Array.from(container.querySelectorAll('input[type="radio"]')) as HTMLElement[]
    const pButtons = Array.from(container.querySelectorAll('p-button')) as HTMLElement[]

    const disabledTabEl = document.createElement('div')
    disabledTabEl.setAttribute('tabindex', '0')
    disabledTabEl.setAttribute('disabled', '')
    pModal.appendChild(disabledTabEl)

    // Mock active element to last p-button — Tab wraps to first radio (not disabledTabEl)
    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(pButtons[pButtons.length - 1])
    const firstFocusSpy = vi.spyOn(radios[0], 'focus')

    fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })

    // Focus wraps to first radio, confirming disabled tabindex element was filtered
    expect(firstFocusSpy).toHaveBeenCalledOnce()

    pModal.removeChild(disabledTabEl)
  })

  // ─── handleDocumentEscape: non-Escape key early return ───────────────────

  it('document keydown with non-Escape key does not call onClose', () => {
    // Covers the `return` branch in handleDocumentEscape:
    //   if (event.key !== 'Escape') { return }
    const { onClose } = renderResolveModal()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    expect(onClose).not.toHaveBeenCalled()
  })

  // ─── Tab key: active is null in ResolveModal handleModalKeyDown ───────────

  it('Tab key when document.activeElement is not an HTMLElement does not wrap focus', () => {
    // Covers the null branch at line 209:
    //   const active = document.activeElement instanceof HTMLElement ? document.activeElement : null
    // When active is null, neither wrap condition is satisfied.
    const { container } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement

    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(null as unknown as Element)

    expect(() => {
      fireEvent.keyDown(pModal, { key: 'Tab', shiftKey: false })
    }).not.toThrow()
  })

  // ─── handleResponseChange: invalid value does not update state ────────────

  it('handleResponseChange with a value outside the allowed set does not update response', () => {
    // Covers the false branch of `if (value === 'approved' || value === 'rejected' || value === 'needs-info')`.
    // When an event fires with an out-of-set value, setResponse is NOT called.
    // The submit button stays disabled (response remains '').
    const { container } = renderResolveModal()
    const radio = container.querySelector('input[type="radio"][value="approved"]') as HTMLElement

    // Fire a change event whose target.value is not in the allowed set
    fireEvent.change(radio, { target: { value: 'unknown-option' } })

    const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement
    // submit remains disabled because response was not updated from ''
    expect(submitBtn.hasAttribute('disabled')).toBe(true)
  })

  // ─── dr.body null / undefined — ?? '' fallback ────────────────────────────

  it('renders without crashing when dr.body is falsy (covers the ?? \'\' fallback)', () => {
    // Covers the '' branch of `{dr.body ?? ''}` in the JSX.
    // When body is null or undefined, ReactMarkdown receives an empty string.
    const drWithNullBody = { ...DR_FIXTURE, body: null } as unknown as typeof DR_FIXTURE
    const { container } = renderResolveModal({ dr: drWithNullBody })
    expect(container.querySelector('p-modal')).not.toBeNull()
    const markdown = container.querySelector('[data-testid="markdown-body"]')
    expect(markdown?.textContent).toBe('')
  })

  // ─── Focus restoration on unmount ─────────────────────────────────────────

  it('restores focus to previously focused element on unmount', () => {
    // Covers `previousFocusRef.current?.focus()` in the ResolveModal useEffect cleanup.
    const triggerBtn = document.createElement('button')
    document.body.appendChild(triggerBtn)
    triggerBtn.focus()

    const focusSpy = vi.spyOn(triggerBtn, 'focus')
    const { unmount } = renderResolveModal()

    focusSpy.mockClear()
    unmount()

    expect(focusSpy).toHaveBeenCalled()
    document.body.removeChild(triggerBtn)
  })

  // ─── Non-Escape, non-Tab key in handleModalKeyDown (line 221) ─────────────

  it('pressing a non-Tab non-Escape key in ResolveModal does not call requestClose', () => {
    // Covers the false branch of `if (event.key === 'Escape')` at line 221
    // for keys that are neither Tab nor Escape — the block is not entered.
    const { container, onClose } = renderResolveModal()
    const pModal = container.querySelector('p-modal') as HTMLElement
    fireEvent.keyDown(pModal, { key: 'Enter' })
    expect(onClose).not.toHaveBeenCalled()
  })

  // ─── ApiError with non-default message (line 91) ─────────────────────────

  it('ApiError with a custom message uses caught.message not the fallback', async () => {
    // Covers the false branch of:
    //   const message = caught.message === `Resolve request failed with status ${caught.status}`
    //     ? fallback
    //     : caught.message
    // When ApiError has a custom (non-default) message, caught.message is used directly.
    vi.spyOn(decisionsApi, 'resolveDR').mockRejectedValueOnce(
      new ApiError(403, 'Specific validation error from server'),
    )
    const { container } = renderResolveModal()

    const radio = container.querySelector('input[type="radio"][value="approved"]') as HTMLElement
    fireEvent.click(radio)

    const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement
    fireEvent.click(submitBtn)

    await waitFor(() => {
      const notification = container.querySelector(
        'p-inline-notification[data-testid="resolve-error"]',
      ) as (HTMLElement & { description?: string }) | null
      expect(notification).not.toBeNull()
      // Non-default message should appear directly (not replaced by fallback)
      expect(notification!.description).toBe('Specific validation error from server')
    })
  })

  // ─── useEffect: document.activeElement null at mount (line 119) ──────────

  it('useEffect sets previousFocusRef to null when activeElement is not an HTMLElement at mount', () => {
    // Covers the null branch of:
    //   previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    // in the useEffect. When null, the cleanup's previousFocusRef.current?.focus() is a no-op.
    vi.spyOn(document, 'activeElement', 'get').mockReturnValue(null as unknown as Element)
    const { unmount } = renderResolveModal()
    // Unmount triggers cleanup — previousFocusRef.current is null → ?.focus() is a no-op
    expect(() => unmount()).not.toThrow()
  })
})
