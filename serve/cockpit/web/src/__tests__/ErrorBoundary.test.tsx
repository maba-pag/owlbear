import { fireEvent, render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from '../components/ErrorBoundary'

function renderErrorBoundary() {
  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  function ThrowError(): never {
    throw new Error('Test error')
  }
  const result = render(
    <PorscheDesignSystemProvider>
      <ErrorBoundary label="Cockpit">
        <ThrowError />
      </ErrorBoundary>
    </PorscheDesignSystemProvider>,
  )
  consoleSpy.mockRestore()
  return result
}

describe('ErrorBoundary', () => {
  afterEach(() => vi.restoreAllMocks())

  it('renders a PDS heading and retry control for page failures', () => {
    const { container } = renderErrorBoundary()
    expect(container.querySelector('p-heading[tag="h3"]')).toHaveTextContent('Something went wrong in Cockpit')
    expect(container.querySelector('p-button')).not.toBeNull()
    expect(container.querySelector('button')).toBeNull()
  })

  it('resets the boundary when Retry is activated', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    let shouldThrow = true
    function ConditionalThrow() {
      if (shouldThrow) throw new Error('Test error')
      return <div data-testid="recovered">Recovered</div>
    }
    const { container, getByTestId } = render(
      <PorscheDesignSystemProvider>
        <ErrorBoundary>
          <ConditionalThrow />
        </ErrorBoundary>
      </PorscheDesignSystemProvider>,
    )
    shouldThrow = false
    fireEvent.click(container.querySelector('p-button')!)
    expect(getByTestId('recovered')).toBeInTheDocument()
    consoleSpy.mockRestore()
  })
})
