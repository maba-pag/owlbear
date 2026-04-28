import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'
import HistorySubtab, { type Session } from './HistorySubtab'
import ConfirmDialog from './ConfirmDialog'

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
  onSelectTask?: (taskId: number, subtab?: string) => void
}

export default function DetailTab({ task, onSelectTask }: DetailTabProps) {
  const [editBody, setEditBody] = useState(false)
  const [showConflict, setShowConflict] = useState(false)
  const [confirmType, setConfirmType] = useState<null | 'move-backward' | 'unblock' | 'unclaim'>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [sessions, setSessions] = useState<Session[]>([])
  const [title, setTitle] = useState(task?.title ?? '')
  const [priority, setPriority] = useState(task?.priority ?? '')
  const [body, setBody] = useState(task?.body ?? '')

  if (!task) return null

  const t = task

  async function handleSave() {
    const res = await fetch(`/api/tasks/${t.id}/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updated: t.updated, title, priority, body }),
    })
    if (res.status === 409) {
      setShowConflict(true)
    }
  }

  async function handleForceSave() {
    setShowConflict(false)
    await fetch(`/api/tasks/${t.id}/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updated: t.updated, title, priority, body }),
    })
  }

  async function handleHistoryClick() {
    setShowHistory(true)
    const res = await fetch('/api/sessions?filter=all', { method: 'GET' })
    if (res.ok) {
      const data = (await res.json()) as { sessions: Session[] }
      setSessions(data.sessions)
    }
  }

  const taskSessions = sessions.filter((s) => s.task_id === t.id)

  return (
    <div>
      {/* History tab button — always visible */}
      <button data-testid="history-tab" onClick={() => void handleHistoryClick()}>
        History
      </button>

      {/* Read-only fields */}
      <span data-testid="field-id">{t.id}</span>
      <span data-testid="field-status">{t.status}</span>
      <span data-testid="field-created">{t.created}</span>

      {/* Editable fields */}
      <input
        data-field="title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <select
        data-field="priority"
        value={priority}
        onChange={(e) => setPriority(e.target.value)}
      >
        <option value="someday">someday</option>
        <option value="nice-to-have">nice-to-have</option>
        <option value="important">important</option>
        <option value="needed">needed</option>
        <option value="critical">critical</option>
      </select>
      {t.tags.map((tag) => (
        <span key={tag} data-testid="tag-chip">
          {tag}
        </span>
      ))}
      <input data-field="depends_on" defaultValue={t.depends_on.join(', ')} />
      <input
        data-field="parent"
        defaultValue={t.parent !== null ? String(t.parent) : ''}
      />
      {t.blocked && (
        <input data-field="block_reason" defaultValue={t.block_reason ?? ''} />
      )}

      {/* Body — markdown view or edit textarea */}
      {editBody ? (
        <textarea data-field="body" value={body} onChange={(e) => setBody(e.target.value)} />
      ) : (
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{t.body}</ReactMarkdown>
      )}
      <button data-testid="body-edit-toggle" onClick={() => setEditBody((v) => !v)}>
        Edit
      </button>

      {/* Actions */}
      <button data-testid="save-button" onClick={() => void handleSave()}>
        Save
      </button>
      <button data-testid="move-backward" onClick={() => setConfirmType('move-backward')}>
        Move Backward
      </button>
      <button data-testid="unclaim-action" onClick={() => setConfirmType('unclaim')}>
        Unclaim
      </button>
      {t.blocked && (
        <button data-testid="unblock-action" onClick={() => setConfirmType('unblock')}>
          Unblock
        </button>
      )}

      {/* History subtab */}
      {showHistory && <HistorySubtab sessions={taskSessions} onSelectTask={onSelectTask} />}

      {/* Conflict modal */}
      {showConflict && (
        <div data-testid="conflict-modal">
          <button
            data-testid="conflict-refresh"
            onClick={() => setShowConflict(false)}
          >
            Discard changes
          </button>
          <button data-testid="conflict-overwrite" onClick={() => void handleForceSave()}>Force save</button>
        </div>
      )}

      {/* Confirm dialog */}
      {confirmType !== null && (
        <ConfirmDialog
          type={confirmType}
          blockReason={t.block_reason}
          onCancel={() => setConfirmType(null)}
          onConfirm={() => setConfirmType(null)}
        />
      )}
    </div>
  )
}
