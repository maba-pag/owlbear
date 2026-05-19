import type { ComponentType } from 'react'
import KanbanBoard, { type KanbanBoardProps } from './KanbanBoard'
import DecisionsPage from './pages/DecisionsPage'

export interface RouteConfigEntry {
  path: string
  label: string
  icon: string
  component: ComponentType<KanbanBoardProps>
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
]