/**
 * Task #1672 — P3-02: Memory accordion detail and state-dependent actions
 *
 * Covers AC1–AC6: PAccordion per-entry expand with sanitised markdown + all metadata,
 * state-dependent action buttons (Approve / Edit / Delete), inline edit form with
 * character counter and POST mutations, nav-rail memory pending-count badge, error UX
 * (409 OCC / 404 / 422 field-level), response-driven local state updates (no
 * list-level spinner), and state-promotion feedback (pending → curated auto-promotion).
 *
 * RED phase:
 * - MemoryTab.tsx renders <li> per entry — no p-accordion, no action buttons, no edit
 *   form, no mutation logic → all MemoryTab assertions fail.
 * - Shell.tsx has no memory pending-count badge logic → all nav-badge assertions fail.
 * - MEMORY_SANITIZE_SCHEMA is not exported from MemoryTab → schema assertions fail.
 * - usePendingMemoryCount hook does not exist → dynamic-import assertion fails.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, fireEvent, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import MemoryTab, { MEMORY_SANITIZE_SCHEMA } from '../pages/MemoryTab'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import { usePendingDRs } from '../hooks/usePendingDRs'
import type { UsePendingDRsResult } from '../hooks/usePendingDRs'

// ─── Module mocks (hoisted before imports by Vitest) ─────────────────────────

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn((): UsePendingDRsResult => ({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}))

// Routes mock includes memory — Shell nav-badge tests need [data-surface="memory"]
vi.mock('../routes', () => {
  function Stub() {
    return null
  }
  return {
    routeConfig: [
      { path: '/', label: 'Kanban', icon: 'kanban', component: Stub },
      { path: '/decisions', label: 'Decisions', icon: 'decisions', component: Stub, hasSidecar: false },
      { path: '/memories', label: 'Memory', icon: 'memory', component: Stub, hasSidecar: false },
    ],
  }
})

// react-markdown mock — wrapped in vi.fn() so rehypePlugins/remarkPlugins props can be inspected
vi.mock('react-markdown', () => ({
  default: vi.fn(({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  )),
}))

import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

type MemoryState = 'pending' | 'curated' | 'approved' | 'deleted'

interface MemoryEntryFixture {
  id: string
  title: string
  content: string
  categories: string[]
  confidence: number
  state: MemoryState
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
    content: '**Important** insight about the system.',
    categories: ['behaviour'],
    confidence: 0.85,
    state: 'pending',
    scope_agents: ['builder'],
    source_agent: 'test-agent',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    approved_at: null,
    ...overrides,
  }
}

function makeApiResponse(entries: MemoryEntryFixture[], parse_errors = 0) {
  return { entries, parse_errors }
}

function makeOkFetch(body: unknown = makeApiResponse([])) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
  })
}

/** Returns ok for the first N list-fetches, then a specific status for one mutation. */
function makeMutationFetch(
  mutationStatus: number,
  mutationBody: unknown,
  listBody: unknown = makeApiResponse([makeEntry()]),
) {
  let call = 0
  return vi.fn().mockImplementation((_url: string) => {
    call++
    // First call: list fetch
    if (call === 1) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(listBody),
      })
    }
    // Subsequent call: mutation
    return Promise.resolve({
      ok: mutationStatus >= 200 && mutationStatus < 300,
      status: mutationStatus,
      json: () => Promise.resolve(mutationBody),
    })
  })
}

/** Abortable pending fetch — used for Shell nav-badge tests to suppress board calls. */
function _makeAbortablePendingFetch() {
  return vi.fn((_url: string, init?: RequestInit) =>
    new Promise<never>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () =>
        reject(new DOMException('Aborted', 'AbortError')),
      )
    }),
  )
}

// ─── Utilities ────────────────────────────────────────────────────────────────

async function flush() {
  await act(async () => {
    await Promise.resolve()
  })
}

function renderMemoryTab() {
  return render(<MemoryTab />)
}

