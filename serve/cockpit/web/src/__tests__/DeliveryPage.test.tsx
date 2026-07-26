import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import DeliveryPage from '../pages/DeliveryPage'

vi.mock('../hooks/NativeChangeProvider', () => ({
  useNativeChangeSelection: vi.fn(() => ({
    selectedChangeId: 'change-invalid',
    selectedSummary: { change_id: 'change-invalid', state: 'invalid' },
  })),
}))

describe('DeliveryPage', () => {
  it('shows invalid authority with icon plus text and selected job identity', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/delivery?change=change-invalid&job=42']}>
        <DeliveryPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Invalid authority prevents delivery.')).toBeInTheDocument()
    expect(screen.getByText('Selected job #42')).toBeInTheDocument()
    expect(container.querySelector('[role="status"] p-icon')).not.toBeNull()
  })
})
