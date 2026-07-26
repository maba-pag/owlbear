import { Suspense, useEffect, useMemo } from 'react'
import { PHeading, PIcon, PLink } from '@porsche-design-system/components-react'
import { useLocation, useNavigate } from 'react-router'
import { routeConfig } from './routes'
import ThemeToggle from './components/ThemeToggle'
import { useNativeChangeSelection } from './hooks/NativeChangeProvider'
import { OPEN_TASK_DETAIL_EVENT, readOpenTaskDetailEvent } from './utils/openTaskDetail'

const ICONS = {
  specification: 'document',
  delivery: 'route',
  memory: 'brain',
  ideas: 'user-manual',
} as const

export default function NativeShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const { selectedChangeId } = useNativeChangeSelection()
  const activeRoute = routeConfig.find((route) => route.path === location.pathname) ?? routeConfig[0]
  const ActivePage = activeRoute.component
  const search = selectedChangeId ? `?change=${encodeURIComponent(selectedChangeId)}` : location.search
  const navItems = useMemo(
    () => routeConfig.map((route) => ({ ...route, active: route.path === activeRoute.path })),
    [activeRoute.path],
  )

  useEffect(() => {
    const openDeliveryJob = (event: Event) => {
      const jobId = readOpenTaskDetailEvent(event)
      if (jobId === null) {
        return
      }
      const params = new URLSearchParams()
      if (selectedChangeId) {
        params.set('change', selectedChangeId)
      }
      params.set('job', String(jobId))
      navigate(`/delivery?${params.toString()}`)
    }
    window.addEventListener(OPEN_TASK_DETAIL_EVENT, openDeliveryJob)
    return () => window.removeEventListener(OPEN_TASK_DETAIL_EVENT, openDeliveryJob)
  }, [navigate, selectedChangeId])

  return (
    <div className="flex min-h-dvh min-w-0 flex-col overflow-x-hidden bg-canvas text-primary" data-testid="native-shell">
      <header className="sticky top-0 z-20 border-b border-contrast-low bg-canvas/95 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between gap-static-md px-static-md py-static-sm md:px-static-xl">
          <div className="min-w-0">
            <PHeading tag="h1" size="md">OwlBear</PHeading>
            <span className="block truncate text-xs text-contrast-medium">{selectedChangeId ?? 'Cockpit'}</span>
          </div>
          <ThemeToggle compact />
        </div>
        <nav aria-label="Product phases" className="mx-auto grid w-full max-w-[1440px] grid-cols-4 gap-1 overflow-hidden px-static-xs sm:gap-static-xs sm:px-static-md md:px-static-xl">
          {navItems.map((route) => (
            <PLink
              key={route.path}
              href={`${route.path}${search}`}
              aria-current={route.active ? 'page' : undefined}
              className={[
                'inline-flex min-h-11 min-w-0 items-center justify-center gap-static-xs border-b-2 px-1 py-static-xs text-xs font-semibold sm:px-static-sm sm:text-sm',
                route.active ? 'border-primary text-primary' : 'border-transparent text-contrast-medium',
              ].join(' ')}
              onClick={(event) => {
                event.preventDefault()
                navigate(`${route.path}${search}`)
              }}
            >
              <span className="hidden sm:inline-flex"><PIcon name={ICONS[route.icon as keyof typeof ICONS] ?? 'grid'} size="sm" aria-hidden="true" /></span>
              <span className="min-w-0 truncate">{route.label}</span>
            </PLink>
          ))}
        </nav>
      </header>

      <div className="min-h-0 min-w-0 flex-1">
        <Suspense fallback={<p className="p-static-lg" role="status">Preparing workspace...</p>}>
          <ActivePage />
        </Suspense>
      </div>
    </div>
  )
}
