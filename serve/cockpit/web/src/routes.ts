import { lazy, type ComponentType, type LazyExoticComponent } from 'react'
import KanbanBoard, { type KanbanBoardProps } from './KanbanBoard'

const decisionsPageModule = import('./pages/DecisionsPage')

const DecisionsPage = lazy(async () => decisionsPageModule)
const MemoryTab = lazy(() => import('./pages/MemoryTab'))

export interface RouteConfigEntry {
  path: string
  label: string
  icon: string
  component: ComponentType<KanbanBoardProps> | LazyExoticComponent<ComponentType<KanbanBoardProps>>
  hasSidecar?: boolean
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
    hasSidecar: false,
  },
  {
    path: '/memories',
    label: 'Memory',
    icon: 'memory',
    component: MemoryTab,
    hasSidecar: false,
  },
]
