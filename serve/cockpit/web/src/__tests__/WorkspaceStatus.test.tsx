import { useState } from 'react'
import { createPortal } from 'react-dom'
import { fireEvent, render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import { describe, expect, it, vi } from 'vitest'
import WorkspaceStatus from '../components/WorkspaceStatus'
import type { WorkspaceHealthResponse } from '../hooks/useWorkspaceHealth'

function renderStatus(health: WorkspaceHealthResponse, options: {
  connectionError?: string
  taskAction?: (onComplete: () => void) => React.ReactNode
  onRefresh?: () => void
} = {}) {
  return render(
    <PorscheDesignSystemProvider>
      <WorkspaceStatus health={health} {...options} />
    </PorscheDesignSystemProvider>,
  )
}

function PortaledTaskAction({ onConfirm }: { onConfirm: () => void }) {
  const [confirming, setConfirming] = useState(false)
  return (
    <>
      <button type="button" onClick={() => setConfirming(true)}>Repair tasks</button>
      {confirming ? createPortal(
        <div data-testid="repair-dialog" data-workspace-status-overlay="">
          <button type="button" onClick={onConfirm}>Confirm repair</button>
        </div>,
        document.body,
      ) : null}
    </>
  )
}

describe('WorkspaceStatus', () => {
  it('starts gray and labels every unknown module before evidence arrives', () => {
    const health: WorkspaceHealthResponse = {
      status: 'checking',
      modules: {
        tasks: { status: 'unknown' },
        requests: { status: 'unknown' },
        memory: { status: 'unknown' },
        ideas: { status: 'unknown' },
      },
    }
    const { container } = renderStatus(health)

    expect(container.querySelector('[data-testid="traffic-light"]')).toHaveAttribute('data-health', 'checking')
    fireEvent.click(container.querySelector('[data-testid="workspace-status"]')!)
    for (const module of ['tasks', 'requests', 'memory', 'ideas']) {
      expect(container.querySelector(`[data-testid="workspace-module-${module}"]`)).toHaveAttribute('data-health', 'unknown')
    }
    expect(container.textContent).toContain('Unknown')
  })

  it('keeps repair available on a red task row and exposes only unresolved findings', () => {
    const health: WorkspaceHealthResponse = {
      status: 'unhealthy',
      modules: {
        tasks: {
          status: 'unhealthy',
          repairable_count: 2,
          findings: [
            { code: 'MOVE_ONE', path: '/tasks/one.md', detail: 'Move to archive', repairable: true },
            { code: 'MOVE_TWO', path: '/tasks/two.md', detail: 'Move to archive', repairable: true },
            { code: 'BROKEN_REF', path: '/tasks/three.md', detail: 'Missing dependency', repairable: false },
          ],
        },
        requests: { status: 'healthy', findings: [] },
        memory: { status: 'attention', findings: [{ code: 'REPAIRABLE', repairable: true }] },
        ideas: { status: 'check-failed', findings: [{ detail: 'Unreadable' }] },
      },
    }
    const { container } = renderStatus(health, { taskAction: () => <button type="button">Repair tasks</button> })

    fireEvent.click(container.querySelector('[data-testid="workspace-status"]')!)
    const taskRow = container.querySelector('[data-testid="workspace-module-tasks"]')!
    expect(taskRow).toHaveAttribute('data-health', 'unhealthy')
    expect(taskRow.textContent).toContain('3 findings, 2 repairable')
    expect(taskRow.textContent).toContain('Repair tasks')
    expect(taskRow.textContent).toContain('/tasks/three.md')
    expect(taskRow.textContent).not.toContain('/tasks/one.md')
    expect(taskRow.textContent).not.toContain('/tasks/two.md')
    expect(container.querySelector('[data-testid="workspace-module-memory"]')).toHaveAttribute('data-health', 'attention')
    expect(container.querySelector('[data-testid="workspace-module-ideas"]')).toHaveAttribute('data-health', 'check-failed')
  })

  it('shows the connection problem and exposes an explicit retry', () => {
    const onRefresh = vi.fn()
    const health: WorkspaceHealthResponse = {
      status: 'check-failed',
      modules: {},
    }
    const { container, getByText } = renderStatus(health, { connectionError: 'backend offline', onRefresh })

    fireEvent.click(container.querySelector('[data-testid="workspace-status"]')!)
    expect(container.textContent).toContain('Connection problem: backend offline')
    fireEvent.click(getByText('Run check again'))
    expect(onRefresh).toHaveBeenCalledOnce()
  })

  it('keeps portaled task actions mounted through their pointerdown and click sequence', () => {
    const onConfirm = vi.fn()
    const health: WorkspaceHealthResponse = {
      status: 'attention',
      modules: { tasks: { status: 'attention', repairable_count: 1, findings: [] } },
    }
    const { container, getByText } = renderStatus(health, {
      taskAction: (closeStatus) => (
        <PortaledTaskAction onConfirm={() => {
          onConfirm()
          closeStatus()
        }} />
      ),
    })

    fireEvent.click(container.querySelector('[data-testid="workspace-status"]')!)
    fireEvent.click(getByText('Repair tasks'))
    const confirm = getByText('Confirm repair')
    fireEvent.pointerDown(confirm)
    expect(container.querySelector('[data-testid="workspace-status-popover"]')).not.toBeNull()
    fireEvent.click(confirm)
    expect(onConfirm).toHaveBeenCalledOnce()
    expect(container.querySelector('[data-testid="workspace-status-popover"]')).toBeNull()
  })
})
