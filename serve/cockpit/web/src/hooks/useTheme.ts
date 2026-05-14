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

function readStoredTheme(): Theme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  return isResolvedTheme(stored) ? stored : 'auto'
}

function setDocumentTheme(resolved: ResolvedTheme): void {
  const root = document.documentElement
  root.dataset.theme = resolved
  root.classList.remove('scheme-dark', 'scheme-light')
  root.classList.add(resolved === 'dark' ? 'scheme-dark' : 'scheme-light')
}

export function applyTheme(): ResolvedTheme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  const resolved = isResolvedTheme(stored) ? stored : (prefersDark() ? 'dark' : 'light')

  setDocumentTheme(resolved)
  return resolved
}

interface UseThemeResult {
  theme: Theme
  toggle: () => void
  isDark: boolean
}

export function useTheme(): UseThemeResult {
  const mediaQueryList = useMemo(
    () => window.matchMedia('(prefers-color-scheme: dark)'),
    [],
  )
  const [theme, setTheme] = useState<Theme>(() => readStoredTheme())
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(
    () => mediaQueryList.matches,
  )

  useEffect(() => {
    const resolved =
      theme === 'auto' ? (systemPrefersDark ? 'dark' : 'light') : theme

    if (theme === 'auto') {
      localStorage.removeItem(THEME_STORAGE_KEY)
    } else {
      localStorage.setItem(THEME_STORAGE_KEY, theme)
    }

    setDocumentTheme(resolved)
  }, [theme, systemPrefersDark])

  useEffect(() => {
    if (theme !== 'auto') {
      return
    }

    setSystemPrefersDark(mediaQueryList.matches)

    const handleChange = (event: MediaQueryListEvent): void => {
      setSystemPrefersDark(event.matches)
      setDocumentTheme(event.matches ? 'dark' : 'light')
    }

    mediaQueryList.addEventListener('change', handleChange)

    return () => {
      mediaQueryList.removeEventListener('change', handleChange)
    }
  }, [theme, mediaQueryList])

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
    () => theme === 'dark' || (theme === 'auto' && systemPrefersDark),
    [theme, systemPrefersDark],
  )

  return { theme, toggle, isDark }
}
