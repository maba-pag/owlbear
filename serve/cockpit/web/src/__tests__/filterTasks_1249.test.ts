/**
 * Failing tests for #1249: P1-02 — filterTasks pure function + FilterState type
 *
 * AC coverage from this file:
 *   - Pure function — no React imports, no side effects (td:1)
 *
 * All other AC lines (filterTasks export td:2, FilterState td:0, AND semantics td:2)
 * are fully covered by filterTasks_1248.test.ts, which is the primary RED suite
 * and becomes the GREEN evidence for this task's td:2 criteria.
 *
 * The test below is RED against the current stub (which always returns []):
 * the correctness assertion `expect(result1).toContainEqual(tasks[0])` fails.
 */
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

const noFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }

// ─── Purity (AC: Pure function — no React imports, no side effects) ───────────

describe('TestFromAC_FilterTasksPurity', () => {
  /**
   * Smoke test for AC: "Pure function — no React imports, no side effects (td:1)"
   *
   * A pure function must be:
   *   - Side-effect-free: the input array must not be mutated.
   *   - Deterministic: identical arguments must produce value-equal results.
   *
   * The correctness assertion (`toContainEqual`) makes this test RED against
   * the stub which always returns [].  After correct implementation both
   * the mutation guard and determinism assertions also remain satisfied.
   */
  it('does not mutate input and returns deterministic results for matching filter', () => {
    const tasks = [
      makeTask({ id: 1, title: 'Alpha' }),
      makeTask({ id: 2, title: 'Beta' }),
    ]
    const capturedLength = tasks.length
    const filter: FilterState = { ...noFilter, text: 'alpha' }

    const result1 = filterTasks(tasks, filter)
    const result2 = filterTasks(tasks, filter)

    // Side-effect guard: input array must remain unchanged after the call
    expect(tasks).toHaveLength(capturedLength)

    // Determinism: two calls with identical arguments must return equal results
    expect(result1).toEqual(result2)

    // Correctness — makes test RED against stub (stub returns [], not [tasks[0]])
    expect(result1).toContainEqual(tasks[0])
  })
})
