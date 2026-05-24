/**
 * Consolidation integration test — Ideas Notebook end-to-end (task #1666)
 *
 * Cross-feature integration across all Ideas Notebook subtasks:
 *   #1662 — core edit/save/dirty state
 *   #1663 — markdown preview toggle
 *   #1664 — unsaved-changes navigation guard
 *   #1665 — external-edit awareness and conflict resolution
 *
 * Durable file: no task-ID suffix — maintained by test-curator after archival.
 * Use descriptive describe names; do NOT use TestFromAC_ prefix here.
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, act, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider, useNavigate } from 'react-router'
import IdeasPage from '../pages/IdeasPage'

// ─── Fetch mock factories ──────────────────────────────────────────────────────

function timestampMinutesAgo(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString()
}

/** GET resolves with content and saved metadata; PUT resolves 204. */
function makeGetOkPutOkFetch(content: string) {
  const updatedAt = timestampMinutesAgo(3)
  return vi.fn((_url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') {
      return Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ content, updated_at: updatedAt }),
    })
  })
}

/** GET only — resolves with content and saved metadata. */
function makeGetOkFetch(content: string) {
  const updatedAt = timestampMinutesAgo(3)
  return vi.fn((_url: string, _init?: RequestInit) =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ content, updated_at: updatedAt }),
    }),
  )
}

// ─── Navigation helper ────────────────────────────────────────────────────────

function NavButton({ to, testId }: { to: string; testId: string }) {
  const navigate = useNavigate()
  return <button type="button" data-testid={testId} onClick={() => navigate(to)} />
}

// ─── Render helpers ───────────────────────────────────────────────────────────

function renderInRouter() {
  const router = createMemoryRouter([
    {
      path: '/ideas',
      element: (
        <>
          <IdeasPage />
          <NavButton to="/" testId="nav-home" />
        </>
      ),
    },
    { path: '/', element: <div data-testid="home-page">Home</div> },
  ], { initialEntries: ['/ideas'] })

  return render(
    <RouterProvider router={router} />,
  )
}

async function flush(): Promise<void> {
  await act(async () => {
    await Promise.resolve()
  })
}

async function enterEditMode(container: HTMLElement): Promise<void> {
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

/** Render in router context and wait for GET /api/ideas to settle. */
async function renderPreviewLoaded(content: string): Promise<ReturnType<typeof renderInRouter>> {
  vi.stubGlobal('fetch', makeGetOkFetch(content))
  let result!: ReturnType<typeof renderInRouter>
  await act(async () => {
    result = renderInRouter()
  })
  await flush()
  return result
}

/** Render in router context and wait for GET /api/ideas to settle. */
async function renderLoaded(content: string): Promise<ReturnType<typeof renderInRouter>> {
  vi.stubGlobal('fetch', makeGetOkFetch(content))
  let result!: ReturnType<typeof renderInRouter>
  await act(async () => {
    result = renderInRouter()
  })
  await flush()
  await enterEditMode(result.container)
  return result
}

/**
 * Render loaded, edit textarea to make dirty, then trigger a successful save.
 * After this, isDirty is false (content === lastSavedContent === editedContent).
 */
async function renderAfterSave(
  initialContent: string,
  editedContent: string,
): Promise<ReturnType<typeof renderInRouter>> {
  vi.stubGlobal('fetch', makeGetOkPutOkFetch(initialContent))
  let result!: ReturnType<typeof renderInRouter>
  await act(async () => {
    result = renderInRouter()
  })
  await flush()
  await enterEditMode(result.container)

  const textarea = result.container.querySelector('textarea')!
  fireEvent.change(textarea, { target: { value: editedContent } })

  const saveBtn = result.container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')!
  await act(async () => {
    fireEvent.click(saveBtn)
  })
  await flush()

  return result
}

function setVisibilityState(state: 'visible' | 'hidden'): void {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => state,
  })
}

