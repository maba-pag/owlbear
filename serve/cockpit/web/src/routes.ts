import { lazy, type ComponentType, type LazyExoticComponent } from 'react'
import type { KanbanBoardProps } from './KanbanBoard'

const SpecificationPage = lazy(() => import('./pages/SpecificationPage'))
const DeliveryPage = lazy(() => import('./pages/DeliveryPage'))
const IdeasPage = lazy(() => import('./pages/IdeasPage'))
const MemoryTab = lazy(() => import('./pages/MemoryTab'))

type WorkspaceComponent = ComponentType<Record<string, never>>

export interface RouteConfigEntry {
  path: string
  label: string
  icon: string
  kind?: 'board' | 'workspace'
  component:
    | ComponentType<KanbanBoardProps>
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
