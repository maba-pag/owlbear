/**
 * P2-07: Task detail information architecture — task #1616 (Cycle 3)
 *
 * AC1: Given a non-null task, DetailTab's root element contains exactly four
 *   data-region children in DOM order: task-detail-body → actions → task-detail-metadata → history.
 *   Asserted via direct-child selector on DetailTab's root element
 *   (querySelectorAll(':scope > [data-region]') on the root <div>).
 *
 * AC2: task-detail-metadata region is a static section, not a collapsible control.
 *   Metadata fields are visible immediately so the section is not an empty/no-op affordance.
 *
 * Cycle 3 revision notes:
 *   - AC2 narrowed from "all field-*" to "at least one field-* testid descendant".
 *     Rationale: PAccordion CSS-visibility contract is proved by any single queryable
 *     descendant — individual field rendering is a separate concern owned by DetailTab.test.tsx.
 *   - AC1 refined: direct-child scoping (not deep query); non-null precondition explicit.
 *   - Metadata is now a plain section; the prior accordion affordance was removed by #1701.
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

  // ─── AC2: task-detail-metadata is static readable content ────────────────

  describe('AC2: task-detail-metadata is visible static content', () => {
    it('element with data-region="task-detail-metadata" is a section, not a p-accordion', () => {
      const { container } = renderDetail()
      const metadataEl = container.querySelector('[data-region="task-detail-metadata"]')
      expect(metadataEl).not.toBeNull()
      expect(metadataEl?.tagName.toLowerCase()).toBe('section')
    })

    it('task-detail-metadata does not expose a collapsible accordion affordance', () => {
      const { container } = renderDetail()
      expect(container.querySelector('p-accordion[data-region="task-detail-metadata"]')).toBeNull()
    })

    it('task-detail-metadata has a visible Metadata heading', () => {
      const { container } = renderDetail()
      const metadata = container.querySelector('[data-region="task-detail-metadata"]')
      expect(metadata?.textContent).toContain('Metadata')
    })

    it('at least one field-* testid descendant is queryable inside metadata', () => {
      const { container } = renderDetail()
      const metadata = container.querySelector('[data-region="task-detail-metadata"]')
      // Checks field-id as representative sample — individual field rendering is owned elsewhere.
      expect(
        metadata?.querySelector('[data-testid="field-id"]'),
        'field-id must be in metadata DOM',
      ).not.toBeNull()
    })
  })
})
