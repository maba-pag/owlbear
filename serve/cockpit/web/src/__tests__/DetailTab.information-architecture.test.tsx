/**
 * P2-07: Task detail information architecture — task #1616 (Cycle 3)
 *
 * AC1: Given a non-null task, DetailTab's root element contains exactly four
 *   data-region children in DOM order: task-detail-body → actions → task-detail-metadata → history.
 *   Asserted via direct-child selector on DetailTab's root element
 *   (querySelectorAll(':scope > [data-region]') on the root <div>).
 *
 * AC2: task-detail-metadata region is a p-accordion host element
 *   (p-accordion[data-region='task-detail-metadata'][compact][heading='Metadata']);
 *   closed by default (no open attribute);
 *   accordion subtree remains in DOM when closed — proved by querying at least one
 *   field-* testid descendant (PAccordion uses CSS height animation, not conditional render).
 *
 * Cycle 3 revision notes:
 *   - AC2 narrowed from "all field-*" to "at least one field-* testid descendant".
 *     Rationale: PAccordion CSS-visibility contract is proved by any single queryable
 *     descendant — individual field rendering is a separate concern owned by DetailTab.test.tsx.
 *   - AC1 refined: direct-child scoping (not deep query); non-null precondition explicit.
 *   - Accordion HOST pattern: data-region on p-accordion itself (not on a child inside it).
 *   - Cycle 2 builder (commit 301a886) already reordered sections; all tests now PASS.
 *   - AC2 tests serve as regression guards (implementation already satisfies them).
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
 * DetailTab's root"). Uses task-detail-body as the unique anchor to locate the
 * DetailTab root <div>, walking up to its parentElement. This is robust across
 * any PDS provider wrapper depth.
 */
function getDirectChildRegions(container: HTMLElement): (string | null)[] {
  // task-detail-body is unique in the tree — its parent is the DetailTab root div
  const bodySection = container.querySelector('[data-region="task-detail-body"]')
  const root = bodySection?.parentElement
  if (!root) return []
  return Array.from(root.querySelectorAll(':scope > [data-region]')).map(
    (el) => el.getAttribute('data-region'),
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('DetailTab task detail information architecture', () => {
  // ─── AC1: Section DOM order via direct-child selector ─────────────────────

  describe('AC1: exactly four direct-child data-region sections in correct DOM order', () => {
    it('sections appear in exact order: task-detail-body, actions, task-detail-metadata, history', () => {
      const { container } = renderDetail()
      const regions = getDirectChildRegions(container)
      expect(regions).toEqual(['task-detail-body', 'actions', 'task-detail-metadata', 'history'])
    })

    it('task-detail-body is the first direct-child data-region section', () => {
      const { container } = renderDetail()
      const regions = getDirectChildRegions(container)
      expect(regions[0]).toBe('task-detail-body')
    })

    it('actions appears before task-detail-metadata in the direct-child data-region list', () => {
      const { container } = renderDetail()
      const regions = getDirectChildRegions(container)
      const actionsIdx = regions.indexOf('actions')
      const metaIdx = regions.indexOf('task-detail-metadata')
      expect(actionsIdx).toBeGreaterThanOrEqual(0)
      expect(metaIdx).toBeGreaterThanOrEqual(0)
      expect(actionsIdx).toBeLessThan(metaIdx)
    })

    it('blocked task has same four direct-child data-region sections in correct order', () => {
      const { container } = renderDetail(TASK_BLOCKED)
      const regions = getDirectChildRegions(container)
      expect(regions).toEqual(['task-detail-body', 'actions', 'task-detail-metadata', 'history'])
    })
  })

  // ─── AC2: task-detail-metadata is p-accordion host element ───────────────
  //
  // Architect revised AC2 to match existing implementation (accordion HOST
  // pattern — data-region placed on the p-accordion element itself, not on a
  // child inside it). These tests are regression guards; all pass against the
  // current implementation. Builder work for this task is AC1 reordering only.

  describe('AC2: task-detail-metadata p-accordion host — attributes and closed-DOM contract', () => {
    it('element with data-region="task-detail-metadata" is a p-accordion host (accordion IS the metadata region)', () => {
      const { container } = renderDetail()
      const metadataEl = container.querySelector('[data-region="task-detail-metadata"]')
      expect(metadataEl).not.toBeNull()
      expect(metadataEl?.tagName.toLowerCase()).toBe('p-accordion')
    })

    it('p-accordion[data-region="task-detail-metadata"] has the compact attribute', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion[data-region="task-detail-metadata"]')
      expect(accordion).not.toBeNull()
      expect(accordion?.hasAttribute('compact')).toBe(true)
    })

    it('p-accordion[data-region="task-detail-metadata"] has heading="Metadata"', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion[data-region="task-detail-metadata"]')
      expect(accordion).not.toBeNull()
      expect(accordion?.getAttribute('heading')).toBe('Metadata')
    })

    it('p-accordion[data-region="task-detail-metadata"] is closed by default — no open attribute', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion[data-region="task-detail-metadata"]')
      expect(accordion).not.toBeNull()
      expect(accordion?.hasAttribute('open')).toBe(false)
    })

    it('at least one field-* testid descendant is queryable inside the closed accordion (CSS visibility contract)', () => {
      const { container } = renderDetail()
      const accordion = container.querySelector('p-accordion[data-region="task-detail-metadata"]')
      expect(accordion?.hasAttribute('open')).toBe(false)
      // Querying any one descendant proves PAccordion CSS height animation (not conditional render).
      // Checks field-id as representative sample — AC2 requires at least one.
      expect(
        accordion?.querySelector('[data-testid="field-id"]'),
        'field-id must be in accordion DOM when closed',
      ).not.toBeNull()
    })
  })
})
