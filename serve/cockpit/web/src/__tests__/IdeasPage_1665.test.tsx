/**
 * Task #1665 — P2-04: IdeasPage — external-edit awareness and conflict resolution
 *
 * AC1: IdeasPage registers a `visibilitychange` listener that calls GET `/api/ideas`
 *      when `document.visibilityState` becomes 'visible'; on route activation
 *      (component mount after navigation), the existing initial fetch satisfies the
 *      re-fetch requirement.
 * AC2: When IdeasPage content is clean (textarea value equals last-saved baseline) at
 *      visibilitychange re-fetch time, fetched content silently replaces both textarea
 *      value and last-saved baseline without showing a loading indicator.
 * AC3: When IdeasPage content is dirty at visibilitychange re-fetch time and fetched
 *      content differs from the last-saved baseline, a conflict notice appears with
 *      Overwrite and Discard & Reload buttons.
 * AC4: While the IdeasPage conflict notice is showing, both the Save button and
 *      Cmd/Ctrl+S keyboard shortcut are blocked (no PUT `/api/ideas` issued).
 * AC5: IdeasPage Overwrite button dismisses the conflict notice, updates last-saved
 *      baseline to fetched content, and re-enables Save (textarea content unchanged;
 *      dirty indicator remains visible).
 * AC6: IdeasPage Discard & Reload button dismisses the conflict notice, sets textarea
 *      value and last-saved baseline to fetched content (dirty indicator hidden, Save
 *      disabled).
 * AC7: If the IdeasPage visibilitychange re-fetch fails (non-2xx or network error),
 *      IdeasPage continues with existing textarea content and state without showing
 *      an error or conflict notice.
 *
 * RED phase: visibilitychange listener, silent update on clean re-fetch, conflict
 * notice, Overwrite/Discard buttons are not yet implemented in IdeasPage.tsx →
 * all tests in this file fail.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, act } from '@testing-library/react'
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
    container = render(<IdeasPage />).container
  })
  await flush()
  return container
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
      const result = render(<IdeasPage />)
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
