/**
 * Consolidation test: board visual design integration (#1554)
 *
 * Durable integration test verifying that all board visual design components
 * integrate coherently. Builder confirms all tests pass; no new source code required.
 *
 * AC-1: Board integration rendering
 *   — full board with tasks in all 4 operational signal states (ready, blocked,
 *     claimed, deps-unmet); column structure (.column class, <header> direct
 *     child, data-testid="column-body" sibling); Card-level dr-pending via
 *     explicit pendingDRIds prop; data-testid="theme-toggle" button present.
 * AC-2: Dark theme token coverage via tokens.css source inspection
 *   — [data-theme="dark"] block overrides all :root color token groups
 *     (--pds-primary, --pds-background-*, --pds-contrast-*, --pds-notification-*,
 *      --pds-signal-*, --pds-state-*); non-color tokens absent from dark block;
 *     component CSS files (Card.css, Column.css, KanbanBoard.css) contain no
 *     hardcoded hex / rgb() / hsl() color literals.
 * AC-3: Card signal left-border CSS mapping
 *   — .card base border-left; all four [data-signal] overrides mapped to
 *     correct --pds-* tokens.
 *
 * Dependencies (all archived): #1543 #1544 #1545 #1546 #1547 #1548 #1549 #1550 #1555
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'
import { Card } from '../components/Card'
import ThemeToggle from '../components/ThemeToggle'
import type { Board, Task } from '../hooks/useBoard'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── Hoisted mock stubs for Shell-level integration tests ─────────────────────
const mockUseBoardState = vi.hoisted(() => vi.fn())
const mockUseTaskSelection = vi.hoisted(() => vi.fn())
const mockUseDRState = vi.hoisted(() => vi.fn())

vi.mock('../hooks/CockpitProvider', () => ({
  CockpitProvider: ({ children }: { children: unknown }) => children,
  useBoardState: mockUseBoardState,
  useTaskSelection: mockUseTaskSelection,
  useDRState: mockUseDRState,
}))

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

import Shell from '../Shell'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// ─── CSS file paths ────────────────────────────────────────────────────────────

const CARD_CSS_PATH = resolve(__dirname, '..', 'components', 'Card.css')
const COLUMN_CSS_PATH = resolve(__dirname, '..', 'components', 'Column.css')
const KANBAN_CSS_PATH = resolve(__dirname, '..', 'KanbanBoard.css')
const TOKENS_CSS_PATH = resolve(__dirname, '..', 'tokens.css')

// ─── Fixtures ──────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    todo: ['in-progress'],
    'in-progress': ['todo'],
  } as Record<string, string[]>,
}

function makeTask(overrides: Partial<Task> & { id: number; status: string }): Task {
  return {
    title: `Task ${overrides.id}`,
    priority: 'important',
    updated: '2026-05-13T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
    dep_status: null,
    ...overrides,
  }
}

// One task per board-level signal state (dr-pending is Card-only — tested separately).
const TASK_READY = makeTask({ id: 1, status: 'todo', blocked: false, claimed: false, dep_status: null })
const TASK_BLOCKED = makeTask({ id: 2, status: 'todo', blocked: true, block_reason: 'Blocked', claimed: false, dep_status: null })
const TASK_CLAIMED = makeTask({ id: 3, status: 'in-progress', blocked: false, claimed: true, dep_status: null })
const TASK_DEPS_UNMET = makeTask({ id: 4, status: 'todo', blocked: false, claimed: false, dep_status: 'blocked' })

const ALL_SIGNAL_TASKS: Task[] = [TASK_READY, TASK_BLOCKED, TASK_CLAIMED, TASK_DEPS_UNMET]

// ─── Render helpers ────────────────────────────────────────────────────────────

function renderBoard(tasks: Task[] = ALL_SIGNAL_TASKS, opts: { pendingDRIds?: Set<number> } = {}) {
  const { pendingDRIds = new Set<number>() } = opts
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard
          board={BOARD}
          tasks={tasks}
          loading={false}
          error={null}
          refetchTasks={() => {}}
          pendingDRIds={pendingDRIds}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

function renderCard(task: Task, pendingDRIds: Set<number> = new Set()) {
  return render(
    <Card
      task={task}
      pendingDRIds={pendingDRIds}
      onContextMenu={() => {}}
      onDragStart={() => {}}
      onDragEnd={() => {}}
    />,
  )
}

// ─── CSS helpers ───────────────────────────────────────────────────────────────

function getCSSBlock(css: string, selector: string): string | null {
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g, '')
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(`${escaped}\\s*\\{([^}]*)\\}`)
  const match = stripped.match(pattern)
  return match ? match[1] : null
}

// ─── AC-1: Board integration — all 4 board-level signal states ────────────────

describe('BoardSignalIntegration', () => {
  it('card with "ready" signal renders data-signal="ready" through full board render', () => {
    const { container } = renderBoard()
    const card = container.querySelector('[data-testid="task-card"][data-id="1"]')
    expect(card, 'Task 1 (ready) must render a card element').not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('ready')
  })

  it('card with "deps-unmet" signal renders data-signal="deps-unmet" when dep_status is "blocked"', () => {
    const { container } = renderBoard()
    const card = container.querySelector('[data-testid="task-card"][data-id="4"]')
    expect(card, 'Task 4 (deps-unmet) must render a card element').not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('deps-unmet')
  })

  it('card with "blocked" signal renders data-signal="blocked" through full board render', () => {
    const { container } = renderBoard()
    const card = container.querySelector('[data-testid="task-card"][data-id="2"]')
    expect(card, 'Task 2 (blocked) must render a card element').not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('blocked')
  })

  it('card with "claimed" signal renders data-signal="claimed" through full board render', () => {
    const { container } = renderBoard()
    const card = container.querySelector('[data-testid="task-card"][data-id="3"]')
    expect(card, 'Task 3 (claimed) must render a card element').not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('claimed')
  })

  it('all 4 board-level signal states are simultaneously present in one full board render', () => {
    const { container } = renderBoard()
    const expected = ['ready', 'blocked', 'claimed', 'deps-unmet'] as const
    for (const signal of expected) {
      const card = container.querySelector(`[data-testid="task-card"][data-signal="${signal}"]`)
      expect(card, `No card found with data-signal="${signal}" in full board render`).not.toBeNull()
    }
  })

  it('column root element has .column CSS class', () => {
    const { container } = renderBoard()
    const columns = container.querySelectorAll('.column')
    // BOARD has 2 statuses: todo, in-progress
    expect(columns.length).toBe(2)
  })

  it('column root has <header> as a direct child (not nested inside column-body)', () => {
    const { container } = renderBoard()
    const column = container.querySelector('.column')
    expect(column, '.column element must exist').not.toBeNull()
    const header = column!.querySelector(':scope > header')
    expect(
      header,
      '<header> must be a direct child of .column — not nested inside the scrollable body',
    ).not.toBeNull()
  })

  it('column has data-testid="column-body" as a direct child sibling of <header>', () => {
    const { container } = renderBoard()
    const column = container.querySelector('.column')
    expect(column, '.column element must exist').not.toBeNull()
    const body = column!.querySelector(':scope > [data-testid="column-body"]')
    expect(
      body,
      'data-testid="column-body" must be a direct child of .column (not nested inside header)',
    ).not.toBeNull()
  })
})

// ─── AC-1: Card-level dr-pending with explicit pendingDRIds ───────────────────

describe('CardDRPendingDirectRender', () => {
  it('Card renders data-signal="dr-pending" when task.id is in pendingDRIds', () => {
    const task = makeTask({ id: 99, status: 'todo', blocked: false, claimed: false, dep_status: null })
    const { container } = renderCard(task, new Set([99]))
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card, 'Card must render with data-testid="task-card"').not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('dr-pending')
  })

  it('Card renders data-signal="ready" when pendingDRIds is empty (baseline: no DR pending)', () => {
    const task = makeTask({ id: 99, status: 'todo', blocked: false, claimed: false, dep_status: null })
    const { container } = renderCard(task, new Set())
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('ready')
  })

  it('dr-pending takes priority over blocked when task is in pendingDRIds and also blocked', () => {
    const task = makeTask({ id: 99, status: 'todo', blocked: true, block_reason: 'blocked', dep_status: null })
    const { container } = renderCard(task, new Set([99]))
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card!.getAttribute('data-signal')).toBe('dr-pending')
  })

  it('Column propagates pendingDRIds to Cards — card shows dr-pending signal when task ID is in the set', () => {
    // When pendingDRIds is passed through KanbanBoard → Column → Card,
    // a task whose ID is in the set must render with data-signal="dr-pending".
    const pendingDRIds = new Set([77])
    const { container } = renderBoard(
      [makeTask({ id: 77, status: 'todo', blocked: false, claimed: false, dep_status: null })],
      { pendingDRIds },
    )
    const card = container.querySelector('[data-testid="task-card"][data-id="77"]')
    expect(card, 'Board must render task 77').not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('dr-pending')
  })
})

// ─── AC-1: ThemeToggle presence ────────────────────────────────────────────────

describe('ThemeTogglePresence', () => {
  it('ThemeToggle renders a <button> element with data-testid="theme-toggle"', () => {
    const { container } = render(<ThemeToggle />)
    const button = container.querySelector('[data-testid="theme-toggle"]')
    expect(button, 'ThemeToggle must render an element with data-testid="theme-toggle"').not.toBeNull()
    expect(button!.tagName.toLowerCase()).toBe('button')
  })
})

// ─── AC-2: Dark theme token coverage ──────────────────────────────────────────

const ALL_COLOR_TOKENS = [
  '--pds-primary',
  '--pds-background-base',
  '--pds-background-surface',
  '--pds-background-shading',
  '--pds-contrast-low',
  '--pds-contrast-medium',
  '--pds-contrast-high',
  '--pds-notification-success',
  '--pds-notification-success-soft',
  '--pds-notification-warning',
  '--pds-notification-warning-soft',
  '--pds-notification-error',
  '--pds-notification-error-soft',
  '--pds-notification-info',
  '--pds-notification-info-soft',
  '--pds-signal-claimed',
  '--pds-state-hover',
  '--pds-state-active',
  '--pds-state-focus',
  '--pds-state-disabled',
] as const

describe('DarkThemeTokenCoverage', () => {
  function extractDarkBlock(css: string): string {
    const block = getCSSBlock(css, '[data-theme="dark"]')
    expect(block, 'tokens.css must have a [data-theme="dark"] block').not.toBeNull()
    return block!
  }

  it('[data-theme="dark"] block in tokens.css overrides all 20 :root color tokens', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const block = extractDarkBlock(css)
    for (const token of ALL_COLOR_TOKENS) {
      expect(
        block,
        `[data-theme="dark"] must override ${token}`,
      ).toMatch(new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*:'))
    }
  })

  it('[data-theme="dark"] block does not override non-color tokens (shadow/radius/spacing)', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const block = extractDarkBlock(css)
    const nonColorPrefixes = ['--pds-shadow-', '--pds-radius-', '--pds-spacing-']
    for (const prefix of nonColorPrefixes) {
      expect(
        block,
        `[data-theme="dark"] must not include ${prefix}* tokens — these are theme-independent`,
      ).not.toMatch(new RegExp(prefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))
    }
  })
})

// ─── AC-2: Component CSS files use only var(--pds-*) for color values ─────────

describe('ComponentCSSTokensOnly', () => {
  // Match hardcoded hex codes and color functions. Does NOT flag `transparent` or
  // `currentColor` which are CSS semantic keywords, not design-token violations.
  const HARDCODED_COLOR_RE = /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/i

  it('Card.css contains no hardcoded hex or rgb()/hsl() color literals', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, '')
    expect(
      HARDCODED_COLOR_RE.test(withoutComments),
      'Card.css must use only var(--pds-*) for color values — found hardcoded hex/rgb/hsl literal',
    ).toBe(false)
  })

  it('Column.css contains no hardcoded hex or rgb()/hsl() color literals', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, '')
    expect(
      HARDCODED_COLOR_RE.test(withoutComments),
      'Column.css must use only var(--pds-*) for color values — found hardcoded hex/rgb/hsl literal',
    ).toBe(false)
  })

  it('KanbanBoard.css contains no hardcoded hex or rgb()/hsl() color literals', () => {
    const css = readFileSync(KANBAN_CSS_PATH, 'utf-8')
    const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, '')
    expect(
      HARDCODED_COLOR_RE.test(withoutComments),
      'KanbanBoard.css must use only var(--pds-*) for color values — found hardcoded hex/rgb/hsl literal',
    ).toBe(false)
  })
})

// ─── AC-3: Card signal left-border CSS mapping (base rule + all 4 overrides) ──

describe('CardSignalBorderMapping', () => {
  it('.card base rule declares border-left: 4px solid var(--pds-contrast-medium)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.card')
    expect(block, '.card rule must exist in Card.css').not.toBeNull()
    expect(block).toMatch(/border-left\s*:\s*4px\s+solid\s+var\(--pds-contrast-medium\)/)
  })

  it('[data-signal="dr-pending"] → border-left-color: var(--pds-notification-warning) (orange)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-signal="dr-pending"]')
    expect(block, '[data-signal="dr-pending"] block must exist').not.toBeNull()
    expect(block).toMatch(/border-left-color\s*:\s*var\(--pds-notification-warning\)/)
  })

  it('[data-signal="blocked"] → border-left-color: var(--pds-notification-error) (red)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-signal="blocked"]')
    expect(block, '[data-signal="blocked"] block must exist').not.toBeNull()
    expect(block).toMatch(/border-left-color\s*:\s*var\(--pds-notification-error\)/)
  })

  it('[data-signal="claimed"] → border-left-color: var(--pds-signal-claimed) (custom purple)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-signal="claimed"]')
    expect(block, '[data-signal="claimed"] block must exist').not.toBeNull()
    expect(block).toMatch(/border-left-color\s*:\s*var\(--pds-signal-claimed\)/)
  })

  it('[data-signal="deps-unmet"] → border-left-color: var(--pds-contrast-medium) (grey)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-signal="deps-unmet"]')
    expect(block, '[data-signal="deps-unmet"] block must exist').not.toBeNull()
    expect(block).toMatch(/border-left-color\s*:\s*var\(--pds-contrast-medium\)/)
  })
})

// ─── AC-1(c): Shell-level integration — ThemeToggle and DRStatusIndicator ─────
//
// Reviewer finding: ThemeToggle was tested in isolation (not Shell-level), so Shell
// could drop ThemeToggle while the suite stayed green. DR routing only proved the
// negative path (Column non-propagation); positive Shell→DRStatusIndicator routing
// was never exercised. These tests close both proof gaps.
//
// Strategy: render Shell with CockpitProvider hooks stubbed via vi.mock (hoisted
// above), following the App.wiring.1504.test.tsx pattern. Assert on DOM elements
// present in Shell's status bar header — the region Shell alone controls.

describe('ShellLevelIntegration', () => {
  const STUB_DR_ITEMS: PendingDR[] = [
    {
      id: 'dr-1',
      task_id: 10,
      agent: 'builder',
      request_type: 'decision',
      created: '2026-01-01T00:00:00Z',
      title: 'DR 1',
      body: 'body',
      body_preview: 'preview',
    },
    {
      id: 'dr-2',
      task_id: 11,
      agent: 'reviewer',
      request_type: 'action',
      created: '2026-01-01T00:00:00Z',
      title: 'DR 2',
      body: 'body',
      body_preview: 'preview',
    },
  ]

  function stubDRState(count: number, items: PendingDR[] = []) {
    mockUseDRState.mockReturnValue({
      count,
      items,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      selectedDRId: null,
      setSelectedDRId: vi.fn(),
      selectedDR: null,
    })
  }

  beforeEach(() => {
    mockUseBoardState.mockReturnValue({
      board: null,
      tasks: [],
      loading: false,
      error: null,
      health: 'yellow',
      refetchTasks: vi.fn(),
      items: [],
      isLoading: false,
      scanError: null,
      refetch: vi.fn(),
    })
    mockUseTaskSelection.mockReturnValue({
      selectedTaskId: null,
      selectedTask: null,
      selectedTaskError: null,
      select: vi.fn(),
      clear: vi.fn(),
      update: vi.fn(),
    })
    stubDRState(0)
    vi.stubGlobal('fetch', vi.fn(() => new Promise<never>(() => {})))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  function renderShell() {
    return render(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <Shell />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )
  }

  it('Shell status bar renders data-testid="theme-toggle" button (ThemeToggle mounted in Shell, not only in isolation)', () => {
    const { container } = renderShell()
    const toggle = container.querySelector('[data-testid="theme-toggle"]')
    expect(
      toggle,
      'Shell status bar must contain data-testid="theme-toggle" — ThemeToggle must be wired into Shell, not just tested as a standalone component',
    ).not.toBeNull()
    expect(toggle!.tagName.toLowerCase()).toBe('button')
  })

  it('Shell status bar renders data-testid="dr-indicator" with data-status="attention" when useDRState returns count=2 with items (positive DR routing proof)', () => {
    stubDRState(2, STUB_DR_ITEMS)
    const { container } = renderShell()
    const indicator = container.querySelector('[data-testid="dr-indicator"]')
    expect(
      indicator,
      'Shell must render data-testid="dr-indicator" — DRStatusIndicator must be wired into Shell status bar',
    ).not.toBeNull()
    expect(indicator!.getAttribute('data-status')).toBe('attention')
  })

  it('Shell status bar renders data-testid="dr-indicator" with data-status="dormant" when useDRState returns count=0 (baseline)', () => {
    stubDRState(0)
    const { container } = renderShell()
    const indicator = container.querySelector('[data-testid="dr-indicator"]')
    expect(
      indicator,
      'Shell must render data-testid="dr-indicator" even when count=0',
    ).not.toBeNull()
    expect(indicator!.getAttribute('data-status')).toBe('dormant')
  })
})
