/**
 * Test Cockpit resolution UX — modal behavior
 *
 * Covers AC2, AC3, AC4, and AC5 against ResolveModal.tsx.
 *
 * GREEN: ResolveModal UX contract is implemented; all tests pass against current implementation.
 * Shell-level popover replacement (DRStatusIndicator → DecisionViewport) is #1389's scope.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ResolveModal from '../components/ResolveModal'
import type { PendingDRWithBody } from '../components/ResolveModal'

// ─── react-markdown mock ──────────────────────────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Fixture ──────────────────────────────────────────────────────────────────

const DR_FIXTURE: PendingDRWithBody = {
  id: 'dr-ux-001',
  task_id: 55,
  agent: 'builder',
  request_type: 'scope-decision',
  created: '2026-05-01T10:00:00Z',
  title: 'Confirm approach for caching strategy',
  body_preview: 'Builder needs guidance on caching.',
  body: '## Context\n\nShould we use Redis or in-memory cache?',
}

// ─── Render helper ────────────────────────────────────────────────────────────

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

describe('TestFromAC_ResolveModalUX', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('sizes the resolver surface with room for PDS modal chrome', () => {
    const { container } = renderModal()
    const surface = container.querySelector('[data-testid="resolve-modal-surface"]') as HTMLElement | null
    expect(surface).not.toBeNull()
    expect(surface?.className).toContain('w-[min(1280px,calc(100vw-18.5rem))]')
    expect(surface?.className).toContain('max-w-full')
    expect(surface?.className).not.toContain('calc(100vw-4rem)')
    expect(surface?.className).not.toContain('calc(100vw-12rem)')
  })

  // ─── AC2 (td:2): Structural description elements (not word-count checks) ─────
  //
  // Refined AC2: tests verify a structurally separate p-text description element
  // adjacent to each radio input (NOT inside the radio's <label>).
  // (a) A p-text exists per option, structurally separate from the label element.
  // (b) Description text contains action-oriented content beyond the bare status token.
  //
  // Current code: bare labels, no p-text in fieldset → all FAIL

  it('approved option has a p-text description element structurally separate from its radio label', () => {
    // AC2: scope to per-option container (data-testid="option-approved"), not shared fieldset parent
    const { container } = renderModal()
    const optionContainer = container.querySelector('[data-testid="option-approved"]')
    expect(optionContainer).not.toBeNull()
    const approvedInput = optionContainer!.querySelector(
      'input[type="radio"][value="approved"]',
    ) as HTMLInputElement | null
    expect(approvedInput).not.toBeNull()
    const approvedLabel = approvedInput!.closest('label') ?? approvedInput!.parentElement!
    const descEl = optionContainer!.querySelector('p-text')
    expect(descEl).not.toBeNull()
    // Description must be outside the radio's label, not inside it
    expect(approvedLabel.contains(descEl)).toBe(false)
  })

  it('approved description p-text uses proceed/continue outcome language', () => {
    // AC2 v2: approved consequence must explicitly communicate proceeding.
    const { container } = renderModal()
    const optionContainer = container.querySelector('[data-testid="option-approved"]')!
    const descEl = optionContainer.querySelector('p-text')!
    const text = descEl.textContent ?? ''
    expect(text).toMatch(/proceed|continue/i)
  })

  it('rejected option has a p-text description element structurally separate from its radio label', () => {
    // AC2: scope to per-option container (data-testid="option-rejected"), not shared fieldset parent
    const { container } = renderModal()
    const optionContainer = container.querySelector('[data-testid="option-rejected"]')
    expect(optionContainer).not.toBeNull()
    const rejectedInput = optionContainer!.querySelector(
      'input[type="radio"][value="rejected"]',
    ) as HTMLInputElement | null
    expect(rejectedInput).not.toBeNull()
    const rejectedLabel = rejectedInput!.closest('label') ?? rejectedInput!.parentElement!
    const descEl = optionContainer!.querySelector('p-text')
    expect(descEl).not.toBeNull()
    expect(rejectedLabel.contains(descEl)).toBe(false)
  })

  it('rejected description p-text uses stop/return/back outcome language', () => {
    // AC2 v2: rejected consequence must explicitly communicate stopping/returning.
    const { container } = renderModal()
    const optionContainer = container.querySelector('[data-testid="option-rejected"]')!
    const descEl = optionContainer.querySelector('p-text')!
    const text = descEl.textContent ?? ''
    expect(text).toMatch(/stop|return|back/i)
  })

  it('needs-info option has a p-text description element structurally separate from its radio label', () => {
    // AC2: scope to per-option container (data-testid="option-needs-info"), not shared fieldset parent
    const { container } = renderModal()
    const optionContainer = container.querySelector('[data-testid="option-needs-info"]')
    expect(optionContainer).not.toBeNull()
    const needsInfoInput = optionContainer!.querySelector(
      'input[type="radio"][value="needs-info"]',
    ) as HTMLInputElement | null
    expect(needsInfoInput).not.toBeNull()
    const needsInfoLabel = needsInfoInput!.closest('label') ?? needsInfoInput!.parentElement!
    const descEl = optionContainer!.querySelector('p-text')
    expect(descEl).not.toBeNull()
    expect(needsInfoLabel.contains(descEl)).toBe(false)
  })

  it('needs-info description p-text uses wait/clarification outcome language', () => {
    // AC2 v2: needs-info consequence must explicitly communicate waiting for clarity.
    const { container } = renderModal()
    const optionContainer = container.querySelector('[data-testid="option-needs-info"]')!
    const descEl = optionContainer.querySelector('p-text')!
    const text = descEl.textContent ?? ''
    expect(text).toMatch(/wait|clarif/i)
  })

  // ─── AC3 (td:2): No pre-selected choice; submit disabled until selection ──
  //
  // Current code: `useState('approved')` pre-selects → FAIL

  it('no radio is checked on initial render (no default pre-selection)', () => {
    const { container } = renderModal()
    const radios = container.querySelectorAll(
      'input[type="radio"][name="resolve-response"]',
    )
    const checked = Array.from(radios).filter((r) => (r as HTMLInputElement).checked)
    expect(checked).toHaveLength(0)
  })

  it('approved radio is not pre-selected on initial render', () => {
    const { container } = renderModal()
    const approved = container.querySelector(
      'input[type="radio"][value="approved"]',
    ) as HTMLInputElement | null
    expect(approved).not.toBeNull()
    expect(approved!.checked).toBe(false)
  })

  it('submit button is disabled when no choice has been selected', () => {
    const { container } = renderModal()
    const submit = container.querySelector(
      '[data-testid="resolve-submit"]',
    ) as HTMLElement | null
    expect(submit).not.toBeNull()
    // PDS PButton surfaces disabled as an attribute on the custom element
    expect(submit!.hasAttribute('disabled')).toBe(true)
  })

  it('submit button is disabled → enabled only after explicit user selection (sequence test)', () => {
    const { container } = renderModal()
    const submit = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement
    // Step 1: disabled before any selection
    expect(submit.hasAttribute('disabled')).toBe(true)
    // Step 2: select a choice
    const radio = container.querySelector(
      'input[type="radio"][value="needs-info"]',
    ) as HTMLInputElement
    fireEvent.click(radio)
    // Step 3: submit is now enabled
    expect(submit.hasAttribute('disabled')).toBe(false)
  })

  // ─── AC4 (td:1): Multi-word action labels ────────────────────────────────
  //
  // Current code: "Submit" (1 word), "Cancel" (1 word) → FAIL

  it('submit button label has more than one word', () => {
    const { container } = renderModal()
    const submit = container.querySelector(
      '[data-testid="resolve-submit"]',
    ) as HTMLElement | null
    expect(submit).not.toBeNull()
    const label = submit!.textContent?.trim() ?? ''
    const wordCount = label.split(/\s+/).filter(Boolean).length
    expect(wordCount).toBeGreaterThan(1)
  })

  it('cancel/close button label has more than one word', () => {
    const { container } = renderModal()
    const cancel = container.querySelector(
      '[data-testid="resolve-cancel"]',
    ) as HTMLElement | null
    expect(cancel).not.toBeNull()
    const label = cancel!.textContent?.trim() ?? ''
    const wordCount = label.split(/\s+/).filter(Boolean).length
    expect(wordCount).toBeGreaterThan(1)
  })

  it('consequence description text for each option uses PDS typography element (p-text)', () => {
    const { container } = renderModal()
    const selector = container.querySelector('[data-testid="response-selector"]')!
    expect(selector).not.toBeNull()
    // Each option's description should be in a p-text element — not bare text nodes
    const pTextEls = selector.querySelectorAll('p-text')
    expect(pTextEls.length).toBeGreaterThanOrEqual(3)
  })

  it('shows a resolver body continuation cue while more inputs continue below', () => {
    const { container } = renderModal()
    const body = container.querySelector('[data-testid="resolve-scroll-body"]') as HTMLElement | null
    expect(body).not.toBeNull()
    Object.defineProperty(body!, 'scrollHeight', { configurable: true, value: 900 })
    Object.defineProperty(body!, 'clientHeight', { configurable: true, value: 360 })
    Object.defineProperty(body!, 'scrollTop', { configurable: true, value: 0 })

    fireEvent.scroll(body!)

    const cue = container.querySelector('[data-testid="resolve-scroll-cue"]')
    expect(cue).not.toBeNull()
    expect(cue?.getAttribute('class') ?? '').toContain('absolute')
    expect(cue?.getAttribute('class') ?? '').toContain('bottom-0')
  })

  it('hides the resolver body continuation cue at the bottom', () => {
    const { container } = renderModal()
    const body = container.querySelector('[data-testid="resolve-scroll-body"]') as HTMLElement | null
    expect(body).not.toBeNull()
    Object.defineProperty(body!, 'scrollHeight', { configurable: true, value: 900 })
    Object.defineProperty(body!, 'clientHeight', { configurable: true, value: 360 })
    Object.defineProperty(body!, 'scrollTop', { configurable: true, value: 540 })

    fireEvent.scroll(body!)

    expect(container.querySelector('[data-testid="resolve-scroll-cue"]')).toBeNull()
  })

  // ─── AC5 (td:2): Keyboard / focus behavior ───────────────────────────────
  //
  // Current code: no focus management, no Escape handler → all FAIL

  it('initial focus within modal is not on the submit button (non-destructive element receives focus)', () => {
    const { container } = renderModal()
    const submit = container.querySelector(
      '[data-testid="resolve-submit"]',
    )
    // After render, the active element must be inside the modal and not the submit button
    const modal = container.querySelector('[data-testid="resolve-modal"]')!
    expect(modal).not.toBeNull()
    // Focus should have moved into the modal
    expect(modal.contains(document.activeElement)).toBe(true)
    // And it must NOT be on the (destructive) submit button
    expect(document.activeElement).not.toBe(submit)
  })

  it('pressing Escape calls onClose', () => {
    const onClose = vi.fn()
    const { container } = renderModal(DR_FIXTURE, onClose)
    const modal = container.querySelector('[data-testid="resolve-modal"]') as HTMLElement | null
    expect(modal).not.toBeNull()
    fireEvent.keyDown(modal!, { key: 'Escape', code: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('pressing Escape on document calls onClose (global handler)', () => {
    const onClose = vi.fn()
    renderModal(DR_FIXTURE, onClose)
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('modal has aria-modal="true" for proper focus trap semantics (required for logical tab order)', () => {
    const { container } = renderModal()
    const modal = container.querySelector('[data-testid="resolve-modal"]')!
    // aria-modal="true" is required so assistive technology constrains Tab navigation
    // within the modal — without it, screen-reader users can navigate out of the dialog.
    expect(modal.getAttribute('aria-modal')).toBe('true')
  })
})
