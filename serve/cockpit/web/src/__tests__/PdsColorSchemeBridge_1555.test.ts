/**
 * RED phase tests for #1555: Bridge PDS v4 color-scheme with data-theme toggle
 *
 * All tests (except AC-7 constraint guards) MUST FAIL before the builder
 * implements the changes.
 *
 * Coverage:
 *   AC-1: main.tsx imports PDS color-scheme.css
 *   AC-2: vite.config.ts excludes Features.LightDark from lightningcss
 *   AC-3: theme-bootstrap.js sets .scheme-dark/.scheme-light on documentElement
 *   AC-4: useTheme.ts — all 3 mutation sites toggle scheme classes (no accumulation)
 *   AC-7: No app-authored color-scheme CSS property declarations in src/ CSS files
 *         (constraint guard — passes in RED because violation doesn't exist yet)
 *
 * AC-5 (Playwright e2e) → e2e/pds-scheme-dark-1555.spec.ts
 * AC-6 (existing tests green) → builder obligation, no new tests needed
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { applyTheme, useTheme } from '../hooks/useTheme'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const MAIN_TSX_PATH = resolve(__dirname, '../main.tsx')
const VITE_CONFIG_PATH = resolve(__dirname, '../../vite.config.ts')
const BOOTSTRAP_PATH = resolve(__dirname, '../../public/theme-bootstrap.js')
const SRC_DIR = resolve(__dirname, '..')

const THEME_STORAGE_KEY = 'owlbear-theme'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function setMatchMedia(darkPreferred: boolean): void {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: darkPreferred && query === '(prefers-color-scheme: dark)',
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => true,
    }),
  })
}

function runBootstrapScript(): void {
  const content = readFileSync(BOOTSTRAP_PATH, 'utf-8')
  new Function(content)()
}

interface SpiedMQL extends MediaQueryList {
  simulateChange: (newMatches: boolean) => void
}

function createSpiedMQL(initialMatches: boolean): SpiedMQL {
  const changeListeners: Array<(e: MediaQueryListEvent) => void> = []
  const mql = {
    matches: initialMatches,
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addEventListener: vi.fn((type: string, handler: (e: MediaQueryListEvent) => void) => {
      if (type === 'change') changeListeners.push(handler)
    }),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(() => true),
    simulateChange(newMatches: boolean): void {
      mql.matches = newMatches
      changeListeners.forEach((h) => h({ matches: newMatches } as unknown as MediaQueryListEvent))
    },
  } as SpiedMQL
  return mql
}

function installSpiedMQL(mql: SpiedMQL): void {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (_query: string) => mql,
  })
}

function cleanupThemeState(): void {
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
  document.documentElement.classList.remove('scheme-dark', 'scheme-light')
}

function collectCssFiles(dir: string): string[] {
  const result: string[] = []
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry)
    const st = statSync(fullPath)
    if (st.isDirectory()) {
      result.push(...collectCssFiles(fullPath))
    } else if (entry.endsWith('.css')) {
      result.push(fullPath)
    }
  }
  return result
}

// ─── AC-1: main.tsx imports PDS color-scheme.css ──────────────────────────────

describe('TestFromAC_MainTsxColorSchemeImport_1555', () => {
  it('AC-1: main.tsx contains a static import of PDS color-scheme.css at the exact package path', () => {
    const content = readFileSync(MAIN_TSX_PATH, 'utf-8')

    expect(content).toContain(
      '@porsche-design-system/components-react/global-styles/color-scheme.css',
    )
  })

  it('AC-1: the color-scheme.css import line is not commented out', () => {
    const content = readFileSync(MAIN_TSX_PATH, 'utf-8')
    const lines = content.split('\n')
    const importLine = lines.find((l) => l.includes('color-scheme.css'))

    expect(importLine, 'import line for color-scheme.css must exist in main.tsx').toBeDefined()
    expect(importLine!.trimStart()).not.toMatch(/^\/\//)
    expect(importLine!.trimStart()).not.toMatch(/^\/\*/)
  })
})

// ─── AC-2: vite.config.ts excludes Features.LightDark ────────────────────────

