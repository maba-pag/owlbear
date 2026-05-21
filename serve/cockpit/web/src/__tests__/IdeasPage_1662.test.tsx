/**
 * Task #1662 — P2-01: IdeasPage core — edit mode, API client, save, dirty state
 *
 * AC1: IdeasPage renders a loading indicator while GET `/api/ideas` is pending;
 *      textarea is not present in DOM
 * AC2: IdeasPage renders a preview populated with content from successful
 *      GET `/api/ideas` response, then exposes focused edit mode on request.
 * AC3: IdeasPage save button sends PUT `/api/ideas` with textarea value; disabled
 *      when textarea value equals last-saved baseline
 * AC4: IdeasPage dirty indicator visible when textarea value differs from last-saved
 *      baseline; hidden after successful PUT
 * AC5: IdeasPage textarea renders placeholder 'Capture ideas here...' when content
 *      is empty string
 * AC6: Cmd+S / Ctrl+S shortcut in IdeasPage sends PUT `/api/ideas` when content is
 *      dirty; no-op when content matches baseline
 * AC7: IdeasPage renders error state when GET `/api/ideas` returns non-2xx; PUT
 *      failure preserves textarea content, re-enables save button, and subsequent
 *      button click or Cmd/Ctrl+S issues a new PUT `/api/ideas`
 * AC8: Route config entry in routes.ts: path `/ideas`, label `Ideas`, icon `ideas`,
 *      component lazy-loaded IdeasPage
 *
 * RED phase: src/pages/IdeasPage.tsx does not exist → import fails, all tests fail.
 * routeConfig has no /ideas entry → all route assertions fail.
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, act } from '@testing-library/react'
import { Suspense, type ComponentType } from 'react'
import { routeConfig } from '../routes'
import IdeasPage from '../pages/IdeasPage'

// ─── Fetch mock factories ──────────────────────────────────────────────────────

/** GET resolves immediately with given content string; no PUT call expected. */
function makeGetOkFetch(content = '') {
  return vi.fn((_url: string, _init?: RequestInit) =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ content }),
    }),
  )
}

/** GET and PUT both resolve successfully (PUT returns 204). */
function makeGetOkPutOkFetch(content = '') {
  return vi.fn((_url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') {
      return Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ content }),
    })
  })
}

/** GET resolves successfully; PUT returns error status. */
function makeGetOkPutErrorFetch(content = '', putStatus = 500) {
  return vi.fn((_url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') {
      return Promise.resolve({
        ok: false,
        status: putStatus,
        json: () => Promise.resolve({ detail: 'Save failed' }),
      })
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ content }),
    })
  })
}

/** GET returns non-2xx status. */
function makeGetErrorFetch(status = 500) {
  return vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve({ detail: 'Server error' }),
    }),
  )
}

