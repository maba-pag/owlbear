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
import type { TaskDetail } from './DetailTab'
import type { ConflictLocalDraft } from '../hooks/useConflictDraft'

export type TaskEditPayload = Record<string, unknown> & {
  updated: string
  title: string
  priority: string
  body: string
  depends_on: number[]
  parent: number | null
  block_reason: string | null
}

export interface TaskFieldsEditorProps {
  task: TaskDetail
  conflictLocalDraft: ConflictLocalDraft | null
  conflictRemoteTaskId: number | null
  serverValidationMessage: string | null
  clearConflictIfTaskChanged: (taskId: number | undefined) => void
  onSave: (payload: TaskEditPayload, conflictDraft: ConflictLocalDraft) => Promise<void>
}

export function parseDependsOn(raw: string): { values: number[]; error: string | null } {
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

export function parseParent(raw: string): { value: number | null; error: string | null } {
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

export default function TaskFieldsEditor({
  task,
  conflictLocalDraft,
  conflictRemoteTaskId,
  serverValidationMessage,
  clearConflictIfTaskChanged,
  onSave,
}: TaskFieldsEditorProps) {
  const [editBody, setEditBody] = useState(false)
  const [title, setTitle] = useState(task.title)
  const [priority, setPriority] = useState(task.priority)
  const [body, setBody] = useState(task.body ?? '')
  const [dependsOn, setDependsOn] = useState(task.depends_on.join(', '))
  const [parent, setParent] = useState(task.parent !== null ? String(task.parent) : '')
  const [blockReason, setBlockReason] = useState(task.block_reason ?? '')

  useEffect(() => {
    if (conflictLocalDraft && conflictRemoteTaskId === task.id) {
      setTitle(conflictLocalDraft.title)
      setPriority(conflictLocalDraft.priority)
      setBody(conflictLocalDraft.body)
      setDependsOn(conflictLocalDraft.dependsOn)
      setParent(conflictLocalDraft.parent)
      setBlockReason(conflictLocalDraft.blockReason)
      return
    }

    setTitle(task.title)
    setPriority(task.priority)
    setBody(task.body ?? '')
    setDependsOn(task.depends_on.join(', '))
    setParent(task.parent !== null ? String(task.parent) : '')
    setBlockReason(task.block_reason ?? '')
    clearConflictIfTaskChanged(task.id)
  }, [task.id, task.updated, conflictLocalDraft, conflictRemoteTaskId, clearConflictIfTaskChanged, task])

  const parsedParent = useMemo(() => parseParent(parent), [parent])
  const parsedDependsOn = useMemo(() => parseDependsOn(dependsOn), [dependsOn])
  const clientValidationMessage = parsedParent.error ?? parsedDependsOn.error
  const isDirty =
    title !== task.title
    || priority !== task.priority
    || body !== (task.body ?? '')
    || dependsOn !== task.depends_on.join(', ')
    || parent !== (task.parent !== null ? String(task.parent) : '')
    || (task.blocked && blockReason !== (task.block_reason ?? ''))
  const validationMessage = clientValidationMessage ?? serverValidationMessage

  async function handleSave() {
    if (clientValidationMessage !== null) {
      return
    }

    const conflictDraft: ConflictLocalDraft = {
      title,
      priority,
      body,
      dependsOn,
      parent,
      blockReason,
    }

    await onSave({
      updated: task.updated,
      title,
      priority,
      body,
      depends_on: parsedDependsOn.values,
      parent: parsedParent.value,
      block_reason: task.blocked ? blockReason : null,
    }, conflictDraft)
  }

  return (
    <>
      <PInputText
        ref={setHideLabelAttr}
        name="title"
        label="Title"
        data-field="title"
        value={title}
        onChange={(event) => setTitle(readControlValue(event))}
        onInput={(event) => setTitle(readControlValue(event))}
      />
      <PSelect
        ref={setHideLabelAttr}
        name="priority"
        label="Priority"
        data-field="priority"
        value={priority}
        onChange={(event) => setPriority(readControlValue(event))}
      >
        <option value={priority}>{priority}</option>
      </PSelect>
      {task.tags.map((tag) => (
        <p-tag key={tag} data-testid="tag-chip">{tag}</p-tag>
      ))}
      <PInputText
        ref={setHideLabelAttr}
        name="depends_on"
        label="Depends on"
        data-field="depends_on"
        value={dependsOn}
        onChange={(event) => setDependsOn(readControlValue(event))}
        onInput={(event) => setDependsOn(readControlValue(event))}
      />
      <PInputText
        ref={setHideLabelAttr}
        name="parent"
        label="Parent"
        data-field="parent"
        value={parent}
        onChange={(event) => setParent(readControlValue(event))}
        onInput={(event) => setParent(readControlValue(event))}
      />
      {task.blocked && (
        <PInputText
          ref={setHideLabelAttr}
          name="block_reason"
          label="Block reason"
          data-field="block_reason"
          value={blockReason}
          onChange={(event) => setBlockReason(readControlValue(event))}
          onInput={(event) => setBlockReason(readControlValue(event))}
        />
      )}

      {editBody ? (
        <PTextarea
          ref={setHideLabelAttr}
          name="body"
          label="Body"
          data-field="body"
          value={body}
          onChange={(event) => setBody(readControlValue(event))}
          onInput={(event) => setBody(readControlValue(event))}
        />
      ) : (
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
          {body}
        </ReactMarkdown>
      )}
      <PButton
        data-testid="body-edit-toggle"
        variant="secondary"
        onClick={() => setEditBody((v) => !v)}
      >
        Edit
      </PButton>

      {isDirty && <div data-testid="dirty-indicator">Unsaved changes</div>}

      <PButton data-testid="save-button" onClick={() => void handleSave()}>
        Save
      </PButton>

      {validationMessage && <div data-testid="validation-message">{validationMessage}</div>}
    </>
  )
}
