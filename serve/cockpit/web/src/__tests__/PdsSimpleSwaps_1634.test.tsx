/**
 * PDS simple swaps — task #1634
 *
 * Covers:
 *   AC1 — TaskFieldsEditor <PSelect> renders PSelectOption children:
 *          p-select-option present, zero native OPTION elements
 *          (FilterPanel falsifiability pattern from #1617).
 *   AC2 — DecisionViewport task-ref renders as <PLinkPure> using host-href:
 *          p-link-pure in DOM, icon="none", data-testid and onClick preserved.
 *   AC3 — Existing DecisionViewport.test.tsx assertions updated for p-link-pure:
 *          task-ref element is p-link-pure, href attribute preserved on host.
 *
 * Proof bundle: smoke — one smoke test per AC line.
 */
import { describe, it, expect, vi, beforeAll, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { TaskDetail } from '../components/DetailTab'
import type { PendingDR } from '../hooks/usePendingDRs'
import type { TaskFieldsEditorProps } from '../components/TaskFieldsEditor'

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))
vi.mock('remark-gfm', () => ({ default: () => {} }))
vi.mock('rehype-sanitize', () => ({ default: () => {} }))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import TaskFieldsEditor from '../components/TaskFieldsEditor'
import DecisionViewport from '../components/DecisionViewport'

// ─── attachInternals polyfill (PDS form controls) ────────────────────────────

beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const PRIORITIES = ['someday', 'needed', 'important', 'critical']

const TASK: TaskDetail = {
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

function renderEditor(overrides: Partial<TaskFieldsEditorProps> = {}) {
  const defaults: TaskFieldsEditorProps = {
    task: TASK,
    priorities: PRIORITIES,
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

function renderViewport({
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

// ─── AC1: TaskFieldsEditor PSelectOption (no native <option>) ─────────────────

describe('TestFromAC_PdsSimpleSwaps_1634_PSelectOption', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('p-select in TaskFieldsEditor renders p-select-option children with no native OPTION elements', () => {
    // AC1: PSelect must use PSelectOption children (renders as p-select-option in jsdom).
    // Current code uses native <option> elements inside PSelect → FAILS.
    const { container } = renderEditor()
    const pSelect = container.querySelector('p-select')
    expect(pSelect, 'p-select must be present in TaskFieldsEditor').not.toBeNull()
    expect(
      pSelect!.querySelector('p-select-option'),
      'p-select must contain at least one p-select-option child',
    ).not.toBeNull()
    const nativeCount = Array.from(pSelect!.children).filter((c) => c.tagName === 'OPTION').length
    expect(nativeCount, 'p-select must have zero native <option> elements').toBe(0)
  })
})

// ─── AC2: DecisionViewport PLinkPure host-href pattern ────────────────────────

describe('TestFromAC_PdsSimpleSwaps_1634_PLinkPure', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('task-ref renders as p-link-pure with host-href, icon="none", data-testid, and onClick fires callback', () => {
    // AC2: task-ref must be PLinkPure using host-href pattern (not native <a>).
    // Current code renders <a href="#task-42"> → tagName is "a", not "p-link-pure" → FAILS.
    const onItemClick = vi.fn()
    const { container } = renderViewport({ items: [DR_A], onItemClick })
    const taskRef = container.querySelector('[data-testid="decision-task-ref-dr-1634-a"]')
    expect(taskRef, 'decision-task-ref element must be present').not.toBeNull()
    expect(
      taskRef!.tagName.toLowerCase(),
      'task-ref must be p-link-pure (not native a)',
    ).toBe('p-link-pure')
    expect(
      taskRef!.getAttribute('href'),
      'href must be set on the p-link-pure host element (host-href pattern)',
    ).toMatch(/^#task-\d+$/)
    expect(
      taskRef!.getAttribute('icon'),
      'icon="none" must suppress the default arrow-right',
    ).toBe('none')
    fireEvent.click(taskRef!)
    expect(onItemClick, 'onClick must fire onItemClick callback').toHaveBeenCalledWith('dr-1634-a')
  })
})

// ─── AC3: DecisionViewport existing assertions accept p-link-pure ─────────────

describe('TestFromAC_PdsSimpleSwaps_1634_KeyboardReachability', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('each task-ref element is p-link-pure with href on host (keyboard-reachability: updated from tagName===a)', () => {
    // AC3: the keyboard-reachability assertion (line ~289 in DecisionViewport.test.tsx)
    // currently hardcodes tagName === 'a'. After builder migration it must accept p-link-pure.
    // Current code uses <a> → tagName === 'a' not 'p-link-pure' → FAILS this assertion.
    const { container } = renderViewport({ items: [DR_A, DR_B] })
    const taskRefs = container.querySelectorAll('[data-testid^="decision-task-ref-"]')
    expect(taskRefs.length).toBe(2)
    for (const taskRef of Array.from(taskRefs)) {
      expect(
        taskRef.tagName.toLowerCase(),
        'task-ref must be p-link-pure for keyboard-reachability (host-href pattern)',
      ).toBe('p-link-pure')
      expect(
        taskRef.getAttribute('href'),
        'href must be preserved on the p-link-pure host element',
      ).toMatch(/^#task-\d+$/)
    }
  })
})