function renderShell(initialRoute = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[initialRoute]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

/** Renders MemoryTab with entries loaded and waits for fetch to complete. */
async function renderWithEntries(entries: MemoryEntryFixture[]): Promise<HTMLElement> {
  vi.stubGlobal('fetch', makeOkFetch(makeApiResponse(entries)))
  let container!: HTMLElement
  await act(async () => {
    container = renderMemoryTab().container
  })
  await flush()
  return container
}

/**
 * Attempts to open the accordion for the entry at entryIndex.
 * Returns the p-accordion element (or null if not found — expected in RED phase).
 */
async function openAccordion(container: HTMLElement, entryIndex = 0): Promise<Element | null> {
  const accordions = container.querySelectorAll('p-accordion')
  const accordion = accordions[entryIndex] ?? null
  if (accordion) {
    await act(async () => {
      fireEvent(accordion, new CustomEvent('update', { bubbles: true, detail: { open: true } }))
    })
    await flush()
  }
  return accordion
}

function memoryBtn(container: HTMLElement): HTMLElement | null {
  return container.querySelector<HTMLElement>('[data-surface="memory"]')
}

// ─── AC1: PAccordion expand per entry with sanitised markdown and metadata ────

describe('TestFromAC_MemoryAccordion', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 happy: each visible entry renders a p-accordion element', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1' }), makeEntry({ id: 'e2' })])
    const accordions = container.querySelectorAll('p-accordion')
    expect(accordions.length).toBe(2)
  })

  it('ac1 happy: accordion is collapsed by default (open is falsy on mount)', async () => {
    const container = await renderWithEntries([makeEntry()])
    const accordion = container.querySelector('p-accordion')
    expect(accordion).not.toBeNull()
    const openAttr = (accordion as HTMLElement & { open?: boolean })?.open ?? accordion?.getAttribute('open')
    expect(openAttr).toBeFalsy()
  })

  it('ac1 happy: firing accordion update event shows the accordion detail element', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)
    expect(container.querySelector('[data-testid="memory-accordion-detail"]')).not.toBeNull()
  })

  it('ac1 happy: accordion detail renders entry content as markdown via ReactMarkdown', async () => {
    const container = await renderWithEntries([makeEntry({ content: '**Bold** content' })])
    await openAccordion(container)
    // react-markdown mock wraps content in [data-testid="markdown-body"]
    const markdownEl = container.querySelector('[data-testid="markdown-body"]')
    expect(markdownEl).not.toBeNull()
    expect(markdownEl?.textContent).toContain('Bold')
  })

  it('ac1 happy: accordion detail shows source_agent metadata field', async () => {
    const container = await renderWithEntries([makeEntry({ source_agent: 'my-agent' })])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('my-agent')
  })

  it('ac1 happy: accordion detail shows confidence value', async () => {
    const container = await renderWithEntries([makeEntry({ confidence: 0.92 })])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('0.92')
  })

  it('ac1 happy: accordion detail shows created_at and updated_at timestamps', async () => {
    const container = await renderWithEntries([
      makeEntry({ created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-03T00:00:00Z' }),
    ])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('2026-01-01')
    expect(detail?.textContent).toContain('2026-01-03')
  })

  it('ac1 edge: closing the accordion hides the detail content', async () => {
    const container = await renderWithEntries([makeEntry()])
    // Open accordion
    await openAccordion(container)
    expect(container.querySelector('[data-testid="memory-accordion-detail"]')).not.toBeNull()
    // Close accordion
    const accordion = container.querySelector('p-accordion')!
    await act(async () => {
      fireEvent(accordion, new CustomEvent('update', { bubbles: true, detail: { open: false } }))
    })
    await flush()
    expect(container.querySelector('[data-testid="memory-accordion-detail"]')).toBeNull()
  })

  it('ac1 edge: opening one accordion does not open the other entries', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1' }), makeEntry({ id: 'e2' })])
    await openAccordion(container, 0)
    // Only one detail panel should be open
    const openDetails = container.querySelectorAll('[data-testid="memory-accordion-detail"]')
    expect(openDetails.length).toBe(1)
  })
})

// ─── AC1: Sanitisation schema ─────────────────────────────────────────────────

describe('TestFromAC_MemoryAccordionSanitize', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 security: MEMORY_SANITIZE_SCHEMA is exported from MemoryTab page module', async () => {
    const mod = await import('../pages/MemoryTab') as Record<string, unknown>
    expect(mod['MEMORY_SANITIZE_SCHEMA']).toBeDefined()
  })

  it('ac1 security: sanitise schema allows block tags p ul ol li br', async () => {
    const mod = await import('../pages/MemoryTab') as Record<string, unknown>
    const schema = mod['MEMORY_SANITIZE_SCHEMA'] as { tagNames?: string[] }
    const allowedTags = schema?.tagNames ?? []
    expect(allowedTags).toContain('p')
    expect(allowedTags).toContain('ul')
    expect(allowedTags).toContain('ol')
    expect(allowedTags).toContain('li')
    expect(allowedTags).toContain('br')
  })

  it('ac1 security: sanitise schema allows inline tags strong em code a', async () => {
    const mod = await import('../pages/MemoryTab') as Record<string, unknown>
    const schema = mod['MEMORY_SANITIZE_SCHEMA'] as { tagNames?: string[] }
    const allowedTags = schema?.tagNames ?? []
    expect(allowedTags).toContain('strong')
    expect(allowedTags).toContain('em')
    expect(allowedTags).toContain('code')
    expect(allowedTags).toContain('a')
  })

  it('ac1 security: sanitise schema restricts a[href] to http https mailto protocols', async () => {
    const mod = await import('../pages/MemoryTab') as Record<string, unknown>
    const schema = mod['MEMORY_SANITIZE_SCHEMA'] as {
      protocols?: Record<string, string[]>
    }
    const hrefProtocols = schema?.protocols?.href ?? []
    expect(hrefProtocols).toContain('http')
    expect(hrefProtocols).toContain('https')
    expect(hrefProtocols).toContain('mailto')
    expect(hrefProtocols).not.toContain('javascript')
    expect(hrefProtocols).not.toContain('data')
  })

  it('ac1 security: accordion detail does not use dangerouslySetInnerHTML (no innerHTML patterns in DOM)', async () => {
    vi.stubGlobal(
      'fetch',
      makeOkFetch(makeApiResponse([makeEntry({ content: '<script>alert(1)</script>' })])),
    )
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()
    await openAccordion(container)
    // A script element must NOT appear in the DOM inside the accordion detail
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.querySelector('script')).toBeNull()
  })
})

