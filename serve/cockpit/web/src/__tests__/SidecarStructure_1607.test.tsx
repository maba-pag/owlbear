/**
 * Tests for sidecar structure: padding, typography hierarchy, dividers
 * Task: #1607 — P1-11: Sidecar structure — padding, sections, typography
 *
 * AC-1: #shell-sidecar-content has --p-spacing-static-md (≥16px) padding on all four sides
 * AC-2: Sidecar renders PHeading elements at 3 distinct size values (large, medium, small)
 * AC-3: PDivider separates: sidecar-header/DecisionViewport, DecisionViewport/p-tabs,
 *        and metadata/editor sections in DetailTab
 */
import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import DetailTab, { type TaskDetail } from '../components/DetailTab'

// ---------------------------------------------------------------------------
// File paths for CSS source tests
// ---------------------------------------------------------------------------
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const SHELL_CSS_PATH = resolve(__dirname, '..', 'Shell.css')

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------
vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

vi.mock('remark-gfm', () => ({ default: () => {} }))
vi.mock('rehype-sanitize', () => ({ default: () => {} }))

// PDS form-internals polyfill — required for PInputText / PSelect / PTextarea in jsdom
beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

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
  vi.resetAllMocks()
})

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------
const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'in-progress',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-05-01T10:00:00+00:00',
  created: '2026-04-01T09:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
  dep_status: null,
  claimed: false,
  claimed_at: null,
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

function renderDetailTab() {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={TASK} />
    </PorscheDesignSystemProvider>,
  )
}

// ---------------------------------------------------------------------------
// CSS source helpers — mirrors SidecarCollapse_1549.test.tsx pattern
// ---------------------------------------------------------------------------
function extractSelectorBlock(css: string, selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  // Negative lookahead: selector must not be extended by class/modifier chars or `[`
  const pattern = new RegExp(
    `(?:^|[\\n\\r])${escaped}(?![a-zA-Z0-9_\\-\\[])\\s*\\{([\\s\\S]*?)\\}`,
  )
  const match = css.match(pattern)
  expect(match, `Missing CSS selector block for: ${selector}`).not.toBeNull()
  return match?.[1] ?? ''
}

// ---------------------------------------------------------------------------
// AC-1: #shell-sidecar-content padding via CSS custom property
// ---------------------------------------------------------------------------
describe('TestFromAC_SidecarStructure_Padding', () => {
  it('Shell.css contains a #shell-sidecar-content selector', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf8')
    expect(css).toContain('#shell-sidecar-content')
  })

  it('#shell-sidecar-content block has a padding shorthand property (covers all 4 sides)', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf8')
    const block = extractSelectorBlock(css, '#shell-sidecar-content')
    expect(block).toMatch(/\bpadding\s*:/)
  })

  it('#shell-sidecar-content padding value references var(--p-spacing-static-md)', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf8')
    const block = extractSelectorBlock(css, '#shell-sidecar-content')
    expect(block).toContain('var(--p-spacing-static-md)')
  })

  it('padding token is a PDS native --p-* token, not a deprecated --pds-* custom token', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf8')
    const block = extractSelectorBlock(css, '#shell-sidecar-content')
    // --p-spacing-static-md is PDS native; --pds-* would be custom tokens from tokens.css (deleted by #1603)
    expect(block).toContain('var(--p-spacing-static-md)')
    expect(block).not.toMatch(/var\(--pds-spacing/)
  })

  it('#shell-sidecar-content has no directional padding-* overrides that zero out any side', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf8')
    const block = extractSelectorBlock(css, '#shell-sidecar-content')
    // Shorthand padding covers all 4 sides; individual overrides to 0 would break the AC
    expect(block).not.toMatch(/padding-(top|bottom|left|right)\s*:\s*0/)
  })
})

