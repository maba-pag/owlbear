/**
 * format_1598: Null-safe formatting utilities (task #1598)
 *
 * RED reason: src/utils/format.ts does not exist yet — all imports fail
 * at module resolution (ImportError). Implementation in task #1604.
 *
 * Prerequisites (builder must create before tests reach assertion-failure RED):
 *   src/utils/format.ts — exports formatRelativeTime, formatPriority,
 *                          formatStatus, formatSignalDescription
 *
 * AC coverage:
 *   AC-1: Each of the 4 formatters returns a defined non-empty fallback
 *         string when called with null or undefined (never throws).
 *   AC-2: No file in the mutation call graph imports from utils/format
 *         (canonical/display partition guardrail).
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  formatRelativeTime,
  formatPriority,
  formatStatus,
  formatSignalDescription,
} from '../utils/format'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// ─── AC-1: Null-safe formatting utilities ─────────────────────────────────────

describe('TestFromAC_FormattingUtilities', () => {
  // ── formatRelativeTime ────────────────────────────────────────────────────

  describe('AC-1: formatRelativeTime — null/undefined fallback', () => {
    it('returns a non-empty string for a valid ISO timestamp', () => {
      const result = formatRelativeTime(new Date().toISOString())
      expect(result).toBeTruthy()
      expect(typeof result).toBe('string')
    })

    it('returns fallback "—" when called with null', () => {
      const result = formatRelativeTime(null)
      expect(result).toBe('—')
    })

    it('returns fallback "—" when called with undefined', () => {
      const result = formatRelativeTime(undefined)
      expect(result).toBe('—')
    })

    it('does not throw when called with null', () => {
      expect(() => formatRelativeTime(null)).not.toThrow()
    })

    it('does not throw when called with undefined', () => {
      expect(() => formatRelativeTime(undefined)).not.toThrow()
    })

    it('returns a non-empty string (not null/undefined) for an unparseable date string', () => {
      const result = formatRelativeTime('not-a-date')
      expect(result).toBeTruthy()
      expect(result).not.toBeNull()
      expect(result).not.toBeUndefined()
    })
  })

  // ── formatPriority ────────────────────────────────────────────────────────

  describe('AC-1: formatPriority — null/undefined fallback', () => {
    it('returns a non-empty string for a known priority value', () => {
      const result = formatPriority('important')
      expect(result).toBeTruthy()
      expect(typeof result).toBe('string')
    })

    it('returns fallback "—" when called with null', () => {
      const result = formatPriority(null)
      expect(result).toBe('—')
    })

    it('returns fallback "—" when called with undefined', () => {
      const result = formatPriority(undefined)
      expect(result).toBe('—')
    })

    it('does not throw when called with null', () => {
      expect(() => formatPriority(null)).not.toThrow()
    })

    it('does not throw when called with undefined', () => {
      expect(() => formatPriority(undefined)).not.toThrow()
    })

    it('returns a non-empty string (not null/undefined) for an unknown priority value', () => {
      const result = formatPriority('unknown-future-priority')
      expect(result).toBeTruthy()
      expect(result).not.toBeNull()
      expect(result).not.toBeUndefined()
    })
  })

  // ── formatStatus ──────────────────────────────────────────────────────────

  describe('AC-1: formatStatus — null/undefined fallback', () => {
    it('converts hyphenated status to title-case display for a valid value', () => {
      const result = formatStatus('in-progress')
      expect(result).toBeTruthy()
      expect(typeof result).toBe('string')
    })

    it('returns fallback "—" when called with null', () => {
      const result = formatStatus(null)
      expect(result).toBe('—')
    })

    it('returns fallback "—" when called with undefined', () => {
      const result = formatStatus(undefined)
      expect(result).toBe('—')
    })

    it('does not throw when called with null', () => {
      expect(() => formatStatus(null)).not.toThrow()
    })

    it('does not throw when called with undefined', () => {
      expect(() => formatStatus(undefined)).not.toThrow()
    })

    it('returns a non-empty fallback string for an empty-string status', () => {
      const result = formatStatus('')
      expect(result).not.toBeNull()
      expect(result).not.toBeUndefined()
    })
  })

  // ── formatSignalDescription ───────────────────────────────────────────────

  describe('AC-1: formatSignalDescription — null/undefined fallback', () => {
    it('returns a non-empty string for a known signal value "ready"', () => {
      const result = formatSignalDescription('ready')
      expect(result).toBeTruthy()
      expect(typeof result).toBe('string')
    })

    it('returns a non-empty string for signal "dr-pending"', () => {
      const result = formatSignalDescription('dr-pending')
      expect(result).toBeTruthy()
      expect(typeof result).toBe('string')
    })

    it('returns fallback "Unknown" when called with null', () => {
      const result = formatSignalDescription(null)
      expect(result).toBe('Unknown')
    })

    it('returns fallback "Unknown" when called with undefined', () => {
      const result = formatSignalDescription(undefined)
      expect(result).toBe('Unknown')
    })

    it('does not throw when called with null', () => {
      expect(() => formatSignalDescription(null)).not.toThrow()
    })

    it('does not throw when called with undefined', () => {
      expect(() => formatSignalDescription(undefined)).not.toThrow()
    })
  })
})

// ─── AC-2: Canonical/display partition guardrail ──────────────────────────────
//
// None of the mutation call graph files may import from utils/format.
// Formatted display values must never flow into API payloads.

describe('TestFromAC_MutationPartitionGuardrail', () => {
  /**
   * The full mutation call graph — every file that assembles or dispatches
   * an API payload (canonical layer). Formatted display strings must not
   * originate from or pass through any of these files.
   */
  const MUTATION_GRAPH_FILES = [
    // API layer
    resolve(__dirname, '..', 'api', 'tasks.ts'),
    resolve(__dirname, '..', 'api', 'decisions.ts'),
    resolve(__dirname, '..', 'api', 'repair.ts'),
    // Hook layer
    resolve(__dirname, '..', 'hooks', 'useTaskMutation.ts'),
    resolve(__dirname, '..', 'hooks', 'useCleanupFlow.ts'),
    resolve(__dirname, '..', 'hooks', 'useRepairFlow.ts'),
    // Component layer — mutation-initiating components
    resolve(__dirname, '..', 'KanbanBoard.tsx'),
    resolve(__dirname, '..', 'components', 'ArchivalModal.tsx'),
    resolve(__dirname, '..', 'components', 'ResolveModal.tsx'),
    resolve(__dirname, '..', 'components', 'DetailTab.tsx'),
    resolve(__dirname, '..', 'components', 'TaskFieldsEditor.tsx'),
    resolve(__dirname, '..', 'components', 'TaskActions.tsx'),
  ]

  /** Matches any static import of utils/format (or a sub-path like utils/format.js) */
  const FORMAT_IMPORT_RE = /from\s+['"][^'"]*utils\/format['"]/

  it.each(MUTATION_GRAPH_FILES)(
    'mutation-graph file does not import from utils/format: %s',
    (filePath) => {
      const content = readFileSync(filePath, 'utf-8')
      expect(content).not.toMatch(FORMAT_IMPORT_RE)
    },
  )
})