// ─── AC2: State-dependent action buttons ──────────────────────────────────────

describe('TestFromAC_MemoryActionButtons', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac2 happy: Approve button is visible inside open accordion for curated entry', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'curated' })])
    await openAccordion(container)
    expect(container.querySelector('[data-testid="memory-approve-btn"]')).not.toBeNull()
  })

  it('ac2 edge: Approve button is absent for pending entry', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'pending' })])
    const accordion = await openAccordion(container)
    // Accordion must open first — fails in RED (no p-accordion rendered)
    expect(accordion).not.toBeNull()
    expect(container.querySelector('[data-testid="memory-approve-btn"]')).toBeNull()
  })

  it('ac2 edge: Approve button is absent for approved entry', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'approved' })])
    const accordion = await openAccordion(container)
    expect(accordion).not.toBeNull()
    expect(container.querySelector('[data-testid="memory-approve-btn"]')).toBeNull()
  })

  it('ac2 edge: Approve button is absent for deleted entry', async () => {
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse([makeEntry({ id: 'e1', state: 'deleted' })])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    // Clear state filter to show deleted entries
    const stateFilter = container.querySelector('[name="state-filter"]')
    if (stateFilter) {
      fireEvent(stateFilter, new CustomEvent('update', { detail: { value: [] }, bubbles: true }))
      await flush()
    }
    const accordion = await openAccordion(container)
    expect(accordion).not.toBeNull()
    expect(container.querySelector('[data-testid="memory-approve-btn"]')).toBeNull()
  })

  it('ac2 happy: Edit button is visible inside open accordion for pending entry', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'pending' })])
    await openAccordion(container)
    expect(container.querySelector('[data-testid="memory-edit-btn"]')).not.toBeNull()
  })

  it('ac2 happy: Edit button is visible inside open accordion for curated entry', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'curated' })])
    await openAccordion(container)
    expect(container.querySelector('[data-testid="memory-edit-btn"]')).not.toBeNull()
  })

  it('ac2 happy: Edit button for approved entry shows inline warning "Editing will require re-approval"', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'approved' })])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('Editing will require re-approval')
    expect(container.querySelector('[data-testid="memory-edit-btn"]')).not.toBeNull()
  })

  it('ac2 edge: Edit button is absent for deleted entry', async () => {
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse([makeEntry({ id: 'e1', state: 'deleted' })])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    const stateFilter = container.querySelector('[name="state-filter"]')
    if (stateFilter) {
      fireEvent(stateFilter, new CustomEvent('update', { detail: { value: [] }, bubbles: true }))
      await flush()
    }
    const accordion = await openAccordion(container)
    expect(accordion).not.toBeNull()
    expect(container.querySelector('[data-testid="memory-edit-btn"]')).toBeNull()
  })

  it('ac2 happy: Delete button is visible inside open accordion for pending entry', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'pending' })])
    await openAccordion(container)
    expect(container.querySelector('[data-testid="memory-delete-btn"]')).not.toBeNull()
  })

  it('ac2 happy: Delete button is visible inside open accordion for curated entry', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'curated' })])
    await openAccordion(container)
    expect(container.querySelector('[data-testid="memory-delete-btn"]')).not.toBeNull()
  })

  it('ac2 edge: Delete button is absent for deleted entry', async () => {
    vi.stubGlobal('fetch', makeOkFetch(makeApiResponse([makeEntry({ id: 'e1', state: 'deleted' })])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    const stateFilter = container.querySelector('[name="state-filter"]')
    if (stateFilter) {
      fireEvent(stateFilter, new CustomEvent('update', { detail: { value: [] }, bubbles: true }))
      await flush()
    }
    const accordion = await openAccordion(container)
    expect(accordion).not.toBeNull()
    expect(container.querySelector('[data-testid="memory-delete-btn"]')).toBeNull()
  })

  it('ac2 happy: Delete dialog for pending entry describes permanent deletion (hard-delete)', async () => {
    vi.stubGlobal(
      'fetch',
      makeMutationFetch(200, { success: true }, makeApiResponse([makeEntry({ id: 'e1', state: 'pending' })])),
    )
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const deleteBtn = container.querySelector('[data-testid="memory-delete-btn"]')
    if (deleteBtn) {
      await act(async () => { fireEvent.click(deleteBtn) })
      await flush()
    }
    // Dialog or confirmation text should mention permanent / hard delete
    expect(container.textContent?.toLowerCase()).toMatch(/permanent|hard.?delete|permanently/)
  })

  it('ac2 happy: Delete dialog for curated entry describes soft-delete (entry becomes deleted state)', async () => {
    vi.stubGlobal(
      'fetch',
      makeMutationFetch(200, { success: true }, makeApiResponse([makeEntry({ id: 'e1', state: 'curated' })])),
    )
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const deleteBtn = container.querySelector('[data-testid="memory-delete-btn"]')
    if (deleteBtn) {
      await act(async () => { fireEvent.click(deleteBtn) })
      await flush()
    }
    // Dialog should mention soft-delete / mark as deleted / hide
    expect(container.textContent?.toLowerCase()).toMatch(/mark|archive|soft.?delete|removed from view/)
  })
})

