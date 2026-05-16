/**
 * Implement resolve modal — ResolveModal plugin props.
 *
 * Covers:
 *   AC8  — ResolveModal passes remarkGfm to ReactMarkdown's remarkPlugins
 *   AC10 — ResolveModal passes rehypeSanitize to ReactMarkdown's rehypePlugins
 *
 * ReactMarkdown is mocked so we can inspect the exact props passed. Both tests
 * without any remarkPlugins or rehypePlugins.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'

// ─── react-markdown mock ──────────────────────────────────────────────────────
// Mocked BEFORE importing the component so Vitest's static hoisting applies.
// The spy captures the exact props (remarkPlugins, rehypePlugins) that
// ResolveModal passes to ReactMarkdown.

vi.mock('react-markdown', () => ({
  default: vi.fn(({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  )),
}))

import ReactMarkdown from 'react-markdown'
import ResolveModal from '../components/ResolveModal'

// ─── Fixture ──────────────────────────────────────────────────────────────────

interface PendingDRWithBody {
  id: string
  task_id: number
  agent: string
  request_type: string
  created: string
  title: string
  body_preview: string
  body: string
}

const DR_FIXTURE: PendingDRWithBody = {
  id: 'ac8-ac10-test',
  task_id: 99,
  agent: 'builder',
  request_type: 'scope-decision',
  created: '2026-04-30T10:00:00+02:00',
  title: 'Plugin verification DR',
  body_preview: 'Preview text.',
  body: '## Context\n\nThis DR body is rendered with plugins.\n\n~~Strikethrough~~ and more.',
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderModal(dr: PendingDRWithBody | null = DR_FIXTURE) {
  return render(
    <PorscheDesignSystemProvider>
      <ResolveModal dr={dr} onClose={vi.fn()} onResolved={vi.fn()} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ResolveModalPlugins', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  // ─── AC8: remarkGfm plugin ─────────────────────────────────────────────────

  describe('AC8: ReactMarkdown receives remarkGfm in remarkPlugins (matches DetailTab pattern)', () => {
    it('passes remarkGfm as a remarkPlugin to ReactMarkdown', () => {
      renderModal()

      expect(vi.mocked(ReactMarkdown)).toHaveBeenCalled()

      // Retrieve the props that ResolveModal passed to ReactMarkdown
      const calls = vi.mocked(ReactMarkdown).mock.calls
      const lastCallProps = calls[calls.length - 1][0] as Record<string, unknown>

      const remarkPlugins = (lastCallProps.remarkPlugins as unknown[] | undefined) ?? []
      expect(remarkPlugins).toContainEqual(remarkGfm)
    })
  })

  // ─── AC10: rehypeSanitize plugin ───────────────────────────────────────────

  describe('AC10: ReactMarkdown receives rehypeSanitize in rehypePlugins (XSS prevention)', () => {
    it('passes rehypeSanitize as a rehypePlugin to ReactMarkdown', () => {
      renderModal()

      expect(vi.mocked(ReactMarkdown)).toHaveBeenCalled()

      const calls = vi.mocked(ReactMarkdown).mock.calls
      const lastCallProps = calls[calls.length - 1][0] as Record<string, unknown>

      const rehypePlugins = (lastCallProps.rehypePlugins as unknown[] | undefined) ?? []
      expect(rehypePlugins).toContainEqual(rehypeSanitize)
    })
  })
})
