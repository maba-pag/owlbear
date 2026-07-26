import { lazy, type ComponentType, type LazyExoticComponent } from 'react'

const SpecificationPage = lazy(() => import('./pages/SpecificationPage'))
const DeliveryPage = lazy(() => import('./pages/DeliveryPage'))
const RequestsPage = lazy(() => import('./pages/RequestsPage'))
const ActivityPage = lazy(() => import('./pages/ActivityPage'))
const EvidencePage = lazy(() => import('./pages/EvidencePage'))
const LegacyPage = lazy(() => import('./pages/LegacyPage'))
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
    path: '/',
    label: 'Specification',
    icon: 'specification',
    component: SpecificationPage,
  },
  {
    path: '/delivery',
    label: 'Delivery',
    icon: 'delivery',
    component: DeliveryPage,
  },
  {
    path: '/requests',
    label: 'Requests',
    icon: 'requests',
    component: RequestsPage,
  },
  {
    path: '/activity',
    label: 'Activity',
    icon: 'activity',
    component: ActivityPage,
  },
  {
    path: '/evidence',
    label: 'Evidence',
    icon: 'evidence',
    component: EvidencePage,
  },
  {
    path: '/legacy',
    label: 'Legacy',
    icon: 'legacy',
    component: LegacyPage,
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
