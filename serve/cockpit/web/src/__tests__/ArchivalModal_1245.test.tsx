/**
 * RED phase tests for #1245: ArchivalModal — refs input placeholder (brief F2 gap)
 *
 * Brief F2 specifies: Refs <input type="text"> has placeholder "e.g., 1230, 1229".
 * This attribute is absent from the current ArchivalModal implementation and
 * untested in #1241. All tests here are RED until the builder adds it.
 *
 * AC coverage:
 *   "All state, rendering … behaviours specified in brief F2 are implemented"
 *   → brief F2: 'placeholder `e.g., 1230, 1229`' on the refs input
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
  const select = container.querySelector('select') as HTMLSelectElement
  fireEvent.change(select, { target: { value: reason } })
}

function getRefsInput(container: HTMLElement): HTMLInputElement {
  const el = container.querySelector('input[type="text"]') as HTMLInputElement | null
  if (!el) throw new Error('refs input not found')
  return el
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ArchivalModal_RefsPlaceholder', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  // Brief F2: 'placeholder `e.g., 1230, 1229`' on the refs input

  describe('AC: refs input has placeholder "e.g., 1230, 1229" when visible', () => {
    it('refs input has placeholder "e.g., 1230, 1229" when reason is "deprecated"', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      const input = getRefsInput(container)
      expect(input.getAttribute('placeholder')).toBe('e.g., 1230, 1229')
    })

    it('refs input has placeholder "e.g., 1230, 1229" when reason is "duplicate"', () => {
      const { container } = renderModal()
      selectReason(container, 'duplicate')
      const input = getRefsInput(container)
      expect(input.getAttribute('placeholder')).toBe('e.g., 1230, 1229')
    })

    it('placeholder text is the exact string "e.g., 1230, 1229" (boundary: not abbreviated or rephrased)', () => {
      const { container } = renderModal()
      selectReason(container, 'deprecated')
      const input = getRefsInput(container)
      // Must be exactly this string — no substitutes accepted
      expect(input.placeholder).toBe('e.g., 1230, 1229')
    })
  })
})
