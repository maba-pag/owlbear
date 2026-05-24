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
import { formatStatusLabel } from '../utils/taskTransitions'

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
  taskReferences?: TaskReferenceSummary[]
  conflictLocalDraft: ConflictLocalDraft | null
  conflictRemoteTaskId: number | null
  serverValidationMessage: string | null
  clearConflictIfTaskChanged: (taskId: number | undefined) => void
  onSave: (payload: TaskEditPayload, conflictDraft: ConflictLocalDraft) => Promise<boolean | void>
  onSelectTask?: (taskId: number) => void
  onDirtyChange?: (dirty: boolean) => void
  onEditingChange?: (editing: boolean) => void
  defaultEditing?: boolean
}

export interface TaskReferenceSummary {
  id: number
  title: string
  status: string
}

function formatTaskIds(ids: number[]): string {
  return ids.join(', ')
}

function normalizeTaskIdToken(token: string): string {
  return token.startsWith('#') ? token.slice(1) : token
}

function mergeTaskIds(existing: number[], additions: number[]): number[] {
  const seen = new Set(existing)
  const merged = [...existing]
  additions.forEach((id) => {
    if (!seen.has(id)) {
      seen.add(id)
      merged.push(id)
    }
  })
  return merged
}

export function parseDependsOn(raw: string): { values: number[]; error: string | null } {
  const tokens = raw
    .split(/[\s,]+/)
    .map((value) => value.trim())
    .filter((value) => value.length > 0)
  const values: number[] = []

  for (const token of tokens) {
    const parsed = Number(normalizeTaskIdToken(token))
    if (!Number.isInteger(parsed) || parsed < 0) {
      return {
        values: [],
        error: 'Dependencies must be task IDs separated with commas or spaces.',
      }
    }
    if (!values.includes(parsed)) {
      values.push(parsed)
    }
  }

  return { values, error: null }
}