// ─── AC1: End-to-end save flow ────────────────────────────────────────────────
//
// IdeasPage loads content from GET /api/ideas, user edits textarea,
// PUT /api/ideas succeeds; dirty indicator (data-testid="ideas-dirty") disappears
// and save button (data-testid="ideas-save") becomes disabled.

describe('IdeasPageIntegration_SaveFlow', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 happy: textarea is populated with content from GET /api/ideas on load', async () => {
    const { container } = await renderLoaded('initial server content')
    expect(container.querySelector('textarea')?.value).toBe('initial server content')
  })

  it('ac1 happy: editing textarea makes the dirty indicator appear', async () => {
    const { container } = await renderLoaded('base')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'edited' } })
    expect(container.querySelector('[data-testid="ideas-dirty"]')).not.toBeNull()
  })

  it('ac1 happy: save button is enabled when textarea value differs from last-saved baseline', async () => {
    const { container } = await renderLoaded('base')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'changed' } })
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(false)
  })

  it('ac1 happy: dirty indicator disappears after PUT /api/ideas succeeds', async () => {
    const { container } = await renderAfterSave('initial', '# Updated heading')
    expect(container.querySelector('[data-testid="ideas-dirty"]')).toBeNull()
  })

  it('ac1 happy: save button is disabled after PUT /api/ideas succeeds', async () => {
    const { container } = await renderAfterSave('initial', 'updated content')
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })

  it('ac1 happy: PUT /api/ideas is called with the current textarea value in the request body', async () => {
    const mockFetch = makeGetOkPutOkFetch('original')
    vi.stubGlobal('fetch', mockFetch)
    let result!: ReturnType<typeof renderInRouter>
    await act(async () => {
      result = renderInRouter()
    })
    await flush()
    await enterEditMode(result.container)

    fireEvent.change(result.container.querySelector('textarea')!, {
      target: { value: '# My saved ideas' },
    })
    await act(async () => {
      fireEvent.click(result.container.querySelector('[data-testid="ideas-save"]')!)
    })
    await flush()

    const putCall = mockFetch.mock.calls.find(
      ([, init]: [string, RequestInit | undefined]) => init?.method === 'PUT',
    )
    expect(putCall).toBeDefined()
    const body = JSON.parse(putCall![1]!.body as string) as { content: string }
    expect(body.content).toBe('# My saved ideas')
  })

  it('ac1 edge: save button is disabled when textarea equals the last-saved baseline (clean)', async () => {
    const { container } = await renderLoaded('same content')
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })

  it('ac1 boundary: dirty indicator is absent when textarea content equals the last-saved baseline', async () => {
    const { container } = await renderLoaded('matching')
    expect(container.querySelector('[data-testid="ideas-dirty"]')).toBeNull()
  })
})

// ─── AC2: Preview after save ──────────────────────────────────────────────────
//
// After successful PUT round-trip, toggling to preview renders the saved content
// as HTML within data-testid="ideas-preview" (markdown heading renders as <h1>).

