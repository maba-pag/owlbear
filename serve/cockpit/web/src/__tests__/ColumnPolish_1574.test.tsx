/**
 * RED phase tests for #1574: P2-14 — Column polish and empty-state behavior
 *
 * AC-1: Column header renders a JS-normalized label (hyphens → spaces, Title Case) in DOM
 *       textContent — must NOT rely on CSS text-transform (which cannot produce "In Progress"
 *       from "in-progress").
 * AC-2: Empty state (a) uses polished label text, (b) has data-testid="empty-column",
 *       (c) CSS structural: .column-empty font-size ≤ .column header font-size, opacity < 1.
 * AC-4: Column header renders count badge (data-testid="column-count") with numeric task
 *       count and CSS font-size smaller than the header label.
 * AC-5: (recorded in Test-Writer Notes on task body — current failures documented there)
 *
 * RED expectations:
 *   AC-1: Column.tsx renders raw status string → header span textContent is "in-progress"
 *         not "In Progress" → FAIL.
 *   AC-2a: Empty text is "No in-progress tasks" (raw) → assert "No In Progress tasks" → FAIL.
 *   AC-2c: .column-empty font-size (0.875rem) > .column header font-size (0.8125rem) → FAIL.
 *   AC-4: Combined with AC-1 label assertion — fails because label is not yet polished.
 *         CSS font-size regression guard (0.75rem < 0.8125rem) passes; combined into AC-1+AC-4
 *         tests so the AC-1 failure drives the overall test failure.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Column } from '../components/Column'
import type { Task } from '../hooks/useBoard'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const COLUMN_CSS = resolve(__dirname, '..', 'components', 'Column.css')

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeTask(id: number, status: string): Task {
  return {
    id,
    title: `Task ${id}`,
    status,
    priority: 'important',
    updated: '2026-05-14T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
    dep_status: null,
  }
}

function renderColumn(status: string, tasks: Task[]) {
  return render(
    <Column
      status={status}
      tasks={tasks}
      priorities={['someday', 'nice-to-have', 'important', 'needed', 'critical']}
      onContextMenu={() => {}}
      onDragStart={() => {}}
      onDrop={() => {}}
      onDragEnd={() => {}}
      isValidDragTarget={false}
    />,
  )
}

/**
 * Extract the declaration block content for a CSS selector.
 * Returns null when the selector is not found.
 * Sufficient for non-nested single-block CSS rules (Column.css structure).
 */
function getCSSBlock(css: string, selector: string): string | null {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(`${escaped}\\s*\\{([^}]*)\\}`)
  const match = css.match(pattern)
  return match ? match[1] : null
}

// ─── AC-1: Header label normalization ─────────────────────────────────────────
// Header label span textContent must be JS-normalized: hyphens → spaces, Title Case.
// CSS text-transform: capitalize is insufficient — it only capitalizes the first letter
// of each CSS word (whitespace-separated), so "in-progress" → "In-progress" (not "In Progress").
//
// RED: Column.tsx renders raw status prop → textContent equals raw status string → FAIL.

describe('TestFromAC_ColumnHeaderLabel', () => {
  // AC-1: status "todo" → DOM textContent must be "Todo" (not "todo").
  // FAIL: Column.tsx renders <span>todo</span> → textContent is "todo".
  it('renders "Todo" as header label textContent for status "todo" (JS normalization)', () => {
    const { container } = renderColumn('todo', [makeTask(1, 'todo')])
    const labelSpan = container.querySelector('[data-column="todo"] header span:first-child')
    expect(labelSpan, 'header label span must exist').not.toBeNull()
    expect(
      labelSpan!.textContent,
      'header label must be JS-normalized: "todo" → "Todo" in DOM textContent — CSS text-transform does not modify textContent',
    ).toBe('Todo')
  })

  // AC-1: hyphenated status "in-progress" → DOM textContent must be "In Progress".
  // FAIL: Column.tsx renders <span>in-progress</span> → textContent is "in-progress".
  // Critical: CSS text-transform: capitalize produces "In-progress" visually — NOT "In Progress".
  // Only JS normalization (replace hyphens with spaces, then capitalize words) is correct.
  it('renders "In Progress" as header label textContent for status "in-progress" (hyphens → spaces, Title Case)', () => {
    const { container } = renderColumn('in-progress', [makeTask(1, 'in-progress')])
    const labelSpan = container.querySelector('[data-column="in-progress"] header span:first-child')
    expect(labelSpan, 'header label span must exist').not.toBeNull()
    expect(
      labelSpan!.textContent,
      'header label must normalize "in-progress" → "In Progress" in DOM textContent — CSS text-transform cannot produce this result',
    ).toBe('In Progress')
  })

  // AC-1: status "done" → DOM textContent must be "Done" (not "done").
  // FAIL: Column.tsx renders <span>done</span> → textContent is "done".
  it('renders "Done" as header label textContent for status "done" (Title Case)', () => {
    const { container } = renderColumn('done', [makeTask(1, 'done')])
    const labelSpan = container.querySelector('[data-column="done"] header span:first-child')
    expect(labelSpan, 'header label span must exist').not.toBeNull()
    expect(labelSpan!.textContent).toBe('Done')
  })
})

