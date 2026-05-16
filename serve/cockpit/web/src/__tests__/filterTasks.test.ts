/**
 * filterTasks unit tests
 *
 * filterTasks implementation in src/utils/filterTasks.ts (task #1249).
 *
 * Prerequisites (builder must create before tests can reach assertion-failure RED):
 *   src/utils/filterTasks.ts — see stub content in ## Test-Writer Notes
 *
 * AC coverage:
 *   - Text dimension: case-insensitive substring match; '' passes all
 *   - Priority dimension: exact match; '' passes all
 *   - Tags dimension: AND semantics; [] passes all
 *   - Blocked dimension: true = only blocked pass; false = all pass
 *   - AND combination: multiple active dimensions apply simultaneously
 *   - Edge cases: empty tags array, undefined tags field
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

/** All-pass default FilterState — no active filters */
const noFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }

// ─── Text dimension ───────────────────────────────────────────────────────────

describe('TestFromAC_FilterTasks', () => {
  describe('text dimension', () => {
    it('includes task whose title contains the filter substring', () => {
      const task = makeTask({ id: 1, title: 'My Task' })
      const result = filterTasks([task], { ...noFilter, text: 'task' })
      expect(result).toEqual([task])
    })

    it('match is case-insensitive', () => {
      const task = makeTask({ id: 1, title: 'my task' })
      const result = filterTasks([task], { ...noFilter, text: 'MY TASK' })
      expect(result).toEqual([task])
    })

    it('empty text passes all tasks through', () => {
      const tasks = [makeTask({ id: 1 }), makeTask({ id: 2 })]
      const result = filterTasks(tasks, { ...noFilter, text: '' })
      expect(result).toEqual(tasks)
    })

    it('non-matching text excludes task while matching task is retained', () => {
      const taskAlpha = makeTask({ id: 1, title: 'Alpha' })
      const taskBeta = makeTask({ id: 2, title: 'Beta' })
      const result = filterTasks([taskAlpha, taskBeta], { ...noFilter, text: 'alpha' })
      expect(result).toEqual([taskAlpha])
    })

    it('partial substring match includes task', () => {
      const task = makeTask({ id: 1, title: 'Frontend Filtering Feature' })
      const result = filterTasks([task], { ...noFilter, text: 'filter' })
      expect(result).toEqual([task])
    })
  })

  // ─── Priority dimension ───────────────────────────────────────────────────

  describe('priority dimension', () => {
    it('includes task with exact matching priority', () => {
      const task = makeTask({ id: 1, priority: 'critical' })
      const result = filterTasks([task], { ...noFilter, priority: 'critical' })
      expect(result).toEqual([task])
    })

    it('empty priority passes all tasks through', () => {
      const tasks = [
        makeTask({ id: 1, priority: 'critical' }),
        makeTask({ id: 2, priority: 'important' }),
      ]
      const result = filterTasks(tasks, { ...noFilter, priority: '' })
      expect(result).toEqual(tasks)
    })

    it('non-matching priority excludes task while matching task is retained', () => {
      const taskCrit = makeTask({ id: 1, priority: 'critical' })
      const taskImpt = makeTask({ id: 2, priority: 'important' })
      const result = filterTasks([taskCrit, taskImpt], { ...noFilter, priority: 'critical' })
      expect(result).toEqual([taskCrit])
    })

    it('priority match is case-sensitive — uppercase variant does not match lowercase filter', () => {
      // Proves exact string equality: 'CRITICAL' !== 'critical'
      // A case-insensitive implementation would return both tasks; exact match returns only the lowercase one.
      const lower = makeTask({ id: 1, priority: 'critical' })
      const upper = makeTask({ id: 2, priority: 'CRITICAL' })
      const result = filterTasks([lower, upper], { ...noFilter, priority: 'critical' })
      expect(result).toEqual([lower])
    })
  })

  // ─── Tags dimension (AND semantics) ──────────────────────────────────────

  describe('tags dimension — AND semantics', () => {
    it('includes task that has all selected tags', () => {
      const task = makeTask({ id: 1, tags: ['a', 'b', 'c'] })
      const result = filterTasks([task], { ...noFilter, tags: ['a', 'b'] })
      expect(result).toEqual([task])
    })

    it('excludes task missing even one selected tag while retaining fully-matching task', () => {
      const taskABC = makeTask({ id: 1, tags: ['a', 'b', 'c'] })
      const taskAB = makeTask({ id: 2, tags: ['a', 'b'] })
      const result = filterTasks([taskABC, taskAB], { ...noFilter, tags: ['a', 'b', 'c'] })
      expect(result).toEqual([taskABC])
    })

    it('empty tags array passes all tasks through', () => {
      const tasks = [
        makeTask({ id: 1, tags: ['x'] }),
        makeTask({ id: 2, tags: [] }),
      ]
      const result = filterTasks(tasks, { ...noFilter, tags: [] })
      expect(result).toEqual(tasks)
    })

    it('task with empty tags array excluded when tag filter is non-empty', () => {
      const taskWithTag = makeTask({ id: 1, tags: ['a'] })
      const taskNoTags = makeTask({ id: 2, tags: [] })
      const result = filterTasks([taskWithTag, taskNoTags], { ...noFilter, tags: ['a'] })
      expect(result).toEqual([taskWithTag])
    })
  })

  // ─── Blocked dimension ────────────────────────────────────────────────────

  describe('blocked dimension', () => {
    it('blocked=true: only blocked tasks pass', () => {
      const blocked = makeTask({ id: 1, blocked: true })
      const unblocked = makeTask({ id: 2, blocked: false })
      const result = filterTasks([blocked, unblocked], { ...noFilter, blocked: true })
      expect(result).toEqual([blocked])
    })

    it('blocked=false: all tasks pass regardless of blocked state', () => {
      const blocked = makeTask({ id: 1, blocked: true })
      const unblocked = makeTask({ id: 2, blocked: false })
      const result = filterTasks([blocked, unblocked], { ...noFilter, blocked: false })
      expect(result).toEqual([blocked, unblocked])
    })
  })

  // ─── AND combination ──────────────────────────────────────────────────────

  describe('AND combination — multiple dimensions', () => {
    it('all active dimensions apply simultaneously', () => {
      const taskMatch = makeTask({
        id: 1,
        title: 'my critical task',
        priority: 'critical',
        tags: ['scope:web'],
        blocked: true,
      })
      const taskPartial = makeTask({
        id: 2,
        title: 'my task',
        priority: 'important',
        tags: ['scope:web'],
        blocked: false,
      })
      const result = filterTasks([taskMatch, taskPartial], {
        text: 'my',
        priority: 'critical',
        tags: ['scope:web'],
        blocked: true,
      })
      expect(result).toEqual([taskMatch])
    })

    it('all-pass default (no active filters) returns all tasks', () => {
      const tasks = [makeTask({ id: 1 }), makeTask({ id: 2 })]
      const result = filterTasks(tasks, noFilter)
      expect(result).toEqual(tasks)
    })
  })

  // ─── Edge cases ───────────────────────────────────────────────────────────

  describe('edge cases', () => {
    it('task with undefined tags is treated as non-matching when tags filter is non-empty', () => {
      const taskWithTags = makeTask({ id: 1, tags: ['a'] })
      // Simulate runtime shape where tags field is absent
      const taskUndefinedTags = { ...makeTask({ id: 2 }), tags: undefined as unknown as string[] }
      const result = filterTasks([taskWithTags, taskUndefinedTags], { ...noFilter, tags: ['a'] })
      expect(result).toEqual([taskWithTags])
    })

    it('task with empty tags passes empty-filter but fails non-empty filter', () => {
      const taskNoTags = makeTask({ id: 1, tags: [] })
      const taskTagged = makeTask({ id: 2, tags: ['x'] })
      // Non-empty filter: only taskTagged passes
      const filtered = filterTasks([taskNoTags, taskTagged], { ...noFilter, tags: ['x'] })
      expect(filtered).toEqual([taskTagged])
    })
  })
})
