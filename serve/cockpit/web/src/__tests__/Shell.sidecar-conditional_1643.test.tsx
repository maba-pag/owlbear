/**
 * Task #1643 — P1-03: Route-conditional sidecar
 * Tests sidecar conditional rendering, navigation state, and grid column adjustment
 * based on the routeConfig entry's `hasSidecar` field.
 *
 * Real routeConfig (routes.ts) is intentionally NOT mocked — these are integration
 * tests that lock in the wiring between /decisions and hasSidecar:false suppression.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { MemoryRouter, useNavigate } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const SHELL_CSS_PATH = resolve(__dirname, '..', 'Shell.css')

/** Extract the property declarations inside the first matching CSS selector block. */
function extractSelectorBlock(css: string, selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(
    `(?:^|[\\n\\r])${escaped}(?![a-zA-Z0-9_\\-\\[])\\s*\\{([\\s\\S]*?)\\}`,
  )
  const match = css.match(pattern)
  expect(match, `Missing CSS selector block for: ${selector}`).not.toBeNull()
  return match?.[1] ?? ''
}

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// Never-resolving fetch keeps board/scan/DR hooks in loading state, preventing
// React state updates after assertions and eliminating act() warnings.
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

/** Navigation helper rendered inside the same MemoryRouter as Shell. */
function NavHelper({ testId, to }: { testId: string; to: string }) {
  const navigate = useNavigate()
  return <button data-testid={testId} onClick={() => navigate(to)} />
}

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

/** Renders Shell with navigation helpers inside the same MemoryRouter context. */
function renderShellWithNav(startRoute = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[startRoute]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
        <NavHelper testId="go-decisions" to="/decisions" />
        <NavHelper testId="go-home" to="/" />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

describe('TestFromAC_SidecarConditional', () => {
  // ── AC1: sidecar absent from DOM on /decisions ────────────────────────────

  it('ac1 happy: [data-region="sidecar"] absent from DOM on /decisions route', () => {
    const { container } = renderShell('/decisions')
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
  })

  // ── AC2: navigation removes and restores sidecar ──────────────────────────

  it('ac2 happy remove: navigating from / to /decisions removes sidecar from DOM', () => {
    const { container } = renderShellWithNav('/')
    // Sidecar present at /
    expect(container.querySelector('[data-region="sidecar"]')).not.toBeNull()
    // Navigate to /decisions
    fireEvent.click(container.querySelector('[data-testid="go-decisions"]')!)
    // Sidecar must be absent after navigation
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
  })

  it('ac2 happy restore: navigating from /decisions back to / restores sidecar in DOM', () => {
    const { container } = renderShellWithNav('/decisions')
    // Start at /decisions — sidecar absent
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
    // Navigate back to /
    fireEvent.click(container.querySelector('[data-testid="go-home"]')!)
    // Sidecar must be restored
    expect(container.querySelector('[data-region="sidecar"]')).not.toBeNull()
  })

  it('ac2 edge preserve-collapsed: isSidecarCollapsed state persists through / → /decisions → / round-trip', () => {
    const { container } = renderShellWithNav('/')
    // Collapse the sidecar at /
    const toggle = container.querySelector('[data-testid="sidecar-collapse"]') as HTMLButtonElement
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    // Navigate to /decisions — sidecar removed from DOM
    fireEvent.click(container.querySelector('[data-testid="go-decisions"]')!)
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
    // Navigate back to / — sidecar restored in its previous collapsed state
    fireEvent.click(container.querySelector('[data-testid="go-home"]')!)
    const restoredToggle = container.querySelector('[data-testid="sidecar-collapse"]') as HTMLButtonElement
    expect(restoredToggle.getAttribute('aria-expanded')).toBe('false')
  })

  // ── AC3: shell grid narrows to 2 columns when sidecar is absent ───────────

  it('ac3 happy: shell element carries data-no-sidecar attribute on /decisions route', () => {
    const { container } = renderShell('/decisions')
    const shell = container.querySelector('.shell')
    expect(shell).not.toBeNull()
    // data-no-sidecar drives the CSS --shell-columns override to 2-column layout
    expect(shell!.hasAttribute('data-no-sidecar')).toBe(true)
  })

  // ── AC3 CSS regression: .shell[data-no-sidecar] grid contract in Shell.css ──

  it('ac3 css-columns: .shell[data-no-sidecar] sets --shell-columns to 2-column value (rail + workspace, no sidecar column)', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.shell[data-no-sidecar]')
    expect(
      /--shell-columns\s*:\s*var\(--shell-rail-width\)\s+minmax\(0,\s*1fr\)/.test(block),
      'Expected .shell[data-no-sidecar] to set --shell-columns to "var(--shell-rail-width) minmax(0, 1fr)" — removing the block or changing to 3 columns would regress the layout',
    ).toBe(true)
  })

  it('ac3 css-no-sidecar-area: .shell[data-no-sidecar] grid-template-areas excludes sidecar region', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.shell[data-no-sidecar]')
    expect(
      /sidecar/.test(block),
      'Expected .shell[data-no-sidecar] grid-template-areas to not include a sidecar grid area',
    ).toBe(false)
  })

})
