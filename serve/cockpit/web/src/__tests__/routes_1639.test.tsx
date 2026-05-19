/**
 * Task #1639 — P1-01: Tab routing infrastructure
 * AC1 coverage: routeConfig array — export, entry count, path values, required field shape
 * AC3 coverage: array extensibility shape
 *
 * RED phase: routes.ts does not exist yet → ImportError causes all tests to fail.
 */
import { describe, it, expect } from 'vitest'
import { routeConfig } from '../routes'

describe('TestFromAC_RouteConfig', () => {
  // ── AC1: routeConfig is exported ─────────────────────────────────────────
  it('ac1 happy: routeConfig is a named export from routes.ts', () => {
    expect(routeConfig).toBeDefined()
  })

  it('ac1 happy: routeConfig is an array', () => {
    expect(Array.isArray(routeConfig)).toBe(true)
  })

  // ── AC1: minimum two entries ─────────────────────────────────────────────
  it('ac1 happy: routeConfig has at least two entries', () => {
    expect(routeConfig.length).toBeGreaterThanOrEqual(2)
  })

  // ── AC1: required paths present ──────────────────────────────────────────
  it('ac1 happy: routeConfig contains an entry with path "/"', () => {
    const paths = routeConfig.map((entry) => entry.path)
    expect(paths).toContain('/')
  })

  it('ac1 happy: routeConfig contains an entry with path "/decisions"', () => {
    const paths = routeConfig.map((entry) => entry.path)
    expect(paths).toContain('/decisions')
  })

  // ── AC1: all four required fields present on every entry ─────────────────
  it('ac1 happy: all entries have path, label, icon, and component fields', () => {
    for (const entry of routeConfig) {
      expect(entry).toHaveProperty('path')
      expect(entry).toHaveProperty('label')
      expect(entry).toHaveProperty('icon')
      expect(entry).toHaveProperty('component')
    }
  })

  it('ac1 happy: component field is a callable ComponentType on every entry', () => {
    for (const entry of routeConfig) {
      expect(typeof entry.component).toBe('function')
    }
  })

  // ── AC1 boundary: field value types ──────────────────────────────────────
  it('ac1 boundary: path values are non-empty strings', () => {
    for (const entry of routeConfig) {
      expect(typeof entry.path).toBe('string')
      expect(entry.path.length).toBeGreaterThan(0)
    }
  })

  it('ac1 boundary: label values are non-empty strings', () => {
    for (const entry of routeConfig) {
      expect(typeof entry.label).toBe('string')
      expect(entry.label.length).toBeGreaterThan(0)
    }
  })

  // ── AC1 edge: paths are unique within the config ──────────────────────────
  it('ac1 edge: all route paths are unique (no duplicates)', () => {
    const paths = routeConfig.map((entry) => entry.path)
    const uniquePaths = new Set(paths)
    expect(uniquePaths.size).toBe(paths.length)
  })

  // ── AC3: routeConfig is a plain mutable array ─────────────────────────────
  it('ac3 boundary: routeConfig is a plain Array (not a frozen object)', () => {
    // Extensibility requires the array to be a standard Array instance
    expect(Array.isArray(routeConfig)).toBe(true)
    // A frozen array would prevent consumers from extending it
    expect(Object.isFrozen(routeConfig)).toBe(false)
  })
})
