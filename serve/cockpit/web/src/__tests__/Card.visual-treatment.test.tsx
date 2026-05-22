/**
 * Card visual treatment tests — tasks #1615, #1696, #1706
 *
 * AC coverage:
 *   AC-1: Status and priority do not render as visible card chips; status is
 *         encoded by the column and priority remains on data/ARIA plus the rail.
 *   AC-2: Ready/default cards do not render a signal chip; exceptional signals do.
 *   AC-3: Signal icon renders as <p-icon size="xs" aria-label={signal}> for
 *         dr-pending, blocked, claimed, deps-unmet; no p-icon element in DOM when signal is ready
 *   AC-4: Each visible tag (up to TAG_PREVIEW_LIMIT=3) renders as quiet text
 *         metadata; overflow count indicator preserved without pill styling
 *   AC-5: Primary card signals are not duplicated as secondary cue text; lower
 *         precedence cues remain visible when they add new information
 *   AC-6: No inline hex color values in Card output; source keeps PDS icons
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

// ─── AC-4: Tags render as quiet metadata text ────────────────────────────────

describe('Card tag metadata', () => {
  it('one tag renders as exactly one quiet metadata text item', () => {
    const task = makeTask({ id: 1, status: 'in-progress', priority: 'critical', tags: ['frontend'] })
    const { container } = renderCard(task)
    const tags = container.querySelectorAll('[data-testid="card-tag"]')
    expect(tags.length).toBe(1)
    expect(container.querySelector('p-tag')).toBeNull()
  })

  it('three tags render exactly three metadata text items', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c'],
    })
    const { container } = renderCard(task)
    const tags = container.querySelectorAll('[data-testid="card-tag"]')
    expect(tags.length).toBe(3)
  })

  it('four tags render exactly three tag text items (TAG_PREVIEW_LIMIT=3 caps display)', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c', 'd'],
    })
    const { container } = renderCard(task)
    const tags = container.querySelectorAll('[data-testid="card-tag"]')
    expect(tags.length).toBe(3)
  })

  it('five tags render three text tags showing the first three tag names', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['frontend', 'backend', 'urgent', 'blocked', 'pds'],
    })
    const { container } = renderCard(task)
    const tags = container.querySelectorAll('[data-testid="card-tag"]')
    expect(tags.length).toBe(3)
    const texts = Array.from(tags).map((el) => el.textContent?.trim())
    expect(texts).toContain('frontend')
    expect(texts).toContain('backend')
    expect(texts).toContain('urgent')
    expect(texts).not.toContain('blocked')
    expect(texts).not.toContain('pds')
  })

  it('zero tags renders no tag text elements', () => {
    // Positive anchor: one-tag case must have a tag first.
    const oneTagTask = makeTask({ id: 99, status: 'in-progress', priority: 'critical', tags: ['x'] })
    const { container: oneTagContainer } = renderCard(oneTagTask)
    expect(oneTagContainer.querySelectorAll('[data-testid="card-tag"]').length).toBe(1)

    // Now verify: zero tags → no tag metadata
    const task = makeTask({ id: 1, status: 'in-progress', priority: 'critical', tags: [] })
    const { container } = renderCard(task)
    expect(container.querySelectorAll('[data-testid="card-tag"]').length).toBe(0)
  })

  it('overflow count indicator preserved when tags exceed TAG_PREVIEW_LIMIT=3', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c', 'd', 'e'],
    })
    const { container } = renderCard(task)
    const tags = container.querySelectorAll('[data-testid="card-tag"]')
    expect(tags.length).toBe(3)
    // Regression guard: overflow indicator preserved alongside tag metadata
    const overflow = container.querySelector('[data-testid="card-tag-overflow"]')
    expect(overflow).not.toBeNull()
    expect(overflow!.textContent).toContain('+2 tags')
  })

  it('tag preview wraps visible metadata text instead of clipping rendered tags', () => {
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
    // Positive anchor: above-limit case must have both tag metadata AND overflow.
    const manyTask = makeTask({
      id: 99,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c', 'd'],
    })
    const { container: manyContainer } = renderCard(manyTask)
    expect(manyContainer.querySelectorAll('[data-testid="card-tag"]').length).toBe(3)
    expect(manyContainer.querySelector('[data-testid="card-tag-overflow"]')).not.toBeNull()

    // Main assertion: 3 tags → exactly 3 text tags, no overflow
    const task = makeTask({ id: 1, status: 'in-progress', priority: 'critical', tags: ['a', 'b', 'c'] })
    const { container } = renderCard(task)
    expect(container.querySelectorAll('[data-testid="card-tag"]').length).toBe(3)
    expect(container.querySelector('[data-testid="card-tag-overflow"]')).toBeNull()
  })

  it('hides active-decision from normal tags when a pending decision signal is already visible', () => {
    const task = makeTask({
      id: 7,
      tags: ['active-decision', 'frontend', 'backend'],
    })
    const { container } = renderCard(task, new Set([7]))
    const tags = container.querySelector('[data-testid="card-tags"]')
    const tagTexts = Array.from(container.querySelectorAll('[data-testid="card-tag"]')).map((el) => el.textContent?.trim())

    expect(container.querySelector('[data-testid="card-signal"]')?.textContent).toContain('Decision')
    expect(tags?.textContent).not.toContain('active-decision')
    expect(tagTexts).toEqual(['frontend', 'backend'])
  })

  it('keeps active-decision as ordinary metadata when there is no pending decision signal', () => {
    const task = makeTask({
      id: 7,
      tags: ['active-decision', 'frontend'],
    })
    const { container } = renderCard(task)
    const tagTexts = Array.from(container.querySelectorAll('[data-testid="card-tag"]')).map((el) => el.textContent?.trim())

    expect(container.querySelector('[data-testid="card-signal"]')).toBeNull()
    expect(tagTexts).toEqual(['active-decision', 'frontend'])
  })
})

// ─── AC-5: Secondary cues avoid duplicating the primary signal ───────────────

describe('Card cue text hierarchy', () => {
  it('blocked card uses the primary signal without duplicating a blocked secondary cue', () => {
    const task = makeTask({ id: 1, blocked: true, status: 'todo' })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent).toContain('Blocked')
    expect(container.querySelector('[data-testid="card-blocked-cue"]')).toBeNull()
  })

  it('claimed card uses the primary signal without duplicating a claimed secondary cue', () => {
    const task = makeTask({ id: 1, claimed: true, status: 'in-progress' })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent).toContain('Claimed')
    expect(container.querySelector('[data-testid="card-claimed-cue"]')).toBeNull()
  })

  it('deps-unmet card uses the primary signal without duplicating a dependency secondary cue', () => {
    const task = makeTask({ id: 1, dep_status: 'blocked', status: 'todo' })
    const { container } = renderCard(task)
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent).toContain('Dependencies')
    expect(container.querySelector('[data-testid="card-deps-unmet-cue"]')).toBeNull()
  })

  it('dr-pending card uses the primary signal without duplicating a decision secondary cue', () => {
    const task = makeTask({ id: 7, status: 'todo' })
    const { container } = renderCard(task, new Set([7]))
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent).toContain('Decision')
    expect(container.querySelector('[data-testid="card-dr-pending-cue"]')).toBeNull()
  })

  it('higher-priority decision signal still shows a blocked secondary cue when the task is also blocked', () => {
    const task = makeTask({ id: 7, status: 'todo', blocked: true })
    const { container } = renderCard(task, new Set([7]))
    expect(container.querySelector('[data-testid="card-signal"]')?.textContent).toContain('Decision')
    const cue = container.querySelector('[data-testid="card-blocked-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.trim()).toBe('Blocked')
  })
})

// ─── AC-6: No inline hex color values in Card output ─────────────────────────

describe('Card color token usage', () => {
  it('Card.tsx source contains no no-restricted-syntax eslint-disable comment', () => {
    const cardSrcPath = resolve(__dirname, '../components/Card.tsx')
    const src = readFileSync(cardSrcPath, 'utf-8')
    expect(src).not.toContain('eslint-disable no-restricted-syntax')
  })

  it('Card.tsx source imports PIcon from @porsche-design-system/components-react', () => {
    const cardSrcPath = resolve(__dirname, '../components/Card.tsx')
    const src = readFileSync(cardSrcPath, 'utf-8')
    expect(src).toContain('PIcon')
    expect(src).toContain('@porsche-design-system/components-react')
  })

  it('Card.tsx source contains no inline hex color values', () => {
    // This is a regression guard — hex patterns like #fff or #aabbcc must not appear
    // in JSX style props.
    const cardSrcPath = resolve(__dirname, '../components/Card.tsx')
    const src = readFileSync(cardSrcPath, 'utf-8')
    expect(src).toContain('PIcon')
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