// ─── AC3a: Inline edit form and character counter ─────────────────────────────

describe('TestFromAC_MemoryEditForm', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac3 happy: clicking Edit button renders an inline edit form within the accordion', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    expect(container.querySelector('[data-testid="memory-edit-form"]')).not.toBeNull()
  })

  it('ac3 happy: edit form contains a title input field', async () => {
    const container = await renderWithEntries([makeEntry()])
    const accordion = await openAccordion(container)
    // Accordion must open first — fails in RED (no p-accordion exists)
    expect(accordion).not.toBeNull()
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const form = container.querySelector('[data-testid="memory-edit-form"]')
    expect(form).not.toBeNull()
    const titleField = form!.querySelector('[name="edit-title"]') ?? form!.querySelector('[data-testid="edit-title"]')
    expect(titleField).not.toBeNull()
  })

  it('ac3 happy: edit form content field has a character counter with 1024 limit', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    expect(container.querySelector('[data-testid="memory-char-counter"]')).not.toBeNull()
  })

  it('ac3 boundary: character counter limit is 1024 characters for content field', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const counter = container.querySelector('[data-testid="memory-char-counter"]')
    expect(counter?.textContent).toContain('1024')
  })

  it('ac3 happy: save sends POST to /api/memories/{id}/edit', async () => {
    const entry = makeEntry({ id: 'entry-42', state: 'pending', updated_at: '2026-01-02T00:00:00Z' })
    const fetchMock = makeMutationFetch(
      200,
      { entry: { ...entry, title: 'Updated' } },
      makeApiResponse([entry]),
    )
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    if (saveBtn) {
      await act(async () => { fireEvent.click(saveBtn) })
      await flush()
    }
    const calls = fetchMock.mock.calls as [string, unknown][]
    const mutationCall = calls.find(([url]) => url.includes('/api/memories/') && url.includes('/edit'))
    expect(mutationCall).toBeDefined()
  })

  it('ac3 happy: save payload includes expected_updated_at matching entry updated_at', async () => {
    const entry = makeEntry({ id: 'entry-42', state: 'pending', updated_at: '2026-03-15T12:00:00Z' })
    const fetchMock = makeMutationFetch(200, { entry }, makeApiResponse([entry]))
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    if (saveBtn) {
      await act(async () => { fireEvent.click(saveBtn) })
      await flush()
    }
    const calls = fetchMock.mock.calls as [string, RequestInit][]
    const mutationCall = calls.find(([url]) => url.includes('/edit'))
    const body = JSON.parse((mutationCall?.[1]?.body as string) ?? '{}') as Record<string, unknown>
    expect(body['expected_updated_at']).toBe('2026-03-15T12:00:00Z')
  })

  it('ac3 happy: entry list remains visible (no list-level loading indicator) during edit save', async () => {
    const entry = makeEntry({ id: 'e1', state: 'pending' })
    // Second fetch (mutation) is slow — doesn't resolve immediately
    let resolveMutation!: (value: unknown) => void
    const fetchMock = vi.fn().mockImplementationOnce(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(makeApiResponse([entry])) }),
    ).mockImplementationOnce(() =>
      new Promise((resolve) => { resolveMutation = resolve }),
    )
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    // Accordion must open — fails in RED (no p-accordion)
    const accordion = await openAccordion(container)
    expect(accordion).not.toBeNull()
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    expect(saveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(saveBtn!) })
    // While mutation is in-flight: entry title must still be in DOM
    expect(container.querySelector('[data-testid="memory-entry-title"]')).not.toBeNull()
    // No list-level loading indicator
    expect(container.querySelector('[data-testid="memory-loading"]')).toBeNull()
    // Clean up
    resolveMutation?.({ ok: true, status: 200, json: () => Promise.resolve({ entry }) })
  })
})

// ─── AC3b: Nav-rail memory pending-count badge ────────────────────────────────
//
// Shell does not yet implement memory pending-count badges — it only badges the
// decisions route. All tests that assert badge presence fail in RED phase.
// The pending count is not injected via a mock hook (usePendingMemoryCount does not
// exist yet); instead we stub fetch to return pending memory entries and assert Shell
// observes them — which it cannot without the implementation.

