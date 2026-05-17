/**
 * Tests for #1618 — P2-11: Complex integrations — modals → PModal
 *
 * Revised AC (post architect refinement, 2026-05-17):
 *
 * AC-1: ConfirmDialog, ResolveModal, and ArchivalModal render via PModal host element;
 *       legacy modal infrastructure removed: no div[role=dialog] wrapper, no
 *       position:fixed overlay, no inline z-index.
 *
 * AC-2: PDS host-level workarounds permitted for documented PModal limitations:
 *       (1) Tab-cycling shim for slotted light-DOM focus trapping,
 *       (2) focus-state capture/restore for close-path variants,
 *       (3) host attribute normalization (role, aria-modal) via MutationObserver.
 *
 * AC-3: Focus behavior preserved per modal:
 *       (a) all three trap Tab within modal boundary on open
 *       (b) ResolveModal returns focus to DR trigger button on close
 *       (c) ArchivalModal returns focus to originating task card on close via
 *           PModal onDismiss + explicit fallback target
 *       (d) ConfirmDialog returns focus to the action button that opened it
 *
 * AC-4: Dismiss policy per modal:
 *       ConfirmDialog — role=alertdialog, disableBackdropClick=true, dismissButton=false
 *       ResolveModal and ArchivalModal — all dismiss methods allowed
 */
import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ConfirmDialog from '../components/ConfirmDialog'
import ResolveModal from '../components/ResolveModal'
import ArchivalModal from '../components/ArchivalModal'
import type { PendingDRWithBody } from '../components/ResolveModal'

// ─── PDS Stencil form-component workaround ───────────────────────────────────
// PDS Stencil form components (p-select, p-input-text, p-textarea) call
// attachInternals() on mount. Newer jsdom versions expose a partial stub that
// lacks setFormValue, causing throws. Override unconditionally.
beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

// ─── react-markdown mock (required by ResolveModal) ──────────────────────────
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const DR_FIXTURE: PendingDRWithBody = {
  id: 'dr-1618-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: '2026-05-01T10:00:00Z',
  title: 'Confirm caching approach',
  body_preview: 'Builder needs guidance on caching.',
  body: '## Context\n\nShould we use Redis or in-memory cache?',
}

// ─── Types ────────────────────────────────────────────────────────────────────

type PModalElement = HTMLElement & {
  open?: boolean
  disableBackdropClick?: boolean
  dismissButton?: boolean
  aria?: { role?: string }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getPModal(container: HTMLElement): PModalElement | null {
  return container.querySelector('p-modal') as PModalElement | null
}

/** True if any descendant has `position: fixed` as an inline style. */
function hasFixedPositionStyle(container: HTMLElement): boolean {
  return Array.from(container.querySelectorAll('*')).some(
    (el) => (el as HTMLElement).style?.position === 'fixed',
  )
}

/** True if any descendant has an inline z-index style set. */
function hasInlineZIndexStyle(container: HTMLElement): boolean {
  return Array.from(container.querySelectorAll('*')).some(
    (el) => !!(el as HTMLElement).style?.zIndex,
  )
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
  onClose?: () => void
  onResolved?: () => void
} = {}) {
  const onClose = overrides.onClose ?? vi.fn()
  const onResolved = overrides.onResolved ?? vi.fn()
  const utils = render(
    <PorscheDesignSystemProvider>
      <ResolveModal dr={DR_FIXTURE} onClose={onClose} onResolved={onResolved} />
    </PorscheDesignSystemProvider>,
  )
  return { ...utils, onClose, onResolved }
}

function renderArchivalModal(overrides: {
  onClose?: () => void
  onRefresh?: () => void
  returnFocusTo?: HTMLElement | null
} = {}) {
  const onClose = overrides.onClose ?? vi.fn()
  const onRefresh = overrides.onRefresh ?? vi.fn()
  const utils = render(
    <PorscheDesignSystemProvider>
      <ArchivalModal
        taskId={42}
        taskStatus="in-progress"
        expectedUpdated="2026-05-01T10:00:00+00:00"
        returnFocusTo={overrides.returnFocusTo ?? null}
        onClose={onClose}
        onRefresh={onRefresh}
      />
    </PorscheDesignSystemProvider>,
  )
  return { ...utils, onClose, onRefresh }
}

// ─────────────────────────────────────────────────────────────────────────────
// AC-1: ConfirmDialog renders via PModal — no hand-rolled overlay
// ─────────────────────────────────────────────────────────────────────────────

