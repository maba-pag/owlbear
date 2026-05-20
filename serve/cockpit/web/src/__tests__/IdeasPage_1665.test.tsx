/**
 * Task #1665 — P2-04: IdeasPage — external-edit awareness and conflict resolution
 *
 * AC1: IdeasPage registers a `visibilitychange` listener that calls GET `/api/ideas`
 *      when `document.visibilityState` becomes 'visible'; on route activation
 *      (component mount after navigation), the existing initial fetch satisfies the
 *      re-fetch requirement.
 * AC2: When IdeasPage content is clean (textarea value equals last-saved baseline)
 *      both at visibilitychange trigger and when the GET response resolves, fetched
 *      content silently replaces both textarea value and last-saved baseline without
 *      showing a loading indicator.
 * AC3 (NEW): If IdeasPage content was clean at visibilitychange trigger but becomes
 *      dirty before the GET response resolves, the refetch result is discarded:
 *      textarea value, last-saved baseline, dirty indicator, and save-button
 *      enablement remain unchanged.
 * AC4: When IdeasPage content is dirty at visibilitychange trigger time and fetched
 *      content differs from the trigger-time last-saved baseline, a conflict notice
 *      appears with Overwrite and Discard & Reload buttons.
 * AC5: While the IdeasPage conflict notice is showing, both the Save button and
 *      Cmd/Ctrl+S keyboard shortcut are blocked (no PUT `/api/ideas` issued).
 * AC6: IdeasPage Overwrite button dismisses the conflict notice, updates last-saved
 *      baseline to fetched content, and re-enables Save (textarea content unchanged;
 *      dirty indicator remains visible).
 * AC7: IdeasPage Discard & Reload button dismisses the conflict notice, sets textarea
 *      value and last-saved baseline to fetched content (dirty indicator hidden, Save
 *      disabled).
 * AC8: If the IdeasPage visibilitychange re-fetch fails (non-2xx or network error),
 *      IdeasPage continues with existing textarea content and state without showing
 *      an error or conflict notice.
 *
 * RED phase (original): visibilitychange listener, silent update on clean re-fetch,
 * conflict notice, Overwrite/Discard buttons — now implemented.
 * RED phase (retry AC3): clean-start pending-refetch interleave — not yet implemented;
 * new TestFromAC_IdeasPageCleanInterleavedRefetch tests FAIL.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, act } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'
import IdeasPage from '../pages/IdeasPage'

// ─── Fetch mock factories ──────────────────────────────────────────────────────

function makeGetOkFetch(content: string) {
  return vi.fn((_url: string, _init?: RequestInit) =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ content }),
    }),
  )
}

function makeGetErrorFetch(status = 500) {
  return vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve({ detail: 'Server error' }),
    }),
  )
}

function makeNetworkErrorFetch() {
  return vi.fn(() => Promise.reject(new TypeError('Network failure')))
}

// ─── Render helpers ──────────────────────────────────────────────────────────

function renderInRouter() {
  return render(
    <MemoryRouter initialEntries={['/ideas']}>
      <Routes>
        <Route path="/ideas" element={<IdeasPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

// ─── Utilities ────────────────────────────────────────────────────────────────

async function flush(): Promise<void> {
  await act(async () => {
    await Promise.resolve()
  })
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

/** Render IdeasPage with a successful initial fetch; wait for load to complete. */
async function renderLoaded(initialContent: string): Promise<HTMLElement> {
  vi.stubGlobal('fetch', makeGetOkFetch(initialContent))
  let container!: HTMLElement
  await act(async () => {
    container = renderInRouter().container
  })
  await flush()
  return container
}

/**
 * Render loaded, then start a pending visibilitychange refetch whose GET response
 * is held until the caller invokes `resolveRefetch()`. Allows typing into the
 * textarea between trigger and resolution to test pending-refetch interleavings.
 */
