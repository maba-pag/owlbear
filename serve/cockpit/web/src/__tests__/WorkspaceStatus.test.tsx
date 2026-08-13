import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import WorkspaceStatus from '../components/WorkspaceStatus'
import { useWorkspaceHealth } from '../hooks/useWorkspaceHealth'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ mtime: null, status: 'closed' as const })),
}))

/** What a sighted operator actually reads, with assistive-technology-only text stripped out. */
function visibleText(element: HTMLElement): string {
  const clone = element.cloneNode(true) as HTMLElement
  clone.querySelectorAll('.sr-only').forEach((node) => { node.remove() })
  return clone.textContent ?? ''
}

function stubHealth(
  memory: unknown,
  ideas: unknown,
) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    const body = url.includes('/health/memory') ? memory : ideas
    if (body === null) return Promise.reject(new TypeError('Failed to fetch'))
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function WorkspaceStatusHarness() {
  const health = useWorkspaceHealth()
  return <WorkspaceStatus health={health} />
}

function SharedWorkspaceStatusHarness() {
  const health = useWorkspaceHealth()
  return <><WorkspaceStatus health={health} /><WorkspaceStatus health={health} /></>
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
  const fetchMock = stubHealth(
    { status: 'healthy', findings: [], repairable_count: 0, checked_paths: [] },
    { status: 'healthy', path: '.owlbear/ideas.md', detail: null },
  )
  render(<SharedWorkspaceStatusHarness />)

  const triggers = screen.getAllByTestId('workspace-status')
  const trigger = triggers[0]
  expect(trigger).toHaveAttribute('data-status', 'unknown')
  expect(trigger).toHaveAttribute('aria-haspopup', 'dialog')
  expect(trigger).toHaveAccessibleName('Workspace health: Not checked; open health details')
  expect(fetchMock).not.toHaveBeenCalled()

  fireEvent.click(trigger)
  const panel = await screen.findByTestId('workspace-status-panel')
  expect(fetchMock).not.toHaveBeenCalled()
  fireEvent.click(screen.getByTestId('workspace-status-recheck'))
  await waitFor(() => expect(trigger).toHaveAttribute('data-status', 'healthy'))
  expect(triggers[1]).toHaveAttribute('data-status', 'healthy')
  expect(fetchMock).toHaveBeenCalledTimes(2)
  expect(fetchMock.mock.calls.every(([, init]) => init === undefined)).toBe(true)
  expect(panel).toHaveAttribute('role', 'dialog')
  expect(panel).toHaveAccessibleName('Workspace health')
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

it('presents workspace health, check scope, and checked surfaces in hierarchy order', async () => {
  stubHealth(
    { status: 'healthy', findings: [], repairable_count: 0, checked_paths: [] },
    { status: 'healthy', path: '.owlbear/ideas.md', detail: null },
  )
  render(<WorkspaceStatusHarness />)

  fireEvent.click(screen.getByTestId('workspace-status'))
  const panel = await screen.findByTestId('workspace-status-panel')

  // The header names the control and its check scope before the rows name individual surfaces.
  const heading = visibleText(panel).slice(0, visibleText(panel).indexOf('Memory store'))
  expect(heading).toBe('Workspace healthPersisted data integrity')
  expect(panel).toHaveAccessibleName('Workspace health')
  expect(visibleText(panel)).toContain('Ideas file')
})

it('advances the freshness label as time passes without issuing another health check', async () => {
  vi.useFakeTimers()
  const fetchMock = stubHealth(
    { status: 'healthy', findings: [], repairable_count: 0, checked_paths: [] },
    { status: 'healthy', path: '.owlbear/ideas.md', detail: null },
  )
  // Fake timers stall async testing helpers, so settle the manual requests through microtasks.
  const settle = async () => { await act(async () => { await Promise.resolve() }) }

  render(<WorkspaceStatusHarness />)
  await settle()
  fireEvent.click(screen.getByTestId('workspace-status'))
  fireEvent.click(screen.getByTestId('workspace-status-recheck'))
  await settle()

  const freshness = screen.getByTestId('workspace-status-freshness')
  expect(freshness).toHaveTextContent('Checked just now')
  const checksSoFar = fetchMock.mock.calls.length

  // Wall-clock time moves on; only the display tick fires and health remains manual.
  act(() => {
    vi.advanceTimersByTime(20 * 60_000)
  })

  expect(freshness).toHaveTextContent('Checked 20m ago')
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
  render(<WorkspaceStatusHarness />)

  const trigger = screen.getByTestId('workspace-status')
  fireEvent.click(trigger)
  fireEvent.click(screen.getByTestId('workspace-status-recheck'))
  await waitFor(() => expect(trigger).toHaveAttribute('data-status', 'attention'))

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
  render(<WorkspaceStatusHarness />)

  const trigger = screen.getByTestId('workspace-status')
  fireEvent.click(trigger)
  fireEvent.click(screen.getByTestId('workspace-status-recheck'))
  await waitFor(() => expect(trigger).toHaveAttribute('data-status', 'unavailable'))
  expect(trigger).toHaveAccessibleName('Workspace health: Cannot be checked; open health details')

  const memoryModule = await screen.findByTestId('workspace-status-module-memory')
  expect(memoryModule).toHaveTextContent('Failed to fetch')
  expect(visibleText(memoryModule)).toContain('Cannot be checked')
})
