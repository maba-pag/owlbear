/**
 * Card visual treatment tests — tasks #1615, #1696, #1706
 *
 * AC coverage:
 *   AC-1: Status and priority do not render as visible card chips; status is
 *         encoded by the column and priority remains on data/ARIA plus the rail.
 *   AC-2: Ready/default cards do not render a signal chip; exceptional signals do.
 *   AC-3: Signal icon renders as <p-icon size="xs" aria-label={signal}> for
 *         dr-pending, blocked, claimed, deps-unmet; no p-icon element in DOM when signal is ready
 *   AC-4: Each visible tag (up to TAG_PREVIEW_LIMIT=3) renders as individual
 *         <PTag compact variant="secondary">; overflow count indicator preserved
 *   AC-5: Existing state cue text spans (Blocked, Claimed, Dependencies blocked,
 *         Decision pending) preserved unchanged
 *   AC-6: No inline hex color values in Card output; source imports PTag from PDS
 *
 * Regression focus:
 *   - No redundant status or priority bubbles on Kanban cards.
 *   - Ordinary tags stay secondary/grey so they do not compete with alerts.
 *   - Exceptional operational cues remain visible and perceivable without color alone.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Card } from '../components/Card'
import type { Task } from '../hooks/useBoard'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// ─── Fixture factory ──────────────────────────────────────────────────────────

interface CardTask {
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

function makeTask(overrides: Partial<CardTask> & { id: number }): CardTask {
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

function renderCard(task: CardTask, pendingDRIds: Set<number> = new Set()) {
  return render(
    <Card
      task={task as unknown as Task}
      pendingDRIds={pendingDRIds}
      onContextMenu={() => {}}
    />,
  )
}

// ─── AC-1: Status and priority do not render as visible card chips ───────────

describe('Card metadata declutter', () => {
  it('does not render a visible status chip because the column already communicates status', () => {
    const task = makeTask({ id: 1, status: 'todo' })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-status"]')).toBeNull()
  })

  it('does not render a visible priority chip because priority is encoded by the rail and ARIA label', () => {
    const task = makeTask({ id: 1, priority: 'critical' })
    const { container } = renderCard(task)
    const card = container.querySelector('[data-testid="task-card"]')
    expect(container.querySelector('[data-testid="card-priority"]')).toBeNull()
    expect(card?.getAttribute('data-priority')).toBe('critical')
    expect(card?.getAttribute('aria-label')).toContain('critical priority')
  })

  it('does not render a default ready signal chip on ordinary cards', () => {
    const task = makeTask({ id: 1 })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-signal"]')).toBeNull()
  })
})

// ─── AC-3: Signal icon renders as PIcon ──────────────────────────────────────

describe('Card signal icon', () => {
  it('dr-pending signal renders p-icon with size="xs" and aria-label="dr-pending"', () => {
    const task = makeTask({ id: 5 })
    const { container } = renderCard(task, new Set([5]))
    const icon = container.querySelector('p-icon[size="xs"][aria-label="dr-pending"]')
    expect(icon).not.toBeNull()
  })

  it('blocked signal renders p-icon with size="xs" and aria-label="blocked"', () => {
    const task = makeTask({ id: 1, blocked: true })
    const { container } = renderCard(task)
    const icon = container.querySelector('p-icon[size="xs"][aria-label="blocked"]')
    expect(icon).not.toBeNull()
  })

  it('claimed signal renders p-icon with size="xs" and aria-label="claimed"', () => {
    const task = makeTask({ id: 1, claimed: true })
    const { container } = renderCard(task)
    const icon = container.querySelector('p-icon[size="xs"][aria-label="claimed"]')
    expect(icon).not.toBeNull()
  })

  it('deps-unmet signal renders p-icon with size="xs" and aria-label="deps-unmet"', () => {
    const task = makeTask({ id: 1, dep_status: 'blocked' })
    const { container } = renderCard(task)
    const icon = container.querySelector('p-icon[size="xs"][aria-label="deps-unmet"]')
    expect(icon).not.toBeNull()
    expect((icon as Element & { name?: string }).name ?? icon!.getAttribute('name')).toBe('unlinked')
  })

  it('ready signal renders no p-icon element — confirmed by blocked card having p-icon', () => {
    const blockedTask = makeTask({ id: 1, blocked: true })
    const { container: blockedContainer } = renderCard(blockedTask)
    expect(blockedContainer.querySelector('p-icon[aria-label="blocked"]')).not.toBeNull()

    const readyTask = makeTask({ id: 2 })
    const { container: readyContainer } = renderCard(readyTask)
    expect(readyContainer.querySelector('p-icon')).toBeNull()
  })

  it('card with no active signals renders no p-icon element', () => {
    // Positive anchor: blocked variant must have p-icon before we can assert ready has none.
    const blockedTask = makeTask({ id: 99, blocked: true })
    const { container: blockedContainer } = renderCard(blockedTask)
    expect(blockedContainer.querySelector('p-icon')).not.toBeNull()

    // Now verify: no signals → no icon
    const cleanTask = makeTask({ id: 10, status: 'done' })
    const { container } = renderCard(cleanTask, new Set())
    expect(container.querySelector('p-icon')).toBeNull()
  })
})

// ─── AC-4: Tags render as individual PTag elements ───────────────────────────

describe('Card tag pills', () => {
  it('one tag renders as exactly one p-tag[compact][variant="secondary"] pill', () => {
    const task = makeTask({ id: 1, status: 'in-progress', priority: 'critical', tags: ['frontend'] })
    const { container } = renderCard(task)
    const tagPills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(tagPills.length).toBe(1)
  })

  it('three tags render exactly three p-tag[compact][variant="secondary"] pills', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c'],
    })
    const { container } = renderCard(task)
    const tagPills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(tagPills.length).toBe(3)
  })

  it('four tags render exactly three tag pills (TAG_PREVIEW_LIMIT=3 caps display)', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c', 'd'],
    })
    const { container } = renderCard(task)
    const tagPills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(tagPills.length).toBe(3)
  })

  it('five tags render three tag pills showing the first three tag names', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['frontend', 'backend', 'urgent', 'blocked', 'pds'],
    })
    const { container } = renderCard(task)
    const tagPills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(tagPills.length).toBe(3)
    const texts = Array.from(tagPills).map((el) => el.textContent?.trim())
    expect(texts).toContain('frontend')
    expect(texts).toContain('backend')
    expect(texts).toContain('urgent')
    expect(texts).not.toContain('blocked')
    expect(texts).not.toContain('pds')
  })

  it('zero tags renders no p-tag pill elements with variant="secondary"', () => {
    // Positive anchor: one-tag case must have a pill first.
    const oneTagTask = makeTask({ id: 99, status: 'in-progress', priority: 'critical', tags: ['x'] })
    const { container: oneTagContainer } = renderCard(oneTagTask)
    expect(oneTagContainer.querySelectorAll('p-tag[compact][variant="secondary"]').length).toBe(1)

    // Now verify: zero tags → no pills
    const task = makeTask({ id: 1, status: 'in-progress', priority: 'critical', tags: [] })
    const { container } = renderCard(task)
    expect(container.querySelectorAll('p-tag[compact][variant="secondary"]').length).toBe(0)
  })

  it('overflow count indicator preserved when tags exceed TAG_PREVIEW_LIMIT=3', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c', 'd', 'e'],
    })
    const { container } = renderCard(task)
    const pills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(pills.length).toBe(3)
    // Regression guard: overflow indicator preserved alongside tag pills
    const overflow = container.querySelector('[data-testid="card-tag-overflow"]')
    expect(overflow).not.toBeNull()
    expect(overflow!.textContent).toContain('+2')
  })

  it('tag preview wraps visible pills instead of clipping rendered tags', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['cockpit-perfect-ui', 'scope:cockpit-web', 'ux-feedback', 'kanban', 'visual-system'],
    })
    const { container } = renderCard(task)
    const tagGroup = container.querySelector('[data-testid="card-tags"]')
    const classes = tagGroup?.getAttribute('class') ?? ''

    expect(tagGroup).not.toBeNull()
    expect(classes).toContain('flex-wrap')
    expect(classes).not.toContain('overflow-hidden')
    expect(classes).not.toContain('whitespace-nowrap')
    expect(classes).not.toContain('text-ellipsis')
  })

  it('overflow indicator absent when tags are within TAG_PREVIEW_LIMIT', () => {
    // Positive anchor: above-limit case must have both pills AND overflow.
    const manyTask = makeTask({
      id: 99,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c', 'd'],
    })
    const { container: manyContainer } = renderCard(manyTask)
    expect(manyContainer.querySelectorAll('p-tag[compact][variant="secondary"]').length).toBe(3)
    expect(manyContainer.querySelector('[data-testid="card-tag-overflow"]')).not.toBeNull()

    // Main assertion: 3 tags → exactly 3 pills, no overflow
    const task = makeTask({ id: 1, status: 'in-progress', priority: 'critical', tags: ['a', 'b', 'c'] })
    const { container } = renderCard(task)
    expect(container.querySelectorAll('p-tag[compact][variant="secondary"]').length).toBe(3)
    expect(container.querySelector('[data-testid="card-tag-overflow"]')).toBeNull()
  })
})

// ─── AC-5: Existing state cue text spans preserved unchanged (regression guard) ─

describe('Card cue text preservation', () => {
  it('blocked card retains card-blocked-cue span with text "Blocked"', () => {
    const task = makeTask({ id: 1, blocked: true, status: 'todo' })
    const { container } = renderCard(task)
    const cue = container.querySelector('[data-testid="card-blocked-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.trim()).toBe('Blocked')
  })

  it('claimed card retains card-claimed-cue span with text "Claimed"', () => {
    const task = makeTask({ id: 1, claimed: true, status: 'in-progress' })
    const { container } = renderCard(task)
    const cue = container.querySelector('[data-testid="card-claimed-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.trim()).toBe('Claimed')
  })

  it('deps-unmet card retains card-deps-unmet-cue span with text "Dependencies blocked"', () => {
    const task = makeTask({ id: 1, dep_status: 'blocked', status: 'todo' })
    const { container } = renderCard(task)
    const cue = container.querySelector('[data-testid="card-deps-unmet-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.trim()).toBe('Dependencies blocked')
  })

  it('dr-pending card retains card-dr-pending-cue span with text "Decision pending"', () => {
    const task = makeTask({ id: 7, status: 'todo' })
    const { container } = renderCard(task, new Set([7]))
    const cue = container.querySelector('[data-testid="card-dr-pending-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.trim()).toBe('Decision pending')
  })
})

// ─── AC-6: No inline hex color values in Card output ─────────────────────────

describe('Card color token usage', () => {
  it('Card.tsx source contains no no-restricted-syntax eslint-disable comment', () => {
    const cardSrcPath = resolve(__dirname, '../components/Card.tsx')
    const src = readFileSync(cardSrcPath, 'utf-8')
    expect(src).not.toContain('eslint-disable no-restricted-syntax')
  })

  it('Card.tsx source imports PTag from @porsche-design-system/components-react', () => {
    const cardSrcPath = resolve(__dirname, '../components/Card.tsx')
    const src = readFileSync(cardSrcPath, 'utf-8')
    expect(src).toContain('PTag')
    expect(src).toContain('@porsche-design-system/components-react')
  })

  it('Card.tsx source contains no inline hex color values', () => {
    // This is a regression guard — hex patterns like #fff or #aabbcc must not appear
    // in JSX style props.
    const cardSrcPath = resolve(__dirname, '../components/Card.tsx')
    const src = readFileSync(cardSrcPath, 'utf-8')
    expect(src).toContain('PTag')
    const hexPattern = /#[0-9a-fA-F]{3,8}\b/g
    const matches = src.match(hexPattern) ?? []
    expect(matches).toHaveLength(0)
  })

  it('rendered Card output has no elements with inline style containing hex color values', () => {
    const task = makeTask({ id: 1, status: 'todo', priority: 'critical' })
    const { container } = renderCard(task)
    const elementsWithStyle = container.querySelectorAll('[style]')
    for (const el of elementsWithStyle) {
      const style = el.getAttribute('style') ?? ''
      expect(style).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    }
  })
})