describe('TestFromAC_PModalMigration', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('AC1: ConfirmDialog — renders via p-modal, overlay code removed', () => {
    it('renders a p-modal custom element as the dialog container', () => {
      // Current code: <div role="dialog" style="position:fixed"> → FAIL
      const { container } = renderConfirmDialog()
      expect(getPModal(container)).not.toBeNull()
    })

    it('does not render a hand-rolled div[role="dialog"] wrapper', () => {
      // Current code: div with role="dialog" exists → FAIL
      const { container } = renderConfirmDialog()
      expect(container.querySelector('div[role="dialog"]')).toBeNull()
    })

    it('has no element with position:fixed as an inline style', () => {
      const { container } = renderConfirmDialog()
      expect(hasFixedPositionStyle(container)).toBe(false)
    })

    it('has no element with an inline z-index style', () => {
      // AC-1: no inline z-index — legacy overlay used zIndex: 1000
      const { container } = renderConfirmDialog()
      expect(hasInlineZIndexStyle(container)).toBe(false)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────
  // AC-1: ResolveModal renders via PModal — no hand-rolled overlay
  // ─────────────────────────────────────────────────────────────────────────

  describe('AC1: ResolveModal — renders via p-modal, overlay code removed', () => {
    it('renders a p-modal custom element as the dialog container', () => {
      // Current code: <div role="dialog" ref={modalRef} style="position:fixed"> → FAIL
      const { container } = renderResolveModal()
      expect(getPModal(container)).not.toBeNull()
    })

    it('does not render a hand-rolled div[role="dialog"] wrapper', () => {
      const { container } = renderResolveModal()
      expect(container.querySelector('div[role="dialog"]')).toBeNull()
    })

    it('has no element with position:fixed as an inline style', () => {
      const { container } = renderResolveModal()
      expect(hasFixedPositionStyle(container)).toBe(false)
    })

    it('has no element with an inline z-index style', () => {
      // AC-1: no inline z-index — legacy overlay used zIndex: 1000
      const { container } = renderResolveModal()
      expect(hasInlineZIndexStyle(container)).toBe(false)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────
  // AC-1: ArchivalModal renders via PModal — no hand-rolled overlay
  // ─────────────────────────────────────────────────────────────────────────

  describe('AC1: ArchivalModal — renders via p-modal, overlay code removed', () => {
    it('renders a p-modal custom element as the dialog container', () => {
      // Current code: <div role="dialog" onKeyDown={handleKeyDown} style="position:fixed"> → FAIL
      const { container } = renderArchivalModal()
      expect(getPModal(container)).not.toBeNull()
    })

    it('does not render a hand-rolled div[role="dialog"] wrapper', () => {
      const { container } = renderArchivalModal()
      expect(container.querySelector('div[role="dialog"]')).toBeNull()
    })

    it('has no element with position:fixed as an inline style', () => {
      const { container } = renderArchivalModal()
      expect(hasFixedPositionStyle(container)).toBe(false)
    })

    it('has no element with an inline z-index style', () => {
      // AC-1: no inline z-index — legacy overlay used zIndex: 1000
      const { container } = renderArchivalModal()
      expect(hasInlineZIndexStyle(container)).toBe(false)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────
  // AC-4: ConfirmDialog dismiss policy — alertdialog pattern
  // ─────────────────────────────────────────────────────────────────────────

  describe('AC4: ConfirmDialog — alertdialog dismiss policy', () => {
    it('p-modal is open when ConfirmDialog is mounted', () => {
      // PModal must receive open={true}; current code has no p-modal → FAIL
      const { container } = renderConfirmDialog()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.open).toBe(true)
    })

    it('p-modal has alertdialog aria role (role=alertdialog)', () => {
      // ConfirmDialog must pass aria={{ role: 'alertdialog' }} to PModal → FAIL
      const { container } = renderConfirmDialog()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.aria?.role).toBe('alertdialog')
    })

    it('p-modal has disableBackdropClick set to true', () => {
      // AlertDialog pattern: backdrop click must not dismiss → FAIL
      const { container } = renderConfirmDialog()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.disableBackdropClick).toBe(true)
    })

    it('p-modal has dismissButton set to false (no X button)', () => {
      // AlertDialog pattern: no dismiss-button (Escape + Cancel/Confirm only) → FAIL
      const { container } = renderConfirmDialog()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.dismissButton).toBe(false)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────
  // AC-3: ResolveModal dismiss policy — all dismiss methods allowed
  // ─────────────────────────────────────────────────────────────────────────

  describe('AC4: ResolveModal — full dismiss policy', () => {
    it('p-modal is open when ResolveModal is mounted', () => {
      const { container } = renderResolveModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.open).toBe(true)
    })

    it('p-modal does not have disableBackdropClick set to true (backdrop click allowed)', () => {
      // ResolveModal allows all dismiss methods → FAIL (no p-modal in current code)
      const { container } = renderResolveModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.disableBackdropClick).not.toBe(true)
    })

    it('p-modal does not have dismissButton set to false (X dismiss button visible)', () => {
      // ResolveModal allows all dismiss methods → FAIL (no p-modal in current code)
      const { container } = renderResolveModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.dismissButton).not.toBe(false)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────
  // AC-3: ArchivalModal dismiss policy — all dismiss methods allowed
  // ─────────────────────────────────────────────────────────────────────────

  describe('AC4: ArchivalModal — full dismiss policy', () => {
    it('p-modal is open when ArchivalModal is mounted', () => {
      const { container } = renderArchivalModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.open).toBe(true)
    })

    it('p-modal does not have disableBackdropClick set to true (backdrop click allowed)', () => {
      // ArchivalModal allows all dismiss methods → FAIL (no p-modal in current code)
      const { container } = renderArchivalModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.disableBackdropClick).not.toBe(true)
    })

    it('p-modal does not have dismissButton set to false (X dismiss button visible)', () => {
      // ArchivalModal allows all dismiss methods → FAIL (no p-modal in current code)
      const { container } = renderArchivalModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      expect(pModal!.dismissButton).not.toBe(false)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────
  // AC-2: ConfirmDialog dismiss event — onCancel wired to PModal dismiss
  // ─────────────────────────────────────────────────────────────────────────

  describe('AC3/AC4: ConfirmDialog — dismiss event calls onCancel', () => {
    it('dispatching dismiss event on p-modal calls onCancel', () => {
      // AC-2(d): dismiss (Escape) must call onCancel.
      // Current code: no p-modal → getPModal returns null → expect .not.toBeNull() fails → FAIL
      const { container, onCancel } = renderConfirmDialog()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      fireEvent(pModal!, new CustomEvent('dismiss', { bubbles: true }))
      expect(onCancel).toHaveBeenCalledOnce()
    })

    it('dispatching dismiss event on p-modal does not call onConfirm', () => {
      // Dismiss (Escape / backdrop) must not trigger the confirm action
      const { container, onConfirm } = renderConfirmDialog()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      fireEvent(pModal!, new CustomEvent('dismiss', { bubbles: true }))
      expect(onConfirm).not.toHaveBeenCalled()
    })

    it('ConfirmDialog type=move-backward dismiss event calls onCancel', () => {
      // Verify dismiss policy is consistent across all ConfirmDialog type variants
      const { container, onCancel } = renderConfirmDialog({ type: 'move-backward', targetStatus: 'todo' })
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      fireEvent(pModal!, new CustomEvent('dismiss', { bubbles: true }))
      expect(onCancel).toHaveBeenCalledOnce()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────
  // AC-2: ResolveModal dismiss event — onClose wired to PModal dismiss
  // ─────────────────────────────────────────────────────────────────────────

  describe('AC3/AC4: ResolveModal — dismiss event calls onClose', () => {
    it('dispatching dismiss event on p-modal calls onClose', () => {
      // AC-2(b): dismiss (Escape, backdrop, X) returns focus to DR trigger and closes modal.
      // Current code: no p-modal → FAIL
      const { container, onClose } = renderResolveModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      fireEvent(pModal!, new CustomEvent('dismiss', { bubbles: true }))
      expect(onClose).toHaveBeenCalledOnce()
    })

    it('dispatching dismiss event on p-modal does not call onResolved', () => {
      // Dismiss must not be treated as a successful resolution
      const { container, onResolved } = renderResolveModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      fireEvent(pModal!, new CustomEvent('dismiss', { bubbles: true }))
      expect(onResolved).not.toHaveBeenCalled()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────
  // AC-2: ArchivalModal dismiss event — onClose + fallback focus target
  // ─────────────────────────────────────────────────────────────────────────

  describe('AC3/AC4: ArchivalModal — dismiss event calls onClose', () => {
    it('dispatching dismiss event on p-modal calls onClose', () => {
      // AC-2(c): dismiss closes modal and returns focus.
      // Current code: no p-modal → FAIL
      const { container, onClose } = renderArchivalModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      fireEvent(pModal!, new CustomEvent('dismiss', { bubbles: true }))
      expect(onClose).toHaveBeenCalledOnce()
    })

    it('dispatching dismiss event on p-modal does not call onRefresh', () => {
      // Dismiss must not trigger a board refresh — only successful archival does
      const { container, onRefresh } = renderArchivalModal()
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      fireEvent(pModal!, new CustomEvent('dismiss', { bubbles: true }))
      expect(onRefresh).not.toHaveBeenCalled()
    })

    it('dismiss event focuses fallback target element when returnFocusTo is provided', () => {
      // AC-2(c): context-menu opener is destroyed before modal close; ArchivalModal must
      // explicitly call focus() on the fallback target via PModal onDismiss.
      // Current code: previousFocusRef cleanup fires on unmount, not on dismiss event.
      // After migration: PModal onDismiss handler calls returnFocusTo?.focus() → FAIL now.
      const fallbackEl = document.createElement('button')
      const focusSpy = vi.spyOn(fallbackEl, 'focus')
      document.body.appendChild(fallbackEl)

      const { container } = renderArchivalModal({ returnFocusTo: fallbackEl })
      const pModal = getPModal(container)
      expect(pModal).not.toBeNull()
      fireEvent(pModal!, new CustomEvent('dismiss', { bubbles: true }))
      expect(focusSpy).toHaveBeenCalledOnce()

      document.body.removeChild(fallbackEl)
    })
  })
})