async function startPendingRefetch(
  initialContent: string,
  fetchedContent: string,
): Promise<{
  container: HTMLElement
  textarea: HTMLTextAreaElement | null
  resolveRefetch: () => Promise<void>
  refetchMock: ReturnType<typeof vi.fn>
}> {
  const container = await renderLoaded(initialContent)

  let doResolve!: () => void
  const refetchPromise = new Promise<void>(resolve => {
    doResolve = resolve
  })

  const refetchMock = vi.fn(() =>
    refetchPromise.then(() => ({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ content: fetchedContent }),
    }))
  )
  vi.stubGlobal('fetch', refetchMock)

  setVisibilityState('visible')
  await act(async () => {
    document.dispatchEvent(new Event('visibilitychange'))
  })

  const resolveRefetch = async () => {
    await act(async () => {
      doResolve()
      await Promise.resolve()
    })
    await flush()
  }

  return {
    container,
    textarea: container.querySelector('textarea'),
    resolveRefetch,
    refetchMock,
  }
}

/**
 * Render loaded, make content dirty, then fire visibilitychange with a re-fetch
 * that returns fetchedContent. Returns the container in whatever state the
 * (unimplemented) conflict logic puts it.
 */
async function renderInConflict(
  initialContent: string,
  dirtyContent: string,
  fetchedContent: string,
): Promise<HTMLElement> {
  const container = await renderLoaded(initialContent)
  const textarea = container.querySelector('textarea')
  if (textarea) {
    fireEvent.change(textarea, { target: { value: dirtyContent } })
  }
  vi.stubGlobal('fetch', makeGetOkFetch(fetchedContent))
  await fireVisibilityVisible()
  return container
}

// ─── AC1: visibilitychange listener ───────────────────────────────────────────

describe('TestFromAC_IdeasPageVisibility', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac1 happy: fires GET /api/ideas when document.visibilityState becomes visible', async () => {
    await renderLoaded('initial')

    const refetchMock = makeGetOkFetch('updated')
    vi.stubGlobal('fetch', refetchMock)

    await fireVisibilityVisible()

    expect(refetchMock).toHaveBeenCalledWith('/api/ideas', expect.anything())
  })

  it('ac1 happy: visibilitychange re-fetch issues GET only — no PUT /api/ideas', async () => {
    await renderLoaded('initial')

    const refetchMock = vi.fn((_url: string, init?: RequestInit) =>
      init?.method === 'PUT'
        ? Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
        : Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ content: 'updated' }) }),
    )
    vi.stubGlobal('fetch', refetchMock)

    await fireVisibilityVisible()

    // GET must have been issued (listener registered — fails in RED)
    const getCalls = refetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit | undefined]) => !init?.method || init.method === 'GET',
    )
    expect(getCalls.length).toBeGreaterThan(0)
    // No PUT issued by the re-fetch
    const putCalls = refetchMock.mock.calls.filter(
      ([, init]: [string, RequestInit | undefined]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBe(0)
  })

  it('ac1 edge: does NOT fire GET /api/ideas when visibilityState remains hidden', async () => {
    await renderLoaded('initial')

    const refetchMock = makeGetOkFetch('visible')
    vi.stubGlobal('fetch', refetchMock)

    // First: visible → must refetch (fails in RED, proving listener is checked)
    await fireVisibilityVisible()
    const callsAfterVisible = refetchMock.mock.calls.length
    expect(callsAfterVisible).toBeGreaterThan(0)

    // Second: hidden → must NOT add another call
    const refetchMock2 = makeGetOkFetch('hidden-ignored')
    vi.stubGlobal('fetch', refetchMock2)
    setVisibilityState('hidden')
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await flush()

    expect(refetchMock2).not.toHaveBeenCalled()
  })

  it('ac1 happy: visibilitychange listener is removed on component unmount', async () => {
    vi.stubGlobal('fetch', makeGetOkFetch('initial'))
    let unmount!: () => void
    await act(async () => {
      const result = renderInRouter()
      unmount = result.unmount
    })
    await flush()

    // Confirm listener is registered: visible → refetch fires
    const beforeUnmountMock = makeGetOkFetch('pre-unmount')
    vi.stubGlobal('fetch', beforeUnmountMock)
    await fireVisibilityVisible()
    expect(beforeUnmountMock).toHaveBeenCalled()

    // Unmount and verify listener is gone: visible event → refetch does NOT fire
    const afterUnmountMock = makeGetOkFetch('post-unmount')
    vi.stubGlobal('fetch', afterUnmountMock)
    unmount()

    setVisibilityState('visible')
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await flush()

    expect(afterUnmountMock).not.toHaveBeenCalled()
  })
})

