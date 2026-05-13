import { useEffect, useState } from 'react'
import { ApiError } from '../api/errors'
import {
  editTask,
  getTask,
  moveTask,
  releaseTask,
  type EditRequest,
  type MoveRequest,
  type ReleaseRequest,
} from '../api/tasks'
import type { TaskDetail } from '../components/DetailTab'
import type { Board } from './useBoard'
import type { ConflictLocalDraft } from './useConflictDraft'

export interface UseTaskMutationOptions {
  taskId: number
  taskUpdated: string
  board?: Board | null
  conflictActions: {
    clearConflict: () => void
    setConflictDetected: (
      localDraft: ConflictLocalDraft | null,
      remoteTask: TaskDetail | null,
    ) => void
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

  async function runTaskMutation(url: string, payload: Record<string, unknown>): Promise<TaskDetail> {
    if (url.endsWith('/edit')) {
      return (await editTask(options.taskId, payload as unknown as EditRequest)) as TaskDetail
    }

    if (url.endsWith('/release')) {
      return (await releaseTask(options.taskId, payload as unknown as ReleaseRequest)) as TaskDetail
    }

    if (url.endsWith('/move')) {
      return (await moveTask(options.taskId, payload as unknown as MoveRequest)) as TaskDetail
    }

    throw new Error(`Unsupported mutation URL: ${url}`)
  }

  async function runMutation(
    url: string,
    payload: Record<string, unknown>,
    mutationOptions: MutationRunOptions,
  ): Promise<void> {
    setServerValidationMessage(null)
    try {
      const updatedTask = await runTaskMutation(url, payload)
      options.conflictActions.clearConflict()
      options.onTaskUpdated?.(updatedTask)
      return
    } catch (error) {
      if (!(error instanceof ApiError)) {
        const message = error instanceof Error ? error.message : 'Network error'
        setServerValidationMessage(message)
        options.onMutationError?.(mutationOptions.errorHeading, message, 'error')
        return
      }

      if (error.status === 409) {
        const localDraft = mutationOptions.conflictDraft ?? null
        try {
          const latestTask = (await getTask(options.taskId)) as TaskDetail
          options.conflictActions.setConflictDetected(localDraft, latestTask)
          options.onTaskUpdated?.(latestTask)
          return
        } catch (latestError) {
          if (latestError instanceof ApiError && latestError.status === 404) {
            setServerValidationMessage(latestError.message)
            options.conflictActions.clearConflict()
            options.onTaskCleared?.(latestError.message)
            return
          }

          options.conflictActions.setConflictDetectedNoRefetch(localDraft)
          const message = latestError instanceof Error ? latestError.message : 'Request failed'
          setServerValidationMessage(message)
          return
        }
      }

      if (error.status === 404) {
        options.onTaskCleared?.()
        return
      }

      if (error.status === 422) {
        setServerValidationMessage(error.message)
        options.onMutationError?.(mutationOptions.errorHeading, error.message, 'warning')
        return
      }

      const fallbackMessage = `Request failed with status ${error.status}`
      const message =
        error.message === `Edit task request failed with status ${error.status}` ||
        error.message === `Release task request failed with status ${error.status}` ||
        error.message === `Move task request failed with status ${error.status}`
          ? fallbackMessage
          : error.message
      setServerValidationMessage(message)
      options.onMutationError?.(mutationOptions.errorHeading, message, 'error')
    }
  }

  return {
    serverValidationMessage,
    setServerValidationMessage,
    previousStatus,
    runMutation,
  }
}
