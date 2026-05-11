/**
 * RED phase Vitest tests for #1457: P4-19 Expose maintenance cleanup through Cockpit
 *
 * AC 3a (td:1): API client function POSTs to /api/tasks/cleanup and returns typed
 *               CleanupResult, with error handling following api/repair.ts pattern.
 *
 * RED reason: src/api/cleanup.ts does not exist — collection fails with ImportError.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { cleanupTasks } from '../api/cleanup'
import type { CleanupResult } from '../api/cleanup'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const RESULT_FULL: CleanupResult = {
  released_claim_ids: [10, 20],
  archived_task_ids: [5, 15, 25],
  skipped_items: [
    { path: '/tasks/TASK-099.md', reason: 'File locked' },
  ],
}

const RESULT_EMPTY: CleanupResult = {
  released_claim_ids: [],
  archived_task_ids: [],
  skipped_items: [],
}

function makeSuccessFetch(result: CleanupResult) {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(result),
    }),
  )
}

function makeNonOkFetch(status: number, body: Record<string, unknown> = { detail: 'Server error' }) {
  return vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve(body),
    }),
  )
}

function makeNetworkErrorFetch(message = 'Network failure') {
  return vi.fn(() => Promise.reject(new Error(message)))
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_cleanupStorage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── AC 3a: sends POST to /api/tasks/cleanup ──────────────────────────────

  describe('AC 3a: sends POST to /api/tasks/cleanup', () => {
    it('sends a request to /api/tasks/cleanup', async () => {
      const fetchMock = makeSuccessFetch(RESULT_EMPTY)
      vi.stubGlobal('fetch', fetchMock)
      await cleanupTasks()
      expect(fetchMock).toHaveBeenCalledWith('/api/tasks/cleanup', expect.objectContaining({ method: 'POST' }))
    })

    it('uses POST method', async () => {
      const fetchMock = makeSuccessFetch(RESULT_EMPTY)
      vi.stubGlobal('fetch', fetchMock)
      await cleanupTasks()
      const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
      expect(init.method).toBe('POST')
    })
  })

  // ─── AC 3a: returns typed CleanupResult ──────────────────────────────────

  describe('AC 3a: returns typed CleanupResult with released_claim_ids, archived_task_ids, skipped_items', () => {
    it('returns released_claim_ids as number array', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch(RESULT_FULL))
      const result = await cleanupTasks()
      expect(result.released_claim_ids).toEqual([10, 20])
    })

    it('returns archived_task_ids as number array', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch(RESULT_FULL))
      const result = await cleanupTasks()
      expect(result.archived_task_ids).toEqual([5, 15, 25])
    })

    it('returns skipped_items as array of {path, reason} objects', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch(RESULT_FULL))
      const result = await cleanupTasks()
      expect(result.skipped_items).toHaveLength(1)
      expect(result.skipped_items[0].path).toBe('/tasks/TASK-099.md')
      expect(result.skipped_items[0].reason).toBe('File locked')
    })

    it('returns empty arrays when nothing was cleaned up', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch(RESULT_EMPTY))
      const result = await cleanupTasks()
      expect(result.released_claim_ids).toEqual([])
      expect(result.archived_task_ids).toEqual([])
      expect(result.skipped_items).toEqual([])
    })
  })

  // ─── AC 3a: error handling following api/repair.ts pattern ───────────────

  describe('AC 3a: error handling — throws on non-ok HTTP response', () => {
    it('throws an Error when the response status is not ok', async () => {
      vi.stubGlobal('fetch', makeNonOkFetch(500))
      await expect(cleanupTasks()).rejects.toThrow()
    })

    it('includes the server detail message in the thrown error', async () => {
      vi.stubGlobal('fetch', makeNonOkFetch(500, { detail: 'cleanup failed: locked files' }))
      await expect(cleanupTasks()).rejects.toThrow(/cleanup failed: locked files/)
    })

    it('includes the status code in the error message when no body detail is available', async () => {
      vi.stubGlobal('fetch', makeNonOkFetch(503, {}))
      await expect(cleanupTasks()).rejects.toThrow(/503/)
    })

    it('throws an Error on network failure', async () => {
      vi.stubGlobal('fetch', makeNetworkErrorFetch('Network failure'))
      await expect(cleanupTasks()).rejects.toThrow('Network failure')
    })
  })
})