// ─── AC-2: Empty state — polished label, data-testid, CSS font-size ───────────
// (a) Empty state text must use the polished label from AC-1 — rejects raw API strings.
// (b) Container must have data-testid="empty-column".
// (c) CSS structural: .column-empty font-size ≤ .column header font-size; opacity < 1.
//
// RED:
//   AC-2a: empty text is "No in-progress tasks" (raw) → assert "No In Progress tasks" → FAIL.
//   AC-2b: data-testid="empty-column" already exists → combined with AC-2a to fail overall.
//   AC-2c: .column-empty (0.875rem) > .column header (0.8125rem) → font-size assertion FAIL.

describe('TestFromAC_ColumnEmptyStatePolish', () => {
  // AC-2a + AC-2b: empty "in-progress" column must have data-testid="empty-column" AND show
  // polished label text "No In Progress tasks" (not raw "No in-progress tasks").
  // FAIL: current code renders "No in-progress tasks" → textContent assertion fails.
  it('empty-column element shows polished label "No In Progress tasks" for status "in-progress" (AC-2a/b)', () => {
    const { container } = renderColumn('in-progress', [])
    const emptyEl = container.querySelector('[data-testid="empty-column"]')
    expect(
      emptyEl,
      'data-testid="empty-column" must be present for empty column (AC-2b)',
    ).not.toBeNull()
    expect(
      emptyEl!.textContent,
      'empty-state text must use polished label: "No In Progress tasks" — rejects raw "No in-progress tasks" (AC-2a)',
    ).toBe('No In Progress tasks')
  })

  // AC-2a: empty "todo" column must show polished label "No Todo tasks" (not "No todo tasks").
  // FAIL: current code renders "No todo tasks" → assertion fails.
  it('empty-column element shows polished label "No Todo tasks" for status "todo" (AC-2a)', () => {
    const { container } = renderColumn('todo', [])
    const emptyEl = container.querySelector('[data-testid="empty-column"]')
    expect(emptyEl, 'data-testid="empty-column" must be present').not.toBeNull()
    expect(emptyEl!.textContent).toBe('No Todo tasks')
  })

  // AC-2c: CSS structural — .column-empty font-size must be ≤ .column header font-size.
  // Current state: .column-empty → 0.875rem; .column header → 0.8125rem (empty text LARGER).
  // FAIL: 0.875 > 0.8125 → lessThanOrEqual assertion fails.
  // Also asserts opacity < 1 (0.6) as a spec guard — combined so font-size failure drives result.
  it('.column-empty font-size is ≤ .column header font-size and opacity < 1 (CSS structural, AC-2c)', () => {
    const css = readFileSync(COLUMN_CSS, 'utf-8')
    const headerBlock = getCSSBlock(css, '.column header')
    const emptyBlock = getCSSBlock(css, '.column-empty')
    expect(headerBlock, '.column header block must exist in Column.css').not.toBeNull()
    expect(emptyBlock, '.column-empty block must exist in Column.css').not.toBeNull()

    const headerFontSizeMatch = headerBlock!.match(/font-size\s*:\s*([\d.]+)rem/)
    const emptyFontSizeMatch = emptyBlock!.match(/font-size\s*:\s*([\d.]+)rem/)
    expect(headerFontSizeMatch, '.column header must declare font-size in rem').not.toBeNull()
    expect(emptyFontSizeMatch, '.column-empty must declare font-size in rem').not.toBeNull()

    const headerFontSize = parseFloat(headerFontSizeMatch![1])
    const emptyFontSize = parseFloat(emptyFontSizeMatch![1])
    expect(
      emptyFontSize,
      `empty-state font-size (${emptyFontSize}rem) must be ≤ header font-size (${headerFontSize}rem) — currently the empty text is LARGER than the column header (AC-2c)`,
    ).toBeLessThanOrEqual(headerFontSize)

    // Also verify opacity < 1 (dimmed state — spec guard, passes with current 0.6).
    const opacityMatch = emptyBlock!.match(/opacity\s*:\s*([\d.]+)/)
    expect(opacityMatch, '.column-empty must declare opacity').not.toBeNull()
    const opacity = parseFloat(opacityMatch![1])
    expect(
      opacity,
      `empty-state opacity (${opacity}) must be < 1 — empty column must be visually dimmed (AC-2c)`,
    ).toBeLessThan(1)
  })
})

