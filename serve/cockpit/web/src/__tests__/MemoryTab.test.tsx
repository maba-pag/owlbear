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
import { render, fireEvent, act, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import MemoryTab, { MEMORY_SANITIZE_SCHEMA } from '../pages/MemoryTab'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import { usePendingMemoryCount } from '../hooks/usePendingMemoryCount'
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
      { path: '/decisions', label: 'Decisions', icon: 'decisions', component: Stub },
      { path: '/memories', label: 'Memory', icon: 'memory', component: Stub },
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

function PendingMemoryCountProbe() {
  const { count } = usePendingMemoryCount()
  return <span data-testid="pending-memory-count">{count}</span>
}

function renderMemoryTabWithPendingProbe() {
  return render(
    <>
      <PendingMemoryCountProbe />
      <MemoryTab />
    </>,
  )
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

describe('MemoryAccordion', () => {
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

  it('ac1 polish: memory content is the primary detail block before the framed metadata section', async () => {
    const container = await renderWithEntries([makeEntry({ content: 'Primary memory text' })])
    await openAccordion(container)

    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    const contentPanel = container.querySelector('[data-testid="memory-content-panel"]')
    const metadataSection = container.querySelector('[data-testid="memory-metadata-section"]')
    const metadataGrid = container.querySelector('[data-testid="memory-metadata-grid"]')
    expect(contentPanel).not.toBeNull()
    expect(metadataSection).not.toBeNull()
    expect(metadataGrid).not.toBeNull()

    const detailChildren = Array.from(detail?.children ?? [])
    expect(detailChildren.indexOf(contentPanel!)).toBeLessThan(detailChildren.indexOf(metadataSection!))
    expect(contentPanel?.className).toContain('bg-surface')
    expect(contentPanel?.className).toContain('text-base')
    expect(metadataSection?.className).toContain('border')
    expect(metadataSection?.textContent).toContain('Metadata')
    expect(metadataGrid?.className).toContain('text-sm')
    expect(metadataGrid?.className).not.toContain('border-t')
  })

  it('ac1 polish: expanded memory detail keeps bottom padding after actions', async () => {
    const container = await renderWithEntries([makeEntry({ state: 'curated' })])
    await openAccordion(container)

    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    const actions = container.querySelector('[data-testid="memory-detail-actions"]')
    expect(detail).not.toBeNull()
    expect(actions).not.toBeNull()
    expect(detail?.className).toContain('pb-static-md')
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

describe('MemoryAccordionSanitize', () => {
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

describe('MemoryActionButtons', () => {
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

describe('MemoryEditForm', () => {
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

  it('ac3 pds: edit scalar fields use PDS input controls', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const form = container.querySelector('[data-testid="memory-edit-form"]')
    expect(form).not.toBeNull()
    expect(form!.querySelector('p-input-text[name="edit-title"]')).not.toBeNull()
    expect(form!.querySelector('p-input-number[name="edit-confidence"]')).not.toBeNull()
    expect(form!.querySelector('p-input-text[name="new-memory-category"]')).not.toBeNull()
    expect(form!.querySelector('p-input-text[name="new-memory-scope-agent"]')).not.toBeNull()
    expect(form!.querySelector('[data-testid="memory-category-chip-list"]')).not.toBeNull()
    expect(form!.querySelector('[data-testid="memory-scope-agent-chip-list"]')).not.toBeNull()
    expect(form!.querySelector('p-textarea[name="edit-content"]')).not.toBeNull()
    expect(form!.querySelector('[data-pds-exception="memory-edit-native-input"]')).toBeNull()
  })

  it('ac3 pds: categories and scope agents use add and dismissible tag editors', async () => {
    const container = await renderWithEntries([makeEntry({ categories: ['old'], scope_agents: ['*'] })])
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()

    const form = container.querySelector('[data-testid="memory-edit-form"]')!
    expect(form.querySelector('[data-testid="memory-category-chip"][data-category="old"]')).not.toBeNull()
    expect(form.querySelector('[data-testid="memory-scope-agent-chip"][data-scope-agent="*"]')).not.toBeNull()

    fireEvent(form.querySelector('p-input-text[name="new-memory-category"]')!, new CustomEvent('input', { detail: { value: 'process' }, bubbles: true }))
    await act(async () => { fireEvent.click(form.querySelector('[data-testid="memory-add-category-button"]')!) })
    await flush()
    expect(form.querySelector('[data-testid="memory-category-chip"][data-category="process"]')).not.toBeNull()

    await act(async () => { fireEvent.click(form.querySelector('[data-testid="memory-scope-agent-chip"][data-scope-agent="*"]')!) })
    await flush()
    expect(form.querySelector('[data-testid="memory-scope-agent-chip"][data-scope-agent="*"]')).toBeNull()
  })

  it('ac3 happy: edit form content field uses the PDS character counter', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const contentField = container.querySelector('p-textarea[name="edit-content"]') as (HTMLElement & { counter?: boolean }) | null
    expect(contentField).not.toBeNull()
    expect(contentField?.counter).toBe(true)
    expect(container.querySelector('[data-testid="memory-char-counter"]')).toBeNull()
  })

  it('ac3 polish: edit save and cancel controls stay in a sticky action bar', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()

    const actions = container.querySelector('[data-testid="memory-edit-actions"]')
    expect(actions).not.toBeNull()
    expect(actions?.className).toContain('sticky')
    expect(actions?.className).toContain('top-0')
    expect(actions?.className).toContain('bg-canvas')
    expect(actions?.querySelector('[data-testid="memory-edit-cancel-btn"]')).not.toBeNull()
    expect(actions?.querySelector('[data-testid="memory-edit-save-btn"]')).not.toBeNull()
  })

  it('ac3 polish: entering edit mode scrolls the sticky action bar into view without horizontal page movement', async () => {
    const scrollIntoView = vi.fn()
    const scrollTo = vi.fn()
    const originalRequestAnimationFrame = window.requestAnimationFrame
    const originalScrollIntoView = HTMLElement.prototype.scrollIntoView
    const originalGetBoundingClientRect = HTMLElement.prototype.getBoundingClientRect
    const rectAt = (top: number): DOMRect => ({
      x: 0,
      y: top,
      top,
      bottom: top + 20,
      left: 0,
      right: 100,
      width: 100,
      height: 20,
      toJSON: () => ({}),
    }) as DOMRect

    window.requestAnimationFrame = ((callback: FrameRequestCallback) => {
      callback(0)
      return 0
    }) as typeof window.requestAnimationFrame
    HTMLElement.prototype.scrollIntoView = scrollIntoView
    HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect() {
      if (this.parentElement?.getAttribute('data-testid') === 'memory-list-scroll-shell') {
        return rectAt(50)
      }
      if (this.getAttribute('data-testid') === 'memory-edit-actions') {
        return rectAt(250)
      }
      return originalGetBoundingClientRect.call(this)
    }

    try {
      const container = await renderWithEntries([makeEntry()])
      const list = container.querySelector('[data-testid="memory-list-scroll-shell"] ul') as HTMLElement | null
      expect(list).not.toBeNull()
      Object.defineProperty(list!, 'scrollTop', { configurable: true, value: 20, writable: true })
      list!.scrollTo = scrollTo

      await openAccordion(container)
      const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
      expect(editBtn).not.toBeNull()

      await act(async () => { fireEvent.click(editBtn!) })
      await flush()

      const actions = container.querySelector('[data-testid="memory-edit-actions"]') as HTMLElement | null
      expect(actions).not.toBeNull()
      expect(scrollTo).toHaveBeenCalledWith({ top: 220, left: 0 })
      expect(scrollIntoView).not.toHaveBeenCalled()
    } finally {
      window.requestAnimationFrame = originalRequestAnimationFrame
      HTMLElement.prototype.scrollIntoView = originalScrollIntoView
      HTMLElement.prototype.getBoundingClientRect = originalGetBoundingClientRect
    }
  })

  it('ac3 polish: edit mode hides the list scroll cue behind sticky actions', async () => {
    const container = await renderWithEntries([makeEntry()])
    const list = container.querySelector('[data-testid="memory-list-scroll-shell"] ul') as HTMLElement | null
    expect(list).not.toBeNull()
    Object.defineProperty(list, 'scrollHeight', { configurable: true, value: 500 })
    Object.defineProperty(list, 'clientHeight', { configurable: true, value: 100 })
    Object.defineProperty(list, 'scrollTop', { configurable: true, value: 0, writable: true })
    Object.defineProperty(list, 'scrollLeft', { configurable: true, value: 0, writable: true })

    await act(async () => { fireEvent.scroll(list!) })
    await flush()
    expect(container.querySelector('[data-testid="memory-list-scroll-cue"]')).not.toBeNull()

    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()

    expect(container.querySelector('[data-testid="memory-list-scroll-cue"]')).toBeNull()
  })

  it('ac3 boundary: character counter limit is 1024 characters for content field', async () => {
    const container = await renderWithEntries([makeEntry()])
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    if (editBtn) {
      await act(async () => { fireEvent.click(editBtn) })
      await flush()
    }
    const contentField = container.querySelector('p-textarea[name="edit-content"]') as (HTMLElement & { maxLength?: number }) | null
    expect(contentField).not.toBeNull()
    expect(contentField?.maxLength).toBe(1024)
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

  it('ac3 pds: edit controls update the save payload from PDS change events', async () => {
    const entry = makeEntry({
      id: 'entry-42',
      state: 'pending',
      title: 'Original title',
      categories: ['old'],
      confidence: 0.82,
      scope_agents: ['builder'],
      content: 'Original content',
      updated_at: '2026-03-15T12:00:00Z',
    })
    const fetchMock = makeMutationFetch(200, { entry }, makeApiResponse([entry]))
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const form = container.querySelector('[data-testid="memory-edit-form"]')!
    fireEvent(form.querySelector('p-input-text[name="edit-title"]')!, new CustomEvent('input', { detail: { value: 'Updated title' }, bubbles: true }))
    await act(async () => { fireEvent.click(form.querySelector('[data-testid="memory-category-chip"][data-category="old"]')!) })
    fireEvent(form.querySelector('p-input-text[name="new-memory-category"]')!, new CustomEvent('input', { detail: { value: 'process, ux' }, bubbles: true }))
    await act(async () => { fireEvent.click(form.querySelector('[data-testid="memory-add-category-button"]')!) })
    fireEvent(form.querySelector('p-input-number[name="edit-confidence"]')!, new CustomEvent('input', { detail: { value: '0.91' }, bubbles: true }))
    fireEvent(form.querySelector('p-input-text[name="new-memory-scope-agent"]')!, new CustomEvent('input', { detail: { value: 'reviewer' }, bubbles: true }))
    await act(async () => { fireEvent.click(form.querySelector('[data-testid="memory-add-scope-agent-button"]')!) })
    fireEvent(form.querySelector('p-textarea[name="edit-content"]')!, new CustomEvent('input', { detail: { value: 'Updated content' }, bubbles: true }))
    const saveBtn = container.querySelector('[data-testid="memory-edit-save-btn"]')
    expect(saveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(saveBtn!) })
    await flush()
    const calls = fetchMock.mock.calls as [string, RequestInit][]
    const mutationCall = calls.find(([url]) => url.includes('/edit'))
    const body = JSON.parse((mutationCall?.[1]?.body as string) ?? '{}') as Record<string, unknown>
    expect(body).toMatchObject({
      title: 'Updated title',
      categories: ['process', 'ux'],
      confidence: 0.91,
      scope_agents: ['builder', 'reviewer'],
      content: 'Updated content',
      expected_updated_at: '2026-03-15T12:00:00Z',
    })
  })

  it('ac3 regression: approve payload includes expected_updated_at matching entry updated_at', async () => {
    const entry = makeEntry({ id: 'entry-42', state: 'curated', updated_at: '2026-03-20T08:30:00Z' })
    const fetchMock = makeMutationFetch(200, { entry: { ...entry, state: 'approved' } }, makeApiResponse([entry]))
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    if (approveBtn) {
      await act(async () => { fireEvent.click(approveBtn) })
      await flush()
    }
    const calls = fetchMock.mock.calls as [string, RequestInit][]
    const mutationCall = calls.find(([url]) => url.includes('/approve'))
    const body = JSON.parse((mutationCall?.[1]?.body as string) ?? '{}') as Record<string, unknown>
    expect(body['expected_updated_at']).toBe('2026-03-20T08:30:00Z')
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

describe('MemoryNavBadge', () => {
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

describe('MemoryErrorUX', () => {
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
    const form = container.querySelector('[data-testid="memory-edit-form"]')
    const message = form?.querySelector('[data-testid="memory-validation-message"]')
    expect(message).not.toBeNull()
    expect(message).toHaveAttribute('data-field', 'confidence')
    expect(message?.textContent).toContain('must be between 0.7 and 1.0')
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
    const form = container.querySelector('[data-testid="memory-edit-form"]')
    const messages = Array.from(form?.querySelectorAll('[data-testid="memory-validation-message"]') ?? [])
    expect(messages.map((message) => message.getAttribute('data-field'))).toEqual([
      'confidence',
      'title',
    ])
    expect(messages.map((message) => message.textContent)).toEqual([
      'confidence: must be >= 0.7',
      'title: field required',
    ])
  })
})

// ─── AC5: Response-driven local state updates ─────────────────────────────────

describe('MemoryLocalUpdate', () => {
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
    const entries = Array.from(container.querySelectorAll('[data-testid="memory-entry"]'))
    expect(entries.some((el) => el.className.includes('border-l-error'))).toBe(true)
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
    // State border must remain 'curated' (not changed optimistically)
    const entryEl = container.querySelector('[data-testid="memory-entry"]')
    expect(entryEl?.className).toContain('border-l-info')
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

describe('MemoryStatePromotion', () => {
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
    const entryEl = container.querySelector('[data-testid="memory-entry"]')
    expect(entryEl?.className).toContain('border-l-info')
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

describe('MemoryApprovedAt', () => {
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

describe('MemoryAccordionPlugins', () => {
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

describe('MemoryDeleteModal', () => {
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

describe('MemorySuccessRefetch', () => {
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

  it('ac3 regression: pending-to-curated edit decrements pending memory count immediately', async () => {
    const pending = makeEntry({ id: 'e1', state: 'pending' })
    const otherPending = makeEntry({ id: 'e2', state: 'pending', title: 'Other pending' })
    const updated = { ...pending, state: 'curated' as MemoryState, scope_agents: ['builder'] }
    let entries = [pending, otherPending]
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === 'POST' && url === '/api/memories/e1/edit') {
        entries = [updated, otherPending]
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ entry: updated }) })
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(makeApiResponse(entries)) })
    })
    vi.stubGlobal('fetch', fetchMock)

    let container!: HTMLElement
    await act(async () => { container = renderMemoryTabWithPendingProbe().container })
    await waitFor(() => expect(container.querySelector('[data-testid="pending-memory-count"]')).toHaveTextContent('2'))
    await openAccordion(container)
    const editBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const saveBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-save-btn"]')
    expect(saveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(saveBtn!) })
    await waitFor(() => expect(container.querySelector('[data-testid="pending-memory-count"]')).toHaveTextContent('1'))
  })

  it('ac3 regression: pending hard-delete decrements pending memory count immediately', async () => {
    const pending = makeEntry({ id: 'e1', state: 'pending' })
    const otherPending = makeEntry({ id: 'e2', state: 'pending', title: 'Other pending' })
    let entries = [pending, otherPending]
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === 'POST' && url === '/api/memories/e1/delete') {
        entries = [otherPending]
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ success: true }) })
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(makeApiResponse(entries)) })
    })
    vi.stubGlobal('fetch', fetchMock)

    let container!: HTMLElement
    await act(async () => { container = renderMemoryTabWithPendingProbe().container })
    await waitFor(() => expect(container.querySelector('[data-testid="pending-memory-count"]')).toHaveTextContent('2'))
    await openAccordion(container)
    const deleteBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-btn"]')
    expect(deleteBtn).not.toBeNull()
    await act(async () => { fireEvent.click(deleteBtn!) })
    await flush()
    const confirmBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-confirm-btn"]')
    expect(confirmBtn).not.toBeNull()
    await act(async () => { fireEvent.click(confirmBtn!) })
    await waitFor(() => expect(container.querySelector('[data-testid="pending-memory-count"]')).toHaveTextContent('1'))
  })
})

// ─── AC7 (retry #1659): Approved-state delete uses soft-delete modal copy ────
//
// Reviewer gap: MemoryTab_1672 suite only exercised pending and curated delete
// dialogs. A regression removing the approved-entry delete affordance, or swapping
// to the hard-delete copy, would still pass the existing suite.
//
// Contract (MemoryTab.tsx:785,943-945):
//   - Delete button is visible for any non-deleted entry (including approved).
//   - Confirmation dialog uses the soft-delete branch for non-pending states.

describe('MemoryApprovedDelete', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac7 retry: Delete button is visible inside open accordion for approved entry', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'approved' })])
    await openAccordion(container)
    expect(container.querySelector('[data-testid="memory-delete-btn"]')).not.toBeNull()
  })

  it('ac7 retry: clicking Delete on approved entry opens the delete confirmation dialog', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'approved' })])
    await openAccordion(container)
    const deleteBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-btn"]')
    expect(deleteBtn).not.toBeNull()
    await act(async () => { fireEvent.click(deleteBtn!) })
    await flush()
    expect(container.querySelector('[data-testid="memory-delete-confirm-dialog"]')).not.toBeNull()
  })

  it('ac7 retry: approved delete dialog uses soft-delete copy, not permanent hard-delete copy', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'approved' })])
    await openAccordion(container)
    const deleteBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-btn"]')
    expect(deleteBtn).not.toBeNull()
    await act(async () => { fireEvent.click(deleteBtn!) })
    await flush()
    const dialog = container.querySelector('[data-testid="memory-delete-confirm-dialog"]')
    expect(dialog).not.toBeNull()
    // Soft-delete branch: "This will soft-delete the memory and mark it as deleted."
    expect(dialog!.textContent?.toLowerCase()).toMatch(/soft.?delete|mark it as deleted/)
    // Must NOT use the permanent hard-delete copy reserved for pending entries
    expect(dialog!.textContent?.toLowerCase()).not.toContain('permanent')
  })

  it('ac7 retry: approved delete dialog contains the confirm button', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'approved' })])
    await openAccordion(container)
    const deleteBtn = container.querySelector<HTMLElement>('[data-testid="memory-delete-btn"]')
    expect(deleteBtn).not.toBeNull()
    await act(async () => { fireEvent.click(deleteBtn!) })
    await flush()
    expect(container.querySelector('[data-testid="memory-delete-confirm-btn"]')).not.toBeNull()
  })
})

