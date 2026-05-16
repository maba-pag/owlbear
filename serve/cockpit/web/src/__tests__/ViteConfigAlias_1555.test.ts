/**
 * Regression coverage for task #1594 cleanup.
 *
 * The old resolve.alias bridge for color-scheme.css is intentionally removed
 * because tokens.css imports global-styles/index.css directly.
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

const LEGACY_PDS_SCHEME_CSS_KEY =
  '@porsche-design-system/components-react/global-styles/color-scheme.css'

describe('TestFromAC_ViteConfigAlias_1555', () => {
  type RawConfig = {
    resolve?: {
      alias?: Record<string, string>
    }
  }

  it('vite.config.ts stays importable in Vitest context', () => {
    expect(config).toBeDefined()
  })

  // AC-6: the legacy color-scheme.css alias key is removed
  it('resolve.alias does not contain the legacy PDS color-scheme.css key', () => {
    const rawConfig = config as RawConfig
    expect(LEGACY_PDS_SCHEME_CSS_KEY in (rawConfig.resolve?.alias ?? {})).toBe(false)
  })

  it('resolve.alias omits legacy key regardless of alias object presence', () => {
    const rawConfig = config as RawConfig
    const aliases = rawConfig.resolve?.alias ?? {}
    expect(Object.prototype.hasOwnProperty.call(aliases, LEGACY_PDS_SCHEME_CSS_KEY)).toBe(false)
  })
})
