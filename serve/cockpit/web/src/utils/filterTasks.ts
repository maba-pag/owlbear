import type { Task } from '../hooks/useBoard'

export interface FilterState {
  text: string
  priority: string
  tags: string[]
  blocked: boolean
}

export function filterTasks(tasks: Task[], filter: FilterState): Task[] {
  const text = filter.text.toLowerCase()

  return tasks.filter((task) => {
    const matchesText = !text || task.title.toLowerCase().includes(text)
    const matchesPriority = !filter.priority || task.priority === filter.priority
    const matchesTags =
      filter.tags.length === 0 || filter.tags.every((tag) => task.tags?.includes(tag) === true)
    const matchesBlocked = !filter.blocked || task.blocked

    return matchesText && matchesPriority && matchesTags && matchesBlocked
  })
}