describe('IdeasPageIntegration_PreviewAfterSave', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac2 happy: toggling to preview after save renders saved content as <h1> in ideas-preview', async () => {
    const { container } = await renderAfterSave('# Old Heading', '# Saved Heading')
    const toggle = container.querySelector<HTMLButtonElement>('[data-testid="ideas-preview-toggle"]')!
    await act(async () => {
      fireEvent.click(toggle)
    })
    await flush()
    const preview = container.querySelector('[data-testid="ideas-preview"]')
    expect(preview).not.toBeNull()
    expect(preview?.querySelector('h1')).not.toBeNull()
  })

  it('ac2 happy: preview renders the SAVED content not the originally loaded content', async () => {
    const { container } = await renderAfterSave('# Original', '# Saved')
    const toggle = container.querySelector<HTMLButtonElement>('[data-testid="ideas-preview-toggle"]')!
    await act(async () => {
      fireEvent.click(toggle)
    })
    await flush()
    const h1 = container.querySelector('[data-testid="ideas-preview"] h1')
    // Must reflect saved edit, not original loaded string
    expect(h1?.textContent).toContain('Saved')
    expect(h1?.textContent).not.toContain('Original')
  })

  it('ac2 edge: preview container appears after toggle even when content is empty after save', async () => {
    const { container } = await renderAfterSave('some content', '')
    const toggle = container.querySelector<HTMLButtonElement>('[data-testid="ideas-preview-toggle"]')!
    await act(async () => {
      fireEvent.click(toggle)
    })
    await flush()
    expect(container.querySelector('[data-testid="ideas-preview"]')).not.toBeNull()
  })

  it('ac2 boundary: preview toggle is present immediately after a successful save', async () => {
    const { container } = await renderAfterSave('initial', 'edited')
    expect(container.querySelector('[data-testid="ideas-preview-toggle"]')).not.toBeNull()
  })
})

describe('IdeasPageIntegration_ScrollAffordance', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a subtle continuation cue when the markdown preview has more content below', async () => {
    const { container } = await renderPreviewLoaded('# Notes\n\n'.repeat(20))
    const preview = container.querySelector('[data-testid="ideas-preview"]') as HTMLElement | null
    expect(preview).not.toBeNull()
    Object.defineProperty(preview!, 'scrollHeight', { configurable: true, value: 800 })
    Object.defineProperty(preview!, 'clientHeight', { configurable: true, value: 300 })
    Object.defineProperty(preview!, 'scrollTop', { configurable: true, value: 0 })

    await act(async () => {
      fireEvent.scroll(preview!)
    })

    const cue = container.querySelector('[data-testid="ideas-scroll-cue"]')
    expect(cue).not.toBeNull()
    expect(cue?.getAttribute('class') ?? '').toContain('absolute')
    expect(cue?.getAttribute('class') ?? '').toContain('bottom-0')
  })

  it('hides the continuation cue when the active Ideas surface reaches the bottom', async () => {
    const { container } = await renderPreviewLoaded('# Notes\n\n'.repeat(20))
    const preview = container.querySelector('[data-testid="ideas-preview"]') as HTMLElement | null
    expect(preview).not.toBeNull()
    Object.defineProperty(preview!, 'scrollHeight', { configurable: true, value: 800 })
    Object.defineProperty(preview!, 'clientHeight', { configurable: true, value: 300 })
    Object.defineProperty(preview!, 'scrollTop', { configurable: true, value: 500 })

    await act(async () => {
      fireEvent.scroll(preview!)
    })

    expect(container.querySelector('[data-testid="ideas-scroll-cue"]')).toBeNull()
  })

  it('tracks the native editor textarea as the active Ideas scroll surface', async () => {
    const { container } = await renderLoaded('draft\n'.repeat(80))
    const textarea = container.querySelector('textarea') as HTMLTextAreaElement | null
    expect(textarea).not.toBeNull()
    Object.defineProperty(textarea!, 'scrollHeight', { configurable: true, value: 1200 })
    Object.defineProperty(textarea!, 'clientHeight', { configurable: true, value: 400 })
    Object.defineProperty(textarea!, 'scrollTop', { configurable: true, value: 0 })

    await act(async () => {
      fireEvent.scroll(textarea!)
    })

    expect(container.querySelector('[data-testid="ideas-scroll-cue"]')).not.toBeNull()
  })
})

// ─── AC3: Guard after save ────────────────────────────────────────────────────
//
// After a successful save clears dirty state, route navigation proceeds without
// the unsaved-changes alertdialog appearing.

