/**
 * Durable route-contract tests for Cockpit routing.
 *
 * Consolidates archived route infrastructure coverage from tasks #1639 and #1644.
 */

import { describe, it, expect } from 'vitest'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { routeConfig } from '../routes'

const testDir = dirname(fileURLToPath(import.meta.url))
const routesSource = resolve(testDir, '../routes.ts')

describe('RoutesConfigContracts', () => {
  it('exports routeConfig as a mutable array of route entries', () => {
    expect(routeConfig).toBeDefined()
    expect(Array.isArray(routeConfig)).toBe(true)
    expect(Object.isFrozen(routeConfig)).toBe(false)
  })

  it('keeps the base and decisions paths present and unique', () => {
    const paths = routeConfig.map((entry) => entry.path)
    expect(paths).toContain('/')
    expect(paths).toContain('/decisions')
    expect(new Set(paths).size).toBe(paths.length)
  })

  it('keeps each route entry shaped with path, label, icon, and component', () => {
    expect(routeConfig.length).toBeGreaterThanOrEqual(2)
    for (const entry of routeConfig) {
      expect(entry).toHaveProperty('path')
      expect(entry).toHaveProperty('label')
      expect(entry).toHaveProperty('icon')
      expect(entry).toHaveProperty('component')
      expect(typeof entry.path).toBe('string')
      expect(entry.path.length).toBeGreaterThan(0)
      expect(typeof entry.label).toBe('string')
      expect(entry.label.length).toBeGreaterThan(0)
      expect(entry.component).toBeDefined()
      expect(entry.component).toBeTruthy()
    }
  })

  it('keeps the home route eager and callable', () => {
    const homeEntry = routeConfig.find((entry) => entry.path === '/')
    expect(homeEntry?.component).toBeDefined()
    expect((homeEntry?.component as { $$typeof?: symbol })?.$$typeof).not.toBe(Symbol.for('react.lazy'))
    expect(typeof homeEntry?.component).toBe('function')
  })
})

describe('RoutesLazyLoadingContracts', () => {
  it('loads the /decisions route via React.lazy', () => {
    const entry = routeConfig.find((route) => route.path === '/decisions')
    expect(entry).toBeDefined()
    expect((entry!.component as { $$typeof?: symbol }).$$typeof).toBe(Symbol.for('react.lazy'))
  })

  it('starts the DecisionsPage import inside the React.lazy callback', () => {
    const source = readFileSync(routesSource, 'utf-8')
    expect(source).toMatch(/lazy\(\s*\(\)\s*=>\s*import\(['"]\.\/pages\/DecisionsPage['"]\)\s*\)/)
    expect(source).not.toMatch(/const\s+\w*decisions\w*\s*=\s*import\(['"]\.\/pages\/DecisionsPage['"]\)/i)
  })

  it('keeps multiple JS chunks in dist/assets after build', () => {
    const distAssets = resolve(testDir, '../../../dist/assets')
    expect(
      existsSync(distAssets),
      "dist/assets/ must exist — run 'npm run build' inside serve/cockpit/web/",
    ).toBe(true)
    const jsFiles = readdirSync(distAssets).filter((file) => file.endsWith('.js'))
    expect(jsFiles.length).toBeGreaterThanOrEqual(2)
  })
})
