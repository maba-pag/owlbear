import { useRef, useEffect, useState } from 'react'
import { Routes, Route } from 'react-router'
import { PBanner, PButton } from '@porsche-design-system/components-react'
import KanbanBoard from './KanbanBoard'
import ActivityTab from './components/ActivityTab'
import CleanupPanel from './components/CleanupPanel'
import DecisionViewport from './components/DecisionViewport'
import DetailTab from './components/DetailTab'
import DRStatusIndicator from './components/DRStatusIndicator'
import HealthBadge, { type ScanItem as HealthBadgeItem } from './components/HealthBadge'
import ResolveModal from './components/ResolveModal'
import { useBoardState, useDRState, useTaskSelection } from './hooks/CockpitProvider'
import { type ScanItem as ScanPollingItem } from './hooks/useScanPolling'
import './Shell.css'

function isHealthBadgeItem(item: ScanPollingItem): item is HealthBadgeItem {
  return item.code !== null && item.detail !== null && item.file_path !== null
}

function Shell() {
  const {
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
  } = useBoardState()
  const {
    count: pendingDRCount,
    items: pendingDRItems,
    isLoading: pendingDRLoading,
    error: pendingDRError,
    refetch: refetchPendingDRs,
    setSelectedDRId,
    selectedDR,
  } = useDRState()
  const { selectedTaskId, selectedTask, selectedTaskError, select, clear, update } = useTaskSelection()
  const normalizedItems = scanItems.filter(isHealthBadgeItem)
  const statusHealth = scanError ? 'red' : health
  const [hasLoadedScan, setHasLoadedScan] = useState(false)
  const [isSidecarCollapsed, setIsSidecarCollapsed] = useState(false)
  const [selectedTaskSubtab, setSelectedTaskSubtab] = useState<string | null>(null)
  const [detailValidationMessage, setDetailValidationMessage] = useState<string | null>(null)
  const [bannerError, setBannerError] = useState<{
    heading: string
    description: string
    state: 'error' | 'warning'
  } | null>(null)
  const tabsRef = useRef<HTMLElement>(null)
  const detailRef = useRef<HTMLDivElement>(null)
  const activityRef = useRef<HTMLDivElement>(null)

  const kanbanProps = {
    board,
    tasks,
    loading,
    error,
    refetchTasks,
    onSelectTask: (taskId: number) => {
      select(taskId)
      setDetailValidationMessage(null)
    },
    onMutationError: (heading: string, description: string, state: 'error' | 'warning') => {
      setBannerError({ heading, description, state })
    },
    onMutationSuccess: () => {
      setBannerError(null)
    },
    selectedId: selectedTaskId,
  }

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

  return (
    <div className="shell" data-sidecar-collapsed={isSidecarCollapsed || undefined}>
      <header className="shell__status-bar" data-region="status-bar">
        <h1
          style={{
            position: 'absolute',
            width: '1px',
            height: '1px',
            padding: 0,
            margin: '-1px',
            overflow: 'hidden',
            clip: 'rect(0, 0, 0, 0)',
            whiteSpace: 'nowrap',
            border: 0,
          }}
        >
          OwlBear Cockpit
        </h1>
        <span data-testid="traffic-light" data-health={statusHealth} />
        <span data-testid="task-count" />
        {hasLoadedScan && !scanError ? (
          <HealthBadge
            items={normalizedItems}
            corruptionCount={normalizedItems.length}
            onRepairSuccess={refetch}
          />
        ) : null}
        <CleanupPanel onSuccess={refetchTasks} />
        {scanError ? (
          <>
            <span data-testid="scan-error" data-health="error" role="status">
              Scan failed: {scanError.message}
            </span>
            <PButton
              type="button"
              data-testid="scan-retry"
              aria-label="Retry scan"
              variant="secondary"
              onClick={refetch}
            >
              Retry scan
            </PButton>
          </>
        ) : null}
        <DRStatusIndicator
          count={pendingDRCount}
          items={pendingDRItems}
          onItemClick={setSelectedDRId}
        />
        {pendingDRError ? (
          <span data-testid="dr-polling-error" role="status">
            {pendingDRError.message}
          </span>
        ) : null}
      </header>
      <nav className="shell__nav-rail" data-region="nav-rail">
        <PButton data-surface="kanban" aria-current="page" variant="secondary" tabIndex={-1}>
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
          <Route path="/" element={<KanbanBoard {...kanbanProps} />} />
        </Routes>
      </main>
      <aside className="shell__sidecar" data-region="sidecar">
        <button
          type="button"
          data-testid="sidecar-collapse"
          aria-expanded={!isSidecarCollapsed}
          aria-controls="shell-sidecar-content"
          onClick={() => setIsSidecarCollapsed((current) => !current)}
        >
          {isSidecarCollapsed ? 'Expand sidecar' : 'Collapse sidecar'}
        </button>
        <div id="shell-sidecar-content" aria-hidden={isSidecarCollapsed ? 'true' : undefined}>
          <DecisionViewport
            items={pendingDRItems}
            isLoading={pendingDRLoading}
            error={pendingDRError}
            onItemClick={setSelectedDRId}
          />
          <p-tabs ref={tabsRef}>
            <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Detail')}>
              <div ref={detailRef} data-tab-content="detail" aria-hidden="false">
                <PBanner
                  open={bannerError !== null}
                  heading={bannerError?.heading ?? ''}
                  description={bannerError?.description ?? ''}
                  state={bannerError?.state ?? 'error'}
                  onDismiss={() => setBannerError(null)}
                />
                {selectedTaskId === null
                  ? <div data-testid="detail-placeholder">Select a task to view details.</div>
                  : null}
                {detailValidationMessage !== null ? (
                  <div data-testid="validation-message" role="status">
                    {detailValidationMessage}
                  </div>
                ) : null}
                {selectedTaskId !== null && selectedTaskError !== null ? (
                  <div data-testid="task-fetch-error" role="status">
                    {selectedTaskError}
                    <PButton
                      type="button"
                      data-testid="task-fetch-retry"
                      variant="secondary"
                      onClick={() => update()}
                    >
                      Retry
                    </PButton>
                  </div>
                ) : null}
                <DetailTab
                  key={selectedTaskId ?? -1}
                  task={selectedTask}
                  board={board}
                  initialSubtab={selectedTaskSubtab}
                  onSelectTask={(taskId, subtab) => {
                    select(taskId)
                    setSelectedTaskSubtab((current) => subtab ?? current)
                  }}
                  onTaskCleared={(message) => {
                    clear()
                    setSelectedTaskSubtab(null)
                    setDetailValidationMessage(message ?? null)
                  }}
                  onTaskUpdated={(updatedTask) => {
                    const previousTask = selectedTask
                    update(updatedTask)
                    setDetailValidationMessage(null)
                    setBannerError(null)
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
                  onMutationError={(heading, description, state) => {
                    setBannerError({ heading, description, state })
                  }}
                />
              </div>
            </p-tabs-item>
            <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Activity')}>
              <div ref={activityRef} data-tab-content="activity" aria-hidden="true">
                <ActivityTab
                  onSelectTask={(taskId, subtab) => {
                    select(taskId)
                    setSelectedTaskSubtab(subtab ?? null)
                  }}
                />
              </div>
            </p-tabs-item>
          </p-tabs>
        </div>
      </aside>
      {selectedDR ? (
        <ResolveModal
          dr={selectedDR}
          onClose={() => setSelectedDRId(null)}
          onResolved={() => {
            void refetchPendingDRs()
            refetchTasks()
            setSelectedDRId(null)
          }}
        />
      ) : null}
      <div className="shell__contextual" data-region="contextual" />
    </div>
  )
}

export default Shell

