/**
 * Durable route-contract tests for Cockpit routing.
 *
 * Consolidates archived route infrastructure coverage from tasks #1639 and #1644.
 */

import { describe, it, expect } from 'vitest'
import { routeConfig } from '../routes'

describe('RoutesConfigContracts', () => {
  it('exposes exactly target work and preserved utility routes', () => {
    const paths = routeConfig.map((entry) => entry.path)
    expect(paths).toEqual(['/work', '/memories', '/ideas'])
    expect(new Set(paths).size).toBe(paths.length)
  })

  it('loads the Work route lazily', () => {
    const workEntry = routeConfig.find((entry) => entry.path === '/work')
    expect(workEntry?.component).toBeDefined()
    expect((workEntry?.component as { $$typeof?: symbol })?.$$typeof).toBe(Symbol.for('react.lazy'))
  })
})
