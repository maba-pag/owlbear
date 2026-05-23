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
import { fireEvent, render } from '@testing-library/react'
import { Column } from '../components/Column'
import type { Task } from '../hooks/useBoard'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeTask(id: number, status: string, overrides: Partial<Task> = {}): Task {
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
    dep_status: null,
    ...overrides,
  }
}

function renderColumn(status: string, tasks: Task[]) {
  return render(
    <Column
      status={status}
      tasks={tasks}
      priorities={['someday', 'nice-to-have', 'important', 'needed', 'critical']}
      onContextMenu={() => {}}
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
  // AC-2a: body container must carry the expected CSS class 'column-body' on its classList.
  // Naming the class proves CSS wiring: the overflow-y rule is attached to THIS selector,
  // not just any selector in the file.
  it('column-body container has the CSS class "column-body" on its classList', () => {
    const { container } = renderColumn('todo', [makeTask(1, 'todo'), makeTask(2, 'todo')])
    const body = container.querySelector('[data-testid="column-body"]') as HTMLElement | null
    expect(body, 'column-body must exist').not.toBeNull()
    expect(
      body!.classList.contains('column-body'),
      'column-body element must have class "column-body" so the overflow-y: auto rule from Column.css is applied',
    ).toBe(true)
  })

  it('column-body is a vertical-only scroll surface', () => {
    const { container } = renderColumn('todo', [makeTask(1, 'todo'), makeTask(2, 'todo')])
    const body = container.querySelector('[data-testid="column-body"]') as HTMLElement | null
    expect(body, 'column-body must exist').not.toBeNull()
    expect(body?.className).toContain('overflow-x-hidden')
    expect(body?.className).toContain('overflow-y-auto')
  })

  // AC-2b: Overflow CSS is now enforced inline via PDS Tailwind utilities in Column.tsx.
  // The old Column.css source-inspection tests are removed since the CSS file is dead.
})

// ─── AC-3: Empty state — parameterized text + Column.css centering ────────────
// (a) Empty column must display "No {status} tasks" (parameterized by status prop).
// (b) Column.css must contain centering declarations on the empty-state class.
//
// RED: current empty text is "No tasks" (static) → 3a tests fail.
//      Column.css does not exist → 3b test fails with ENOENT.

describe('TestFromAC_ColumnEmptyState', () => {
  // AC-3a: empty todo column must display polished label "No Todo tasks".
  // Updated in retry (#1574): #1574 AC-2 supersedes the raw-string contract —
  // implementation normalizes status labels (hyphens→spaces, Title Case) before
  // composing empty-state text, so "todo" → "Todo".
  it('renders "No Todo tasks" when status is "todo" and tasks array is empty', () => {
    const { container } = renderColumn('todo', [])
    const emptyEl = container.querySelector('[data-testid="empty-column"]')
    expect(emptyEl, 'empty-column element must exist for empty todo column').not.toBeNull()
    expect(
      emptyEl!.textContent,
      'empty state text must use polished label: "No Todo tasks" — #1574 AC-2 requires JS-normalized status in empty text',
    ).toBe('No Todo tasks')
  })

  // AC-3a: empty research column must display polished label "No Research tasks".
  // Updated in retry (#1574): polished label contract.
  it('renders "No Research tasks" when status is "research" and tasks array is empty', () => {
    const { container } = renderColumn('research', [])
    const emptyEl = container.querySelector('[data-testid="empty-column"]')
    expect(emptyEl, 'empty-column element must exist for empty research column').not.toBeNull()
    expect(emptyEl!.textContent).toBe('No Research tasks')
  })

  // AC-3a: empty in-progress column must display polished label "No In Progress tasks".
  // Updated in retry (#1574): hyphens → spaces, Title Case — "in-progress" → "In Progress".
  // CSS text-transform: capitalize cannot produce "In Progress" from "in-progress";
  // JS normalization is required and applied before composing empty-state text.
  it('renders "No In Progress tasks" when status is "in-progress" and tasks array is empty', () => {
    const { container } = renderColumn('in-progress', [])
    const emptyEl = container.querySelector('[data-testid="empty-column"]')
    expect(emptyEl, 'empty-column element must exist for empty in-progress column').not.toBeNull()
    expect(emptyEl!.textContent).toBe('No In Progress tasks')
  })

  // AC-3b: Centering CSS is now enforced inline via PDS Tailwind utilities in Column.tsx.
  // The old Column.css source-inspection test is removed since the CSS file is dead.
})

describe('Column lane accent visual system', () => {
  it('uses one neutral lane accent instead of decorative semantic status colors', () => {
    const statuses = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']

    for (const status of statuses) {
      const { container, unmount } = renderColumn(status, [])
      const root = container.querySelector(`[data-column="${status}"]`)
      const classes = root?.getAttribute('class') ?? ''

      expect(classes).toContain('border-t-contrast-low')
      expect(classes).not.toMatch(/border-t-(warning|error|primary|success)/)
      expect(classes).not.toContain('--custom-signal-claimed')

      unmount()
    }
  })
})