/** GET never resolves — simulates in-flight request. */
function makeGetPendingFetch() {
  return vi.fn(() => new Promise<never>(() => {}))
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderIdeasPage() {
  return render(<IdeasPage />)
}

// ─── Utilities ────────────────────────────────────────────────────────────────

async function flush() {
  await act(async () => {
    await Promise.resolve()
  })
}

async function enterEditMode(container: HTMLElement) {
  if (container.querySelector('textarea')) {
    return
  }

  const toggle = container.querySelector<HTMLButtonElement>('[data-testid="ideas-preview-toggle"]')
  expect(toggle).not.toBeNull()
  await act(async () => {
    fireEvent.click(toggle!)
  })
  await flush()
}

/** Render IdeasPage, wait for the fetch to complete, return the preview-mode container. */
async function renderPreviewLoaded(content = 'Some ideas here') {
  vi.stubGlobal('fetch', makeGetOkFetch(content))
  let container!: HTMLElement
  await act(async () => {
    container = renderIdeasPage().container
  })
  await flush()
  return container
}

/** Render IdeasPage, wait for the fetch to complete, enter edit mode, return the container. */
async function renderLoaded(content = 'Some ideas here') {
  const container = await renderPreviewLoaded(content)
  await enterEditMode(container)
  return container
}

/** Render loaded, then change textarea value. Returns { container, textarea }. */
async function renderDirty(initialContent = 'initial', newContent = 'changed') {
  const container = await renderLoaded(initialContent)
  const textarea = container.querySelector('textarea')
  if (textarea) {
    fireEvent.change(textarea, { target: { value: newContent } })
  }
  return { container, textarea }
}

// ─── AC8: Route config entry ──────────────────────────────────────────────────

describe('TestFromAC_IdeasPageRoute', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac8 happy: routeConfig contains an entry with path "/ideas"', () => {
    const paths = routeConfig.map((e) => e.path)
    expect(paths).toContain('/ideas')
  })

  it('ac8 happy: /ideas route entry has label "Ideas"', () => {
    const entry = routeConfig.find((e) => e.path === '/ideas')
    expect(entry?.label).toBe('Ideas')
  })

  it('ac8 happy: /ideas route entry has icon "ideas"', () => {
    const entry = routeConfig.find((e) => e.path === '/ideas')
    expect(entry?.icon).toBe('ideas')
  })

  it('ac8 happy: /ideas route component is a React.lazy wrapper', () => {
    const entry = routeConfig.find((e) => e.path === '/ideas')
    // React.lazy() objects carry $$typeof === Symbol.for('react.lazy')
    expect((entry?.component as { $$typeof?: symbol })?.$$typeof).toBe(
      Symbol.for('react.lazy'),
    )
  })

  it('ac8 happy: /ideas route component renders IdeasPage-specific DOM when rendered (binding proof)', async () => {
    // Prove the /ideas entry is wired to IdeasPage specifically:
    // a different lazy component would not render data-testid="ideas-loading".
    vi.stubGlobal('fetch', makeGetPendingFetch())
    const entry = routeConfig.find((e) => e.path === '/ideas')
    const RouteComponent = entry!.component as unknown as ComponentType<Record<string, never>>
    let container!: HTMLElement
    await act(async () => {
      const result = render(
        <Suspense fallback={<div>Suspense fallback</div>}>
          <RouteComponent />
        </Suspense>,
      )
      container = result.container
    })
    await flush()
    expect(container.querySelector('[data-testid="ideas-loading"]')).not.toBeNull()
  })
})

// ─── AC1: Loading state ───────────────────────────────────────────────────────

describe('TestFromAC_IdeasPageLoading', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 happy: shows data-testid="ideas-loading" while GET /api/ideas is in-flight', async () => {
    vi.stubGlobal('fetch', makeGetPendingFetch())
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    expect(container.querySelector('[data-testid="ideas-loading"]')).not.toBeNull()
  })

  it('ac1 happy: textarea is absent from DOM while GET /api/ideas is pending', async () => {
    vi.stubGlobal('fetch', makeGetPendingFetch())
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    expect(container.querySelector('textarea')).toBeNull()
  })

  it('ac1 edge: loading indicator is absent after GET /api/ideas resolves', async () => {
    const container = await renderLoaded()
    expect(container.querySelector('[data-testid="ideas-loading"]')).toBeNull()
  })
})

// ─── AC2: Loaded state — preview first, edit on request ──────────────────────

describe('TestFromAC_IdeasPageLoaded', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac2 happy: renders preview after successful GET /api/ideas', async () => {
    const container = await renderPreviewLoaded('Hello world')
    expect(container.querySelector('[data-testid="ideas-preview"]')).not.toBeNull()
    expect(container.querySelector('textarea')).toBeNull()
  })

  it('ac2 happy: entering edit mode shows textarea with content from GET /api/ideas response', async () => {
    const content = 'My brilliant ideas\n\nLine two'
    const container = await renderLoaded(content)
    const textarea = container.querySelector('textarea')
    expect(textarea?.value).toBe(content)
  })

  it('ac2 happy: textarea is focused after entering edit mode', async () => {
    const container = await renderLoaded('Content here')
    const textarea = container.querySelector('textarea')
    expect(document.activeElement).toBe(textarea)
  })

  it('ac2 happy: GET fetch targets exactly /api/ideas (not another endpoint)', async () => {
    const fetchMock = makeGetOkFetch('hello')
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    void container
    const getCalls = fetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit | undefined]) => !init?.method || init.method === 'GET',
    )
    expect(getCalls.length).toBeGreaterThan(0)
    expect(getCalls[0][0]).toBe('/api/ideas')
  })
})

