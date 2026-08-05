import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import WorkspaceStatus from '../components/WorkspaceStatus'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ mtime: null, status: 'closed' as const })),
}))

/** What a sighted operator actually reads, with assistive-technology-only text stripped out. */
function visibleText(element: HTMLElement): string {
  const clone = element.cloneNode(true) as HTMLElement
  clone.querySelectorAll('.sr-only').forEach((node) => { node.remove() })
  return clone.textContent ?? ''
}

function stubHealth(memory: unknown, ideas: unknown) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    const body = url.includes('/health/memory') ? memory : ideas
    if (body === null) return Promise.reject(new TypeError('Failed to fetch'))
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

it('states healthy persisted-data modules without prose, repair, or a Memory detour', async () => {
  stubHealth(
    { status: 'healthy', findings: [], repairable_count: 0, checked_paths: [] },
    { status: 'healthy', path: '.owlbear/ideas.md', detail: null },
  )
  render(<WorkspaceStatus />)

  const trigger = screen.getByTestId('workspace-status')
  await waitFor(() => expect(trigger).toHaveAttribute('data-status', 'healthy'))
  expect(trigger).toHaveAttribute('aria-haspopup', 'dialog')
  expect(trigger).toHaveAccessibleName('Memory and Ideas health: Healthy; open health details')

  fireEvent.click(trigger)
  const panel = await screen.findByTestId('workspace-status-panel')
  expect(panel).toHaveAttribute('role', 'dialog')
  expect(panel).toHaveAccessibleName('Memory and Ideas health')
  const memoryModule = screen.getByTestId('workspace-status-module-memory')
  expect(memoryModule).toHaveTextContent('Memory store')
  expect(memoryModule).not.toHaveTextContent('No storage issues found')
  const ideasModule = screen.getByTestId('workspace-status-module-ideas')
  expect(ideasModule).not.toHaveTextContent('.owlbear/ideas.md')
  expect(ideasModule).not.toHaveTextContent('readable')

  // The green dot carries healthy on screen; the word stays for assistive technology only.
  for (const module of [memoryModule, ideasModule]) {
    expect(module).toHaveTextContent('Healthy')
    expect(visibleText(module)).not.toContain('Healthy')
  }
  expect(visibleText(memoryModule)).toContain('Memory store')
  expect(visibleText(ideasModule)).toContain('Ideas file')

  expect(screen.queryByTestId('workspace-status-maintenance')).toBeNull()
  expect(panel).not.toHaveTextContent('Memory lists entries')
  expect(panel).not.toHaveTextContent('repair')
  await waitFor(() => expect(screen.getByTestId('workspace-status-freshness')).toHaveTextContent('Checked just now'))
  expect(screen.getByTestId('workspace-status-recheck')).toHaveTextContent('Re-check')
})

it('names the checked property once and the checked surfaces once', async () => {
  stubHealth(
    { status: 'healthy', findings: [], repairable_count: 0, checked_paths: [] },
    { status: 'healthy', path: '.owlbear/ideas.md', detail: null },
  )
  render(<WorkspaceStatus />)

  fireEvent.click(screen.getByTestId('workspace-status'))
  const panel = await screen.findByTestId('workspace-status-panel')

  // The heading states what is checked about the data and nothing else; only the rows name surfaces.
  const heading = visibleText(panel).slice(0, visibleText(panel).indexOf('Memory store'))
  expect(heading).toBe('Persisted data integrity')
  // Scope stays in the row names and the dialog name, never in a defensive sentence.
  expect(panel).toHaveAccessibleName('Memory and Ideas health')
  expect(visibleText(panel)).toContain('Ideas file')
})

it('advances the freshness label as time passes without issuing another health check', async () => {
  vi.useFakeTimers()
  const fetchMock = stubHealth(
    { status: 'healthy', findings: [], repairable_count: 0, checked_paths: [] },
    { status: 'healthy', path: '.owlbear/ideas.md', detail: null },
  )
  // Fake timers stall the library's polling helpers, so settle work by flushing microtasks instead.
  const settle = async () => { await act(async () => { await Promise.resolve() }) }

  render(<WorkspaceStatus />)
  await settle()
  fireEvent.click(screen.getByTestId('workspace-status'))
  await settle()

  const freshness = screen.getByTestId('workspace-status-freshness')
  expect(freshness).toHaveTextContent('Checked just now')
  const checksSoFar = fetchMock.mock.calls.length

  // Wall-clock time moves on; only the display tick fires, staying below the 60s poll interval.
  act(() => {
    vi.setSystemTime(Date.now() + 3 * 60_000)
    vi.advanceTimersByTime(30_000)
  })

  expect(freshness).toHaveTextContent('Checked 3m ago')
  expect(fetchMock.mock.calls.length).toBe(checksSoFar)
})

it('ranks the worst module status and lists memory storage findings without claiming repair', async () => {
  stubHealth(
    {
      status: 'attention',
      findings: [{ path: 'store/memory/x.md', code: 'missing-scope', detail: 'scope is absent' }],
      repairable_count: 0,
      checked_paths: ['store/memory/x.md'],
    },
    { status: 'healthy', path: '.owlbear/ideas.md', detail: null },
  )
  render(<WorkspaceStatus />)

  const trigger = screen.getByTestId('workspace-status')
  await waitFor(() => expect(trigger).toHaveAttribute('data-status', 'attention'))

  fireEvent.click(trigger)
  const memoryModule = await screen.findByTestId('workspace-status-module-memory')
  // A problem state is never left to colour alone: the word stays on screen.
  expect(visibleText(memoryModule)).toContain('Needs attention')
  expect(memoryModule).toHaveTextContent('1 storage issue found')
  expect(memoryModule).not.toHaveTextContent('repair')
  expect(screen.getByText('store/memory/x.md — missing-scope — scope is absent')).toBeInTheDocument()

  fireEvent.keyDown(screen.getByTestId('workspace-status-panel'), { key: 'Escape' })
  await waitFor(() => expect(screen.queryByTestId('workspace-status-panel')).not.toBeInTheDocument())
  expect(document.activeElement).toBe(trigger)
})

it('reports an unreachable health check instead of claiming health', async () => {
  stubHealth(null, null)
  render(<WorkspaceStatus />)

  const trigger = screen.getByTestId('workspace-status')
  await waitFor(() => expect(trigger).toHaveAttribute('data-status', 'unavailable'))
  expect(trigger).toHaveAccessibleName('Memory and Ideas health: Cannot be checked; open health details')

  fireEvent.click(trigger)
  const memoryModule = await screen.findByTestId('workspace-status-module-memory')
  expect(memoryModule).toHaveTextContent('Failed to fetch')
  expect(visibleText(memoryModule)).toContain('Cannot be checked')
})
