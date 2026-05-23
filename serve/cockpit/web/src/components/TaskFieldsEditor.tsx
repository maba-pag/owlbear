import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import {
  PButton,
  PInputText,
  PSelect,
  PSelectOption,
  PTag,
  PTagDismissible,
  PTextarea,
} from '@porsche-design-system/components-react'
import type { TaskDetail } from './DetailTab'
import MarkdownPreview from './MarkdownPreview'
import type { ConflictLocalDraft } from '../hooks/useConflictDraft'

export type TaskEditPayload = Record<string, unknown> & {
  updated: string
  title: string
  priority: string
  body: string
  tags: string[]
  depends_on: number[]
  parent: number | null
  block_reason: string | null
}

export interface TaskFieldsEditorProps {
  task: TaskDetail
  priorities: string[]
  conflictLocalDraft: ConflictLocalDraft | null
  conflictRemoteTaskId: number | null
  serverValidationMessage: string | null
  clearConflictIfTaskChanged: (taskId: number | undefined) => void
  onSave: (payload: TaskEditPayload, conflictDraft: ConflictLocalDraft) => Promise<boolean | void>
  onDirtyChange?: (dirty: boolean) => void
  onEditingChange?: (editing: boolean) => void
  defaultEditing?: boolean
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

function areTagListsEqual(left: string[], right: string[]): boolean {
  if (left.length !== right.length) {
    return false
  }

  return left.every((tag, index) => tag === right[index])
}

function normalizeTag(raw: string): string {
  return raw.trim()
}

function validateTag(tag: string, currentTags: string[]): string | null {
  if (tag.length === 0) {
    return 'Enter a tag before adding it.'
  }

  if (/[,\s]/.test(tag)) {
    return 'Tags must be a single token without spaces or commas.'
  }

  if (currentTags.includes(tag)) {
    return 'That tag is already on this task.'
  }

  return null
}

function TaskFieldsDisplay({
  task,
  taskBodyLabel,
  onEdit,
}: {
  task: TaskDetail
  taskBodyLabel: string
  onEdit: () => void
}) {
  const body = task.body ?? ''
  const hasRelations = task.depends_on.length > 0 || task.parent !== null || task.blocked

  return (
    <div className="grid gap-static-sm" data-testid="task-detail-display">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-static-sm">
        <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
          <span className="text-sm font-semibold text-contrast-high">Tags</span>
          {task.tags.length > 0 ? (
            task.tags.map((tag) => (
              <PTag key={tag} compact data-testid="display-tag-chip" data-tag={tag}>{tag}</PTag>
            ))
          ) : (
            <span data-testid="display-no-tags" className="text-sm text-contrast-high">No tags</span>
          )}
        </div>
        <PButton
          data-testid="edit-details-button"
          variant="secondary"
          icon="edit"
          compact
          onClick={onEdit}
        >
          Edit details
        </PButton>
      </div>

      <section className="rounded-lg border border-contrast-low bg-surface p-static-md" data-region="task-body-preview">
        <div className="mb-static-xs text-sm font-semibold text-contrast-high">{taskBodyLabel}</div>
        <MarkdownPreview className="text-sm">{body}</MarkdownPreview>
      </section>

      {hasRelations ? (
        <dl className="grid gap-static-sm text-sm text-primary md:grid-cols-3" data-region="task-relations-summary">
          {task.depends_on.length > 0 ? (
            <div>
              <dt className="font-semibold text-contrast-high">Depends on</dt>
              <dd>{task.depends_on.join(', ')}</dd>
            </div>
          ) : null}
          {task.parent !== null ? (
            <div>
              <dt className="font-semibold text-contrast-high">Parent</dt>
              <dd>{task.parent}</dd>
            </div>
          ) : null}
          {task.blocked ? (
            <div>
              <dt className="font-semibold text-contrast-high">Block reason</dt>
              <dd>{task.block_reason ?? 'Blocked'}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
    </div>
  )
}

export default function TaskFieldsEditor({
  task,
  priorities,
  conflictLocalDraft,
  conflictRemoteTaskId,
  serverValidationMessage,
  clearConflictIfTaskChanged,
  onSave,
  onDirtyChange,
  onEditingChange,
  defaultEditing,
}: TaskFieldsEditorProps) {
  const startsEditing = defaultEditing ?? true
  const [isEditing, setIsEditing] = useState(startsEditing)
  const [editBody, setEditBody] = useState(false)
  const [title, setTitle] = useState(task.title)
  const [priority, setPriority] = useState(task.priority)
  const [body, setBody] = useState(task.body ?? '')
  const [editableTags, setEditableTags] = useState(task.tags)
  const [newTag, setNewTag] = useState('')
  const [tagValidationMessage, setTagValidationMessage] = useState<string | null>(null)
  const [saveConfirmed, setSaveConfirmed] = useState(false)
  const [dependsOn, setDependsOn] = useState(task.depends_on.join(', '))
  const [parent, setParent] = useState(task.parent !== null ? String(task.parent) : '')
  const [blockReason, setBlockReason] = useState(task.block_reason ?? '')
  const saveConfirmedTimerRef = useRef<number | null>(null)
  const previousTaskIdRef = useRef(task.id)
  const taskBodyLabel = 'Task body'

  useEffect(() => {
    const isTaskSwitch = previousTaskIdRef.current !== task.id
    previousTaskIdRef.current = task.id

    if (conflictLocalDraft && conflictRemoteTaskId === task.id) {
      setIsEditing(true)
      setTitle(conflictLocalDraft.title)
      setPriority(conflictLocalDraft.priority)
      setBody(conflictLocalDraft.body)
      setEditableTags(conflictLocalDraft.tags)
      setDependsOn(conflictLocalDraft.dependsOn)
      setParent(conflictLocalDraft.parent)
      setBlockReason(conflictLocalDraft.blockReason)
      setNewTag('')
      setTagValidationMessage(null)
      return
    }

    setTitle(task.title)
    setPriority(task.priority)
    setBody(task.body ?? '')
    setEditableTags(task.tags)
    if (isTaskSwitch) {
      setIsEditing(startsEditing)
      setSaveConfirmed(false)
      setEditBody(false)
    }
    setDependsOn(task.depends_on.join(', '))
    setParent(task.parent !== null ? String(task.parent) : '')
    setBlockReason(task.block_reason ?? '')
    setNewTag('')
    setTagValidationMessage(null)
    clearConflictIfTaskChanged(task.id)
  }, [task.id, task.updated, conflictLocalDraft, conflictRemoteTaskId, clearConflictIfTaskChanged, task, startsEditing])

  useEffect(() => {
    return () => {
      if (saveConfirmedTimerRef.current !== null) {
        window.clearTimeout(saveConfirmedTimerRef.current)
      }
    }
  }, [])

  const parsedParent = useMemo(() => parseParent(parent), [parent])
  const parsedDependsOn = useMemo(() => parseDependsOn(dependsOn), [dependsOn])
  const clientValidationMessage = parsedParent.error ?? parsedDependsOn.error
  const isDirty =
    title !== task.title
    || priority !== task.priority
    || body !== (task.body ?? '')
    || !areTagListsEqual(editableTags, task.tags)
    || normalizeTag(newTag).length > 0
    || dependsOn !== task.depends_on.join(', ')
    || parent !== (task.parent !== null ? String(task.parent) : '')
    || (task.blocked && blockReason !== (task.block_reason ?? ''))
  const validationMessage = clientValidationMessage ?? serverValidationMessage

  useLayoutEffect(() => {
    onDirtyChange?.(isDirty)
  }, [isDirty, onDirtyChange])

  useEffect(() => {
    onEditingChange?.(isEditing)
  }, [isEditing, onEditingChange])

  useEffect(() => {
    return () => {
      onEditingChange?.(false)
    }
  }, [onEditingChange])

  useEffect(() => {
    return () => {
      onDirtyChange?.(false)
    }
  }, [onDirtyChange])

  function resetDraftFromTask(): void {
    setTitle(task.title)
    setPriority(task.priority)
    setBody(task.body ?? '')
    setEditableTags(task.tags)
    setDependsOn(task.depends_on.join(', '))
    setParent(task.parent !== null ? String(task.parent) : '')
    setBlockReason(task.block_reason ?? '')
    setNewTag('')
    setTagValidationMessage(null)
    setSaveConfirmed(false)
    setEditBody(false)
  }

  function addTagFromInput(): string[] | null {
    const tag = normalizeTag(newTag)
    const validation = validateTag(tag, editableTags)

    if (validation !== null) {
      setTagValidationMessage(validation)
      return null
    }

    const nextTags = [...editableTags, tag]
    setEditableTags(nextTags)
    setNewTag('')
    setTagValidationMessage(null)
    return nextTags
  }

  function removeTag(tagToRemove: string): void {
    setEditableTags((currentTags) => currentTags.filter((tag) => tag !== tagToRemove))
    setTagValidationMessage(null)
  }

  function tagsForSave(): string[] | null {
    const pendingTag = normalizeTag(newTag)
    if (pendingTag.length === 0) {
      return editableTags
    }

    const validation = validateTag(pendingTag, editableTags)
    if (validation !== null) {
      setTagValidationMessage(validation)
      return null
    }

    return [...editableTags, pendingTag]
  }

  async function handleSave() {
    if (clientValidationMessage !== null) {
      return
    }
    const nextTags = tagsForSave()
    if (nextTags === null) {
      return
    }
    const shouldShowSaveConfirmed = isDirty

    const conflictDraft: ConflictLocalDraft = {
      title,
      priority,
      body,
      tags: nextTags,
      dependsOn,
      parent,
      blockReason,
    }

    try {
      const mutationSucceeded = await onSave({
        updated: task.updated,
        title,
        priority,
        body,
        tags: nextTags,
        depends_on: parsedDependsOn.values,
        parent: parsedParent.value,
        block_reason: task.blocked ? blockReason : null,
      }, conflictDraft)

      if (shouldShowSaveConfirmed && mutationSucceeded !== false) {
        setEditableTags(nextTags)
        setNewTag('')
        setTagValidationMessage(null)
        setSaveConfirmed(true)
        if (saveConfirmedTimerRef.current !== null) {
          window.clearTimeout(saveConfirmedTimerRef.current)
        }
        saveConfirmedTimerRef.current = window.setTimeout(() => {
          setSaveConfirmed(false)
          saveConfirmedTimerRef.current = null
        }, 2000)
      } else if (mutationSucceeded === false) {
        setSaveConfirmed(false)
        if (saveConfirmedTimerRef.current !== null) {
          window.clearTimeout(saveConfirmedTimerRef.current)
          saveConfirmedTimerRef.current = null
        }
      }

      if (mutationSucceeded !== false && !startsEditing) {
        setIsEditing(false)
        setEditBody(false)
      }
    } catch {
      setSaveConfirmed(false)
    }
  }

  function handleCancelEdit(): void {
    resetDraftFromTask()
    setIsEditing(false)
  }

  return (
    <div className="grid gap-static-sm">
      {!isEditing ? (
        <TaskFieldsDisplay
          task={task}
          taskBodyLabel={taskBodyLabel}
          onEdit={() => setIsEditing(true)}
        />
      ) : null}

      <div
        className={isEditing ? 'grid gap-static-sm' : 'hidden'}
        data-region="task-detail-edit-form"
        hidden={!isEditing}
      >
      <div className="grid gap-static-sm lg:grid-cols-[minmax(0,1fr)_14rem]">
        <PInputText
          name="title"
          label="Title"
          data-field="title"
          value={title}
          onChange={(event) => setTitle(readControlValue(event))}
          onInput={(event) => setTitle(readControlValue(event))}
        />
        <PSelect
          name="priority"
          label="Priority"
          data-field="priority"
          value={priority}
          onChange={(event) => setPriority(readControlValue(event))}
        >
          {priorities.map((p) => (
            <PSelectOption key={p} value={p}>{p}</PSelectOption>
          ))}
        </PSelect>
      </div>

      <section className="grid gap-static-xs" data-region="task-detail-tags">
        <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
          <span className="text-sm font-semibold text-contrast-high">Tags</span>
          {editableTags.length > 0 ? (
            <div className="flex min-w-0 flex-wrap items-center gap-static-xs" data-testid="tag-chip-list">
              {editableTags.map((tag) => (
                <PTagDismissible
                  key={tag}
                  data-testid="tag-chip"
                  data-tag={tag}
                  compact
                  label={tag}
                  aria={{ 'aria-label': `Remove tag ${tag}` }}
                  onClick={() => removeTag(tag)}
                />
              ))}
            </div>
          ) : (
            <span data-testid="no-tags" className="text-sm text-contrast-high">No tags</span>
          )}
        </div>
        <div className="grid gap-static-xs sm:grid-cols-[minmax(0,1fr)_auto]">
          <PInputText
            name="new_tag"
            label="Add tag"
            data-field="new-tag"
            value={newTag}
            onChange={(event) => setNewTag(readControlValue(event))}
            onInput={(event) => setNewTag(readControlValue(event))}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                addTagFromInput()
              }
            }}
          />
          <PButton
            type="button"
            data-testid="add-tag-button"
            variant="secondary"
            icon="plus"
            compact
            disabled={normalizeTag(newTag).length === 0}
            onClick={() => addTagFromInput()}
          >
            Add
          </PButton>
        </div>
        {tagValidationMessage ? (
          <div data-testid="tag-validation-message" className="text-sm font-semibold text-warning" role="status">
            {tagValidationMessage}
          </div>
        ) : null}
      </section>

      <section className="rounded-lg border border-contrast-low bg-surface p-static-md">
        <div className={`mb-static-xs flex min-w-0 flex-wrap items-center gap-static-xs ${editBody ? 'justify-end' : 'justify-between'}`}>
          {editBody ? null : <span className="text-sm font-semibold text-contrast-high">{taskBodyLabel}</span>}
          <PButton
            data-testid="body-edit-toggle"
            variant="secondary"
            compact
            onClick={() => setEditBody((v) => !v)}
          >
            {editBody ? 'Preview' : 'Edit'}
          </PButton>
        </div>

        {editBody ? (
          <PTextarea
            name="body"
            label={taskBodyLabel}
            data-field="body"
            value={body}
            onChange={(event) => setBody(readControlValue(event))}
            onInput={(event) => setBody(readControlValue(event))}
          />
        ) : (
          <MarkdownPreview className="text-sm">{body}</MarkdownPreview>
        )}
      </section>

      <div className="grid gap-static-sm lg:grid-cols-2">
        <PInputText
          name="depends_on"
          label="Depends on"
          data-field="depends_on"
          value={dependsOn}
          onChange={(event) => setDependsOn(readControlValue(event))}
          onInput={(event) => setDependsOn(readControlValue(event))}
        />
        <PInputText
          name="parent"
          label="Parent"
          data-field="parent"
          value={parent}
          onChange={(event) => setParent(readControlValue(event))}
          onInput={(event) => setParent(readControlValue(event))}
        />
      </div>

      {task.blocked && (
        <PInputText
          name="block_reason"
          label="Block reason"
          data-field="block_reason"
          value={blockReason}
          onChange={(event) => setBlockReason(readControlValue(event))}
          onInput={(event) => setBlockReason(readControlValue(event))}
        />
      )}

      <div
        data-testid="task-detail-edit-actions"
        className="sticky bottom-0 z-20 flex min-w-0 flex-wrap items-center gap-static-sm border-t border-contrast-low bg-canvas px-static-xs py-static-sm shadow-lg"
      >
        <PButton data-testid="save-button" onClick={() => void handleSave()}>
          Save
        </PButton>
        {!startsEditing ? (
          <PButton data-testid="cancel-edit-button" variant="secondary" onClick={handleCancelEdit}>
            Cancel
          </PButton>
        ) : null}
        {isDirty && <div data-testid="dirty-indicator" className="text-sm font-semibold text-warning">Unsaved changes</div>}
        {saveConfirmed && <div data-testid="save-confirmed" className="text-sm font-semibold text-success">Saved</div>}
        {validationMessage && <div data-testid="validation-message" className="rounded-lg border border-warning bg-warning-low p-static-xs text-sm text-primary">{validationMessage}</div>}
      </div>
      </div>
    </div>
  )
}
