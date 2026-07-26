import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  CANDIDATE_REVISION,
  NativeApiError,
  cancelNativeJob,
  getLegacyInventory,
  getNativeChangeHealth,
  getNativeGraph,
  getNativeInvalidation,
  getNativeJob,
  getNativeWorkHealth,
  listNativeJobs,
  listNativeRequests,
  setNativeJobPriority,
} from '../api/native'

function response(status: number, payload: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(payload),
  } as unknown as Response
}

describe('native API boundary', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('always supplies the explicit HEAD candidate revision and cursor', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(200, { items: [], next_cursor: null }))
    vi.stubGlobal('fetch', fetchMock)

    await listNativeJobs('replace delivery', 'cursor/2', 25)

    const url = new URL(String(fetchMock.mock.calls[0][0]), 'http://cockpit.test')
    expect(url.pathname).toBe('/api/changes/replace%20delivery/jobs')
    expect(url.searchParams.get('candidate_revision')).toBe(CANDIDATE_REVISION)
    expect(url.searchParams.get('candidate_revision')).toBe('HEAD')
    expect(url.searchParams.get('cursor')).toBe('cursor/2')
    expect(url.searchParams.get('limit')).toBe('25')
  })

  it.each([404, 409, 422, 503])('retains nested FastAPI authority on %i', async (status) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        response(status, {
          detail: {
            code: 'ERR_JOB_ADMIN_OCC_STALE',
            detail: 'job OCC token is stale',
            current_delivery_digest: 'a'.repeat(64),
            target: '20',
            lower_code: 'ERR_JOB_OCC_STALE',
            current: { job: { job_id: 20 }, token: 'token-2' },
          },
        }),
      ),
    )

    const error = await listNativeJobs('change').catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(NativeApiError)
    expect(error).toMatchObject({
      status,
      code: 'ERR_JOB_ADMIN_OCC_STALE',
      detail: 'job OCC token is stale',
      currentDeliveryDigest: 'a'.repeat(64),
      target: '20',
      token: 'token-2',
      lowerCode: 'ERR_JOB_OCC_STALE',
      current: { job: { job_id: 20 }, token: 'token-2' },
    })
  })

  it('retains FastAPI validation entries on 422', async () => {
    const validation = [{ loc: ['body', 'expected_token'], msg: 'Field required' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(422, { detail: validation })))

    const error = await listNativeJobs('change').catch((caught: unknown) => caught)

    expect(error).toMatchObject({
      status: 422,
      code: 'ERR_NATIVE_REQUEST',
      detail: 'Request validation failed',
      validation,
    })
  })

  it('parses real flat job rows and nested request records', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        response(200, {
          items: [
            {
              job_id: 20,
              token: 'job-token',
              kind: 'build',
              priority: 9,
              change_id: 'change',
              delivery_digest: 'a'.repeat(64),
              target_node_id: 'DN-001',
              title: 'Build',
              outcome: 'Done',
              acceptance: [],
              modules: [],
              interfaces: [],
              proof: 'PROOF-001',
              dependency_ready: true,
              claim_id: null,
              requests: [],
              block_id: null,
              attempt: null,
              finding: null,
              receipt: null,
              validity: null,
              disposition: 'pending',
            },
          ],
          next_cursor: null,
        }),
      )
      .mockResolvedValueOnce(
        response(200, {
          items: [{ request: { request_id: 'request-1' }, resolution: null }],
          next_cursor: null,
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    const jobs = await listNativeJobs('change')
    const requests = await listNativeRequests('change')

    expect(jobs.items[0]).toMatchObject({ job_id: 20, token: 'job-token' })
    expect(requests.items[0].request.request_id).toBe('request-1')
  })

  it('sends exact priority and cancel identities without generic mutable fields', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(200, { job: {} }))
    vi.stubGlobal('fetch', fetchMock)
    const priority = {
      job_id: 20,
      delivery_digest: 'b'.repeat(64),
      expected_token: 'token-1',
      priority: 9,
      updated_at: '2026-07-26T10:00:00Z',
    }
    const cancellation = {
      job_id: 21,
      delivery_digest: 'b'.repeat(64),
      expected_token: 'token-2',
      cancelled_at: '2026-07-26T10:01:00Z',
    }

    await setNativeJobPriority('change', priority)
    await cancelNativeJob('change', cancellation)

    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual(priority)
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual(cancellation)
    expect(fetchMock.mock.calls[0][0]).toContain('/jobs/20/priority')
    expect(fetchMock.mock.calls[1][0]).toContain('/jobs/21/cancel')
  })

  it('uses only real route-specific non-page endpoints', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(response(200, { job: { job_id: 20 }, token: 'detail-token' }))
    vi.stubGlobal('fetch', fetchMock)

    const detail = await getNativeJob('change', 20)
    await getNativeGraph('change')
    await getNativeInvalidation('change', 'supersession/1')
    await getNativeWorkHealth('change')
    await getNativeChangeHealth('change')
    await getLegacyInventory()

    expect(detail).toMatchObject({ job: { job_id: 20 }, token: 'detail-token' })
    expect(fetchMock.mock.calls.map((call) => String(call[0]))).toEqual([
      '/api/changes/change/jobs/20',
      '/api/changes/change/graph',
      '/api/changes/change/invalidations/supersession%2F1',
      '/api/changes/change/health/work?limit=100',
      '/api/changes/change/health/change?limit=100',
      '/api/legacy',
    ])
  })
})
