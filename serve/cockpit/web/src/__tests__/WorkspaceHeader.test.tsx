import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  WorkspaceHeader,
  WorkspaceHeaderMetric,
  WorkspaceHeaderPill,
} from '../components/WorkspaceHeader'

describe('WorkspaceHeader', () => {
  it('renders a route title and summary with shared header test ids', () => {
    const { container } = render(
      <WorkspaceHeader
        title="Decisions"
        titleId="decisions-title"
        summaryLabel="Decision summary"
        summary={<WorkspaceHeaderMetric value={3} label="waiting" />}
      />,
    )

    expect(container.querySelector('[data-testid="workspace-header"]')).not.toBeNull()
    expect(container.querySelector('#decisions-title')?.textContent).toBe('Decisions')
    expect(container.querySelector('[data-testid="workspace-header-summary"]')?.textContent).toContain('3')
    expect(container.querySelector('[data-testid="workspace-header-summary"]')?.textContent).toContain('waiting')
    expect(container.querySelector('[data-testid="workspace-header-metric"]')?.className).not.toContain('border-l')
    expect(container.querySelector('[data-testid="workspace-header-metric"] strong')?.className).toContain('text-base')
  })

  it('can render a secondary heading and route actions', () => {
    const { container } = render(
      <WorkspaceHeader
        title="Kanban"
        titleId="kanban-board-title"
        headingLevel={2}
        actions={<button type="button">Filters</button>}
      />,
    )

    expect(container.querySelector('h2#kanban-board-title')?.textContent).toBe('Kanban')
    expect(container.querySelector('[data-testid="workspace-header-actions"]')?.textContent).toContain('Filters')
  })

  it('renders route state pills without changing metric text', () => {
    const { container } = render(
      <WorkspaceHeader
        title="Ideas"
        titleId="ideas-title"
        summary={(
          <>
            <WorkspaceHeaderPill tone="info">Unsaved</WorkspaceHeaderPill>
            <WorkspaceHeaderMetric value="10" label="words" />
          </>
        )}
      />,
    )

    const summary = container.querySelector('[data-testid="workspace-header-summary"]')
    expect(summary?.textContent).toContain('Unsaved')
    expect(summary?.textContent).toContain('10')
    expect(summary?.textContent).toContain('words')
  })

  it('only separates a metric when it follows another metric', () => {
    const { container } = render(
      <WorkspaceHeader
        title="Memory"
        titleId="memory-title"
        summary={(
          <>
            <WorkspaceHeaderMetric value="12" label="entries" />
            <WorkspaceHeaderMetric value="4" label="shown" />
          </>
        )}
      />,
    )

    const summary = container.querySelector('[data-testid="workspace-header-summary"]')
    const metrics = container.querySelectorAll('[data-testid="workspace-header-metric"]')

    expect(summary?.className).toContain('[&>[data-workspace-header-metric]~[data-workspace-header-metric]]:border-l')
    expect(metrics).toHaveLength(2)
    expect(metrics[0]?.className).not.toContain('border-l')
    expect(metrics[1]?.className).not.toContain('border-l')
  })
})
