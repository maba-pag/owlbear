/**
 * AC-8 (retry gap): resolve.alias PDS color-scheme.css mapping resolves correctly
 * in Vitest import context — task #1555.
 *
 * The existing vite_config.test.ts and vite_config_pds_1513.test.ts cover the
 * "importable without TypeError" half of AC-8 (they fail with the same TypeError).
 * This file covers the second half: after importability is restored, the
 * resolve.alias entry must map the correct key to a path ending in color-scheme.css.
 *
 * RED reason: module-level fileURLToPath(new URL('./node_modules/...', import.meta.url))
 * in vite.config.ts throws TypeError when import.meta.url is not a file:// URL
 * (Vitest jsdom runner context). All three tests fail at module load time before
 * any assertions execute.
 *
 * Builder fix: make the PDS alias path resolution lazy (e.g. inside a function
 * called only at build/serve time, or use path.resolve(__dirname, ...)) so that
 * vite.config.ts can be safely imported in Vitest without a file:// URL.
 */
import { describe, it, expect, vi } from 'vitest'

// Hoisted mocks — must precede all module imports.
// Mirror the pattern from vite_config.test.ts and vite_config_pds_1513.test.ts
// to prevent esbuild initialisation and node:fs side-effects during import.
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

// This import currently throws:
//   TypeError: The URL must be of scheme file
// because vite.config.ts evaluates fileURLToPath(new URL(..., import.meta.url))
// at module level, where import.meta.url is not a file:// URL in Vitest.
import config from '../../vite.config'

const PDS_SCHEME_CSS_KEY =
  '@porsche-design-system/components-react/global-styles/color-scheme.css'

describe('TestFromAC_ViteConfigAlias_1555', () => {
  type RawConfig = {
    resolve?: {
      alias?: Record<string, string>
    }
  }

  // AC-8: the alias object exists and contains the expected PDS key
  it('AC-8: resolve.alias contains the PDS color-scheme.css mapping key', () => {
    const rawConfig = config as RawConfig
    expect(rawConfig.resolve?.alias, 'resolve.alias must be defined').toBeDefined()
    expect(
      PDS_SCHEME_CSS_KEY in (rawConfig.resolve?.alias ?? {}),
      `resolve.alias must have key "${PDS_SCHEME_CSS_KEY}"`,
    ).toBe(true)
  })

  // AC-8: alias value is a non-empty string (not undefined / null / number)
  it('AC-8: resolve.alias PDS color-scheme.css value is a non-empty string', () => {
    const rawConfig = config as RawConfig
    const value = rawConfig.resolve?.alias?.[PDS_SCHEME_CSS_KEY]
    expect(typeof value, 'alias value must be a string').toBe('string')
    expect((value as string).length, 'alias value must be non-empty').toBeGreaterThan(0)
  })

  // AC-8: alias value resolves to the correct CSS file
  it('AC-8: resolve.alias PDS color-scheme.css value ends with color-scheme.css', () => {
    const rawConfig = config as RawConfig
    const value = rawConfig.resolve?.alias?.[PDS_SCHEME_CSS_KEY] ?? ''
    expect(value).toMatch(/color-scheme\.css$/)
  })
})
