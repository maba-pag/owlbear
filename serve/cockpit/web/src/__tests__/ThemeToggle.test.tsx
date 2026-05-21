import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ThemeToggle from '../components/ThemeToggle'
import { useTheme } from '../hooks/useTheme'

vi.mock('../hooks/useTheme', () => ({
  useTheme: vi.fn(),
}))

type ThemeMode = 'light' | 'dark' | 'auto'

const mockedUseTheme = vi.mocked(useTheme)

function renderThemeToggle(theme: ThemeMode = 'light', toggle = vi.fn()) {
  mockedUseTheme.mockReturnValue({
    theme,
    toggle,
    isDark: theme === 'dark',
  })

  const view = render(
    <PorscheDesignSystemProvider>
      <ThemeToggle />
    </PorscheDesignSystemProvider>,
  )

  return { ...view, toggle }
}

function renderCompactThemeToggle(theme: ThemeMode = 'light', toggle = vi.fn()) {
  mockedUseTheme.mockReturnValue({
    theme,
    toggle,
    isDark: theme === 'dark',
  })

  const view = render(
    <PorscheDesignSystemProvider>
      <ThemeToggle compact />
    </PorscheDesignSystemProvider>,
  )

  return { ...view, toggle }
}

function getButtonDescriptor(theme: ThemeMode): string {
  const { container, unmount } = renderThemeToggle(theme)
  const button = container.querySelector('[data-testid="theme-toggle"]')
  const descriptor = `${button?.getAttribute('aria-label') ?? ''}|${button?.textContent ?? ''}`
  unmount()
  return descriptor
}

describe('TestFromAC_ThemeToggle_1540', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AC-1: renders an accessible PDS button-pure element', () => {
    const { container } = renderThemeToggle('light')

    const button = container.querySelector('[data-testid="theme-toggle"]')
    expect(button).toBeInTheDocument()
    expect(button!.tagName.toLowerCase()).toBe('p-button-pure')
    expect(button).toHaveAttribute('aria-label', 'Theme mode: light')
  })

  it('AC-2: clicking toggle button invokes useTheme().toggle exactly once', () => {
    const { container, toggle } = renderThemeToggle('light')

    fireEvent.click(container.querySelector('[data-testid="theme-toggle"]')!)

    expect(toggle).toHaveBeenCalledTimes(1)
  })

  it('AC-3: button accessible name or content differs across light, dark, and auto theme states', () => {
    const descriptors = [getButtonDescriptor('light'), getButtonDescriptor('dark'), getButtonDescriptor('auto')]

    expect(new Set(descriptors).size).toBe(3)
  })

  it('compact mode shows a one-character mode indicator instead of full persistent text', () => {
    const { container } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]')
    const indicator = container.querySelector('[data-testid="theme-mode-indicator"]')

    expect(button).toHaveAttribute('aria-label', 'Theme mode: auto (OS)')
    expect(button).toHaveAttribute('title', 'Theme mode: auto (OS)')
    expect(indicator?.textContent).toBe('A')
    expect(indicator?.getAttribute('aria-hidden')).toBe('true')
  })
})
