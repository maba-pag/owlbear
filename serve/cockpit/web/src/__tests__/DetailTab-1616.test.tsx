/**
 * P2-07: Sidecar information architecture — task #1616
 *
 * AC1: DetailTab renders data-region sections in DOM order:
 *   sidecar-body (Editor) → actions (Actions) → sidecar-metadata (Metadata) → history (History)
 *   Asserted via querySelectorAll('[data-region]') on DetailTab's root element.
 *
 * AC2: Metadata section (data-region='sidecar-metadata') wrapped in a p-accordion element
 *   with compact attribute and heading='Metadata'; closed by default (no open attribute);
 *   field-* testid elements remain in DOM when closed (PAccordion uses CSS visibility).
 *
 * All tests must FAIL until the builder reorders sections and wraps metadata in PAccordion.
 */
import { beforeAll, describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../components/DetailTab'

// PDS Stencil form components (p-input-text, p-textarea, p-select) need
// attachInternals patched in jsdom — same pattern as DetailTab.test.tsx.
beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-04-18T10:00:00+00:00',
  created: '2026-04-17T09:00:00+00:00',
  tags: ['bug', 'frontend'],
  blocked: false,
  block_reason: null,
  claimed: false,
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [],
}

const TASK_BLOCKED: TaskDetail = {
  ...TASK,
  blocked: true,
  block_reason: 'Waiting for dependency #100',
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderDetail(task: TaskDetail = TASK) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_SidecarIA', () => {
  // ─── AC1: Section DOM order ───────────────────────────────────────────────

  describe('AC1: data-region section DOM order', () => {
    it('data-region sections appear in exact order: sidecar-body → actions → sidecar-metadata → history', () => {
      const { container } = renderDetail()
      const regions = Array.from(container.querySelectorAll('[data-region]')).map(
        (el) => el.getAttribute('data-region'),
      )
      expect(regions).toEqual(['sidecar-body', 'actions', 'sidecar-metadata', 'history'])
    })

    it('actions appears before sidecar-metadata in DOM order', () => {
      const { container } = renderDetail()
      const regions = Array.from(container.querySelectorAll('[data-region]')).map(
        (el) => el.getAttribute('data-region'),
      )
      const actionsIdx = regions.indexOf('actions')
      const metadataIdx = regions.indexOf('sidecar-metadata')
      expect(actionsIdx).toBeGreaterThanOrEqual(0)
      expect(metadataIdx).toBeGreaterThanOrEqual(0)
      expect(actionsIdx).toBeLessThan(metadataIdx)
    })

    it('sidecar-metadata appears before history in DOM order', () => {
      const { container } = renderDetail()
      const regions = Array.from(container.querySelectorAll('[data-region]')).map(
        (el) => el.getAttribute('data-region'),
      )
      const metadataIdx = regions.indexOf('sidecar-metadata')
      const historyIdx = regions.indexOf('history')
      expect(metadataIdx).toBeGreaterThanOrEqual(0)
      expect(historyIdx).toBeGreaterThanOrEqual(0)
      expect(metadataIdx).toBeLessThan(historyIdx)
    })

    it('DOM order is preserved for a blocked task', () => {
      const { container } = renderDetail(TASK_BLOCKED)
      const regions = Array.from(container.querySelectorAll('[data-region]')).map(
        (el) => el.getAttribute('data-region'),
      )
      expect(regions).toEqual(['sidecar-body', 'actions', 'sidecar-metadata', 'history'])
    })
  })

  // ─── AC2: Metadata p-accordion wrapping ───────────────────────────────────

  describe('AC2: sidecar-metadata wrapped in p-accordion', () => {
    it('a p-accordion element is present in DetailTab', () => {
      const { container } = renderDetail()
      expect(container.querySelector('p-accordion')).not.toBeNull()
    })

    it('sidecar-metadata region is contained within the p-accordion element', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion')
      expect(accordion).not.toBeNull()
      expect(accordion?.querySelector('[data-region="sidecar-metadata"]')).not.toBeNull()
    })

    it('p-accordion has the compact attribute', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion')
      expect(accordion).not.toBeNull()
      expect(accordion?.hasAttribute('compact')).toBe(true)
    })

    it('p-accordion has heading="Metadata"', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion')
      expect(accordion).not.toBeNull()
      expect(accordion?.getAttribute('heading')).toBe('Metadata')
    })

    it('p-accordion is closed by default — no open attribute present', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion')
      expect(accordion).not.toBeNull()
      expect(accordion?.hasAttribute('open')).toBe(false)
    })

    it('field-id element remains in DOM when accordion is closed (CSS visibility, not unmount)', () => {
      const { container } = renderDetail()
      // Closed by default — no open attribute
      const accordion = container.querySelector('p-accordion')
      expect(accordion?.hasAttribute('open')).toBe(false)
      // Content must still be in DOM (PAccordion uses CSS height animation, not conditional rendering)
      expect(container.querySelector('[data-testid="field-id"]')).not.toBeNull()
    })

    it('field-status element remains in DOM when accordion is closed', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion')
      expect(accordion?.hasAttribute('open')).toBe(false)
      expect(container.querySelector('[data-testid="field-status"]')).not.toBeNull()
    })

    it('field-created element remains in DOM when accordion is closed', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion')
      expect(accordion?.hasAttribute('open')).toBe(false)
      expect(container.querySelector('[data-testid="field-created"]')).not.toBeNull()
    })

    it('field-claimed element remains in DOM when accordion is closed', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion')
      expect(accordion?.hasAttribute('open')).toBe(false)
      expect(container.querySelector('[data-testid="field-claimed"]')).not.toBeNull()
    })
  })
})