// ─── AC8 (retry #1659): Edit of approved entry downgrades state to curated ───
//
// Reviewer gap: backend and engine tests prove the approved→curated downgrade,
// and the UI shows the "Editing will require re-approval" warning, but no
// MemoryTab test starts from an approved entry, saves, and asserts the visible
// state transitions to curated in the frontend.
//
// Contract (MemoryTab.tsx:580-594): save path is generic — it replaces the
// local entry state with the API response entry. Backend returns state=curated
// for an approved-entry edit (test_cockpit_memory_routes_1670.py:337).

describe('MemoryApprovedEditDowngrade', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac8 retry: approved entry has an Edit button', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'e1', state: 'approved' })])
    await openAccordion(container)
    expect(container.querySelector('[data-testid="memory-edit-btn"]')).not.toBeNull()
  })

  it('ac8 retry: saving edit of approved entry with state=curated response updates state badge to curated', async () => {
    const original = makeEntry({ id: 'e1', state: 'approved' })
    const downgraded = { ...original, state: 'curated' as MemoryState }
    vi.stubGlobal('fetch', makeMutationFetch(200, { entry: downgraded }, makeApiResponse([original])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const saveBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-save-btn"]')
    expect(saveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(saveBtn!) })
    await flush()
    const entryEl = container.querySelector('[data-testid="memory-entry"]')
    expect(entryEl?.className).toContain('border-l-info')
  })

  it('ac8 retry: state badge is NOT approved after saving edit of approved entry', async () => {
    const original = makeEntry({ id: 'e1', state: 'approved' })
    const downgraded = { ...original, state: 'curated' as MemoryState }
    vi.stubGlobal('fetch', makeMutationFetch(200, { entry: downgraded }, makeApiResponse([original])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const saveBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-save-btn"]')
    expect(saveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(saveBtn!) })
    await flush()
    const entryEl = container.querySelector('[data-testid="memory-entry"]')
    expect(entryEl?.className).not.toContain('border-l-success')
  })

  it('ac8 retry: Approve button appears after approved-entry edit downgrades state to curated', async () => {
    const original = makeEntry({ id: 'e1', state: 'approved' })
    const downgraded = { ...original, state: 'curated' as MemoryState }
    vi.stubGlobal('fetch', makeMutationFetch(200, { entry: downgraded }, makeApiResponse([original])))
    let container!: HTMLElement
    await act(async () => { container = renderMemoryTab().container })
    await flush()
    await openAccordion(container)
    const editBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-btn"]')
    expect(editBtn).not.toBeNull()
    await act(async () => { fireEvent.click(editBtn!) })
    await flush()
    const saveBtn = container.querySelector<HTMLElement>('[data-testid="memory-edit-save-btn"]')
    expect(saveBtn).not.toBeNull()
    await act(async () => { fireEvent.click(saveBtn!) })
    await flush()
    // After downgrade to curated, Approve button should now be visible
    expect(container.querySelector('[data-testid="memory-approve-btn"]')).not.toBeNull()
  })
})

