import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { applyTheme, useTheme } from '../hooks/useTheme'

type MatchMediaMock = (query: string) => MediaQueryList

const VALID_THEME_VALUES = ['dark', 'light'] as const
const THEME_STORAGE_KEY = 'owlbear-theme'

function setMatchMedia(darkPreferred: boolean): void {
  const mock: MatchMediaMock = (query: string) => {
    const mediaQueryList: MediaQueryList = {
      matches: darkPreferred && query === '(prefers-color-scheme: dark)',
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => true,
    }
    return mediaQueryList
  }

  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: mock,
  })
}

// ─── AC-1 + AC-3: applyTheme bootstrap function ──────────────────────────────

describe('TestFromAC_ThemeBootstrap_1537', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    setMatchMedia(false)
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it.each(VALID_THEME_VALUES)(
    'AC-1: applyTheme reads localStorage key owlbear-theme and sets html data-theme to %s',
    (value) => {
      localStorage.setItem(THEME_STORAGE_KEY, value)

      applyTheme()

      expect(document.documentElement.dataset.theme).toBe(value)
    },
  )

  it('AC-3: applyTheme falls back to OS dark when localStorage key is absent', () => {
    setMatchMedia(true)

    applyTheme()

    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('AC-3: applyTheme falls back to OS light when localStorage key contains invalid value', () => {
    setMatchMedia(false)
    localStorage.setItem(THEME_STORAGE_KEY, 'sepia')

    applyTheme()

    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('AC-3: applyTheme falls back to OS dark when localStorage contains invalid value and OS prefers dark', () => {
    setMatchMedia(true)
    localStorage.setItem(THEME_STORAGE_KEY, 'sepia')

    applyTheme()

    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('AC-3: applyTheme falls back to OS light when localStorage key is absent and OS prefers light', () => {
    // setMatchMedia(false) already set in beforeEach

    applyTheme()

    expect(document.documentElement.dataset.theme).toBe('light')
  })
})

// ─── AC-2: useTheme hook ──────────────────────────────────────────────────────

describe('TestFromAC_UseThemeHook_1537', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    setMatchMedia(false)
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  // AC-2(a): localStorage 'dark' —————————————————————————————————————————

  it('AC-2a: when localStorage has dark, returns theme=dark and isDark=true and sets data-theme to dark', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')

    const { result } = renderHook(() => useTheme())

    expect(result.current.theme).toBe('dark')
    expect(result.current.isDark).toBe(true)
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  // AC-2(b): localStorage 'light' ————————————————————————————————————————

  it('AC-2b: when localStorage has light, returns theme=light and isDark=false and sets data-theme to light', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    const { result } = renderHook(() => useTheme())

    expect(result.current.theme).toBe('light')
    expect(result.current.isDark).toBe(false)
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  // AC-2(c): localStorage absent/cleared → auto state ————————————————————

  it('AC-2c: when localStorage is absent and OS prefers dark, returns theme=auto, isDark=true, data-theme=dark', () => {
    setMatchMedia(true)

    const { result } = renderHook(() => useTheme())

    expect(result.current.theme).toBe('auto')
    expect(result.current.isDark).toBe(true)
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('AC-2c: when localStorage is absent and OS prefers light, returns theme=auto, isDark=false, data-theme=light', () => {
    // setMatchMedia(false) already set in beforeEach

    const { result } = renderHook(() => useTheme())

    expect(result.current.theme).toBe('auto')
    expect(result.current.isDark).toBe(false)
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  // AC-2(d): full 3-transition toggle cycle light → dark → auto → light ———

  it('AC-2d: toggle cycles light→dark→auto→light with localStorage and DOM proof at every transition', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    const { result } = renderHook(() => useTheme())

    expect(result.current.theme).toBe('light')

    // Transition 1: light → dark
    act(() => {
      result.current.toggle()
    })

    expect(result.current.theme).toBe('dark')
    expect(result.current.isDark).toBe(true)
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')

    // Transition 2: dark → auto (OS light per beforeEach setMatchMedia(false))
    act(() => {
      result.current.toggle()
    })

    expect(result.current.theme).toBe('auto')
    expect(result.current.isDark).toBe(false)
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBeNull()
    expect(document.documentElement.dataset.theme).toBe('light')

    // Transition 3: auto → light
    act(() => {
      result.current.toggle()
    })

    expect(result.current.theme).toBe('light')
    expect(result.current.isDark).toBe(false)
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  // AC-2(e): isDark formula ————————————————————————————————————————————————

  it('AC-2e: isDark is true when theme=dark (formula: theme===dark)', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')

    const { result } = renderHook(() => useTheme())

    expect(result.current.isDark).toBe(true)
    expect(result.current.isDark).toBe(
      result.current.theme === 'dark' ||
        (result.current.theme === 'auto' &&
          window.matchMedia('(prefers-color-scheme: dark)').matches),
    )
  })

  it('AC-2e: isDark is true when theme=auto and OS prefers dark (formula: auto && matches)', () => {
    setMatchMedia(true)

    const { result } = renderHook(() => useTheme())

    expect(result.current.theme).toBe('auto')
    expect(result.current.isDark).toBe(true)
    expect(result.current.isDark).toBe(
      result.current.theme === 'dark' ||
        (result.current.theme === 'auto' &&
          window.matchMedia('(prefers-color-scheme: dark)').matches),
    )
  })

  it('AC-2e: isDark is false when theme=light', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    const { result } = renderHook(() => useTheme())

    expect(result.current.isDark).toBe(false)
    expect(result.current.isDark).toBe(
      result.current.theme === 'dark' ||
        (result.current.theme === 'auto' &&
          window.matchMedia('(prefers-color-scheme: dark)').matches),
    )
  })

  it('AC-2e: isDark is false when theme=auto and OS prefers light', () => {
    // setMatchMedia(false) already set in beforeEach

    const { result } = renderHook(() => useTheme())

    expect(result.current.theme).toBe('auto')
    expect(result.current.isDark).toBe(false)
    expect(result.current.isDark).toBe(
      result.current.theme === 'dark' ||
        (result.current.theme === 'auto' &&
          window.matchMedia('(prefers-color-scheme: dark)').matches),
    )
  })
})
