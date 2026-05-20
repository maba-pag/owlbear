/**
 * Task #1664 — P2-03: IdeasPage — unsaved-changes guard
 *
 * AC1: dirty + navigate → alertdialog with role="alertdialog" and text
 *      'You have unsaved changes. Leave anyway?'; proceed completes nav;
 *      cancel dismisses dialog and user remains on IdeasPage.
 * AC2: dirty → beforeunload handler calls event.preventDefault()
 * AC3: clean → navigation proceeds without dialog; no beforeunload handler registered
 * AC4: beforeunload event listeners removed on component unmount
 *
 * RED phase: IdeasPage has no useBlocker or beforeunload implementation.
 *   AC1, AC2, AC4 tests → FAIL (guard not implemented).
 *   AC3 tests → PASS by design (regression guards for negative behavior;
 *               cannot fail in RED — blocking is absent, so "no block" is trivially true).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, act, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router'
import IdeasPage from '../pages/IdeasPage'

// ─── Fetch mock helpers ───────────────────────────────────────────────────────

function makeGetOkFetch(content = '') {
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
  return (
    <button type="button" data-testid={testId} onClick={() => navigate(to)} />
  )
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

async function flush() {
  await act(async () => {
    await Promise.resolve()
  })
}

/** Render IdeasPage in router context and wait for GET /api/ideas to complete. */
async function renderLoaded(content = 'initial content') {
  vi.stubGlobal('fetch', makeGetOkFetch(content))
  let result!: ReturnType<typeof renderInRouter>
  await act(async () => {
    result = renderInRouter()
  })
  await flush()
  return result
}

/** Render loaded, then modify textarea to make content dirty. */
async function renderDirty(initialContent = 'initial', newContent = 'changed') {
  const result = await renderLoaded(initialContent)
  const textarea = result.container.querySelector('textarea')!
  fireEvent.change(textarea, { target: { value: newContent } })
  return result
}

// ─── AC1: Navigation guard when dirty ────────────────────────────────────────

describe('TestFromAC_UnsavedChangesNavGuard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 happy: alertdialog element renders when dirty user navigates to another route', async () => {
    const { container } = await renderDirty()
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[role="alertdialog"]')).not.toBeNull()
    })
  })

  it('ac1 happy: dialog text contains the required string "You have unsaved changes. Leave anyway?"', async () => {
    const { container } = await renderDirty()
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      const dialog = container.querySelector('[role="alertdialog"]')
      expect(dialog).not.toBeNull()
      expect(dialog!.textContent).toContain('You have unsaved changes. Leave anyway?')
    })
  })

  it('ac1 happy: navigation is blocked — home page not rendered while dialog is visible', async () => {
    const { container } = await renderDirty()
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[role="alertdialog"]')).not.toBeNull()
    })
    // Home page has NOT replaced IdeasPage — navigation is pending
    expect(container.querySelector('[data-testid="home-page"]')).toBeNull()
    // Textarea still present — user is still on /ideas
    expect(container.querySelector('textarea')).not.toBeNull()
  })

  it('ac1 happy: clicking the proceed action completes navigation to the requested route', async () => {
    const { container } = await renderDirty()
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[role="alertdialog"]')).not.toBeNull()
    })
    const dialog = container.querySelector('[role="alertdialog"]')!
    const buttons = Array.from(dialog.querySelectorAll('button'))
    // Find the proceed / leave button by text content
    const proceedBtn = buttons.find((b) =>
      /leave|proceed|confirm|yes/i.test(b.textContent ?? ''),
    )
    expect(proceedBtn).not.toBeUndefined()
    fireEvent.click(proceedBtn!)
    await waitFor(() => {
      // Home page is now visible — navigation completed
      expect(container.querySelector('[data-testid="home-page"]')).not.toBeNull()
    })
    expect(container.querySelector('[role="alertdialog"]')).toBeNull()
  })

  it('ac1 happy: clicking the cancel action dismisses dialog and user remains on IdeasPage', async () => {
    const { container } = await renderDirty()
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[role="alertdialog"]')).not.toBeNull()
    })
    const dialog = container.querySelector('[role="alertdialog"]')!
    const buttons = Array.from(dialog.querySelectorAll('button'))
    // Find the cancel / stay button by text content
    const cancelBtn = buttons.find((b) =>
      /cancel|stay|no|dismiss/i.test(b.textContent ?? ''),
    )
    expect(cancelBtn).not.toBeUndefined()
    fireEvent.click(cancelBtn!)
    await waitFor(() => {
      // Dialog dismissed
      expect(container.querySelector('[role="alertdialog"]')).toBeNull()
    })
    // User remains on IdeasPage — textarea still visible, home page absent
    expect(container.querySelector('textarea')).not.toBeNull()
    expect(container.querySelector('[data-testid="home-page"]')).toBeNull()
  })

  it('ac1 boundary: alertdialog appears when content differs from last-saved by a single character', async () => {
    const { container } = await renderLoaded('hello world')
    fireEvent.change(container.querySelector('textarea')!, {
      target: { value: 'hello worlD' },
    })
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[role="alertdialog"]')).not.toBeNull()
    })
  })
})