// ─── AC1 (cycle-3): Exhaustive metadata field proof ───────────────────────────
//
// Reviewer gap: task-local proof would not fail if the accordion detail dropped
// id, scope_agents, categories, state, or the approved_at '-' fallback.
// The prior retry proved approved_at (date present) but not the other fields or
// the null fallback.  Source renders all 9 metadata fields at MemoryTab.tsx:701-709.

describe('MemoryMetadataFields', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 cycle3: accordion detail renders the entry id value', async () => {
    const container = await renderWithEntries([makeEntry({ id: 'unique-entry-id-99' })])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('unique-entry-id-99')
  })

  it('ac1 cycle3: accordion detail renders scope_agents as comma-joined list when non-empty', async () => {
    const container = await renderWithEntries([
      makeEntry({ scope_agents: ['builder', 'reviewer'] }),
    ])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('builder')
    expect(detail?.textContent).toContain('reviewer')
  })

  it('ac1 cycle3: accordion detail renders "All agents" for scope_agents when list is empty', async () => {
    const container = await renderWithEntries([makeEntry({ scope_agents: [] })])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('All agents')
  })

  it('ac1 cycle3: accordion detail renders categories as comma-joined list', async () => {
    const container = await renderWithEntries([
      makeEntry({ categories: ['behaviour', 'pitfall'] }),
    ])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('behaviour')
    expect(detail?.textContent).toContain('pitfall')
  })

  it('ac1 cycle3: accordion detail renders the entry state value', async () => {
    const container = await renderWithEntries([makeEntry({ state: 'curated' })])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('curated')
  })

  it('ac1 cycle3: accordion detail renders "-" for approved_at when null', async () => {
    const container = await renderWithEntries([makeEntry({ approved_at: null })])
    await openAccordion(container)
    const detail = container.querySelector('[data-testid="memory-accordion-detail"]')
    expect(detail?.textContent).toContain('-')
  })
})

