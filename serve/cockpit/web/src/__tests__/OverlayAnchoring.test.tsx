/**
 * Retry gap-fill for #1569 — overlay anchoring and CleanupPanel modal semantics.
 *
 * AC-1: HealthBadge and DRStatusIndicator popovers are anchored to the trigger
 *       element via getBoundingClientRect(); positioning is not hard-coded.
 * AC-2: CleanupPanel confirm dialog has modal-equivalent semantics:
 *       aria-modal="true", role="dialog", Tab/Shift+Tab focus-trap, focus-return.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { UseCleanupFlowResult, CleanupPhase } from '../hooks/useCleanupFlow'
import HealthBadge from '../components/HealthBadge'
import DRStatusIndicator from '../components/DRStatusIndicator'
import CleanupPanel from '../components/CleanupPanel'

vi.mock('../hooks/useCleanupFlow', () => ({ useCleanupFlow: vi.fn() }))
import { useCleanupFlow } from '../hooks/useCleanupFlow'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const HEALTH_ITEM = { code: 'E001', detail: 'Missing field', file_path: 'src/model.py' }

interface LocalPendingDR {
  id: string
  task_id: number
  agent: string
  request_type: string
  created: string
  title: string
  body_preview: string
}

const DR_ITEM: LocalPendingDR = {
  id: 'dr-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope',
  created: new Date().toISOString(),
  title: 'Confirm scope',
  body_preview: 'Some details',
}

// ─── Render helpers ───────────────────────────────────────────────────────────

function renderHealthBadge() {
  return render(
    <PorscheDesignSystemProvider>
      <HealthBadge items={[HEALTH_ITEM]} />
    </PorscheDesignSystemProvider>,
  )
}

function renderDRIndicator() {
  return render(
    <PorscheDesignSystemProvider>
      <DRStatusIndicator count={1} items={[DR_ITEM] as never} onItemClick={vi.fn()} />
    </PorscheDesignSystemProvider>,
  )
}

function hookBase(overrides: Partial<UseCleanupFlowResult> = {}): UseCleanupFlowResult {
  return {
    phase: 'idle' as CleanupPhase,
    results: null,
    error: null,
    requestCleanup: vi.fn(),
    confirmCleanup: vi.fn(),
    cancelCleanup: vi.fn(),
    dismissResults: vi.fn(),
    ...overrides,
  }
}

function mockHook(overrides: Partial<UseCleanupFlowResult> = {}) {
  vi.mocked(useCleanupFlow).mockReturnValue(hookBase(overrides))
}

function renderCleanupPanel() {
  return render(
    <PorscheDesignSystemProvider>
      <CleanupPanel />
    </PorscheDesignSystemProvider>,
  )
}

// ─── AC-1: HealthBadge trigger-anchored positioning ──────────────────────────

describe('TestFromAC_HealthBadgeTriggerAnchoring', () => {
  it('popover renders with position:fixed style (out-of-flow container)', () => {
    const { container } = renderHealthBadge()
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]') as HTMLElement
    expect(popover.style.position).toBe('fixed')
  })

  it('popover top is anchored below trigger: top = round(trigger.getBoundingClientRect().bottom + 8)', () => {
    const { container } = renderHealthBadge()
    const trigger = container.querySelector('[data-testid="health-badge"]') as HTMLElement
    // Mock getBoundingClientRect so the test would fail if coordinates were hard-coded
    trigger.getBoundingClientRect = vi.fn(
      () =>
        ({ top: 40, bottom: 60, left: 100, right: 200, width: 100, height: 20, x: 100, y: 40, toJSON: vi.fn() }) as DOMRect,
    )
    fireEvent.click(trigger)
    const popover = container.querySelector('[data-testid="health-badge-popover"]') as HTMLElement
    // getAnchoredPopoverPosition: top = Math.round(60 + 8) = 68
    expect(popover.style.top).toBe('68px')
  })

  it('popover left keeps the full popover inside the viewport padding floor', () => {
    const { container } = renderHealthBadge()
    const trigger = container.querySelector('[data-testid="health-badge"]') as HTMLElement
    trigger.getBoundingClientRect = vi.fn(
      () =>
        ({ top: 40, bottom: 60, left: 200, right: 300, width: 100, height: 20, x: 200, y: 40, toJSON: vi.fn() }) as DOMRect,
    )
    fireEvent.click(trigger)
    const popover = container.querySelector('[data-testid="health-badge-popover"]') as HTMLElement
    expect(popover.style.left).toBe('16px')
  })

  it('popover left applies viewport-padding floor (16px) when trigger.left < 16', () => {
    const { container } = renderHealthBadge()
    const trigger = container.querySelector('[data-testid="health-badge"]') as HTMLElement
    trigger.getBoundingClientRect = vi.fn(
      () =>
        ({ top: 40, bottom: 60, left: 4, right: 104, width: 100, height: 20, x: 4, y: 40, toJSON: vi.fn() }) as DOMRect,
    )
    fireEvent.click(trigger)
    const popover = container.querySelector('[data-testid="health-badge-popover"]') as HTMLElement
    // getAnchoredPopoverPosition: left = Math.round(Math.max(16, 4)) = 16
    expect(popover.style.left).toBe('16px')
  })

  it('popover left clamps against the viewport right edge for header triggers', () => {
    const originalInnerWidth = window.innerWidth
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 500 })
    try {
      const { container } = renderHealthBadge()
      const trigger = container.querySelector('[data-testid="health-badge"]') as HTMLElement
      trigger.getBoundingClientRect = vi.fn(
        () =>
          ({ top: 40, bottom: 60, left: 460, right: 500, width: 40, height: 20, x: 460, y: 40, toJSON: vi.fn() }) as DOMRect,
      )
      fireEvent.click(trigger)
      const popover = container.querySelector('[data-testid="health-badge-popover"]') as HTMLElement
      expect(popover.style.left).toBe('64px')
    } finally {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: originalInnerWidth })
    }
  })
})

// ─── AC-1: DRStatusIndicator trigger-anchored positioning ────────────────────

describe('TestFromAC_DRPopoverTriggerAnchoring', () => {
  it('popover renders with position:fixed style (out-of-flow container)', () => {
    const { container } = renderDRIndicator()
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    const popover = container.querySelector('[data-testid="dr-popover"]') as HTMLElement
    expect(popover.style.position).toBe('fixed')
  })

  it('popover top is anchored below trigger: top = round(trigger.getBoundingClientRect().bottom + 8)', () => {
    const { container } = renderDRIndicator()
    const trigger = container.querySelector('[data-testid="dr-indicator"]') as HTMLElement
    trigger.getBoundingClientRect = vi.fn(
      () =>
        ({ top: 20, bottom: 40, left: 50, right: 150, width: 100, height: 20, x: 50, y: 20, toJSON: vi.fn() }) as DOMRect,
    )
    fireEvent.click(trigger)
    const popover = container.querySelector('[data-testid="dr-popover"]') as HTMLElement
    // getAnchoredPopoverPosition: top = Math.round(40 + 8) = 48
    expect(popover.style.top).toBe('48px')
  })

  it('popover left is anchored to trigger left with padding floor: left = round(max(16, trigger.left))', () => {
    const { container } = renderDRIndicator()
    const trigger = container.querySelector('[data-testid="dr-indicator"]') as HTMLElement
    trigger.getBoundingClientRect = vi.fn(
      () =>
        ({ top: 20, bottom: 40, left: 180, right: 280, width: 100, height: 20, x: 180, y: 20, toJSON: vi.fn() }) as DOMRect,
    )
    fireEvent.click(trigger)
    const popover = container.querySelector('[data-testid="dr-popover"]') as HTMLElement
    // getAnchoredPopoverPosition: left = Math.round(Math.max(16, 180)) = 180
    expect(popover.style.left).toBe('180px')
  })

  it('popover left clamps against the viewport right edge for header triggers', () => {
    const originalInnerWidth = window.innerWidth
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 500 })
    try {
      const { container } = renderDRIndicator()
      const trigger = container.querySelector('[data-testid="dr-indicator"]') as HTMLElement
      trigger.getBoundingClientRect = vi.fn(
        () =>
          ({ top: 20, bottom: 40, left: 460, right: 500, width: 40, height: 20, x: 460, y: 20, toJSON: vi.fn() }) as DOMRect,
      )
      fireEvent.click(trigger)
      const popover = container.querySelector('[data-testid="dr-popover"]') as HTMLElement
      expect(popover.style.left).toBe('64px')
    } finally {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: originalInnerWidth })
    }
  })
})

// ─── AC-2: CleanupPanel modal-equivalent semantics ───────────────────────────

describe('TestFromAC_CleanupPanelModalSemantics', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('confirm dialog has aria-modal="true"', () => {
    mockHook({ phase: 'confirming' })
    const { container } = renderCleanupPanel()
    const dialog = container.querySelector('[data-testid="cleanup-confirm-dialog"]')!
    expect(dialog.getAttribute('aria-modal')).toBe('true')
  })

  it('confirm dialog has role="dialog"', () => {
    mockHook({ phase: 'confirming' })
    const { container } = renderCleanupPanel()
    const dialog = container.querySelector('[data-testid="cleanup-confirm-dialog"]')!
    expect(dialog.getAttribute('role')).toBe('dialog')
  })

  it('Tab on last focusable element wraps focus to first (forward focus-trap)', () => {
    mockHook({ phase: 'confirming' })
    const { container } = renderCleanupPanel()
    const dialog = container.querySelector('[data-testid="cleanup-confirm-dialog"]') as HTMLElement
    const focusable = dialog.querySelectorAll<HTMLElement>('p-button:not([disabled])')
    expect(focusable.length).toBeGreaterThanOrEqual(2)

    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    // PDS custom elements need explicit tabIndex for jsdom focus — matches ArchivalModal test pattern
    const firstFocusSpy = vi.spyOn(first, 'focus')
    last.setAttribute('tabindex', '0')
    last.focus()

    fireEvent.keyDown(last, { key: 'Tab', shiftKey: false, bubbles: true })

    expect(firstFocusSpy).toHaveBeenCalled()
  })

  it('Shift+Tab on first focusable element wraps focus to last (backward focus-trap)', () => {
    mockHook({ phase: 'confirming' })
    const { container } = renderCleanupPanel()
    const dialog = container.querySelector('[data-testid="cleanup-confirm-dialog"]') as HTMLElement
    const focusable = dialog.querySelectorAll<HTMLElement>('p-button:not([disabled])')
    expect(focusable.length).toBeGreaterThanOrEqual(2)

    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const lastFocusSpy = vi.spyOn(last, 'focus')
    first.setAttribute('tabindex', '0')
    first.focus()

    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true, bubbles: true })

    expect(lastFocusSpy).toHaveBeenCalled()
  })

  it('focus returns to previously active element when confirm dialog closes (focus-return)', () => {
    // Set up a trigger button outside the component and focus it before the dialog opens
    const triggerOutside = document.createElement('button')
    triggerOutside.setAttribute('data-testid', 'external-trigger')
    document.body.appendChild(triggerOutside)
    triggerOutside.focus()

    // Render with phase=confirming — useEffect captures previousFocusRef = triggerOutside
    vi.mocked(useCleanupFlow).mockReturnValue(hookBase({ phase: 'confirming' }))
    const { rerender } = render(
      <PorscheDesignSystemProvider>
        <CleanupPanel />
      </PorscheDesignSystemProvider>,
    )

    // Spy set up after initial render so we capture only the restore call
    const triggerFocusSpy = vi.spyOn(triggerOutside, 'focus')

    // Transition to idle — useEffect calls previousFocusRef.current?.focus()
    vi.mocked(useCleanupFlow).mockReturnValue(hookBase({ phase: 'idle' }))
    rerender(
      <PorscheDesignSystemProvider>
        <CleanupPanel />
      </PorscheDesignSystemProvider>,
    )

    expect(triggerFocusSpy).toHaveBeenCalled()
    document.body.removeChild(triggerOutside)
  })

  it('Escape key calls cancelCleanup (confirm dialog Escape handling)', () => {
    const hook = hookBase({ phase: 'confirming' })
    vi.mocked(useCleanupFlow).mockReturnValue(hook)
    const { container } = renderCleanupPanel()
    const dialog = container.querySelector('[data-testid="cleanup-confirm-dialog"]') as HTMLElement
    fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(hook.cancelCleanup).toHaveBeenCalledOnce()
  })
})
