import { useEffect, useState } from 'react'
import {
  PButton,
  PInputText,
  PSelect,
  PTextarea,
} from '@porsche-design-system/components-react'
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

  useEffect(() => {
    setTitle(task?.title ?? '')
    setPriority(task?.priority ?? '')
    setBody(task?.body ?? '')
  }, [task?.id])

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

  function setHideLabelAttr(element: HTMLElement | null): void {
    element?.setAttribute('hide-label', '')
  }

  function readControlValue(
    event: {
      target?: { value?: unknown }
      detail?: { value?: unknown }
    },
  ): string {
    if (typeof event.detail?.value === 'string') {
      return event.detail.value
    }

    if (typeof event.target?.value === 'string') {
      return event.target.value
    }

    return ''
  }

  return (
    <div>
      {/* History tab button — always visible */}
      <PButton data-testid="history-tab" variant="tertiary" onClick={() => void handleHistoryClick()}>
        History
      </PButton>

      {/* Read-only fields */}
      <span data-testid="field-id">{t.id}</span>
      <span data-testid="field-status">{t.status}</span>
      <span data-testid="field-created">{t.created}</span>

      {/* Editable fields */}
      <PInputText
        ref={setHideLabelAttr}
        data-field="title"
        hideLabel={true}
        value={title}
        onChange={(event) => setTitle(readControlValue(event))}
        onInput={(event) => setTitle(readControlValue(event))}
      />
      <PSelect
        ref={setHideLabelAttr}
        data-field="priority"
        hideLabel={true}
        value={priority}
        onChange={(event) => setPriority(readControlValue(event))}
        onInput={(event) => setPriority(readControlValue(event))}
      >
        <option value="someday">someday</option>
        <option value="nice-to-have">nice-to-have</option>
        <option value="important">important</option>
        <option value="needed">needed</option>
        <option value="critical">critical</option>
      </PSelect>
      {t.tags.map((tag) => (
        <span key={tag} data-testid="tag-chip">
          {tag}
        </span>
      ))}
      <PInputText
        ref={setHideLabelAttr}
        data-field="depends_on"
        hideLabel={true}
        defaultValue={t.depends_on.join(', ')}
      />
      <PInputText
        ref={setHideLabelAttr}
        data-field="parent"
        hideLabel={true}
        defaultValue={t.parent !== null ? String(t.parent) : ''}
      />
      {t.blocked && (
        <PInputText
          ref={setHideLabelAttr}
          data-field="block_reason"
          hideLabel={true}
          defaultValue={t.block_reason ?? ''}
        />
      )}

      {/* Body — markdown view or edit textarea */}
      {editBody ? (
        <PTextarea
          ref={setHideLabelAttr}
          data-field="body"
          hideLabel={true}
          value={body}
          onChange={(event) => setBody(readControlValue(event))}
          onInput={(event) => setBody(readControlValue(event))}
        />
      ) : (
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{t.body}</ReactMarkdown>
      )}
      <PButton data-testid="body-edit-toggle" variant="tertiary" onClick={() => setEditBody((v) => !v)}>
        Edit
      </PButton>

      {/* Actions */}
      <PButton data-testid="save-button" onClick={() => void handleSave()}>
        Save
      </PButton>
      <PButton data-testid="move-backward" variant="tertiary" onClick={() => setConfirmType('move-backward')}>
        Move Backward
      </PButton>
      <PButton data-testid="unclaim-action" variant="tertiary" onClick={() => setConfirmType('unclaim')}>
        Unclaim
      </PButton>
      {t.blocked && (
        <PButton data-testid="unblock-action" variant="tertiary" onClick={() => setConfirmType('unblock')}>
          Unblock
        </PButton>
      )}

      {/* History subtab */}
      {showHistory && <HistorySubtab sessions={taskSessions} onSelectTask={onSelectTask} />}

      {/* Conflict modal */}
      {showConflict && (
        <div data-testid="conflict-modal">
          <PButton
            data-testid="conflict-refresh"
            variant="tertiary"
            onClick={() => setShowConflict(false)}
          >
            Discard changes
          </PButton>
          <PButton data-testid="conflict-overwrite" onClick={() => void handleForceSave()}>Force save</PButton>
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
