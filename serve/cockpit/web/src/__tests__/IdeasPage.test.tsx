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
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router'
import IdeasPage from '../pages/IdeasPage'

// ─── Fetch mock factories ──────────────────────────────────────────────────────

/** GET resolves with content; PUT resolves 204. */
function makeGetOkPutOkFetch(content: string) {
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

/** GET only — resolves with content. */
function makeGetOkFetch(content: string) {
  return vi.fn((_url: string, _init?: RequestInit) =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ content }),
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
  return render(
    <MemoryRouter initialEntries={['/ideas']}>
      <Routes>
        <Route path="/ideas" element={<IdeasPage />} />
        <Route path="/" element={<div data-testid="home-page">Home</div>} />
      </Routes>
      <NavButton to="/" testId="nav-home" />
    </MemoryRouter>,
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

async function fireVisibilityVisible(): Promise<void> {
  setVisibilityState('visible')
  await act(async () => {
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await flush()
}

/**
 * Render loaded, make content dirty, then trigger a visibilitychange refetch
 * returning fetchedContent (which differs from baseline). Resolves with the
 * container after conflict state is set.
 */
async function renderInConflict(
  initialContent: string,
  dirtyContent: string,
  fetchedContent: string,
): Promise<HTMLElement> {
  const { container } = await renderLoaded(initialContent)
  const textarea = container.querySelector('textarea')!
  fireEvent.change(textarea, { target: { value: dirtyContent } })
  vi.stubGlobal('fetch', makeGetOkFetch(fetchedContent))
  await fireVisibilityVisible()
  return container
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
})

describe('IdeasPageIntegration_PdsControls', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders editor commands as PDS buttons while keeping the markdown textarea native', async () => {
    const { container } = await renderLoaded('base')
    expect(container.querySelector('[data-testid="ideas-preview-toggle"]')?.tagName.toLowerCase()).toBe('p-button')
    expect(container.querySelector('[data-testid="ideas-save"]')?.tagName.toLowerCase()).toBe('p-button')
    expect(container.querySelector('textarea')?.getAttribute('data-pds-exception')).toBe('ideas-markdown-editor')
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

  it('keeps the Ideas header summary focused on save state only', async () => {
    const { container } = await renderLoaded('one two three four five')
    const summary = container.querySelector('[data-testid="workspace-header-summary"]')

    expect(summary?.textContent).toBe('Saved')
    expect(summary?.querySelector('[data-testid="workspace-header-metric"]')).toBeNull()
    expect(summary?.textContent).not.toMatch(/edit|preview|words/i)
  })

  it('shows unsaved changes as the actionable header state after editing', async () => {
    const { container } = await renderLoaded('base')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'changed' } })

    const summary = container.querySelector('[data-testid="workspace-header-summary"]')
    expect(summary?.textContent).toBe('Unsaved changes')
  })

  it('does not render visible draft wording in the notebook surface', async () => {
    const { container } = await renderLoaded('base')

    expect(container.textContent).not.toMatch(/\bdraft\b/i)
    expect(container.querySelector('[data-testid="ideas-state-panel"]')?.textContent).toContain('Writing metrics')
  })
})

// ─── AC4: Conflict trigger ────────────────────────────────────────────────────
//
// While dirty, visibilitychange re-fetch returning different server content causes
// conflict notice (data-testid="ideas-conflict-notice") to appear with Overwrite
// and Discard & Reload buttons.

