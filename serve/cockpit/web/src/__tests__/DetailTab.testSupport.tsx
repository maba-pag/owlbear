import { beforeAll, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type DetailTabProps, type TaskDetail } from '../components/DetailTab'
import type { Board } from '../hooks/useBoard'

// Newer jsdom versions expose a partial attachInternals that lacks setFormValue,
// causing PDS Stencil form components to throw on mount. Override for stable tests.
beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

export const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-04-18T10:00:00+00:00',
  created: '2026-04-17T09:00:00+00:00',
  tags: ['bug', 'frontend'],
  blocked: false,
  block_reason: null,
  claimed: true,
  claimed_at: '2026-04-18T09:30:00+00:00',
  dep_status: null,
  parent: null,
  depends_on: [],
  proof_bundle: null,
}

export const TASK_WITH_DEPS: TaskDetail = {
  ...TASK,
  depends_on: [10, 20],
  parent: 5,
}

export const TASK_WITH_MISSING_REF: TaskDetail = {
  ...TASK,
  depends_on: [10, 404],
  parent: 999,
}

export const TASK_REFERENCES = [
  { id: 5, title: 'Parent rollout', status: 'backlog' },
  { id: 10, title: 'API contract', status: 'todo' },
  { id: 20, title: 'UX proof', status: 'in-progress' },
]

export const TASK_WITH_AC: TaskDetail = {
  ...TASK,
  ac: [
    'User can see the acceptance criteria in task detail.',
    'Missing acceptance criteria has an explicit empty state.',
  ],
}

export const TASK_WITHOUT_AC: TaskDetail = {
  ...TASK,
  ac: [],
}

export const BOARD: Board = {
  statuses: [
    { name: 'research' },
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'review' },
    { name: 'docs' },
    { name: 'done' },
  ],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'review'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  },
}

export function renderDetail(task: TaskDetail = TASK) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
    </PorscheDesignSystemProvider>,
  )
}

export function renderDetailTab(overrides: Partial<DetailTabProps>) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={TASK} {...overrides} />
    </PorscheDesignSystemProvider>,
  )
}

export function openEditor(container: HTMLElement): void {
  const editButton = container.querySelector('[data-testid="edit-details-button"]') as HTMLElement | null
  expect(editButton).not.toBeNull()
  fireEvent.click(editButton!)
}

export function typeIntoPdsField(container: HTMLElement, selector: string, value: string): void {
  const field = container.querySelector(selector) as HTMLElement | null
  expect(field).not.toBeNull()
  fireEvent(field!, new CustomEvent('input', { detail: { value }, bubbles: true }))
}

export function getFetchBody(
  fetchMock: { mock: { calls: unknown[][] } },
  callIndex = 0,
): Record<string, unknown> {
  expect(fetchMock.mock.calls.length).toBeGreaterThan(callIndex)
  const [, options] = fetchMock.mock.calls[callIndex] as unknown as [string, RequestInit]
  return JSON.parse(options.body as string) as Record<string, unknown>
}

export async function flushAsyncSave(): Promise<void> {
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
}
