/**
 * Card signal attribute rendering tests — AC-1
 *
 * Tests that Card renders the correct data-signal attribute for each operational
 * state. Card.tsx currently lacks data-signal and pendingDRIds prop — all tests
 * fail RED until builder #1546 wires signal computation into the Card component.
 *
 * Self-contained: expected signal values are defined inline per brief D10/D14.
 * No import of computeSignal — this test verifies the rendered DOM contract,
 * not the computation logic (tested separately in computeSignal.test.ts).
 *
 * Prerequisites (builder must create before tests reach assertion-failure RED):
 *   src/components/Card.tsx — accept pendingDRIds: Set<number>, render data-signal
 *   src/hooks/useBoard.ts — Task type extended with dep_status: string | null (#1544)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { Card } from '../components/Card'
import type { Task } from '../hooks/useBoard'

// ─── Local task shape ────────────────────────────────────────────────────────
// Includes dep_status (added by builder #1544) — defined locally to keep
// tests self-contained and not blocked by the type-extension task.

interface SignalTask {
  id: number
  title: string
  status: string
  priority: string
  updated: string
  tags: string[]
  blocked: boolean
  block_reason: string | null
  claimed: boolean
  dep_status: string | null
}

function makeTask(overrides: Partial<SignalTask> & { id: number }): SignalTask {
  return {
    title: 'Test task',
    status: 'todo',
    priority: 'important',
    updated: '2026-01-01T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
    dep_status: null,
    ...overrides,
  }
}

function renderCard(task: SignalTask, pendingDRIds: Set<number> = new Set()) {
  // pendingDRIds prop will be added by builder #1546; currently unknown to CardProps.
  // Vitest transpiles without type-checking — extra prop causes no runtime error.
  return render(
    <Card
      task={task as unknown as Task}
      // @ts-expect-error prop added by builder #1546
      pendingDRIds={pendingDRIds}
      onContextMenu={() => {}}
    />,
  )
}

// ─── AC-1: Card renders data-signal attribute per operational state ────────────
// Signal precedence (brief D14): dr-pending > blocked > claimed > deps-unmet > ready
// Each test verifies a single isolated state — no coupling to computeSignal.

describe('TestFromAC_CardSignalAttribute', () => {
  it('renders data-signal="dr-pending" when task.id is in pendingDRIds (highest precedence)', () => {
    const task = makeTask({ id: 42 })
    const { container } = renderCard(task, new Set([42]))
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('dr-pending')
  })

  it('renders data-signal="blocked" when task.blocked=true and task not in pendingDRIds', () => {
    const task = makeTask({ id: 1, blocked: true })
    const { container } = renderCard(task, new Set<number>())
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('blocked')
  })

  it('renders data-signal="claimed" when task.claimed=true, not blocked, no pending DR', () => {
    const task = makeTask({ id: 2, claimed: true })
    const { container } = renderCard(task, new Set<number>())
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('claimed')
  })

  it('renders data-signal="deps-unmet" when dep_status="blocked" and no higher-priority signals active', () => {
    const task = makeTask({ id: 3, dep_status: 'blocked' })
    const { container } = renderCard(task, new Set<number>())
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('deps-unmet')
  })

  it('renders data-signal="ready" when no operational conditions are active (default state)', () => {
    const task = makeTask({ id: 4 })
    const { container } = renderCard(task, new Set<number>())
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('ready')
  })
})

// ─── AC-1 (density retry): Card metadata — id, priority, updated ─────────────

describe('TestFromAC_CardDensityElements', () => {
  it('card renders quiet id metadata showing #{task.id}', () => {
    const task = makeTask({ id: 42 })
    const { container } = renderCard(task)
    const idMetadata = container.querySelector('[data-testid="card-id"]')
    expect(idMetadata).not.toBeNull()
    expect(idMetadata!.textContent).toContain('#42')
    expect(idMetadata!.getAttribute('class')).not.toContain('rounded-full')
  })

  it('card keeps priority in data and accessible text without rendering a priority chip', () => {
    const task = makeTask({ id: 1, priority: 'critical' })
    const { container } = renderCard(task)
    const card = container.querySelector('[data-testid="task-card"]')
    expect(container.querySelector('[data-testid="card-priority"]')).toBeNull()
    expect(card?.getAttribute('data-priority')).toBe('critical')
    expect(card?.getAttribute('aria-label')).toContain('critical priority')
  })

  it('card renders updated metadata with non-empty text', () => {
    const task = makeTask({ id: 1, updated: '2026-05-15T10:00:00Z' })
    const { container } = renderCard(task)
    const updatedMetadata = container.querySelector('[data-testid="card-updated"]')
    expect(updatedMetadata).not.toBeNull()
    expect(updatedMetadata!.textContent?.trim().length).toBeGreaterThan(0)
  })

  it('card renders visible title element with correct task title text (AC-1 title fixture)', () => {
    // AC-1 explicitly requires E2E rendering fixtures for task title.
    // Architect refinement (second review cycle): task-local proof for card-title
    // required — re-dispatched to test-writer/builder.
    // Note: path guard prevents test-writer from writing to e2e/; this Vitest test
    // provides unit-level AC-1 title proof. Builder must add the companion E2E
    // assertion to serve/cockpit/web/e2e/card-density.spec.ts (see Builder Notes).
    const task = makeTask({ id: 1, title: 'My specific task title' })
    const { container } = renderCard(task)
    const titleEl = container.querySelector('[data-testid="card-title"]')
    expect(titleEl).not.toBeNull()
    expect(titleEl!.textContent?.trim()).toBe('My specific task title')
  })
})

// ─── AC-4 (density retry): Update recency branches via formatUpdatedAge ───────
// Uses vi.useFakeTimers() to control Date.now() so branch outputs are deterministic.
// "now" = 2026-05-15T12:00:00Z for all tests in this block.

describe('TestFromAC_UpdateRecencyBranches', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-15T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders minutes-ago label for timestamp 10 minutes before now', () => {
    // 2026-05-15T11:50:00Z → 10 minutes ago → "10m ago"
    const task = makeTask({ id: 1, updated: '2026-05-15T11:50:00Z' })
    const { container } = renderCard(task)
    const chip = container.querySelector('[data-testid="card-updated"]')
    expect(chip).not.toBeNull()
    expect(chip!.textContent).toBe('10m ago')
  })

  it('renders hours-ago label for timestamp 2 hours before now', () => {
    // 2026-05-15T10:00:00Z → 120 minutes → "2h ago"
    const task = makeTask({ id: 1, updated: '2026-05-15T10:00:00Z' })
    const { container } = renderCard(task)
    const chip = container.querySelector('[data-testid="card-updated"]')
    expect(chip).not.toBeNull()
    expect(chip!.textContent).toBe('2h ago')
  })

  it('renders days-ago label for timestamp 3 days before now', () => {
    // 2026-05-12T12:00:00Z → 72 hours = 4320 minutes → "3d ago"
    const task = makeTask({ id: 1, updated: '2026-05-12T12:00:00Z' })
    const { container } = renderCard(task)
    const chip = container.querySelector('[data-testid="card-updated"]')
    expect(chip).not.toBeNull()
    expect(chip!.textContent).toBe('3d ago')
  })

  it('renders fallback label for invalid updated timestamp', () => {
    // Non-parseable date → formatUpdatedAge returns "Updated recently"
    const task = makeTask({ id: 1, updated: 'not-a-date' })
    const { container } = renderCard(task)
    const chip = container.querySelector('[data-testid="card-updated"]')
    expect(chip).not.toBeNull()
    expect(chip!.textContent).toBe('Updated recently')
  })

  it('stale task (months old) renders different recency text than a recent task', () => {
    // Constant-label guard: proves formatUpdatedAge output varies with updated.
    // A constant non-ISO label (e.g. "Updated recently") would pass non-empty / non-ISO
    // checks but fails here because the two timestamps must produce different outputs.
    const recentTask = makeTask({ id: 1, updated: '2026-05-15T11:50:00Z' }) // 10m ago
    const staleTask = makeTask({ id: 2, updated: '2026-01-01T00:00:00Z' })  // 134d ago

    const { container: recentContainer } = renderCard(recentTask)
    const { container: staleContainer } = renderCard(staleTask)

    const recentText = recentContainer.querySelector('[data-testid="card-updated"]')!.textContent
    const staleText = staleContainer.querySelector('[data-testid="card-updated"]')!.textContent
    expect(recentText).not.toEqual(staleText)
  })
})

// ─── AC-1/AC-2 (density retry): Cue element rendering and accessibility ───────

describe('TestFromAC_CardCueRendering', () => {
  it('blocked card uses primary signal text without duplicating card-blocked-cue', () => {
    const task = makeTask({ id: 1, blocked: true })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent?.toLowerCase()).toContain('blocked')
    expect(container.querySelector('[data-testid="card-blocked-cue"]')).toBeNull()
  })

  it('non-blocked card does not render card-blocked-cue element', () => {
    const task = makeTask({ id: 1, blocked: false })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-blocked-cue"]')).toBeNull()
  })

  it('claimed card uses primary signal text without duplicating card-claimed-cue', () => {
    const task = makeTask({ id: 1, claimed: true })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent?.toLowerCase()).toContain('claimed')
    expect(container.querySelector('[data-testid="card-claimed-cue"]')).toBeNull()
  })

  it('non-claimed card does not render card-claimed-cue element', () => {
    const task = makeTask({ id: 1, claimed: false })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-claimed-cue"]')).toBeNull()
  })

  it('deps-unmet card uses primary signal text without duplicating card-deps-unmet-cue', () => {
    const task = makeTask({ id: 1, dep_status: 'blocked' })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent?.toLowerCase()).toMatch(/deps|depend/)
    expect(container.querySelector('[data-testid="card-deps-unmet-cue"]')).toBeNull()
  })

  it('task with dep_status=null does not render card-deps-unmet-cue element', () => {
    const task = makeTask({ id: 1, dep_status: null })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-deps-unmet-cue"]')).toBeNull()
  })

  it('dr-pending card uses primary signal text without duplicating card-dr-pending-cue', () => {
    const task = makeTask({ id: 7 })
    const { container } = renderCard(task, new Set([7]))
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent?.toLowerCase()).toMatch(/decision/)
    expect(container.querySelector('[data-testid="card-dr-pending-cue"]')).toBeNull()
  })

  it('higher-priority decision signal preserves blocked as a secondary cue when both are active', () => {
    const task = makeTask({ id: 7, blocked: true })
    const { container } = renderCard(task, new Set([7]))
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent?.toLowerCase()).toContain('decision')
    const cue = container.querySelector('[data-testid="card-blocked-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.toLowerCase()).toContain('blocked')
  })

  it('task not in pendingDRIds does not render card-dr-pending-cue element', () => {
    const task = makeTask({ id: 8 })
    const { container } = renderCard(task, new Set([99]))
    expect(container.querySelector('[data-testid="card-dr-pending-cue"]')).toBeNull()
  })

  it('task with no tags does not render card-tags element', () => {
    const task = makeTask({ id: 1, tags: [] })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-tags"]')).toBeNull()
  })

  it('task with 1–3 tags renders card-tags element without overflow indicator', () => {
    const task = makeTask({ id: 1, tags: ['frontend', 'backend'] })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-tags"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="card-tag-overflow"]')).toBeNull()
  })

  it('task with more than 3 tags renders all tags without overflow indicator', () => {
    const task = makeTask({ id: 1, tags: ['a', 'b', 'c', 'd', 'e'] })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-tags"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="card-tag-overflow"]')).toBeNull()
    expect(container.querySelectorAll('[data-testid="card-tag"]').length).toBe(5)
  })

  // AC-2 retry gap-fill (#1570): tag preview text contains actual tag names
  // Reviewer Finding #2: tests proved card-tags element presence but never
  // asserted the preview text rendered from previewTags.join(', ').
  it('task with multiple tags renders card-tags element with tag names as text content', () => {
    const task = makeTask({ id: 1, tags: ['frontend', 'backend'] })
    const { container } = renderCard(task)
    const tagsEl = container.querySelector('[data-testid="card-tags"]')
    expect(tagsEl).not.toBeNull()
    expect(tagsEl!.textContent).toContain('frontend')
    expect(tagsEl!.textContent).toContain('backend')
  })

  it('task with 5 tags renders card-tags element showing every tag name in text content', () => {
    const task = makeTask({ id: 1, tags: ['a', 'b', 'c', 'd', 'e'] })
    const { container } = renderCard(task)
    const tagsEl = container.querySelector('[data-testid="card-tags"]')
    expect(tagsEl).not.toBeNull()
    const text = tagsEl!.textContent ?? ''
    expect(text).toContain('a')
    expect(text).toContain('b')
    expect(text).toContain('c')
    expect(text).toContain('d')
    expect(text).toContain('e')
  })
})
