/**
 * Task #1663 — P2-02: IdeasPage — markdown preview toggle
 *
 * AC1: Toggle button switches IdeasPage between preview (rendered markdown visible)
 *      and edit (textarea visible); only one mode active at a time; default mode is preview
 * AC2: Preview mode renders GFM content (tables render as <table> elements, ~~text~~ as
 *      strikethrough, - [x] as checked items); raw HTML in source (e.g. <script>,
 *      <img onerror=...>) is stripped by rehype-sanitize default schema
 * AC3: Switching from preview back to edit preserves textarea content without data loss
 *
 * RED phase: IdeasPage.tsx has no toggle or preview UI — all tests fail.
 * Expected testids: ideas-preview-toggle (toggle button), ideas-preview (preview container).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, act } from '@testing-library/react'
import IdeasPage from '../pages/IdeasPage'

// ─── Fetch mock ────────────────────────────────────────────────────────────────

function makeGetOkFetch(content = '') {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ content }),
    }),
  )
}

// ─── Utilities ─────────────────────────────────────────────────────────────────

async function flush() {
  await act(async () => {
    await Promise.resolve()
  })
}

async function renderLoaded(content = '') {
  vi.stubGlobal('fetch', makeGetOkFetch(content))
  let container!: HTMLElement
  await act(async () => {
    container = render(<IdeasPage />).container
  })
  await flush()
  return container
}

function getToggle(container: HTMLElement): HTMLButtonElement | null {
  return container.querySelector<HTMLButtonElement>('[data-testid="ideas-preview-toggle"]')
}

/** Asserts toggle is present, then clicks it. Fails fast in RED (toggle absent). */
async function clickToggle(container: HTMLElement) {
  const toggle = getToggle(container)
  expect(toggle).not.toBeNull()
  await act(async () => {
    fireEvent.click(toggle!)
  })
  await flush()
}

// ─── AC1: Toggle button and mode switching ─────────────────────────────────────

describe('TestFromAC_IdeasPageToggle', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac1 happy: toggle button is present in initial preview mode', async () => {
    const container = await renderLoaded('some content')
    expect(getToggle(container)).not.toBeNull()
    expect(container.querySelector('[data-testid="ideas-preview"]')).not.toBeNull()
    expect(container.querySelector('textarea')).toBeNull()
  })

  it('ac1 happy: clicking toggle enters edit — textarea visible, preview absent', async () => {
    const container = await renderLoaded('# Heading')
    await clickToggle(container)
    expect(container.querySelector('textarea')).not.toBeNull()
    expect(container.querySelector('[data-testid="ideas-preview"]')).toBeNull()
  })

  it('ac1 happy: clicking toggle again returns to preview — preview visible, textarea absent', async () => {
    const container = await renderLoaded('content')
    await clickToggle(container) // -> edit
    await clickToggle(container) // -> preview
    expect(container.querySelector('[data-testid="ideas-preview"]')).not.toBeNull()
    expect(container.querySelector('textarea')).toBeNull()
  })

  it('ac1 edge: in preview mode textarea and preview are never simultaneously visible', async () => {
    const container = await renderLoaded('content')
    const hasTextarea = container.querySelector('textarea') !== null
    const hasPreview = container.querySelector('[data-testid="ideas-preview"]') !== null
    // Exactly one must be active; never both
    expect(hasTextarea && hasPreview).toBe(false)
    expect(hasTextarea || hasPreview).toBe(true)
  })

  it('ac1 boundary: toggle button remains visible in preview mode (can switch back)', async () => {
    const container = await renderLoaded('content')
    expect(getToggle(container)).not.toBeNull()
  })
})

// ─── AC2: GFM rendering and HTML sanitization ──────────────────────────────────

describe('TestFromAC_IdeasPageGFMRendering', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac2 happy: GFM table in content renders as <table> element in preview mode', async () => {
    const tableMarkdown = '| col1 | col2 |\n|------|------|\n| a    | b    |'
    const container = await renderLoaded(tableMarkdown)
    const preview = container.querySelector('[data-testid="ideas-preview"]')
    expect(preview?.querySelector('table')).not.toBeNull()
  })

  it('ac2 happy: GFM strikethrough ~~text~~ renders as <del> element in preview mode', async () => {
    const container = await renderLoaded('~~strikethrough text~~')
    const preview = container.querySelector('[data-testid="ideas-preview"]')
    expect(preview?.querySelector('del')).not.toBeNull()
  })

  it('ac2 happy: GFM task list - [x] renders a checked checkbox input in preview mode', async () => {
    const container = await renderLoaded('- [x] Done item\n- [ ] Pending item')
    const preview = container.querySelector('[data-testid="ideas-preview"]')
    const checkboxes = preview
      ? [...preview.querySelectorAll('input[type="checkbox"]')]
      : []
    const checkedBoxes = checkboxes.filter((el) => (el as HTMLInputElement).checked)
    expect(checkedBoxes.length).toBeGreaterThan(0)
  })

  it('ac2 error: <script> tag in content is stripped from preview output by rehype-sanitize', async () => {
    const container = await renderLoaded('<script>alert("xss")</script>safe text')
    const preview = container.querySelector('[data-testid="ideas-preview"]')
    expect(preview?.querySelector('script')).toBeNull()
  })

  it('ac2 error: <img onerror=...> has onerror attribute removed from preview by rehype-sanitize', async () => {
    const container = await renderLoaded('<img src="x" onerror="alert(1)">safe text')
    const preview = container.querySelector('[data-testid="ideas-preview"]')
    expect(preview?.querySelector('[onerror]')).toBeNull()
  })

  it('ac2 boundary: empty content renders preview container without error', async () => {
    const container = await renderLoaded('')
    expect(container.querySelector('[data-testid="ideas-preview"]')).not.toBeNull()
  })
})

// ─── AC3: Content preservation across toggle round-trip ───────────────────────

describe('TestFromAC_IdeasPageContentPreservation', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ac3 happy: textarea content is unchanged after preview toggle round-trip', async () => {
    const content = 'Ideas I want to keep'
    const container = await renderLoaded(content)
    await clickToggle(container) // -> edit
    await clickToggle(container) // -> preview
    await clickToggle(container) // -> edit
    const textarea = container.querySelector('textarea')
    expect(textarea?.value).toBe(content)
  })

  it('ac3 happy: user-edited content is preserved after toggle round-trip', async () => {
    const container = await renderLoaded('original')
    await clickToggle(container) // -> edit
    const textarea = container.querySelector('textarea')
    if (textarea) {
      fireEvent.change(textarea, { target: { value: 'edited by user' } })
    }
    await clickToggle(container) // -> preview
    await clickToggle(container) // -> edit
    const textareaAfter = container.querySelector('textarea')
    expect(textareaAfter?.value).toBe('edited by user')
  })

  it('ac3 edge: empty content is preserved after toggle round-trip', async () => {
    const container = await renderLoaded('')
    await clickToggle(container) // -> edit
    await clickToggle(container) // -> preview
    await clickToggle(container) // -> edit
    const textarea = container.querySelector('textarea')
    expect(textarea?.value).toBe('')
  })

  it('ac3 boundary: multiline markdown content preserved verbatim after toggle round-trip', async () => {
    const md = '# Title\n\n- item\n- [x] checked\n\n> quote\n\n```\ncode\n```'
    const container = await renderLoaded(md)
    await clickToggle(container) // -> edit
    await clickToggle(container) // -> preview
    await clickToggle(container) // -> edit
    const textarea = container.querySelector('textarea')
    expect(textarea?.value).toBe(md)
  })
})
