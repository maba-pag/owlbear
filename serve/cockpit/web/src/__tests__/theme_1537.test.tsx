import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { applyTheme, useTheme } from '../hooks/useTheme'

type MatchMediaMock = (query: string) => MediaQueryList

const VALID_THEME_VALUES = ['dark', 'light'] as const
const THEME_STORAGE_KEY = 'owlbear-theme'

function setMatchMedia(matches: boolean): void {
  const mock: MatchMediaMock = (query: string) => {
    const mediaQueryList: MediaQueryList = {
      matches,
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
    'AC-1: applyTheme reads key owlbear-theme and sets html data-theme to %s',
    (value) => {
      localStorage.setItem(THEME_STORAGE_KEY, value)

      applyTheme()

      expect(document.documentElement.dataset.theme).toBe(value)
    },
  )

  it('AC-3: applyTheme uses OS preference dark when localStorage key is missing', () => {
    setMatchMedia(true)

    applyTheme()

    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('AC-3: applyTheme uses OS preference light when localStorage key is invalid', () => {
    setMatchMedia(false)
    localStorage.setItem(THEME_STORAGE_KEY, 'sepia')

    applyTheme()

    expect(document.documentElement.dataset.theme).toBe('light')
  })
})

describe('TestFromAC_UseThemeHook_1537', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.dataset.theme = 'light'
    setMatchMedia(false)
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it('AC-2: returns dark theme and isDark true when html data-theme is dark', () => {
    document.documentElement.dataset.theme = 'dark'

    const { result } = renderHook(() => useTheme())

    expect(result.current.theme).toBe('dark')
    expect(result.current.isDark).toBe(true)
    expect(result.current.isDark).toBe(result.current.theme === 'dark')
  })

  it('AC-2: toggle flips data-theme and updates localStorage', () => {
    const { result } = renderHook(() => useTheme())

    expect(result.current.theme).toBe('light')

    act(() => {
      result.current.toggle()
    })

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
    expect(result.current.theme).toBe('dark')
    expect(result.current.isDark).toBe(result.current.theme === 'dark')
  })
})
