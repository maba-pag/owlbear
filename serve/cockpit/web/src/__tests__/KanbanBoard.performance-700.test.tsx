/**
 * 700-task board performance (Vitest / jsdom)
 *
 * Validates that the board renders 700 tasks within the structural DOM budget
 * defined by the AC. Tests use a SEED=42 deterministic LCG fixture for
 * reproducibility across uniform (100/col) and skewed (400 backlog / 150 done /
 * 30 each remaining) distributions.
 *
 * AC: "Vitest structural test: render 700 tasks, assert total DOM node count <5,000"
 * AC: "Mock API serves deterministic 700-task fixture (SEED=42 for reproducibility)"
 *
 * Note — DOM count assertion: research §3.1 estimates ~2,500 nodes for 700 tasks
 * (well within the 5,000 limit). The tests scope to the board container via
 * data-testid="kanban-board" — the builder must add this testid to the board root
 * div so the count can be scoped correctly and tests can pass.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'

// ─── SEED=42 deterministic LCG ────────────────────────────────────────────────
// Linear Congruential Generator — same constants as bench_959.spec.ts.
// Produces identical fixtures across both test suites.

function lcg(seed: number): () => number {
  let s = seed & 0xffffffff
  return () => {
    s = Math.imul(s, 1664525) + 1013904223
    s = s & 0xffffffff
    return (s >>> 0) / 0x100000000
  }
}

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done'] as const
const PRIORITIES = ['someday', 'nice-to-have', 'important', 'needed', 'critical'] as const

interface TaskFixture {
  id: number
  title: string
  status: string
  priority: string
  tags: string[]
  blocked: boolean
  block_reason: string | null
  claimed: boolean
}

/** Uniform: 100 tasks per column, 7 columns × 100 = 700 */
function generateUniformTasks(seed = 42): TaskFixture[] {
  const rand = lcg(seed)
  return Array.from({ length: 700 }, (_, i) => {
    const r1 = rand()
    const r2 = rand()
    const r3 = rand()
    const blocked = r1 < 0.1
    return {
      id: i + 1,
      title: `Task ${i + 1}`,
      status: STATUSES[i % STATUSES.length],
      priority: PRIORITIES[Math.floor(r2 * PRIORITIES.length)],
      tags: [],
      blocked,
      block_reason: blocked ? `Blocked reason ${i + 1}` : null,
      claimed: r3 < 0.15,
    }
  })
}

/** Skewed: 400 backlog / 150 done / 30 each in remaining 5 statuses = 700 */
function generateSkewedTasks(seed = 42): TaskFixture[] {
  const rand = lcg(seed)
  const distribution: [string, number][] = [
    ['backlog', 400],
    ['done', 150],
    ['research', 30],
    ['todo', 30],
    ['in-progress', 30],
    ['review', 30],
    ['docs', 30],
  ]
  const tasks: TaskFixture[] = []
  let id = 1
  for (const [status, count] of distribution) {
    for (let j = 0; j < count; j++) {
      const r1 = rand()
      const r2 = rand()
      const r3 = rand()
      const blocked = r1 < 0.1
      tasks.push({
        id: id++,
        title: `Task ${id}`,
        status,
        priority: PRIORITIES[Math.floor(r2 * PRIORITIES.length)],
        tags: [],
        blocked,
        block_reason: blocked ? `Blocked reason ${id}` : null,
        claimed: r3 < 0.15,
      })
    }
  }
  return tasks
}

// ─── Board fixture ────────────────────────────────────────────────────────────

const BOARD = {
  statuses: STATUSES.map((name) => ({ name })),
  priorities: [...PRIORITIES],
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

// ─── Fetch stub ───────────────────────────────────────────────────────────────

function stubFetch(tasks: TaskFixture[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/board')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
      }
      if (url.includes('/api/tasks') && !url.includes('/move')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ tasks, mtime: 1713456000 }),
        })
      }
      return Promise.reject(new Error(`Unexpected fetch URL: ${url}`))
    }),
  )
}

let currentTasks: TaskFixture[] = []

// ─── Render helper ────────────────────────────────────────────────────────────

