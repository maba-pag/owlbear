import { useEffect, useState } from 'react'
import { getResponseErrorMessage } from '../api/errorMessage'
import type { TaskDetail } from '../components/DetailTab'
import type { Board } from './useBoard'
import type { ConflictLocalDraft } from './useConflictDraft'

export interface UseTaskMutationOptions {
  taskId: number
  taskUpdated: string
  board?: Board | null
  conflictActions: {
    clearConflict: () => void
    setConflictDetected: (localDraft: ConflictLocalDraft | null, remoteTask: TaskDetail | null) => void
    setConflictDetectedNoRefetch: (localDraft: ConflictLocalDraft | null) => void
  }
  onTaskUpdated?: (task: TaskDetail) => void
  onTaskCleared?: (message?: string) => void
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
}

export interface MutationRunOptions {
  conflictDraft?: ConflictLocalDraft
  errorHeading: string
}

export interface UseTaskMutationResult {
  serverValidationMessage: string | null
  setServerValidationMessage: (message: string | null) => void
  previousStatus: (current: string) => string | null
  runMutation: (
    url: string,
    payload: Record<string, unknown>,
    options: MutationRunOptions,
  ) => Promise<void>
}

export function useTaskMutation(options: UseTaskMutationOptions): UseTaskMutationResult {
  const [serverValidationMessage, setServerValidationMessage] = useState<string | null>(null)

  useEffect(() => {
    setServerValidationMessage(null)
  }, [options.taskId, options.taskUpdated])

  function previousStatus(current: string): string | null {
    if (!options.board) {
      return null
    }

    const statuses = options.board.statuses.map((status) => status.name)
    const currentIndex = statuses.indexOf(current)
    if (currentIndex <= 0) {
      return null
    }

    const previous = statuses[currentIndex - 1]
    const valid = options.board.valid_transitions[current] ?? []
    return valid.includes(previous) ? previous : null
  }

  async function runMutation(
    url: string,
    payload: Record<string, unknown>,
    mutationOptions: MutationRunOptions,
  ): Promise<void> {
    setServerValidationMessage(null)
    let res: Response
    try {
      res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Network error'
      setServerValidationMessage(message)
      options.onMutationError?.(mutationOptions.errorHeading, message, 'error')
      return
    }

    if (res.ok) {
      const updatedTask = (await res.json()) as TaskDetail
      options.conflictActions.clearConflict()
      options.onTaskUpdated?.(updatedTask)
      return
    }

    if (res.status === 409) {
      const localDraft = mutationOptions.conflictDraft ?? null
      const latestRes = await fetch(`/api/tasks/${options.taskId}`, { method: 'GET' })
      if (latestRes.ok) {
        const latestTask = (await latestRes.json()) as TaskDetail
        options.conflictActions.setConflictDetected(localDraft, latestTask)
        options.onTaskUpdated?.(latestTask)
      } else if (latestRes.status === 404) {
        const message = await getResponseErrorMessage(latestRes, 'Task not found')
        setServerValidationMessage(message)
        options.conflictActions.clearConflict()
        options.onTaskCleared?.(message)
        return
      } else {
        options.conflictActions.setConflictDetectedNoRefetch(localDraft)
        setServerValidationMessage(
          await getResponseErrorMessage(latestRes, `Request failed with status ${latestRes.status}`),
        )
        return
      }
      return
    }

    if (res.status === 404) {
      options.onTaskCleared?.()
      return
    }

    if (res.status === 422) {
      const message = await getResponseErrorMessage(res, 'Validation failed')
      setServerValidationMessage(message)
      options.onMutationError?.(mutationOptions.errorHeading, message, 'warning')
      return
    }

    const message = await getResponseErrorMessage(res, `Request failed with status ${res.status}`)
    setServerValidationMessage(message)
    options.onMutationError?.(mutationOptions.errorHeading, message, 'error')
  }

  return {
    serverValidationMessage,
    setServerValidationMessage,
    previousStatus,
    runMutation,
  }
}