// ─── AC2: Clean state — silent update ─────────────────────────────────────────

describe('TestFromAC_IdeasPageCleanSilentUpdate', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac2 happy: textarea value is replaced with fetched content when clean at re-fetch time', async () => {
    const container = await renderLoaded('original content')

    vi.stubGlobal('fetch', makeGetOkFetch('server updated content'))
    await fireVisibilityVisible()

    const textarea = container.querySelector('textarea')
    expect(textarea?.value).toBe('server updated content')
  })

  it('ac2 happy: last-saved baseline is updated to fetched content after clean re-fetch', async () => {
    // Proof: after silent update, typing the fetched value into textarea → clean → save disabled.
    // Without baseline update (RED), typing fetched value into textarea is still dirty relative
    // to original baseline → save remains enabled → assertion fails.
    const container = await renderLoaded('original')

    vi.stubGlobal('fetch', makeGetOkFetch('server update'))
    await fireVisibilityVisible()

    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'server update' } })
    }
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })

  it('ac2 happy: no loading indicator is shown while visibilitychange re-fetch is in-flight', async () => {
    await renderLoaded('original')

    let resolveRefetch!: (value: unknown) => void
    const pendingRefetchFetch = vi.fn(
      () => new Promise((resolve) => { resolveRefetch = resolve }),
    )
    vi.stubGlobal('fetch', pendingRefetchFetch)

    setVisibilityState('visible')
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })

    // Re-fetch must be in-flight (fails in RED because listener not registered)
    expect(pendingRefetchFetch).toHaveBeenCalled()
    // No loading indicator during background re-fetch
    const loadingContainer = document.querySelector('[data-testid="ideas-loading"]')
    expect(loadingContainer).toBeNull()

    // Resolve the pending fetch to avoid state-update warnings
    await act(async () => {
      resolveRefetch({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ content: 'updated' }),
      })
    })
    await flush()
  })

})

// ─── AC3: Dirty + differing fetched content — conflict notice ─────────────────

describe('TestFromAC_IdeasPageConflictNotice', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac3 happy: conflict notice appears when content is dirty and fetched differs from baseline', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).not.toBeNull()
  })

  it('ac3 happy: conflict notice contains an Overwrite button', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    expect(container.querySelector('[data-testid="ideas-conflict-overwrite"]')).not.toBeNull()
  })

  it('ac3 happy: conflict notice contains a Discard & Reload button', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    expect(container.querySelector('[data-testid="ideas-conflict-discard"]')).not.toBeNull()
  })
})

// ─── AC4: Save blocked during conflict ────────────────────────────────────────

describe('TestFromAC_IdeasPageConflictSaveBlocked', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac4 happy: Save button is disabled while conflict notice is showing', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })

  it('ac4 happy: Cmd+S during conflict does not issue PUT /api/ideas', async () => {
    await renderInConflict('baseline', 'user edits', 'server version')

    const putCapture = vi.fn((_url: string, init?: RequestInit) =>
      init?.method === 'PUT'
        ? Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
        : Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ content: 'server version' }) }),
    )
    vi.stubGlobal('fetch', putCapture)

    await act(async () => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 's', metaKey: true, bubbles: true }),
      )
    })
    await flush()

    const putCalls = putCapture.mock.calls.filter(
      ([, init]: [string, RequestInit | undefined]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBe(0)
  })

  it('ac4 happy: Ctrl+S during conflict does not issue PUT /api/ideas', async () => {
    await renderInConflict('baseline', 'user edits', 'server version')

    const putCapture = vi.fn((_url: string, init?: RequestInit) =>
      init?.method === 'PUT'
        ? Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
        : Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ content: 'server version' }) }),
    )
    vi.stubGlobal('fetch', putCapture)

    await act(async () => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true }),
      )
    })
    await flush()

    const putCalls = putCapture.mock.calls.filter(
      ([, init]: [string, RequestInit | undefined]) => init?.method === 'PUT',
    )
    expect(putCalls.length).toBe(0)
  })
})

