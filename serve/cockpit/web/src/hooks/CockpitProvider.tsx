import { createContext, useContext, useEffect, useRef, useState, type PropsWithChildren, type ReactElement } from 'react'
import { ApiError } from '../api/errors'
import { getTask, type TaskDetail } from '../api/tasks'
import { useBoard } from './useBoard'
import { usePendingDRs } from './usePendingDRs'
import { useScanPolling } from './useScanPolling'

type BoardStateValue = {
  board: ReturnType<typeof useBoard>['board']
  tasks: ReturnType<typeof useBoard>['tasks']
  loading: ReturnType<typeof useBoard>['loading']
  error: ReturnType<typeof useBoard>['error']
  health: ReturnType<typeof useBoard>['health']
  refetchTasks: ReturnType<typeof useBoard>['refetchTasks']
  items: ReturnType<typeof useScanPolling>['items']
  isLoading: ReturnType<typeof useScanPolling>['isLoading']
  scanError: ReturnType<typeof useScanPolling>['error']
  refetch: ReturnType<typeof useScanPolling>['refetch']
}

type TaskSelectionValue = {
  selectedTaskId: number | null
  selectedTask: TaskDetail | null
  selectedTaskError: string | null
  select: (taskId: number) => void
  clear: () => void
  update: (nextTask?: TaskDetail) => void
}

type DRStateValue = {
  count: ReturnType<typeof usePendingDRs>['count']
  items: ReturnType<typeof usePendingDRs>['items']
  isLoading: ReturnType<typeof usePendingDRs>['isLoading']
  error: ReturnType<typeof usePendingDRs>['error']
  refetch: ReturnType<typeof usePendingDRs>['refetch']
  selectedDRId: string | null
  setSelectedDRId: (id: string | null) => void
  selectedDR: ReturnType<typeof usePendingDRs>['items'][number] | null
}

interface CockpitContextValue {
  boardState: BoardStateValue
  taskSelection: TaskSelectionValue
  drState: DRStateValue
}

const CockpitContext = createContext<CockpitContextValue | null>(null)

export function CockpitProvider({ children }: PropsWithChildren): ReactElement {
  const { board, tasks, loading, error, health, refetchTasks, lastDecisionsMtime } = useBoard()
  const {
    count,
    items: pendingDRItems,
    isLoading: pendingDRLoading,
    error: pendingDRError,
    refetch: refetchPendingDRs,
  } = usePendingDRs()
  const { items: scanItems, isLoading, error: scanError, refetch } = useScanPolling()

  const [selectedDRId, setSelectedDRId] = useState<string | null>(null)
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null)
  const [selectedTaskError, setSelectedTaskError] = useState<string | null>(null)
  const [taskFetchNonce, setTaskFetchNonce] = useState(0)
  const activeTaskControllerRef = useRef<AbortController | null>(null)
  const previousSelectedTaskIdRef = useRef<number | null>(null)

  useEffect(() => {
    if (lastDecisionsMtime !== null) {
      void refetchPendingDRs()
    }
  }, [lastDecisionsMtime, refetchPendingDRs])

  useEffect(() => {
    if (selectedTaskId === null) {
      previousSelectedTaskIdRef.current = null
      activeTaskControllerRef.current?.abort()
      activeTaskControllerRef.current = null
      setSelectedTask(null)
      setSelectedTaskError(null)
      return
    }

    const isTaskSwitch =
      previousSelectedTaskIdRef.current !== null && previousSelectedTaskIdRef.current !== selectedTaskId
    previousSelectedTaskIdRef.current = selectedTaskId
    activeTaskControllerRef.current?.abort()

    setSelectedTask(null)
    setSelectedTaskError(null)

    const controller = new AbortController()
    activeTaskControllerRef.current = controller
    let cancelled = false
    let deferredFetch: ReturnType<typeof setTimeout> | null = null

    const runFetch = async () => {
      try {
        const task = await getTask(selectedTaskId, { signal: controller.signal })
        if (!cancelled) {
          setSelectedTask(task)
          setSelectedTaskError(null)
        }
      } catch (caught) {
        if (caught instanceof ApiError && !cancelled) {
          setSelectedTask(null)
          const fallback = `Task fetch failed with status ${caught.status}`
          const message =
            caught.message === `Get task request failed with status ${caught.status}`
              ? fallback
              : caught.message
          setSelectedTaskError(message)
          return
        }

        if (!(caught instanceof DOMException && caught.name === 'AbortError') && !cancelled) {
          setSelectedTask(null)
          setSelectedTaskError(caught instanceof Error ? caught.message : 'Task fetch failed')
        }
      }
    }

    if (isTaskSwitch) {
      deferredFetch = setTimeout(() => {
        void runFetch()
      }, 1)
    } else {
      void runFetch()
    }

    return () => {
      cancelled = true
      if (deferredFetch !== null) {
        clearTimeout(deferredFetch)
      }
      controller.abort()
      if (activeTaskControllerRef.current === controller) {
        activeTaskControllerRef.current = null
      }
    }
  }, [selectedTaskId, taskFetchNonce])

  const value: CockpitContextValue = {
    boardState: {
      board,
      tasks,
      loading,
      error,
      health,
      refetchTasks,
      items: scanItems,
      isLoading,
      scanError,
      refetch,
    },
    taskSelection: {
      selectedTaskId,
      selectedTask,
      selectedTaskError,
      select: (taskId) => {
        setSelectedTaskId(taskId)
      },
      clear: () => {
        setSelectedTaskId(null)
        setSelectedTask(null)
        setSelectedTaskError(null)
      },
      update: (nextTask) => {
        if (nextTask) {
          setSelectedTask(nextTask)
          setSelectedTaskError(null)
        }
        if (selectedTaskId !== null) {
          setTaskFetchNonce((value) => value + 1)
        }
      },
    },
    drState: {
      count,
      items: pendingDRItems,
      isLoading: pendingDRLoading,
      error: pendingDRError,
      refetch: refetchPendingDRs,
      selectedDRId,
      setSelectedDRId,
      selectedDR: pendingDRItems.find((item) => item.id === selectedDRId) ?? null,
    },
  }

  return <CockpitContext.Provider value={value}>{children}</CockpitContext.Provider>
}

function useCockpitContext(): CockpitContextValue {
  const context = useContext(CockpitContext)
  if (!context) {
    throw new Error('Cockpit hooks must be used within CockpitProvider')
  }
  return context
}

export function useBoardState(): BoardStateValue {
  return useCockpitContext().boardState
}

export function useTaskSelection(): TaskSelectionValue {
  return useCockpitContext().taskSelection
}

export function useDRState(): DRStateValue {
  return useCockpitContext().drState
}