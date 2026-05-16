/**
 * (retry): AC10 — CSP meta tag via cspPlugin in vite.config.ts
 *
 * Reviewer Pass 2 identified missing TestFromAC_CSP coverage.
 * Verifies the production-only cspPlugin injects the correct Content-Security-Policy
 * meta tag during builds and is guarded from dev/serve via apply: 'build'.
 *
 * @vitejs/plugin-react is mocked to prevent esbuild initialization in jsdom
 * (esbuild's TextEncoder invariant fails in jsdom environment).
 */
import { describe, it, expect, vi } from 'vitest'

// Must be hoisted before vite.config import to suppress esbuild initialisation
vi.mock('vitest/config', () => ({ defineConfig: (c: unknown) => c }))
vi.mock('@vitejs/plugin-react', () => ({
  default: () => [{ name: 'react-plugin' }],
  reactCompilerPreset: () => 'react-compiler-preset',
}))
vi.mock('@rolldown/plugin-babel', () => ({ default: () => ({ name: 'babel-plugin' }) }))

import config from '../../vite.config'

// Flatten nested plugin arrays (e.g. react() returns Plugin[])
function findCspPlugin(plugins: unknown[]): Record<string, unknown> | undefined {
  for (const p of (plugins as unknown[]).flat(2)) {
    if (p && typeof p === 'object' && (p as Record<string, unknown>).name === 'csp-meta') {
      return p as Record<string, unknown>
    }
  }
  return undefined
}

const SAMPLE_HTML = '<!DOCTYPE html><html><head></head><body></body></html>'
const NO_HEAD_HTML = '<html><body>no head tag here</body></html>'

describe('TestFromAC_CSP', () => {
  const rawConfig = config as { plugins?: unknown[] }
  const plugins = rawConfig.plugins ?? []
  const csp = findCspPlugin(plugins)
  const transform = csp?.transformIndexHtml as ((html: string) => string) | undefined

  // ─── Plugin registration and dev guard ────────────────────────────────────

  it('vite config registers a plugin named csp-meta', () => {
    expect(csp).toBeDefined()
    expect(csp!.name).toBe('csp-meta')
  })

  it('csp-meta plugin has apply: "build" — never runs during dev/serve', () => {
    expect(csp).toBeDefined()
    expect(csp!.apply).toBe('build')
  })

  // ─── CSP meta tag injection (build mode) ──────────────────────────────────

  it('transformIndexHtml injects <meta http-equiv="Content-Security-Policy"> tag', () => {
    expect(transform).toBeDefined()
    const result = transform!(SAMPLE_HTML)
    expect(result).toContain('<meta http-equiv="Content-Security-Policy"')
  })

  it("CSP policy includes default-src 'self'", () => {
    expect(transform).toBeDefined()
    const result = transform!(SAMPLE_HTML)
    expect(result).toContain("default-src 'self'")
  })

  it("CSP policy includes script-src 'self'", () => {
    expect(transform).toBeDefined()
    const result = transform!(SAMPLE_HTML)
    expect(result).toContain("script-src 'self'")
  })

  // ─── Edge: no-op when </head> is absent ───────────────────────────────────

  it('transformIndexHtml leaves HTML unchanged when no </head> tag is present', () => {
    expect(transform).toBeDefined()
    const result = transform!(NO_HEAD_HTML)
    expect(result).toBe(NO_HEAD_HTML)
    expect(result).not.toContain('Content-Security-Policy')
  })
})
