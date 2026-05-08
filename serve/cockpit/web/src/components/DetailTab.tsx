import { useEffect, useMemo, useState } from 'react'
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
import type { Board } from '../hooks/useBoard'
import { getResponseErrorMessage } from '../api/errorMessage'

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
  claimed: boolean
  claimed_at: string | null
  dep_status: string | null
  parent: number | null
  depends_on: number[]
}

export interface DetailTabProps {
  task: TaskDetail | null
  board?: Board | null
  onTaskUpdated?: (task: TaskDetail) => void
  onSelectTask?: (taskId: number, subtab?: string) => void
  onTaskCleared?: () => void
  initialSubtab?: string | null
}

export default function DetailTab({
  task,
  board,
  onTaskUpdated,
  onSelectTask,
  onTaskCleared,
  initialSubtab,
}: DetailTabProps) {
  const [editBody, setEditBody] = useState(false)
  const [showConflict, setShowConflict] = useState(false)
  const [serverValidationMessage, setServerValidationMessage] = useState<string | null>(null)
  const [confirmType, setConfirmType] = useState<null | 'move-backward' | 'unblock' | 'unclaim'>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [sessions, setSessions] = useState<Session[]>([])
  const [title, setTitle] = useState(task?.title ?? '')
  const [priority, setPriority] = useState(task?.priority ?? '')
  const [body, setBody] = useState(task?.body ?? '')
  const [dependsOn, setDependsOn] = useState(task?.depends_on.join(', ') ?? '')
  const [parent, setParent] = useState(task?.parent !== null ? String(task?.parent) : '')
  const [blockReason, setBlockReason] = useState(task?.block_reason ?? '')

  useEffect(() => {
    setTitle(task?.title ?? '')
    setPriority(task?.priority ?? '')
    setBody(task?.body ?? '')
    setDependsOn(task?.depends_on.join(', ') ?? '')
    setParent(task?.parent !== null ? String(task?.parent) : '')
    setBlockReason(task?.block_reason ?? '')
    setServerValidationMessage(null)
    setConfirmType(null)
  }, [task?.id, task?.updated])

  useEffect(() => {
    if (initialSubtab !== 'history' || task === null) {
      return
    }

    setShowHistory(true)
  }, [initialSubtab, task])

  if (!task) return null

  const t = task

  function parseDependsOn(raw: string): { values: number[]; error: string | null } {
    const tokens = raw
      .split(',')
      .map((value) => value.trim())
      .filter((value) => value.length > 0)
    const values: number[] = []

    for (const token of tokens) {
      const parsed = Number(token)
      if (!Number.isInteger(parsed) || parsed < 0) {
        return {
          values: [],
          error: 'Dependencies must be a comma-separated list of non-negative integers.',
        }
      }
      values.push(parsed)
    }

    return { values, error: null }
  }

  function parseParent(raw: string): { value: number | null; error: string | null } {
    const trimmed = raw.trim()
    if (trimmed.length === 0) {
      return { value: null, error: null }
    }

    const parsed = Number(trimmed)
    if (!Number.isInteger(parsed) || parsed < 0) {
      return {
        value: null,
        error: 'Parent must be a non-negative integer.',
      }
    }

    return { value: parsed, error: null }
  }

  const parsedParent = useMemo(() => parseParent(parent), [parent])
  const parsedDependsOn = useMemo(() => parseDependsOn(dependsOn), [dependsOn])
  const clientValidationMessage = parsedParent.error ?? parsedDependsOn.error

  const isDirty =
    title !== t.title
    || priority !== t.priority
    || body !== t.body
    || dependsOn !== t.depends_on.join(', ')
    || parent !== (t.parent !== null ? String(t.parent) : '')
    || (t.blocked && blockReason !== (t.block_reason ?? ''))

  const validationMessage = clientValidationMessage ?? serverValidationMessage

  function previousStatus(current: string): string | null {
    const statuses = board?.statuses.map((status) => status.name) ?? []
    const currentIndex = statuses.indexOf(current)
    const valid = board?.valid_transitions[current] ?? []
    const fromValid = valid.find((candidate) => statuses.indexOf(candidate) === currentIndex - 1)
    if (fromValid) {
      return fromValid
    }
    if (currentIndex > 0) {
      return statuses[currentIndex - 1]
    }
    return null
  }

  async function runMutation(url: string, payload: Record<string, unknown>): Promise<void> {
    setServerValidationMessage(null)
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (res.ok) {
      const updatedTask = (await res.json()) as TaskDetail
      onTaskUpdated?.(updatedTask)
      return
    }

    if (res.status === 409) {
      const latestRes = await fetch(`/api/tasks/${t.id}`, { method: 'GET' })
      if (latestRes.ok) {
        const latestTask = (await latestRes.json()) as TaskDetail
        onTaskUpdated?.(latestTask)
      } else if (latestRes.status === 404) {
        onTaskCleared?.()
      }
      setShowConflict(true)
      return
    }

    if (res.status === 404) {
      onTaskCleared?.()
      return
    }

    if (res.status === 422) {
      setServerValidationMessage(await getResponseErrorMessage(res, 'Validation failed'))
      return
    }

    setServerValidationMessage(await getResponseErrorMessage(res, `Request failed with status ${res.status}`))
  }

  async function handleSave() {
    if (clientValidationMessage !== null) {
      return
    }

    const payload: Record<string, unknown> = {
      updated: t.updated,
      title,
      priority,
      body,
      depends_on: parsedDependsOn.values,
      parent: parsedParent.value,
      block_reason: t.blocked ? blockReason : null,
    }
    await runMutation(`/api/tasks/${t.id}/edit`, payload)
  }

  async function handleForceSave() {
    if (clientValidationMessage !== null) {
      return
    }

    setShowConflict(false)
    await runMutation(`/api/tasks/${t.id}/edit`, {
      updated: t.updated,
      title,
      priority,
      body,
      depends_on: parsedDependsOn.values,
      parent: parsedParent.value,
      block_reason: t.blocked ? blockReason : null,
    })
  }

  async function handleConfirm() {
    if (confirmType === 'unblock') {
      await runMutation(`/api/tasks/${t.id}/edit`, { updated: t.updated, block_reason: null })
      setConfirmType(null)
      return
    }
    if (confirmType === 'unclaim') {
      await runMutation(`/api/tasks/${t.id}/release`, { updated: t.updated })
      setConfirmType(null)
      return
    }
    if (confirmType === 'move-backward') {
      const target = previousStatus(t.status)
      if (target) {
        await runMutation(`/api/tasks/${t.id}/move`, { updated: t.updated, status: target })
      }
      setConfirmType(null)
    }
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
      target?: EventTarget | null
      detail?: unknown
    },
  ): string {
    if (event.detail && typeof event.detail === 'object' && 'value' in event.detail) {
      const detailValue = event.detail.value
      if (typeof detailValue === 'string') {
        return detailValue
      }
    }

    if (event.target && 'value' in event.target) {
      const value = event.target.value
      if (typeof value === 'string') {
        return value
      }
    }

    return ''
  }

  return (
    <div>
      {/* History tab button — always visible */}
      <PButton data-testid="history-tab" variant="secondary" onClick={() => void handleHistoryClick()}>
        History
      </PButton>

      {/* Read-only fields */}
      <span data-testid="field-id">{t.id}</span>
      <span data-testid="field-status">{t.status}</span>
      <span data-testid="field-created">{t.created}</span>
      <span data-testid="field-claimed">{String(t.claimed)}</span>
      <span data-testid="field-claimed-at">{t.claimed_at ?? ''}</span>
      <span data-testid="field-dep-status">{t.dep_status ?? ''}</span>

      {/* Editable fields */}
      <PInputText
        ref={setHideLabelAttr}
        name="title"
        data-field="title"
        hideLabel={true}
        value={title}
        onChange={(event) => setTitle(readControlValue(event))}
        onInput={(event) => setTitle(readControlValue(event))}
      />
      <PSelect
        ref={setHideLabelAttr}
        name="priority"
        data-field="priority"
        hideLabel={true}
        value={priority}
        onChange={(event) => setPriority(readControlValue(event))}
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
        name="depends_on"
        data-field="depends_on"
        hideLabel={true}
        value={dependsOn}
        onChange={(event) => setDependsOn(readControlValue(event))}
        onInput={(event) => setDependsOn(readControlValue(event))}
      />
      <PInputText
        ref={setHideLabelAttr}
        name="parent"
        data-field="parent"
        hideLabel={true}
        value={parent}
        onChange={(event) => setParent(readControlValue(event))}
        onInput={(event) => setParent(readControlValue(event))}
      />
      {t.blocked && (
        <PInputText
          ref={setHideLabelAttr}
          name="block_reason"
          data-field="block_reason"
          hideLabel={true}
          value={blockReason}
          onChange={(event) => setBlockReason(readControlValue(event))}
          onInput={(event) => setBlockReason(readControlValue(event))}
        />
      )}

      {/* Body — markdown view or edit textarea */}
      {editBody ? (
        <PTextarea
          ref={setHideLabelAttr}
          name="body"
          data-field="body"
          hideLabel={true}
          value={body}
          onChange={(event) => setBody(readControlValue(event))}
          onInput={(event) => setBody(readControlValue(event))}
        />
      ) : (
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{t.body}</ReactMarkdown>
      )}
      <PButton data-testid="body-edit-toggle" variant="secondary" onClick={() => setEditBody((v) => !v)}>
        Edit
      </PButton>

      {isDirty && <div data-testid="dirty-indicator">Unsaved changes</div>}

      {/* Actions */}
      <PButton data-testid="save-button" onClick={() => void handleSave()}>
        Save
      </PButton>
      <PButton data-testid="move-backward" variant="secondary" onClick={() => setConfirmType('move-backward')}>
        Move Backward
      </PButton>
      <PButton data-testid="unclaim-action" variant="secondary" onClick={() => setConfirmType('unclaim')}>
        Unclaim
      </PButton>
      {t.blocked && (
        <PButton data-testid="unblock-action" variant="secondary" onClick={() => setConfirmType('unblock')}>
          Unblock
        </PButton>
      )}

      {/* History subtab */}
      {(showHistory || initialSubtab === 'history') && (
        <HistorySubtab sessions={taskSessions} onSelectTask={onSelectTask} />
      )}

      {/* Conflict modal */}
      {showConflict && (
        <div data-testid="conflict-modal">
          <PButton
            data-testid="conflict-refresh"
            variant="secondary"
            onClick={() => setShowConflict(false)}
          >
            Discard changes
          </PButton>
          <PButton data-testid="conflict-overwrite" onClick={() => void handleForceSave()}>Force save</PButton>
        </div>
      )}
      {validationMessage && <div data-testid="validation-message">{validationMessage}</div>}

      {/* Confirm dialog */}
      {confirmType !== null && (
        <ConfirmDialog
          type={confirmType}
          blockReason={t.block_reason}
          onCancel={() => setConfirmType(null)}
          onConfirm={() => void handleConfirm()}
        />
      )}
    </div>
  )
}