describe('TestFromAC_ViteConfigLightDark_1555', () => {
  it('AC-2: vite.config.ts references Features.LightDark', () => {
    const content = readFileSync(VITE_CONFIG_PATH, 'utf-8')

    expect(content).toContain('Features.LightDark')
  })

  it('AC-2: vite.config.ts contains a lightningcss exclude configuration block', () => {
    const content = readFileSync(VITE_CONFIG_PATH, 'utf-8')

    expect(content).toMatch(/lightningcss/)
    expect(content).toMatch(/exclude/)
  })
})

// ─── AC-3: theme-bootstrap.js sets .scheme-dark / .scheme-light ──────────────

describe('TestFromAC_BootstrapSchemeClass_1555', () => {
  beforeEach(() => {
    cleanupThemeState()
    setMatchMedia(false)
  })

  afterEach(() => {
    cleanupThemeState()
  })

  // Happy path

  it('AC-3 happy: stored=dark → .scheme-dark class added to documentElement', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')

    runBootstrapScript()

    expect(document.documentElement.classList.contains('scheme-dark')).toBe(true)
  })

  it('AC-3 happy: stored=light → .scheme-light class added to documentElement', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    runBootstrapScript()

    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
  })

  it('AC-3 happy: stored=dark → data-theme=dark AND .scheme-dark are set together', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(document.documentElement.classList.contains('scheme-dark')).toBe(true)
  })

  it('AC-3 happy: stored=light → data-theme=light AND .scheme-light are set together', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('light')
    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
  })

  // Edge cases — OS preference fallback

  it('AC-3 edge: OS prefers dark, no localStorage → .scheme-dark added', () => {
    setMatchMedia(true)

    runBootstrapScript()

    expect(document.documentElement.classList.contains('scheme-dark')).toBe(true)
  })

  it('AC-3 edge: OS prefers light, no localStorage → .scheme-light added', () => {
    // setMatchMedia(false) already in beforeEach

    runBootstrapScript()

    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
  })

  // Boundary — no class accumulation across runs

  it('AC-3 boundary: two bootstrap runs with flipped theme → only current scheme class, no accumulation', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')
    runBootstrapScript()

    localStorage.setItem(THEME_STORAGE_KEY, 'light')
    runBootstrapScript()

    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
    expect(document.documentElement.classList.contains('scheme-dark')).toBe(false)
  })
})

// ─── AC-4 (site 1): applyTheme() exported function ───────────────────────────

describe('TestFromAC_ApplyThemeSchemeClass_1555', () => {
  beforeEach(() => {
    cleanupThemeState()
    setMatchMedia(false)
  })

  afterEach(() => {
    cleanupThemeState()
  })

  it('AC-4 site1 happy: applyTheme() with dark localStorage → .scheme-dark added to documentElement', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')

    applyTheme()

    expect(document.documentElement.classList.contains('scheme-dark')).toBe(true)
  })

  it('AC-4 site1 happy: applyTheme() with light localStorage → .scheme-light added to documentElement', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    applyTheme()

    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
  })

  it('AC-4 site1 boundary: applyTheme() called twice with flipped theme → no accumulation', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')
    applyTheme()

    localStorage.setItem(THEME_STORAGE_KEY, 'light')
    applyTheme()

    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
    expect(document.documentElement.classList.contains('scheme-dark')).toBe(false)
  })
})

// ─── AC-4 (site 2): useTheme hook effect (theme / systemPrefersDark change) ───