// ─── AC5: Overwrite button ────────────────────────────────────────────────────

describe('TestFromAC_IdeasPageConflictOverwrite', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac5 happy: Overwrite button dismisses the conflict notice', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')

    const overwriteBtn = container.querySelector('[data-testid="ideas-conflict-overwrite"]')
    // Must exist (fails in RED — no conflict UI implemented)
    expect(overwriteBtn).not.toBeNull()

    await act(async () => {
      if (overwriteBtn) fireEvent.click(overwriteBtn as HTMLButtonElement)
    })

    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
  })

  it('ac5 happy: textarea content is unchanged after clicking Overwrite', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')

    const overwriteBtn = container.querySelector('[data-testid="ideas-conflict-overwrite"]')
    expect(overwriteBtn).not.toBeNull()

    await act(async () => {
      if (overwriteBtn) fireEvent.click(overwriteBtn as HTMLButtonElement)
    })

    const textarea = container.querySelector('textarea')
    expect(textarea?.value).toBe('user edits')
  })

  it('ac5 happy: Save is re-enabled and dirty indicator visible after clicking Overwrite', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')

    const overwriteBtn = container.querySelector('[data-testid="ideas-conflict-overwrite"]')
    expect(overwriteBtn).not.toBeNull()

    await act(async () => {
      if (overwriteBtn) fireEvent.click(overwriteBtn as HTMLButtonElement)
    })

    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(false)
    expect(container.querySelector('[data-testid="ideas-dirty"]')).not.toBeNull()
  })

  it('ac5 happy: last-saved baseline is updated to fetched content after Overwrite', async () => {
    // Proof: baseline = fetched ("server version"). After overwrite, set textarea to
    // "server version" → clean (textarea == new baseline) → save disabled.
    // Without baseline update (RED), textarea "server version" != old baseline "baseline"
    // → still dirty → save stays enabled → assertion fails.
    const container = await renderInConflict('baseline', 'user edits', 'server version')

    const overwriteBtn = container.querySelector('[data-testid="ideas-conflict-overwrite"]')
    expect(overwriteBtn).not.toBeNull()

    await act(async () => {
      if (overwriteBtn) fireEvent.click(overwriteBtn as HTMLButtonElement)
    })

    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'server version' } })
    }
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })
})

// ─── AC6: Discard & Reload button ─────────────────────────────────────────────

describe('TestFromAC_IdeasPageConflictDiscard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac6 happy: Discard & Reload button dismisses the conflict notice', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')

    const discardBtn = container.querySelector('[data-testid="ideas-conflict-discard"]')
    // Must exist (fails in RED — no conflict UI implemented)
    expect(discardBtn).not.toBeNull()

    await act(async () => {
      if (discardBtn) fireEvent.click(discardBtn as HTMLButtonElement)
    })

    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
  })

  it('ac6 happy: textarea value is set to fetched content after Discard & Reload', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')

    const discardBtn = container.querySelector('[data-testid="ideas-conflict-discard"]')
    expect(discardBtn).not.toBeNull()

    await act(async () => {
      if (discardBtn) fireEvent.click(discardBtn as HTMLButtonElement)
    })

    const textarea = container.querySelector('textarea')
    expect(textarea?.value).toBe('server version')
  })

  it('ac6 happy: dirty indicator is hidden after Discard & Reload', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')

    const discardBtn = container.querySelector('[data-testid="ideas-conflict-discard"]')
    expect(discardBtn).not.toBeNull()

    await act(async () => {
      if (discardBtn) fireEvent.click(discardBtn as HTMLButtonElement)
    })

    expect(container.querySelector('[data-testid="ideas-dirty"]')).toBeNull()
  })

  it('ac6 happy: Save button is disabled after Discard & Reload (content matches new baseline)', async () => {
    const container = await renderInConflict('baseline', 'user edits', 'server version')

    const discardBtn = container.querySelector('[data-testid="ideas-conflict-discard"]')
    expect(discardBtn).not.toBeNull()

    await act(async () => {
      if (discardBtn) fireEvent.click(discardBtn as HTMLButtonElement)
    })

    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })
})

