/** Durable runtime tests for PDS color-scheme class synchronization. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { applyTheme, useTheme } from '../hooks/useTheme'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const BOOTSTRAP_PATH = resolve(__dirname, '../../public/theme-bootstrap.js')

const THEME_STORAGE_KEY = 'owlbear-theme'

// Mined from #1555: PDS scheme classes follow bootstrap, hook, and OS changes.

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

describe('ThemeBootstrapSchemeClasses', () => {
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

describe('ApplyThemeSchemeClasses', () => {
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

describe('UseThemeSchemeClasses', () => {
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

describe('MediaChangeSchemeClasses', () => {
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
