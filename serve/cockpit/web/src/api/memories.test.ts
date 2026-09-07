import { describe, expect, it, vi } from 'vitest'
import { editMemory, MemoryMutationError, type MemoryEditPayload } from './memories'

function response(body: unknown, status: number): Response {
  return {
    ok: false,
    status,
    json: async () => body,
  } as Response
}

const payload: MemoryEditPayload = {
  title: 'Updated title',
  categories: ['process'],
  confidence: 0.9,
  scope_agents: ['builder'],
  content: 'Updated content',
  expected_updated_at: '2026-01-01T00:00:00+00:00',
}

describe('memory mutation errors', () => {
  it('preserves structured API error codes separately from messages', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(response({ code: 'MEM_CONFLICT', message: 'Entry changed' }, 409)),
    )

    await expect(editMemory('entry-1', payload)).rejects.toMatchObject({
      apiError: expect.objectContaining({
        status: 409,
        code: 'MEM_CONFLICT',
        message: 'Entry changed',
      }),
    })
  })

  it('keeps generic conflict responses usable without inventing a code', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ message: 'Conflict' }, 409)))

    const failure = await editMemory('entry-1', payload).catch((caught: unknown) => caught)

    expect(failure).toBeInstanceOf(MemoryMutationError)
    expect((failure as MemoryMutationError).apiError).toMatchObject({ status: 409, code: null, message: 'Conflict' })
  })
})
