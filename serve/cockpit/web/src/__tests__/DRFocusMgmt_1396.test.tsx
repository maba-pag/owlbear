/**
 * Workflow behavior tests1396: P3-06 Implement Cockpit accessibility and PDS verification gate
 *
 * Scope: DRStatusIndicator popover focus management parity with HealthBadge.
 *
 * AC2 explicitly lists DRStatusIndicator as requiring focus-on-open, Escape dismissal,
 * and focus-restore-on-close. The architect annotated AC2 as (td:0) on the basis that
 * "tests exist in #1395", but KeyboardA11y_1395.test.tsx contains NO DRStatusIndicator
 * focus management tests. These tests fill that gap to give the builder concrete failing
 * evidence.
 *
 * RED reasons:
 *   — DRStatusIndicator.tsx has no useRef for the popover, no focus-on-open call,
 *     no onKeyDown or document-level Escape handler, and no focus-restore on close.
 *   — All four assertions below fail against the current implementation.
 *
 * Implementation task: #1396.
 * Counterpart for the pattern: KeyboardA11y_1395.test.tsx (HealthBadge section).
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DRStatusIndicator from '../components/DRStatusIndicator'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const DR_FIXTURE: PendingDR = {
  id: 'dr-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  title: 'Should we use approach A?',
  body: 'Full context for the decision.',
  body_preview: 'Context: the builder encountered a fork...',
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderDR(items: PendingDR[] = [DR_FIXTURE]) {
  return render(
    <PorscheDesignSystemProvider>
      <DRStatusIndicator count={items.length} items={items} onItemClick={vi.fn()} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── AC2: TestFromAC_DRStatusIndicatorFocus ───────────────────────────────────
//
// DRStatusIndicator.tsx currently has no focus management:
//   — No useRef for the popover, no focus() call when isOpen becomes true.
//   — No onKeyDown on the popover element, no document-level Escape listener.
//   — No trigger ref, no focus-restore when the popover closes.
//
// Required fix: apply the same pattern as HealthBadge (focus-on-open via useEffect +
// popoverRef.focus(); Escape via useEffect document listener; focus-restore via
// triggerRef.focus() in close path).

describe('TestFromAC_DRStatusIndicatorFocus', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('opening DR popover moves focus inside the popover (AC2)', () => {
    // After clicking the trigger, the popover must receive programmatic focus so keyboard
    // users land inside the dialog region. Currently DRStatusIndicator has no focus call.
    const focusCalls: HTMLElement[] = []
    const origFocus = HTMLElement.prototype.focus
    HTMLElement.prototype.focus = function (this: HTMLElement) {
      focusCalls.push(this)
      return origFocus.call(this)
    }
    try {
      const { container } = renderDR()
      const trigger = container.querySelector('[data-testid="dr-indicator"]') as HTMLElement
      expect(trigger, 'dr-indicator trigger must be rendered').not.toBeNull()

      fireEvent.click(trigger)

      const popover = container.querySelector('[data-testid="dr-popover"]')
      expect(popover, 'popover must be present after clicking trigger').not.toBeNull()

      const focusedInsidePopover = focusCalls.some(
        (el) => el === popover || popover!.contains(el),
      )
      // FAILS: DRStatusIndicator has no focus-on-open mechanism → focusCalls is empty or
      // does not include the popover element.
      expect(focusedInsidePopover).toBe(true)
    } finally {
      HTMLElement.prototype.focus = origFocus
    }
  })

  it('pressing Escape on DR popover element closes the popover (AC2)', () => {
    // WCAG 2.1 SC 1.4.13: the popover must be dismissible via Escape without moving focus.
    // Currently DRStatusIndicator has no onKeyDown on the popover → Escape does nothing.
    const { container } = renderDR()
    const trigger = container.querySelector('[data-testid="dr-indicator"]') as HTMLElement

    fireEvent.click(trigger)
    expect(
      container.querySelector('[data-testid="dr-popover"]'),
      'popover must be open before Escape test',
    ).not.toBeNull()

    const popover = container.querySelector('[data-testid="dr-popover"]') as HTMLElement
    fireEvent.keyDown(popover, { key: 'Escape', code: 'Escape' })

    // FAILS: no onKeyDown Escape handler on the popover element → popover stays open
    expect(container.querySelector('[data-testid="dr-popover"]')).toBeNull()
  })

  it('pressing Escape on document while DR popover is open closes the popover (AC2)', () => {
    // Global Escape handler is required for popovers that trap or move focus inside them.
    // Currently DRStatusIndicator has no document-level keydown listener.
    const { container } = renderDR()
    const trigger = container.querySelector('[data-testid="dr-indicator"]') as HTMLElement

    fireEvent.click(trigger)
    expect(
      container.querySelector('[data-testid="dr-popover"]'),
      'popover must be open',
    ).not.toBeNull()

    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })

    // FAILS: no document-level Escape listener → popover persists
    expect(container.querySelector('[data-testid="dr-popover"]')).toBeNull()
  })

  it('closing DR popover restores focus to the trigger button (AC2)', () => {
    // When a dialog/popover closes, WCAG 2.1 SC 3.2.2 requires focus to return to the
    // element that opened it. DRStatusIndicator currently has no focus-restore mechanism.
    const focusCalls: HTMLElement[] = []
    const origFocus = HTMLElement.prototype.focus
    HTMLElement.prototype.focus = function (this: HTMLElement) {
      focusCalls.push(this)
      return origFocus.call(this)
    }
    try {
      const { container } = renderDR()
      const trigger = container.querySelector('[data-testid="dr-indicator"]') as HTMLElement

      // Open
      fireEvent.click(trigger)
      expect(container.querySelector('[data-testid="dr-popover"]')).not.toBeNull()

      // Reset spy — only capture focus calls that happen during close
      focusCalls.length = 0

      // Close via toggle click (same trigger)
      fireEvent.click(trigger)
      expect(
        container.querySelector('[data-testid="dr-popover"]'),
        'popover must be closed after second click',
      ).toBeNull()

      // Focus must have returned to the trigger after closing
      const focusReturnedToTrigger = focusCalls.some(
        (el) => el === trigger || trigger.contains(el),
      )
      // FAILS: DRStatusIndicator has no focus-restore code → focusCalls is empty
      expect(focusReturnedToTrigger).toBe(true)
    } finally {
      HTMLElement.prototype.focus = origFocus
    }
  })
})
