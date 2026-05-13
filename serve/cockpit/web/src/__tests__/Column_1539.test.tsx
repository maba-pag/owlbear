/**
 * Column component CSS: fixed header, scroll body, empty text fallback.
 * Task: #1539 (test-writer RED phase)
 *
 * AC-1: Column root has <header> direct child AND separate sibling body container
 *       (data-testid="column-body") — header is NOT inside the scrollable region.
 * AC-2: Dual-proof overflow — (a) body container has a CSS class via classList;
 *       (b) Column.css file contains overflow-y: auto on that class (regex).
 * AC-3: Dual-proof empty state — (a) renders "No {status} tasks" for empty column;
 *       (b) Column.css file contains centering declarations on the empty-state class.
 *
 * RED expectations:
 *   - Column.tsx has no data-testid="column-body" sibling → AC-1 / AC-2a fail.
 *   - Column.css does not exist → AC-2b / AC-3b fail (ENOENT on readFileSync).
 *   - Column.tsx renders "No tasks" (static) not "No {status} tasks" → AC-3a fails.
 *
 * Column.css is created by impl task #1547.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import fs from 'node:fs'
import path from 'node:path'
import { Column } from '../components/Column'
import type { Task } from '../hooks/useBoard'

// ─── File paths ───────────────────────────────────────────────────────────────

const COLUMN_CSS = path.resolve(__dirname, '../components/Column.css')

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeTask(id: number, status: string): Task {
  return {
    id,
    title: `Task ${id}`,
    status,
    priority: 'important',
    updated: '2026-05-13T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
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

// ─── AC-1: Structural separation — <header> + sibling body container ──────────
// Column root must have <header> as a direct child AND a separate sibling
// body container identified by data-testid="column-body".
// Header must NOT be inside the scrollable body region.
//
// RED: Column.tsx has no data-testid="column-body" element → all 3 tests fail.

describe('TestFromAC_ColumnStructure', () => {
  // AC-1: column root must have both <header> direct child AND column-body sibling.
  // FAIL: data-testid="column-body" does not exist in current Column.tsx.
  it('column root has <header> direct child AND sibling data-testid="column-body" container', () => {
    const { container } = renderColumn('todo', [makeTask(1, 'todo')])
    const root = container.querySelector('[data-column="todo"]')
    expect(root, 'Column root [data-column] must exist').not.toBeNull()

    const header = root?.querySelector(':scope > header')
    expect(header, 'Column root must have a direct <header> child').not.toBeNull()

    const body = root?.querySelector(':scope > [data-testid="column-body"]')
    expect(
      body,
      'Column root must have a direct child with data-testid="column-body" (body container for scrollable tasks)',
    ).not.toBeNull()
  })

  // AC-1: <header> must be a sibling of column-body, NOT nested inside it.
  // This proves structural separation: header is outside the scrollable region.
  // FAIL: column-body does not exist → querySelector on it returns null → expect fails.
  it('header element is NOT nested inside the column-body container', () => {
    const { container } = renderColumn('todo', [makeTask(1, 'todo')])
    const body = container.querySelector('[data-testid="column-body"]')
    expect(
      body,
      'column-body must exist — this test proves header is outside the scrollable region',
    ).not.toBeNull()

    const headerInsideBody = body!.querySelector('header')
    expect(
      headerInsideBody,
      'header must NOT be nested inside column-body — it must be a sibling at the root level',
    ).toBeNull()
  })

  // AC-1: structural separation must hold even when tasks array is empty (empty state).
  // FAIL: column-body does not exist in Column.tsx.
  it('column-body sibling exists even when tasks array is empty (empty state)', () => {
    const { container } = renderColumn('research', [])
    const root = container.querySelector('[data-column="research"]')
    const body = root?.querySelector(':scope > [data-testid="column-body"]')
    expect(
      body,
      'column-body must exist when tasks is empty — structural separation applies to all states',
    ).not.toBeNull()
  })
})

// ─── AC-2: Overflow CSS — body class presence + Column.css source contract ───
// (a) Body container must have a CSS class on its classList (not inline-only).
// (b) Column.css file must contain overflow-y: auto for the body class.
//
// RED: column-body does not exist (2a fails); Column.css does not exist (2b fails with ENOENT).

describe('TestFromAC_ColumnOverflow', () => {
  // AC-2a: body container must have a CSS class — proves CSS wiring, not just inline style.
  // FAIL: data-testid="column-body" does not exist in current Column.tsx.
  it('column-body container has at least one CSS class on its classList', () => {
    const { container } = renderColumn('todo', [makeTask(1, 'todo'), makeTask(2, 'todo')])
    const body = container.querySelector('[data-testid="column-body"]') as HTMLElement | null
    expect(body, 'column-body must exist').not.toBeNull()
    expect(
      body!.classList.length,
      'column-body must have a CSS class (the class is what carries overflow-y: auto from Column.css)',
    ).toBeGreaterThan(0)
  })

  // AC-2b: Column.css file must exist alongside Column.tsx.
  // FAIL: Column.css does not exist yet (created by impl task #1547).
  it('Column.css file exists alongside Column.tsx', () => {
    expect(
      fs.existsSync(COLUMN_CSS),
      `Column.css must exist at ${COLUMN_CSS} — created by impl task #1547`,
    ).toBe(true)
  })

  // AC-2b: Column.css must declare overflow-y: auto for the scrollable body class.
  // FAIL: Column.css does not exist → fs.readFileSync throws ENOENT.
  it('Column.css contains overflow-y: auto declaration for the body/scroll container class', () => {
    const css = fs.readFileSync(COLUMN_CSS, 'utf-8')
    expect(
      css,
      'Column.css must contain overflow-y: auto for the body container class',
    ).toMatch(/overflow-y\s*:\s*auto/)
  })
})

// ─── AC-3: Empty state — parameterized text + Column.css centering ────────────
// (a) Empty column must display "No {status} tasks" (parameterized by status prop).
// (b) Column.css must contain centering declarations on the empty-state class.
//
// RED: current empty text is "No tasks" (static) → 3a tests fail.
//      Column.css does not exist → 3b test fails with ENOENT.

describe('TestFromAC_ColumnEmptyState', () => {
  // AC-3a: empty todo column must display "No todo tasks".
  // FAIL: current Column.tsx renders "No tasks" (static), not "No todo tasks".
  it('renders "No todo tasks" when status is "todo" and tasks array is empty', () => {
    const { container } = renderColumn('todo', [])
    const emptyEl = container.querySelector('[data-testid="empty-column"]')
    expect(emptyEl, 'empty-column element must exist for empty todo column').not.toBeNull()
    expect(
      emptyEl!.textContent,
      'empty state text must be parameterized: "No todo tasks" not the static "No tasks"',
    ).toBe('No todo tasks')
  })

  // AC-3a: empty research column must display "No research tasks".
  // FAIL: current Column.tsx renders "No tasks" (static).
  it('renders "No research tasks" when status is "research" and tasks array is empty', () => {
    const { container } = renderColumn('research', [])
    const emptyEl = container.querySelector('[data-testid="empty-column"]')
    expect(emptyEl, 'empty-column element must exist for empty research column').not.toBeNull()
    expect(emptyEl!.textContent).toBe('No research tasks')
  })

  // AC-3a: empty in-progress column must display "No in-progress tasks" (hyphenated status).
  // FAIL: current Column.tsx renders "No tasks" (static).
  it('renders "No in-progress tasks" when status is "in-progress" and tasks array is empty', () => {
    const { container } = renderColumn('in-progress', [])
    const emptyEl = container.querySelector('[data-testid="empty-column"]')
    expect(emptyEl, 'empty-column element must exist for empty in-progress column').not.toBeNull()
    expect(emptyEl!.textContent).toBe('No in-progress tasks')
  })

  // AC-3b: Column.css must have centering declarations on the empty-state class.
  // FAIL: Column.css does not exist → fs.readFileSync throws ENOENT.
  it('Column.css contains centering declarations on the empty-state class', () => {
    const css = fs.readFileSync(COLUMN_CSS, 'utf-8')
    const hasFlex = /display\s*:\s*flex/.test(css) && /align-items\s*:\s*center/.test(css)
    const hasTextAlign = /text-align\s*:\s*center/.test(css)
    expect(
      hasFlex || hasTextAlign,
      'Column.css must contain centering declarations (flex align-items: center, or text-align: center) on the empty-state class',
    ).toBe(true)
  })
})