// ─── AC2: beforeunload handler when dirty ─────────────────────────────────────

describe('TestFromAC_BeforeUnloadDirty', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac2 happy: beforeunload event.preventDefault() is called when content is dirty', async () => {
    await renderDirty('initial', 'changed')
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
  })

  it('ac2 boundary: beforeunload calls preventDefault when content differs by only one character', async () => {
    const { container } = await renderLoaded('abc')
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'abC' } })
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
  })
})

// ─── AC3: Clean state — no blocking (regression guards) ──────────────────────
// NOTE: These tests PASS in the RED phase by design. When content is clean and no
// blocking implementation exists at all, "no blocking" is trivially true.
// They are retained as regression guards: once the guard is implemented, these
// tests prevent over-blocking of clean navigation.

describe('TestFromAC_CleanStateNoBlock', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac3 happy: route navigation completes without dialog when content is clean', async () => {
    const { container } = await renderLoaded('same content')
    // Content is clean (not modified after load)
    fireEvent.click(container.querySelector('[data-testid="nav-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="home-page"]')).not.toBeNull()
    })
    expect(container.querySelector('[role="alertdialog"]')).toBeNull()
  })

  it('ac3 happy: beforeunload event.preventDefault() is NOT called when content is clean', async () => {
    await renderLoaded('clean content')
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(false)
  })
})

// ─── AC4: Event listener cleanup on unmount ───────────────────────────────────

describe('TestFromAC_EventListenerCleanup', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac4 happy: beforeunload handler prevents default while mounted (dirty) and NOT after unmount', async () => {
    const { unmount } = await renderDirty('initial', 'changed')

    // Verify handler is active while mounted and dirty (also covers AC2)
    const mountedEvent = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(mountedEvent)
    expect(mountedEvent.defaultPrevented).toBe(true)

    // Unmount the component
    unmount()

    // Listener must be removed — no preventDefault after unmount
    const afterUnmountEvent = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(afterUnmountEvent)
    expect(afterUnmountEvent.defaultPrevented).toBe(false)
  })

  it('ac4 edge: beforeunload handler deregistered when dirty state clears (content saved)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        if (init?.method === 'PUT') {
          return Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ content: 'initial' }),
        })
      }),
    )
    let result!: ReturnType<typeof renderInRouter>
    await act(async () => {
      result = renderInRouter()
    })
    await flush()
    const { container } = result

    // Make content dirty
    fireEvent.change(container.querySelector('textarea')!, { target: { value: 'modified' } })

    // While dirty, beforeunload must prevent default
    const dirtyEvent = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(dirtyEvent)
    expect(dirtyEvent.defaultPrevented).toBe(true)

    // Trigger save (Cmd/Ctrl+S) → PUT resolves → isDirty becomes false
    await act(async () => {
      fireEvent.keyDown(document, { key: 's', ctrlKey: true })
    })
    await flush()

    // After save, content is clean → handler deregistered → no preventDefault
    const cleanEvent = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(cleanEvent)
    expect(cleanEvent.defaultPrevented).toBe(false)
  })
})
