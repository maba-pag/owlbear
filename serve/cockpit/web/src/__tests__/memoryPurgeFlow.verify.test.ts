import { expect, it } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useMemoryPurgeFlow } from '../hooks/useCleanupFlow'

it('initializes the purge threshold to the shaped 30-day default', () => {
  const { result } = renderHook(() => useMemoryPurgeFlow())

  expect(result.current.threshold).toBe('30')
})
