/**
 * Workflow behavior tests1396 AC7: RepairPanel confirm-dialog focus management
 *
 * AC7 requires proving the same 4-assertion pattern as DRFocusMgmt_1396.test.tsx
 * for the RepairPanel confirm dialog (data-testid="repair-confirm-dialog"):
 *   — focus-on-open: when phase becomes 'confirming', focus moves inside the dialog
 *   — Escape on element: pressing Escape on the dialog element calls cancelRepair
 *   — Escape on document: pressing Escape on document calls cancelRepair
 *   — focus-restore: when phase leaves 'confirming', focus returns to the prior element
 *
 * Implementation surface: serve/cockpit/web/src/components/RepairPanel.tsx:23,35-42,51,54,58
 * Pattern: same 4-assertion structure as DRFocusMgmt_1396.test.tsx (HealthBadge/DR parity).
 *
 * RED reasons:
 *   — Escape on document (test 3): RepairPanel.tsx has no document-level keydown listener.
 *     The onKeyDown at line 54 only fires when the dialog element itself receives the event.
 *     This test FAILS until a document listener matching the HealthBadge/DRStatusIndicator
 *     pattern is added.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { UseRepairFlowResult } from '../hooks/useRepairFlow'

// ─── Module mock ──────────────────────────────────────────────────────────────

vi.mock('../hooks/useRepairFlow', () => ({
  useRepairFlow: vi.fn(),
}))

import { useRepairFlow } from '../hooks/useRepairFlow'
import RepairPanel from '../components/RepairPanel'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function hookDefaults(): UseRepairFlowResult {
  return {
    phase: 'idle',
    corruptionCount: null,
    results: null,
    error: null,
    requestRepair: vi.fn(),
    confirmRepair: vi.fn(),
    cancelRepair: vi.fn(),
    dismissResults: vi.fn(),
  }
}

function mockHook(overrides: Partial<UseRepairFlowResult> = {}): UseRepairFlowResult {
  const merged = { ...hookDefaults(), ...overrides }
  vi.mocked(useRepairFlow).mockReturnValue(merged)
  return merged
}

function renderPanel(corruptionCount = 2) {
  return render(
    <PorscheDesignSystemProvider>
      <RepairPanel corruptionCount={corruptionCount} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── AC7: TestFromAC_RepairPanelFocus ─────────────────────────────────────────
//
// Tests the 4-assertion focus-management contract for the RepairPanel confirm dialog.
// RepairPanel.tsx already implements focus-on-open (line 42), Escape-on-element (line 54),
// and focus-restore (line 38), but LACKS a document-level Escape listener.
// Test 3 (Escape on document) FAILS against the current implementation.

describe('TestFromAC_RepairPanelFocus', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('opening repair confirm dialog moves focus inside the dialog (AC7)', () => {
    // When phase becomes 'confirming', the dialog must receive programmatic focus so keyboard
    // users land inside the confirm dialog region.
    // RepairPanel.tsx:35-42 implements this via dialogRef.current?.focus() in useEffect.
    const focusCalls: HTMLElement[] = []
    const origFocus = HTMLElement.prototype.focus
    HTMLElement.prototype.focus = function (this: HTMLElement) {
      focusCalls.push(this)
      return origFocus.call(this)
    }
    try {
      mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { container } = renderPanel()
      const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
      expect(dialog, 'confirm dialog must be rendered in confirming phase').not.toBeNull()

      const focusedInsideDialog = focusCalls.some(
        (el) => el === dialog || dialog!.contains(el),
      )
      expect(focusedInsideDialog, 'focus must move inside the confirm dialog on open').toBe(true)
    } finally {
      HTMLElement.prototype.focus = origFocus
    }
  })

  it('pressing Escape on repair confirm dialog element calls cancelRepair (AC7)', () => {
    // WCAG 2.1 SC 1.4.13: the confirm dialog must be dismissible via Escape without
    // requiring pointer interaction. RepairPanel.tsx:54-60 implements onKeyDown Escape.
    const hook = mockHook({ phase: 'confirming', corruptionCount: 2 })
    const { container } = renderPanel()
    const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]') as HTMLElement
    expect(dialog, 'confirm dialog must be present in confirming phase').not.toBeNull()

    fireEvent.keyDown(dialog, { key: 'Escape', code: 'Escape' })

    expect(
      hook.cancelRepair,
      'cancelRepair must be called when Escape is pressed on the dialog element',
    ).toHaveBeenCalledOnce()
  })

  it('pressing Escape on document while confirm dialog is open calls cancelRepair (AC7)', () => {
    // Global Escape handler is required for dialogs that receive programmatic focus.
    // When focus moves inside the dialog, keyboard events go to the focused element, not
    // the dialog div — so a document-level listener is the safety net (same pattern as
    // HealthBadge.tsx and DRStatusIndicator.tsx).
    //
    // FAILS: RepairPanel has no document-level keydown listener → cancelRepair not called.
    const hook = mockHook({ phase: 'confirming', corruptionCount: 2 })
    renderPanel()

    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })

    // FAILS: no document-level Escape listener in RepairPanel.tsx
    expect(
      hook.cancelRepair,
      'cancelRepair must be called when Escape is pressed at document level',
    ).toHaveBeenCalledOnce()
  })

  it('closing repair confirm dialog restores focus to the previously-focused element (AC7)', () => {
    // WCAG 2.1 SC 3.2.2: when a dialog closes, focus must return to the element that
    // opened it. RepairPanel.tsx:37-41 implements this via previousFocusRef in useEffect.
    const focusCalls: HTMLElement[] = []
    const origFocus = HTMLElement.prototype.focus
    HTMLElement.prototype.focus = function (this: HTMLElement) {
      focusCalls.push(this)
      return origFocus.call(this)
    }
    try {
      // Establish a prior focused element that RepairPanel should restore focus to.
      const previouslyFocused = document.createElement('button')
      previouslyFocused.setAttribute('data-testid', 'repair-trigger-sentinel')
      document.body.appendChild(previouslyFocused)
      previouslyFocused.focus()

      // Open: render in confirming phase — useEffect captures document.activeElement
      // (previouslyFocused) and calls dialogRef.current?.focus().
      mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { rerender } = renderPanel()

      // Reset spy — only capture focus calls that happen during the close transition.
      focusCalls.length = 0

      // Close: re-render with a non-confirming phase — useEffect calls previousFocusRef.current?.focus().
      mockHook({ phase: 'idle' })
      act(() => {
        rerender(
          <PorscheDesignSystemProvider>
            <RepairPanel corruptionCount={2} />
          </PorscheDesignSystemProvider>,
        )
      })

      const focusReturnedToPrevious = focusCalls.some((el) => el === previouslyFocused)
      expect(
        focusReturnedToPrevious,
        'focus must be restored to the previously-focused element when the confirm dialog closes',
      ).toBe(true)

      document.body.removeChild(previouslyFocused)
    } finally {
      HTMLElement.prototype.focus = origFocus
    }
  })
})
