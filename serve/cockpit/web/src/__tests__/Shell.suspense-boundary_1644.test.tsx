/**
 * Task #1644 — P1-04: Lazy loading — React.lazy() with Suspense boundary
 * AC1 coverage (Shell.tsx): <Routes> is wrapped in
 *   <Suspense fallback={<div data-testid="route-loading" />}>
 *
 * Routes are mocked to return a single lazy component that never resolves
 * (suspends indefinitely). Without a Suspense boundary in Shell.tsx, React
 * throws an uncaught suspension error (RED failure). With the boundary, the
 * fallback element renders and data-testid="route-loading" is found.
 *
 * RED phase: Shell.tsx has no <Suspense> wrapping <Routes> → render() throws,
 *            test fails with uncaught React suspension error.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

// ── Module mocks ──────────────────────────────────────────────────────────────

// Provide a single route whose component is a lazy component that suspends
// indefinitely. When Shell renders this route, the lazy component will throw a
// Promise, triggering the Suspense fallback (or crashing without one).
vi.mock('../routes', async () => {
  const { lazy } = await import('react')
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const SuspendingComponent = lazy((): Promise<any> => new Promise(() => {}))
  return {
    routeConfig: [{ path: '/', label: 'Kanban', icon: 'kanban', component: SuspendingComponent }],
  }
})

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// ── Per-test setup ────────────────────────────────────────────────────────────

beforeEach(() => {
  // Suppress React's error output for missing Suspense boundary (RED phase noise).
  vi.spyOn(console, 'error').mockImplementation(() => {})
  // Never-resolving fetch keeps board/scan/DR hooks in loading state, preventing
  // state-update warnings after assertions.
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
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TestFromAC_ShellSuspenseBoundary', () => {
  // ── AC1: Suspense boundary renders route-loading fallback ─────────────────
  it('ac1 smoke: Shell shows route-loading fallback while lazy route component is loading', () => {
    // The mocked route component suspends indefinitely.
    // In RED: no <Suspense> in Shell.tsx → render() throws an uncaught error.
    // In GREEN: <Suspense fallback={<div data-testid="route-loading" />}> wraps
    //           <Routes>, so the fallback renders and the testid is found.
    renderShell('/')
    expect(screen.getByTestId('route-loading')).not.toBeNull()
  })
})
