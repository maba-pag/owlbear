/**
 * Durable route-contract tests for Cockpit routing.
 *
 * Consolidates archived route infrastructure coverage from tasks #1639 and #1644.
 */

import { describe, it, expect } from 'vitest'
import { legacyRouteRedirects, routeConfig, routeForPath } from '../routes'

describe('RoutesConfigContracts', () => {
  it('exposes exactly target work and preserved utility routes', () => {
    const paths = routeConfig.map((entry) => entry.path)
    expect(paths).toEqual(['/delivery', '/memory', '/ideas'])
    expect(new Set(paths).size).toBe(paths.length)
  })

  it('redirects superseded paths to the aligned route', () => {
    expect(legacyRouteRedirects).toEqual([
      { from: '/', to: '/delivery' },
      { from: '/work', to: '/delivery' },
      { from: '/memories', to: '/memory' },
    ])
    const paths = routeConfig.map((entry) => entry.path)
    for (const redirect of legacyRouteRedirects) {
      expect(paths).toContain(redirect.to)
      expect(paths).not.toContain(redirect.from)
    }
  })

  it('loads the Delivery route lazily', () => {
    const workEntry = routeConfig.find((entry) => entry.path === '/delivery')
    expect(workEntry?.component).toBeDefined()
    expect((workEntry?.component as { $$typeof?: symbol })?.$$typeof).toBe(Symbol.for('react.lazy'))
  })

  it('matches only valid route families and rejects malformed deep links', () => {
    expect(routeForPath('/delivery')?.path).toBe('/delivery')
    expect(routeForPath('/delivery/change-alpha/outcome%3AOUT-001')?.path).toBe('/delivery')
    expect(routeForPath('/delivery/change-alpha')).toBeUndefined()
    expect(routeForPath('/delivery/change-alpha/outcome%3AOUT-001/extra')).toBeUndefined()
    expect(routeForPath('/unknown')).toBeUndefined()
  })
})
