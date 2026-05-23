/**
 * Task #1671 — P3-01: Memory list view with state/category/agent filters and text search
 *
 * Covers AC1–AC6: route registration, fetch on mount + visibilitychange, sort order,
 * filter controls and defaults, intersection semantics, row rendering, empty states,
 * parse-errors warning.
 *
 * RED phase: pages/MemoryTab.tsx does not exist yet → import fails.
 * routeConfig has no /memories entry yet → route assertions fail.
 * All tests fail at import or assertion level.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, act } from '@testing-library/react'
import { routeConfig } from '../routes'
import MemoryTab from '../pages/MemoryTab'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

interface MemoryEntryFixture {
  id: string
  title: string
  content: string
  categories: string[]
  confidence: number
  state: 'pending' | 'curated' | 'approved' | 'deleted'
  scope_agents: string[]
  source_agent: string
  created_at: string
  updated_at: string
  approved_at: string | null
}

function makeEntry(overrides: Partial<MemoryEntryFixture> = {}): MemoryEntryFixture {
  return {
    id: 'entry-1',
    title: 'Test Memory',
    content: 'Some content',
    categories: ['behaviour'],
    confidence: 0.85,
    state: 'pending',
    scope_agents: ['builder'],
    source_agent: 'test-agent',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    approved_at: null,
    ...overrides,
  }
}

function makeApiResponse(entries: MemoryEntryFixture[], parse_errors = 0) {
  return { entries, parse_errors }
}

function makeOkFetch(body: unknown = makeApiResponse([])) {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    }),
  )
}

function makePendingFetch() {
  return vi.fn(() => new Promise<never>(() => {}))
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderMemoryTab() {
  return render(<MemoryTab />)
}

// ─── Utilities ────────────────────────────────────────────────────────────────

async function flush() {
  await act(async () => {
    await Promise.resolve()
  })
}

function readHostValue(element: Element | null): unknown {
  return (element as (Element & { value?: unknown }) | null)?.value ?? element?.getAttribute('value')
}

function readHostStringArray(element: Element | null): string[] {
  const value = readHostValue(element)
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function readPdsVariant(element: Element | null): string | undefined {
  return (element as (Element & { variant?: string }) | null)?.variant ?? element?.getAttribute('variant') ?? undefined
}

function readMetricTexts(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll('[data-testid="workspace-header-metric"]')).map(
    (el) => el.textContent?.replace(/\s+/g, '') ?? '',
  )
}

// ─── AC1: Route registration ──────────────────────────────────────────────────

describe('TestFromAC_MemoryTabRoute', () => {
  it('ac1 happy: routeConfig contains an entry with path "/memories"', () => {
    const paths = routeConfig.map((e) => e.path)
    expect(paths).toContain('/memories')
  })

  it('ac1 happy: /memories route entry has no retired sidecar configuration', () => {
    const entry = routeConfig.find((e) => e.path === '/memories')
    expect(entry).not.toBeUndefined()
    expect('hasSidecar' in (entry ?? {})).toBe(false)
  })

  it('ac1 happy: /memories route entry has label "Memory"', () => {
    const entry = routeConfig.find((e) => e.path === '/memories')
    expect(entry?.label).toBe('Memory')
  })

  it('ac1 happy: /memories route component is a React.lazy wrapper', () => {
    const entry = routeConfig.find((e) => e.path === '/memories')
    // React.lazy() objects carry $$typeof === Symbol.for('react.lazy')
    expect((entry?.component as { $$typeof?: symbol })?.$$typeof).toBe(Symbol.for('react.lazy'))
  })

  it('ac1 happy: /memories route entry has an icon field', () => {
    const entry = routeConfig.find((e) => e.path === '/memories')
    expect(typeof entry?.icon).toBe('string')
    expect((entry?.icon as string).length).toBeGreaterThan(0)
  })
})

// ─── AC1: Fetch on mount + loading indicator ──────────────────────────────────

describe('TestFromAC_MemoryTabMount', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 happy: fetches GET /api/memories on mount', async () => {
    const fetchMock = makeOkFetch()
    vi.stubGlobal('fetch', fetchMock)
    await act(async () => {
      renderMemoryTab()
    })
    await flush()
    expect(fetchMock).toHaveBeenCalledWith('/api/memories', expect.anything())
  })

  it('ac1 happy: shows data-testid="memory-loading" while fetch is in-flight', async () => {
    vi.stubGlobal('fetch', makePendingFetch())
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    expect(container.querySelector('[data-testid="memory-loading"]')).not.toBeNull()
  })

  it('ac1 edge: loading indicator is absent after fetch resolves', async () => {
    vi.stubGlobal('fetch', makeOkFetch())
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()
    expect(container.querySelector('[data-testid="memory-loading"]')).toBeNull()
  })

  it('ac1 happy: refetches /api/memories when document visibilitychange fires with visibilityState=visible', async () => {
    const fetchMock = makeOkFetch()
    vi.stubGlobal('fetch', fetchMock)
    await act(async () => {
      renderMemoryTab()
    })
    await flush()
    const callsAfterMount = fetchMock.mock.calls.length

    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' })
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await flush()

    expect(fetchMock.mock.calls.length).toBeGreaterThan(callsAfterMount)
  })

  it('ac1 edge: does NOT refetch on visibilitychange when document is hidden', async () => {
    const fetchMock = makeOkFetch()
    vi.stubGlobal('fetch', fetchMock)
    await act(async () => {
      renderMemoryTab()
    })
    await flush()
    const callsAfterMount = fetchMock.mock.calls.length

    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' })
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await flush()

    expect(fetchMock.mock.calls.length).toBe(callsAfterMount)
  })
})

// ─── AC1: Sort order ─────────────────────────────────────────────────────────

describe('TestFromAC_MemoryTabSort', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 happy: higher-confidence entries appear first regardless of state', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Lower Confidence Pending', state: 'pending', confidence: 0.45 }),
      makeEntry({ id: 'e2', title: 'Higher Confidence Approved', state: 'approved', confidence: 0.95 }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles.indexOf('Higher Confidence Approved')).toBeLessThan(titles.indexOf('Lower Confidence Pending'))
  })

  it('ac1 happy: when confidence ties, pending entries appear before curated entries regardless of created_at', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Curated Entry', state: 'curated', created_at: '2026-01-01T00:00:00Z' }),
      makeEntry({ id: 'e2', title: 'Pending Entry', state: 'pending', created_at: '2026-01-02T00:00:00Z' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles.indexOf('Pending Entry')).toBeLessThan(titles.indexOf('Curated Entry'))
  })

  it('ac1 happy: when confidence and state tie, entries sorted by created_at ascending', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Later Pending', state: 'pending', created_at: '2026-01-02T00:00:00Z' }),
      makeEntry({ id: 'e2', title: 'Earlier Pending', state: 'pending', created_at: '2026-01-01T00:00:00Z' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles.indexOf('Earlier Pending')).toBeLessThan(titles.indexOf('Later Pending'))
  })

  it('ac1 edge: malformed confidence sorts after finite confidence and id breaks complete ties', async () => {
    const entries = [
      makeEntry({ id: 'z', title: 'Malformed Confidence Z', confidence: Number.NaN, state: 'pending' }),
      makeEntry({ id: 'b', title: 'Finite Confidence', confidence: 0.1, state: 'pending' }),
      makeEntry({ id: 'a', title: 'Malformed Confidence A', confidence: Number.NaN, state: 'pending' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toEqual(['Finite Confidence', 'Malformed Confidence A', 'Malformed Confidence Z'])
  })

  it('ac1 boundary: full state priority order is pending < curated < approved < deleted', async () => {
    const entries = [
      makeEntry({ id: 'e4', title: 'Deleted', state: 'deleted', created_at: '2026-01-01T00:00:00Z' }),
      makeEntry({ id: 'e3', title: 'Approved', state: 'approved', created_at: '2026-01-01T00:00:00Z' }),
      makeEntry({ id: 'e2', title: 'Curated', state: 'curated', created_at: '2026-01-01T00:00:00Z' }),
      makeEntry({ id: 'e1', title: 'Pending', state: 'pending', created_at: '2026-01-01T00:00:00Z' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    // Clear state filter so deleted entries are visible too
    const stateFilter = container.querySelector('[name="state-filter"]')
    fireEvent(stateFilter!, new CustomEvent('update', { detail: { value: [] }, bubbles: true }))
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toEqual(['Pending', 'Curated', 'Approved', 'Deleted'])
  })
})

// ─── AC2: Filter controls and defaults ───────────────────────────────────────

describe('TestFromAC_MemoryTabFilters', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac2 happy: renders a state filter control (p-multi-select or similar with name="state-filter")', async () => {
    vi.stubGlobal('fetch', makeOkFetch())
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()
    expect(container.querySelector('[name="state-filter"]')).not.toBeNull()
  })

  it('ac2 happy: default state filter shows pending, curated, and approved entries', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Pending Entry', state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Curated Entry', state: 'curated' }),
      makeEntry({ id: 'e3', title: 'Approved Entry', state: 'approved' }),
      makeEntry({ id: 'e4', title: 'Deleted Entry', state: 'deleted' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Pending Entry')
    expect(titles).toContain('Curated Entry')
    expect(titles).toContain('Approved Entry')
  })

  it('ac2 happy: default state filter hides deleted entries', async () => {
    const entries = [makeEntry({ id: 'e1', title: 'Deleted Entry', state: 'deleted' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).not.toContain('Deleted Entry')
  })

  it('ac2 regression: PDS change event on state filter controls visible states and shown count', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Pending Entry', state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Curated Entry', state: 'curated' }),
      makeEntry({ id: 'e3', title: 'Approved Entry', state: 'approved' }),
      makeEntry({ id: 'e4', title: 'Deleted Entry', state: 'deleted' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const stateFilter = container.querySelector('[name="state-filter"]')
    fireEvent(stateFilter!, new CustomEvent('change', { detail: { value: ['deleted'] }, bubbles: true }))
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toEqual(['Deleted Entry'])

    expect(readMetricTexts(container)).toEqual(['1of4shown'])
  })

  it('ac2 polish: summary reads visible of total when default state filter hides deleted entries', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Pending Entry', state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Curated Entry', state: 'curated' }),
      makeEntry({ id: 'e3', title: 'Approved Entry', state: 'approved' }),
      makeEntry({ id: 'e4', title: 'Deleted Entry', state: 'deleted' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    expect(readMetricTexts(container)).toEqual(['3of4shown'])
  })

  it('ac2 polish: summary collapses to total count when every entry is visible', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Pending Entry', state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Curated Entry', state: 'curated' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    expect(readMetricTexts(container)).toEqual(['2entries'])
  })

  it('ac2 polish: parse errors remain visible alongside the compact count', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Pending Entry', state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Deleted Entry', state: 'deleted' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries, 2)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    expect(readMetricTexts(container)).toEqual(['1of2shown'])
    expect(container.querySelector('[data-testid="workspace-header-summary"]')?.textContent).toContain('2 unreadable')
  })

  it('ac2 happy: category filter is populated from distinct categories across all entries', async () => {
    const entries = [
      makeEntry({ id: 'e1', categories: ['behaviour', 'pitfall'], state: 'pending' }),
      makeEntry({ id: 'e2', categories: ['behaviour', 'process'], state: 'pending' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const categoryFilter = container.querySelector('[name="category-filter"]')
    expect(categoryFilter).not.toBeNull()
    const options = categoryFilter!.querySelectorAll('p-multi-select-option')
    const values = Array.from(options).map((el) => readHostValue(el))
    expect(values).toContain('behaviour')
    expect(values).toContain('pitfall')
    expect(values).toContain('process')
    // No duplicate values
    expect(new Set(values).size).toBe(values.length)
  })

  it('ac2 happy: agent filter (PSelect) is populated from distinct scope_agents values', async () => {
    const entries = [
      makeEntry({ id: 'e1', scope_agents: ['builder', 'reviewer'], state: 'pending' }),
      makeEntry({ id: 'e2', scope_agents: ['builder'], state: 'pending' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const agentFilter = container.querySelector('[name="agent-filter"]')
    expect(agentFilter).not.toBeNull()
    const options = agentFilter!.querySelectorAll('p-select-option')
    const values = Array.from(options)
      .map((el) => readHostValue(el))
      .filter(Boolean)
    expect(values).toContain('builder')
    expect(values).toContain('reviewer')
    expect(new Set(values).size).toBe(values.length)
  })

  it('ac2 edge: agent wildcard is omitted from filter options', async () => {
    const entries = [
      makeEntry({ id: 'e1', scope_agents: ['*'], state: 'pending' }),
      makeEntry({ id: 'e2', scope_agents: ['builder'], state: 'pending' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const agentFilter = container.querySelector('[name="agent-filter"]')
    expect(agentFilter).not.toBeNull()
    const values = Array.from(agentFilter!.querySelectorAll('p-select-option')).map((el) => readHostValue(el))
    expect(values).not.toContain('*')
    expect(values).toContain('builder')
  })

  it('ac2 happy: text search control (PInputSearch) is present', async () => {
    vi.stubGlobal('fetch', makeOkFetch())
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()
    expect(container.querySelector('p-input-search')).not.toBeNull()
  })

  it('ac2 edge: entry with empty scope_agents always passes the agent filter regardless of selected agent', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Global Entry', scope_agents: [], state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Builder Only', scope_agents: ['builder'], state: 'pending' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    // Set agent filter to 'reviewer' — no entry specifically targets reviewer
    const agentFilter = container.querySelector('[name="agent-filter"]')
    fireEvent(agentFilter!, new CustomEvent('update', { detail: { value: 'reviewer' }, bubbles: true }))
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Global Entry')
    expect(titles).not.toContain('Builder Only')
  })

  it('ac2 edge: entry with wildcard scope_agents always passes the agent filter', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Wildcard Entry', scope_agents: ['*'], state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Builder Only', scope_agents: ['builder'], state: 'pending' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const agentFilter = container.querySelector('[name="agent-filter"]')
    fireEvent(agentFilter!, new CustomEvent('update', { detail: { value: 'reviewer' }, bubbles: true }))
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Wildcard Entry')
    expect(titles).not.toContain('Builder Only')
  })
})

// ─── AC3: Filter intersection semantics ──────────────────────────────────────

describe('TestFromAC_MemoryTabFilterIntersection', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac3 happy: entry must satisfy ALL active filters (intersection — not union)', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Full Match', state: 'pending', categories: ['behaviour'], scope_agents: ['builder'] }),
      makeEntry({ id: 'e2', title: 'Wrong State', state: 'curated', categories: ['behaviour'], scope_agents: ['builder'] }),
      makeEntry({ id: 'e3', title: 'Wrong Category', state: 'pending', categories: ['pitfall'], scope_agents: ['builder'] }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    // Narrow state to pending only
    const stateFilter = container.querySelector('[name="state-filter"]')
    fireEvent(stateFilter!, new CustomEvent('update', { detail: { value: ['pending'] }, bubbles: true }))

    // Narrow category to behaviour only
    const categoryFilter = container.querySelector('[name="category-filter"]')
    fireEvent(categoryFilter!, new CustomEvent('update', { detail: { value: ['behaviour'] }, bubbles: true }))

    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Full Match')
    expect(titles).not.toContain('Wrong State')
    expect(titles).not.toContain('Wrong Category')
  })

  it('ac3 happy: selecting no options in state multi-select makes that filter inactive (shows all states)', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Pending', state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Deleted', state: 'deleted' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    // Clear state filter → inactive → all states visible
    const stateFilter = container.querySelector('[name="state-filter"]')
    fireEvent(stateFilter!, new CustomEvent('update', { detail: { value: [] }, bubbles: true }))
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Pending')
    expect(titles).toContain('Deleted')
  })

  it('ac3 edge: empty category filter (no options) means filter is inactive — all categories pass', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Behaviour Entry', categories: ['behaviour'], state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Pitfall Entry', categories: ['pitfall'], state: 'pending' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    // Default: category filter starts empty (inactive) — both entries visible
    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Behaviour Entry')
    expect(titles).toContain('Pitfall Entry')
  })

  it('ac3 happy: text search filters by title substring case-insensitively', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Alpha Entry', content: 'unrelated', state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Beta Entry', content: 'unrelated', state: 'pending' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const searchEl = container.querySelector('p-input-search')!
    fireEvent(searchEl, new CustomEvent('input', { detail: { value: 'ALPHA' }, bubbles: true }))
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Alpha Entry')
    expect(titles).not.toContain('Beta Entry')
  })

  it('ac3 happy: text search also matches entry content case-insensitively', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'No Match Title', content: 'alpha found here', state: 'pending' }),
      makeEntry({ id: 'e2', title: 'Beta Title', content: 'unrelated content', state: 'pending' }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const searchEl = container.querySelector('p-input-search')!
    fireEvent(searchEl, new CustomEvent('input', { detail: { value: 'ALPHA' }, bubbles: true }))
    await flush()

    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('No Match Title')
    expect(titles).not.toContain('Beta Title')
  })
})

// ─── AC4: Entry row rendering ─────────────────────────────────────────────────

describe('TestFromAC_MemoryTabRowRendering', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac4 happy: entry row renders title as primary text', async () => {
    const entries = [makeEntry({ title: 'My Specific Memory Title', state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const titleEl = container.querySelector('[data-testid="memory-entry-title"]')
    expect(titleEl?.textContent).toContain('My Specific Memory Title')
  })

  it('ac4 happy: entry row renders one p-tag per category', async () => {
    const entries = [makeEntry({ categories: ['behaviour', 'pitfall', 'process'], state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const row = container.querySelector('[data-testid="memory-entry"]')
    const categoryTags = row?.querySelectorAll('[data-testid="memory-entry-category"]')
    expect(categoryTags?.length).toBe(3)
  })

  it('ac4 happy: entry row renders confidence as decimal string (e.g. "0.85")', async () => {
    const entries = [makeEntry({ confidence: 0.85, state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const confidenceEl = container.querySelector('[data-testid="memory-entry-confidence"]')
    expect(confidenceEl?.textContent).toContain('0.85')
  })

  it('ac4 polish: row separates content categories from confidence and state signals', async () => {
    const entries = [makeEntry({ categories: ['behaviour', 'pitfall'], confidence: 0.91, state: 'curated' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const row = container.querySelector('[data-testid="memory-entry"]')
    const categoryGroup = row?.querySelector('[data-testid="memory-entry-category-group"]')
    const signalGroup = row?.querySelector('[data-testid="memory-entry-signal-group"]')
    const categories = Array.from(row?.querySelectorAll('[data-testid="memory-entry-category"]') ?? [])
    const confidenceEl = row?.querySelector('[data-testid="memory-entry-confidence"]')
    const stateEl = row?.querySelector('[data-testid="memory-entry-state"]')

    expect(categoryGroup).not.toBeNull()
    expect(signalGroup).not.toBeNull()
    expect(categories).toHaveLength(2)
    expect(categories.every((category) => categoryGroup?.contains(category))).toBe(true)
    expect(signalGroup?.contains(confidenceEl)).toBe(true)
    expect(signalGroup?.contains(stateEl)).toBe(true)
    expect(categoryGroup?.contains(confidenceEl)).toBe(false)
    expect(categoryGroup?.contains(stateEl)).toBe(false)
    expect(signalGroup?.className).toContain('lg:border-l')
    expect(confidenceEl?.textContent).toContain('Confidence')
  })

  it('ac4 polish: entry list is a vertical-only scroll surface with a cue shell', async () => {
    const entries = [makeEntry({ title: 'Scrollable Memory', state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const shell = container.querySelector('[data-testid="memory-list-scroll-shell"]')
    const list = shell?.querySelector('ul')

    expect(shell?.className).toContain('overflow-hidden')
    expect(list?.className).toContain('overflow-x-hidden')
    expect(list?.className).toContain('overflow-y-auto')
    expect(list?.className).toContain('pb-static-lg')
  })

  it('ac4 happy: pending state badge uses info color variant', async () => {
    const entries = [makeEntry({ state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const badge = container.querySelector('[data-testid="memory-entry-state"]')
    expect(badge).not.toBeNull()
    expect(readPdsVariant(badge)).toBe('info')
  })

  it('ac4 happy: curated state badge uses secondary color variant', async () => {
    const entries = [makeEntry({ state: 'curated' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const badge = container.querySelector('[data-testid="memory-entry-state"]')
    expect(badge).not.toBeNull()
    expect(readPdsVariant(badge)).toBe('secondary')
  })

  it('ac4 happy: approved state badge uses success color variant', async () => {
    const entries = [makeEntry({ state: 'approved' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const badge = container.querySelector('[data-testid="memory-entry-state"]')
    expect(badge).not.toBeNull()
    expect(readPdsVariant(badge)).toBe('success')
  })

  it('ac4 happy: deleted state badge uses primary color variant', async () => {
    const entries = [makeEntry({ state: 'deleted' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    // Clear state filter to expose deleted entries
    const stateFilter = container.querySelector('[name="state-filter"]')
    fireEvent(stateFilter!, new CustomEvent('update', { detail: { value: [] }, bubbles: true }))
    await flush()

    const badge = container.querySelector('[data-testid="memory-entry-state"]')
    expect(badge).not.toBeNull()
    expect(readPdsVariant(badge)).toBe('primary')
  })

  it('ac4 happy: scope_agents renders as comma-joined string when non-empty', async () => {
    const entries = [makeEntry({ scope_agents: ['builder', 'reviewer', 'auditor'], state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const agentsEl = container.querySelector('[data-testid="memory-entry-agents"]')
    const text = agentsEl?.textContent ?? ''
    expect(text).toContain('builder')
    expect(text).toContain('reviewer')
    expect(text).toContain('auditor')
  })

  it('ac4 edge: empty scope_agents array renders the string "All agents"', async () => {
    const entries = [makeEntry({ scope_agents: [], state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const agentsEl = container.querySelector('[data-testid="memory-entry-agents"]')
    expect(agentsEl?.textContent).toBe('All agents')
  })

  it('ac4 edge: wildcard scope_agents renders the string "All agents"', async () => {
    const entries = [makeEntry({ scope_agents: ['*'], state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const agentsEl = container.querySelector('[data-testid="memory-entry-agents"]')
    expect(agentsEl?.textContent).toBe('All agents')
  })
})

// ─── AC5: Empty states ────────────────────────────────────────────────────────

describe('TestFromAC_MemoryTabEmptyStates', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac5 happy: (a) API returns zero entries → shows "No memory entries yet"', async () => {
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse([])))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    expect(container.textContent).toContain('No memory entries yet')
  })

  it('ac5 boundary: (a) message is absent when at least one entry exists', async () => {
    const entries = [makeEntry({ state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    expect(container.textContent).not.toContain('No memory entries yet')
  })

  it('ac5 happy: (b) entries exist but filters match nothing → shows "No entries match your filters"', async () => {
    const entries = [makeEntry({ id: 'e1', categories: ['behaviour'], state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    // Set category filter to something that matches nothing
    const categoryFilter = container.querySelector('[name="category-filter"]')
    fireEvent(categoryFilter!, new CustomEvent('update', { detail: { value: ['process'] }, bubbles: true }))
    await flush()

    expect(container.textContent).toContain('No entries match your filters')
  })

  it('ac5 happy: filter-mismatch empty state renders clear-filters button with data-testid="clear-filters"', async () => {
    const entries = [makeEntry({ id: 'e1', categories: ['behaviour'], state: 'pending' })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const categoryFilter = container.querySelector('[name="category-filter"]')
    fireEvent(categoryFilter!, new CustomEvent('update', { detail: { value: ['process'] }, bubbles: true }))
    await flush()

    expect(container.querySelector('[data-testid="clear-filters"]')).not.toBeNull()
  })

  it('ac5 happy: clicking clear-filters resets every control to AC2 initial values', async () => {
    const entries = [
      makeEntry({ id: 'e1', title: 'Pending Entry', state: 'pending', categories: ['behaviour'] }),
      makeEntry({ id: 'e2', title: 'Deleted Entry', state: 'deleted', categories: ['behaviour'] }),
    ]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    // Apply category filter that matches nothing to trigger filter-mismatch empty state
    const categoryFilter = container.querySelector('[name="category-filter"]')
    fireEvent(categoryFilter!, new CustomEvent('update', { detail: { value: ['process'] }, bubbles: true }))
    await flush()

    const clearBtn = container.querySelector('[data-testid="clear-filters"]')!
    fireEvent.click(clearBtn)
    await flush()

    const stateFilter = container.querySelector('[name="state-filter"]')
    const categoryFilterAfterReset = container.querySelector('[name="category-filter"]')
    const agentFilter = container.querySelector('[name="agent-filter"]')
    const searchFilter = container.querySelector('[name="memory-search"]')

    expect(readHostStringArray(stateFilter)).toEqual(['pending', 'curated', 'approved'])
    expect(readHostStringArray(categoryFilterAfterReset)).toEqual([])
    expect(readHostValue(agentFilter)).toBe('')
    expect(readHostValue(searchFilter)).toBe('')

    // After reset, pending entry visible; deleted remains hidden (initial state filter)
    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Pending Entry')
    expect(titles).not.toContain('Deleted Entry')
  })

  it('ac5 edge: (b) message is absent when at least one entry passes filters', async () => {
    const entries = [makeEntry({ state: 'pending', categories: ['behaviour'] })]
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    expect(container.textContent).not.toContain('No entries match your filters')
  })
})

// ─── AC6: Parse errors warning ────────────────────────────────────────────────

describe('TestFromAC_MemoryTabParseErrors', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac6 happy: parse_errors > 0 renders element with data-testid="parse-errors-warning"', async () => {
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse([], 3)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    expect(container.querySelector('[data-testid="parse-errors-warning"]')).not.toBeNull()
  })

  it('ac6 happy: parse-errors warning text contains "{N} entries couldn\'t be read"', async () => {
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse([], 3)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const warning = container.querySelector('[data-testid="parse-errors-warning"]')
    expect(warning?.textContent).toContain("3 entries couldn't be read")
  })

  it('ac6 boundary: parse_errors = 1 shows "1 entries couldn\'t be read"', async () => {
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse([], 1)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    const warning = container.querySelector('[data-testid="parse-errors-warning"]')
    expect(warning?.textContent).toContain("1 entries couldn't be read")
  })

  it('ac6 edge: parse_errors = 0 does NOT render parse-errors-warning element', async () => {
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse([], 0)))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()

    expect(container.querySelector('[data-testid="parse-errors-warning"]')).toBeNull()
  })
})
