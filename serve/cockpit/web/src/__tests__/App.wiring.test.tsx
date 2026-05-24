/**
 * App.wiring.1504.test.tsx
 *
 * Tests for task #1504: Implement CockpitProvider and slim Shell.tsx
 *
 * AC-8:  App.tsx provider order: PorscheDesignSystemProvider > data router >
 *        EventSourceProvider > CockpitProvider > ErrorBoundary > Shell
 * AC-9:  Shell.tsx has zero direct calls to useBoard, usePendingDRs, or
 *        useScanPolling; retains only layout and hook-based composition via
 *        useBoardState / useTaskSelection / useDRState
 *
 * Strategy for AC-8:
 *   vi.mock intercepts App's import of CockpitProvider. If App.tsx does not yet
 *   import CockpitProvider (RED), the spy is never called -> assertion fails.
 *   After builder adds CockpitProvider to App (GREEN), rendering App calls the spy.
 *
 * Strategy for AC-9:
 *   useBoard/usePendingDRs/useScanPolling are spied with valid return values so Shell
 *   can render. CockpitProvider consumer hooks are stubbed. Render Shell and assert the
 *   underlying spies were NOT called (Shell must delegate to useBoardState etc.).
 *   In RED (Shell still calls hooks directly) -> spy.toHaveBeenCalled() -> AssertionError.
 *   In GREEN (Shell uses useBoardState/useTaskSelection/useDRState) -> spies not called.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { isValidElement } from 'react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ---- Hoisted mocks ----------------------------------------------------------
// vi.hoisted() runs before vi.mock() factories -- safe to reference in closures.

const capturedCockpitCalls = vi.hoisted(() => [] as { children: unknown }[])

// Stub functions for CockpitProvider consumer hook return values
const mockRefetchTasks = vi.hoisted(() => vi.fn())
const mockScanRefetch = vi.hoisted(() => vi.fn())
const mockSelectTask = vi.hoisted(() => vi.fn())
const mockClearTask = vi.hoisted(() => vi.fn())
const mockUpdateTask = vi.hoisted(() => vi.fn())
const mockSetSelectedDRId = vi.hoisted(() => vi.fn())
const mockRefetchPendingDRs = vi.hoisted(() => vi.fn())

// Underlying hook spies -- must NOT be called by Shell in GREEN (AC-9)
const mockUseBoard = vi.hoisted(() => vi.fn())
const mockUsePendingDRs = vi.hoisted(() => vi.fn())
const mockUseScanPolling = vi.hoisted(() => vi.fn())

// ---- Module mocks -----------------------------------------------------------

vi.mock('../hooks/CockpitProvider', () => ({
  CockpitProvider: vi.fn(({ children }: { children: unknown }) => {
    capturedCockpitCalls.push({ children })
    return children
  }),
  useBoardState: vi.fn(() => ({
    board: null,
    tasks: [],
    loading: false,
    error: null,
    health: 'yellow',
    refetchTasks: mockRefetchTasks,
    items: [],
    isLoading: false,
    scanError: null,
    refetch: mockScanRefetch,
    lastDecisionsMtime: null,
  })),
  useTaskSelection: vi.fn(() => ({
    selectedTaskId: null,
    selectedTask: null,
    selectedTaskError: null,
    select: mockSelectTask,
    clear: mockClearTask,
    update: mockUpdateTask,
  })),
  useDRState: vi.fn(() => ({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: mockRefetchPendingDRs,
    selectedDRId: null,
    setSelectedDRId: mockSetSelectedDRId,
    selectedDR: null,
  })),
}))

vi.mock('../hooks/EventSourceProvider', () => ({
  EventSourceProvider: vi.fn(({ children }: { children: unknown }) => children),
  useSSEEvent: vi.fn(() => ({ mtime: null, status: 'connecting' })),
}))

// Underlying hooks -- spied on; returned values allow Shell to render without crash
vi.mock('../hooks/useBoard', () => ({ useBoard: mockUseBoard }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: mockUsePendingDRs }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: mockUseScanPolling }))

vi.mock('../api/tasks', () => ({
  getTask: vi.fn(() => new Promise(() => {})),
}))

// ---- Imports (after vi.mock registrations) ----------------------------------

import App from '../App'
import Shell from '../Shell'

// ---- Global stubs -----------------------------------------------------------

class MinimalEventSource {
  url: string
  onopen: null = null
  onerror: null = null
  constructor(url: string) {
    this.url = url
  }
  addEventListener() {}
  close() {}
}

// ---- Tests ------------------------------------------------------------------

describe('TestFromAC_CockpitProviderWiring', () => {
  beforeEach(() => {
    capturedCockpitCalls.length = 0
    vi.stubGlobal('EventSource', MinimalEventSource)
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url: string, init?: RequestInit) =>
          new Promise<never>((_resolve, reject) => {
            init?.signal?.addEventListener('abort', () =>
              reject(new DOMException('Aborted', 'AbortError')),
            )
          }),
      ),
    )
    // Provide valid returns so Shell can render without crashing when testing AC-9.
    // The assertions check whether the spies WERE called (RED: yes -> fail) or NOT (GREEN: pass).
    mockUseBoard.mockReturnValue({
      board: null,
      tasks: [],
      loading: false,
      error: null,
      isFetching: false,
      isStale: false,
      health: 'yellow',
      refetchTasks: mockRefetchTasks,
      lastDecisionsMtime: null,
    })
    mockUsePendingDRs.mockReturnValue({
      count: 0,
      items: [],
      isLoading: false,
      error: null,
      refetch: mockRefetchPendingDRs,
    })
    mockUseScanPolling.mockReturnValue({
      items: [],
      isLoading: false,
      error: null,
      refetch: mockScanRefetch,
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ---- AC-8: App.tsx provider order -----------------------------------------

  describe('AC-8: App.tsx provider order includes CockpitProvider', () => {
    it('App renders CockpitProvider during mount', () => {
      render(<App />)
      // CockpitProvider spy must be called. Fails in RED: App.tsx has no CockpitProvider import.
      expect(capturedCockpitCalls.length).toBeGreaterThan(0)
    })

    it('CockpitProvider children contain ErrorBoundary', () => {
      render(<App />)

      expect(capturedCockpitCalls.length).toBeGreaterThan(0)
      const children = capturedCockpitCalls[0].children

      expect(isValidElement(children)).toBe(true)
      const childType = (children as { type: unknown }).type
      const typeName =
        typeof childType === 'function'
          ? ((childType as { displayName?: string; name?: string }).displayName ??
            (childType as { name?: string }).name)
          : String(childType)
      expect(typeName).toBe('ErrorBoundary')
    })

    it('ErrorBoundary child is Shell', () => {
      render(<App />)

      expect(capturedCockpitCalls.length).toBeGreaterThan(0)
      const errorBoundary = capturedCockpitCalls[0].children as {
        props?: { children?: unknown }
      }
      const boundaryChild = errorBoundary.props?.children
      expect(isValidElement(boundaryChild)).toBe(true)
      const innerType = (boundaryChild as { type: unknown }).type
      const innerName =
        typeof innerType === 'function'
          ? ((innerType as { displayName?: string; name?: string }).displayName ??
            (innerType as { name?: string }).name)
          : String(innerType)
      expect(innerName).toBe('Shell')
    })
  })

  // ---- AC-9: Shell.tsx zero direct hook calls --------------------------------

  describe('AC-9: Shell.tsx has zero direct calls to useBoard, usePendingDRs, or useScanPolling', () => {
    // CockpitProvider mock passes children through and returns stub values for
    // useBoardState/useTaskSelection/useDRState. In GREEN, Shell will consume
    // those stubs; the underlying hook spies should remain uncalled.

    const renderShellWithProvider = () =>
      render(
        <PorscheDesignSystemProvider>
          <MemoryRouter initialEntries={['/']}>
            <Shell />
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )

    it('Shell does not call useBoard() directly', () => {
      renderShellWithProvider()
      // RED: Shell imports and calls useBoard -> spy called -> AssertionError fails test.
      // GREEN: Shell calls useBoardState from mocked CockpitProvider -> spy not called.
      expect(mockUseBoard).not.toHaveBeenCalled()
    })

    it('Shell does not call usePendingDRs() directly', () => {
      renderShellWithProvider()
      expect(mockUsePendingDRs).not.toHaveBeenCalled()
    })

    it('Shell does not call useScanPolling() directly', () => {
      renderShellWithProvider()
      expect(mockUseScanPolling).not.toHaveBeenCalled()
    })
  })
})
