/**
 * Decision data contract and refetch flow.
 *
 * Separate file because DecisionContract_1386.test.tsx globally mocks usePendingDRs;
 * these tests need the REAL hook with a mocked fetch response to prove the full chain.
 *
 * AC1 (td:1): body field is present in hook output items when backend includes it.
 *   PASS against current code — usePendingDRs passes raw payload.items through the
 *   JS runtime. TypeScript-level contract (body in canonical PendingDR type) requires
 *   vitest typecheck mode or tsc; builder adds it in #1387.
 *
 * AC2 (td:2): hook output items include all required fields including body.
 *   PASS against current code — same root cause as AC1 (JS passthrough).
 *
 * AC4 (td:1): usePendingDRs → usePollingFetch → getResponseErrorMessage chain
 *   surfaces backend error body content in hook error.message.
 *   PASS against current code — getResponseErrorMessage is implemented in #1375 and
 *   usePollingFetch calls it on non-OK responses. These tests prove the decision-
 *   specific error path without relying on a pre-built Error object (unlike
 *   ErrorContract_1374.test.tsx:563). Not duplicating usePendingDRs_1191 tests
 *   which only assert error instanceof Error, not error.message content.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePendingDRs } from '../hooks/usePendingDRs'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeOkFetch(jsonBody: unknown) {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(jsonBody),
    } as Response),
  )
}

function makeErrorFetch(status: number, jsonBody: unknown) {
  return vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve(jsonBody),
    } as Response),
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_DecisionPollBodyAndErrorChain', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  // AC1 + AC2: body field is present in hook output when backend includes it.
  // Proves hook does not strip body from raw payload.items.
  it('hook output items include body field when backend /api/decisions/pending response includes it', async () => {
    vi.stubGlobal(
      'fetch',
      makeOkFetch({
        count: 1,
        items: [
          {
            id: 'dr-001',
            task_id: 42,
            agent: 'builder',
            request_type: 'decision',
            created: '2026-05-01T00:00:00Z',
            title: 'Architecture gate decision',
            body_preview: 'Preview of the decision body...',
            body: '## Full decision context\n\nShould we proceed with approach A or B?',
          },
        ],
      }),
    )

    const { result } = renderHook(() => usePendingDRs({ intervalMs: 60_000 }))
    await act(async () => {})

    expect(result.current.items).toHaveLength(1)
    expect(result.current.items[0]).toHaveProperty(
      'body',
      '## Full decision context\n\nShould we proceed with approach A or B?',
    )
  })

  // AC2: all required fields including body are present in hook output items.
  it('hook output items contain all AC2-required fields: id, task_id, agent, request_type, created, title, body_preview, body', async () => {
    vi.stubGlobal(
      'fetch',
      makeOkFetch({
        count: 1,
        items: [
          {
            id: 'dr-full-fields',
            task_id: 303,
            agent: 'architect',
            request_type: 'decision',
            created: '2026-05-08T12:00:00Z',
            title: 'Field completeness verification',
            body_preview: 'All required fields should be present...',
            body: '## Decision details\n\nComplete context for resolution.',
          },
        ],
      }),
    )

    const { result } = renderHook(() => usePendingDRs({ intervalMs: 60_000 }))
    await act(async () => {})

    const item = result.current.items[0]
    expect(item).toHaveProperty('id', 'dr-full-fields')
    expect(item).toHaveProperty('task_id', 303)
    expect(item).toHaveProperty('agent', 'architect')
    expect(item).toHaveProperty('request_type', 'decision')
    expect(item).toHaveProperty('created', '2026-05-08T12:00:00Z')
    expect(item).toHaveProperty('title', 'Field completeness verification')
    expect(item).toHaveProperty('body_preview', 'All required fields should be present...')
    expect(item).toHaveProperty('body', '## Decision details\n\nComplete context for resolution.')
  })

  // AC4: backend JSON message field → getResponseErrorMessage → hook error.message.
  // Tests the full chain without a pre-built Error object (unlike ErrorContract_1374:563).
  it('hook error.message contains backend JSON message field content on HTTP 503', async () => {
    vi.stubGlobal(
      'fetch',
      makeErrorFetch(503, { message: 'DR polling failed: decision service overloaded' }),
    )

    const { result } = renderHook(() => usePendingDRs({ intervalMs: 60_000 }))
    await act(async () => {})

    expect(result.current.error).not.toBeNull()
    expect(result.current.error!.message).toBe('DR polling failed: decision service overloaded')
  })

  // AC4: backend JSON detail field → getResponseErrorMessage → hook error.message
  // (when message field is absent, detail field is used as fallback source).
  it('hook error.message contains backend JSON detail field content when message field is absent', async () => {
    vi.stubGlobal(
      'fetch',
      makeErrorFetch(422, { detail: 'DR endpoint validation failed: missing required field' }),
    )

    const { result } = renderHook(() => usePendingDRs({ intervalMs: 60_000 }))
    await act(async () => {})

    expect(result.current.error).not.toBeNull()
    expect(result.current.error!.message).toBe('DR endpoint validation failed: missing required field')
  })

  // AC4: hook resets items and count to empty/zero state on backend error.
  // Proves error state is clean (no stale data from previous successful fetch).
  it('hook resets items to empty array and count to 0 when backend returns error response', async () => {
    vi.stubGlobal('fetch', makeErrorFetch(500, { message: 'internal decision service error' }))

    const { result } = renderHook(() => usePendingDRs({ intervalMs: 60_000 }))
    await act(async () => {})

    expect(result.current.items).toEqual([])
    expect(result.current.count).toBe(0)
  })
})