describe('IdeasPageIntegration_GuardAfterSave', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac3 happy: navigation proceeds without alertdialog after a successful save', async () => {
    const { container } = await renderAfterSave('initial', 'saved edits')
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="home-page"]')).not.toBeNull()
    })
    expect(container.querySelector('[role="alertdialog"]')).toBeNull()
  })

  it('ac3 happy: home page renders immediately after navigation following a save', async () => {
    const { container } = await renderAfterSave('initial', 'saved')
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="home-page"]')).not.toBeNull()
    })
  })

  it('ac3 regression: alertdialog DOES appear when navigating while still dirty (no save)', async () => {
    const { container } = await renderLoaded('base')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'unsaved' } })
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[role="alertdialog"]')).not.toBeNull()
    })
  })

  it('keeps the user on Ideas when cancelling a dirty navigation', async () => {
    const { container } = await renderLoaded('base')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'unsaved' } })
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="ideas-unsaved-dialog"]')).not.toBeNull()
    })

    fireEvent.click(container.querySelector('[data-testid="ideas-unsaved-cancel"]')!)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="ideas-unsaved-dialog"]')).toBeNull()
    })
    expect(container.querySelector('[data-testid="ideas-editor-shell"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="home-page"]')).toBeNull()
  })

  it('continues the blocked navigation when the user confirms leaving Ideas', async () => {
    const { container } = await renderLoaded('base')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'unsaved' } })
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="ideas-unsaved-dialog"]')).not.toBeNull()
    })

    fireEvent.click(container.querySelector('[data-testid="ideas-unsaved-leave"]')!)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="home-page"]')).not.toBeNull()
    })
    expect(container.querySelector('[data-testid="ideas-unsaved-dialog"]')).toBeNull()
  })
})

describe('IdeasPageIntegration_PdsControls', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders editor commands as PDS buttons while keeping the markdown textarea native', async () => {
    const { container } = await renderLoaded('base')
    const previewToggle = container.querySelector<HTMLElement & { icon?: string }>('[data-testid="ideas-preview-toggle"]')
    const saveButton = container.querySelector<HTMLElement & { icon?: string }>('[data-testid="ideas-save"]')
    expect(previewToggle?.tagName.toLowerCase()).toBe('p-button')
    expect(saveButton?.tagName.toLowerCase()).toBe('p-button')
    expect(previewToggle?.icon).toBe('view')
    expect(saveButton?.icon).toBe('save')
    expect(container.querySelector('textarea')?.getAttribute('data-pds-exception')).toBe('ideas-markdown-editor')
  })

  it('lets the native editor textarea shrink inside the bounded shell on narrow viewports', async () => {
    const { container } = await renderLoaded('draft\n'.repeat(80))
    const shellClass = container.querySelector('[data-testid="ideas-editor-shell"]')?.getAttribute('class') ?? ''
    const textareaClass = container.querySelector('textarea')?.getAttribute('class') ?? ''

    expect(shellClass).toContain('overflow-hidden')
    expect(textareaClass).toContain('min-h-0')
    expect(textareaClass).not.toContain('min-h-[420px]')
  })

  it('renders the unsaved navigation confirmation with PModal', async () => {
    const { container } = await renderLoaded('base')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'unsaved' } })
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="ideas-unsaved-dialog"]')?.tagName.toLowerCase()).toBe('p-modal')
    })
  })
})

describe('IdeasPageIntegration_StatusWording', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('omits the Ideas header summary when the notebook is clean', async () => {
    const { container } = await renderLoaded('one two three four five')
    const summary = container.querySelector('[data-testid="workspace-header-summary"]')

    expect(summary).toBeNull()
  })

  it('keeps unsaved changes out of the Ideas header after editing', async () => {
    const { container } = await renderLoaded('base')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'changed' } })

    const summary = container.querySelector('[data-testid="workspace-header-summary"]')
    expect(summary).toBeNull()
    expect(container.querySelector('[data-testid="ideas-dirty"]')?.textContent).toBe('Unsaved changes')
  })

  it('shows the last saved recency in the notebook state panel', async () => {
    const { container } = await renderLoaded('base')

    const statePanel = container.querySelector('[data-testid="ideas-state-panel"]')
    expect(statePanel?.textContent).toContain('Last saved')
    expect(container.querySelector('[data-testid="ideas-last-saved"]')?.textContent).toBe('3m ago')
  })

  it('does not render visible draft wording in the notebook surface', async () => {
    const { container } = await renderLoaded('base')

    expect(container.textContent).not.toMatch(/\bdraft\b/i)
    expect(container.querySelector('[data-testid="ideas-state-panel"]')?.textContent).toContain('Writing metrics')
  })
})

