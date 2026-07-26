import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import LegacyPage from '../pages/LegacyPage'

vi.mock('../hooks/useNativeResources', () => ({
  useLegacyInventory: () => ({
    data: {
      tasks: [{ provenance: 'archive', task: { id: 42, title: 'Archived task' } }],
      requests: [{ provenance: 'decisions/resolved', request: { request_id: 'request-1' } }],
      activity: [{ provenance: 'activity.jsonl', event: { event_id: 'event-1' } }],
      truncated: { tasks: true, requests: false, activity: true },
    },
    error: null, isLoading: false, retry: vi.fn(),
  }),
}))

describe('LegacyPage', () => {
  it('renders source provenance and explicit truncation without mutation affordances', () => {
    const { container } = render(<LegacyPage />)
    expect(screen.getByText('archive')).toBeInTheDocument()
    expect(screen.getByText('decisions/resolved')).toBeInTheDocument()
    expect(screen.getByText('activity.jsonl')).toBeInTheDocument()
    expect(screen.getByText('Truncated to the first 100 records')).toBeInTheDocument()
    expect(screen.getByText('Truncated to the latest 100 records')).toBeInTheDocument()
    expect(container.querySelectorAll('button')).toHaveLength(0)
    expect(container.querySelectorAll('p-button')).toHaveLength(0)
  })
})
