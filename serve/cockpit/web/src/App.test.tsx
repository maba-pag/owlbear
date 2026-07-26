import { render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('./hooks/NativeInvalidationProvider', () => ({
  NativeInvalidationProvider: ({ children }: { children: unknown }) => children,
}))
vi.mock('./hooks/NativeChangeProvider', () => ({
  NativeChangeProvider: ({ children }: { children: unknown }) => children,
  useNativeChangeSelection: () => ({ selectedChangeId: 'change-a' }),
}))
vi.mock('./NativeShell', () => ({
  default: () => <div data-testid="native-shell" data-no-sidecar="" />,
}))

describe('App native shell integration', () => {
  afterEach(() => vi.clearAllMocks())

  it('renders the native product shell', () => {
    const { getByTestId } = render(<App />)
    expect(getByTestId('native-shell')).toBeInTheDocument()
  })

  it('does not restore the retired task sidecar', () => {
    const { container } = render(<App />)
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
  })
})
