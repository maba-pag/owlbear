import { lazy, type ComponentType, type LazyExoticComponent } from 'react'

const WorkPortfolioPage = lazy(() => import('./pages/WorkPortfolioPage'))
const IdeasPage = lazy(() => import('./pages/IdeasPage'))
const MemoryTab = lazy(() => import('./pages/MemoryTab'))

type WorkspaceComponent = ComponentType<Record<string, never>>

export interface RouteConfigEntry {
  path: string
  label: string
  icon: string
  kind?: 'board' | 'workspace'
  component:
    | WorkspaceComponent
    | LazyExoticComponent<WorkspaceComponent>
}

export const routeConfig: RouteConfigEntry[] = [
  {
    path: '/delivery',
    label: 'Delivery',
    icon: 'work',
    component: WorkPortfolioPage,
  },
  {
    path: '/memory',
    label: 'Memory',
    icon: 'memory',
    component: MemoryTab,
  },
  {
    path: '/ideas',
    label: 'Ideas',
    icon: 'ideas',
    component: IdeasPage,
  },
]

export function routeForPath(pathname: string): RouteConfigEntry | undefined {
  return routeConfig.find((route) => {
    if (route.path !== '/delivery') return pathname === route.path
    const segments = pathname.split('/').filter(Boolean)
    return segments[0] === 'delivery' && (segments.length === 1 || segments.length === 3)
  })
}

/** Superseded paths kept reachable so existing links and bookmarks still resolve. */
export const legacyRouteRedirects: Array<{ from: string; to: string }> = [
  { from: '/', to: '/delivery' },
  { from: '/work', to: '/delivery' },
  { from: '/memories', to: '/memory' },
]
