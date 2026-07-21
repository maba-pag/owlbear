/**
 * Frontend — PDS migration regression guards (design system consistency)
 *
 * Trimmed to representative tests: one "no raw element" assertion per AC category
 * plus one payload propagation test. These catch any regression back to raw HTML.
 *
 * AC1: <button> → <PButton>
 * AC2: <h3> → <PHeading tag="h3">
 * AC3: standalone <p> → <PText> / PInlineNotification
 * AC4: form controls → PInputText/PSelect/PTextarea
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ConfirmDialog from '../components/ConfirmDialog'
import ArchivalModal from '../components/ArchivalModal'
import ActivityTab from '../components/ActivityTab'
import DetailTab, { type TaskDetail } from '../components/DetailTab'
import ResolveModal from '../components/ResolveModal'
import WorkspaceStatus from '../components/WorkspaceStatus'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

vi.mock('remark-gfm', () => ({ default: () => {} }))
vi.mock('rehype-sanitize', () => ({ default: () => {} }))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

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
  claimed: false,
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [],
  proof_bundle: null,
}

const DR_FIXTURE = {
  id: '42-scope-question',
  task_id: 42,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-04-30T14:30:00+00:00',
  title: 'Scope question',
  summary: 'Should we include X?',
  kind: 'decision' as const,
  options: [],
  body_preview: 'Context: Should we include X?',
  body: '## Context\n\nShould we include X?',
}

// ─── Render helpers ────────────────────────────────────────────────────────────

function renderConfirm() {
  return render(
    <PorscheDesignSystemProvider>
      <ConfirmDialog type="move-backward" onCancel={vi.fn()} onConfirm={vi.fn()} />
    </PorscheDesignSystemProvider>,
  )
}

function renderArchival() {
  return render(
    <PorscheDesignSystemProvider>
      <ArchivalModal
        taskId={42}
        taskStatus="in-progress"
        expectedUpdated="2026-05-01T10:00:00+00:00"
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    </PorscheDesignSystemProvider>,
  )
}

function renderActivityTab() {
  vi.stubGlobal('fetch', vi.fn(() => new Promise<never>(() => {})))
  return render(
    <PorscheDesignSystemProvider>
      <ActivityTab />
    </PorscheDesignSystemProvider>,
  )
}

function renderDetailTab(task: TaskDetail = TASK) {
  vi.stubGlobal('fetch', vi.fn(() => new Promise<never>(() => {})))
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
    </PorscheDesignSystemProvider>,
  )
}

function openDetailEditor(container: HTMLElement): void {
  const editButton = container.querySelector('[data-testid="edit-details-button"]') as HTMLElement | null
  expect(editButton).not.toBeNull()
  fireEvent.click(editButton!)
}

function renderResolveModal() {
  return render(
    <PorscheDesignSystemProvider>
      <ResolveModal dr={DR_FIXTURE} onClose={vi.fn()} onResolved={vi.fn()} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── AC1: no raw <button> in migrated components ──────────────────────────────

describe('PdsMigration_Buttons', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  it('ConfirmDialog has no raw <button> elements', () => {
    const { container } = renderConfirm()
    expect(container.querySelectorAll('button')).toHaveLength(0)
  })

  it('ArchivalModal has no raw <button> elements', () => {
    const { container } = renderArchival()
    expect(container.querySelectorAll('button')).toHaveLength(0)
  })

  it('ActivityTab has no raw <button> elements', () => {
    const { container } = renderActivityTab()
    expect(container.querySelectorAll('button')).toHaveLength(0)
  })

  it('DetailTab has no raw <button> elements', () => {
    const { container } = renderDetailTab()
    expect(container.querySelectorAll('button')).toHaveLength(0)
  })

  it('ResolveModal has no raw <button> elements', () => {
    const { container } = renderResolveModal()
    expect(container.querySelectorAll('button')).toHaveLength(0)
  })
})

// ─── AC2: no raw <h3> in modals ──────────────────────────────────────────────

describe('PdsMigration_Headings', () => {
  it('ArchivalModal has no raw <h3> (uses PHeading)', () => {
    const { container } = renderArchival()
    expect(container.querySelectorAll('h3')).toHaveLength(0)
    expect(container.querySelector('p-heading')).not.toBeNull()
  })

  it('ResolveModal has no raw <h3> (uses PHeading)', () => {
    const { container } = renderResolveModal()
    expect(container.querySelectorAll('h3')).toHaveLength(0)
    expect(container.querySelector('p-heading')).not.toBeNull()
  })
})

// ─── AC3: no raw <p> for empty states / error messages ────────────────────────

describe('PdsMigration_Text', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  it('ArchivalModal uses PSelect and PButton (no raw select/button)', () => {
    const { container } = render(
      <PorscheDesignSystemProvider>
        <ArchivalModal
          taskId={42}
          taskStatus="in-progress"
          expectedUpdated="2026-05-01T10:00:00+00:00"
          onClose={vi.fn()}
          onRefresh={vi.fn()}
        />
      </PorscheDesignSystemProvider>,
    )
    expect(container.querySelector('p-select')).not.toBeNull()
    expect(container.querySelector('p-button')).not.toBeNull()
    expect(container.querySelectorAll('select')).toHaveLength(0)
  })

  it('WorkspaceStatus module copy does not regress to raw <p> elements', () => {
    const { container } = render(
      <PorscheDesignSystemProvider>
        <WorkspaceStatus
          health={{
            status: 'healthy',
            modules: {
              tasks: { status: 'healthy', findings: [], repairable_count: 0 },
              requests: { status: 'healthy', findings: [] },
              memory: { status: 'healthy', findings: [] },
              ideas: { status: 'healthy', findings: [] },
            },
          }}
        />
      </PorscheDesignSystemProvider>,
    )
    const badge = container.querySelector('[data-testid="workspace-status"]') as HTMLElement
    if (badge) fireEvent.click(badge)
    expect(container.querySelector('[data-testid="workspace-status-popover"]')).not.toBeNull()
    expect(container.querySelectorAll('p')).toHaveLength(0)
  })
})

// ─── AC4: form controls use PDS equivalents ───────────────────────────────────

describe('PdsMigration_FormControls', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  it('DetailTab uses PInputText for title, PSelect for priority', () => {
    const { container } = renderDetailTab()
    openDetailEditor(container)
    expect(container.querySelector('p-input-text[data-field="title"]')).not.toBeNull()
    expect(container.querySelector('p-select[data-field="priority"]')).not.toBeNull()
    expect(container.querySelector('input[data-field="title"]')).toBeNull()
    expect(container.querySelector('select[data-field="priority"]')).toBeNull()
  })

  it('PDS event propagation: changed title appears in save POST body', async () => {
    const mockFetch = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) }),
    )
    const { container } = renderDetailTab()
    vi.stubGlobal('fetch', mockFetch)
    openDetailEditor(container)

    const titleInput = container.querySelector('p-input-text[data-field="title"]')!
    fireEvent(titleInput, new CustomEvent('change', { detail: { value: 'Updated title' }, bubbles: true }))

    const saveBtn = container.querySelector('p-button[data-testid="save-button"]')!
    fireEvent.click(saveBtn)
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledOnce())

    const callArgs = mockFetch.mock.calls[0] as unknown as [string, RequestInit]
    const payload = JSON.parse(callArgs[1].body as string) as Record<string, unknown>
    expect(payload.title).toBe('Updated title')
  })
})
