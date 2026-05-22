import { lazy, type ComponentType, type LazyExoticComponent } from 'react'
import KanbanBoard, { type KanbanBoardProps } from './KanbanBoard'

const DecisionsPage = lazy(() => import('./pages/DecisionsPage'))
const IdeasPage = lazy(() => import('./pages/IdeasPage'))
const MemoryTab = lazy(() => import('./pages/MemoryTab'))

type WorkspaceComponent = ComponentType<Record<string, never>>

export interface RouteConfigEntry {
  path: string
  label: string
  icon: string
  component:
    | ComponentType<KanbanBoardProps>
    | WorkspaceComponent
    | LazyExoticComponent<WorkspaceComponent>
}

export const routeConfig: RouteConfigEntry[] = [
  {
    path: '/',
    label: 'Kanban',
    icon: 'kanban',
    component: KanbanBoard,
  },
  {
    path: '/decisions',
    label: 'Decisions',
    icon: 'decisions',
    component: DecisionsPage,
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
