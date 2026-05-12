/**
 * Smoke tests for pdsVersionCheckPlugin — task #1513
 * Proof bundle: smoke — one test per AC line.
 * Establishes lifecycle-hook simulation pattern for Vite plugin tests
 * (configResolved + buildStart hooks with mocked node:fs).
 *
 * @vitejs/plugin-react is mocked to prevent esbuild initialisation in jsdom.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Hoisted mocks — must precede all module imports
vi.mock('vitest/config', () => ({ defineConfig: (c: unknown) => c }))
vi.mock('@vitejs/plugin-react', () => ({
  default: () => [{ name: 'react-plugin' }],
  reactCompilerPreset: () => 'react-compiler-preset',
}))
vi.mock('@rolldown/plugin-babel', () => ({ default: () => ({ name: 'babel-plugin' }) }))
vi.mock('node:fs', () => ({
  readFileSync: vi.fn(),
  readdirSync: vi.fn(),
}))

import { readFileSync, readdirSync } from 'node:fs'
import config from '../../vite.config'

type Plugin = Record<string, unknown>

function findPlugin(plugins: unknown[], name: string): Plugin | undefined {
  for (const p of (plugins as unknown[]).flat(2)) {
    if (p && typeof p === 'object' && (p as Plugin).name === name) {
      return p as Plugin
    }
  }
  return undefined
}

const FAKE_ROOT = '/fake/project'

function invokeConfigResolved(plugin: Plugin): void {
  const configResolved = plugin.configResolved as (cfg: { root: string }) => void
  configResolved({ root: FAKE_ROOT })
}

describe('TestFromAC_PdsVersionCheck', () => {
  const rawConfig = config as { plugins?: unknown[] }
  const plugin = findPlugin(rawConfig.plugins ?? [], 'pds-version-check')

  let warnSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.clearAllMocks()
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
  })

  // AC-1: Plugin is registered in the vite config plugins array with correct name
  it('AC-1: vite config registers a plugin named pds-version-check', () => {
    expect(plugin).toBeDefined()
    expect(plugin!.name).toBe('pds-version-check')
  })

  // AC-2: Plugin has configResolved + buildStart hooks; no apply property
  it('AC-2: plugin has configResolved and buildStart hooks with no apply property', () => {
    expect(plugin).toBeDefined()
    expect(typeof plugin!.configResolved).toBe('function')
    expect(typeof plugin!.buildStart).toBe('function')
    expect(plugin!.apply).toBeUndefined()
  })

  // AC-3: buildStart reads npm package version from the expected path
  it('AC-3: buildStart reads version from @porsche-design-system/components-js/package.json', async () => {
    expect(plugin).toBeDefined()
    vi.mocked(readFileSync).mockReturnValue(JSON.stringify({ version: '3.21.0' }) as never)
    vi.mocked(readdirSync).mockReturnValue(['porsche-design-system.v3.21.0.abc123.js'] as never)
    invokeConfigResolved(plugin!)
    const buildStart = plugin!.buildStart as () => Promise<void> | void

    await buildStart()

    expect(vi.mocked(readFileSync)).toHaveBeenCalledWith(
      expect.stringContaining('@porsche-design-system/components-js/package.json'),
      'utf-8',
    )
  })

  // AC-4: buildStart scans the correct assets directory
  it('AC-4: buildStart scans public/porsche-design-system/components/ directory', async () => {
    expect(plugin).toBeDefined()
    vi.mocked(readFileSync).mockReturnValue(JSON.stringify({ version: '3.21.0' }) as never)
    vi.mocked(readdirSync).mockReturnValue(['porsche-design-system.v3.21.0.abc123.js'] as never)
    invokeConfigResolved(plugin!)
    const buildStart = plugin!.buildStart as () => Promise<void> | void

    await buildStart()

    expect(vi.mocked(readdirSync)).toHaveBeenCalledWith(
      expect.stringContaining('public/porsche-design-system/components'),
    )
  })

  // AC-5: Version mismatch → warn contains both versions and sync command
  it('AC-5: buildStart warns with both version strings and npm run sync:pds on mismatch', async () => {
    expect(plugin).toBeDefined()
    vi.mocked(readFileSync).mockReturnValue(JSON.stringify({ version: '3.22.0' }) as never)
    vi.mocked(readdirSync).mockReturnValue(['porsche-design-system.v3.21.0.abc123.js'] as never)
    invokeConfigResolved(plugin!)
    const buildStart = plugin!.buildStart as () => Promise<void> | void

    await buildStart()

    const warnMsg = (warnSpy.mock.calls[0]?.[0] as string) ?? ''
    expect(warnMsg).toContain('3.21.0')
    expect(warnMsg).toContain('3.22.0')
    expect(warnMsg).toContain('npm run sync:pds')
  })

  // AC-6: No matching file → warn indicates missing assets and sync command
  it('AC-6: buildStart warns about missing assets with npm run sync:pds when no file matches', async () => {
    expect(plugin).toBeDefined()
    vi.mocked(readFileSync).mockReturnValue(JSON.stringify({ version: '3.22.0' }) as never)
    vi.mocked(readdirSync).mockReturnValue(['unrelated-file.js'] as never)
    invokeConfigResolved(plugin!)
    const buildStart = plugin!.buildStart as () => Promise<void> | void

    await buildStart()

    const warnMsg = (warnSpy.mock.calls[0]?.[0] as string) ?? ''
    expect(warnMsg).toContain('npm run sync:pds')
  })

  // AC-7: Any thrown error → console.warn skip message, no re-throw
  it('AC-7: buildStart warns "PDS version check skipped: {msg}" and does not throw on error', async () => {
    expect(plugin).toBeDefined()
    vi.mocked(readFileSync).mockImplementation(() => {
      throw new Error('ENOENT: no such file')
    })
    invokeConfigResolved(plugin!)
    const buildStart = plugin!.buildStart as () => Promise<void> | void

    await buildStart()

    const warnMsg = (warnSpy.mock.calls[0]?.[0] as string) ?? ''
    expect(warnMsg).toContain('PDS version check skipped:')
    expect(warnMsg).toContain('ENOENT: no such file')
  })

  // AC-4 (retry gap): multiple matching filenames — plugin must use first regex match
  it('AC-4(first-match): uses first regex-matching filename as asset version when multiple matches present', async () => {
    expect(plugin).toBeDefined()
    vi.mocked(readFileSync).mockReturnValue(JSON.stringify({ version: '3.21.0' }) as never)
    // First matching file is v3.19.0; second is v3.21.0 — plugin must pick first
    vi.mocked(readdirSync).mockReturnValue([
      'porsche-design-system.v3.19.0.xyz123.js',
      'porsche-design-system.v3.21.0.abc456.js',
    ] as never)
    invokeConfigResolved(plugin!)
    const buildStart = plugin!.buildStart as () => Promise<void> | void

    await buildStart()

    const warnMsg = (warnSpy.mock.calls[0]?.[0] as string) ?? ''
    // Warning must reference first-match asset version (3.19.0), not the second (3.21.0 would be silent match)
    expect(warnMsg).toContain('3.19.0')
    expect(warnMsg).toContain('3.21.0')
    expect(warnMsg).toContain('npm run sync:pds')
  })

  // AC-6 (retry gap): missing-assets warning must explicitly indicate missing/unmatched core asset
  it('AC-6(missing-indicator): warning explicitly states missing or unmatched core asset (not just sync command)', async () => {
    expect(plugin).toBeDefined()
    vi.mocked(readFileSync).mockReturnValue(JSON.stringify({ version: '3.22.0' }) as never)
    vi.mocked(readdirSync).mockReturnValue(['unrelated-file.js'] as never)
    invokeConfigResolved(plugin!)
    const buildStart = plugin!.buildStart as () => Promise<void> | void

    await buildStart()

    const warnMsg = (warnSpy.mock.calls[0]?.[0] as string) ?? ''
    // Must indicate the asset is missing/unmatched — remediation command alone is insufficient proof
    expect(warnMsg.toLowerCase()).toMatch(/no matching|missing|not found/)
    expect(warnMsg).toContain('npm run sync:pds')
  })
})
