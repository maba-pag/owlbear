import { lazy, type ComponentType } from 'react'
import KanbanBoard, { type KanbanBoardProps } from './KanbanBoard'

const DecisionsPage = lazy(() => import('./pages/DecisionsPage'))

export interface RouteConfigEntry {
  path: string
  label: string
  icon: string
  component: ComponentType<KanbanBoardProps>
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
]
