/**
 * Task #1644 — P1-04: Lazy loading — React.lazy() with Suspense boundary
 * AC1 coverage (routes.ts): DecisionsPage is loaded via React.lazy, not an eager import
 * AC2 coverage: npm run build produces ≥2 JS asset chunks in dist/assets/
 *
 * RED phase:
 *   - routes.ts uses a plain eager import for DecisionsPage (typeof function) →
 *     React.lazy $$typeof check fails.
 *   - dist/assets/ does not exist (gitignored in dev) or has only 1 JS chunk →
 *     AC2 assertion fails.
 */
import { describe, it, expect } from 'vitest'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { routeConfig } from '../routes'

const _dir = dirname(fileURLToPath(import.meta.url))
const ROUTES_SOURCE = resolve(_dir, '../routes.ts')

describe('TestFromAC_LazyLoadingRoutes', () => {
  // ── AC1: DecisionsPage loaded via React.lazy ─────────────────────────────
  it('ac1 smoke: /decisions component is React.lazy ($$typeof === Symbol.for("react.lazy"))', () => {
    const entry = routeConfig.find((e) => e.path === '/decisions')
    expect(entry).toBeDefined()
    // React.lazy() returns an object, not a function.
    // In RED: DecisionsPage is a plain eager import (typeof 'function') — this fails.
    // In GREEN: React.lazy(…) wraps DecisionsPage — $$typeof is the react.lazy symbol.
    const comp = entry!.component as unknown as { $$typeof: symbol }
    expect(comp.$$typeof).toBe(Symbol.for('react.lazy'))
  })

  it('ac1 challenge: /decisions lazy import starts inside the React.lazy callback', () => {
    const source = readFileSync(ROUTES_SOURCE, 'utf-8')
    expect(source).toMatch(/lazy\(\s*\(\)\s*=>\s*import\(['"]\.\/pages\/DecisionsPage['"]\)\s*\)/)
    expect(source).not.toMatch(/const\s+\w*decisions\w*\s*=\s*import\(['"]\.\/pages\/DecisionsPage['"]\)/i)
  })

  // ── AC2: build produces ≥2 JS chunks ─────────────────────────────────────
  it('ac2 smoke: dist/assets/ contains ≥2 JS chunks after npm run build', () => {
    // serve/cockpit/dist/assets/ is 3 levels above serve/cockpit/web/src/__tests__/
    const distAssets = resolve(_dir, '../../../dist/assets')
    expect(
      existsSync(distAssets),
      `dist/assets/ must exist — run 'npm run build' inside serve/cockpit/web/`,
    ).toBe(true)
    const jsFiles = readdirSync(distAssets).filter((f) => f.endsWith('.js'))
    expect(
      jsFiles.length,
      `Expected ≥2 JS chunks (lazy split), found ${jsFiles.length}: ${jsFiles.join(', ')}`,
    ).toBeGreaterThanOrEqual(2)
  })
})