// ─── AC7: Re-fetch failure — silent continuation ───────────────────────────────

describe('TestFromAC_IdeasPageRefetchFailure', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac7 happy: network error during re-fetch does not show an error message', async () => {
    const container = await renderLoaded('existing content')

    const errorFetch = makeNetworkErrorFetch()
    vi.stubGlobal('fetch', errorFetch)
    await fireVisibilityVisible()

    // Re-fetch must be attempted (fails in RED — no listener)
    expect(errorFetch).toHaveBeenCalled()
    expect(container.querySelector('[data-testid="ideas-error"]')).toBeNull()
  })

  it('ac7 happy: network error during re-fetch does not show a conflict notice', async () => {
    const container = await renderLoaded('existing content')

    const errorFetch = makeNetworkErrorFetch()
    vi.stubGlobal('fetch', errorFetch)
    await fireVisibilityVisible()

    expect(errorFetch).toHaveBeenCalled()
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
  })

  it('ac7 happy: non-2xx response during re-fetch does not show an error message', async () => {
    const container = await renderLoaded('existing content')

    const errorFetch = makeGetErrorFetch(503)
    vi.stubGlobal('fetch', errorFetch)
    await fireVisibilityVisible()

    expect(errorFetch).toHaveBeenCalled()
    expect(container.querySelector('[data-testid="ideas-error"]')).toBeNull()
  })

  it('ac7 happy: non-2xx response during re-fetch preserves existing textarea content', async () => {
    const container = await renderLoaded('my existing ideas')

    const errorFetch = makeGetErrorFetch(503)
    vi.stubGlobal('fetch', errorFetch)
    await fireVisibilityVisible()

    expect(errorFetch).toHaveBeenCalled()
    const textarea = container.querySelector('textarea')
    expect(textarea?.value).toBe('my existing ideas')
  })
})

// ─── AC3 (new): Clean-start pending-refetch interleave — discard on dirty ────
//
// AC3: If content was clean at trigger but becomes dirty before GET resolves,
// the refetch result is discarded — textarea, baseline, dirty indicator, and
// save-button enablement all remain unchanged.
//
// Current bug: wasDirtyAtTrigger=false → clean branch applies fetched content
// unconditionally after await, overwriting edits typed mid-flight.
// These tests FAIL against the current implementation.