// ─── AC3: Save button — PUT request and disabled-when-clean ──────────────────

describe('TestFromAC_IdeasPageSave', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac3 happy: save button sends PUT to /api/ideas', async () => {
    const fetchMock = makeGetOkPutOkFetch('initial')
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'changed' } })
    }
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    if (saveBtn) {
      await act(async () => {
        fireEvent.click(saveBtn)
      })
      await flush()
    }
    const putCalls = fetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBeGreaterThan(0)
  })

  it('ac3 happy: PUT /api/ideas body contains textarea value as JSON content field', async () => {
    const fetchMock = makeGetOkPutOkFetch('initial')
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'new content' } })
    }
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    if (saveBtn) {
      await act(async () => {
        fireEvent.click(saveBtn)
      })
      await flush()
    }
    const putCall = fetchMock.mock.calls.find(
      ([, init]: [string, RequestInit]) => init?.method === 'PUT',
    )
    expect(putCall).toBeDefined()
    const body = JSON.parse(putCall![1].body as string) as Record<string, unknown>
    expect(body.content).toBe('new content')
  })

  it('ac3 boundary: save button is disabled when textarea value equals last-saved baseline', async () => {
    const container = await renderLoaded('same content')
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    // Textarea value === fetched content (baseline) → button must be disabled
    expect(saveBtn?.disabled).toBe(true)
  })

  it('ac3 happy: save button is enabled when textarea value differs from last-saved baseline', async () => {
    const { container } = await renderDirty('initial', 'changed')
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(false)
  })

  it('ac3 happy: PUT fetch targets exactly /api/ideas (not another endpoint)', async () => {
    const fetchMock = makeGetOkPutOkFetch('initial')
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'changed' } })
    }
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    if (saveBtn) {
      await act(async () => {
        fireEvent.click(saveBtn)
      })
      await flush()
    }
    const putCalls = fetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBeGreaterThan(0)
    expect(putCalls[0][0]).toBe('/api/ideas')
  })
})

// ─── AC4: Dirty indicator ─────────────────────────────────────────────────────

describe('TestFromAC_IdeasPageDirtyState', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac4 happy: dirty indicator absent when content matches last-saved baseline', async () => {
    const container = await renderLoaded('unchanged')
    expect(container.querySelector('[data-testid="ideas-dirty"]')).toBeNull()
  })

  it('ac4 happy: dirty indicator visible when textarea value differs from baseline', async () => {
    const { container } = await renderDirty('original', 'modified')
    expect(container.querySelector('[data-testid="ideas-dirty"]')).not.toBeNull()
  })

  it('ac4 happy: dirty indicator hidden after successful PUT /api/ideas', async () => {
    const fetchMock = makeGetOkPutOkFetch('initial')
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'modified' } })
    }
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    await act(async () => {
      if (saveBtn) fireEvent.click(saveBtn)
    })
    await flush()
    expect(container.querySelector('[data-testid="ideas-dirty"]')).toBeNull()
  })
})

// ─── AC5: Placeholder text ────────────────────────────────────────────────────

describe('TestFromAC_IdeasPagePlaceholder', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac5 happy: textarea placeholder is "Capture ideas here..." when content is empty string', async () => {
    const container = await renderLoaded('')
    const textarea = container.querySelector('textarea')
    expect(textarea?.placeholder).toBe('Capture ideas here...')
  })

  it('ac5 boundary: placeholder is present regardless of fetched content length', async () => {
    const container = await renderLoaded('some content')
    const textarea = container.querySelector('textarea')
    // Placeholder exists as an attribute even when content is non-empty
    expect(textarea?.getAttribute('placeholder')).toBe('Capture ideas here...')
  })
})

// ─── AC6: Keyboard shortcut (Cmd+S / Ctrl+S) ─────────────────────────────────

