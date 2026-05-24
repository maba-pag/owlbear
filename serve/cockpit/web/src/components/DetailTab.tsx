import { useEffect, useRef, useState } from 'react'
import {
  PButton,
  PDivider,
  PHeading,
} from '@porsche-design-system/components-react'
import HistorySubtab, { type Session } from './HistorySubtab'
import ConflictBanner from './ConflictBanner'
import ArchivalModal from './ArchivalModal'
import TaskActions from './TaskActions'
import TaskFieldsEditor, {
  parseDependsOn,
  parseParent,
  type TaskReferenceSummary,
  type TaskEditPayload,
} from './TaskFieldsEditor'
import type { Board } from '../hooks/useBoard'
import {
  useConflictDraft,
  type ConflictLocalDraft,
} from '../hooks/useConflictDraft'
import { useTaskMutation } from '../hooks/useTaskMutation'
import { getOrderedTransitionTargets, shouldShowArchiveAction } from '../utils/taskTransitions'

interface TaskDetail {
  id: number
  title: string
  status: string
  priority: string
  body: string | null
  ac?: string[]
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
  taskReferences?: TaskReferenceSummary[]
  onTaskUpdated?: (task: TaskDetail) => void
  onSelectTask?: (taskId: number, subtab?: string) => void
  onTaskCleared?: (message?: string) => void
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
  onDirtyChange?: (dirty: boolean) => void
  onEditingChange?: (editing: boolean) => void
  actionPortalTarget?: HTMLElement | null
  initialSubtab?: string | null
}

export type { TaskDetail }

function syncHeadingAttrs(tag: 'h3', size: 'medium' | 'small') {
  return (element: HTMLElement | null): void => {
    if (!element) {
      return
    }
    element.setAttribute('tag', tag)
    element.setAttribute('size', size)
  }
}

function formatClaimed(claimed: boolean): string {
  return claimed ? 'Yes' : 'No'
}

function formatOptionalMetadata(value: string | null, fallback: string): string {
  return value && value.length > 0 ? value : fallback
}

