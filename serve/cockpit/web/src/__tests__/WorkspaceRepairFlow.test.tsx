import { act, fireEvent, render, renderHook } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { WorkspaceRepairResponse } from '../api/repair'
import RepairReceipt from '../components/RepairReceipt'
import { useRepairFlow } from '../hooks/useRepairFlow'

vi.mock('../api/repair', () => ({ repairWorkspace: vi.fn() }))

import { repairWorkspace } from '../api/repair'

const RECEIPT: WorkspaceRepairResponse = {
  status: 'completed',
  started_at: '2026-07-20T03:59:58Z',
  completed_at: '2026-07-20T04:00:00Z',
  removed_count: 1,
  moved_count: 2,
  quarantined_count: 3,
  skipped_count: 4,
  failed_count: 1,
  unresolved_count: 1,
  outcomes: [
    { task_id: 1, file_path: '/tasks/removed.md', code: 'REMOVED', action: 'removed', detail: 'Do not show this detail' },
    { task_id: 2, file_path: '/tasks/failed.md', code: 'FAILED_MOVE', action: 'failed', detail: 'Permission denied' },
  ],
  unresolved_findings: [
    { path: '/tasks/unresolved.md', code: 'BROKEN_REF', detail: 'Missing dependency', repairable: false },
  ],
  task_health_result: {
    findings: [{ path: '/tasks/unresolved.md', code: 'BROKEN_REF', repairable: false }],
    repairable_count: 0,
    checked_paths: ['tasks'],
  },
}

describe('workspace repair flow', () => {
  beforeEach(() => vi.resetAllMocks())

  it('closes the execution flow and hands the complete receipt to provider state', async () => {
    vi.mocked(repairWorkspace).mockResolvedValueOnce(RECEIPT)
    const onSuccess = vi.fn()
    const { result } = renderHook(() => useRepairFlow({ onSuccess }))

    act(() => result.current.requestRepair(2))
    expect(result.current.phase).toBe('confirming')
    await act(async () => result.current.confirmRepair())

    expect(repairWorkspace).toHaveBeenCalledOnce()
    expect(onSuccess).toHaveBeenCalledWith(RECEIPT)
    expect(result.current.phase).toBe('idle')
    expect(result.current.repairableCount).toBeNull()
  })

  it('keeps an orchestration error actionable without creating a completed receipt', async () => {
    vi.mocked(repairWorkspace).mockRejectedValueOnce(new Error('post-scan failed'))
    const onSuccess = vi.fn()
    const { result } = renderHook(() => useRepairFlow({ onSuccess }))

    act(() => result.current.requestRepair(1))
    await act(async () => result.current.confirmRepair())

    expect(result.current.phase).toBe('error')
    expect(result.current.error).toBe('post-scan failed')
    expect(onSuccess).not.toHaveBeenCalled()
  })

  it('shows all terminal counts and only failed or unresolved details until dismissed', () => {
    const onDismiss = vi.fn()
    const { getByText } = render(
      <PorscheDesignSystemProvider>
        <RepairReceipt receipt={RECEIPT} onDismiss={onDismiss} />
      </PorscheDesignSystemProvider>,
    )

    expect(document.body.querySelector('[data-testid="repair-count-removed_count"]')).toHaveTextContent('1')
    expect(document.body.querySelector('[data-testid="repair-count-moved_count"]')).toHaveTextContent('2')
    expect(document.body.querySelector('[data-testid="repair-count-quarantined_count"]')).toHaveTextContent('3')
    expect(document.body.querySelector('[data-testid="repair-count-skipped_count"]')).toHaveTextContent('4')
    expect(document.body.querySelector('[data-testid="repair-count-failed_count"]')).toHaveTextContent('1')
    expect(document.body.querySelector('[data-testid="repair-count-unresolved_count"]')).toHaveTextContent('1')
    expect(document.body.textContent).toContain('/tasks/failed.md')
    expect(document.body.textContent).toContain('/tasks/unresolved.md')
    expect(document.body.textContent).not.toContain('/tasks/removed.md')

    fireEvent.click(getByText('Dismiss'))
    expect(onDismiss).toHaveBeenCalledOnce()
  })
})