describe('TestFromAC_IdeasPageCleanInterleavedRefetch', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac3 happy: textarea preserves user edits typed before clean-start GET resolves', async () => {
    const { container, textarea, resolveRefetch, refetchMock } =
      await startPendingRefetch('original', 'server update')

    // Listener must be registered — GET must be in-flight (fails in RED if missing)
    expect(refetchMock).toHaveBeenCalled()

    // User types before GET resolves — page becomes dirty
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'user typed this' } })
    }

    // GET resolves; refetch result must be discarded
    await resolveRefetch()

    // Textarea must still show user's edits, not the fetched server content
    expect(container.querySelector('textarea')?.value).toBe('user typed this')
  })

  it('ac3 happy: last-saved baseline unchanged when refetch discarded after mid-flight edit', async () => {
    // Proof: after discard, typing the original baseline content back makes the
    // page clean (save disabled). If baseline was wrongly updated to fetched
    // content, typing the original would still be dirty → save enabled → FAIL.
    const { container, textarea, resolveRefetch, refetchMock } =
      await startPendingRefetch('original', 'server update')

    expect(refetchMock).toHaveBeenCalled()

    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'user typed this' } })
    }

    await resolveRefetch()

    // Type original baseline value back; if baseline = 'original' → clean → save disabled
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'original' } })
    }
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })

  it('ac3 happy: dirty indicator remains visible after refetch discarded (user edits preserved)', async () => {
    const { container, textarea, resolveRefetch, refetchMock } =
      await startPendingRefetch('original', 'server update')

    expect(refetchMock).toHaveBeenCalled()

    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'user typed this' } })
    }

    await resolveRefetch()

    // Page must still be dirty — user's unsaved edits must not be silently cleared
    expect(container.querySelector('[data-testid="ideas-dirty"]')).not.toBeNull()
  })

  it('ac3 happy: save button remains enabled after refetch discarded (user still has dirty edits)', async () => {
    const { container, textarea, resolveRefetch, refetchMock } =
      await startPendingRefetch('original', 'server update')

    expect(refetchMock).toHaveBeenCalled()

    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'user typed this' } })
    }

    await resolveRefetch()

    // Save must be re-enabled — user's edits are still pending
    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(false)
  })
})

// ─── AC6 (refined): Overwrite — content===fetched branch → page becomes clean ─
//
// AC6: "dirty indicator visibility and Save-button enablement reflect whether
// textarea content differs from the updated baseline."
//
// Branch under test: user has typed the same text the server returned, so after
// Overwrite (baseline=fetched, content unchanged), isDirty=false → clean.
// This branch was not covered by the original AC5 tests.

describe('TestFromAC_IdeasPageOverwriteCleanBranch', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac6 edge: conflict dismissed when textarea already matches fetched content after Overwrite', async () => {
    // User typed 'server version' which matches the server's current content.
    // Conflict still appears (fetched ≠ original baseline), but after Overwrite the page is clean.
    const container = await renderInConflict('original baseline', 'server version', 'server version')

    const overwriteBtn = container.querySelector('[data-testid="ideas-conflict-overwrite"]')
    expect(overwriteBtn).not.toBeNull()

    await act(async () => {
      if (overwriteBtn) fireEvent.click(overwriteBtn as HTMLButtonElement)
    })

    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
  })

  it('ac6 edge: dirty indicator hidden when textarea content equals fetched after Overwrite', async () => {
    // After Overwrite: baseline = fetched = 'server version'; content = 'server version'.
    // isDirty = false → dirty indicator must be hidden (reflects content vs updated baseline).
    const container = await renderInConflict('original baseline', 'server version', 'server version')

    const overwriteBtn = container.querySelector('[data-testid="ideas-conflict-overwrite"]')
    expect(overwriteBtn).not.toBeNull()

    await act(async () => {
      if (overwriteBtn) fireEvent.click(overwriteBtn as HTMLButtonElement)
    })

    expect(container.querySelector('[data-testid="ideas-dirty"]')).toBeNull()
  })

  it('ac6 edge: Save disabled when textarea content equals fetched after Overwrite', async () => {
    // After Overwrite: baseline = fetched = content → isDirty=false → Save must be disabled.
    const container = await renderInConflict('original baseline', 'server version', 'server version')

    const overwriteBtn = container.querySelector('[data-testid="ideas-conflict-overwrite"]')
    expect(overwriteBtn).not.toBeNull()

    await act(async () => {
      if (overwriteBtn) fireEvent.click(overwriteBtn as HTMLButtonElement)
    })

    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="ideas-save"]')
    expect(saveBtn?.disabled).toBe(true)
  })
})

