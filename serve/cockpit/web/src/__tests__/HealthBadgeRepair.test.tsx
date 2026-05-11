/**
 * Workflow behavior tests1168: RF-06 RepairPanel wired into HealthBadge
 *
 * AC6 — RepairPanel rendered inside HealthBadge popover (data-testid="health-badge-popover")
 *        below the issue list when corruptionCount > 0
 * AC7 — useScanPolling exposes refetch(); RepairPanel accepts onSuccess prop threaded from
 *        caller (Shell/HealthBadge) via useScanPolling.refetch
 * AC8 — RepairPanel uses PDS components throughout (p-button, p-spinner, p-text)
 *
 * AC1–AC5 and AC9 are covered by #1167 tests (RepairPanel_1167.test.tsx). This suite
 * adds the integration and PDS-conversion contracts.
 *
 * All tests are RED (failing) until the builder implements AC6–AC8.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { renderHook, act } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { UseRepairFlowResult } from '../hooks/useRepairFlow'
import type { ScanItem } from '../components/HealthBadge'

// ─── Module mocks ─────────────────────────────────────────────────────────────
// useRepairFlow mocked at file scope so RepairPanel can be rendered without
// network calls in AC6 and AC8 tests.
// useScanPolling is NOT mocked here — TestFromAC_UseScanPollingRefetch exercises
// the real hook with a stubbed global fetch.

vi.mock('../hooks/useRepairFlow', () => ({
  useRepairFlow: vi.fn(),
}))

import { useRepairFlow } from '../hooks/useRepairFlow'
import RepairPanel from '../components/RepairPanel'
import HealthBadge from '../components/HealthBadge'
import { useScanPolling } from '../hooks/useScanPolling'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const ITEM_A: ScanItem = {
  code: 'E001',
  detail: 'Missing required field',
  file_path: '/tasks/TASK-001.md',
}

const ITEM_B: ScanItem = {
  code: 'CORRUPT_YAML',
  detail: 'YAML parse error',
  file_path: '/tasks/TASK-007.md',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function hookDefaults(): UseRepairFlowResult {
  return {
    phase: 'idle',
    corruptionCount: null,
    results: null,
    error: null,
    requestRepair: vi.fn(),
    confirmRepair: vi.fn(),
    cancelRepair: vi.fn(),
    dismissResults: vi.fn(),
  }
}

function mockHook(overrides: Partial<UseRepairFlowResult> = {}): UseRepairFlowResult {
  const merged = { ...hookDefaults(), ...overrides }
  vi.mocked(useRepairFlow).mockReturnValue(merged)
  return merged
}

// Renders HealthBadge with extra props forwarded (allows testing new builder-added props
// such as corruptionCount without TypeScript compile gating these RED tests).
function renderBadge(items: ScanItem[], extra: Record<string, unknown> = {}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const props = { items, ...(extra as any) }
  return render(
    <PorscheDesignSystemProvider>
      <HealthBadge {...props} />
    </PorscheDesignSystemProvider>,
  )
}

// Renders RepairPanel with extra props forwarded (allows testing new builder-added props
// such as onSuccess without TypeScript compile gating these RED tests).
function renderPanel(corruptionCount: number, extra: Record<string, unknown> = {}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const props = { corruptionCount, ...(extra as any) }
  return render(
    <PorscheDesignSystemProvider>
      <RepairPanel {...props} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── AC6: RepairPanel inside HealthBadge popover ──────────────────────────────

describe('TestFromAC_HealthBadgePopoverRepair', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockHook()
  })

  // Happy path: corruptionCount > 0 → repair button appears in popover

  it('popover contains repair-button when corruptionCount is 1', () => {
    const { container } = renderBadge([ITEM_A], { corruptionCount: 1 })
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')
    expect(popover?.querySelector('[data-testid="repair-button"]')).not.toBeNull()
  })

  it('popover contains repair-button when corruptionCount is large (10)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B], { corruptionCount: 10 })
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')
    expect(popover?.querySelector('[data-testid="repair-button"]')).not.toBeNull()
  })

  // Edge: corruptionCount boundary — 1 is the minimum that shows the panel

  it('popover contains repair-button when corruptionCount is exactly 1 (boundary minimum)', () => {
    const { container } = renderBadge([ITEM_B], { corruptionCount: 1 })
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')
    expect(popover?.querySelector('[data-testid="repair-button"]')).not.toBeNull()
  })

  // Structural: RepairPanel must appear BELOW the issue list

  it('repair-button appears after the issue list (ul) in the popover DOM order', () => {
    const { container } = renderBadge([ITEM_A], { corruptionCount: 1 })
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    const ul = popover.querySelector('ul')
    const repairBtn = popover.querySelector('[data-testid="repair-button"]')
    expect(ul).not.toBeNull()
    expect(repairBtn).not.toBeNull()
    // DOCUMENT_POSITION_FOLLOWING (4) means repairBtn comes after ul in document order
    const position = ul!.compareDocumentPosition(repairBtn!)
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  // Negative boundary: corruptionCount 0 must not render the repair panel inside the popover

  it('repair panel is absent from popover when corruptionCount is 0', () => {
    const { container } = renderBadge([ITEM_A], { corruptionCount: 0 })
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')
    expect(popover?.querySelector('[data-testid="repair-button"]')).toBeNull()
  })

})

// ─── AC7: useScanPolling refetch interface ─────────────────────────────────────

describe('TestFromAC_UseScanPollingRefetch', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  // Happy path: hook exposes refetch

  it('useScanPolling result includes a refetch property', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) }),
      ),
    )
    const { result } = renderHook(() => useScanPolling())
    await act(async () => {})
    expect('refetch' in result.current).toBe(true)
  })

  it('useScanPolling refetch is a callable function', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) }),
      ),
    )
    const { result } = renderHook(() => useScanPolling())
    await act(async () => {})
    expect(typeof result.current.refetch).toBe('function')
  })

  // Edge: calling refetch triggers an immediate re-poll (fetch is called again)

  it('calling refetch triggers a new fetch request', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useScanPolling())
    await act(async () => {})
    const callsAfterMount = fetchMock.mock.calls.length
    // Call refetch and wait for the new fetch to complete
    await act(async () => {
      result.current.refetch()
    })
    expect(fetchMock.mock.calls.length).toBeGreaterThan(callsAfterMount)
  })
})

// ─── AC7: RepairPanel onSuccess prop forwarded to useRepairFlow ────────────────

describe('TestFromAC_RepairPanelOnSuccess', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockHook()
  })

  // Happy path: RepairPanel passes onSuccess to useRepairFlow

  it('RepairPanel forwards onSuccess prop to useRepairFlow as options.onSuccess', () => {
    const onSuccess = vi.fn()
    renderPanel(3, { onSuccess })
    expect(vi.mocked(useRepairFlow)).toHaveBeenCalledWith(
      expect.objectContaining({ onSuccess }),
    )
  })

  // Boundary: distinct onSuccess references are threaded correctly

  it('RepairPanel threads the exact onSuccess reference to useRepairFlow', () => {
    const onSuccessA = vi.fn()
    renderPanel(1, { onSuccess: onSuccessA })
    const callArg = vi.mocked(useRepairFlow).mock.calls[0]?.[0] as
      | { onSuccess?: () => void }
      | undefined
    expect(callArg?.onSuccess).toBe(onSuccessA)
  })
})

// ─── AC8: RepairPanel PDS component smoke tests ───────────────────────────────

describe('TestFromAC_RepairPanelPDS', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockHook()
  })

  // Smoke: idle state uses p-button for the Repair trigger

  it('RepairPanel idle state renders p-button custom element (not plain button)', () => {
    const { container } = renderPanel(1)
    // PDS PButton renders as <p-button> custom element in the DOM.
    // Current implementation uses plain <button> — this test fails until PDS conversion.
    expect(container.querySelector('p-button')).not.toBeNull()
  })

  // Smoke: loading state uses p-spinner

  it('RepairPanel loading state renders p-spinner custom element (not plain div)', () => {
    mockHook({ phase: 'repairing' })
    const { container } = renderPanel(3)
    // PDS PSpinner renders as <p-spinner>. Current impl uses <div data-testid="repair-loading">.
    expect(container.querySelector('p-spinner')).not.toBeNull()
  })

  // Smoke: confirming state uses p-text for the dialog message

  it('RepairPanel confirming state renders p-text custom element', () => {
    mockHook({ phase: 'confirming', corruptionCount: 2 })
    const { container } = renderPanel(2)
    // PDS PText renders as <p-text>. Proves AC8 p-text coverage explicitly.
    expect(container.querySelector('p-text')).not.toBeNull()
  })
})

// ─── AC7 (integration): HealthBadge → RepairPanel → useRepairFlow callback chain ──

describe('TestFromAC_HealthBadgeRepairPropChain', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  // Happy path: HealthBadge threads onRepairSuccess all the way into useRepairFlow opts

  it('HealthBadge threads onRepairSuccess into useRepairFlow opts.onSuccess via RepairPanel', () => {
    let capturedOnSuccess: (() => void) | undefined
    vi.mocked(useRepairFlow).mockImplementation((opts: { onSuccess?: () => void } | undefined) => {
      capturedOnSuccess = opts?.onSuccess
      return hookDefaults()
    })

    const onRepairSuccessSpy = vi.fn()
    const { container } = renderBadge([ITEM_A], {
      corruptionCount: 1,
      onRepairSuccess: onRepairSuccessSpy,
    })
    // Open popover — triggers RepairPanel render, which calls useRepairFlow
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)

    expect(capturedOnSuccess).toBeDefined()
    expect(capturedOnSuccess).toBe(onRepairSuccessSpy)
  })

  // Integration: calling the captured onSuccess propagates back to the original handler

  it('invoking useRepairFlow opts.onSuccess calls the HealthBadge onRepairSuccess handler', () => {
    let capturedOnSuccess: (() => void) | undefined
    vi.mocked(useRepairFlow).mockImplementation((opts: { onSuccess?: () => void } | undefined) => {
      capturedOnSuccess = opts?.onSuccess
      return hookDefaults()
    })

    const onRepairSuccessSpy = vi.fn()
    const { container } = renderBadge([ITEM_A], {
      corruptionCount: 1,
      onRepairSuccess: onRepairSuccessSpy,
    })
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)

    expect(capturedOnSuccess).toBeDefined()
    capturedOnSuccess!()
    expect(onRepairSuccessSpy).toHaveBeenCalledOnce()
  })
})

// ─── AC2 (exact copy): confirmation dialog verbatim sentence ──────────────────

describe('TestFromAC_RepairConfirmCopyExact', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  // Contract: the exact sentence is required per AC2 — count-only assertions are insufficient

  it('confirmation dialog contains the verbatim sentence with count interpolated', () => {
    mockHook({ phase: 'confirming', corruptionCount: 3 })
    const { container } = renderPanel(3)
    const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
    const text = (dialog?.textContent ?? '').replace(/\s+/g, ' ').trim()
    expect(text).toContain(
      'This will attempt to repair 3 corrupted files. ' +
        'Fixed files are restored, quarantined files are moved to the quarantine directory (.owlbear/scratch/quarantine), and failed files remain corrupted. This action can be irreversible and cannot be undone.',
    )
  })

  it('verbatim sentence interpolates the count correctly for a different value', () => {
    mockHook({ phase: 'confirming', corruptionCount: 42 })
    const { container } = renderPanel(42)
    const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
    const text = (dialog?.textContent ?? '').replace(/\s+/g, ' ').trim()
    expect(text).toContain(
      'This will attempt to repair 42 corrupted files. ' +
        'Fixed files are restored, quarantined files are moved to the quarantine directory (.owlbear/scratch/quarantine), and failed files remain corrupted. This action can be irreversible and cannot be undone.',
    )
  })
})
