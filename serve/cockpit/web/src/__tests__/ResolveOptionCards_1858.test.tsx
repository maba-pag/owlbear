/**
 * Task #1858 — P2-01: Decision resolver UI with option cards
 *
 * Covers:
 *   AC1: ResolveModal renders one card per decision option with a confidence bar
 *        ([data-testid="option-confidence-{option_id}"], width proportional to
 *        confidence 0→0% 1→100%), rationale text (omitted if empty), and a
 *        Recommended badge ([data-testid="option-recommended-{option_id}"],
 *        DOM-present only when recommended===true).
 *   AC2: Clicking an option card sets aria-selected="true" on it and
 *        aria-selected="false" on siblings; selected option_id used as
 *        selected_option_id in the resolve payload; submitting with no option
 *        selected sends selected_option_id: null (when textarea has content).
 *   AC3: For decision-kind, submit is functional (fetch called) when no option
 *        is selected but textarea has non-whitespace text; canSubmit = option
 *        selected OR non-empty trimmed textarea.
 *
 * RED reasons (expected failures against current implementation):
 *   AC1: option buttons render only the label — no confidence bar element
 *        ([data-testid="option-confidence-*"] absent), no rationale sub-element,
 *        no recommended badge ([data-testid="option-recommended-*"] absent).
 *   AC2: buttons have no aria-selected attribute; handleSubmit returns early when
 *        selectedOptionId===null even if textarea has content.
 *   AC3: canSubmit = selectedOptionId !== null — textarea content is not
 *        considered; submit click with no option does nothing regardless of notes.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ResolveModal from '../components/ResolveModal'

// ─── react-markdown mock ──────────────────────────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Types ────────────────────────────────────────────────────────────────────

interface PendingDROption {
  option_id: string
  label: string
  confidence: number
  recommended: boolean
  rationale: string
}

interface PendingDR {
  id: string
  task_id: number
  agent: string
  request_type: string
  created: string
  title: string
  summary: string
  kind: 'decision' | 'action'
  options: PendingDROption[]
  body: string
  body_preview: string
}

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const DR_DECISION: PendingDR = {
  id: 'req-1858',
  task_id: 1858,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-05-25T10:00:00Z',
  title: 'Choose implementation approach',
  summary: 'Which approach should we use?',
  kind: 'decision',
  options: [
    {
      option_id: 'opt-alpha',
      label: 'Alpha approach',
      confidence: 0.8,
      recommended: true,
      rationale: 'Best performance characteristics',
    },
    {
      option_id: 'opt-beta',
      label: 'Beta approach',
      confidence: 0.5,
      recommended: false,
      rationale: '',
    },
  ],
  body: '## Context\nSome context here.',
  body_preview: 'Some context here.',
}

const DR_BOUNDARY_CONFIDENCE: PendingDR = {
  ...DR_DECISION,
  id: 'req-1858-boundary',
  options: [
    {
      option_id: 'opt-zero',
      label: 'Zero confidence option',
      confidence: 0.0,
      recommended: false,
      rationale: '',
    },
    {
      option_id: 'opt-full',
      label: 'Full confidence option',
      confidence: 1.0,
      recommended: true,
      rationale: 'Maximum confidence',
    },
  ],
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderModal(dr: PendingDR, onClose = vi.fn(), onResolved = vi.fn()) {
  return render(
    <PorscheDesignSystemProvider>
      <ResolveModal dr={dr} onClose={onClose} onResolved={onResolved} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── AC1: Confidence bar, rationale, recommended badge ───────────────────────

describe('TestFromAC_OptionCards', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  describe('AC1: confidence bar', () => {
    it('renders a confidence bar element per option identified by data-testid="option-confidence-{option_id}"', () => {
      const { container } = renderModal(DR_DECISION)
      // FAILS: no [data-testid="option-confidence-*"] elements exist in current implementation
      const alphaBar = container.querySelector('[data-testid="option-confidence-opt-alpha"]')
      const betaBar = container.querySelector('[data-testid="option-confidence-opt-beta"]')
      expect(alphaBar).not.toBeNull()
      expect(betaBar).not.toBeNull()
    })

    it('confidence bar width is proportional to confidence value (0.8 → "80%")', () => {
      const { container } = renderModal(DR_DECISION)
      // FAILS: element absent; even if present, width not set to 80%
      const bar = container.querySelector('[data-testid="option-confidence-opt-alpha"]') as HTMLElement | null
      expect(bar).not.toBeNull()
      expect(bar?.style.width).toBe('80%')
    })

    it('confidence bar width is "0%" when confidence is 0.0 (lower boundary)', () => {
      const { container } = renderModal(DR_BOUNDARY_CONFIDENCE)
      // FAILS: element absent
      const bar = container.querySelector('[data-testid="option-confidence-opt-zero"]') as HTMLElement | null
      expect(bar).not.toBeNull()
      expect(bar?.style.width).toBe('0%')
    })

    it('confidence bar width is "100%" when confidence is 1.0 (upper boundary)', () => {
      const { container } = renderModal(DR_BOUNDARY_CONFIDENCE)
      // FAILS: element absent
      const bar = container.querySelector('[data-testid="option-confidence-opt-full"]') as HTMLElement | null
      expect(bar).not.toBeNull()
      expect(bar?.style.width).toBe('100%')
    })
  })

  describe('AC1: rationale text', () => {
    it('renders rationale text inside the option card when rationale is non-empty', () => {
      const { container } = renderModal(DR_DECISION)
      const alphaCard = container.querySelector('[data-testid="resolve-option-opt-alpha"]')
      // FAILS: current button renders only the label — rationale text absent from card content
      expect(alphaCard).not.toBeNull()
      expect(alphaCard?.textContent).toContain('Best performance characteristics')
    })
  })

  describe('AC1: recommended badge', () => {
    it('renders recommended badge ([data-testid="option-recommended-{id}"]) when recommended===true, and omits it when recommended===false', () => {
      const { container } = renderModal(DR_DECISION)
      // FAILS: [data-testid="option-recommended-opt-alpha"] absent — badge not rendered yet
      const alphaBadge = container.querySelector('[data-testid="option-recommended-opt-alpha"]')
      const betaBadge = container.querySelector('[data-testid="option-recommended-opt-beta"]')
      // alpha has recommended: true → badge must be in DOM
      expect(alphaBadge).not.toBeNull()
      // beta has recommended: false → badge must be absent
      expect(betaBadge).toBeNull()
    })
  })
})

// ─── AC2: aria-selected state management + payload ───────────────────────────

describe('TestFromAC_OptionSelection', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  describe('AC2: aria-selected on click', () => {
    it('clicking an option card sets aria-selected="true" on that card', () => {
      const { container } = renderModal(DR_DECISION)
      const alphaCard = container.querySelector('[data-testid="resolve-option-opt-alpha"]') as HTMLElement | null
      expect(alphaCard).not.toBeNull()
      fireEvent.click(alphaCard!)
      // FAILS: no aria-selected attribute set on option buttons in current implementation
      expect(alphaCard!.getAttribute('aria-selected')).toBe('true')
    })

    it('clicking an option card sets aria-selected="false" on sibling cards', () => {
      const { container } = renderModal(DR_DECISION)
      const alphaCard = container.querySelector('[data-testid="resolve-option-opt-alpha"]') as HTMLElement | null
      const betaCard = container.querySelector('[data-testid="resolve-option-opt-beta"]') as HTMLElement | null
      expect(alphaCard).not.toBeNull()
      expect(betaCard).not.toBeNull()
      fireEvent.click(alphaCard!)
      // FAILS: no aria-selected attribute on buttons; sibling does not get aria-selected="false"
      expect(betaCard!.getAttribute('aria-selected')).toBe('false')
    })

    it('clicking a different card transfers aria-selected (first becomes false, new becomes true)', () => {
      const { container } = renderModal(DR_DECISION)
      const alphaCard = container.querySelector('[data-testid="resolve-option-opt-alpha"]') as HTMLElement | null
      const betaCard = container.querySelector('[data-testid="resolve-option-opt-beta"]') as HTMLElement | null
      expect(alphaCard).not.toBeNull()
      expect(betaCard).not.toBeNull()

      fireEvent.click(alphaCard!)
      fireEvent.click(betaCard!)

      // FAILS: no aria-selected attribute managed; beta does not become "true"
      expect(betaCard!.getAttribute('aria-selected')).toBe('true')
      expect(alphaCard!.getAttribute('aria-selected')).toBe('false')
    })

    it('all option cards have aria-selected="false" before any click (initial state)', () => {
      const { container } = renderModal(DR_DECISION)
      const allOptions = container.querySelectorAll('[data-testid^="resolve-option-"]')
      expect(allOptions.length).toBeGreaterThan(0)
      // FAILS: current buttons have no aria-selected attribute at all; getAttribute returns null ≠ "false"
      for (const card of Array.from(allOptions)) {
        expect(card.getAttribute('aria-selected')).toBe('false')
      }
    })
  })

  describe('AC2+AC3: submit with no option selected but textarea has content', () => {
    it('with no option selected and textarea containing non-whitespace text, submit triggers POST with selected_option_id: null', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
      )
      vi.stubGlobal('fetch', fetchMock)

      const { container } = renderModal(DR_DECISION)

      // Do NOT select any option — selected_option_id must be null in the payload
      const notesField = container.querySelector('[data-testid="resolve-notes"]') as HTMLElement | null
      expect(notesField).not.toBeNull()
      // Type non-whitespace text — this should enable submit for decision-kind
      fireEvent.change(notesField!, { target: { value: 'Free-text resolution note.' } })

      const submitBtn = container.querySelector('[data-testid="resolve-submit"]') as HTMLElement | null
      expect(submitBtn).not.toBeNull()
      fireEvent.click(submitBtn!)

      // FAILS: handleSubmit currently returns early when selectedOptionId===null for decision-kind,
      // so fetch is never called regardless of textarea content.
      await waitFor(
        () => {
          expect(fetchMock).toHaveBeenCalled()
          const resolveCall = fetchMock.mock.calls.find((c) =>
            String(c[0]).includes('/resolve'),
          )
          expect(resolveCall).toBeDefined()
          const body = JSON.parse(
            ((resolveCall![1] as RequestInit).body as string),
          ) as Record<string, unknown>
          expect(body.selected_option_id).toBeNull()
        },
        { timeout: 500 },
      )
    })
  })
})
