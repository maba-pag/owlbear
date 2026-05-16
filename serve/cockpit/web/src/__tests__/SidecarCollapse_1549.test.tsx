import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

// ---------------------------------------------------------------------------
// Test setup — mirrors SidecarCollapse_1541.test.tsx
// ---------------------------------------------------------------------------

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn((_url: string, init?: RequestInit) =>
      new Promise<never>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      }),
    ),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// ---------------------------------------------------------------------------
// CSS source-contract helpers
// ---------------------------------------------------------------------------

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const SHELL_CSS_PATH = resolve(__dirname, '..', 'Shell.css')

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Extract the content inside a CSS selector block.
 * Uses a negative lookahead to avoid partial-class matches:
 * e.g. looking for ".shell" will NOT match ".shell__sidecar".
 */
function extractSelectorBlock(css: string, selector: string): string {
  const escaped = escapeRegExp(selector)
  // Negative lookahead: ensure the selector is not extended by class/modifier chars or `[`
  const pattern = new RegExp(
    `(?:^|[\\n\\r])${escaped}(?![a-zA-Z0-9_\\-\\[])\\s*\\{([\\s\\S]*?)\\}`,
  )
  const match = css.match(pattern)
  expect(match, `Missing CSS selector block for: ${selector}`).not.toBeNull()
  return match?.[1] ?? ''
}

/**
 * Extract the full body of a balanced @-rule block (handles nested braces).
 */
function extractAtRuleBody(css: string, atRulePrefix: string): string {
  const startIndex = css.indexOf(atRulePrefix)
  expect(startIndex, `Missing at-rule: ${atRulePrefix}`).toBeGreaterThanOrEqual(0)

  const openBraceIndex = css.indexOf('{', startIndex)
  expect(openBraceIndex, `Missing opening brace for: ${atRulePrefix}`).toBeGreaterThanOrEqual(0)

  let depth = 0
  for (let index = openBraceIndex; index < css.length; index++) {
    const char = css[index]
    if (char === '{') {
      depth += 1
    } else if (char === '}') {
      depth -= 1
      if (depth === 0) {
        return css.slice(openBraceIndex + 1, index)
      }
    }
  }
  throw new Error(`Unclosed at-rule block: ${atRulePrefix}`)
}

// ---------------------------------------------------------------------------
// Render helpers
// ---------------------------------------------------------------------------

function renderShell() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

function getCollapseToggle(container: HTMLElement): HTMLElement {
  const toggle = container.querySelector('[data-testid="sidecar-collapse"]')
  if (!toggle) throw new Error('sidecar-collapse toggle not found')
  return toggle as HTMLElement
}

function getShellContainer(container: HTMLElement): HTMLElement {
  const shell = container.querySelector('.shell')
  if (!shell) throw new Error('.shell container not found')
  return shell as HTMLElement
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TestFromAC_SidecarCollapse_1549', () => {
  // AC-1: Shell.tsx sets data-sidecar-collapsed on .shell when isSidecarCollapsed is true;
  //       attribute is absent when the sidecar is expanded.

  it('AC-1 happy: clicking collapse toggle sets data-sidecar-collapsed on the .shell grid container', () => {
    const { container } = renderShell()
    const toggle = getCollapseToggle(container)
    const shell = getShellContainer(container)

    fireEvent.click(toggle)

    expect(
      shell.hasAttribute('data-sidecar-collapsed'),
      'Expected .shell to have data-sidecar-collapsed attribute after collapse click',
    ).toBe(true)
  })

  it('AC-1 round-trip: collapse then expand removes data-sidecar-collapsed from .shell', () => {
    const { container } = renderShell()
    const toggle = getCollapseToggle(container)
    const shell = getShellContainer(container)

    // collapse — attribute must appear
    fireEvent.click(toggle)
    expect(
      shell.hasAttribute('data-sidecar-collapsed'),
      'Expected .shell to have data-sidecar-collapsed after first (collapse) click',
    ).toBe(true)

    // expand — attribute must be removed
    fireEvent.click(toggle)
    expect(
      shell.hasAttribute('data-sidecar-collapsed'),
      'Expected data-sidecar-collapsed to be absent after second (expand) click',
    ).toBe(false)
  })

  // AC-2: Shell.css transition + collapsed grid-template-columns (desktop + tablet)

  it('AC-2 transition: Shell.css .shell rule declares transition: grid-template-columns var(--p-duration-sm) var(--p-ease-in-out)', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const shellBlock = extractSelectorBlock(css, '.shell')
    expect(
      /transition\s*:\s*grid-template-columns\s+var\(--p-duration-sm\)\s+var\(--p-ease-in-out\)/.test(shellBlock),
      'Expected .shell block to contain "transition: grid-template-columns var(--p-duration-sm) var(--p-ease-in-out)"',
    ).toBe(true)
  })

  it('AC-2 desktop collapsed: Shell.css .shell[data-sidecar-collapsed] sets grid-template-columns to 56px 1fr 0fr', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const collapsedBlock = extractSelectorBlock(css, '.shell[data-sidecar-collapsed]')
    expect(
      /grid-template-columns\s*:\s*56px\s+1fr\s+0fr/.test(collapsedBlock),
      'Expected .shell[data-sidecar-collapsed] to set grid-template-columns: 56px 1fr 0fr',
    ).toBe(true)
  })

  it('AC-2 tablet collapsed: tablet @media block .shell[data-sidecar-collapsed] sets grid-template-columns to 56px minmax(0, 1fr) 0fr', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const tabletBody = extractAtRuleBody(
      css,
      '@media (min-width: 768px) and (max-width: 1023px)',
    )
    const collapsedBlock = extractSelectorBlock(tabletBody, '.shell[data-sidecar-collapsed]')
    expect(
      /grid-template-columns\s*:\s*56px\s+minmax\(0,\s*1fr\)\s+0fr/.test(collapsedBlock),
      'Expected tablet @media .shell[data-sidecar-collapsed] to set grid-template-columns: 56px minmax(0, 1fr) 0fr',
    ).toBe(true)
  })

  // AC-3: Shell.css overflow: hidden on .shell__sidecar

  it('AC-3 overflow: Shell.css .shell__sidecar has overflow: hidden', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const sidecarBlock = extractSelectorBlock(css, '.shell__sidecar')
    expect(
      /overflow\s*:\s*hidden/.test(sidecarBlock),
      'Expected .shell__sidecar block to declare overflow: hidden — prevents content spill during grid column transition',
    ).toBe(true)
  })
})