// ─── AC9: Save before GET resolves — trigger-time baseline governs conflict ───
//
// AC9: "When IdeasPage is dirty at visibilitychange trigger time and the user
// saves successfully before the background GET resolves, conflict determination
// still compares fetched content against the trigger-time last-saved baseline
// (not the post-save baseline)."
//
// Setup: render dirty → fire visibilitychange (GET pending) → Cmd+S save
// (PUT resolves immediately, updating baseline) → resolve GET → assert conflict.
//
// Discriminating case: GET returns the post-save baseline value.
//   Correct impl  (trigger-time): fetched ≠ trigger-time baseline → conflict.
//   Broken impl   (post-save):    fetched === post-save baseline → no conflict.

describe('TestFromAC_IdeasPageSaveBeforeResolve', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setVisibilityState('visible')
  })

  it('ac9 happy: conflict shows when GET resolves with content != trigger-time baseline after mid-flight save', async () => {
    const container = await renderLoaded('original baseline')
    const textarea = container.querySelector('textarea')

    // Make dirty before trigger
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'user edits' } })
    }

    // GET is pending; PUT resolves 204 immediately
    let doResolveGet!: () => void
    const getPromise = new Promise<void>(resolve => { doResolveGet = resolve })
    const interleave = vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        return Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
      }
      return getPromise.then(() => ({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ content: 'server changed independently' }),
      }))
    })
    vi.stubGlobal('fetch', interleave)

    // Fire visibilitychange — GET starts; triggerLastSaved = 'original baseline'
    setVisibilityState('visible')
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })

    // Save while GET is in-flight — baseline updates to 'user edits'
    await act(async () => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 's', metaKey: true, bubbles: true }),
      )
    })
    await flush()

    // Resolve GET — 'server changed independently' ≠ trigger-time baseline 'original baseline'
    await act(async () => {
      doResolveGet()
      await Promise.resolve()
    })
    await flush()

    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).not.toBeNull()
  })

  it('ac9 happy: conflict shows when GET returns post-save baseline value (discriminating case)', async () => {
    // Discriminating: GET resolves with 'user edits' = post-save baseline, ≠ trigger-time baseline.
    //   Correct impl:  'user edits' ≠ 'original baseline' → conflict shows.
    //   Broken impl:   'user edits' === 'user edits' (post-save) → no conflict (regression).
    const container = await renderLoaded('original baseline')
    const textarea = container.querySelector('textarea')

    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'user edits' } })
    }

    let doResolveGet!: () => void
    const getPromise = new Promise<void>(resolve => { doResolveGet = resolve })
    const interleave = vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        return Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
      }
      // Fetched = post-save baseline ('user edits'), ≠ trigger-time baseline ('original baseline')
      return getPromise.then(() => ({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ content: 'user edits' }),
      }))
    })
    vi.stubGlobal('fetch', interleave)

    setVisibilityState('visible')
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })

    await act(async () => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 's', metaKey: true, bubbles: true }),
      )
    })
    await flush()

    await act(async () => {
      doResolveGet()
      await Promise.resolve()
    })
    await flush()

    // Must show conflict: fetched ('user edits') ≠ trigger-time baseline ('original baseline')
    // A broken impl using post-save baseline would false-green this path
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).not.toBeNull()
  })

  it('ac9 happy: no conflict when GET returns trigger-time baseline (no external change)', async () => {
    // Server still has 'original baseline' — no external edit occurred.
    // No conflict should show, even though user saved 'user edits' post-trigger.
    const container = await renderLoaded('original baseline')
    const textarea = container.querySelector('textarea')

    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'user edits' } })
    }

    let doResolveGet!: () => void
    const getPromise = new Promise<void>(resolve => { doResolveGet = resolve })
    const interleave = vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        return Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
      }
      // Server unchanged — returns same as trigger-time baseline
      return getPromise.then(() => ({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ content: 'original baseline' }),
      }))
    })
    vi.stubGlobal('fetch', interleave)

    setVisibilityState('visible')
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })

    await act(async () => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 's', metaKey: true, bubbles: true }),
      )
    })
    await flush()

    await act(async () => {
      doResolveGet()
      await Promise.resolve()
    })
    await flush()

    // No external change → no conflict
    expect(container.querySelector('[data-testid="ideas-conflict-notice"]')).toBeNull()
  })
})
