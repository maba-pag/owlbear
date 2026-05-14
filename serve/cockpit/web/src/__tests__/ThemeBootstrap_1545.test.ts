import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
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

  it('AC-1: theme-bootstrap.js script tag is located inside <head>', () => {
    const headMatch = indexHtml.match(/<head[^>]*>([\s\S]*?)<\/head>/i)

    expect(headMatch).not.toBeNull()
    expect(headMatch![1]).toContain('theme-bootstrap.js')
  })

  it('AC-1: theme-bootstrap.js script tag does not carry type="module" attribute', () => {
    const lines = indexHtml.split('\n')
    const bootstrapLine = lines.find((line) => line.includes('theme-bootstrap.js'))

    expect(bootstrapLine).toBeDefined()
    expect(bootstrapLine).not.toContain('type="module"')
  })
})