describe('IdeasPageIntegration_ConflictTrigger', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac4 happy: conflict notice appears when dirty and re-fetch returns different server content', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).not.toBeNull()
  })

  it('ac4 happy: conflict notice contains an Overwrite button', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    expect(container.querySelector('[data-testid="ideas-conflict-overwrite"]')).not.toBeNull()
  })

  it('ac4 happy: conflict notice contains a Discard & Reload button', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    expect(container.querySelector('[data-testid="ideas-conflict-discard"]')).not.toBeNull()
  })

  it('ac4 edge: no conflict notice when content is clean at visibilitychange time', async () => {
    const { container } = await renderLoaded('baseline')
    // Content is NOT edited — clean state
    vi.stubGlobal('fetch', makeGetOkFetch('server version'))
    await fireVisibilityVisible()
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
  })

  it('ac4 boundary: conflict notice appears even when dirty content differs from baseline by one word', async () => {
    const container = await renderInConflict('word1 word2', 'word1 word3', 'word1 word4')
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).not.toBeNull()
  })
})

// ─── AC5: Conflict — Overwrite ───────────────────────────────────────────────
//
// Clicking Overwrite: dismisses notice, updates last-saved baseline to server
// content, keeps textarea content unchanged, dirty indicator remains visible,
// save button re-enables.

describe('IdeasPageIntegration_ConflictOverwrite', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  async function clickOverwrite(container: HTMLElement): Promise<void> {
    const btn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-conflict-overwrite"]')!
    await act(async () => {
      fireEvent.click(btn)
    })
    await flush()
  }

  it('ac5 happy: clicking Overwrite dismisses the conflict notice', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    await clickOverwrite(container)
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
  })

  it('ac5 happy: textarea content is unchanged after clicking Overwrite', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    await clickOverwrite(container)
    expect(container.querySelector('textarea')?.value).toBe('user edits')
  })

  it('ac5 happy: dirty indicator remains visible after clicking Overwrite', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    await clickOverwrite(container)
    expect(container.querySelector('[data-testid="ideas-dirty"]')).not.toBeNull()
  })

  it('ac5 happy: save button is re-enabled after clicking Overwrite', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    await clickOverwrite(container)
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(false)
  })

  it('ac5 happy: last-saved baseline is updated to server content after Overwrite', async () => {
    // Proof: after overwrite, typing server content into textarea makes state clean
    // (save button disabled). If baseline were NOT updated, typing server content
    // would still differ from old baseline → save stays enabled → assertion fails.
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    await clickOverwrite(container)
    const textarea = container.querySelector('textarea')!
    fireEvent.change(textarea, { target: { value: 'server version' } })
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })
})

// ─── AC6: Conflict — Discard ──────────────────────────────────────────────────
//
// Clicking Discard & Reload: dismisses notice, sets textarea value and baseline
// to server content, dirty indicator disappears, save button disables.

describe('IdeasPageIntegration_ConflictDiscard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  async function clickDiscard(container: HTMLElement): Promise<void> {
    const btn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-conflict-discard"]')!
    await act(async () => {
      fireEvent.click(btn)
    })
    await flush()
  }

  it('ac6 happy: clicking Discard & Reload dismisses the conflict notice', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    await clickDiscard(container)
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
  })

  it('ac6 happy: textarea value is set to server content after Discard & Reload', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    await clickDiscard(container)
    expect(container.querySelector('textarea')?.value).toBe('server version')
  })

  it('ac6 happy: dirty indicator disappears after Discard & Reload', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    await clickDiscard(container)
    expect(container.querySelector('[data-testid="ideas-dirty"]')).toBeNull()
  })

  it('ac6 happy: save button is disabled after Discard & Reload', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    await clickDiscard(container)
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })

  it('ac6 cross-feature: navigation proceeds without alertdialog after Discard clears dirty state', async () => {
    // Cross-feature: conflict resolution (#1665) + navigation guard (#1664)
    // After discard, isDirty=false → guard does not block navigation.
    const { container } = await renderLoaded('baseline')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'user edits' } })
    vi.stubGlobal('fetch', makeGetOkFetch('server version'))
    await fireVisibilityVisible()

    // Conflict notice must be showing before discard
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).not.toBeNull()

    await clickDiscard(container)

    // Navigate — guard must NOT block (clean after discard)
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="home-page"]')).not.toBeNull()
    })
    expect(container.querySelector('[role="alertdialog"]')).toBeNull()
  })
})
