import { useState } from 'react'
import { Card } from './Card'
import type { Task } from '../hooks/useBoard'
import './Column.css'

export interface ColumnProps {
  status: string
  tasks: Task[]
  priorities: string[]
  selectedId?: number | null
  onSelectTask?: (taskId: number) => void
  onContextMenu: (e: React.MouseEvent, task: Task) => void
  onDragStart: (status: string, taskId: number, updated: string) => void
  onDrop: (targetStatus: string) => void
  onDragEnd: () => void
  isValidDragTarget: boolean
}

export function Column({
  status,
  tasks,
  priorities,
  selectedId,
  onSelectTask,
  onContextMenu,
  onDragStart,
  onDrop,
  onDragEnd,
  isValidDragTarget,
}: ColumnProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  const sorted = [...tasks].sort((a, b) => priorities.indexOf(b.priority) - priorities.indexOf(a.priority))

  const handleCardDragStart = (taskId: number, updated: string) => {
    onDragStart(status, taskId, updated)
  }

  return (
    <div
      className="column"
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
        setIsDragOver(false)
        if (!isValidDragTarget) {
          return
        }
        e.preventDefault()
        onDrop(status)
      }}
    >
      <header>
        <span>{status}</span>
        <span data-testid="column-count">{tasks.length}</span>
      </header>
      <div className="column-body" data-testid="column-body">
        {sorted.length === 0 ? (
          <div className="column-empty" data-testid="empty-column">{`No ${status} tasks`}</div>
        ) : (
          sorted.map((task) => (
            <Card
              key={task.id}
              task={task}
              selected={selectedId === task.id}
              onSelect={onSelectTask}
              onContextMenu={onContextMenu}
              onDragStart={handleCardDragStart}
              onDragEnd={onDragEnd}
            />
          ))
        )}
      </div>
    </div>
  )
}

