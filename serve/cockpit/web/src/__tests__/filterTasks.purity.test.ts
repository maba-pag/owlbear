/**
 * filterTasks pure function + FilterState type
 *
 * AC coverage from this file:
 *   - Pure function — no React imports, no side effects (td:1)
 *
 * All other AC lines (filterTasks export td:2, FilterState td:0, AND semantics td:2)
 * are fully covered by filterTasks_1248.test.ts, which is the primary RED suite
 * and becomes the GREEN evidence for this task's td:2 criteria.
 *
 * Strengthened per reviewer feedback (#1249 reject):
 *   1. Module source is read from disk and asserted to contain no React import
 *      (fails if any `from 'react'` / `import 'react'` / `require('react')` is added)
 *   2. Task objects are deep-snapshotted before calling filterTasks and compared
 *      afterwards — catches in-place mutation of properties or nested arrays even
 *      when the filtered output length stays stable
 */
import { readFileSync } from 'fs'
import { resolve } from 'path'
import { describe, it, expect } from 'vitest'
import { filterTasks, type FilterState } from '../utils/filterTasks'
import type { Task } from '../hooks/useBoard'

// ─── Fixture factory ─────────────────────────────────────────────────────────

function makeTask(overrides: Partial<Task> & { id: number }): Task {
  return {
    title: 'default title',
    status: 'todo',
    priority: 'important',
    updated: '2026-01-01T00:00:00Z',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
    ...overrides,
  }
}

/** Deep snapshot of a Task (primitives + shallow-copied tags array). */
function snapshotTask(task: Task): Task {
  return { ...task, tags: [...(task.tags ?? [])] }
}

const noFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }

// ─── Purity (AC: Pure function — no React imports, no side effects) ───────────

describe('TestFromAC_FilterTasksPurity', () => {
  /**
   * Structural proof: module source must contain no React import.
   * Reads the file from disk at test time so the assertion fails the moment
   * any `from 'react'` (or require/bare-import variant) is introduced.
   */
  it('module source contains no React import', () => {
    const sourceCode = readFileSync(
      resolve(__dirname, '../utils/filterTasks.ts'),
      'utf-8',
    )
    expect(sourceCode).not.toMatch(/from ['"]react['"]/)
    expect(sourceCode).not.toMatch(/import\s+['"]react['"]/)
    expect(sourceCode).not.toMatch(/require\s*\(\s*['"]react['"]\s*\)/)
  })

  /**
   * Mutation guard: task objects must not be mutated in place.
   * Uses a deep snapshot (including the mutable `tags` array) so a future
   * implementation that sorts, adds, or removes tags — while still returning
   * the correct filtered array — still fails this test.
   */
  it('does not mutate input task objects in place', () => {
    const tasks = [
      makeTask({ id: 1, title: 'Alpha', tags: ['x', 'y'], blocked: false }),
      makeTask({ id: 2, title: 'Beta', tags: ['z'], blocked: true }),
    ]
    const snapshots = tasks.map(snapshotTask)

    filterTasks(tasks, { ...noFilter, text: 'alpha' })

    tasks.forEach((task, i) => {
      expect(task).toEqual(snapshots[i])
    })
  })

  /**
   * Array-level mutation guard: the input array reference must not be shortened,
   * extended, or reordered after the call.
   */
  it('does not mutate the input array itself', () => {
    const tasks = [
      makeTask({ id: 1, title: 'Alpha' }),
      makeTask({ id: 2, title: 'Beta' }),
    ]
    const capturedLength = tasks.length

    filterTasks(tasks, { ...noFilter, text: 'alpha' })

    expect(tasks).toHaveLength(capturedLength)
    expect(tasks[0].id).toBe(1)
    expect(tasks[1].id).toBe(2)
  })

  /**
   * Determinism: identical arguments must produce value-equal results across
   * repeated calls.
   */
  it('returns deterministic results for identical arguments', () => {
    const tasks = [
      makeTask({ id: 1, title: 'Alpha' }),
      makeTask({ id: 2, title: 'Beta' }),
    ]
    const filter: FilterState = { ...noFilter, text: 'alpha' }

    const result1 = filterTasks(tasks, filter)
    const result2 = filterTasks(tasks, filter)

    expect(result1).toEqual(result2)
    expect(result1).toContainEqual(tasks[0])
  })
})

