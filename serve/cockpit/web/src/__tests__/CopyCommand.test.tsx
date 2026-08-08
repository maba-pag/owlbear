import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import CopyCommand from '../components/CopyCommand'

afterEach(() => {
  vi.restoreAllMocks()
})

function stubClipboard(writeText: (value: string) => Promise<void>) {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  })
}

it('copies the complete command and confirms success', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  stubClipboard(writeText)
  render(<CopyCommand command="/design website-to-knowledge-vertical" />)

  fireEvent.click(screen.getByRole('button', { name: 'Copy command /design website-to-knowledge-vertical' }))

  await waitFor(() => expect(writeText).toHaveBeenCalledWith('/design website-to-knowledge-vertical'))
  expect(screen.getByRole('status')).toHaveTextContent('Copied /design website-to-knowledge-vertical')
})

it('reports a clipboard failure without navigating', async () => {
  stubClipboard(vi.fn().mockRejectedValue(new Error('Clipboard denied')))
  render(<CopyCommand command="/orchestrate" />)

  fireEvent.click(screen.getByRole('button', { name: 'Copy command /orchestrate' }))

  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Could not copy /orchestrate'))
})
