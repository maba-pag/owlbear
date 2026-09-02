import { Suspense, useState } from 'react'
import { PButtonPure, PFlyout, PHeading, PIcon, PLinkPure } from '@porsche-design-system/components-react'
import { useLocation, useNavigate } from 'react-router'
import { routeConfig, routeForPath } from './routes'
import ThemeToggle from './components/ThemeToggle'
import CopyCommand from './components/CopyCommand'
import WorkspaceStatus from './components/WorkspaceStatus'
import { useWorkspaceHealth } from './hooks/useWorkspaceHealth'

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
    <nav aria-label="Product areas" className={compact ? 'grid w-full justify-items-center gap-static-sm' : 'grid gap-static-lg'}>
      {routeConfig.map((route) => compact ? (
        <a
          key={route.path}
          href={route.path}
          title={route.label}
          aria-label={route.label}
          aria-current={route.path === activePath ? 'page' : undefined}
          className={[
            "relative grid h-10 w-10 place-items-center focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus before:absolute before:-left-2 before:top-2 before:h-6 before:w-0.5 before:content-['']",
            route.path === activePath
              ? 'bg-frosted-soft text-primary before:bg-primary'
              : 'text-contrast-medium before:bg-transparent hover:bg-canvas hover:text-primary',
          ].join(' ')}
          onClick={(event) => {
            event.preventDefault()
            onNavigate(route.path)
          }}
        >
          <PIcon name={ICONS[route.icon as keyof typeof ICONS] ?? 'grid'} aria-hidden="true" />
        </a>
      ) : (
        <PLinkPure
          key={route.path}
          href={route.path}
          icon={ICONS[route.icon as keyof typeof ICONS] ?? 'grid'}
          active={route.path === activePath}
          stretch
          size="medium"
          aria={{ 'aria-current': route.path === activePath ? 'page' : undefined, 'aria-label': route.label }}
          className="min-h-11"
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

function CommandReference() {
  return (
    <footer
      className="border-t border-contrast-low bg-surface px-static-md py-static-sm md:px-static-lg"
      aria-label="Command reference"
      data-testid="command-reference"
    >
      <div className="flex min-w-0 flex-wrap items-center gap-x-static-lg gap-y-static-xs text-xs">
        <strong className="shrink-0 text-primary">Commands</strong>
        <ul className="m-0 flex min-w-0 flex-wrap items-center gap-x-static-md gap-y-static-xs p-0">
          {['/ideate', '/design <change-id>', '/orchestrate', '/finalize-change <change-id>'].map((command) => (
            <li key={command} className="min-w-0">
              <CopyCommand command={command} />
            </li>
          ))}
        </ul>
        <span className="h-4 border-l border-contrast-low" aria-hidden="true" />
        <span className="shrink-0 text-contrast-medium">Recovery</span>
        <CopyCommand command="/resolve-delivery-attention <change-id> <attention-id>" />
      </div>
    </footer>
  )
}

export default function CockpitShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false)
  const workspaceHealth = useWorkspaceHealth()
  const activeRoute = routeForPath(location.pathname)
  const ActivePage = activeRoute?.component

  const goTo = (path: string) => {
    setMobileNavigationOpen(false)
    navigate(path)
  }

  return (
    <div className="grid h-dvh min-w-0 grid-cols-1 overflow-hidden bg-canvas text-primary md:grid-cols-[4rem_minmax(0,1fr)]" data-testid="cockpit-shell">
      <aside className="hidden h-dvh flex-col items-center border-r border-contrast-low bg-surface px-static-xs py-static-md md:flex" data-region="nav-rail" data-testid="desktop-product-navigation">
        {/* The rail is 64px wide, so identity is a stacked wordmark rather than a boxed monogram. */}
        <div
          className="grid w-full justify-items-center gap-px py-1 leading-none"
          data-testid="rail-identity"
          role="img"
          aria-label="OwlBear Cockpit"
          title="OwlBear Cockpit"
        >
          <span aria-hidden="true" className="text-[0.5625rem] font-semibold uppercase tracking-[0.14em] text-primary">OwlBear</span>
          <span aria-hidden="true" className="text-[0.5625rem] uppercase tracking-[0.14em] text-contrast-medium">Cockpit</span>
        </div>
        <div className="mt-static-lg flex w-full flex-1 items-start justify-center">
          <ProductNavigation activePath={activeRoute?.path ?? ''} compact onNavigate={goTo} />
        </div>
        <div className="grid justify-items-center gap-1.5">
          <WorkspaceStatus health={workspaceHealth} />
          <ThemeToggle compact />
        </div>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-col overflow-y-auto overflow-x-hidden" data-region="workspace">
        <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between gap-static-md border-b border-contrast-low bg-canvas/95 px-static-md backdrop-blur-md md:hidden">
          <div className="min-w-0">
            <strong className="block text-sm">OwlBear</strong>
            <span className="block text-xs text-contrast-medium">Cockpit</span>
          </div>
          <div className="flex items-center gap-static-md">
            <WorkspaceStatus health={workspaceHealth} />
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
            <ProductNavigation activePath={activeRoute?.path ?? ''} onNavigate={goTo} />
          </div>
        </PFlyout>

        {/* Auto row stretches a short page to full height and grows a long one so the workspace column scrolls. */}
        <div className="grid min-h-0 flex-1 grid-cols-1">
          <Suspense fallback={<p className="p-static-lg" role="status">Preparing workspace...</p>}>
            {ActivePage ? <ActivePage /> : (
              <main className="grid min-h-full place-items-center p-static-xl" data-testid="not-found-view">
                <section className="grid max-w-lg gap-static-sm text-center">
                  <PHeading tag="h1" size="xl">Page not found</PHeading>
                  <p className="text-sm text-contrast-medium">This Cockpit address does not match an available workspace.</p>
                  <PLinkPure href="/delivery" onClick={(event) => { event.preventDefault(); goTo('/delivery') }}>Go to Delivery portfolio</PLinkPure>
                </section>
              </main>
            )}
          </Suspense>
        </div>
        <CommandReference />
      </div>
    </div>
  )
}