describe('TestFromAC_UseThemeEffectSchemeClass_1555', () => {
  beforeEach(() => {
    cleanupThemeState()
    setMatchMedia(false)
  })

  afterEach(() => {
    cleanupThemeState()
  })

  it('AC-4 site2 happy: hook mount with dark localStorage → .scheme-dark added to documentElement', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')

    const { unmount } = renderHook(() => useTheme())

    expect(document.documentElement.classList.contains('scheme-dark')).toBe(true)
    unmount()
  })

  it('AC-4 site2 happy: hook mount with light localStorage → .scheme-light added to documentElement', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    const { unmount } = renderHook(() => useTheme())

    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
    unmount()
  })

  it('AC-4 site2 happy: toggle light→dark → .scheme-dark replaces .scheme-light on documentElement', async () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    const { result, unmount } = renderHook(() => useTheme())

    await act(async () => {
      result.current.toggle()
    })

    expect(document.documentElement.classList.contains('scheme-dark')).toBe(true)
    unmount()
  })

  it('AC-4 site2 boundary: after toggle dark→auto (OS prefers light), .scheme-light present and .scheme-dark absent', async () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')
    // setMatchMedia(false) = OS prefers light, set in beforeEach

    const { result, unmount } = renderHook(() => useTheme())

    await act(async () => {
      result.current.toggle() // dark → auto (OS light)
    })

    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
    expect(document.documentElement.classList.contains('scheme-dark')).toBe(false)
    unmount()
  })
})

// ─── AC-4 (site 3): media-change handler (fires on OS preference change) ──────

describe('TestFromAC_MediaChangeSchemeClass_1555', () => {
  let mql: SpiedMQL

  beforeEach(() => {
    cleanupThemeState()
    mql = createSpiedMQL(false)
    installSpiedMQL(mql)
  })

  afterEach(() => {
    cleanupThemeState()
  })

  it('AC-4 site3 happy: OS changes light→dark in auto mode → .scheme-dark added to documentElement', async () => {
    // theme=auto (no localStorage), OS prefers light initially
    const { unmount } = renderHook(() => useTheme())

    await act(async () => {
      mql.simulateChange(true)
    })

    expect(document.documentElement.classList.contains('scheme-dark')).toBe(true)
    unmount()
  })

  it('AC-4 site3 happy: OS changes dark→light in auto mode → .scheme-light added to documentElement', async () => {
    mql = createSpiedMQL(true)
    installSpiedMQL(mql)

    const { unmount } = renderHook(() => useTheme())

    await act(async () => {
      mql.simulateChange(false)
    })

    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
    unmount()
  })

  it('AC-4 site3 boundary: OS flip light→dark then dark→light → no class accumulation', async () => {
    const { unmount } = renderHook(() => useTheme())

    await act(async () => {
      mql.simulateChange(true) // → dark
    })

    await act(async () => {
      mql.simulateChange(false) // → light, remove dark
    })

    expect(document.documentElement.classList.contains('scheme-light')).toBe(true)
    expect(document.documentElement.classList.contains('scheme-dark')).toBe(false)
    unmount()
  })
})

// ─── AC-7: No app-authored color-scheme CSS property declarations ──────────────
//
// NOTE: These are constraint guard tests. They PASS in RED phase because no
// app CSS files currently declare `color-scheme:`. They catch regressions if the
// builder accidentally introduces the property in app CSS. AC coverage is
// maintained per pipeline protocol; passing tests are noted in Test-Writer Notes.

describe('TestFromAC_NoAppColorSchemeProp_1555', () => {
  it('AC-7: no CSS file under src/ contains a color-scheme property declaration (not media query)', () => {
    const cssFiles = collectCssFiles(SRC_DIR)

    expect(cssFiles.length, 'must find at least one CSS file to scan').toBeGreaterThan(0)

    const violators: string[] = []
    for (const filePath of cssFiles) {
      const content = readFileSync(filePath, 'utf-8')
      // Match "color-scheme:" only as a CSS property (preceded by {, ;, or newline+whitespace)
      // Does NOT match "@media (prefers-color-scheme: ...)" or "/*...color-scheme:..."
      if (/(?:^|[{;])\s*color-scheme\s*:/m.test(content)) {
        violators.push(filePath)
      }
    }

    expect(violators, `app CSS files must not declare color-scheme property: ${violators.join(', ')}`).toEqual([])
  })

  it('AC-7: tokens.css specifically does not declare a color-scheme property', () => {
    const tokensPath = join(SRC_DIR, 'tokens.css')
    const content = readFileSync(tokensPath, 'utf-8')

    // Only @media (prefers-color-scheme: ...) is allowed — not a property declaration
    expect(content).not.toMatch(/(?:^|[{;])\s*color-scheme\s*:/m)
  })
})
