import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ThemeToggle from '../components/ThemeToggle'
import { useTheme } from '../hooks/useTheme'

vi.mock('../hooks/useTheme', () => ({
  useTheme: vi.fn(),
}))

type ThemeMode = 'light' | 'dark' | 'auto'

const mockedUseTheme = vi.mocked(useTheme)

function renderThemeToggle(theme: ThemeMode = 'light', toggle = vi.fn(), selectTheme = vi.fn()) {
  mockedUseTheme.mockReturnValue({
    theme,
    toggle,
    selectTheme,
    isDark: theme === 'dark',
  })

  const view = render(
    <PorscheDesignSystemProvider>
      <ThemeToggle />
    </PorscheDesignSystemProvider>,
  )

  return { ...view, toggle, selectTheme }
}

function renderCompactThemeToggle(theme: ThemeMode = 'light', toggle = vi.fn(), selectTheme = vi.fn()) {
  mockedUseTheme.mockReturnValue({
    theme,
    toggle,
    selectTheme,
    isDark: theme === 'dark',
  })

  const view = render(
    <PorscheDesignSystemProvider>
      <ThemeToggle compact />
    </PorscheDesignSystemProvider>,
  )

  return { ...view, toggle, selectTheme }
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

  it('compact mode renders an icon-only trigger instead of a letter badge', () => {
    const { container } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]')

    expect(button).toHaveAttribute('aria-label', 'Theme mode: auto (OS); open theme menu')
    expect(button).toHaveAttribute('title', 'Theme mode: auto (OS); open theme menu')
    expect(button).toHaveAttribute('aria-haspopup', 'menu')
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(container.querySelector('[data-testid="theme-mode-indicator"]')).toBeNull()
  })

  it('compact mode opens a mode menu and selects an explicit theme', () => {
    const { container, toggle, selectTheme } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]')!

    fireEvent.click(button)

    expect(toggle).not.toHaveBeenCalled()
    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByTestId('theme-mode-menu')).toHaveAttribute('role', 'menu')
    expect(screen.getByTestId('theme-mode-option-auto')).toHaveAttribute('aria-checked', 'true')

    fireEvent.click(screen.getByTestId('theme-mode-option-dark'))

    expect(selectTheme).toHaveBeenCalledWith('dark')
    expect(screen.queryByTestId('theme-mode-menu')).toBeNull()
  })
})
