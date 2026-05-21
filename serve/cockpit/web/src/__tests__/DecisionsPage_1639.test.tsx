/**
 * Task #1639 — P1-01: Tab routing infrastructure
 * AC2 coverage: DecisionsPage requires CockpitProvider wiring.
 */
import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import DecisionsPage from '../pages/DecisionsPage'

describe('TestFromAC_DecisionsPageSkeleton', () => {
  it('ac2 edge: DecisionsPage fails loudly when mounted outside CockpitProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    try {
      expect(() => render(<DecisionsPage />)).toThrow('Cockpit hooks must be used within CockpitProvider')
    } finally {
      consoleError.mockRestore()
    }
  })
})
