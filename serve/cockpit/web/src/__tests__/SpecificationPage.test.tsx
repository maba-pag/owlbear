import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SpecificationPage from '../pages/SpecificationPage'

const selection = vi.hoisted(() => ({
  changes: [
    { change_id: 'change-a', state: 'loaded' as const, delivery_digest: 'a'.repeat(64), diagnostics: [] },
  ],
  selectedChangeId: 'change-a',
  missingChangeId: null,
  selectedSummary: { change_id: 'change-a', state: 'loaded' as const, delivery_digest: 'a'.repeat(64), diagnostics: [] },
  detail: {
    change_id: 'change-a',
    delivery_digest: 'a'.repeat(64),
    intent: 'Ship the native delivery system.',
    design: 'Compose exact authority with runtime evidence.',
    decisions: {
      decisions: [
        { id: 'DEC-001', status: 'accepted', title: 'Use native authority', rationale: 'One source of truth.' },
        { id: 'DEC-002', status: 'superseded', title: 'Use legacy tasks', rationale: 'Retired.' },
      ],
    },
    graph: {
      state: 'admitted',
      authority: { intent: 'intent.md', design: 'design.md', decisions: 'decisions.yaml', research: ['research.md'] },
      admission: { receipt: 'admission-001', limits: ['No generic mutations'] },
    },
  },
  isLoading: false,
  error: null as Error | null,
  selectChange: vi.fn(),
  retry: vi.fn(),
}) as {
  changes: Array<Record<string, unknown>>
  selectedChangeId: string
  selectedSummary: Record<string, unknown> | null
  missingChangeId: string | null
  detail: Record<string, unknown> | null
  isLoading: boolean
  error: Error | null
  selectChange: ReturnType<typeof vi.fn>
  retry: ReturnType<typeof vi.fn>
})

vi.mock('../hooks/NativeChangeProvider', () => ({
  useNativeChangeSelection: vi.fn(() => selection),
}))

describe('SpecificationPage', () => {
  afterEach(() => {
    selection.error = null
    vi.clearAllMocks()
  })

  it('renders digest, intent, design, accepted decisions, and keyboard sections', () => {
    render(<SpecificationPage />)

    expect(screen.getByText('Specification')).toBeInTheDocument()
    expect(screen.getByText('a'.repeat(64))).toBeInTheDocument()
    expect(screen.getByText('Ship the native delivery system.')).toBeInTheDocument()
    expect(screen.getByText('Compose exact authority with runtime evidence.')).toBeInTheDocument()
    expect(screen.getByText('Use native authority')).toBeInTheDocument()
    expect(screen.getByText('One source of truth.')).toBeInTheDocument()
    expect(screen.queryByText('Use legacy tasks')).not.toBeInTheDocument()
    expect(screen.getByText('admission-001')).toBeInTheDocument()
    expect(screen.getByText('research.md')).toBeInTheDocument()
    expect(screen.getByText('No generic mutations')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Product Intent' })).toHaveAttribute('tabindex', '0')
  })

  it('labels invalid authority with icon-adjacent text', () => {
    const previousSummary = selection.selectedSummary
    const previousDetail = selection.detail
    selection.selectedSummary = {
      change_id: 'change-b',
      state: 'invalid',
      delivery_digest: null,
      diagnostics: [{ code: 'ERR_CHANGE_INVALID', detail: 'Broken authority', target: null }],
    }
    selection.detail = null

    const { container } = render(<SpecificationPage />)

    expect(screen.getByText('Invalid authority')).toBeInTheDocument()
    expect(screen.getByText(/ERR_CHANGE_INVALID/)).toBeInTheDocument()
    expect(container.querySelector('[data-testid="invalid-change"] p-icon')).not.toBeNull()
    selection.selectedSummary = previousSummary
    selection.detail = previousDetail
  })

  it('retains authority while showing an actionable Retry error', () => {
    selection.error = new Error('network unavailable')
    render(<SpecificationPage />)

    expect(screen.getByText('Ship the native delivery system.')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Retry'))
    expect(selection.retry).toHaveBeenCalledOnce()
  })
})
