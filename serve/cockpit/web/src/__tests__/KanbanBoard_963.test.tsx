/**
 * Failing tests for #963: Memoize KanbanBoard
 *
 * Structural tests verify React.memo on Card/Column, useMemo on tasksByStatus
 * and column sort, and useCallback on handleContextMenu per the refined AC.
 * All tests are RED (failing) until the builder implements the optimisation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'

// ─── Hook-call tracker (hoisted before all imports) ──────────────────────────
// vi.hoisted ensures the object exists before vi.mock factory runs and before
// any module-level code executes — required to capture memo() calls at module
// evaluation time.

const hookCalls = vi.hoisted(() => ({ memo: 0, useMemo: 0, useCallback: 0 }))

// ─── React mock: wrap memo/useMemo/useCallback with counters ─────────────────
// vi.mock is hoisted before static imports, so memo() calls that happen when
// KanbanBoard.tsx is evaluated (Card = memo(...), Column = memo(...)) are caught.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFn = (...args: any[]) => any

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react')>()
  return {
    ...actual,
    memo: (component: AnyFn, compare?: AnyFn): AnyFn => {
      hookCalls.memo++
      return actual.memo(component, compare)
    },
    useMemo: (factory: AnyFn, deps: unknown[] | undefined): unknown => {
      hookCalls.useMemo++
      return actual.useMemo(factory, deps as any) // eslint-disable-line @typescript-eslint/no-explicit-any
    },
    useCallback: (callback: AnyFn, deps: unknown[]): AnyFn => {
      hookCalls.useCallback++
      return actual.useCallback(callback, deps as any) // eslint-disable-line @typescript-eslint/no-explicit-any
    },
  }
})

// ─── Component imports ────────────────────────────────────────────────────────
// KanbanBoardModule gives access to named exports (Card, Column).
// These will be undefined until the builder adds: export const Card = memo(...)
// Accessed via (KanbanBoardModule as any) to avoid TypeScript compile error.

import KanbanBoard, * as KanbanBoardModule from '../KanbanBoard'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Card = (KanbanBoardModule as any).Card
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Column = (KanbanBoardModule as any).Column

// ─── Mock fixtures ────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [
    { name: 'research' },
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'review' },
    { name: 'docs' },
    { name: 'done' },
  ],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'review'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  } as Record<string, string[]>,
}

const TASKS = {
  tasks: [
    {
      id: 1,
      title: 'Critical task',
      status: 'backlog',
      priority: 'critical',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
    {
      id: 2,
      title: 'Blocked task',
      status: 'todo',
      priority: 'needed',
      tags: [],
      blocked: true,
      block_reason: 'Waiting for API',
      claimed: false,
    },
    {
      id: 3,
      title: 'Active task',
      status: 'in-progress',
      priority: 'important',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: true,
    },
    {
      id: 4,
      title: 'Someday task',
      status: 'backlog',
      priority: 'someday',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
    {
      id: 5,
      title: 'Done task',
      status: 'done',
      priority: 'nice-to-have',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
  ],
  mtime: 1713456000,
}

function stubFetchSuccess() {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/board'))
        return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
      if (url.includes('/api/tasks'))
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS) })
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    }),
  )
}

function stubFetchPending() {
  vi.stubGlobal('fetch', vi.fn(() => new Promise<never>(() => {})))
}

// Render without PDS/router wrappers — KanbanBoard has no PDS or router
// dependencies. Bare render isolates hookCalls counts to KanbanBoard + Column
// + Card only, making useMemo/useCallback counts reliable.
function renderBoard() {
  return render(<KanbanBoard />)
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_MemoizeKanbanBoard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── AC 1: Card wrapped in React.memo ────────────────────────────────────

  describe('Card wrapped in React.memo (AC 1)', () => {
    it('Card is exported as a named export from KanbanBoard', () => {
      // Fails until builder adds: export const Card = memo(function Card(...) { ... })
      expect(Card).toBeDefined()
    })

    it('Card $$typeof equals Symbol.for("react.memo")', () => {
      // Fails if Card is undefined (not exported) or not wrapped with memo()
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      expect((Card as any).$$typeof).toBe(Symbol.for('react.memo'))
    })
  })

  // ─── AC 2: Column wrapped in React.memo ──────────────────────────────────

  describe('Column wrapped in React.memo (AC 2)', () => {
    it('Column is exported as a named export from KanbanBoard', () => {
      expect(Column).toBeDefined()
    })

    it('Column $$typeof equals Symbol.for("react.memo")', () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      expect((Column as any).$$typeof).toBe(Symbol.for('react.memo'))
    })
  })

  // ─── AC 1+2: React.memo call count at module load ────────────────────────

  describe('React.memo applied to Card and Column at module evaluation', () => {
    it('React.memo is called at least twice when the KanbanBoard module is loaded', () => {
      // hookCalls.memo is incremented when memo(Card) and memo(Column) run at
      // module-evaluation time. Currently 0 — no memo wrapping exists.
      // Must be >= 2 after builder wraps both Card and Column.
      expect(hookCalls.memo).toBeGreaterThanOrEqual(2)
    })
  })

  // ─── AC 3+5: useMemo for column sort and tasksByStatus ───────────────────

  describe('useMemo used for column sort (AC 3) and tasksByStatus map (AC 5)', () => {
    it('useMemo is called at least once during a successful board render', async () => {
      stubFetchSuccess()
      hookCalls.useMemo = 0
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelectorAll('[data-column]').length).toBe(7)
      })
      // Currently 0 (no useMemo anywhere in KanbanBoard.tsx)
      expect(hookCalls.useMemo).toBeGreaterThanOrEqual(1)
    })

    it('useMemo called >= 8 times: 1 tasksByStatus (KanbanBoard) + 7 sort (one per Column)', async () => {
      stubFetchSuccess()
      hookCalls.useMemo = 0
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelectorAll('[data-column]').length).toBe(7)
      })
      // 1 KanbanBoard-level useMemo (tasksByStatus) + 7 Column-level useMemo (sort) = 8
      expect(hookCalls.useMemo).toBeGreaterThanOrEqual(8)
    })

    it('useMemo for tasksByStatus is called during loading state (must be before early return)', async () => {
      // With a never-resolving fetch, board stays in loading state forever.
      // tasksByStatus useMemo must be declared before the `if (loading) return` guard
      // per React hooks ordering rules — so it runs even when loading is true.
      stubFetchPending()
      hookCalls.useMemo = 0
      const { container } = renderBoard()
      expect(container.querySelector('[data-testid="loading-indicator"]')).not.toBeNull()
      // Currently 0 — no useMemo in KanbanBoard.tsx
      expect(hookCalls.useMemo).toBeGreaterThanOrEqual(1)
    })
  })

  // ─── AC 4: useCallback for handleContextMenu, before early returns ────────

  describe('useCallback used for handleContextMenu (AC 4)', () => {
    it('useCallback is called at least once during a successful board render', async () => {
      stubFetchSuccess()
      hookCalls.useCallback = 0
      const { container } = renderBoard()
      await waitFor(() => {
        expect(container.querySelectorAll('[data-column]').length).toBe(7)
      })
      // Currently 0 — handleContextMenu is a plain nested function, not useCallback
      expect(hookCalls.useCallback).toBeGreaterThanOrEqual(1)
    })

    it('useCallback is called even in loading state (hooks ordering: must precede early returns)', async () => {
      // handleContextMenu must be converted to useCallback([]) and declared BEFORE
      // the `if (loading) return` guard. If it is placed after the guard, it would
      // (a) never run in loading state and (b) violate React hooks ordering rules.
      stubFetchPending()
      hookCalls.useCallback = 0
      const { container } = renderBoard()
      expect(container.querySelector('[data-testid="loading-indicator"]')).not.toBeNull()
      // Currently 0 — handleContextMenu is defined after the early returns
      expect(hookCalls.useCallback).toBeGreaterThanOrEqual(1)
    })
  })

})