export default function DetailTab({
  task,
  board,
  taskReferences = [],
  onTaskUpdated,
  onSelectTask,
  onTaskCleared,
  onMutationError,
  onDirtyChange,
  onEditingChange,
  actionPortalTarget,
  initialSubtab,
}: DetailTabProps) {
  const {
    showConflict,
    showConflictOverwrite,
    conflictLocalDraft,
    conflictRemoteTask,
    conflictChangedFields,
    conflictRemoteValues,
    conflictLocalValues,
    setConflictDetected,
    clearConflict,
    acknowledgeOverwrite,
    dismissConflict,
    clearConflictIfTaskChanged,
  } = useConflictDraft()
  const {
    serverValidationMessage,
    runMutation,
  } = useTaskMutation({
    taskId: task?.id ?? 0,
    taskUpdated: task?.updated ?? '',
    board,
    conflictActions: {
      clearConflict,
      setConflictDetected,
      setConflictDetectedNoRefetch: (localDraft) => {
        setConflictDetected(localDraft, null)
      },
    },
    onTaskUpdated,
    onTaskCleared,
    onMutationError,
  })
  const [showHistory, setShowHistory] = useState(false)
  const [sessions, setSessions] = useState<Session[]>([])
  const [archiveModalOpen, setArchiveModalOpen] = useState(false)
  const [isEditingTask, setIsEditingTask] = useState(false)
  const [acceptanceCriteriaPortalTarget, setAcceptanceCriteriaPortalTarget] = useState<HTMLElement | null>(null)
  const historyRegionRef = useRef<HTMLDivElement | null>(null)
  const archiveReturnFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (initialSubtab !== 'history' || task === null) {
      return
    }

    setShowHistory(true)
  }, [initialSubtab, task])

  useEffect(() => {
    if (!showHistory && initialSubtab !== 'history') {
      return undefined
    }

    const frameId = requestAnimationFrame(() => {
      historyRegionRef.current?.scrollIntoView({ block: 'nearest' })
    })
    return () => cancelAnimationFrame(frameId)
  }, [initialSubtab, sessions.length, showHistory, task?.id])

  if (!task) return null

  const t = task
  const moveTargets = board ? getOrderedTransitionTargets(board, t.status) : []
  const canArchive = shouldShowArchiveAction(t.status)

  async function handleSave(payload: TaskEditPayload, conflictDraft: ConflictLocalDraft) {
    return runMutation(`/api/tasks/${t.id}/edit`, payload, {
      conflictDraft,
      errorHeading: 'Edit failed',
    })
  }

  async function handleForceSave() {
    const draft = conflictLocalDraft ?? {
      title: t.title,
      priority: t.priority,
      body: t.body,
      ac: t.ac ?? [],
      tags: t.tags,
      dependsOn: t.depends_on.join(', '),
      parent: t.parent !== null ? String(t.parent) : '',
      blockReason: t.block_reason ?? '',
    }
    const forceDependsOn = parseDependsOn(draft.dependsOn)
    const forceParent = parseParent(draft.parent)

    dismissConflict()
    await runMutation(`/api/tasks/${t.id}/edit`, {
      updated: t.updated,
      title: draft.title,
      priority: draft.priority,
      body: draft.body,
      ac: draft.ac,
      tags: draft.tags,
      depends_on: forceDependsOn.values,
      parent: forceParent.value,
      block_reason: t.blocked ? draft.blockReason : null,
    }, { errorHeading: 'Edit failed' })
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
  const hasTaskActions = moveTargets.length > 0 || canArchive || t.claimed !== false || t.blocked
  const acceptanceCriteria = Array.isArray(t.ac) ? t.ac.filter((item) => item.trim().length > 0) : []

  return (
    <div className="flex w-full min-w-0 flex-col gap-static-md">
      <section className="rounded-lg border border-contrast-low bg-canvas p-static-xs sm:p-static-sm" data-region="task-detail-body">
        <TaskFieldsEditor
          task={t}
          priorities={board?.priorities ?? []}
          taskReferences={taskReferences}
          conflictLocalDraft={conflictLocalDraft}
          conflictRemoteTaskId={conflictRemoteTask?.id ?? null}
          serverValidationMessage={serverValidationMessage}
          clearConflictIfTaskChanged={clearConflictIfTaskChanged}
          onSave={handleSave}
          onSelectTask={(taskId) => onSelectTask?.(taskId)}
          onDirtyChange={onDirtyChange}
          onEditingChange={(editing) => {
            setIsEditingTask(editing)
            onEditingChange?.(editing)
          }}
          actionPortalTarget={actionPortalTarget}
          acceptanceCriteriaPortalTarget={acceptanceCriteriaPortalTarget}
          defaultEditing={false}
        />
      </section>

      <section className="rounded-lg border border-contrast-low bg-canvas p-static-sm" data-region="task-acceptance-criteria">
        <div className="mb-static-xs flex min-w-0 items-center justify-between gap-static-sm">
          <PHeading ref={syncHeadingAttrs('h3', 'small')} size="small" tag="h3">Acceptance Criteria</PHeading>
        </div>
        <div ref={setAcceptanceCriteriaPortalTarget} className="grid gap-static-xs">
          {!isEditingTask ? (
            acceptanceCriteria.length > 0 ? (
              <ul data-testid="task-ac-list" className="m-0 grid list-none gap-static-xs p-0 text-sm text-primary">
                {acceptanceCriteria.map((item, index) => (
                  <li key={`${index}-${item}`} data-testid="task-ac-item" className="rounded-md border border-contrast-low bg-surface px-static-sm py-static-xs">
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <span data-testid="task-ac-empty-state" className="text-sm text-contrast-high">No acceptance criteria defined.</span>
            )
          ) : null}
        </div>
      </section>

      <section className="rounded-lg border border-contrast-low bg-canvas p-static-sm" data-region="actions">
        <div className="mb-static-xs flex min-w-0 items-center justify-between gap-static-sm">
          <PHeading ref={syncHeadingAttrs('h3', 'small')} size="small" tag="h3">Actions</PHeading>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
          {hasTaskActions ? (
            <TaskActions
              key={`${t.id}:${t.updated}`}
              task={t}
              moveTargets={moveTargets}
              canArchive={canArchive}
              runMutation={runMutation}
              onArchive={(returnFocusTo) => {
                archiveReturnFocusRef.current = returnFocusTo
                setArchiveModalOpen(true)
              }}
            />
          ) : (
            <span data-testid="actions-empty-state" className="text-sm text-contrast-high">
              No direct actions available.
            </span>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-contrast-low bg-canvas p-static-sm" data-region="task-detail-metadata">
        <div className="mb-static-xs flex min-w-0 items-center justify-between gap-static-sm">
          <PHeading ref={syncHeadingAttrs('h3', 'small')} size="small" tag="h3">Metadata</PHeading>
        </div>
        <dl className="grid gap-x-static-lg gap-y-static-xs text-sm text-primary sm:grid-cols-2 lg:grid-cols-3">
          <div><dt className="font-semibold text-contrast-high">ID</dt><dd data-testid="field-id">{t.id}</dd></div>
          <div><dt className="font-semibold text-contrast-high">Status</dt><dd data-testid="field-status">{t.status}</dd></div>
          <div><dt className="font-semibold text-contrast-high">Priority</dt><dd data-testid="field-priority">{t.priority}</dd></div>
          <div><dt className="font-semibold text-contrast-high">Created</dt><dd data-testid="field-created">{t.created}</dd></div>
          <div><dt className="font-semibold text-contrast-high">Claimed</dt><dd data-testid="field-claimed">{formatClaimed(t.claimed)}</dd></div>
          <div><dt className="font-semibold text-contrast-high">Claimed at</dt><dd data-testid="field-claimed-at">{formatOptionalMetadata(t.claimed_at, 'Not claimed')}</dd></div>
          <div><dt className="font-semibold text-contrast-high">Dependency status</dt><dd data-testid="field-dep-status">{formatOptionalMetadata(t.dep_status, 'None')}</dd></div>
        </dl>
      </section>

      <PDivider />

      {archiveModalOpen ? (
        <ArchivalModal
          taskId={t.id}
          taskStatus={t.status}
          expectedUpdated={t.updated}
          returnFocusTo={archiveReturnFocusRef.current}
          onClose={() => setArchiveModalOpen(false)}
          onRefresh={() => undefined}
          onArchived={onTaskUpdated}
        />
      ) : null}

      <section className="flex min-w-0 items-center justify-start" data-region="history">
        <PButton data-testid="history-tab" variant="secondary" compact onClick={() => void handleHistoryClick()}>
          History
        </PButton>
      </section>

      {/* History subtab */}
      {(showHistory || initialSubtab === 'history') && (
        <div ref={historyRegionRef} data-region="task-history-events">
          <HistorySubtab sessions={taskSessions} taskId={t.id} createdAt={t.created} onSelectTask={onSelectTask} />
        </div>
      )}

      {/* Conflict modal */}
      <ConflictBanner
        showConflict={showConflict}
        showConflictOverwrite={showConflictOverwrite}
        conflictChangedFields={conflictChangedFields}
        conflictRemoteValues={conflictRemoteValues}
        conflictLocalValues={conflictLocalValues}
        onAcknowledgeOverwrite={acknowledgeOverwrite}
        onDiscardChanges={dismissConflict}
        onForceSave={() => void handleForceSave()}
      />

    </div>
  )
}