function renderBoard() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard
          board={BOARD}
          tasks={currentTasks}
          loading={false}
          error={null}
          refetchTasks={vi.fn()}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_Board700Structural', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── AC: uniform distribution — 100 tasks per column ──────────────────────

  describe('uniform distribution (SEED=42, 100 tasks/column)', () => {
    beforeEach(() => {
      currentTasks = generateUniformTasks(42)
      stubFetch(currentTasks)
    })

    it('board container has data-testid="kanban-board" for DOM scoping', async () => {
      // The board root div must expose data-testid="kanban-board" so tests can
      // scope DOM node counts to the board and not the full document.
      const { container } = renderBoard()
      await waitFor(() => {
        const board = container.querySelector('[data-testid="kanban-board"]')
        expect(board).not.toBeNull()
      })
    })

    it('renders all 700 task cards', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const board = container.querySelector('[data-testid="kanban-board"]')
        expect(board).not.toBeNull()
        expect(board!.querySelectorAll('[data-testid="task-card"]').length).toBe(700)
      })
    })

    it('total DOM node count within board stays below 5000', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(
          container.querySelector('[data-testid="kanban-board"]'),
        ).not.toBeNull()
      })
      const board = container.querySelector('[data-testid="kanban-board"]')!
      await waitFor(() => {
        expect(board.querySelectorAll('[data-testid="task-card"]').length).toBe(700)
      })
      const nodeCount = board.querySelectorAll('*').length
      expect(nodeCount).toBeLessThan(5000)
    })

    it('each of the 7 columns shows exactly 100 tasks in its header', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const board = container.querySelector('[data-testid="kanban-board"]')
        expect(board).not.toBeNull()
        expect(board!.querySelectorAll('[data-testid="task-card"]').length).toBe(700)
      })
      const board = container.querySelector('[data-testid="kanban-board"]')!
      const columnCounts = Array.from(
        board.querySelectorAll('[data-testid="column-count"]'),
      ).map((el) => Number(el.textContent))
      expect(columnCounts).toHaveLength(7)
      columnCounts.forEach((count) => {
        expect(count).toBe(100)
      })
    })
  })

  // ─── AC: skewed distribution — 400 backlog / 150 done / 30 each remaining ─

  describe('skewed distribution (SEED=42, 400 backlog / 150 done / 30 each remaining)', () => {
    beforeEach(() => {
      currentTasks = generateSkewedTasks(42)
      stubFetch(currentTasks)
    })

    it('board container has data-testid="kanban-board" for DOM scoping', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const board = container.querySelector('[data-testid="kanban-board"]')
        expect(board).not.toBeNull()
      })
    })

    it('renders all 700 task cards', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const board = container.querySelector('[data-testid="kanban-board"]')
        expect(board).not.toBeNull()
        expect(board!.querySelectorAll('[data-testid="task-card"]').length).toBe(700)
      })
    })

    it('total DOM node count within board stays below 5000', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        expect(
          container.querySelector('[data-testid="kanban-board"]'),
        ).not.toBeNull()
      })
      const board = container.querySelector('[data-testid="kanban-board"]')!
      await waitFor(() => {
        expect(board.querySelectorAll('[data-testid="task-card"]').length).toBe(700)
      })
      const nodeCount = board.querySelectorAll('*').length
      expect(nodeCount).toBeLessThan(5000)
    })

    it('backlog column contains 400 task cards', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const board = container.querySelector('[data-testid="kanban-board"]')
        expect(board).not.toBeNull()
        expect(board!.querySelectorAll('[data-testid="task-card"]').length).toBe(700)
      })
      const board = container.querySelector('[data-testid="kanban-board"]')!
      const backlogCards = board
        .querySelector('[data-column="backlog"]')
        ?.querySelectorAll('[data-testid="task-card"]')
      expect(backlogCards?.length).toBe(400)
    })

    it('done column contains 150 task cards', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const board = container.querySelector('[data-testid="kanban-board"]')
        expect(board).not.toBeNull()
        expect(board!.querySelectorAll('[data-testid="task-card"]').length).toBe(700)
      })
      const board = container.querySelector('[data-testid="kanban-board"]')!
      const doneCards = board
        .querySelector('[data-column="done"]')
        ?.querySelectorAll('[data-testid="task-card"]')
      expect(doneCards?.length).toBe(150)
    })

    it('each remaining column (research/todo/in-progress/review/docs) contains 30 task cards', async () => {
      const { container } = renderBoard()
      await waitFor(() => {
        const board = container.querySelector('[data-testid="kanban-board"]')
        expect(board).not.toBeNull()
        expect(board!.querySelectorAll('[data-testid="task-card"]').length).toBe(700)
      })
      const board = container.querySelector('[data-testid="kanban-board"]')!
      const remaining = ['research', 'todo', 'in-progress', 'review', 'docs'] as const
      for (const status of remaining) {
        const cards = board
          .querySelector(`[data-column="${status}"]`)
          ?.querySelectorAll('[data-testid="task-card"]')
        expect(cards?.length, `${status} column task count`).toBe(30)
      }
    })
  })
})

