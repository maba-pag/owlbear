import type { Task } from '../hooks/useBoard'

export interface FilterState {
  text: string
  priority: string
  tags: string[]
  blocked: boolean
}

// RED-phase stub for task #1248; real filtering logic is implemented in #1249.
export function filterTasks(_tasks: Task[], _filter: FilterState): Task[] {
  return []
}