import { useEffect, useMemo, useState } from 'react'

const THEME_STORAGE_KEY = 'owlbear-theme'
const VALID_STORAGE_THEMES = new Set(['dark', 'light'])

type ResolvedTheme = 'dark' | 'light'
export type Theme = ResolvedTheme | 'auto'

function isResolvedTheme(value: string | null): value is ResolvedTheme {
  return value !== null && VALID_STORAGE_THEMES.has(value)
}

function prefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function resolveTheme(theme: Theme): ResolvedTheme {
  if (theme === 'auto') {
    return prefersDark() ? 'dark' : 'light'
  }

  return theme
}

function readStoredTheme(): Theme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  return isResolvedTheme(stored) ? stored : 'auto'
}

export function applyTheme(): ResolvedTheme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  const resolved = isResolvedTheme(stored) ? stored : (prefersDark() ? 'dark' : 'light')

  document.documentElement.dataset.theme = resolved
  return resolved
}

interface UseThemeResult {
  theme: Theme
  toggle: () => void
  isDark: boolean
}

export function useTheme(): UseThemeResult {
  const [theme, setTheme] = useState<Theme>(() => readStoredTheme())

  useEffect(() => {
    const resolved = resolveTheme(theme)

    if (theme === 'auto') {
      localStorage.removeItem(THEME_STORAGE_KEY)
    } else {
      localStorage.setItem(THEME_STORAGE_KEY, theme)
    }

    document.documentElement.dataset.theme = resolved
  }, [theme])

  const toggle = (): void => {
    setTheme((current) => {
      if (current === 'light') {
        return 'dark'
      }

      if (current === 'dark') {
        return 'auto'
      }

      return 'light'
    })
  }

  const isDark = useMemo(
    () => theme === 'dark' || (theme === 'auto' && prefersDark()),
    [theme],
  )

  return { theme, toggle, isDark }
}
