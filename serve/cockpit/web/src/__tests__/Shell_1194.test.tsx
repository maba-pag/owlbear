/**
 * RED phase tests for #1194: P3-06 Implement resolve modal — Shell integration.
 *
 * Covers:
 *   AC1 (Shell): Shell renders ResolveModal with full 'body' field when a DR is selected
 *   AC5 (Shell): After onResolved fires, Shell triggers usePendingDRs re-poll (refetch)
 *
 * All tests FAIL (RED phase) — Shell.tsx does not yet import or render ResolveModal,
 * and usePendingDRs does not expose a refetch function.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn(),
}))

vi.mock('../hooks/useScanPolling', () => ({
  useScanPolling: vi.fn(),
}))

vi.mock('../hooks/usePolling', () => ({
  usePolling: vi.fn(),
}))

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(
    ({
      count,
      onItemClick,
    }: {
      count: number
      items: unknown[]
      onItemClick: (id: string) => void
    }) => (
      <button data-testid="dr-indicator" data-count={count} onClick={() => onItemClick('dr-001')}>
        DR {count}
      </button>
    ),
  ),
}))

// ResolveModal is mocked to:
// (a) track when it's rendered and with what props, and
// (b) expose data-testid="resolve-modal" for DOM assertions.
vi.mock('../components/ResolveModal', () => ({
  default: vi.fn(() => <div data-testid="resolve-modal" />),
}))

// ─── Imports (after mocks) ─────────────────────────────────────────────────────

import { usePendingDRs } from '../hooks/usePendingDRs'
import type { UsePendingDRsResult } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import { usePolling } from '../hooks/usePolling'
import DRStatusIndicator from '../components/DRStatusIndicator'
import type { DRStatusIndicatorProps } from '../components/DRStatusIndicator'
import ResolveModal from '../components/ResolveModal'
import type { ResolveModalProps, PendingDRWithBody } from '../components/ResolveModal'
import Shell from '../Shell'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

// DR fixture includes `body` (full text). After the builder updates PendingDR to
// include `body`, this will be fully typed. The cast bypasses the current missing field.
const DR_A_WITH_BODY: PendingDRWithBody = {
  id: 'dr-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 3_600_000).toISOString(),
  title: 'Should we use approach A?',
  body_preview: 'Context: the builder encountered a fork in the road...',
  body: '## Context\n\nThe builder encountered a fork in the road.\n\n## Options\n\n1. Approach A\n2. Approach B',
}

// ─── Stub helpers ─────────────────────────────────────────────────────────────

const refetchMock = vi.fn()

function stubPendingDRs(partial: Partial<UsePendingDRsResult> = {}): void {
  vi.mocked(usePendingDRs).mockReturnValue(
    // `refetch` will be added by the builder; cast bypasses current missing field
    {
      count: 0,
      items: [],
      isLoading: false,
      error: null,
      refetch: refetchMock,
      ...partial,
    } as unknown as UsePendingDRsResult,
  )
}

function stubPolling(): void {
  vi.mocked(usePolling).mockReturnValue({
    health: 'green',
    skipNextPoll: vi.fn(),
    lastMtime: null,
  })
}

function stubScan(): void {
  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderShell() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <Shell />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Helper: trigger onItemClick on DRStatusIndicator ─────────────────────────

function triggerOnItemClick(id: string): void {
  const calls = vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][]
  const lastProps = calls[calls.length - 1][0]
  act(() => {
    lastProps.onItemClick(id)
  })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ShellResolveModalIntegration', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) =>
        new Promise<never>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError')),
          )
        }),
      ),
    )
    stubPolling()
    stubScan()
    stubPendingDRs({
      count: 1,
      items: [DR_A_WITH_BODY] as unknown as UsePendingDRsResult['items'],
    })
    refetchMock.mockClear()
    vi.mocked(ResolveModal).mockClear()
    vi.mocked(DRStatusIndicator).mockClear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── AC1: Shell renders ResolveModal when DR is selected ──────────────────

  describe('AC1: Shell renders ResolveModal when a DR is selected', () => {
    it('renders [data-testid="resolve-modal"] in the DOM after onItemClick fires', () => {
      const { container } = renderShell()

      // Before selection: resolve-modal must NOT be present
      expect(container.querySelector('[data-testid="resolve-modal"]')).toBeNull()

      // Trigger DR selection
      triggerOnItemClick('dr-001')

      // After selection: resolve-modal must appear
      expect(container.querySelector('[data-testid="resolve-modal"]')).not.toBeNull()
    })

    it('passes a dr prop with body field populated to ResolveModal', () => {
      renderShell()

      triggerOnItemClick('dr-001')

      // ResolveModal mock must have been called
      expect(vi.mocked(ResolveModal)).toHaveBeenCalled()

      const calls = vi.mocked(ResolveModal).mock.calls as unknown as ResolveModalProps[][]
      const lastProps = calls[calls.length - 1][0]

      expect(lastProps.dr).not.toBeNull()
      expect(lastProps.dr?.body).toBeDefined()
      expect(lastProps.dr?.body).toBe(DR_A_WITH_BODY.body)
    })
  })

  // ─── AC5: Shell triggers re-poll after onResolved ─────────────────────────

  describe('AC5: Shell triggers usePendingDRs refetch after onResolved fires', () => {
    it('calls refetch after the ResolveModal onResolved callback is invoked', () => {
      renderShell()

      // Open the modal
      triggerOnItemClick('dr-001')

      // Retrieve the onResolved prop from the ResolveModal mock
      expect(vi.mocked(ResolveModal)).toHaveBeenCalled()
      const calls = vi.mocked(ResolveModal).mock.calls as unknown as ResolveModalProps[][]
      const lastProps = calls[calls.length - 1][0]
      expect(typeof lastProps.onResolved).toBe('function')

      // Trigger resolution
      act(() => {
        lastProps.onResolved()
      })

      // Shell must trigger a re-poll via usePendingDRs refetch
      expect(refetchMock).toHaveBeenCalledOnce()
    })
  })
})
