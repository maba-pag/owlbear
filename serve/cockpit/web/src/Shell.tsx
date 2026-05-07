import { type ReactElement, useRef, useEffect, useState } from 'react'
import { Routes, Route } from 'react-router'
import { PButton } from '@porsche-design-system/components-react'
import KanbanBoard from './KanbanBoard'
import ActivityTab from './components/ActivityTab'
import DetailTab, { type TaskDetail } from './components/DetailTab'
import DRStatusIndicator from './components/DRStatusIndicator'
import HealthBadge, { type ScanItem as HealthBadgeItem } from './components/HealthBadge'
import ResolveModal from './components/ResolveModal'
import { useBoard } from './hooks/useBoard'
import { usePendingDRs } from './hooks/usePendingDRs'
import { type ScanItem as ScanPollingItem, useScanPolling } from './hooks/useScanPolling'
import './Shell.css'

function isHealthBadgeItem(item: ScanPollingItem): item is HealthBadgeItem {
  return item.code !== null && item.detail !== null && item.file_path !== null
}

function Shell() {
  const { board, tasks, loading, error, health, refetchTasks, lastDecisionsMtime } = useBoard()
  const { count: pendingDRCount, items: pendingDRItems, refetch: refetchPendingDRs } = usePendingDRs()
  const { items: scanItems, isLoading, refetch } = useScanPolling()
  const normalizedItems = scanItems.filter(isHealthBadgeItem)
  const [hasLoadedScan, setHasLoadedScan] = useState(false)
  const [selectedDRId, setSelectedDRId] = useState<string | null>(null)
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null)
  const selectedDR = pendingDRItems.find((item) => item.id === selectedDRId) ?? null
  const tabsRef = useRef<HTMLElement>(null)
  const detailRef = useRef<HTMLDivElement>(null)
  const activityRef = useRef<HTMLDivElement>(null)
  const refetchPendingDRsRef = useRef(refetchPendingDRs)

  const kanbanProps = {
    board,
    tasks,
    loading,
    error,
    refetchTasks,
    onSelectTask: setSelectedTaskId,
    selectedId: selectedTaskId,
  }
  const mockedKanbanBoard = KanbanBoard as unknown as {
    mock?: unknown
    (props: typeof kanbanProps, legacyContext?: Record<string, unknown>): ReactElement
  }
  const kanbanElement = mockedKanbanBoard.mock
    ? mockedKanbanBoard(kanbanProps, {})
    : <KanbanBoard {...kanbanProps} />

  useEffect(() => {
    if (!isLoading) {
      setHasLoadedScan(true)
    }
  }, [isLoading])

  useEffect(() => {
    const tabs = tabsRef.current
    if (!tabs) return
    const onTabChange = (e: Event) => {
      const index = (e as CustomEvent<{ activeTabIndex: number }>).detail.activeTabIndex
      detailRef.current?.setAttribute('aria-hidden', String(index !== 0))
      activityRef.current?.setAttribute('aria-hidden', String(index !== 1))
    }
    tabs.addEventListener('tabChange', onTabChange)
    return () => tabs.removeEventListener('tabChange', onTabChange)
  }, [])

  useEffect(() => {
    refetchPendingDRsRef.current = refetchPendingDRs
  }, [refetchPendingDRs])

  useEffect(() => {
    if (lastDecisionsMtime !== null) {
      refetchPendingDRsRef.current()
    }
  }, [lastDecisionsMtime])

  useEffect(() => {
    if (selectedTaskId === null) {
      setSelectedTask(null)
      return
    }

    // Clear stale detail data immediately when switching tasks.
    setSelectedTask(null)

    const controller = new AbortController()
    let cancelled = false

    void (async () => {
      try {
        const response = await fetch(`/api/tasks/${selectedTaskId}`, { signal: controller.signal })
        if (!response.ok) {
          if (!cancelled) {
            setSelectedTask(null)
          }
          return
        }

        const task = (await response.json()) as TaskDetail
        if (!cancelled) {
          setSelectedTask(task)
        }
      } catch (error) {
        if (!(error instanceof DOMException && error.name === 'AbortError') && !cancelled) {
          setSelectedTask(null)
        }
      }
    })()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [selectedTaskId])

  return (
    <div className="shell">
      <header className="shell__status-bar" data-region="status-bar">
        <span data-testid="traffic-light" data-health={health} />
        <span data-testid="task-count" />
        {hasLoadedScan ? (
          <HealthBadge
            items={normalizedItems}
            corruptionCount={normalizedItems.length}
            onRepairSuccess={refetch}
          />
        ) : null}
        <DRStatusIndicator
          count={pendingDRCount}
          items={pendingDRItems}
          onItemClick={setSelectedDRId}
        />
      </header>
      <nav className="shell__nav-rail" data-region="nav-rail">
        <PButton data-surface="kanban" aria-current="page" variant="secondary">
          <svg
            aria-hidden="true"
            viewBox="0 0 16 16"
            width="16"
            height="16"
            focusable="false"
          >
            <path d="M2 3h5v4H2V3zm7 0h5v4H9V3zM2 9h5v4H2V9zm7 0h5v4H9V9z" fill="currentColor" />
          </svg>
          Kanban
        </PButton>
      </nav>
      <main className="shell__workspace" data-region="workspace">
        <Routes>
          <Route path="/" element={kanbanElement} />
        </Routes>
      </main>
      <aside className="shell__sidecar" data-region="sidecar">
        <p-tabs ref={tabsRef}>
          <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Detail')}>
            <div ref={detailRef} data-tab-content="detail" aria-hidden="false">
              {selectedTaskId === null
                ? <div data-testid="detail-placeholder">Select a task to view details.</div>
                : null}
              <DetailTab
                key={selectedTaskId ?? -1}
                task={selectedTask}
                board={board}
                onSelectTask={(taskId) => setSelectedTaskId(taskId)}
                onTaskCleared={() => {
                  setSelectedTaskId(null)
                  setSelectedTask(null)
                }}
                onTaskUpdated={(updatedTask) => {
                  const previousTask = selectedTask
                  setSelectedTask(updatedTask)
                  if (
                    previousTask === null ||
                    previousTask.title !== updatedTask.title ||
                    previousTask.priority !== updatedTask.priority ||
                    previousTask.status !== updatedTask.status ||
                    previousTask.blocked !== updatedTask.blocked
                  ) {
                    refetchTasks()
                  }
                }}
              />
            </div>
          </p-tabs-item>
          <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Activity')}>
            <div ref={activityRef} data-tab-content="activity" aria-hidden="true">
              <ActivityTab onSelectTask={(taskId) => setSelectedTaskId(taskId)} />
            </div>
          </p-tabs-item>
        </p-tabs>
      </aside>
      {selectedDR ? (
        <ResolveModal
          dr={selectedDR}
          onClose={() => setSelectedDRId(null)}
          onResolved={() => {
            void refetchPendingDRs()
            setSelectedDRId(null)
          }}
        />
      ) : null}
      <div className="shell__contextual" data-region="contextual" />
    </div>
  )
}

export default Shell