describe('TestFromAC_IdeasPageKeyboardShortcut', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac6 happy: Cmd+S triggers PUT /api/ideas when content is dirty', async () => {
    const fetchMock = makeGetOkPutOkFetch('initial')
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'changed' } })
    }
    await act(async () => {
      fireEvent.keyDown(document, { key: 's', code: 'KeyS', metaKey: true })
    })
    await flush()
    const putCalls = fetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBe(1)
  })

  it('ac6 happy: Ctrl+S triggers PUT /api/ideas when content is dirty', async () => {
    const fetchMock = makeGetOkPutOkFetch('initial')
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'changed' } })
    }
    await act(async () => {
      fireEvent.keyDown(document, { key: 's', code: 'KeyS', ctrlKey: true })
    })
    await flush()
    const putCalls = fetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBe(1)
  })

  it('ac6 boundary: Cmd+S is a no-op when content matches baseline (clean state)', async () => {
    const fetchMock = makeGetOkFetch('unchanged')
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    void container
    await act(async () => {
      fireEvent.keyDown(document, { key: 's', code: 'KeyS', metaKey: true })
    })
    await flush()
    const putCalls = fetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBe(0)
  })
})

// ─── AC7: Error states ────────────────────────────────────────────────────────

describe('TestFromAC_IdeasPageError', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac7 error: renders data-testid="ideas-error" when GET /api/ideas returns non-2xx', async () => {
    vi.stubGlobal('fetch', makeGetErrorFetch(500))
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    expect(container.querySelector('[data-testid="ideas-error"]')).not.toBeNull()
  })

  it('ac7 error: textarea is absent from DOM when GET /api/ideas fails', async () => {
    vi.stubGlobal('fetch', makeGetErrorFetch(404))
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    expect(container.querySelector('textarea')).toBeNull()
  })

  it('ac7 error: PUT failure preserves textarea content (value unchanged after failed save)', async () => {
    const fetchMock = makeGetOkPutErrorFetch('original text', 500)
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'modified text' } })
    }
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    await act(async () => {
      if (saveBtn) fireEvent.click(saveBtn)
    })
    await flush()
    const textareaAfter = container.querySelector('textarea')
    expect(textareaAfter?.value).toBe('modified text')
  })

  it('ac7 error: save button is re-enabled after PUT failure', async () => {
    const fetchMock = makeGetOkPutErrorFetch('original', 500)
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'changed' } })
    }
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    await act(async () => {
      if (saveBtn) fireEvent.click(saveBtn)
    })
    await flush()
    const saveBtnAfter = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtnAfter?.disabled).toBe(false)
  })

  it('ac7 retry: button click after failed PUT issues a second PUT /api/ideas', async () => {
    const fetchMock = makeGetOkPutErrorFetch('original text', 500)
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'modified text' } })
    }
    // First save attempt — PUT fails, errorMessage set
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    await act(async () => {
      if (saveBtn) fireEvent.click(saveBtn)
    })
    await flush()
    // Second save attempt — must issue another PUT to /api/ideas
    const saveBtnAfter = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    await act(async () => {
      if (saveBtnAfter) fireEvent.click(saveBtnAfter)
    })
    await flush()
    const putCalls = fetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBe(2)
    expect(putCalls[1][0]).toBe('/api/ideas')
  })

  it('ac7 retry: Cmd+S after failed PUT issues a second PUT /api/ideas', async () => {
    const fetchMock = makeGetOkPutErrorFetch('original text', 500)
    vi.stubGlobal('fetch', fetchMock)
    let container!: HTMLElement
    await act(async () => {
      container = renderIdeasPage().container
    })
    await flush()
    await enterEditMode(container)
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'modified text' } })
    }
    // First save via Cmd+S — PUT fails, errorMessage set
    await act(async () => {
      fireEvent.keyDown(document, { key: 's', code: 'KeyS', metaKey: true })
    })
    await flush()
    // Second save via Cmd+S — must issue another PUT to /api/ideas
    await act(async () => {
      fireEvent.keyDown(document, { key: 's', code: 'KeyS', metaKey: true })
    })
    await flush()
    const putCalls = fetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBe(2)
    expect(putCalls[1][0]).toBe('/api/ideas')
  })
})