// ─── AC-4: Count badge — data-testid, numeric count, CSS font-size < header ──
// Column header must render count badge (data-testid="column-count") with numeric task count.
// Badge font-size must be smaller than the header label font-size.
//
// Strategy: DOM assertions are combined with AC-1 label polishing assertions so the AC-1
// failure (raw label) drives the overall test failure. CSS structural font-size comparison
// (0.75rem < 0.8125rem) passes as a regression guard — included to specify the contract.

describe('TestFromAC_ColumnCountBadge', () => {
  // AC-4: header has polished label "In Progress" AND count badge shows task count.
  // FAIL: header label textContent is "in-progress" (not polished) → AC-1 assertion fails.
  // Once builder fixes AC-1 label, the badge count assertion becomes the relevant check.
  it('column header renders polished label "In Progress" alongside count badge showing task count (AC-1 + AC-4)', () => {
    const { container } = renderColumn('in-progress', [
      makeTask(1, 'in-progress'),
      makeTask(2, 'in-progress'),
    ])

    // AC-1: polished label — FAILS currently (textContent is "in-progress").
    const labelSpan = container.querySelector('[data-column="in-progress"] header span:first-child')
    expect(labelSpan, 'header label span must exist').not.toBeNull()
    expect(
      labelSpan!.textContent,
      'header label must be polished "In Progress" — AC-1 normalization must be applied (AC-1)',
    ).toBe('In Progress')

    // AC-4: count badge exists with correct numeric count.
    const badge = container.querySelector('[data-column="in-progress"] [data-testid="column-count"]')
    expect(badge, 'data-testid="column-count" badge must be present in the header (AC-4)').not.toBeNull()
    expect(
      badge!.textContent,
      'count badge must display numeric task count: 2 tasks (AC-4)',
    ).toBe('2')
  })

  // AC-4: empty column has polished label "Todo" AND count badge shows 0.
  // FAIL: header label textContent is "todo" (not polished) → AC-1 assertion fails.
  it('empty column renders polished label "Todo" alongside count badge showing 0 (AC-1 + AC-4)', () => {
    const { container } = renderColumn('todo', [])

    // AC-1: polished label — FAILS currently (textContent is "todo").
    const labelSpan = container.querySelector('[data-column="todo"] header span:first-child')
    expect(labelSpan, 'header label span must exist').not.toBeNull()
    expect(
      labelSpan!.textContent,
      'header label must be polished "Todo" for empty column (AC-1)',
    ).toBe('Todo')

    // AC-4: count badge shows 0 for empty column.
    const badge = container.querySelector('[data-column="todo"] [data-testid="column-count"]')
    expect(badge, 'count badge must be present even for empty column (AC-4)').not.toBeNull()
    expect(badge!.textContent, 'count badge must show 0 for empty column (AC-4)').toBe('0')
  })

  // AC-4: empty column has polished label "Research" AND count badge shows 0.
  // FAIL: header label textContent is "research" (not polished) → AC-1 assertion fails.
  // CSS font-size contract (count < header) is embedded: both are checked once AC-1 is fixed.
  it('empty column renders polished label "Research" alongside count badge showing 0 (AC-1 + AC-4)', () => {
    const { container } = renderColumn('research', [])

    // AC-1: polished label — FAILS currently (textContent is "research").
    const labelSpan = container.querySelector('[data-column="research"] header span:first-child')
    expect(labelSpan, 'header label span must exist').not.toBeNull()
    expect(
      labelSpan!.textContent,
      'header label must be polished "Research" for empty column (AC-1)',
    ).toBe('Research')

    // AC-4: count badge shows 0 for empty column.
    const badge = container.querySelector('[data-column="research"] [data-testid="column-count"]')
    expect(badge, 'count badge must be present even for empty column (AC-4)').not.toBeNull()
    expect(badge!.textContent, 'count badge must show 0 for empty column (AC-4)').toBe('0')

    // AC-4: CSS structural — count font-size < header font-size (spec guard).
    const css = readFileSync(COLUMN_CSS, 'utf-8')
    const headerBlock = getCSSBlock(css, '.column header')
    const countBlock = getCSSBlock(css, '.column-count')
    expect(headerBlock, '.column header block must exist in Column.css').not.toBeNull()
    expect(countBlock, '.column-count block must exist in Column.css').not.toBeNull()
    const headerFontSize = parseFloat(headerBlock!.match(/font-size\s*:\s*([\d.]+)rem/)![1])
    const countFontSize = parseFloat(countBlock!.match(/font-size\s*:\s*([\d.]+)rem/)![1])
    expect(
      countFontSize,
      `count badge font-size (${countFontSize}rem) must be < header font-size (${headerFontSize}rem) — badge visually subordinate to label (AC-4)`,
    ).toBeLessThan(headerFontSize)
  })
})
