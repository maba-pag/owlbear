/**
 * Tests for sidecar structure: padding, typography hierarchy, dividers
 * Task: #1607 — P1-11: Sidecar structure — padding, sections, typography
 *
 * AC-1: #shell-sidecar-content elements in Shell.tsx carry Tailwind class p-[var(--p-spacing-static-md)] on all four sides;
 *        present in both mobile (p-sheet) and desktop render paths
 * AC-2: Shell [data-region='sidecar-header'] contains p-heading[size='large'] (no raw h2);
 *        DetailTab [data-region='sidecar-body'] contains p-heading[size='medium'];
 *        DetailTab [data-region='actions'] contains p-heading[size='small']; DetailTab contains no raw h3
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
const SHELL_TSX_PATH = resolve(__dirname, '..', 'Shell.tsx')

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
// AC-1: #shell-sidecar-content Tailwind arbitrary-value padding class in Shell.tsx
// ---------------------------------------------------------------------------
describe('TestFromAC_SidecarStructure_Padding', () => {
  it('Shell.tsx source contains the Tailwind arbitrary-value padding class p-[var(--p-spacing-static-md)]', () => {
    const src = readFileSync(SHELL_TSX_PATH, 'utf8')
    expect(src).toContain('p-[var(--p-spacing-static-md)]')
  })

  it('Tailwind padding class appears at least twice in Shell.tsx — covering both mobile and desktop render paths', () => {
    const src = readFileSync(SHELL_TSX_PATH, 'utf8')
    const occurrences = (src.match(/p-\[var\(--p-spacing-static-md\)\]/g) ?? []).length
    expect(occurrences).toBeGreaterThanOrEqual(2)
  })

  it('desktop render path #shell-sidecar-content DOM element className includes the Tailwind padding class', () => {
    const { container } = renderShell()
    const el = container.querySelector('#shell-sidecar-content')
    expect(el).not.toBeNull()
    expect(el?.className).toContain('p-[var(--p-spacing-static-md)]')
  })

  it('Tailwind padding class uses PDS-native --p-spacing-static-md token (not deprecated --pds-* token)', () => {
    const src = readFileSync(SHELL_TSX_PATH, 'utf8')
    expect(src).toContain('p-[var(--p-spacing-static-md)]')
    expect(src).not.toMatch(/p-\[var\(--pds-spacing/)
  })

  it('Tailwind shorthand p-[...] covers all four sides — no directional overrides (pt-/pb-/pl-/pr-) that would negate a side', () => {
    const src = readFileSync(SHELL_TSX_PATH, 'utf8')
    expect(src).toContain('p-[var(--p-spacing-static-md)]')
    // Directional variants targeting the same token would conflict with the shorthand AC
    expect(src).not.toContain('pt-[var(--p-spacing-static-md)]')
    expect(src).not.toContain('pb-[var(--p-spacing-static-md)]')
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
