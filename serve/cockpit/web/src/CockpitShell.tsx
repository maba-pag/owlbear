import { Suspense, useState } from 'react'
import { PButtonPure, PFlyout, PLinkPure } from '@porsche-design-system/components-react'
import { useLocation, useNavigate } from 'react-router'
import { routeConfig } from './routes'
import ThemeToggle from './components/ThemeToggle'

const ICONS = {
  work: 'grid',
  memory: 'brain',
  ideas: 'user-manual',
} as const

interface ProductNavigationProps {
  activePath: string
  compact?: boolean
  onNavigate: (path: string) => void
}

function ProductNavigation({ activePath, compact = false, onNavigate }: ProductNavigationProps) {
  return (
    <nav aria-label="Product areas" className={compact ? 'grid justify-items-center gap-static-md' : 'grid gap-static-lg'}>
      {routeConfig.map((route) => (
        <PLinkPure
          key={route.path}
          href={route.path}
          icon={ICONS[route.icon as keyof typeof ICONS] ?? 'grid'}
          active={route.path === activePath}
          hideLabel={compact}
          stretch={!compact}
          size="medium"
          title={compact ? route.label : undefined}
          aria={{ 'aria-current': route.path === activePath ? 'page' : undefined, 'aria-label': route.label }}
          className={compact ? 'flex min-h-11 min-w-11 items-center justify-center' : 'min-h-11'}
          onClick={(event) => {
            event.preventDefault()
            onNavigate(route.path)
          }}
        >
          {route.label}
        </PLinkPure>
      ))}
    </nav>
  )
}

export default function CockpitShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false)
  const activeRoute = routeConfig.find((route) => route.path === location.pathname) ?? routeConfig[0]
  const ActivePage = activeRoute.component

  const goTo = (path: string) => {
    setMobileNavigationOpen(false)
    navigate(path)
  }

  return (
    <div className="grid min-h-dvh min-w-0 grid-cols-1 overflow-x-hidden bg-canvas text-primary lg:grid-cols-[5.75rem_minmax(0,1fr)]" data-testid="cockpit-shell">
      <aside className="sticky top-0 hidden h-dvh flex-col items-center border-r border-contrast-low bg-surface px-static-sm py-static-md lg:flex" data-region="nav-rail" data-testid="desktop-product-navigation">
        <div className="text-center">
          <strong className="block text-sm">OwlBear</strong>
          <span className="text-xs text-contrast-medium">Cockpit</span>
        </div>
        <div className="mt-static-xl flex-1">
          <ProductNavigation activePath={activeRoute.path} compact onNavigate={goTo} />
        </div>
        <ThemeToggle compact />
      </aside>

      <div className="min-h-0 min-w-0" data-region="workspace">
        <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between gap-static-md border-b border-contrast-low bg-canvas/95 px-static-md backdrop-blur-md lg:hidden">
          <div className="min-w-0">
            <strong className="block text-sm">OwlBear</strong>
            <span className="block text-xs text-contrast-medium">Cockpit</span>
          </div>
          <div className="flex items-center gap-static-md">
            <ThemeToggle compact />
            <PButtonPure
              type="button"
              icon="menu-lines"
              hideLabel
              aria={{ 'aria-label': 'Open navigation', 'aria-expanded': mobileNavigationOpen }}
              onClick={() => setMobileNavigationOpen(true)}
            >
              Open navigation
            </PButtonPure>
          </div>
        </header>

        <PFlyout
          open={mobileNavigationOpen}
          position="start"
          fullscreen
          aria={{ 'aria-label': 'Product areas' }}
          onDismiss={() => setMobileNavigationOpen(false)}
        >
          <div className="grid gap-static-xl p-static-lg">
            <div>
              <strong className="block text-lg">OwlBear</strong>
              <span className="text-sm text-contrast-medium">Cockpit</span>
            </div>
            <ProductNavigation activePath={activeRoute.path} onNavigate={goTo} />
          </div>
        </PFlyout>

        <Suspense fallback={<p className="p-static-lg" role="status">Preparing workspace...</p>}>
          <ActivePage />
        </Suspense>
      </div>
    </div>
  )
}
