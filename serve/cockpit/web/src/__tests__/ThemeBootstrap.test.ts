import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { existsSync, readFileSync } from 'node:fs'
import { useTheme } from '../hooks/useTheme'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const BOOTSTRAP_PATH = resolve(__dirname, '../../public/theme-bootstrap.js')
const INDEX_HTML_PATH = resolve(__dirname, '../../index.html')
const THEME_STORAGE_KEY = 'owlbear-theme'

type MatchMediaMock = (query: string) => MediaQueryList

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

function runBootstrapScript(): void {
  const content = readFileSync(BOOTSTRAP_PATH, 'utf-8')
  new Function(content)()
}

// ─── AC-4: OS preference listener helpers ─────────────────────────────────────

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

// ─── AC-1: file existence ─────────────────────────────────────────────────────

describe('TestFromAC_ThemeBootstrapFile_1545', () => {
  it('AC-1: public/theme-bootstrap.js exists in the public directory', () => {
    expect(existsSync(BOOTSTRAP_PATH)).toBe(true)
  })
})

// ─── AC-1: bootstrap script behavior ─────────────────────────────────────────

describe('TestFromAC_ThemeBootstrapBehavior_1545', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    setMatchMedia(false)
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  // Happy path — valid localStorage values

  it('AC-1 happy: localStorage owlbear-theme=dark → sets document.documentElement.dataset.theme to dark', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('AC-1 happy: localStorage owlbear-theme=light → sets document.documentElement.dataset.theme to light', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('light')
  })

  // Edge cases — OS preference fallback when localStorage is absent

  it('AC-1 edge: localStorage absent and OS prefers dark → data-theme=dark', () => {
    setMatchMedia(true)

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('AC-1 edge: localStorage absent and OS prefers light → data-theme=light', () => {
    // setMatchMedia(false) already set in beforeEach

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('light')
  })

  // Error paths — invalid localStorage values

  it('AC-1 error: invalid value "sepia" treated as absent → falls back to OS light preference', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'sepia')

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('AC-1 error: invalid value "DARK" (uppercase) treated as absent → falls back to OS light preference', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'DARK')

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('AC-1 error: invalid value "auto" treated as absent → falls back to OS light preference', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'auto')

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('AC-1 error: invalid value "sepia" with OS dark preference → data-theme=dark', () => {
    setMatchMedia(true)
    localStorage.setItem(THEME_STORAGE_KEY, 'sepia')

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  // Boundary conditions — validation accepts only 'dark' and 'light'

  it('AC-1 boundary: empty string is invalid → falls back to OS light preference', () => {
    localStorage.setItem(THEME_STORAGE_KEY, '')

    runBootstrapScript()

    expect(document.documentElement.dataset.theme).toBe('light')
  })
})

// ─── AC-1: index.html wiring ──────────────────────────────────────────────────

describe('TestFromAC_IndexHtmlBootstrap_1545', () => {
  let indexHtml: string

  beforeEach(() => {
    indexHtml = readFileSync(INDEX_HTML_PATH, 'utf-8')
  })

  it('AC-1: index.html contains <script src="/theme-bootstrap.js"> tag', () => {
    expect(indexHtml).toContain('src="/theme-bootstrap.js"')
  })

  it('AC-1: theme-bootstrap.js script is first child of <body>, not in <head>, before <div id="root">', () => {
    const bodyMatch = indexHtml.match(/<body[^>]*>([\s\S]*?)<\/body>/i)
    expect(bodyMatch).not.toBeNull()
    const bodyContent = bodyMatch![1]
    const scriptPos = bodyContent.indexOf('/theme-bootstrap.js')
    const rootDivPos = bodyContent.indexOf('<div id="root">')

    expect(scriptPos).toBeGreaterThanOrEqual(0) // script must be inside <body>
    expect(scriptPos).toBeLessThan(rootDivPos) // must appear before <div id="root">

    const headMatch = indexHtml.match(/<head[^>]*>([\s\S]*?)<\/head>/i)
    expect(headMatch?.[1]).not.toContain('theme-bootstrap.js') // must NOT be in <head>
  })

  it('AC-1: theme-bootstrap.js script tag does not carry type="module" attribute', () => {
    const lines = indexHtml.split('\n')
    const bootstrapLine = lines.find((line) => line.includes('theme-bootstrap.js'))

    expect(bootstrapLine).toBeDefined()
    expect(bootstrapLine).not.toContain('type="module"')
  })

  it('AC-1p1: bootstrap script is the structural first element child of <body>', () => {
    const parser = new DOMParser()
    const doc = parser.parseFromString(indexHtml, 'text/html')
    const firstBodyChild = doc.body.firstElementChild

    expect(firstBodyChild).not.toBeNull()
    expect(firstBodyChild!.tagName.toLowerCase()).toBe('script')
    expect(firstBodyChild!.getAttribute('src')).toBe('/theme-bootstrap.js')
  })
})

// ─── AC-4: OS preference listener lifecycle ───────────────────────────────────

describe('TestFromAC_OsListenerBehavior_1545', () => {
  let mql: SpiedMQL

  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    mql = createSpiedMQL(false)
    installSpiedMQL(mql)
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  // Happy path — listener registration

  it('AC-4 happy: when theme=auto, addEventListener("change") is called on the matchMedia result', () => {
    const { unmount } = renderHook(() => useTheme())

    expect(mql.addEventListener).toHaveBeenCalledWith('change', expect.any(Function))

    unmount()
  })

  it('AC-4 happy: when theme=auto and OS changes to dark, data-theme becomes dark', async () => {
    const { unmount } = renderHook(() => useTheme())

    await act(async () => {
      mql.simulateChange(true)
    })

    expect(document.documentElement.dataset.theme).toBe('dark')

    unmount()
  })

  it('AC-4 happy: when theme=auto (OS dark initial) and OS changes to light, data-theme becomes light', async () => {
    mql = createSpiedMQL(true)
    installSpiedMQL(mql)

    const { unmount } = renderHook(() => useTheme())

    await act(async () => {
      mql.simulateChange(false)
    })

    expect(document.documentElement.dataset.theme).toBe('light')

    unmount()
  })

  it('AC-4 happy: when OS changes to dark while theme=auto, isDark becomes true', async () => {
    const { result, unmount } = renderHook(() => useTheme())

    expect(result.current.isDark).toBe(false)

    await act(async () => {
      mql.simulateChange(true)
    })

    expect(result.current.isDark).toBe(true)

    unmount()
  })

  // Edge cases — stable reference and cleanup

  it('AC-4 edge: addEventListener and removeEventListener target the same MediaQueryList instance (stable reference)', () => {
    const instances: SpiedMQL[] = []
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: (_query: string) => {
        const inst = createSpiedMQL(false)
        instances.push(inst)
        return inst
      },
    })

    const { unmount } = renderHook(() => useTheme())

    const addInstance = instances.find((i) => (i.addEventListener as ReturnType<typeof vi.fn>).mock.calls.length > 0)
    expect(addInstance).toBeDefined()

    unmount()

    expect(addInstance!.removeEventListener).toHaveBeenCalled()
  })

  it('AC-4 edge: when theme transitions from auto to dark, removeEventListener is called on the MQL instance', async () => {
    const { result, unmount } = renderHook(() => useTheme())

    await act(async () => {
      result.current.toggle() // auto → light
    })

    await act(async () => {
      result.current.toggle() // light → dark
    })

    await act(async () => {
      result.current.toggle() // dark → auto
    })

    // Listener must be registered now (theme=auto)
    expect(mql.addEventListener).toHaveBeenCalledWith('change', expect.any(Function))

    await act(async () => {
      result.current.toggle() // auto → light: listener must be removed
    })

    expect(mql.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))

    unmount()
  })

  it('AC-4 edge: when component unmounts with theme=auto, change listener is removed from MQL instance', () => {
    const { unmount } = renderHook(() => useTheme())

    unmount()

    expect(mql.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))
  })

  // Negative proof — no listener for explicit themes (AC-4p1)

  it('AC-4p1: when theme=dark (from localStorage), addEventListener is NOT called on the MQL spy', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')

    const { unmount } = renderHook(() => useTheme())

    expect(mql.addEventListener).not.toHaveBeenCalled()

    unmount()
  })

  it('AC-4p1: when theme=light (from localStorage), addEventListener is NOT called on the MQL spy', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    const { unmount } = renderHook(() => useTheme())

    expect(mql.addEventListener).not.toHaveBeenCalled()

    unmount()
  })

  // Bidirectional isDark (AC-4p2)

  it('AC-4p2: when theme=auto and OS changes from dark to light, isDark becomes false', async () => {
    mql = createSpiedMQL(true)
    installSpiedMQL(mql)

    const { result, unmount } = renderHook(() => useTheme())

    expect(result.current.isDark).toBe(true)

    await act(async () => {
      mql.simulateChange(false)
    })

    expect(result.current.isDark).toBe(false)

    unmount()
  })
})
