import { useState } from 'react'
import { Card } from './Card'
import type { Task } from '../hooks/useBoard'

export interface ColumnProps {
  status: string
  tasks: Task[]
  priorities: string[]
  onContextMenu: (e: React.MouseEvent, task: Task) => void
  onDragStart: (status: string) => void
  onDragEnd: () => void
  isValidDragTarget: boolean
}

export function Column({
  status,
  tasks,
  priorities,
  onContextMenu,
  onDragStart,
  onDragEnd,
  isValidDragTarget,
}: ColumnProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  const sorted = [...tasks].sort((a, b) => priorities.indexOf(b.priority) - priorities.indexOf(a.priority))

  const handleCardDragStart = () => {
    onDragStart(status)
  }

  return (
    <div
      data-column={status}
      data-drag-over={isDragOver && isValidDragTarget ? 'true' : undefined}
      onDragOver={(e) => {
        if (isValidDragTarget) {
          e.preventDefault()
          setIsDragOver(true)
        }
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setIsDragOver(false)
      }}
      style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 56px)' }}
    >
      <header>
        <span>{status}</span>
        <span data-testid="column-count">{tasks.length}</span>
      </header>
      {sorted.length === 0 ? (
        <div data-testid="empty-column">No tasks</div>
      ) : (
        sorted.map((task) => (
          <Card
            key={task.id}
            task={task}
            onContextMenu={onContextMenu}
            onDragStart={handleCardDragStart}
            onDragEnd={onDragEnd}
          />
        ))
      )}
    </div>
  )
}
