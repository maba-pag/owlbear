import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import DeliveryGraphOutline from '../components/DeliveryGraphOutline'
import type { NativeGraphDetail } from '../api/native'
import { createDeliveryGraphFixture as graphFixture } from '../../e2e/support/delivery-graph-fixture'

function renderOutline(detail: NativeGraphDetail, entry = '/?change=change') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <DeliveryGraphOutline detail={detail} />
    </MemoryRouter>,
  )
}

beforeAll(() => {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function mockRect() {
    const height = this.getAttribute('role') === 'listbox' ? 480 : 88
    return { x: 0, y: 0, width: 600, height, top: 0, right: 600, bottom: height, left: 0, toJSON: () => ({}) }
  })
})

describe('DeliveryGraphOutline', () => {
  it('exposes complete node authority and packet plan for the selected node', async () => {
    renderOutline(graphFixture(14), '/?change=change&node=DN-014')

    await waitFor(() => expect(screen.getByTestId('node-detail')).toHaveTextContent('DN-014'))
    expect(screen.getByTestId('node-detail')).toHaveTextContent('REQ-014')
    expect(screen.getByTestId('node-detail')).toHaveTextContent('IF-014')
    expect(screen.getByTestId('node-detail')).toHaveTextContent('MOD-014')
    expect(screen.getByTestId('node-detail')).toHaveTextContent('RISK-014')
    expect(screen.getByTestId('node-detail')).toHaveTextContent('PROOF-014')
    expect(screen.getByTestId('node-detail')).toHaveTextContent('DN-014-PK-001')
    expect(screen.getByTestId('node-detail')).toHaveTextContent('Authority: DN-014, PROOF-014')
  })

  it.each([
    [0, 'Requirement', 'REQ-014', 1],
    [1, 'Interface', 'IF-014', 1],
    [2, 'Migration', 'MIG-002', 7],
    [3, 'Proof', 'PROOF-014', 1],
  ])('filter %i matches %s authority', async (index, _label, value, expectedCount) => {
    const { container } = renderOutline(graphFixture(14))
    const input = container.querySelectorAll('p-input-text')[index] as HTMLElement
    fireEvent(input, new CustomEvent('change', { detail: { value } }))

    await waitFor(() => expect(screen.getByText(new RegExp(`${expectedCount} of 14 nodes`))).toBeInTheDocument())
  })

  it('deep-links to DN-275 in a 300-node fixture with fewer than 100 mounted rows', async () => {
    const { container } = renderOutline(graphFixture(300), '/?change=change&node=DN-275')

    await waitFor(() => expect(screen.getByTestId('node-detail')).toHaveTextContent('DN-275'))
    expect(container.querySelectorAll('[data-node-id]').length).toBeLessThan(100)
    expect(screen.getByText('300 of 300 nodes')).toBeInTheDocument()
  })

  it('moves filtered-out deep links to the first matching node and renders an empty state for zero matches', async () => {
    const { container } = renderOutline(graphFixture(300), '/?change=change&node=DN-275')
    const requirement = container.querySelectorAll('p-input-text')[0]
    fireEvent(requirement, new CustomEvent('change', { detail: { value: 'REQ-001' } }))

    await waitFor(() => expect(screen.getByTestId('node-detail')).toHaveTextContent('DN-001'))
    expect(screen.getByTestId('node-detail')).not.toHaveTextContent('DN-275')

    fireEvent(requirement, new CustomEvent('change', { detail: { value: 'NO-SUCH' } }))
    await waitFor(() => expect(screen.getByText('No matching nodes.')).toBeInTheDocument())
  })

  it('moves listbox selection with ArrowDown', async () => {
    renderOutline(graphFixture(14), '/?change=change&node=DN-001')
    const listbox = screen.getByRole('listbox', { name: 'Delivery nodes' })
    listbox.focus()
    fireEvent.keyDown(listbox, { key: 'ArrowDown' })

    await waitFor(() => expect(screen.getByTestId('node-detail')).toHaveTextContent('DN-002'))
    expect(listbox).toHaveAttribute('aria-activedescendant', 'delivery-node-DN-002')
  })
})