describe('TestFromAC_MemoryNavBadge', () => {
  beforeEach(() => {
    // Stub fetch: /api/memories returns 3 pending entries; other calls stay pending+abort.
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        if (typeof _url === 'string' && _url.includes('/api/memories')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () =>
              Promise.resolve(
                makeApiResponse([
                  makeEntry({ id: 'm1', state: 'pending' }),
                  makeEntry({ id: 'm2', state: 'pending' }),
                  makeEntry({ id: 'm3', state: 'pending' }),
                ]),
              ),
          })
        }
        return new Promise<never>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError')),
          )
        })
      }),
    )
    vi.mocked(usePendingDRs).mockReturnValue({
      count: 0,
      items: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac3 happy: memory nav button shows [data-testid="nav-badge"] when pending entries exist', async () => {
    // Shell must derive pending count from /api/memories (or CockpitProvider) and show badge.
    // Currently Shell only badges the decisions route → assertion fails in RED.
    const { container } = renderShell('/')
    await flush()
    const btn = memoryBtn(container)
    expect(btn).not.toBeNull()
    expect(btn!.querySelector('[data-testid="nav-badge"]')).not.toBeNull()
  })

  it('ac3 happy: memory nav button badge text shows pending entry count', async () => {
    // Badge text must equal the number of pending memory entries (3 in this test).
    // Shell currently ignores /api/memories for badge → assertion fails in RED.
    const { container } = renderShell('/')
    await flush()
    const btn = memoryBtn(container)
    expect(btn).not.toBeNull()
    const badge = btn!.querySelector('[data-testid="nav-badge"]')
    expect(badge).not.toBeNull()
    expect(badge?.textContent?.trim()).toBe('3')
  })

  it('ac3 happy: memory nav button aria-label includes pending count text when badge visible', async () => {
    // aria-label must be "Memory (3 pending)" when count > 0.
    // Shell currently does not update aria-label for memory route → fails in RED.
    const { container } = renderShell('/')
    await flush()
    const btn = memoryBtn(container)
    expect(btn).not.toBeNull()
    expect(btn!.getAttribute('aria-label')).toMatch(/Memory \(3 pending\)/)
  })
})

// ─── AC4: Error UX — 409 OCC, 404 not found, 422 validation ─────────────────

