import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useWorkspaceHealth, type WorkspaceHealthResponse } from '../hooks/useWorkspaceHealth'

const response = (modules: WorkspaceHealthResponse['modules']): Response =>
  new Response(JSON.stringify({ status: 'healthy', modules }), { status: 200 })

describe('useWorkspaceHealth', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('starts gray, aggregates module status, and keeps connection errors separate', async () => {
    let resolveHealth!: (value: Response) => void
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise((resolve) => {
      resolveHealth = resolve
    }))

    const { result } = renderHook(() => useWorkspaceHealth(60_000))
    expect(result.current.health.status).toBe('checking')
    expect(result.current.health.modules.tasks?.status).toBe('unknown')

    await act(async () => resolveHealth(response({
      tasks: { status: 'healthy', checked_at: '2026-07-20T00:00:00Z' },
      requests: { status: 'attention', checked_at: '2026-07-20T00:00:00Z' },
      memory: { status: 'unhealthy', checked_at: '2026-07-20T00:00:00Z' },
      ideas: { status: 'healthy', checked_at: '2026-07-20T00:00:00Z' },
    })))
    expect(result.current.health.status).toBe('unhealthy')

    vi.mocked(fetch).mockRejectedValueOnce(new Error('offline'))
    act(() => result.current.refresh())
    await act(async () => await Promise.resolve())
    expect(result.current.connectionError).toBe('offline')
    expect(result.current.health.status).toBe('check-failed')
    expect(result.current.health.modules.memory?.status).toBe('unhealthy')
  })

  it('rejects stale responses and retains a repair receipt across polling', async () => {
    vi.useFakeTimers()
    const pending: Array<(value: Response) => void> = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise((resolve) => {
      pending.push(resolve)
    }))

    const { result } = renderHook(() => useWorkspaceHealth(60_000))
    await act(async () => pending.shift()?.(response({
      tasks: { status: 'healthy', checked_at: '2026-07-20T02:00:00Z' },
    })))

    act(() => result.current.refresh())
    act(() => result.current.refresh())
    await act(async () => pending.pop()?.(response({
      tasks: { status: 'attention', checked_at: '2026-07-20T03:00:00Z' },
    })))
    await act(async () => pending.shift()?.(response({
      tasks: { status: 'unhealthy', checked_at: '2026-07-20T01:00:00Z' },
    })))
    expect(result.current.health.modules.tasks?.status).toBe('attention')

    act(() => result.current.mergeRepair({
      outcomes: [],
      task_health_result: { status: 'healthy', checked_at: '2026-07-20T04:00:00Z' },
    }))
    expect(result.current.receipt?.task_health_result?.checked_at).toBe('2026-07-20T04:00:00Z')
    expect(result.current.health.modules.tasks?.checked_at).toBe('2026-07-20T04:00:00Z')

    act(() => result.current.refresh())
    await act(async () => pending.shift()?.(response({
      tasks: { status: 'unhealthy', checked_at: '2026-07-20T03:30:00Z' },
    })))
    expect(result.current.receipt?.task_health_result?.checked_at).toBe('2026-07-20T04:00:00Z')
    expect(result.current.health.modules.tasks?.status).toBe('healthy')
  })

  it('merges repair health without an immediate fetch and exposes mutation refresh', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({
      tasks: { status: 'healthy', checked_at: '2026-07-20T00:00:00Z' },
    }))
    const { result } = renderHook(() => useWorkspaceHealth(60_000))
    await act(async () => await Promise.resolve())
    fetchMock.mockClear()

    act(() => result.current.mergeRepair({
      outcomes: [],
      task_health_result: { status: 'healthy', checked_at: '2026-07-20T04:00:00Z' },
    }))
    expect(fetchMock).not.toHaveBeenCalled()

    act(() => result.current.refreshAfterMutation())
    expect(fetchMock).toHaveBeenCalledWith('/health')
  })
})
