/**
 * computeSignal unit tests
 *
 * computeSignal implementation target: src/utils/computeSignal.ts (task #1544).
 *
 * Prerequisites (builder must create before tests reach assertion-failure RED):
 *   src/utils/computeSignal.ts — export `computeSignal` function and `CardSignal` type
 *
 * AC coverage:
 *   AC-1: "dr-pending" when task.id is in pendingDRIds Set, regardless of other flags
 *   AC-2: full precedence chain — dr-pending > blocked > claimed > deps-unmet > ready
 *   AC-3: dep_status mapping — "blocked" → deps-unmet; "ok"/"redirect"/null → no deps-unmet
 */
import { describe, it, expect } from 'vitest'
import { computeSignal } from '../utils/computeSignal'

// ─── Fixture factory ─────────────────────────────────────────────────────────

/** Minimal task shape required by computeSignal — self-contained, not coupled to Task */
interface SignalInput {
  id: number
  blocked: boolean
  claimed: boolean
  dep_status: string | null
}

function makeTask(overrides: Partial<SignalInput> & { id: number }): SignalInput {
  return {
    blocked: false,
    claimed: false,
    dep_status: null,
    ...overrides,
  }
}

const noDRs = new Set<number>()

// ─── AC-1: dr-pending when task ID is in pendingDRIds ────────────────────────

describe('TestFromAC_ComputeSignal', () => {
  describe('AC-1: dr-pending when task.id is in pendingDRIds Set', () => {
    it('returns "dr-pending" when task.id is present in the pendingDRIds Set', () => {
      const task = makeTask({ id: 42 })
      const result = computeSignal(task, new Set([42]))
      expect(result).toBe('dr-pending')
    })

    it('does not return "dr-pending" when task.id is absent from the pendingDRIds Set', () => {
      const task = makeTask({ id: 42 })
      const result = computeSignal(task, new Set([99]))
      expect(result).not.toBe('dr-pending')
    })

    it('returns "dr-pending" regardless of blocked=true', () => {
      const task = makeTask({ id: 1, blocked: true })
      const result = computeSignal(task, new Set([1]))
      expect(result).toBe('dr-pending')
    })

    it('returns "dr-pending" regardless of claimed=true', () => {
      const task = makeTask({ id: 1, claimed: true })
      const result = computeSignal(task, new Set([1]))
      expect(result).toBe('dr-pending')
    })

    it('returns "dr-pending" regardless of dep_status="blocked"', () => {
      const task = makeTask({ id: 1, dep_status: 'blocked' })
      const result = computeSignal(task, new Set([1]))
      expect(result).toBe('dr-pending')
    })

    it('returns "dr-pending" when all other signals are simultaneously active', () => {
      const task = makeTask({ id: 5, blocked: true, claimed: true, dep_status: 'blocked' })
      const result = computeSignal(task, new Set([5]))
      expect(result).toBe('dr-pending')
    })
  })

  // ─── AC-2: Precedence chain ───────────────────────────────────────────────

  describe('AC-2: precedence chain — dr-pending > blocked > claimed > deps-unmet > ready', () => {
    it('dr-pending beats blocked: "dr-pending" wins when both are active', () => {
      const task = makeTask({ id: 1, blocked: true })
      const result = computeSignal(task, new Set([1]))
      expect(result).toBe('dr-pending')
    })

    it('blocked alone: "blocked" when blocked=true with no pending DR and no other active signal', () => {
      const task = makeTask({ id: 1, blocked: true })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('blocked')
    })

    it('blocked beats claimed: "blocked" wins when blocked=true and claimed=true (no DR)', () => {
      const task = makeTask({ id: 1, blocked: true, claimed: true })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('blocked')
    })

    it('claimed beats deps-unmet: "claimed" wins when claimed=true and dep_status="blocked" (not blocked, no DR)', () => {
      const task = makeTask({ id: 1, claimed: true, dep_status: 'blocked' })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('claimed')
    })

    it('deps-unmet beats ready: "deps-unmet" when dep_status="blocked" with no higher-priority signals', () => {
      const task = makeTask({ id: 1, dep_status: 'blocked' })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('deps-unmet')
    })

    it('"ready" is returned when no signals are active (baseline state)', () => {
      const task = makeTask({ id: 1 })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('ready')
    })
  })

  // ─── AC-3: dep_status value mapping ──────────────────────────────────────

  describe('AC-3: dep_status value mapping to signal', () => {
    it('dep_status "blocked" maps to "deps-unmet" (isolated, no other active signals)', () => {
      const task = makeTask({ id: 1, dep_status: 'blocked' })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('deps-unmet')
    })

    it('dep_status "ok" does not produce "deps-unmet" — falls through to "ready"', () => {
      const task = makeTask({ id: 1, dep_status: 'ok' })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('ready')
    })

    it('dep_status "redirect" does not produce "deps-unmet" — falls through to "ready"', () => {
      const task = makeTask({ id: 1, dep_status: 'redirect' })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('ready')
    })

    it('dep_status null does not produce "deps-unmet" — falls through to "ready"', () => {
      const task = makeTask({ id: 1, dep_status: null })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('ready')
    })

    it('dep_status "ok" does not interfere with higher-precedence "claimed" signal', () => {
      const task = makeTask({ id: 1, claimed: true, dep_status: 'ok' })
      const result = computeSignal(task, noDRs)
      expect(result).toBe('claimed')
    })
  })
})