describe('TestFromAC_MemoryErrorUX', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac4 happy: 409 response after approve shows inline banner within accordion', async () => {
    const entry = makeEntry({ id: 'e1', state: 'curated' })
    vi.stubGlobal('fetch', makeMutationFetch(409, { detail: 'conflict' }, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    if (approveBtn) {
      await act(async () => { fireEvent.click(approveBtn) })
      await flush()
    }
    expect(container.querySelector('[data-testid="memory-occ-banner"]')).not.toBeNull()
  })

  it('ac4 happy: 409 OCC banner contains "Entry was modified" text', async () => {
    const entry = makeEntry({ id: 'e1', state: 'curated' })
    vi.stubGlobal('fetch', makeMutationFetch(409, { detail: 'conflict' }, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    if (approveBtn) {
      await act(async () => { fireEvent.click(approveBtn) })
      await flush()
    }
    const banner = container.querySelector('[data-testid="memory-occ-banner"]')
    expect(banner?.textContent).toContain('Entry was modified')
  })

  it('ac4 happy: 409 OCC triggers automatic re-fetch of /api/memories', async () => {
    const entry = makeEntry({ id: 'e1', state: 'curated' })
    const fetchMock = makeMutationFetch(409, { detail: 'conflict' }, makeApiResponse([entry]))
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    const callsAfterMount = (fetchMock.mock.calls as [string][]).filter(([url]) => url.includes('/api/memories')).length
    await openAccordion(container)
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    if (approveBtn) {
      await act(async () => { fireEvent.click(approveBtn) })
      await flush()
    }
    const callsAfterMutation = (fetchMock.mock.calls as [string][]).filter(([url]) => url.includes('/api/memories')).length
    expect(callsAfterMutation).toBeGreaterThan(callsAfterMount)
  })

  it('ac4 happy: 404 response shows "Entry no longer exists" message in accordion', async () => {
    const entry = makeEntry({ id: 'e1', state: 'curated' })
    vi.stubGlobal('fetch', makeMutationFetch(404, { detail: 'not found' }, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    if (approveBtn) {
      await act(async () => { fireEvent.click(approveBtn) })
      await flush()
    }
    expect(container.textContent).toContain('Entry no longer exists')
  })

  it('ac4 happy: 404 response removes the affected entry from the visible list', async () => {
    const entry = makeEntry({ id: 'e1', title: 'Gone Entry', state: 'curated' })
    vi.stubGlobal('fetch', makeMutationFetch(404, { detail: 'not found' }, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    if (approveBtn) {
      await act(async () => { fireEvent.click(approveBtn) })
      await flush()
    }
    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).not.toContain('Gone Entry')
  })

  it('ac4 happy: 422 response shows field-level messages parsed from FastAPI detail array', async () => {
    const entry = makeEntry({ id: 'e1', state: 'pending' })
    const validationBody = {
      detail: [
        { loc: ['body', 'confidence'], msg: 'must be between 0.7 and 1.0', type: 'value_error' },
      ],
    }
    vi.stubGlobal('fetch', makeMutationFetch(422, validationBody, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    if (saveBtn) {
      await act(async () => { fireEvent.click(saveBtn) })
      await flush()
    }
    expect(container.textContent).toContain('must be between 0.7 and 1.0')
  })

  it('ac4 edge: 422 with multiple field errors shows each field message individually', async () => {
    const entry = makeEntry({ id: 'e1', state: 'pending' })
    const validationBody = {
      detail: [
        { loc: ['body', 'confidence'], msg: 'must be >= 0.7', type: 'value_error' },
        { loc: ['body', 'title'], msg: 'field required', type: 'missing' },
      ],
    }
    vi.stubGlobal('fetch', makeMutationFetch(422, validationBody, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    if (saveBtn) {
      await act(async () => { fireEvent.click(saveBtn) })
      await flush()
    }
    expect(container.textContent).toContain('must be >= 0.7')
    expect(container.textContent).toContain('field required')
  })
})

// ─── AC5: Response-driven local state updates ─────────────────────────────────

describe('TestFromAC_MemoryLocalUpdate', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac5 happy: approve success replaces entry in list from response payload entry field', async () => {
    const original = makeEntry({ id: 'e1', state: 'curated', title: 'Original Title' })
    const updated = { ...original, state: 'approved' as MemoryState, title: 'Approved Title' }
    vi.stubGlobal('fetch', makeMutationFetch(200, { entry: updated }, makeApiResponse([original])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    if (approveBtn) {
      await act(async () => { fireEvent.click(approveBtn) })
      await flush()
    }
    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Approved Title')
    expect(titles).not.toContain('Original Title')
  })

  it('ac5 happy: edit success replaces entry in list from response payload entry field', async () => {
    const original = makeEntry({ id: 'e1', state: 'pending', title: 'Before Edit' })
    const updated = { ...original, title: 'After Edit' }
    vi.stubGlobal('fetch', makeMutationFetch(200, { entry: updated }, makeApiResponse([original])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    if (saveBtn) {
      await act(async () => { fireEvent.click(saveBtn) })
      await flush()
    }
    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('After Edit')
    expect(titles).not.toContain('Before Edit')
  })

  it('ac5 happy: delete on pending entry removes it entirely from the visible list', async () => {
    const entry = makeEntry({ id: 'e1', title: 'Pending Gone', state: 'pending' })
    vi.stubGlobal('fetch', makeMutationFetch(200, { success: true }, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const deleteBtn = container.querySelector('[data-testid="memory-delete-btn"]')
    if (deleteBtn) {
      await act(async () => { fireEvent.click(deleteBtn) })
      await flush()
      // Confirm dialog if it appears
      const confirmBtn = container.querySelector('[data-testid="memory-delete-confirm-btn"]')
      if (confirmBtn) {
        await act(async () => { fireEvent.click(confirmBtn) })
        await flush()
      }
    }
    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).not.toContain('Pending Gone')
  })

  it('ac5 happy: delete on curated entry updates its state to "deleted" in the list (soft-delete)', async () => {
    const entry = makeEntry({ id: 'e1', title: 'Curated Soft', state: 'curated' })
    vi.stubGlobal('fetch', makeMutationFetch(200, { success: true }, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const deleteBtn = container.querySelector('[data-testid="memory-delete-btn"]')
    if (deleteBtn) {
      await act(async () => { fireEvent.click(deleteBtn) })
      await flush()
      const confirmBtn = container.querySelector('[data-testid="memory-delete-confirm-btn"]')
      if (confirmBtn) {
        await act(async () => { fireEvent.click(confirmBtn) })
        await flush()
      }
    }
    // Entry state badge should now read "deleted" (soft-delete, not removed from list)
    // Show deleted entries by clearing state filter
    const stateFilter = container.querySelector('[name="state-filter"]')
    if (stateFilter) {
      fireEvent(stateFilter, new CustomEvent('update', { detail: { value: [] }, bubbles: true }))
      await flush()
    }
    const stateBadges = Array.from(container.querySelectorAll('[data-testid="memory-entry-state"]')).map(
      (el) => el.textContent,
    )
    expect(stateBadges).toContain('deleted')
  })

  it('ac5 happy: mutation failure leaves local state unchanged (no optimistic update)', async () => {
    const entry = makeEntry({ id: 'e1', state: 'curated', title: 'Should Stay' })
    vi.stubGlobal('fetch', makeMutationFetch(500, { detail: 'server error' }, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    // Accordion must open — fails in RED (no p-accordion exists)
    const accordion = await openAccordion(container)
    expect(accordion).not.toBeNull()
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    expect(approveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(approveBtn!) })
    await flush()
    const titles = Array.from(container.querySelectorAll('[data-testid="memory-entry-title"]')).map(
      (el) => el.textContent,
    )
    expect(titles).toContain('Should Stay')
    // State badge must remain 'curated' (not changed optimistically)
    const stateBadge = container.querySelector('[data-testid="memory-entry-state"]')
    expect(stateBadge?.textContent).toBe('curated')
  })

  it('ac5 edge: no list-level loading spinner appears during mutation — entries stay visible', async () => {
    const entry = makeEntry({ id: 'e1', state: 'curated', title: 'Visible During Mutation' })
    let resolveMutation!: (value: unknown) => void
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(makeApiResponse([entry])),
      })
      .mockImplementationOnce(
        () => new Promise((resolve) => { resolveMutation = resolve }),
      )
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    // Accordion must open — fails in RED (no p-accordion exists)
    const accordion = await openAccordion(container)
    expect(accordion).not.toBeNull()
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    // Approve button must exist — fails in RED
    expect(approveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(approveBtn!) })
    // While mutation is in-flight: entry still visible and no list loading indicator
    expect(container.querySelector('[data-testid="memory-entry-title"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="memory-loading"]')).toBeNull()
    resolveMutation?.({ ok: true, status: 200, json: () => Promise.resolve({ entry }) })
  })
})

// ─── AC6: State promotion feedback ───────────────────────────────────────────

describe('TestFromAC_MemoryStatePromotion', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac6 happy: edit response with state "curated" for previously pending entry updates state badge immediately', async () => {
    const original = makeEntry({ id: 'e1', state: 'pending', scope_agents: [] })
    const promoted = { ...original, state: 'curated' as MemoryState, scope_agents: ['builder'] }
    vi.stubGlobal('fetch', makeMutationFetch(200, { entry: promoted }, makeApiResponse([original])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    if (saveBtn) {
      await act(async () => { fireEvent.click(saveBtn) })
      await flush()
    }
    const stateBadge = container.querySelector('[data-testid="memory-entry-state"]')
    expect(stateBadge?.textContent).toBe('curated')
  })

  it('ac6 happy: state promotion shows inline note "Promoted to curated — scope agents assigned"', async () => {
    const original = makeEntry({ id: 'e1', state: 'pending', scope_agents: [] })
    const promoted = { ...original, state: 'curated' as MemoryState, scope_agents: ['builder'] }
    vi.stubGlobal('fetch', makeMutationFetch(200, { entry: promoted }, makeApiResponse([original])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    if (saveBtn) {
      await act(async () => { fireEvent.click(saveBtn) })
      await flush()
    }
    expect(container.textContent).toContain('Promoted to curated — scope agents assigned')
  })

  it('ac6 edge: no promotion note when edit response state remains pending', async () => {
    const original = makeEntry({ id: 'e1', state: 'pending' })
    const updated = { ...original, title: 'Updated Title' } // state still pending
    vi.stubGlobal('fetch', makeMutationFetch(200, { entry: updated }, makeApiResponse([original])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    // Accordion must open — fails in RED (no p-accordion exists)
    const accordion = await openAccordion(container)
    expect(accordion).not.toBeNull()
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    expect(saveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(saveBtn!) })
    await flush()
    expect(container.textContent).not.toContain('Promoted to curated')
  })

  it('ac6 edge: no promotion note when entry was already curated before the edit', async () => {
    const original = makeEntry({ id: 'e1', state: 'curated' })
    const updated = { ...original, title: 'Curated Updated' }
    vi.stubGlobal('fetch', makeMutationFetch(200, { entry: updated }, makeApiResponse([original])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    const accordion = await openAccordion(container)
    expect(accordion).not.toBeNull()
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    expect(saveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(saveBtn!) })
    await flush()
    expect(container.textContent).not.toContain('Promoted to curated')
  })
})

// ─── AC1 (retry): approved_at metadata field in accordion detail ──────────────
//
// Reviewer gap: existing tests assert source_agent/confidence/created_at/updated_at
// but never assert approved_at is rendered in the accordion detail surface.

describe('TestFromAC_MemoryApprovedAt', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 retry: accordion detail renders approved_at date string when entry has approved_at set', async () => {
    const container = await renderWithEntries([
      makeEntry({ state: 'approved', approved_at: '2026-03-15T10:00:00Z' }),
    ])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('2026-03-15')
  })
})

// ─── AC1 (retry): ReactMarkdown plugin wiring proof ──────────────────────────
//
// Reviewer gap: react-markdown was mocked as a passthrough so the suite could not
// prove that MemoryTab wires rehypeSanitize + MEMORY_SANITIZE_SCHEMA into
// ReactMarkdown's rehypePlugins. The mock now uses vi.fn() so .mock.calls can be
// inspected. Pattern follows ResolveModal.plugins.test.tsx:91-101.

describe('TestFromAC_MemoryAccordionPlugins', () => {
  beforeEach(() => {
    vi.mocked(ReactMarkdown).mockClear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 retry: ReactMarkdown receives rehypeSanitize as the first rehypePlugin when accordion detail opens', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)

    const calls = vi.mocked(ReactMarkdown).mock.calls
    expect(calls.length).toBeGreaterThan(0)
    const props = calls[calls.length - 1][0] as Record<string, unknown>
    const rehypePlugins = (props.rehypePlugins as unknown[] | undefined) ?? []
    // MemoryTab passes [[rehypeSanitize, MEMORY_SANITIZE_SCHEMA]] — tuple form
    expect(rehypePlugins.length).toBeGreaterThan(0)
    const firstPlugin = rehypePlugins[0]
    const pluginFn = Array.isArray(firstPlugin) ? firstPlugin[0] : firstPlugin
    expect(pluginFn).toBe(rehypeSanitize)
  })

  it('ac1 retry: ReactMarkdown receives MEMORY_SANITIZE_SCHEMA as config paired with rehypeSanitize', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)

    const calls = vi.mocked(ReactMarkdown).mock.calls
    expect(calls.length).toBeGreaterThan(0)
    const props = calls[calls.length - 1][0] as Record<string, unknown>
    const rehypePlugins = (props.rehypePlugins as unknown[] | undefined) ?? []
    const firstPlugin = rehypePlugins[0]
    // Tuple form: [rehypeSanitize, MEMORY_SANITIZE_SCHEMA]
    expect(Array.isArray(firstPlugin)).toBe(true)
    const pluginConfig = (firstPlugin as unknown[])[1]
    expect(pluginConfig).toBe(MEMORY_SANITIZE_SCHEMA)
  })
})

// ─── AC2 (retry): Delete confirmation modal element contract ──────────────────
//
// Reviewer gap: existing tests only check container.textContent (which would pass
// for either inline copy or a real modal). Tests must assert the PModal element
// [data-testid="memory-delete-confirm-dialog"] is present and the confirm button
// exists — without conditional if-guards.

describe('TestFromAC_MemoryDeleteModal', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac2 retry: clicking Delete on pending entry renders PModal [data-testid="memory-delete-confirm-dialog"]', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'pending' })])
    await openAccordion(container)
    const deleteBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-btn"]')
    expect(deleteBtn).not.toBeNull()
    await act(async () => { fireEvent.click(deleteBtn!) })
    await flush()
    expect(container.querySelector('[data-testid="memory-delete-confirm-dialog"]')).not.toBeNull()
  })

  it('ac2 retry: clicking Delete on curated entry renders PModal [data-testid="memory-delete-confirm-dialog"]', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'curated' })])
    await openAccordion(container)
    const deleteBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-btn"]')
    expect(deleteBtn).not.toBeNull()
    await act(async () => { fireEvent.click(deleteBtn!) })
    await flush()
    expect(container.querySelector('[data-testid="memory-delete-confirm-dialog"]')).not.toBeNull()
  })

  it('ac2 retry: delete confirmation dialog contains confirm button — unconditional assertion', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'pending' })])
    await openAccordion(container)
    const deleteBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-btn"]')
    expect(deleteBtn).not.toBeNull()
    await act(async () => { fireEvent.click(deleteBtn!) })
    await flush()
    const dialog = container.querySelector('[data-testid="memory-delete-confirm-dialog"]')
    expect(dialog).not.toBeNull()
    // Confirm button must be present — no conditional if-guard
    expect(container.querySelector('[data-testid="memory-delete-confirm-btn"]')).not.toBeNull()
  })
})