// ---------------------------------------------------------------------------
// AC-2: PHeading at 3 distinct size values (large, medium, small)
// ---------------------------------------------------------------------------
describe('TestFromAC_SidecarStructure_Typography', () => {
  it('sidecar-header section does not use a raw <h2> element (replaced by PHeading)', () => {
    const { container } = renderShell()
    const header = container.querySelector('[data-region="sidecar-header"]')
    expect(header?.querySelector('h2')).toBeNull()
  })

  it('sidecar-header contains a p-heading element for the task title', () => {
    const { container } = renderShell()
    const header = container.querySelector('[data-region="sidecar-header"]')
    expect(header?.querySelector('p-heading')).not.toBeNull()
  })

  it('sidecar-header p-heading has size="large"', () => {
    const { container } = renderShell()
    const header = container.querySelector('[data-region="sidecar-header"]')
    expect(header?.querySelector('p-heading[size="large"]')).not.toBeNull()
  })

  it('DetailTab with task renders at least one p-heading element', () => {
    const { container } = renderDetailTab()
    expect(container.querySelector('p-heading')).not.toBeNull()
  })

  it('DetailTab with task renders p-heading[size="medium"] for a primary section', () => {
    const { container } = renderDetailTab()
    expect(container.querySelector('p-heading[size="medium"]')).not.toBeNull()
  })

  it('DetailTab with task renders p-heading[size="small"] for a secondary section', () => {
    const { container } = renderDetailTab()
    expect(container.querySelector('p-heading[size="small"]')).not.toBeNull()
  })

  it('DetailTab does not use raw <h3> elements (replaced by PHeading)', () => {
    const { container } = renderDetailTab()
    expect(container.querySelector('h3')).toBeNull()
  })

  it('all 3 distinct PHeading sizes are present across sidecar components (large, medium, small)', () => {
    const { container: shellContainer } = renderShell()
    const { container: detailContainer } = renderDetailTab()
    const shellSizes = new Set(
      Array.from(shellContainer.querySelectorAll('p-heading'))
        .map(el => el.getAttribute('size'))
        .filter(Boolean),
    )
    const detailSizes = new Set(
      Array.from(detailContainer.querySelectorAll('p-heading'))
        .map(el => el.getAttribute('size'))
        .filter(Boolean),
    )
    const allSizes = new Set([...shellSizes, ...detailSizes])
    expect(allSizes.has('large')).toBe(true)
    expect(allSizes.has('medium')).toBe(true)
    expect(allSizes.has('small')).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// AC-3: PDivider between sidecar content blocks
// ---------------------------------------------------------------------------
describe('TestFromAC_SidecarStructure_Dividers', () => {
  it('#shell-sidecar-content contains at least one p-divider element', () => {
    const { container } = renderShell()
    const content = container.querySelector('#shell-sidecar-content')
    expect(content?.querySelector('p-divider')).not.toBeNull()
  })

  it('p-divider is placed as the direct next sibling after sidecar-header (between header and DecisionViewport)', () => {
    const { container } = renderShell()
    const content = container.querySelector('#shell-sidecar-content') as HTMLElement
    const children = Array.from(content.children)
    const headerIdx = children.findIndex(
      el => el.getAttribute('data-region') === 'sidecar-header',
    )
    expect(headerIdx).toBeGreaterThanOrEqual(0)
    const nextSibling = children[headerIdx + 1]
    expect(nextSibling?.tagName.toLowerCase()).toBe('p-divider')
  })

  it('p-divider is placed immediately before p-tabs (between DecisionViewport and tabs)', () => {
    const { container } = renderShell()
    const content = container.querySelector('#shell-sidecar-content') as HTMLElement
    const children = Array.from(content.children)
    const tabsIdx = children.findIndex(el => el.tagName.toLowerCase() === 'p-tabs')
    expect(tabsIdx).toBeGreaterThanOrEqual(0)
    const prevSibling = children[tabsIdx - 1]
    expect(prevSibling?.tagName.toLowerCase()).toBe('p-divider')
  })

  it('at least two p-divider elements exist in #shell-sidecar-content (one per AC-3 position)', () => {
    const { container } = renderShell()
    const content = container.querySelector('#shell-sidecar-content') as HTMLElement
    const dividers = Array.from(content.children).filter(
      el => el.tagName.toLowerCase() === 'p-divider',
    )
    expect(dividers.length).toBeGreaterThanOrEqual(2)
  })

  it('DetailTab contains a p-divider between sidecar-metadata and sidecar-body sections', () => {
    const { container } = renderDetailTab()
    const metadata = container.querySelector('[data-region="sidecar-metadata"]')
    expect(metadata).not.toBeNull()
    const parent = metadata?.parentElement
    const siblings = parent ? Array.from(parent.children) : []
    const metaIdx = siblings.findIndex(
      el => el.getAttribute('data-region') === 'sidecar-metadata',
    )
    expect(metaIdx).toBeGreaterThanOrEqual(0)
    const afterMetadata = siblings.slice(metaIdx + 1)
    expect(afterMetadata.some(el => el.tagName.toLowerCase() === 'p-divider')).toBe(true)
  })

  it('the element immediately after sidecar-metadata is a p-divider (no interleaved content)', () => {
    const { container } = renderDetailTab()
    const metadata = container.querySelector('[data-region="sidecar-metadata"]')
    expect(metadata).not.toBeNull()
    const parent = metadata?.parentElement
    const siblings = parent ? Array.from(parent.children) : []
    const metaIdx = siblings.findIndex(
      el => el.getAttribute('data-region') === 'sidecar-metadata',
    )
    expect(metaIdx).toBeGreaterThanOrEqual(0)
    const nextSibling = siblings[metaIdx + 1]
    expect(nextSibling?.tagName.toLowerCase()).toBe('p-divider')
  })
})
