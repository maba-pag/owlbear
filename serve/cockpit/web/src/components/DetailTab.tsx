import { useEffect, useState } from 'react'
import {
  PButton,
  PDivider,
  PHeading,
} from '@porsche-design-system/components-react'
import HistorySubtab, { type Session } from './HistorySubtab'
import ConflictBanner from './ConflictBanner'
import TaskActions from './TaskActions'
import TaskFieldsEditor, {
  parseDependsOn,
  parseParent,
  type TaskEditPayload,
} from './TaskFieldsEditor'
import type { Board } from '../hooks/useBoard'
import {
  useConflictDraft,
  type ConflictLocalDraft,
} from '../hooks/useConflictDraft'
import { useTaskMutation } from '../hooks/useTaskMutation'

interface TaskDetail {
  id: number
  title: string
  status: string
  priority: string
  body: string | null
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
  onTaskCleared?: (message?: string) => void
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
  initialSubtab?: string | null
}

export type { TaskDetail }

function setHeadingMediumSizeAttr(element: HTMLElement | null): void {
  element?.setAttribute('size', 'medium')
}

function setHeadingSmallSizeAttr(element: HTMLElement | null): void {
  if (!element) {
    return
  }
  element.setAttribute('size', 'small')
  element.setAttribute('tag', 'h3')
}

function setMetadataAccordionAttrs(element: HTMLElement | null): void {
  if (!element) {
    return
  }

  element.setAttribute('compact', '')
  element.setAttribute('heading', 'Metadata')
}

export default function DetailTab({
  task,
  board,
  onTaskUpdated,
  onSelectTask,
  onTaskCleared,
  onMutationError,
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
    previousStatus,
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

  useEffect(() => {
    if (initialSubtab !== 'history' || task === null) {
      return
    }

    setShowHistory(true)
  }, [initialSubtab, task])

  if (!task) return null

  const t = task
  const backwardTarget = previousStatus(t.status)

  async function handleSave(payload: TaskEditPayload, conflictDraft: ConflictLocalDraft) {
    await runMutation(`/api/tasks/${t.id}/edit`, payload, {
      conflictDraft,
      errorHeading: 'Edit failed',
    })
  }

  async function handleForceSave() {
    const draft = conflictLocalDraft ?? {
      title: t.title,
      priority: t.priority,
      body: t.body,
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

  return (
    <div>
      <p-accordion ref={setMetadataAccordionAttrs} data-region="sidecar-metadata">
        {/* Read-only fields */}
        <div>
          <p>
            <strong>ID:</strong> <span data-testid="field-id">{t.id}</span>
          </p>
          <p>
            <strong>Status:</strong> <span data-testid="field-status">{t.status}</span>
          </p>
          <p>
            <strong>Priority:</strong> <span data-testid="field-priority">{t.priority}</span>
          </p>
          <p>
            <strong>Created:</strong> <span data-testid="field-created">{t.created}</span>
          </p>
          <p>
            <strong>Claimed:</strong> <span data-testid="field-claimed">{String(t.claimed)}</span>
          </p>
          <p>
            <strong>Claimed at:</strong> <span data-testid="field-claimed-at">{t.claimed_at ?? ''}</span>
          </p>
          <p>
            <strong>Dependency status:</strong> <span data-testid="field-dep-status">{t.dep_status ?? ''}</span>
          </p>
        </div>
      </p-accordion>

      <PDivider />

      <section data-region="sidecar-body">
        <PHeading ref={setHeadingMediumSizeAttr} size="medium">Details</PHeading>
        <TaskFieldsEditor
          task={t}
          priorities={board?.priorities ?? []}
          conflictLocalDraft={conflictLocalDraft}
          conflictRemoteTaskId={conflictRemoteTask?.id ?? null}
          serverValidationMessage={serverValidationMessage}
          clearConflictIfTaskChanged={clearConflictIfTaskChanged}
          onSave={handleSave}
        />
      </section>

      <section data-region="actions">
        <PHeading ref={setHeadingSmallSizeAttr} size="small">Actions</PHeading>
        <TaskActions
          key={`${t.id}:${t.updated}`}
          task={t}
          backwardTarget={backwardTarget}
          runMutation={runMutation}
        />
      </section>

      {/* History tab button — always visible */}
      <section data-region="history">
        <PButton data-testid="history-tab" variant="secondary" onClick={() => void handleHistoryClick()}>
          History
        </PButton>
      </section>

      {/* History subtab */}
      {(showHistory || initialSubtab === 'history') && (
        <HistorySubtab sessions={taskSessions} onSelectTask={onSelectTask} />
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