// ─── AC3 (retry): Success-path background refetch after every mutation ─────────
//
// Reviewer gap: the only explicit refetch assertion was for the 409 conflict path.
// The source calls void refetch() in handleApprove, handleEditSave, and handleDelete
// on success — this must be proven for each mutation type.
//
// Strategy: count fetch calls to exactly '/api/memories' before and after each
// successful mutation. The background refetch increments the count by 1.

describe('TestFromAC_MemorySuccessRefetch', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac3 retry: approve success triggers background refetch of /api/memories', async () => {
    const entry = makeEntry({ id: 'e1', state: 'curated' })
    const updated = { ...entry, state: 'approved' as MemoryState }
    const fetchMock = makeMutationFetch(200, { entry: updated }, makeApiResponse([entry]))
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    const listCallsBefore = (fetchMock.mock.calls as [string][]).filter(([url]) => url === '/api/memories').length
    await openAccordion(container)
    const approveBtn = container.querySelector<HTMLElement>('[data-testid="memory-approve-btn"]')
    expect(approveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(approveBtn!) })
    await flush()
    const listCallsAfter = (fetchMock.mock.calls as [string][]).filter(([url]) => url === '/api/memories').length
    expect(listCallsAfter).toBeGreaterThan(listCallsBefore)
  })

  it('ac3 retry: edit success triggers background refetch of /api/memories', async () => {
    const entry = makeEntry({ id: 'e1', state: 'pending' })
    const updated = { ...entry, title: 'Edited Title' }
    const fetchMock = makeMutationFetch(200, { entry: updated }, makeApiResponse([entry]))
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    const listCallsBefore = (fetchMock.mock.calls as [string][]).filter(([url]) => url === '/api/memories').length
    await openAccordion(container)
    const editBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const saveBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-save-btn"]')
    expect(saveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(saveBtn!) })
    await flush()
    const listCallsAfter = (fetchMock.mock.calls as [string][]).filter(([url]) => url === '/api/memories').length
    expect(listCallsAfter).toBeGreaterThan(listCallsBefore)
  })

  it('ac3 retry: delete success triggers background refetch of /api/memories', async () => {
    const entry = makeEntry({ id: 'e1', state: 'pending' })
    const fetchMock = makeMutationFetch(200, { success: true }, makeApiResponse([entry]))
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    const listCallsBefore = (fetchMock.mock.calls as [string][]).filter(([url]) => url === '/api/memories').length
    await openAccordion(container)
    const deleteBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-btn"]')
    expect(deleteBtn).not.toBeNull()
    await act(async () => { fireEvent.click(deleteBtn!) })
    await flush()
    const dialog = container.querySelector('[data-testid="memory-delete-confirm-dialog"]')
    expect(dialog).not.toBeNull()
    const confirmBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-confirm-btn"]')
    expect(confirmBtn).not.toBeNull()
    await act(async () => { fireEvent.click(confirmBtn!) })
    await flush()
    const listCallsAfter = (fetchMock.mock.calls as [string][]).filter(([url]) => url === '/api/memories').length
    expect(listCallsAfter).toBeGreaterThan(listCallsBefore)
  })
})
