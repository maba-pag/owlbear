import { useCallback, useMemo, useState } from 'react'

export interface ConflictLocalDraft {
  title: string
  priority: string
  body: string
  tags: string[]
  ac: string[]
  dependsOn: string
  parent: string
  blockReason: string
}

export interface ConflictRemoteTask {
  id: number
  title: string
  priority: string
  body: string | null
  tags: string[]
  ac?: string[]
  depends_on: number[]
  parent: number | null
  block_reason: string | null
}

export interface UseConflictDraftResult {
  showConflict: boolean
  showConflictOverwrite: boolean
  conflictLocalDraft: ConflictLocalDraft | null
  conflictRemoteTask: ConflictRemoteTask | null
  conflictChangedFields: string[]
  conflictRemoteValues: Record<string, string>
  conflictLocalValues: Record<string, string>
  setConflictDetected: (
    localDraft: ConflictLocalDraft | null,
    remoteTask: ConflictRemoteTask | null,
  ) => void
  clearConflict: () => void
  acknowledgeOverwrite: () => void
  dismissConflict: () => void
  clearConflictIfTaskChanged: (taskId: number | undefined) => void
}

const CONFLICT_FIELDS = ['title', 'priority', 'body', 'tags', 'ac', 'depends_on', 'parent', 'block_reason']

export function useConflictDraft(): UseConflictDraftResult {
  const [showConflict, setShowConflict] = useState(false)
  const [showConflictOverwrite, setShowConflictOverwrite] = useState(false)
  const [conflictLocalDraft, setConflictLocalDraft] = useState<ConflictLocalDraft | null>(null)
  const [conflictRemoteTask, setConflictRemoteTask] = useState<ConflictRemoteTask | null>(null)

  const conflictRemoteValues = useMemo<Record<string, string>>(
    () => ({
      title: conflictRemoteTask?.title ?? '',
      priority: conflictRemoteTask?.priority ?? '',
      body: conflictRemoteTask?.body ?? '',
      tags: (conflictRemoteTask?.tags ?? []).join(', '),
      ac: (conflictRemoteTask?.ac ?? []).join('\n'),
      depends_on: (conflictRemoteTask?.depends_on ?? []).join(', '),
      parent:
        conflictRemoteTask?.parent !== null && conflictRemoteTask?.parent !== undefined
          ? String(conflictRemoteTask.parent)
          : '',
      block_reason: conflictRemoteTask?.block_reason ?? '',
    }),
    [conflictRemoteTask],
  )

  const conflictLocalValues = useMemo<Record<string, string>>(
    () => ({
      title: conflictLocalDraft?.title ?? '',
      priority: conflictLocalDraft?.priority ?? '',
      body: conflictLocalDraft?.body ?? '',
      tags: (conflictLocalDraft?.tags ?? []).join(', '),
      ac: (conflictLocalDraft?.ac ?? []).join('\n'),
      depends_on: conflictLocalDraft?.dependsOn ?? '',
      parent: conflictLocalDraft?.parent ?? '',
      block_reason: conflictLocalDraft?.blockReason ?? '',
    }),
    [conflictLocalDraft],
  )

  const conflictChangedFields = useMemo(
    () => CONFLICT_FIELDS.filter((field) => conflictRemoteValues[field] !== conflictLocalValues[field]),
    [conflictLocalValues, conflictRemoteValues],
  )

  const setConflictDetected = useCallback((
    localDraft: ConflictLocalDraft | null,
    remoteTask: ConflictRemoteTask | null,
  ): void => {
    setConflictLocalDraft(localDraft)
    setConflictRemoteTask(remoteTask)
    setShowConflictOverwrite(false)
    setShowConflict(true)
  }, [])

  const clearConflict = useCallback((): void => {
    setConflictLocalDraft(null)
    setConflictRemoteTask(null)
    setShowConflict(false)
    setShowConflictOverwrite(false)
  }, [])

  const acknowledgeOverwrite = useCallback((): void => {
    setShowConflictOverwrite(true)
  }, [])

  const dismissConflict = useCallback((): void => {
    setShowConflict(false)
    setShowConflictOverwrite(false)
  }, [])

  const clearConflictIfTaskChanged = useCallback((taskId: number | undefined): void => {
    if (conflictRemoteTask === null) {
      return
    }

    if (taskId === conflictRemoteTask.id) {
      return
    }

    setConflictLocalDraft(null)
    setConflictRemoteTask(null)
    setShowConflict(false)
    setShowConflictOverwrite(false)
  }, [conflictRemoteTask?.id])

  return {
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
  }
}
