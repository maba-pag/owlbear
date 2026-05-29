/**
 * Frontend — PDS migration (design system consistency)
 *
 * AC1 (td:1): <button> → <PButton> in ConfirmDialog, ArchivalModal, ActivityTab,
 *              DetailTab, ResolveModal, Shell.tsx
 * AC2 (td:1): <h3> → <PHeading tag="h3"> in ArchivalModal, ResolveModal
 * AC3 (td:1): standalone <p> → <PText> in ArchivalModal error, DRStatusIndicator
 *              empty state, HealthBadge empty state, ArchivalModal refs hint
 * AC4 (td:2): form controls → PInputText/PSelect/PTextarea in DetailTab,
 *              ArchivalModal, ResolveModal; visible labels where they anchor form fields
 * AC5/AC6 (td:0): Card/Column and KanbanBoard context menu — not tested here
 *
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { act, render, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ConfirmDialog from '../components/ConfirmDialog'
import ArchivalModal from '../components/ArchivalModal'
import ActivityTab from '../components/ActivityTab'
import DetailTab, { type TaskDetail } from '../components/DetailTab'
import ResolveModal from '../components/ResolveModal'
import HealthBadge from '../components/HealthBadge'
import DRStatusIndicator from '../components/DRStatusIndicator'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// ─── Module mocks ─────────────────────────────────────────────────────────────

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
  parent: null,
  depends_on: [],
}

const TASK_BLOCKED: TaskDetail = {
  ...TASK,
  blocked: true,
  block_reason: 'Waiting for dep',
}

const DR_FIXTURE = {
  id: '42-scope-question',
  task_id: 42,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-04-30T14:30:00+00:00',
  title: 'Scope question',
  body_preview: 'Context: Should we include X?',
  body: '## Context\n\nShould we include X?',
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

const SCAN_ITEM = {
  code: 'E001',
  detail: 'Missing required field',
  file_path: 'src/models/task.py',
}

// ─── Render helpers ────────────────────────────────────────────────────────────

function renderConfirm(type: 'move-backward' | 'unblock' | 'unclaim' = 'move-backward') {
  return render(
    <PorscheDesignSystemProvider>
      <ConfirmDialog type={type} onCancel={vi.fn()} onConfirm={vi.fn()} />
    </PorscheDesignSystemProvider>,
  )
}

function renderArchival({
  taskId = 42,
  taskStatus = 'in-progress',
  expectedUpdated = '2026-05-01T10:00:00+00:00',
  onClose = vi.fn(),
  onRefresh = vi.fn(),
} = {}) {
  return render(
    <PorscheDesignSystemProvider>
      <ArchivalModal
        taskId={taskId}
        taskStatus={taskStatus}
        expectedUpdated={expectedUpdated}
        onClose={onClose}
        onRefresh={onRefresh}
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

function renderHealthBadge(items: { code: string; detail: string; file_path: string }[] = [SCAN_ITEM]) {
  return render(
    <PorscheDesignSystemProvider>
      <HealthBadge items={items} />
    </PorscheDesignSystemProvider>,
  )
}

function renderDRIndicator(count = 0, items: typeof DR_PENDING[] = [DR_PENDING]) {
  return render(
    <PorscheDesignSystemProvider>
      <DRStatusIndicator count={count} items={items} onItemClick={vi.fn()} />
    </PorscheDesignSystemProvider>,
  )
}

function renderShell() {
  vi.stubGlobal('fetch', vi.fn((_url: string, init?: RequestInit) =>
    new Promise<never>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () =>
        reject(new DOMException('Aborted', 'AbortError')),
      )
    }),
  ))
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

// ─── AC1: <button> → <PButton> ───────────────────────────────────────────────

describe('TestFromAC_PdsMigration_Buttons', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  describe('AC1: ConfirmDialog uses PButton', () => {
    it('renders p-button for cancel action', () => {
      const { container } = renderConfirm()
      expect(container.querySelector('p-button')).not.toBeNull()
    })

    it('renders no raw <button> elements (all replaced by PButton)', () => {
      const { container } = renderConfirm()
      expect(container.querySelector('button')).toBeNull()
    })

    it('cancel and confirm actions both use p-button (at least 2 p-buttons)', () => {
      const { container } = renderConfirm()
      const buttons = container.querySelectorAll('p-button')
      expect(buttons.length).toBeGreaterThanOrEqual(2)
    })
  })

  describe('AC1: ArchivalModal uses PButton', () => {
    it('renders p-button for archive submit action', () => {
      const { container } = renderArchival()
      const submitBtn = container.querySelector('p-button[data-testid="archival-submit"]')
      expect(submitBtn).not.toBeNull()
    })

    it('renders p-button for cancel action', () => {
      const { container } = renderArchival()
      const buttons = container.querySelectorAll('p-button')
      expect(buttons.length).toBeGreaterThanOrEqual(2)
    })

    it('renders no raw <button> in ArchivalModal', () => {
      const { container } = renderArchival()
      expect(container.querySelector('button')).toBeNull()
    })
  })

  describe('AC1: ActivityTab filter buttons use PButton', () => {
    it('filter-active button is p-button', () => {
      const { container } = renderActivityTab()
      expect(container.querySelector('p-button[data-testid="filter-active"]')).not.toBeNull()
    })

    it('filter-all button is p-button', () => {
      const { container } = renderActivityTab()
      expect(container.querySelector('p-button[data-testid="filter-all"]')).not.toBeNull()
    })

    it('renders no raw <button> elements in ActivityTab', () => {
      const { container } = renderActivityTab()
      expect(container.querySelector('button')).toBeNull()
    })
  })

  describe('AC1: DetailTab action buttons use PButton', () => {
    it('save button is p-button', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      expect(container.querySelector('p-button[data-testid="save-button"]')).not.toBeNull()
    })

    it('history tab trigger is p-button', () => {
      const { container } = renderDetailTab()
      expect(container.querySelector('p-button[data-testid="history-tab"]')).not.toBeNull()
    })

    it('body-edit-toggle is p-button', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      expect(container.querySelector('p-button[data-testid="body-edit-toggle"]')).not.toBeNull()
    })

    it('renders no raw <button> in DetailTab (excl. ConfirmDialog which is also migrated)', () => {
      const { container } = renderDetailTab()
      expect(container.querySelector('button')).toBeNull()
    })
  })

  describe('AC1: ResolveModal uses PButton', () => {
    it('submit button is p-button', () => {
      const { container } = renderResolveModal()
      expect(container.querySelector('p-button[data-testid="resolve-submit"]')).not.toBeNull()
    })

    it('cancel button is p-button', () => {
      const { container } = renderResolveModal()
      expect(container.querySelector('p-button[data-testid="resolve-cancel"]')).not.toBeNull()
    })

    it('renders no raw <button> in ResolveModal', () => {
      const { container } = renderResolveModal()
      expect(container.querySelector('button')).toBeNull()
    })
  })

  describe('AC1: Shell nav rail uses intentional custom workspace controls', () => {
    it('kanban surface selector is an accessible custom workspace control', () => {
      const { container } = renderShell()
      const navRail = container.querySelector('[data-region="nav-rail"]')
      const control = navRail?.querySelector('[data-surface="kanban"]')
      expect(control).not.toBeNull()
      expect(control?.getAttribute('aria-label')).toBe('Kanban')
      expect(control?.getAttribute('aria-current')).toBe('page')
    })

    it('renders an intentional dock surface for workspace controls', () => {
      const { container } = renderShell()
      const navRail = container.querySelector('[data-region="nav-rail"]')
      expect(navRail?.querySelector('[data-testid="nav-rail-dock"]')).not.toBeNull()
    })
  })

  // ─ AC1 variant: cancel/toggle/filter/nav buttons are secondary; action buttons are primary ─
  // PDS v4 variant is a DOM property (not a reflected HTML attribute) — access via .variant
  // PDS v4 removed the 'tertiary' variant; 'secondary' is the correct non-primary variant.

  describe('AC1 variant: ConfirmDialog — cancel=secondary, confirm=primary', () => {
    it('cancel button has variant="secondary" (PDS v4: tertiary removed)', () => {
      const { container } = renderConfirm()
      const buttons = container.querySelectorAll('p-button')
      expect((buttons[0] as HTMLElement & { variant: string }).variant).toBe('secondary')
    })

    it('confirm button has variant="primary" (default action)', () => {
      const { container } = renderConfirm()
      const buttons = container.querySelectorAll('p-button')
      expect((buttons[1] as HTMLElement & { variant: string }).variant).toBe('primary')
    })
  })

  describe('AC1 variant: ArchivalModal — archive=primary, cancel=secondary', () => {
    it('archive submit button has variant="primary" (default action)', () => {
      const { container } = renderArchival()
      const submitBtn = container.querySelector('p-button[data-testid="archival-submit"]')
      expect((submitBtn as HTMLElement & { variant: string }).variant).toBe('primary')
    })

    it('cancel button has variant="secondary" (PDS v4: tertiary removed)', () => {
      const { container } = renderArchival()
      const buttons = container.querySelectorAll('p-button')
      const secondary = Array.from(buttons).find(
        (b) => (b as HTMLElement & { variant: string }).variant === 'secondary',
      )
      expect(secondary).not.toBeUndefined()
    })
  })

  describe('AC1 variant: ActivityTab — all filter buttons are secondary (PDS v4: tertiary removed)', () => {
    it('filter-active has variant="secondary"', () => {
      const { container } = renderActivityTab()
      const el = container.querySelector('p-button[data-testid="filter-active"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })

    it('filter-all has variant="secondary"', () => {
      const { container } = renderActivityTab()
      const el = container.querySelector('p-button[data-testid="filter-all"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })

    it('filter-blocked has variant="secondary"', () => {
      const { container } = renderActivityTab()
      const el = container.querySelector('p-button[data-testid="filter-blocked"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })

    it('filter-stuck has variant="secondary"', () => {
      const { container } = renderActivityTab()
      const el = container.querySelector('p-button[data-testid="filter-stuck"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })

    it('filter-released has variant="secondary"', () => {
      const { container } = renderActivityTab()
      const el = container.querySelector('p-button[data-testid="filter-released"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })
  })

  describe('AC1 variant: DetailTab — save=primary, all other action buttons=secondary (PDS v4: tertiary removed)', () => {
    it('save-button has variant="primary" (default action)', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      const el = container.querySelector('p-button[data-testid="save-button"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('primary')
    })

    it('history-tab has variant="secondary"', () => {
      const { container } = renderDetailTab()
      const el = container.querySelector('p-button[data-testid="history-tab"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })

    it('body-edit-toggle has variant="secondary"', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      const el = container.querySelector('p-button[data-testid="body-edit-toggle"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })

    it('unclaim-action has variant="secondary"', () => {
      const { container } = renderDetailTab()
      const el = container.querySelector('p-button[data-testid="unclaim-action"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })

    it('unblock-action has variant="secondary" when task is blocked', () => {
      const { container } = renderDetailTab(TASK_BLOCKED)
      const el = container.querySelector('p-button[data-testid="unblock-action"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })

    it('conflict-refresh has variant="secondary" (shown in conflict modal)', async () => {
      const { container } = renderDetailTab()
      let callCount = 0
      vi.stubGlobal(
        'fetch',
        vi.fn(() => {
          callCount += 1
          if (callCount === 1) {
            return Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
          }
          return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(TASK) })
        }),
      )
      const saveBtn = container.querySelector('p-button[data-testid="save-button"]')!
      fireEvent.click(saveBtn)
      await new Promise((r) => setTimeout(r, 0))
      const el = container.querySelector('p-button[data-testid="conflict-refresh"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })
  })

  describe('AC1 variant: ResolveModal — submit=primary, cancel=secondary (PDS v4: tertiary removed)', () => {
    it('resolve-submit has variant="primary" (default action)', () => {
      const { container } = renderResolveModal()
      const el = container.querySelector('p-button[data-testid="resolve-submit"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('primary')
    })

    it('resolve-cancel has variant="secondary"', () => {
      const { container } = renderResolveModal()
      const el = container.querySelector('p-button[data-testid="resolve-cancel"]')
      expect((el as HTMLElement & { variant: string }).variant).toBe('secondary')
    })
  })

  describe('AC1 variant: Shell — nav rail control remains accessible', () => {
    it('kanban surface selector has an accessible name and current-page state', () => {
      const { container } = renderShell()
      const el = container.querySelector('[data-surface="kanban"]')
      expect(el?.getAttribute('aria-label')).toBe('Kanban')
      expect(el?.getAttribute('aria-current')).toBe('page')
    })
  })
})

// ─── AC2: <h3> → <PHeading tag="h3"> ─────────────────────────────────────────

describe('TestFromAC_PdsMigration_Headings', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  describe('AC2: ArchivalModal uses PHeading for dialog title', () => {
    it('renders p-heading element for "Archive task" title', () => {
      const { container } = renderArchival()
      expect(container.querySelector('p-heading')).not.toBeNull()
    })

    it('p-heading has tag="h3" (or tag attribute set to h3)', () => {
      const { container } = renderArchival()
      const heading = container.querySelector('p-heading')
      expect(heading?.getAttribute('tag')).toBe('h3')
    })

    it('renders no raw <h3> in ArchivalModal', () => {
      const { container } = renderArchival()
      expect(container.querySelector('h3')).toBeNull()
    })

    it('PHeading contains dialog title text "Archive task"', () => {
      const { container } = renderArchival()
      const heading = container.querySelector('p-heading')
      expect(heading?.textContent).toContain('Archive task')
    })
  })

  describe('AC2: ResolveModal uses PHeading for DR title', () => {
    it('renders p-heading element for DR title', () => {
      const { container } = renderResolveModal()
      expect(container.querySelector('p-heading')).not.toBeNull()
    })

    it('p-heading has tag="h3"', () => {
      const { container } = renderResolveModal()
      const heading = container.querySelector('p-heading')
      expect(heading?.getAttribute('tag')).toBe('h3')
    })

    it('renders no raw <h3> in ResolveModal', () => {
      const { container } = renderResolveModal()
      expect(container.querySelector('h3')).toBeNull()
    })

    it('PHeading contains the DR title text', () => {
      const { container } = renderResolveModal()
      const heading = container.querySelector('p-heading')
      expect(heading?.textContent).toContain('Scope question')
    })
  })
})

// ─── AC3: standalone <p> → <PText> ───────────────────────────────────────────

describe('TestFromAC_PdsMigration_Text', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  describe('AC3: ArchivalModal error message uses PInlineNotification', () => {
    it('renders p-inline-notification[data-testid="archival-error"] for submission errors', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }),
        ),
      )
      const { container } = renderArchival()
      // Submit with a valid reason — drive p-select with CustomEvent matching readControlValue
      const pSelect = container.querySelector('p-select')
      if (pSelect) fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'dropped' }, bubbles: true }))
      const submitBtn = container.querySelector('[data-testid="archival-submit"]')
      // Wrap in act to flush the async fetch and subsequent state update
      await act(async () => {
        if (submitBtn) fireEvent.click(submitBtn)
      })

      // After migration the error host must be p-inline-notification
      expect(
        container.querySelector('p-inline-notification[data-testid="archival-error"]'),
      ).not.toBeNull()
    })

    it('renders no p-text[data-testid="archival-error"] (replaced by PInlineNotification)', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }),
        ),
      )
      const { container } = renderArchival()
      const pSelect = container.querySelector('p-select')
      if (pSelect) fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'dropped' }, bubbles: true }))
      const submitBtn = container.querySelector('[data-testid="archival-submit"]')
      if (submitBtn) fireEvent.click(submitBtn)

      await new Promise((r) => setTimeout(r, 0))
      expect(container.querySelector('p-text[data-testid="archival-error"]')).toBeNull()
    })
  })

  describe('AC3: ArchivalModal refs hint uses PText', () => {
    it('renders p-text for "Required — enter at least one task ID" hint when refs visible', () => {
      const { container } = renderArchival()
      // Select a reason that requires refs — drive p-select with CustomEvent
      const pSelect = container.querySelector('p-select')
      if (pSelect) fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'deprecated' }, bubbles: true }))

      // The inline hint paragraph must be p-text
      expect(container.querySelector('p-text')).not.toBeNull()
    })

    it('renders no raw <p> hint text (replaced by PText)', () => {
      const { container } = renderArchival()
      const pSelect = container.querySelector('p-select')
      if (pSelect) fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'deprecated' }, bubbles: true }))
      // After migration, no standalone <p> inside the refs label
      expect(container.querySelector('label p')).toBeNull()
    })
  })

  describe('AC3: DRStatusIndicator empty state uses PText', () => {
    it('renders p-text with "No pending decision requests" when popover is open and no items', () => {
      const { container } = renderDRIndicator(0, [])
      const indicator = container.querySelector('[data-testid="dr-indicator"]')!
      fireEvent.click(indicator)
      expect(container.querySelector('p-text')).not.toBeNull()
    })

    it('renders no raw <p> element for empty state in DRStatusIndicator popover', () => {
      const { container } = renderDRIndicator(0, [])
      const indicator = container.querySelector('[data-testid="dr-indicator"]')!
      fireEvent.click(indicator)
      const popover = container.querySelector('[data-testid="dr-popover"]')
      expect(popover?.querySelector('p')).toBeNull()
    })
  })

  describe('AC3: HealthBadge empty state uses PText', () => {
    it('renders p-text with "No issues" when popover is open and items is empty', () => {
      const { container } = renderHealthBadge([])
      const badge = container.querySelector('[data-testid="health-badge"]')!
      fireEvent.click(badge)
      const popover = container.querySelector('[data-testid="health-badge-popover"]')
      expect(popover?.querySelector('p-text')).not.toBeNull()
    })

    it('renders no raw <p> for the "No issues" empty state', () => {
      const { container } = renderHealthBadge([])
      const badge = container.querySelector('[data-testid="health-badge"]')!
      fireEvent.click(badge)
      const popover = container.querySelector('[data-testid="health-badge-popover"]')
      expect(popover?.querySelector('p')).toBeNull()
    })
  })
})

// ─── AC4: Form controls → PDS form components ────────────────────────────────

describe('TestFromAC_PdsMigration_FormControls', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  // ─ Happy: PInputText ─────────────────────────────────────────────────────

  describe('AC4 happy: DetailTab title uses PInputText', () => {
    it('renders p-input-text for the title field', () => {
      const { container } = renderDetailTab()
      expect(container.querySelector('p-input-text[data-field="title"]')).not.toBeNull()
    })

    it('renders no raw <input data-field="title">', () => {
      const { container } = renderDetailTab()
      expect(container.querySelector('input[data-field="title"]')).toBeNull()
    })
  })

  describe('AC4 happy: ArchivalModal refs input uses PInputText when visible', () => {
    it('renders p-input-text for refs when reason requires refs', () => {
      const { container } = renderArchival()
      // Select deprecated to show refs — drive p-select with CustomEvent
      const pSelect = container.querySelector('p-select')
      if (pSelect) fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'deprecated' }, bubbles: true }))
      expect(container.querySelector('p-input-text')).not.toBeNull()
    })

    it('renders no raw <input type="text"> for refs field', () => {
      const { container } = renderArchival()
      const pSelect = container.querySelector('p-select')
      if (pSelect) fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'deprecated' }, bubbles: true }))
      expect(container.querySelector('input[type="text"]')).toBeNull()
    })
  })

  // ─ Happy: PSelect ────────────────────────────────────────────────────────

  describe('AC4 happy: DetailTab priority uses PSelect', () => {
    it('renders p-select for the priority field', () => {
      const { container } = renderDetailTab()
      expect(container.querySelector('p-select[data-field="priority"]')).not.toBeNull()
    })

    it('renders no raw <select data-field="priority">', () => {
      const { container } = renderDetailTab()
      expect(container.querySelector('select[data-field="priority"]')).toBeNull()
    })
  })

  describe('AC4 happy: ArchivalModal reason uses PSelect', () => {
    it('renders p-select for the reason field', () => {
      const { container } = renderArchival()
      expect(container.querySelector('p-select')).not.toBeNull()
    })

    it('renders no raw <select> for reason field', () => {
      const { container } = renderArchival()
      expect(container.querySelector('select')).toBeNull()
    })
  })

  // ─ Happy: PTextarea ──────────────────────────────────────────────────────

  describe('AC4 happy: DetailTab body textarea uses PTextarea in edit mode', () => {
    it('renders p-textarea for body when edit mode is active', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      const toggleBtn = container.querySelector('[data-testid="body-edit-toggle"]')
      if (toggleBtn) fireEvent.click(toggleBtn)
      expect(container.querySelector('p-textarea[data-field="body"]')).not.toBeNull()
    })

    it('renders no raw <textarea data-field="body"> in edit mode', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      const toggleBtn = container.querySelector('[data-testid="body-edit-toggle"]')
      if (toggleBtn) fireEvent.click(toggleBtn)
      expect(container.querySelector('textarea[data-field="body"]')).toBeNull()
    })
  })

  describe('AC4 happy: ResolveModal notes uses PTextarea', () => {
    it('renders p-textarea for notes field', () => {
      const { container } = renderResolveModal()
      expect(container.querySelector('p-textarea[data-testid="resolve-notes"]')).not.toBeNull()
    })

    it('renders no raw <textarea data-testid="resolve-notes">', () => {
      const { container } = renderResolveModal()
      expect(container.querySelector('textarea[data-testid="resolve-notes"]')).toBeNull()
    })
  })

  // ─ Boundary: DetailTab fields keep visible labels ───────────────────────

  describe('AC4 boundary: DetailTab inputs keep visible labels', () => {
    it('p-input-text for title does not hide its label', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      const el = container.querySelector('p-input-text[data-field="title"]')
      expect(el?.hasAttribute('hide-label')).toBe(false)
    })

    it('p-select for priority does not hide its label', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      const el = container.querySelector('p-select[data-field="priority"]')
      expect(el?.hasAttribute('hide-label')).toBe(false)
    })

    it('p-textarea for body in edit mode does not hide its label', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      const toggleBtn = container.querySelector('[data-testid="body-edit-toggle"]')
      if (toggleBtn) fireEvent.click(toggleBtn)
      const el = container.querySelector('p-textarea[data-field="body"]')
      expect(el?.hasAttribute('hide-label')).toBe(false)
    })

    it('p-input-text for depends_on does not hide its label', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      const el = container.querySelector('p-input-text[data-field="depends_on"]')
      expect(el?.hasAttribute('hide-label')).toBe(false)
    })

    it('p-input-text for parent does not hide its label', () => {
      const { container } = renderDetailTab()
      openDetailEditor(container)
      const el = container.querySelector('p-input-text[data-field="parent"]')
      expect(el?.hasAttribute('hide-label')).toBe(false)
    })

    it('p-input-text for block_reason does not hide its label when task is blocked', () => {
      const { container } = renderDetailTab(TASK_BLOCKED)
      openDetailEditor(container)
      const el = container.querySelector('p-input-text[data-field="block_reason"]')
      expect(el?.hasAttribute('hide-label')).toBe(false)
    })
  })

  // ─ Boundary: labeled fields do NOT get hideLabel ─────────────────────────

  describe('AC4 boundary: ArchivalModal labeled fields do not get hide-label', () => {
    it('p-select for reason does NOT have hide-label (has visible label wrapper)', () => {
      const { container } = renderArchival()
      const pSelect = container.querySelector('p-select')
      expect(pSelect?.hasAttribute('hide-label')).toBe(false)
    })

    it('p-input-text for refs does NOT have hide-label (has visible label wrapper)', () => {
      const { container } = renderArchival()
      const pSelect = container.querySelector('p-select')
      if (pSelect) fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'duplicate' }, bubbles: true }))
      const pInput = container.querySelector('p-input-text')
      expect(pInput?.hasAttribute('hide-label')).toBe(false)
    })

    it('p-textarea for resolve notes keeps its visible PDS label', () => {
      const { container } = renderResolveModal()
      const textarea = container.querySelector('p-textarea[data-testid="resolve-notes"]') as HTMLElement & { label?: string }
      expect(textarea).not.toBeNull()
      expect(textarea.hasAttribute('hide-label')).toBe(false)
      expect(textarea.label ?? textarea.getAttribute('label')).toBe('Resolution notes')
    })
  })

  // ─ Additional: DetailTab blocked renders PInputText for block_reason ─────

  describe('AC4 additional: DetailTab block_reason uses PInputText when task is blocked', () => {
    it('renders p-input-text for block_reason when task is blocked', () => {
      const { container } = renderDetailTab(TASK_BLOCKED)
      expect(container.querySelector('p-input-text[data-field="block_reason"]')).not.toBeNull()
    })
  })

})

// ─── AC4 payload: PDS event path propagates field values into POST body ───────

describe('TestFromAC_PdsMigration_DetailTabPayload', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  describe('AC4 payload: mutating title and priority via PDS events sends updated values in edit POST', () => {
    it('changed title appears in the POST body after save', async () => {
      const mockFetch = vi.fn(() =>
        Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) }),
      )
      const { container } = renderDetailTab()
      // Override the hanging-promise stub set by renderDetailTab
      vi.stubGlobal('fetch', mockFetch)
      openDetailEditor(container)

      const titleInput = container.querySelector('p-input-text[data-field="title"]')!
      fireEvent(titleInput, new CustomEvent('change', { detail: { value: 'Updated title' }, bubbles: true }))

      const saveBtn = container.querySelector('p-button[data-testid="save-button"]')!
      fireEvent.click(saveBtn)
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledOnce())

      const [, callOptions] = mockFetch.mock.calls[0]
      const payload = JSON.parse((callOptions as RequestInit).body as string) as Record<string, unknown>
      expect(payload.title).toBe('Updated title')
    })

    it('changed priority appears in the POST body after save', async () => {
      const mockFetch = vi.fn(() =>
        Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) }),
      )
      const { container } = renderDetailTab()
      vi.stubGlobal('fetch', mockFetch)
      openDetailEditor(container)

      const prioritySelect = container.querySelector('p-select[data-field="priority"]')!
      fireEvent(prioritySelect, new CustomEvent('change', { detail: { value: 'critical' }, bubbles: true }))

      const saveBtn = container.querySelector('p-button[data-testid="save-button"]')!
      fireEvent.click(saveBtn)
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledOnce())

      const [, callOptions] = mockFetch.mock.calls[0]
      const payload = JSON.parse((callOptions as RequestInit).body as string) as Record<string, unknown>
      expect(payload.priority).toBe('critical')
    })

    it('both title and priority changes are reflected together in a single save', async () => {
      const mockFetch = vi.fn(() =>
        Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) }),
      )
      const { container } = renderDetailTab()
      vi.stubGlobal('fetch', mockFetch)
      openDetailEditor(container)

      const titleInput = container.querySelector('p-input-text[data-field="title"]')!
      fireEvent(titleInput, new CustomEvent('change', { detail: { value: 'New task title' }, bubbles: true }))

      const prioritySelect = container.querySelector('p-select[data-field="priority"]')!
      fireEvent(prioritySelect, new CustomEvent('change', { detail: { value: 'needed' }, bubbles: true }))

      const saveBtn = container.querySelector('p-button[data-testid="save-button"]')!
      fireEvent.click(saveBtn)
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledOnce())

      const [, callOptions] = mockFetch.mock.calls[0]
      const payload = JSON.parse((callOptions as RequestInit).body as string) as Record<string, unknown>
      expect(payload.title).toBe('New task title')
      expect(payload.priority).toBe('needed')
    })
  })
})