describe('IdeasPageIntegration_SaveTimeConflict', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  function makeSaveConflictFetch() {
    const loadedAt = '2026-05-24T09:00:00+00:00'
    const diskAt = '2026-05-24T09:05:00+00:00'
    return vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        const body = JSON.parse(init.body as string) as Record<string, unknown>
        if (body.force === true) {
          return Promise.resolve({ ok: true, status: 204, headers: new Headers({ 'x-ideas-updated-at': '2026-05-24T09:06:00+00:00' }), json: () => Promise.resolve(null) })
        }
        return Promise.resolve({
          ok: false,
          status: 409,
          json: () => Promise.resolve({ content: 'disk version', updated_at: diskAt }),
        })
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ content: 'baseline', updated_at: loadedAt }) })
    })
  }

  async function renderAfterSaveConflict(): Promise<{ container: HTMLElement; fetchMock: ReturnType<typeof vi.fn> }> {
    const fetchMock = makeSaveConflictFetch()
    vi.stubGlobal('fetch', fetchMock)
    let result!: ReturnType<typeof renderInRouter>
    await act(async () => {
      result = renderInRouter()
    })
    await flush()
    await enterEditMode(result.container)
    const { container } = result
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'user edits' } })
    await act(async () => {
      fireEvent.click(container.querySelector('[data-testid="ideas-save"]')!)
    })
    await flush()
    return { container, fetchMock }
  }

  it('shows overwrite, load, and cancel choices when save detects a disk change', async () => {
    const { container } = await renderAfterSaveConflict()
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="ideas-conflict-overwrite"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="ideas-conflict-load"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="ideas-conflict-cancel"]')).not.toBeNull()
  })

  it('cancel keeps the local draft dirty and re-enables save', async () => {
    const { container } = await renderAfterSaveConflict()
    fireEvent.click(container.querySelector('[data-testid="ideas-conflict-cancel"]')!)
    await flush()
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
    expect(container.querySelector('textarea')?.value).toBe('user edits')
    expect(container.querySelector('[data-testid="ideas-dirty"]')).not.toBeNull()
    expect(container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')?.disabled).toBe(false)
  })

  it('load from disk replaces the draft and clears dirty state', async () => {
    const { container } = await renderAfterSaveConflict()
    fireEvent.click(container.querySelector('[data-testid="ideas-conflict-load"]')!)
    await flush()
    expect(container.querySelector('textarea')?.value).toBe('disk version')
    expect(container.querySelector('[data-testid="ideas-dirty"]')).toBeNull()
    expect(container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')?.disabled).toBe(true)
  })

  it('overwrite sends a forced save with the local draft', async () => {
    const { container, fetchMock } = await renderAfterSaveConflict()
    await act(async () => {
      fireEvent.click(container.querySelector('[data-testid="ideas-conflict-overwrite"]')!)
    })
    await flush()
    const putBodies = fetchMock.mock.calls
      .filter(([, init]: [string, RequestInit | undefined]) => init?.method === 'PUT')
      .map(([, init]: [string, RequestInit]) => JSON.parse(init.body as string) as Record<string, unknown>)
    expect(putBodies[1]).toMatchObject({ content: 'user edits', force: true })
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
    expect(container.querySelector('[data-testid="ideas-dirty"]')).toBeNull()
  })
})
