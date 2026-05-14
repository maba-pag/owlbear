import { useTheme } from '../hooks/useTheme'

const THEME_LABELS = {
  light: {
    ariaLabel: 'Theme mode: light',
    text: 'Theme: Light',
  },
  dark: {
    ariaLabel: 'Theme mode: dark',
    text: 'Theme: Dark',
  },
  auto: {
    ariaLabel: 'Theme mode: auto',
    text: 'Theme: Auto',
  },
} as const

export default function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const label = THEME_LABELS[theme]

  return (
    <button
      type="button"
      data-testid="theme-toggle"
      aria-label={label.ariaLabel}
      onClick={toggle}
    >
      {label.text}
    </button>
  )
}