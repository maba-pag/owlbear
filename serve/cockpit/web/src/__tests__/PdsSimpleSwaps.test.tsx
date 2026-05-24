/**
 * Frontend — PDS simple component swaps (task #1614)
 *
 * AC-1: Zero raw <select> in source .tsx files — regression guard, pre-satisfied.
 *       No RED tests possible (all would be green). Noted in AC coverage table.
 * AC-2: session-row → PButton (ActivityTab); resolve-button → PButton (DRStatusIndicator);
 *       retry button → PButton (ErrorBoundary). data-testid and onClick preserved.
 * AC-3: Shell title uses the PCanvas title slot; Shell no longer renders the
 *       retired PCanvas sidebar-end-header; DetailTab
 *       <h3> (Actions) → PHeading tag="h3"; ErrorBoundary <h3> → PHeading tag="h3".
 * AC-4: Raw <button> only where data-pds-exception attribute applies.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ActivityTab from '../components/ActivityTab'
import DRStatusIndicator from '../components/DRStatusIndicator'
import DecisionViewport from '../components/DecisionViewport'
import { ErrorBoundary } from '../components/ErrorBoundary'
import DetailTab, { type TaskDetail } from '../components/DetailTab'
import TaskFieldsEditor from '../components/TaskFieldsEditor'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import type { PendingDR } from '../hooks/usePendingDRs'
import { usePollingFetch } from '../hooks/usePollingFetch'
import type { TaskFieldsEditorProps } from '../components/TaskFieldsEditor'

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../hooks/usePollingFetch', () => ({
  usePollingFetch: vi.fn((_url: string, _options?: unknown) => ({
    isFetching: false,
    hasFetched: false,
    refetch: vi.fn(),
  })),
}))

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

vi.mock('remark-gfm', () => ({ default: () => {} }))
vi.mock('rehype-sanitize', () => ({ default: () => {} }))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const SESSION_FIXTURE = {
  task_id: 42,
  agent: 'builder',
  state: 'running',
  duration: 120,
  outcome: null,
}

const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'in-progress',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-05-01T10:00:00+00:00',
  created: '2026-04-01T09:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
}

const TASK_FIELDS: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: 'Some body text.',
  updated: '2026-05-01T12:00:00+00:00',
  created: '2026-05-01T10:00:00+00:00',
  tags: ['bug'],
  blocked: false,
  block_reason: null,
  claimed: false,
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [],
}

const DR_PENDING = {
  id: 'dr-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  title: 'Should we use approach A?',
  body_preview: 'Context...',
}

const DR_A: PendingDR = {
  id: 'dr-1634-a',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 2 * 3_600_000).toISOString(),
  title: 'Should we refactor the cache?',
  body: '## Context\n\nSome context.',
  body_preview: 'Consider architectural simplification.',
}

const DR_B: PendingDR = {
  id: 'dr-1634-b',
  task_id: 99,
  agent: 'architect',
  request_type: 'user-action',
  created: new Date(Date.now() - 25 * 3_600_000).toISOString(),
  title: 'Confirm scope change.',
  body: '## Scope\n\nPhase 2 scope.',
  body_preview: 'Confirm the feature boundary.',
}

// ─── Render helpers ────────────────────────────────────────────────────────────

function renderActivityTab(onSelectTask?: (taskId: number, subtab?: string) => void) {
  return render(
    <PorscheDesignSystemProvider>
      <ActivityTab onSelectTask={onSelectTask} />
    </PorscheDesignSystemProvider>,
  )
}

function renderDRIndicator(count = 1, items = [DR_PENDING], onItemClick = vi.fn()) {
  return render(
    <PorscheDesignSystemProvider>
      <DRStatusIndicator count={count} items={items} onItemClick={onItemClick} />
    </PorscheDesignSystemProvider>,
  )
}

function renderErrorBoundaryInError(label?: string) {
  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  function ThrowError(): never {
    throw new Error('Test error')
  }
  const result = render(
    <PorscheDesignSystemProvider>
      <ErrorBoundary label={label}>
        <ThrowError />
      </ErrorBoundary>
    </PorscheDesignSystemProvider>,
  )
  consoleSpy.mockRestore()
  return result
}

function renderDetailTab(task: TaskDetail = TASK) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
    </PorscheDesignSystemProvider>,
  )
}

function renderTaskFieldsEditor(overrides: Partial<TaskFieldsEditorProps> = {}) {
  const defaults: TaskFieldsEditorProps = {
    task: TASK_FIELDS,
    priorities: ['someday', 'needed', 'important', 'critical'],
    conflictLocalDraft: null,
    conflictRemoteTaskId: null,
    serverValidationMessage: null,
    clearConflictIfTaskChanged: vi.fn(),
    onSave: vi.fn().mockResolvedValue(undefined),
  }
  return render(
    <PorscheDesignSystemProvider>
      <TaskFieldsEditor {...defaults} {...overrides} />
    </PorscheDesignSystemProvider>,
  )
}

function renderDecisionViewport({
  items = [] as PendingDR[],
  isLoading = false,
  error = null as Error | null,
  onItemClick = vi.fn(),
} = {}) {
  return render(
    <PorscheDesignSystemProvider>
      <DecisionViewport
        items={items}
        isLoading={isLoading}
        error={error}
        onItemClick={onItemClick}
      />
    </PorscheDesignSystemProvider>,
  )
}

function renderShell() {
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
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// Helper: inject sessions into ActivityTab via the mocked usePollingFetch onSuccess callback.
async function injectSessions(sessions = [SESSION_FIXTURE]) {
  const calls = vi.mocked(usePollingFetch).mock.calls
  const sessionCall = [...calls].reverse().find(([url]) =>
    typeof url === 'string' && url.includes('/api/sessions'),
  )
  const options = sessionCall?.[1] as
    | { onSuccess?: (data: { sessions: typeof sessions }) => void }
    | undefined
  if (options?.onSuccess) {
    await act(async () => {
      options.onSuccess!({ sessions })
    })
  }
}

// ─── AC-2: ActivityTab session-row → PButton ──────────────────────────────────

describe('TestFromAC_SimpleSwaps_ActivityTabSessionRow', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.mocked(usePollingFetch).mockClear()
  })

  it('session-row renders as p-button (not native button) after sessions load', async () => {
    const { container } = renderActivityTab()
    await injectSessions()
    expect(container.querySelector('p-button[data-testid="session-row"]')).not.toBeNull()
  })

  it('no native <button data-testid="session-row"> after sessions load', async () => {
    const { container } = renderActivityTab()
    await injectSessions()
    expect(container.querySelector('button[data-testid="session-row"]')).toBeNull()
  })

  it('session-row tag is p-button (data-testid preserved on correct host)', async () => {
    const { container } = renderActivityTab()
    await injectSessions()
    const sessionRow = container.querySelector('[data-testid="session-row"]')
    expect(sessionRow?.tagName.toLowerCase()).toBe('p-button')
  })

  it('session-row p-button onClick fires onSelectTask with taskId and history subtab', async () => {
    const onSelectTask = vi.fn()
    const { container } = renderActivityTab(onSelectTask)
    await injectSessions()
    const sessionRow = container.querySelector('p-button[data-testid="session-row"]')
    expect(sessionRow).not.toBeNull()
    fireEvent.click(sessionRow!)
    expect(onSelectTask).toHaveBeenCalledWith(42, 'history')
  })

  it('no unexcepted native <button> in ActivityTab when sessions loaded (AC4)', async () => {
    const { container } = renderActivityTab()
    await injectSessions()
    const rawButtons = Array.from(container.querySelectorAll('button'))
    const unexcepted = rawButtons.filter((b) => !b.hasAttribute('data-pds-exception'))
    expect(unexcepted).toHaveLength(0)
  })
})

// ─── AC-2: DRStatusIndicator resolve-button → PButton ────────────────────────

describe('TestFromAC_SimpleSwaps_DRResolveButton', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.mocked(usePollingFetch).mockClear()
  })

  it('resolve-button renders as p-button after popover opens', () => {
    const { container } = renderDRIndicator()
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    expect(container.querySelector('p-button[data-testid="resolve-button"]')).not.toBeNull()
  })

  it('no native <button data-testid="resolve-button"> in open popover', () => {
    const { container } = renderDRIndicator()
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    expect(container.querySelector('button[data-testid="resolve-button"]')).toBeNull()
  })

  it('resolve-button tag is p-button (data-testid preserved on correct host)', () => {
    const { container } = renderDRIndicator()
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    const resolveBtn = container.querySelector('[data-testid="resolve-button"]')
    expect(resolveBtn?.tagName.toLowerCase()).toBe('p-button')
  })

  it('resolve-button p-button onClick calls onItemClick with item id', () => {
    const onItemClick = vi.fn()
    const { container } = renderDRIndicator(1, [DR_PENDING], onItemClick)
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    const resolveBtn = container.querySelector('p-button[data-testid="resolve-button"]')
    expect(resolveBtn).not.toBeNull()
    fireEvent.click(resolveBtn!)
    expect(onItemClick).toHaveBeenCalledWith(DR_PENDING.id)
  })

  it('no unexcepted native <button> in DRStatusIndicator when popover open (AC4)', () => {
    const { container } = renderDRIndicator()
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    const rawButtons = Array.from(container.querySelectorAll('button'))
    const unexcepted = rawButtons.filter((b) => !b.hasAttribute('data-pds-exception'))
    expect(unexcepted).toHaveLength(0)
  })
})

// ─── AC-2: ErrorBoundary retry button → PButton ──────────────────────────────

describe('TestFromAC_SimpleSwaps_ErrorBoundaryRetry', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.mocked(usePollingFetch).mockClear()
  })

  it('retry button in error state renders as p-button (not native button)', () => {
    const { container } = renderErrorBoundaryInError()
    expect(container.querySelector('p-button')).not.toBeNull()
  })

  it('no unexcepted native <button> in ErrorBoundary error state (AC4)', () => {
    const { container } = renderErrorBoundaryInError()
    const rawButtons = Array.from(container.querySelectorAll('button'))
    const unexcepted = rawButtons.filter((b) => !b.hasAttribute('data-pds-exception'))
    expect(unexcepted).toHaveLength(0)
  })

  it('retry p-button onClick resets error state (children render after retry)', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    let shouldThrow = true
    function ConditionalThrow(): JSX.Element {
      if (shouldThrow) throw new Error('Test error')
      return <div data-testid="recovered">Recovered</div>
    }
    const { container } = render(
      <PorscheDesignSystemProvider>
        <ErrorBoundary>
          <ConditionalThrow />
        </ErrorBoundary>
      </PorscheDesignSystemProvider>,
    )
    const retryBtn = container.querySelector('p-button')
    expect(retryBtn).not.toBeNull()
    shouldThrow = false
    fireEvent.click(retryBtn!)
    expect(container.querySelector('[data-testid="recovered"]')).not.toBeNull()
    consoleSpy.mockRestore()
  })
})

// ─── AC-3: Shell app title → PCanvas title slot ──────────────────────────────

describe('TestFromAC_SimpleSwaps_ShellH1', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.mocked(usePollingFetch).mockClear()
  })

  it('Shell renders app identity in a visually hidden PCanvas title slot', () => {
    const { container } = renderShell()
    const title = container.querySelector('[slot="title"]')
    expect(title).not.toBeNull()
    expect(title?.textContent).toContain('OwlBear Cockpit')
    expect(title?.classList.contains('sr-only')).toBe(true)
  })

  it('Shell title slot is a non-interactive label owned by PCanvas', () => {
    const { container } = renderShell()
    const title = container.querySelector('[slot="title"]')
    expect(title?.tagName.toLowerCase()).toBe('span')
  })

  it('no raw <h1> anywhere in Shell', () => {
    const { container } = renderShell()
    expect(container.querySelector('h1')).toBeNull()
  })

  it('status-bar no longer owns the app title heading after PCanvas migration', () => {
    const { container } = renderShell()
    const statusBar = container.querySelector('[data-region="status-bar"]')
    expect(statusBar?.textContent).not.toContain('OwlBear Cockpit')
  })
})

// ─── AC-3: Shell does not render retired sidebar-end heading ────────────────

describe('TestFromAC_SimpleSwaps_ShellH2', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.mocked(usePollingFetch).mockClear()
  })

  it('Shell does not render p-heading in the retired PCanvas sidebar-end-header slot', () => {
    const { container } = renderShell()
    expect(container.querySelector('p-heading[slot="sidebar-end-header"]')).toBeNull()
  })

  it('Shell does not render any sidebar-end header slot content', () => {
    const { container } = renderShell()
    expect(container.querySelector('[slot="sidebar-end-header"]')).toBeNull()
  })

  it('no raw <h2> in Shell light DOM', () => {
    const { container } = renderShell()
    expect(container.querySelector('h2')).toBeNull()
  })

  it('task detail modal is not mounted before task selection', () => {
    const { container } = renderShell()
    expect(container.querySelector('[data-testid="task-detail-modal"]')).toBeNull()
  })
})

// ─── AC-3: DetailTab <h3> (Actions) → PHeading tag="h3" ──────────────────────

describe('TestFromAC_SimpleSwaps_DetailTabH3', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.mocked(usePollingFetch).mockClear()
  })

  it('actions section renders p-heading (replaces raw <h3>)', () => {
    const { container } = renderDetailTab()
    const actions = container.querySelector('[data-region="actions"]')
    expect(actions?.querySelector('p-heading')).not.toBeNull()
  })

  it('actions p-heading has tag="h3"', () => {
    const { container } = renderDetailTab()
    const actions = container.querySelector('[data-region="actions"]')
    const heading = actions?.querySelector('p-heading')
    expect(heading?.getAttribute('tag')).toBe('h3')
  })

  it('no raw <h3> in DetailTab actions section', () => {
    const { container } = renderDetailTab()
    const actions = container.querySelector('[data-region="actions"]')
    expect(actions?.querySelector('h3')).toBeNull()
  })

  it('actions p-heading contains "Actions"', () => {
    const { container } = renderDetailTab()
    const actions = container.querySelector('[data-region="actions"]')
    const heading = actions?.querySelector('p-heading')
    expect(heading?.textContent).toContain('Actions')
  })
})

// ─── AC-3: ErrorBoundary <h3> → PHeading tag="h3" ────────────────────────────

describe('TestFromAC_SimpleSwaps_ErrorBoundaryH3', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.mocked(usePollingFetch).mockClear()
  })

  it('error state renders p-heading (replaces raw <h3>)', () => {
    const { container } = renderErrorBoundaryInError()
    expect(container.querySelector('p-heading')).not.toBeNull()
  })

  it('error state p-heading has tag="h3"', () => {
    const { container } = renderErrorBoundaryInError()
    const heading = container.querySelector('p-heading')
    expect(heading?.getAttribute('tag')).toBe('h3')
  })

  it('no raw <h3> in ErrorBoundary error state', () => {
    const { container } = renderErrorBoundaryInError()
    expect(container.querySelector('h3')).toBeNull()
  })

  it('error state p-heading contains "Something went wrong"', () => {
    const { container } = renderErrorBoundaryInError()
    const heading = container.querySelector('p-heading')
    expect(heading?.textContent).toContain('Something went wrong')
  })
})

describe('TestFromAC_PdsSimpleSwaps_TaskFieldsEditor', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('TaskFieldsEditor p-select renders p-select-option children with no native OPTION elements', () => {
    const { container } = renderTaskFieldsEditor()
    const pSelect = container.querySelector('p-select')
    expect(pSelect).not.toBeNull()
    expect(pSelect?.querySelector('p-select-option')).not.toBeNull()
    const nativeCount = Array.from(pSelect?.children ?? []).filter((child) => child.tagName === 'OPTION').length
    expect(nativeCount).toBe(0)
  })
})

describe('TestFromAC_PdsSimpleSwaps_DecisionViewport', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('DecisionViewport task-ref renders as p-link-pure with href on the host and icon none', () => {
    const onItemClick = vi.fn()
    const { container } = renderDecisionViewport({ items: [DR_A], onItemClick })
    const taskRef = container.querySelector('[data-testid="decision-task-ref-dr-1634-a"]')

    expect(taskRef).not.toBeNull()
    expect(taskRef?.tagName.toLowerCase()).toBe('p-link-pure')
    expect(taskRef?.getAttribute('href')).toMatch(/^#task-\d+$/)
    expect(taskRef?.getAttribute('icon')).toBe('none')

    fireEvent.click(taskRef!)
    expect(onItemClick).toHaveBeenCalledWith('dr-1634-a')
  })

  it('each DecisionViewport task-ref element is p-link-pure with href preserved on the host', () => {
    const { container } = renderDecisionViewport({ items: [DR_A, DR_B] })
    const taskRefs = container.querySelectorAll('[data-testid^="decision-task-ref-"]')

    expect(taskRefs.length).toBe(2)
    for (const taskRef of Array.from(taskRefs)) {
      expect(taskRef.tagName.toLowerCase()).toBe('p-link-pure')
      expect(taskRef.getAttribute('href')).toMatch(/^#task-\d+$/)
    }
  })
})
