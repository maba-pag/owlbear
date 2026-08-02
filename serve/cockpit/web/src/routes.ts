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
    path: '/work',
    label: 'Work',
    icon: 'work',
    component: WorkPortfolioPage,
  },
  {
    path: '/memories',
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