export function parseParent(raw: string): { value: number | null; error: string | null } {
  const trimmed = raw.trim()
  if (trimmed.length === 0) {
    return { value: null, error: null }
  }

  const parsed = Number(normalizeTaskIdToken(trimmed))
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

function formatReferenceLabel(taskId: number, referenceById: Map<number, TaskReferenceSummary>): string {
  const summary = referenceById.get(taskId)
  return summary ? `#${taskId} ${summary.title}` : `#${taskId}`
}

function TaskReferenceChip({
  taskId,
  summary,
  relationLabel,
  onSelectTask,
}: {
  taskId: number
  summary: TaskReferenceSummary | undefined
  relationLabel: 'Dependency' | 'Parent'
  onSelectTask?: (taskId: number) => void
}) {
  const statusLabel = summary ? formatStatusLabel(summary.status) : 'Unavailable'
  const chipClassName = [
    'inline-flex min-h-8 max-w-full items-center gap-static-xs rounded-full border px-static-sm py-1 text-xs font-semibold leading-none',
    summary
      ? 'border-contrast-low bg-canvas text-primary hover:bg-frosted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]'
      : 'border-warning bg-warning-low text-primary',
  ].join(' ')
  const content = (
    <>
      <span className="shrink-0 font-mono">#{taskId}</span>
      {summary ? <span className="min-w-0 max-w-[14rem] truncate">{summary.title}</span> : null}
      <span className="shrink-0 rounded-full bg-frosted-soft px-2 py-px text-[0.68rem] uppercase leading-none text-contrast-high">
        {statusLabel}
      </span>
    </>
  )

  if (summary && onSelectTask) {
    return (
      <button
        type="button"
        data-testid="task-reference-chip"
        data-reference-id={taskId}
        data-reference-kind={relationLabel.toLowerCase()}
        data-reference-state="available"
        className={chipClassName}
        aria-label={`Open ${relationLabel.toLowerCase()} task #${taskId}: ${summary.title}`}
        onClick={() => onSelectTask(taskId)}
      >
        {content}
      </button>
    )
  }

  return (
    <span
      data-testid="task-reference-chip"
      data-reference-id={taskId}
      data-reference-kind={relationLabel.toLowerCase()}
      data-reference-state={summary ? 'available' : 'unavailable'}
      className={chipClassName}
      aria-label={summary ? `${relationLabel} task #${taskId}: ${summary.title}` : `${relationLabel} task #${taskId} is unavailable`}
    >
      {content}
    </span>
  )
}

function TaskFieldsDisplay({
  task,
  onEdit,
  taskReferences = [],
  onSelectTask,
}: {
  task: TaskDetail
  onEdit: () => void
  taskReferences?: TaskReferenceSummary[]
  onSelectTask?: (taskId: number) => void
}) {
  const body = task.body ?? ''
  const hasRelations = task.depends_on.length > 0 || task.parent !== null || task.blocked
  const referenceById = useMemo(
    () => new Map(taskReferences.map((reference) => [reference.id, reference])),
    [taskReferences],
  )

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
        <MarkdownPreview className="text-sm">{body}</MarkdownPreview>
      </section>

      {hasRelations ? (
        <dl className="grid gap-static-sm text-sm text-primary md:grid-cols-3" data-region="task-relations-summary">
          {task.depends_on.length > 0 ? (
            <div>
              <dt className="font-semibold text-contrast-high">Depends on</dt>
              <dd className="mt-1 flex min-w-0 flex-wrap gap-static-xs" data-testid="task-dependency-references">
                {task.depends_on.map((taskId) => (
                  <TaskReferenceChip
                    key={taskId}
                    taskId={taskId}
                    summary={referenceById.get(taskId)}
                    relationLabel="Dependency"
                    onSelectTask={onSelectTask}
                  />
                ))}
              </dd>
            </div>
          ) : null}
          {task.parent !== null ? (
            <div>
              <dt className="font-semibold text-contrast-high">Parent</dt>
              <dd className="mt-1 flex min-w-0 flex-wrap gap-static-xs" data-testid="task-parent-reference">
                <TaskReferenceChip
                  taskId={task.parent}
                  summary={referenceById.get(task.parent)}
                  relationLabel="Parent"
                  onSelectTask={onSelectTask}
                />
              </dd>
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
  taskReferences,
  conflictLocalDraft,
  conflictRemoteTaskId,
  serverValidationMessage,
  clearConflictIfTaskChanged,
  onSave,
  onSelectTask,
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
  const [newDependency, setNewDependency] = useState('')
  const [tagValidationMessage, setTagValidationMessage] = useState<string | null>(null)
  const [saveConfirmed, setSaveConfirmed] = useState(false)
  const [dependsOn, setDependsOn] = useState(task.depends_on.join(', '))
  const [parent, setParent] = useState(task.parent !== null ? String(task.parent) : '')
  const [blockReason, setBlockReason] = useState(task.block_reason ?? '')
  const saveConfirmedTimerRef = useRef<number | null>(null)
  const previousTaskIdRef = useRef(task.id)
  const bodyFieldLabel = 'Body'

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
      setNewDependency('')
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
    setNewDependency('')
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
  const parsedPendingDependencies = useMemo(() => parseDependsOn(newDependency), [newDependency])
  const clientValidationMessage = parsedParent.error ?? parsedDependsOn.error ?? parsedPendingDependencies.error
  const referenceById = useMemo(
    () => new Map((taskReferences ?? []).map((reference) => [reference.id, reference])),
    [taskReferences],
  )
  const isDirty =
    title !== task.title
    || priority !== task.priority
    || body !== (task.body ?? '')
    || !areTagListsEqual(editableTags, task.tags)
    || normalizeTag(newTag).length > 0
    || newDependency.trim().length > 0
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
    setNewDependency('')
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

  function addDependencyFromInput(): void {
    const pending = newDependency.trim()
    if (pending.length === 0 || parsedPendingDependencies.error !== null) {
      return
    }

    const nextDependencies = mergeTaskIds(parsedDependsOn.values, parsedPendingDependencies.values)
    setDependsOn(formatTaskIds(nextDependencies))
    setNewDependency('')
  }

  function removeDependency(taskId: number): void {
    setDependsOn(formatTaskIds(parsedDependsOn.values.filter((id) => id !== taskId)))
  }

  function dependenciesForSave(): number[] | null {
    if (parsedDependsOn.error !== null || parsedPendingDependencies.error !== null) {
      return null
    }

    return mergeTaskIds(parsedDependsOn.values, parsedPendingDependencies.values)
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
    const nextDependencies = dependenciesForSave()
    if (nextDependencies === null) {
      return
    }
    const shouldShowSaveConfirmed = isDirty

    const conflictDraft: ConflictLocalDraft = {
      title,
      priority,
      body,
      tags: nextTags,
      dependsOn: formatTaskIds(nextDependencies),
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
        depends_on: nextDependencies,
        parent: parsedParent.value,
        block_reason: task.blocked ? blockReason : null,
      }, conflictDraft)

      if (shouldShowSaveConfirmed && mutationSucceeded !== false) {
        setEditableTags(nextTags)
        setDependsOn(formatTaskIds(nextDependencies))
        setNewTag('')
        setNewDependency('')
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
    <div className="grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)] gap-static-sm">
      {!isEditing ? (
        <TaskFieldsDisplay
          task={task}
          taskReferences={taskReferences}
          onSelectTask={onSelectTask}
          onEdit={() => setIsEditing(true)}
        />
      ) : null}

      <div
        className={isEditing ? 'grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)] gap-static-sm' : 'hidden'}
        data-region="task-detail-edit-form"
        hidden={!isEditing}
      >
      <div className="grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)] gap-static-sm lg:grid-cols-[minmax(0,1fr)_14rem]">
        <PInputText
          name="title"
          label="Title"
          className="min-w-0"
          data-field="title"
          value={title}
          onChange={(event) => setTitle(readControlValue(event))}
          onInput={(event) => setTitle(readControlValue(event))}
        />
        <PSelect
          name="priority"
          label="Priority"
          className="min-w-0"
          data-field="priority"
          value={priority}
          onChange={(event) => setPriority(readControlValue(event))}
        >
          {priorities.map((p) => (
            <PSelectOption key={p} value={p}>{p}</PSelectOption>
          ))}
        </PSelect>
      </div>

      <section className="grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)] gap-static-xs" data-region="task-detail-tags">
        <div className="grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)] gap-static-xs sm:grid-cols-[minmax(0,1fr)_auto]" data-testid="tag-editor-row">
          <PInputText
            ref={(element) => element?.setAttribute('spellcheck', 'false')}
            name="new_tag"
            label="Tags"
            placeholder="Add tags"
            compact
            className="min-w-0"
            data-field="new-tag"
            spellCheck={false}
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
            className="min-w-0 self-end"
            compact
            disabled={normalizeTag(newTag).length === 0}
            onClick={() => addTagFromInput()}
          >
            Add tag
          </PButton>
        </div>
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
        {tagValidationMessage ? (
          <div data-testid="tag-validation-message" className="text-sm font-semibold text-warning" role="status">
            {tagValidationMessage}
          </div>
        ) : null}
      </section>

      <section className="rounded-lg border border-contrast-low bg-surface p-static-md">
        <div className="mb-static-xs flex min-w-0 flex-wrap items-center justify-end gap-static-xs">
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
            label={bodyFieldLabel}
            hideLabel
            className="min-w-0"
            data-field="body"
            value={body}
            onChange={(event) => setBody(readControlValue(event))}
            onInput={(event) => setBody(readControlValue(event))}
          />
        ) : (
          <MarkdownPreview className="text-sm">{body}</MarkdownPreview>
        )}
      </section>

      <section className="grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)] gap-static-sm lg:grid-cols-2" data-region="task-reference-editors">
        <div className="grid min-w-0 gap-static-xs" data-region="dependency-editor">
          <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
            <span className="text-sm font-semibold text-contrast-high">Depends on</span>
            {parsedDependsOn.values.length > 0 ? (
              <div className="flex min-w-0 flex-wrap items-center gap-static-xs" data-testid="dependency-chip-list">
                {parsedDependsOn.values.map((taskId) => (
                  <PTagDismissible
                    key={taskId}
                    data-testid="dependency-chip"
                    data-reference-id={taskId}
                    compact
                    label={formatReferenceLabel(taskId, referenceById)}
                    aria={{ 'aria-label': `Remove dependency ${taskId}` }}
                    onClick={() => removeDependency(taskId)}
                  />
                ))}
              </div>
            ) : (
              <span data-testid="no-dependencies" className="text-sm text-contrast-high">No dependencies</span>
            )}
          </div>
          <div className="grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)] gap-static-xs sm:grid-cols-[minmax(0,1fr)_auto]">
            <PInputText
              name="depends_on"
              label="Add dependency ID"
              className="min-w-0"
              data-field="depends_on"
              value={newDependency}
              onChange={(event) => setNewDependency(readControlValue(event))}
              onInput={(event) => setNewDependency(readControlValue(event))}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  addDependencyFromInput()
                }
              }}
            />
            <PButton
              type="button"
              data-testid="add-dependency-button"
              variant="secondary"
              icon="plus"
              className="min-w-0 self-end"
              compact
              disabled={newDependency.trim().length === 0}
              onClick={addDependencyFromInput}
            >
              Add
            </PButton>
          </div>
        </div>

        <div className="grid min-w-0 gap-static-xs" data-region="parent-editor">
          <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
            <span className="text-sm font-semibold text-contrast-high">Parent</span>
            {parsedParent.value !== null && parsedParent.error === null ? (
              <PTagDismissible
                data-testid="parent-chip"
                data-reference-id={parsedParent.value}
                compact
                label={formatReferenceLabel(parsedParent.value, referenceById)}
                aria={{ 'aria-label': `Clear parent ${parsedParent.value}` }}
                onClick={() => setParent('')}
              />
            ) : (
              <span data-testid="no-parent" className="text-sm text-contrast-high">No parent</span>
            )}
          </div>
          <div className="grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)] gap-static-xs sm:grid-cols-[minmax(0,1fr)_auto]">
            <PInputText
              name="parent"
              label="Set parent ID"
              className="min-w-0"
              data-field="parent"
              value={parent}
              onChange={(event) => setParent(readControlValue(event))}
              onInput={(event) => setParent(readControlValue(event))}
            />
            <PButton
              type="button"
              data-testid="clear-parent-button"
              variant="secondary"
              className="min-w-0 self-end"
              compact
              disabled={parent.trim().length === 0}
              onClick={() => setParent('')}
            >
              Clear
            </PButton>
          </div>
        </div>
      </section>

      {task.blocked && (
        <PInputText
          name="block_reason"
          label="Block reason"
          className="min-w-0"
          data-field="block_reason"
          value={blockReason}
          onChange={(event) => setBlockReason(readControlValue(event))}
          onInput={(event) => setBlockReason(readControlValue(event))}
        />
      )}

      <div
        data-testid="task-detail-edit-actions"
        className="flex w-full min-w-0 max-w-full flex-wrap items-center gap-static-sm border-t border-contrast-low bg-canvas px-static-xs py-static-sm md:sticky md:bottom-0 md:z-20 md:shadow-lg"
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