// ─── AC3 (cycle-3): Nav badge hidden at zero pending count ────────────────────
//
// Reviewer gap: existing suite only tests the positive (count > 0) path.
// When pending count is 0, [data-testid="nav-badge"] must NOT appear on the
// memory nav button (Shell uses {badgeCount > 0 ? <span ...> : null}).

describe('MemoryNavBadgeZero', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac3 cycle3: memory nav button has no nav-badge when pending count is 0', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        if (typeof _url === 'string' && _url.includes('/api/memories')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(makeApiResponse([])),
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
    const { container } = renderShell('/')
    await flush()
    const btn = memoryBtn(container)
    expect(btn).not.toBeNull()
    // When count is 0, Shell renders null for the badge span — it must be absent
    expect(btn!.querySelector('[data-testid="nav-badge"]')).toBeNull()
  })
})

// ─── AC4 (cycle-3): OCC banner exact copy with em-dash ───────────────────────
//
// Reviewer gap: existing tests assert the substring 'Entry was modified' which
// passes even when the source uses an ASCII hyphen instead of the AC-specified
// em-dash (U+2014). This test asserts the EXACT string from the AC.
//
// RED expectation: FAILS against the current source because MemoryTab.tsx:477
// emits 'Entry was modified - refreshing' (ASCII hyphen '-').
// Builder must change that literal to 'Entry was modified \u2014 refreshing'.

describe('MemoryOCCExactCopy', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac4 cycle3: 409 OCC banner text matches exact AC string with em-dash (U+2014)', async () => {
    const entry = makeEntry({ id: 'e1', state: 'curated' })
    vi.stubGlobal('fetch', makeMutationFetch(409, { detail: 'conflict' }, makeApiResponse([entry])))
    let container!: HTMLElement
    await act(async () => {
      container = renderMemoryTab().container
    })
    await flush()
    await openAccordion(container)
    const approveBtn = container.querySelector('[data-testid="memory-approve-btn"]')
    if (approveBtn) {
      await act(async () => {
        fireEvent.click(approveBtn)
      })
      await flush()
    }
    const banner = container.querySelector('[data-testid="memory-occ-banner"]')
    // AC specifies em-dash: 'Entry was modified \u2014 refreshing'
    // Source currently uses hyphen — this test intentionally fails until builder fixes the literal
    expect(banner?.textContent).toBe('Entry was modified \u2014 refreshing')
  })
})
