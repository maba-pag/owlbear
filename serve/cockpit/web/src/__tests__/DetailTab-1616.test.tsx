/**
 * P2-07: Sidecar information architecture — task #1616 (Cycle 2)
 *
 * AC1: Given a non-null task, DetailTab's root element contains exactly four
 *   data-region children in DOM order: sidecar-body → actions → sidecar-metadata → history.
 *   Asserted via direct-child selector on DetailTab's root element
 *   (querySelectorAll(':scope > [data-region]') on the root <div>).
 *
 * AC2: sidecar-metadata region is a p-accordion host element
 *   (p-accordion[data-region='sidecar-metadata'][compact][heading='Metadata']);
 *   closed by default (no open attribute);
 *   all field-* testid elements within remain queryable in DOM when closed
 *   (PAccordion CSS visibility contract per research).
 *
 * Cycle 2 revision notes:
 *   - AC1 refined: direct-child scoping (not deep query); non-null precondition explicit.
 *   - AC2 refined: accordion HOST is the metadata region (data-region on p-accordion itself,
 *     not on a child). Architect revised AC2 to match existing implementation —
 *     AC2 tests serve as regression guards (all pass against current impl).
 *   - Builder work: AC1 section reordering only.
 *     AC1 tests fail until builder moves sidecar-body and actions before sidecar-metadata.
 */
import { beforeAll, describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../components/DetailTab'

// PDS Stencil form components need attachInternals patched in jsdom —
// same pattern as DetailTab.test.tsx.
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

// ─── Render helper ────────────────────────────────────────────────────────────

function renderDetail(task: TaskDetail = TASK) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
    </PorscheDesignSystemProvider>,
  )
}

/**
 * Returns the values of data-region attributes for DIRECT children of the
 * DetailTab root element, per AC1 requirement ("direct-child selector on
 * DetailTab's root"). Uses sidecar-body as the unique anchor to locate the
 * DetailTab root <div>, walking up to its parentElement. This is robust across
 * any PDS provider wrapper depth.
 */
function getDirectChildRegions(container: HTMLElement): (string | null)[] {
  // sidecar-body is unique in the tree — its parent is the DetailTab root div
  const bodySection = container.querySelector('[data-region="sidecar-body"]')
  const root = bodySection?.parentElement
  if (!root) return []
  return Array.from(root.querySelectorAll(':scope > [data-region]')).map(
    (el) => el.getAttribute('data-region'),
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_SidecarIA', () => {
  // ─── AC1: Section DOM order via direct-child selector ─────────────────────

  describe('AC1: exactly four direct-child data-region sections in correct DOM order', () => {
    it('sections appear in exact order: sidecar-body, actions, sidecar-metadata, history', () => {
      const { container } = renderDetail()
      const regions = getDirectChildRegions(container)
      expect(regions).toEqual(['sidecar-body', 'actions', 'sidecar-metadata', 'history'])
    })

    it('sidecar-body is the first direct-child data-region section', () => {
      const { container } = renderDetail()
      const regions = getDirectChildRegions(container)
      expect(regions[0]).toBe('sidecar-body')
    })

    it('actions appears before sidecar-metadata in the direct-child data-region list', () => {
      const { container } = renderDetail()
      const regions = getDirectChildRegions(container)
      const actionsIdx = regions.indexOf('actions')
      const metaIdx = regions.indexOf('sidecar-metadata')
      expect(actionsIdx).toBeGreaterThanOrEqual(0)
      expect(metaIdx).toBeGreaterThanOrEqual(0)
      expect(actionsIdx).toBeLessThan(metaIdx)
    })

    it('blocked task has same four direct-child data-region sections in correct order', () => {
      const { container } = renderDetail(TASK_BLOCKED)
      const regions = getDirectChildRegions(container)
      expect(regions).toEqual(['sidecar-body', 'actions', 'sidecar-metadata', 'history'])
    })
  })

  // ─── AC2: sidecar-metadata is p-accordion host element ───────────────────
  //
  // Architect revised AC2 to match existing implementation (accordion HOST
  // pattern — data-region placed on the p-accordion element itself, not on a
  // child inside it). These tests are regression guards; all pass against the
  // current implementation. Builder work for this task is AC1 reordering only.

  describe('AC2: sidecar-metadata p-accordion host — attributes and closed-DOM contract', () => {
    it('element with data-region="sidecar-metadata" is a p-accordion host (accordion IS the metadata region)', () => {
      const { container } = renderDetail()
      const metadataEl = container.querySelector('[data-region="sidecar-metadata"]')
      expect(metadataEl).not.toBeNull()
      expect(metadataEl?.tagName.toLowerCase()).toBe('p-accordion')
    })

    it('p-accordion[data-region="sidecar-metadata"] has the compact attribute', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion[data-region="sidecar-metadata"]')
      expect(accordion).not.toBeNull()
      expect(accordion?.hasAttribute('compact')).toBe(true)
    })

    it('p-accordion[data-region="sidecar-metadata"] has heading="Metadata"', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion[data-region="sidecar-metadata"]')
      expect(accordion).not.toBeNull()
      expect(accordion?.getAttribute('heading')).toBe('Metadata')
    })

    it('p-accordion[data-region="sidecar-metadata"] is closed by default — no open attribute', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion[data-region="sidecar-metadata"]')
      expect(accordion).not.toBeNull()
      expect(accordion?.hasAttribute('open')).toBe(false)
    })

    it('all field-* testid elements remain queryable inside the accordion when closed (CSS visibility contract)', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion[data-region="sidecar-metadata"]')
      expect(accordion?.hasAttribute('open')).toBe(false)
      // Content must stay in DOM — PAccordion uses CSS height animation, not conditional render.
      for (const testid of ['field-id', 'field-status', 'field-created', 'field-claimed']) {
        expect(
          accordion?.querySelector(`[data-testid="${testid}"]`),
          `${testid} must be in accordion DOM when closed`,
        ).not.toBeNull()
      }
    })
  })
})
