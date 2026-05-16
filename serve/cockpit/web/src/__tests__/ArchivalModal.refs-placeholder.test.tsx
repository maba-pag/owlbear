/**
 * ArchivalModal — selector reconciliation + em-dash
 *
 * Covers two (td:1)/(td:2) AC items not yet green:
 *
 * 1. Selector reconciliation: original placeholder tests are retained with
 *    PDS-correct selectors (p-select + p-input-text). These pass once
 *    selectors are fixed and serve as regression guards.
 *
 * 2. Em-dash in hint text: brief F2 line 130 requires the exact string
 *    "Required — enter at least one task ID" (em-dash). The component
 *    currently renders "Required - enter at least one task ID" (hyphen).
 *
 * AC coverage:
 *   "Hint text displayed below refs field when visible:
 *    'Required — enter at least one task ID' (em-dash —, not hyphen)"
 *   "Placeholder `e.g., 1230, 1229` on refs input when visible"
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ArchivalModal from '../components/ArchivalModal'

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
  return render(
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
}

function selectReason(container: HTMLElement, reason: string): void {
  const pSelect = container.querySelector('p-select')
  if (!pSelect) throw new Error('reason p-select not found')
  fireEvent(pSelect, new CustomEvent('change', { detail: { value: reason }, bubbles: true }))
}

function getRefsInput(container: HTMLElement): HTMLElement {
  const el = container.querySelector('p-input-text') as HTMLElement | null
  if (!el) throw new Error('refs p-input-text not found')
  return el
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ArchivalModal_RefsPlaceholder', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  // Brief F2: 'placeholder `e.g., 1230, 1229`' on the refs input

  describe('AC: refs input has placeholder "e.g., 1230, 1229" when visible', () => {
    it('p-input-text has placeholder "e.g., 1230, 1229" when reason is "deprecated"', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      const pInput = getRefsInput(container)
      // PDS PInputText sets placeholder as a JS property (React 19 sets it as property on custom element)
      expect((pInput as HTMLInputElement).placeholder).toBe('e.g., 1230, 1229')
    })

    it('p-input-text has placeholder "e.g., 1230, 1229" when reason is "duplicate"', () => {
      const { container } = renderModal()
      selectReason(container, 'duplicate')
      const pInput = getRefsInput(container)
      expect((pInput as HTMLInputElement).placeholder).toBe('e.g., 1230, 1229')
    })

    it('placeholder text is the exact string "e.g., 1230, 1229" (boundary: not abbreviated or rephrased)', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      const pInput = getRefsInput(container)
      // Must be exactly this string — no substitutes accepted
      expect((pInput as HTMLInputElement).placeholder).toBe('e.g., 1230, 1229')
    })
  })
})

// ─── Em-dash test (RED until builder fixes hint text) ──────────────────────────────

describe('TestFromAC_ArchivalModal_HintEmDash', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  // Brief F2 line 130: em-dash — not hyphen -

  describe('AC: hint text uses em-dash (—), not hyphen (-)', () => {
    it('hint text contains em-dash version: "Required — enter at least one task ID"', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      expect(container.textContent).toContain('Required — enter at least one task ID')
    })

    it('hint text does NOT contain hyphen version: "Required - enter at least one task ID"', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      // The component must use em-dash, not ASCII hyphen
      expect(container.textContent).not.toContain('Required - enter at least one task ID')
    })

    it('em-dash requirement holds for "duplicate" reason too', () => {
      const { container } = renderModal()
      selectReason(container, 'duplicate')
      expect(container.textContent).toContain('Required — enter at least one task ID')
    })
  })
})
