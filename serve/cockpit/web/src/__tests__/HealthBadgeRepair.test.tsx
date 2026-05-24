/**
 * RF-06 RepairPanel contract coverage after extraction from HealthBadge
 *
 * AC7 — useScanPolling exposes refetch(); RepairPanel accepts onSuccess prop directly
 * AC8 — RepairPanel uses PDS components throughout (p-button, p-spinner, p-text)
 *
 * AC1–AC5 and AC9 are covered by #1167 tests (RepairPanel_1167.test.tsx). This suite
 * covers remaining hook and RepairPanel contracts.
 *
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { renderHook, act } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { UseRepairFlowResult } from '../hooks/useRepairFlow'

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
import { useScanPolling } from '../hooks/useScanPolling'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

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

// ─── AC2 (exact copy): confirmation dialog verbatim sentence ──────────────────

describe('TestFromAC_RepairConfirmCopyExact', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  // Contract: the dialog must state the count and the backend-owned quarantine destination.

  it('confirmation dialog contains the verbatim sentence with count interpolated', () => {
    mockHook({ phase: 'confirming', corruptionCount: 3 })
    const { container } = renderPanel(3)
    const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
    const text = (dialog?.textContent ?? '').replace(/\s+/g, ' ').trim()
    expect(text).toContain('Repair 3 corrupted files?')
    expect(text).toContain(
      'Fixed files are restored, quarantined files move to the quarantine folder .owlbear/kanban/quarantine, and failed files remain corrupted. This action can be irreversible.',
    )
  })

  it('verbatim sentence interpolates the count correctly for a different value', () => {
    mockHook({ phase: 'confirming', corruptionCount: 42 })
    const { container } = renderPanel(42)
    const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
    const text = (dialog?.textContent ?? '').replace(/\s+/g, ' ').trim()
    expect(text).toContain('Repair 42 corrupted files?')
    expect(text).toContain(
      'Fixed files are restored, quarantined files move to the quarantine folder .owlbear/kanban/quarantine, and failed files remain corrupted. This action can be irreversible.',
    )
  })
})
