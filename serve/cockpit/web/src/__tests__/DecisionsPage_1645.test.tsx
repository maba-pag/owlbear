/**
 * Task #1645 — P2-01: Decisions list page with empty state
 *
 * AC1: DecisionsPage renders a full-width single-column list of pending DRs from
 *      useDRState().items; each list item displays agent, request_type, relative age
 *      (d/h/m format matching DecisionViewport formatAge), task_id, and body_preview
 *      (truncated to 200 characters); the root element retains data-testid='decisions-page'
 * AC2: When useDRState().items is empty AND isLoading is false AND error is null,
 *      DecisionsPage renders an empty-state element with data-testid='decisions-empty-state'
 *      and a 'nothing to decide' message
 * AC3: DecisionsPage list items have generous vertical spacing (gap >= 16px between items);
 *      each item is identified by data-testid='dr-item-{id}' and calls setSelectedDRId(item.id)
 *      on click
 *
 * RED phase: DecisionsPage.tsx is a skeleton (<section data-testid="decisions-page" />)
 * with no list rendering, no useDRState consumption, no empty state, no click handling.
 * All tests that require list items, empty state, or click behavior fail.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── Directory helpers ─────────────────────────────────────────────────────────

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const webSrcDir = resolve(__dirname, '..') // src/__tests__/.. = src/

// ─── Hoisted mock stubs ────────────────────────────────────────────────────────

const mockSetSelectedDRId = vi.hoisted(() => vi.fn())
const mockUseDRState = vi.hoisted(() => vi.fn())

// ─── Module mocks ──────────────────────────────────────────────────────────────

vi.mock('../hooks/CockpitProvider', () => ({
  useDRState: mockUseDRState,
}))

// ─── Imports (after vi.mock registrations) ────────────────────────────────────

import DecisionsPage from '../pages/DecisionsPage'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BODY_PREVIEW_OVER_200 = 'X'.repeat(201)
const BODY_PREVIEW_EXACTLY_200 = 'Y'.repeat(200)

const DR_A: PendingDR = {
  id: 'dr-a-001',
  task_id: 100,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 30 * 60_000).toISOString(), // ~30 min ago
  title: 'Scope decision A',
  body: 'Full body text for DR A',
  body_preview: 'Preview text for DR A — a short preview that is well within limits.',
}

const DR_B: PendingDR = {
  id: 'dr-b-002',
  task_id: 200,
  agent: 'architect',
  request_type: 'user-action',
  created: new Date(Date.now() - 3 * 3_600_000).toISOString(), // ~3h ago
  title: 'User action B',
  body: 'Full body text for DR B',
  body_preview: 'Preview text for DR B — another short, distinct preview.',
}

const DR_LONG_PREVIEW: PendingDR = {
  id: 'dr-long-001',
  task_id: 300,
  agent: 'reviewer',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 60_000).toISOString(),
  title: 'Long preview DR',
  body: 'Full body',
  body_preview: BODY_PREVIEW_OVER_200,
}

const DR_EXACT_200_PREVIEW: PendingDR = {
  id: 'dr-exact-001',
  task_id: 400,
  agent: 'test-writer',
  request_type: 'user-action',
  created: new Date(Date.now() - 60_000).toISOString(),
  title: 'Exact 200 preview DR',
  body: 'Full body',
  body_preview: BODY_PREVIEW_EXACTLY_200,
}

// Fixed timestamp for age format tests
const FIXED_NOW = new Date('2026-05-19T12:00:00.000Z').getTime()

const DR_RECENT: PendingDR = {
  id: 'dr-recent-001',
  task_id: 500,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(FIXED_NOW - 45 * 60_000).toISOString(), // 45 min ago → "45m ago"
  title: 'Recent DR',
  body: 'body',
  body_preview: 'recent preview',
}

const DR_HOURS: PendingDR = {
  id: 'dr-hours-001',
  task_id: 501,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(FIXED_NOW - 90 * 60_000).toISOString(), // 90 min ago → "1h ago"
  title: 'Hours DR',
  body: 'body',
  body_preview: 'hours preview',
}

const DR_DAYS: PendingDR = {
  id: 'dr-days-001',
  task_id: 502,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(FIXED_NOW - 48 * 3_600_000).toISOString(), // 48h ago → "2d ago"
  title: 'Days DR',
  body: 'body',
  body_preview: 'days preview',
}

// ─── DR state factory ──────────────────────────────────────────────────────────

function makeDRState(overrides: {
  items?: PendingDR[]
  isLoading?: boolean
  error?: Error | null
} = {}) {
  const items = overrides.items ?? []
  return {
    count: items.length,
    items,
    isLoading: overrides.isLoading ?? false,
    error: overrides.error ?? null,
    refetch: vi.fn(),
    selectedDRId: null as string | null,
    setSelectedDRId: mockSetSelectedDRId,
    selectedDR: null,
  }
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderPage(overrides: Parameters<typeof makeDRState>[0] = {}) {
  mockUseDRState.mockReturnValue(makeDRState(overrides))
  return render(<DecisionsPage />)
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_DecisionsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ─── AC1: Full-width list of pending DRs ─────────────────────────────────────

  describe('AC1: full-width single-column list of pending DRs from useDRState().items', () => {
    // Regression guard: root testid preserved — combined with list assertion to fail in RED

    it('ac1 regression: root element retains data-testid="decisions-page" when items are populated', () => {
      const { getByTestId, container } = renderPage({ items: [DR_A] })
      // Root testid preserved (regression)
      expect(getByTestId('decisions-page')).toBeInTheDocument()
      // Combined: list item must also render — fails in RED where skeleton is an empty section
      expect(container.querySelector('[data-testid="dr-item-dr-a-001"]')).not.toBeNull()
    })

    it('ac1 happy: renders one list item per DR in useDRState().items', () => {
      const { container } = renderPage({ items: [DR_A, DR_B] })
      expect(container.querySelector('[data-testid="dr-item-dr-a-001"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="dr-item-dr-b-002"]')).not.toBeNull()
    })

    it('ac1 happy: each item renders the agent field', () => {
      const { container } = renderPage({ items: [DR_A] })
      const item = container.querySelector('[data-testid="dr-item-dr-a-001"]')
      expect(item).not.toBeNull()
      expect(item!.textContent).toContain(DR_A.agent)
    })

    it('ac1 happy: each item renders the request_type field', () => {
      const { container } = renderPage({ items: [DR_A] })
      const item = container.querySelector('[data-testid="dr-item-dr-a-001"]')
      expect(item!.textContent).toContain(DR_A.request_type)
    })

    it('ac1 happy: each item renders the task_id', () => {
      const { container } = renderPage({ items: [DR_A] })
      const item = container.querySelector('[data-testid="dr-item-dr-a-001"]')
      expect(item!.textContent).toContain(String(DR_A.task_id))
    })

    it('ac1 happy: each item renders body_preview', () => {
      const { container } = renderPage({ items: [DR_A] })
      const item = container.querySelector('[data-testid="dr-item-dr-a-001"]')
      expect(item!.textContent).toContain(DR_A.body_preview)
    })

    it('ac1 edge: body_preview truncated to 200 chars when longer than 200 chars', () => {
      const { container } = renderPage({ items: [DR_LONG_PREVIEW] })
      const item = container.querySelector('[data-testid="dr-long-001"]')
      expect(item).not.toBeNull()
      // First 200 chars of the overlong preview must appear
      expect(item!.textContent).toContain(BODY_PREVIEW_OVER_200.slice(0, 200))
      // The full 201-char string must NOT appear (201st char must be cut)
      expect(item!.textContent).not.toContain(BODY_PREVIEW_OVER_200)
    })

    it('ac1 boundary: body_preview not truncated when exactly 200 chars', () => {
      const { container } = renderPage({ items: [DR_EXACT_200_PREVIEW] })
      const item = container.querySelector('[data-testid="dr-exact-001"]')
      expect(item).not.toBeNull()
      // All 200 chars must appear — no truncation at the boundary
      expect(item!.textContent).toContain(BODY_PREVIEW_EXACTLY_200)
    })

    it('ac1 happy: each item renders a relative age in d/h/m format', () => {
      const { container } = renderPage({ items: [DR_A] })
      const item = container.querySelector('[data-testid="dr-item-dr-a-001"]')
      expect(item).not.toBeNull()
      // Age must match the d/h/m pattern (e.g. "30m ago", "3h ago", "2d ago")
      expect(item!.textContent).toMatch(/\d+[dhm]\s+ago/i)
    })

    it('ac1 edge: age shows minutes (Xm ago) for items less than 60 minutes old', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date(FIXED_NOW))
      try {
        const { container } = renderPage({ items: [DR_RECENT] })
        const item = container.querySelector('[data-testid="dr-recent-001"]')
        expect(item).not.toBeNull()
        expect(item!.textContent).toMatch(/45m ago/)
      } finally {
        vi.useRealTimers()
      }
    })

    it('ac1 edge: age shows hours (Xh ago) for items 60–1439 minutes old', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date(FIXED_NOW))
      try {
        const { container } = renderPage({ items: [DR_HOURS] })
        const item = container.querySelector('[data-testid="dr-hours-001"]')
        expect(item).not.toBeNull()
        expect(item!.textContent).toMatch(/1h ago/)
      } finally {
        vi.useRealTimers()
      }
    })

    it('ac1 boundary: age shows days (Xd ago) for items >= 24 hours old', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date(FIXED_NOW))
      try {
        const { container } = renderPage({ items: [DR_DAYS] })
        const item = container.querySelector('[data-testid="dr-days-001"]')
        expect(item).not.toBeNull()
        expect(item!.textContent).toMatch(/2d ago/)
      } finally {
        vi.useRealTimers()
      }
    })

    it('ac1 edge: renders all items when multiple DRs are provided (no items dropped)', () => {
      const three = [DR_A, DR_B, DR_RECENT]
      const { container } = renderPage({ items: three })
      const rendered = container.querySelectorAll('[data-testid^="dr-item-"]')
      expect(rendered.length).toBe(three.length)
    })
  })

  // ─── AC2: Empty state ──────────────────────────────────────────────────────────

  describe('AC2: empty state when items=[] AND isLoading=false AND error=null', () => {
    it('ac2 happy: renders element with data-testid="decisions-empty-state" when conditions met', () => {
      const { container } = renderPage({ items: [], isLoading: false, error: null })
      expect(container.querySelector('[data-testid="decisions-empty-state"]')).not.toBeNull()
    })

    it('ac2 happy: empty state contains "nothing to decide" message (case-insensitive)', () => {
      const { container } = renderPage({ items: [], isLoading: false, error: null })
      const emptyState = container.querySelector('[data-testid="decisions-empty-state"]')
      expect(emptyState).not.toBeNull()
      expect(emptyState!.textContent!.toLowerCase()).toContain('nothing to decide')
    })

    it('ac2 edge: empty state is absent when isLoading=true — combined with page presence', () => {
      // decisions-page must still render while loading (regression), but empty state must not
      const { getByTestId, container } = renderPage({ items: [], isLoading: true })
      expect(getByTestId('decisions-page')).toBeInTheDocument()
      expect(container.querySelector('[data-testid="decisions-empty-state"]')).toBeNull()
      // decisions-page must have children (loading indicator) — not an empty skeleton
      expect(getByTestId('decisions-page').childElementCount).toBeGreaterThan(0)
    })

    it('ac2 edge: empty state is absent when error is set — component must surface an error indication instead', () => {
      const { container } = renderPage({ items: [], isLoading: false, error: new Error('fetch failed') })
      expect(container.querySelector('[data-testid="decisions-empty-state"]')).toBeNull()
      // decisions-page has children (error state) — fails in RED (skeleton is empty section)
      const page = container.querySelector('[data-testid="decisions-page"]')!
      expect(page.childElementCount).toBeGreaterThan(0)
    })

    it('ac2 boundary: empty state absent when items is non-empty — combined with item presence', () => {
      const { container } = renderPage({ items: [DR_A] })
      // List item must be present (fails in RED since skeleton renders nothing)
      expect(container.querySelector('[data-testid="dr-item-dr-a-001"]')).not.toBeNull()
      // And empty state must be absent
      expect(container.querySelector('[data-testid="decisions-empty-state"]')).toBeNull()
    })
  })

  // ─── AC3: Item testids, click handler, vertical spacing ─────────────────────

  describe('AC3: item testids, setSelectedDRId on click, gap >= 16px', () => {
    it('ac3 happy: each item has data-testid="dr-item-{id}"', () => {
      const { container } = renderPage({ items: [DR_A, DR_B] })
      expect(container.querySelector('[data-testid="dr-item-dr-a-001"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="dr-item-dr-b-002"]')).not.toBeNull()
    })

    it('ac3 happy: clicking an item calls setSelectedDRId with that item.id', () => {
      const { container } = renderPage({ items: [DR_A] })
      const item = container.querySelector('[data-testid="dr-item-dr-a-001"]')
      expect(item).not.toBeNull()
      fireEvent.click(item!)
      expect(mockSetSelectedDRId).toHaveBeenCalledOnce()
      expect(mockSetSelectedDRId).toHaveBeenCalledWith('dr-a-001')
    })

    it('ac3 happy: clicking item A calls setSelectedDRId with dr-a-001, not dr-b-002', () => {
      const { container } = renderPage({ items: [DR_A, DR_B] })
      fireEvent.click(container.querySelector('[data-testid="dr-item-dr-a-001"]')!)
      expect(mockSetSelectedDRId).toHaveBeenCalledWith('dr-a-001')
      expect(mockSetSelectedDRId).not.toHaveBeenCalledWith('dr-b-002')
    })

    it('ac3 happy: clicking item B calls setSelectedDRId with dr-b-002', () => {
      const { container } = renderPage({ items: [DR_A, DR_B] })
      fireEvent.click(container.querySelector('[data-testid="dr-item-dr-b-002"]')!)
      expect(mockSetSelectedDRId).toHaveBeenCalledWith('dr-b-002')
    })

    it('ac3 boundary: list items are rendered as siblings in a shared list container', () => {
      // Structural requirement for gap layout — fails in RED (skeleton renders no list)
      const { container } = renderPage({ items: [DR_A, DR_B] })
      const page = container.querySelector('[data-testid="decisions-page"]')!
      const itemA = page.querySelector('[data-testid="dr-item-dr-a-001"]')
      const itemB = page.querySelector('[data-testid="dr-item-dr-b-002"]')
      expect(itemA).not.toBeNull()
      expect(itemB).not.toBeNull()
      // Siblings must share a direct parent (the list container)
      const listContainer = itemA!.parentElement
      expect(listContainer).not.toBeNull()
      expect(itemB!.parentElement).toBe(listContainer)
    })

    it('ac3 boundary: list container has gap >= 16px between items (CSS or inline style)', () => {
      // Primary guard: items must render (fails in RED)
      const { container } = renderPage({ items: [DR_A, DR_B] })
      const page = container.querySelector('[data-testid="decisions-page"]')!
      const drItems = [...page.querySelectorAll('[data-testid^="dr-item-"]')]
      expect(drItems.length).toBe(2)

      const listContainer = drItems[0].parentElement!

      // Attempt 1: inline style (works for React style={{gap: '1rem'}} patterns)
      const inlineGapStr = listContainer.style.gap || listContainer.style.rowGap
      if (inlineGapStr) {
        const inlineGapPx = inlineGapStr.endsWith('rem')
          ? parseFloat(inlineGapStr) * 16
          : parseFloat(inlineGapStr)
        expect(inlineGapPx).toBeGreaterThanOrEqual(16)
        return
      }

      // Attempt 2: CSS file — scan pages/ for any Decision-related CSS
      // jsdom cannot compute CSS from stylesheets, so we read the file directly
      const pagesDir = resolve(webSrcDir, 'pages')
      let cssContent = ''
      try {
        const cssFiles = readdirSync(pagesDir).filter(
          (f) =>
            f.toLowerCase().includes('decision') && (f.endsWith('.css') || f.endsWith('.scss')),
        )
        cssContent = cssFiles.map((f) => readFileSync(resolve(pagesDir, f), 'utf8')).join('\n')
      } catch {
        // pagesDir not readable — will fail the assertion below
      }

      // Look for any gap or row-gap rule >= 16px (16px or 1rem+)
      const gapMatches = [...cssContent.matchAll(/(?:row-)?gap:\s*(\d+(?:\.\d+)?)(px|rem)/g)]
      const hasAdequateGap = gapMatches.some(([, value, unit]) => {
        const px = unit === 'px' ? parseFloat(value) : parseFloat(value) * 16
        return px >= 16
      })
      expect(
        hasAdequateGap,
        'List container must have gap >= 16px defined in inline style or CSS file',
      ).toBe(true)
    })
  })

  // ─── AC4: Root width 100% and list container column direction ────────────────

  describe('AC4: root section width 100%, list container flexDirection column (inline style or CSS)', () => {
    it('ac4 happy: root section has width 100% via inline style or CSS', () => {
      const { container } = renderPage({ items: [DR_A] })
      const root = container.querySelector('[data-testid="decisions-page"]') as HTMLElement
      expect(root).not.toBeNull()

      // Attempt 1: inline style
      if (root.style.width) {
        expect(root.style.width).toBe('100%')
        return
      }

      // Attempt 2: scan pages/ for Decision-related CSS with a width:100% rule
      const pagesDir = resolve(webSrcDir, 'pages')
      let cssContent = ''
      try {
        const cssFiles = readdirSync(pagesDir).filter(
          (f) =>
            f.toLowerCase().includes('decision') && (f.endsWith('.css') || f.endsWith('.scss')),
        )
        cssContent = cssFiles.map((f) => readFileSync(resolve(pagesDir, f), 'utf8')).join('\n')
      } catch {
        // pagesDir not readable — fall through to assertion failure
      }

      const hasFullWidth = /width:\s*100%/.test(cssContent)
      expect(
        hasFullWidth,
        'Root decisions-page section must have width 100% via inline style or CSS',
      ).toBe(true)
    })

    it('ac4 happy: list container (direct parent of dr-item-{id}) uses column direction via inline style or CSS', () => {
      const { container } = renderPage({ items: [DR_A, DR_B] })
      const page = container.querySelector('[data-testid="decisions-page"]')!
      const drItems = [...page.querySelectorAll('[data-testid^="dr-item-"]')]
      expect(drItems.length).toBeGreaterThan(0)

      const listContainer = drItems[0].parentElement as HTMLElement
      expect(listContainer).not.toBeNull()

      // Attempt 1: inline style
      if (listContainer.style.flexDirection) {
        expect(listContainer.style.flexDirection).toBe('column')
        return
      }

      // Attempt 2: scan pages/ for Decision-related CSS with a flex-direction:column rule
      const pagesDir = resolve(webSrcDir, 'pages')
      let cssContent = ''
      try {
        const cssFiles = readdirSync(pagesDir).filter(
          (f) =>
            f.toLowerCase().includes('decision') && (f.endsWith('.css') || f.endsWith('.scss')),
        )
        cssContent = cssFiles.map((f) => readFileSync(resolve(pagesDir, f), 'utf8')).join('\n')
      } catch {
        // pagesDir not readable — fall through to assertion failure
      }

      const hasColumnDirection = /flex-direction:\s*column/.test(cssContent)
      expect(
        hasColumnDirection,
        'List container must have flex-direction:column via inline style or CSS',
      ).toBe(true)
    })

    it('ac4 boundary: root width assertion is discriminating — value must be exactly 100% not a partial match', () => {
      // Guard: ensures the test would fail for e.g. width:50% or width:auto
      const { container } = renderPage({ items: [DR_A] })
      const root = container.querySelector('[data-testid="decisions-page"]') as HTMLElement
      expect(root).not.toBeNull()

      if (root.style.width) {
        // Explicit exact-value check: only '100%' passes
        expect(root.style.width).toBe('100%')
        expect(root.style.width).not.toBe('50%')
        expect(root.style.width).not.toBe('auto')
        return
      }

      // CSS fallback: if no inline style, the CSS must have width:100% specifically
      const pagesDir = resolve(webSrcDir, 'pages')
      let cssContent = ''
      try {
        const cssFiles = readdirSync(pagesDir).filter(
          (f) =>
            f.toLowerCase().includes('decision') && (f.endsWith('.css') || f.endsWith('.scss')),
        )
        cssContent = cssFiles.map((f) => readFileSync(resolve(pagesDir, f), 'utf8')).join('\n')
      } catch {
        // pagesDir not readable — fall through to assertion failure
      }

      expect(/width:\s*100%/.test(cssContent)).toBe(true)
    })

    it('ac4 boundary: column-direction assertion is discriminating — row or unset would fail', () => {
      // Guard: ensures the test would fail if flexDirection were changed to row or removed
      const { container } = renderPage({ items: [DR_A, DR_B] })
      const page = container.querySelector('[data-testid="decisions-page"]')!
      const drItems = [...page.querySelectorAll('[data-testid^="dr-item-"]')]
      expect(drItems.length).toBeGreaterThan(0)

      const listContainer = drItems[0].parentElement as HTMLElement
      expect(listContainer).not.toBeNull()

      if (listContainer.style.flexDirection) {
        expect(listContainer.style.flexDirection).toBe('column')
        expect(listContainer.style.flexDirection).not.toBe('row')
        return
      }

      const pagesDir = resolve(webSrcDir, 'pages')
      let cssContent = ''
      try {
        const cssFiles = readdirSync(pagesDir).filter(
          (f) =>
            f.toLowerCase().includes('decision') && (f.endsWith('.css') || f.endsWith('.scss')),
        )
        cssContent = cssFiles.map((f) => readFileSync(resolve(pagesDir, f), 'utf8')).join('\n')
      } catch {
        // pagesDir not readable — fall through to assertion failure
      }

      expect(/flex-direction:\s*column/.test(cssContent)).toBe(true)
    })
  })
})