describe('Column chrome visual system', () => {
  it('renders columns as quiet lanes without outer contrast border or shadow chrome', () => {
    const { container } = renderColumn('todo', [makeTask(1, 'todo')])
    const root = container.querySelector('[data-column="todo"]')
    const classes = root?.getAttribute('class') ?? ''

    expect(classes).toContain('border-transparent')
    expect(classes).not.toContain('border-contrast-low')
    expect(classes).not.toContain('shadow-sm')
  })

  it('renders empty states as quiet text instead of dashed boxes', () => {
    const { container } = renderColumn('research', [])
    const empty = container.querySelector('[data-testid="empty-column"]')
    const classes = empty?.getAttribute('class') ?? ''

    expect(empty?.textContent).toBe('No Research tasks')
    expect(classes).not.toContain('border-dashed')
    expect(classes).not.toContain('border-contrast-low')
    expect(classes).not.toContain('bg-canvas')
  })

  it('does not expose drag/drop target state on quiet lanes', () => {
    const { container } = renderColumn('todo', [makeTask(1, 'todo')])
    const root = container.querySelector('[data-column="todo"]')

    expect(root?.getAttribute('data-drag-over')).toBeNull()
    expect(root?.getAttribute('class') ?? '').not.toContain('bg-success-frosted')
  })

  it('shows a subtle scroll cue while additional cards continue below the visible body', () => {
    const tasks = Array.from({ length: 6 }, (_, index) => makeTask(index + 1, 'done'))
    const { container } = renderColumn('done', tasks)
    const body = container.querySelector('[data-testid="column-body"]') as HTMLElement | null
    expect(body).not.toBeNull()
    Object.defineProperty(body, 'scrollHeight', { configurable: true, value: 800 })
    Object.defineProperty(body, 'clientHeight', { configurable: true, value: 300 })
    Object.defineProperty(body, 'scrollTop', { configurable: true, value: 0 })

    fireEvent.scroll(body!)

    const cue = container.querySelector('[data-testid="column-scroll-cue"]')
    expect(cue).not.toBeNull()
    expect(cue?.getAttribute('class') ?? '').toContain('absolute')
    expect(cue?.getAttribute('class') ?? '').toContain('bottom-0')
  })

  it('hides the scroll cue when the column body reaches the bottom', () => {
    const tasks = Array.from({ length: 6 }, (_, index) => makeTask(index + 1, 'done'))
    const { container } = renderColumn('done', tasks)
    const body = container.querySelector('[data-testid="column-body"]') as HTMLElement | null
    expect(body).not.toBeNull()
    Object.defineProperty(body, 'scrollHeight', { configurable: true, value: 800 })
    Object.defineProperty(body, 'clientHeight', { configurable: true, value: 300 })
    Object.defineProperty(body, 'scrollTop', { configurable: true, value: 500 })

    fireEvent.scroll(body!)

    expect(container.querySelector('[data-testid="column-scroll-cue"]')).toBeNull()
  })
})

describe('Column default task sorting', () => {
  function renderedTaskIds(container: HTMLElement): string[] {
    return Array.from(container.querySelectorAll('[data-testid="task-card"]')).map((card) => card.getAttribute('data-id') ?? '')
  }

  it('sorts cards by semantic priority descending, then updated timestamp descending', () => {
    const tasks = [
      makeTask(1, 'todo', { priority: 'needed', updated: '2026-05-22T10:00:00Z' }),
      makeTask(2, 'todo', { priority: 'critical', updated: '2026-05-21T10:00:00Z' }),
      makeTask(3, 'todo', { priority: 'critical', updated: '2026-05-22T10:00:00Z' }),
      makeTask(4, 'todo', { priority: 'someday', updated: '2026-05-23T10:00:00Z' }),
    ]
    const { container } = renderColumn('todo', tasks)

    expect(renderedTaskIds(container)).toEqual(['3', '2', '1', '4'])
  })

  it('puts malformed priority and updated values last while keeping a deterministic id tie-break', () => {
    const tasks = [
      makeTask(3, 'todo', { priority: 'unknown', updated: '2026-05-24T10:00:00Z' }),
      makeTask(2, 'todo', { priority: 'critical', updated: 'not-a-date' }),
      makeTask(1, 'todo', { priority: 'critical', updated: '2026-05-24T10:00:00Z' }),
      makeTask(4, 'todo', { priority: 'unknown', updated: '2026-05-24T10:00:00Z' }),
    ]
    const { container } = renderColumn('todo', tasks)

    expect(renderedTaskIds(container)).toEqual(['1', '2', '3', '4'])
  })
})
