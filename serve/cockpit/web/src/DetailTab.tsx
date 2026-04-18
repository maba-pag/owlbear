// RED-phase stub — minimal shell so tests compile.
// Builder replaces this with the real implementation.

export interface TaskDetail {
  id: number
  title: string
  status: string
  priority: string
  body: string
  updated: string
  created: string
  tags: string[]
  blocked: boolean
  block_reason: string | null
  parent: number | null
  depends_on: number[]
}

export interface DetailTabProps {
  task: TaskDetail | null
  onTaskUpdated?: (task: TaskDetail) => void
}

export default function DetailTab(_props: DetailTabProps): null {
  return null
}
