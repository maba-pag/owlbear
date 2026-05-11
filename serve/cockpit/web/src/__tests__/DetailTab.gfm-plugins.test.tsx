/**
 * G1 — remark-gfm + rehype-sanitize wiring
 *
 * Verifies that DetailTab passes the correct markdown plugins to ReactMarkdown.
 * rehype-sanitize and wires them into the <ReactMarkdown> call (G1, research doc).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../components/DetailTab'

// ─── Mock react-markdown to capture plugin props ──────────────────────────────
// vi.hoisted ensures the spy is available before module evaluation.

const ReactMarkdownMock = vi.hoisted(() => vi.fn())

vi.mock('react-markdown', () => ({
  default: ReactMarkdownMock,
}))

// ─── Fixture ──────────────────────────────────────────────────────────────────

const TASK: TaskDetail = {
  id: 1,
  title: 'Test task',
  status: 'todo',
  priority: 'important',
  body: '## Hello\n\n~~strikethrough~~\n\n| col1 | col2 |\n|---|---|\n| a | b |\n\n- [ ] task item',
  updated: '2026-04-18T10:00:00+00:00',
  created: '2026-04-17T09:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderDetail() {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={TASK} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_GFMPlugins', () => {
  beforeEach(() => {
    ReactMarkdownMock.mockClear()
    ReactMarkdownMock.mockImplementation(() => null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── remark-gfm wiring ───────────────────────────────────────────────────

  describe('remark-gfm wiring', () => {
    it('DetailTab passes remarkPlugins prop to ReactMarkdown', () => {
      renderDetail()
      expect(ReactMarkdownMock).toHaveBeenCalled()
      const [props] = ReactMarkdownMock.mock.calls[0] as [Record<string, unknown>]
      expect(props).toHaveProperty('remarkPlugins')
    })

    it('remarkPlugins is a non-empty array', () => {
      renderDetail()
      const [props] = ReactMarkdownMock.mock.calls[0] as [Record<string, unknown>]
      const remarkPlugins = props['remarkPlugins'] as unknown[]
      expect(Array.isArray(remarkPlugins)).toBe(true)
      expect(remarkPlugins.length).toBeGreaterThan(0)
    })

    it('remarkPlugins contains a callable plugin (remark-gfm)', () => {
      renderDetail()
      const [props] = ReactMarkdownMock.mock.calls[0] as [Record<string, unknown>]
      const remarkPlugins = props['remarkPlugins'] as unknown[]
      expect(remarkPlugins.some((p) => typeof p === 'function')).toBe(true)
    })
  })

  // ─── rehype-sanitize wiring ───────────────────────────────────────────────

  describe('rehype-sanitize wiring', () => {
    it('DetailTab passes rehypePlugins prop to ReactMarkdown', () => {
      renderDetail()
      expect(ReactMarkdownMock).toHaveBeenCalled()
      const [props] = ReactMarkdownMock.mock.calls[0] as [Record<string, unknown>]
      expect(props).toHaveProperty('rehypePlugins')
    })

    it('rehypePlugins is a non-empty array', () => {
      renderDetail()
      const [props] = ReactMarkdownMock.mock.calls[0] as [Record<string, unknown>]
      const rehypePlugins = props['rehypePlugins'] as unknown[]
      expect(Array.isArray(rehypePlugins)).toBe(true)
      expect(rehypePlugins.length).toBeGreaterThan(0)
    })

    it('rehypePlugins contains a callable plugin (rehype-sanitize)', () => {
      renderDetail()
      const [props] = ReactMarkdownMock.mock.calls[0] as [Record<string, unknown>]
      const rehypePlugins = props['rehypePlugins'] as unknown[]
      expect(rehypePlugins.some((p) => typeof p === 'function')).toBe(true)
    })
  })
})

