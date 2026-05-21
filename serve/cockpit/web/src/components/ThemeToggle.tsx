import { PButtonPure } from '@porsche-design-system/components-react'
import { useTheme } from '../hooks/useTheme'

const THEME_LABELS = {
  light: {
    ariaLabel: 'Theme mode: light',
    text: 'Light',
  },
  dark: {
    ariaLabel: 'Theme mode: dark',
    text: 'Dark',
  },
  auto: {
    ariaLabel: 'Theme mode: auto (OS)',
    text: 'Auto',
  },
} as const

interface ThemeToggleProps {
  compact?: boolean
}

export default function ThemeToggle({ compact = false }: ThemeToggleProps) {
  const { theme, toggle } = useTheme()
  const label = THEME_LABELS[theme]

  return (
    <PButtonPure
      type="button"
      icon="theme"
      hideLabel={compact}
      className="rounded-full bg-canvas px-static-xs py-1"
      data-testid="theme-toggle"
      aria-label={label.ariaLabel}
      onClick={toggle}
    >
      {label.text}
    </PButtonPure>
  )
}
