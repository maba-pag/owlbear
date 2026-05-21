/**
 * cardVariants.ts unit tests — task #1615 (AC-1, AC-2)
 *
 * Tests that statusToVariant() and priorityToVariant() utilities:
 * - Return a valid PDS PTag variant string for all known status/priority values
 * - Return 'secondary' as the fallback for unknown or empty inputs
 *
 * All tests fail with ModuleNotFoundError until builder creates utils/cardVariants.ts.
 *
 * Known status values (from Builder Guidance): research, backlog, todo, in-progress,
 *   review, docs, done
 * Known priority values (from Builder Guidance): someday, nice-to-have, important,
 *   needed, critical
 * Valid PDS TagVariant values: primary, secondary, info, info-frosted, warning,
 *   warning-frosted, success, success-frosted, error, error-frosted
 * Note: 'notification' is NOT a valid PDS TagVariant and must NOT appear in mappings.
 */
import { describe, it, expect } from 'vitest'
import { statusToVariant, priorityToVariant } from '../utils/cardVariants'

const KNOWN_STATUSES = [
  'research',
  'backlog',
  'todo',
  'in-progress',
  'review',
  'docs',
  'done',
] as const

const KNOWN_PRIORITIES = [
  'someday',
  'nice-to-have',
  'important',
  'needed',
  'critical',
] as const

const VALID_PDS_VARIANTS = [
  'primary',
  'secondary',
  'info',
  'info-frosted',
  'warning',
  'warning-frosted',
  'success',
  'success-frosted',
  'error',
  'error-frosted',
] as const

// ─── AC-1: statusToVariant ───────────────────────────────────────────────────

describe('card variant mappings', () => {
  describe('statusToVariant — AC-1', () => {
    it('returns a valid PDS variant string for each known status value', () => {
      for (const status of KNOWN_STATUSES) {
        const variant = statusToVariant(status)
        expect(VALID_PDS_VARIANTS as readonly string[]).toContain(variant)
      }
    })

    it('returns "secondary" for an unknown status string', () => {
      expect(statusToVariant('completely-unknown-status-xyz')).toBe('secondary')
    })

    it('returns "secondary" for an empty string status', () => {
      expect(statusToVariant('')).toBe('secondary')
    })

    it('statusToVariant("todo") returns a non-empty string', () => {
      const variant = statusToVariant('todo')
      expect(typeof variant).toBe('string')
      expect(variant.length).toBeGreaterThan(0)
    })

    it('statusToVariant("in-progress") returns a non-empty string', () => {
      const variant = statusToVariant('in-progress')
      expect(typeof variant).toBe('string')
      expect(variant.length).toBeGreaterThan(0)
    })

    it('statusToVariant("done") returns a non-empty string', () => {
      const variant = statusToVariant('done')
      expect(typeof variant).toBe('string')
      expect(variant.length).toBeGreaterThan(0)
    })

    it('all 7 known status values return a valid PDS variant (not undefined or null)', () => {
      for (const status of KNOWN_STATUSES) {
        const variant = statusToVariant(status)
        expect(variant).toBeDefined()
        expect(variant).not.toBeNull()
      }
    })

    it('statusToVariant("backlog") returns "info" — not the invalid "notification"', () => {
      expect(statusToVariant('backlog')).toBe('info')
    })

    it('statusToVariant("review") returns "info" — not the invalid "notification"', () => {
      expect(statusToVariant('review')).toBe('info')
    })
  })

  // ─── AC-2: priorityToVariant ─────────────────────────────────────────────

  describe('priorityToVariant — AC-2', () => {
    it('returns a valid PDS variant string for each known priority value', () => {
      for (const priority of KNOWN_PRIORITIES) {
        const variant = priorityToVariant(priority)
        expect(VALID_PDS_VARIANTS as readonly string[]).toContain(variant)
      }
    })

    it('returns "secondary" for an unknown priority string', () => {
      expect(priorityToVariant('completely-unknown-priority-xyz')).toBe('secondary')
    })

    it('returns "secondary" for an empty string priority', () => {
      expect(priorityToVariant('')).toBe('secondary')
    })

    it('priorityToVariant("critical") returns a non-empty string', () => {
      const variant = priorityToVariant('critical')
      expect(typeof variant).toBe('string')
      expect(variant.length).toBeGreaterThan(0)
    })

    it('priorityToVariant("someday") returns a non-empty string', () => {
      const variant = priorityToVariant('someday')
      expect(typeof variant).toBe('string')
      expect(variant.length).toBeGreaterThan(0)
    })

    it('priorityToVariant("important") returns a non-empty string', () => {
      const variant = priorityToVariant('important')
      expect(typeof variant).toBe('string')
      expect(variant.length).toBeGreaterThan(0)
    })

    it('all 5 known priority values return a valid PDS variant (not undefined or null)', () => {
      for (const priority of KNOWN_PRIORITIES) {
        const variant = priorityToVariant(priority)
        expect(variant).toBeDefined()
        expect(variant).not.toBeNull()
      }
    })

    it('priorityToVariant("needed") returns "info" — not the invalid "notification"', () => {
      expect(priorityToVariant('needed')).toBe('info')
    })
  })
})
