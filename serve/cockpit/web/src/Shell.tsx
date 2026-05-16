import { useRef, useEffect, useState } from 'react'
import { Routes, Route } from 'react-router'
import { PBanner, PButton, PDivider, PHeading } from '@porsche-design-system/components-react'
import KanbanBoard from './KanbanBoard'
import ActivityTab from './components/ActivityTab'
import CleanupPanel from './components/CleanupPanel'
import DecisionViewport from './components/DecisionViewport'
import DetailTab from './components/DetailTab'
import DRStatusIndicator from './components/DRStatusIndicator'
import HealthBadge, { type ScanItem as HealthBadgeItem } from './components/HealthBadge'
import RepairPanel from './components/RepairPanel'
import ResolveModal from './components/ResolveModal'
import ThemeToggle from './components/ThemeToggle'
import { useBoardState, useDRState, useTaskSelection } from './hooks/CockpitProvider'
import { type ScanItem as ScanPollingItem } from './hooks/useScanPolling'
import './Shell.css'

function isHealthBadgeItem(item: ScanPollingItem): item is HealthBadgeItem {
  return item.code !== null && item.detail !== null && item.file_path !== null
}

function setHeadingLargeSizeAttr(element: HTMLElement | null): void {
  if (!element) {
    return
  }
  element.setAttribute('size', 'large')
  element.setAttribute('tag', 'h2')
}

function setHeadingH1TagAttr(element: HTMLElement | null): void {
  element?.setAttribute('tag', 'h1')
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
  const selectedTaskHeading = selectedTask
    ? `${selectedTask.title || `#${selectedTask.id}`}`
    : selectedTaskId !== null
      ? `#${selectedTaskId}`
      : 'No task selected'
  const normalizedItems = scanItems.filter(isHealthBadgeItem)
  const statusHealth = scanError ? 'red' : health
  const [hasLoadedScan, setHasLoadedScan] = useState(false)
  const [isSidecarCollapsed, setIsSidecarCollapsed] = useState(false)
  const [isMobileViewport, setIsMobileViewport] = useState(false)
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
    pendingDRIds: new Set(pendingDRItems.map((dr) => dr.task_id)),
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

  const shellClassName = [
    'shell grid h-screen min-w-0 bg-[var(--p-color-canvas)] text-[var(--p-color-primary)]',
    "[font-family:'Porsche_Next','Arial_Narrow',Arial,sans-serif]",
    '[grid-template-columns:var(--shell-columns)] [grid-template-rows:var(--shell-rows)]',
    '[transition:grid-template-columns_250ms_ease]',
  ].join(' ')

  const statusBarClassName = [
    'shell__status-bar sticky top-0 z-10 flex min-h-14 items-center',
    'gap-[var(--p-spacing-static-sm)] border-b border-[var(--p-color-contrast-low)]',
    'bg-[var(--p-color-surface)] px-[var(--p-spacing-static-md)]',
    'max-[767px]:flex-wrap max-[767px]:gap-y-1 max-[767px]:py-1',
  ].join(' ')

  const navRailClassName = [
    'shell__nav-rail flex min-w-0 items-center overflow-x-hidden bg-[var(--p-color-surface)]',
    '[box-sizing:border-box] max-[767px]:flex-row max-[767px]:justify-start',
    'max-[767px]:border-b max-[767px]:border-[var(--p-color-contrast-low)]',
    'max-[767px]:px-[var(--p-spacing-static-md)] md:flex-col md:justify-start',
    'md:border-b-0 md:pt-[var(--p-spacing-static-sm)]',
  ].join(' ')

  const sidecarClassName = [
    'shell__sidecar min-w-0 overflow-hidden border-t border-[var(--p-color-contrast-low)]',
    'md:border-t-0 md:border-l md:border-[var(--p-color-contrast-low)]',
  ].join(' ')

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 767px)')
    const handleViewportChange = () => {
      setIsMobileViewport(window.innerWidth <= 767 || mediaQuery.matches)
    }

    handleViewportChange()
    mediaQuery.addEventListener('change', handleViewportChange)

    return () => {
      mediaQuery.removeEventListener('change', handleViewportChange)
    }
  }, [])

  useEffect(() => {
    const statusBar = document.querySelector<HTMLElement>('[data-region="status-bar"]')
    if (!statusBar) {
      return
    }

    const applyPdsExceptions = () => {
      // Record explicit exceptions for native <button> internals emitted by wrappers.
      statusBar
        .querySelectorAll<HTMLButtonElement>('button:not([data-pds])')
        .forEach((button) => {
          button.setAttribute('data-pds-exception', 'status-bar-wrapper')
        })
    }

    applyPdsExceptions()

    const observer = new MutationObserver(() => {
      applyPdsExceptions()
    })
    observer.observe(statusBar, { childList: true, subtree: true })

    return () => {
      observer.disconnect()
    }
  }, [])

  return (
    <div
      className={shellClassName}
      data-sidecar-collapsed={isSidecarCollapsed || undefined}
    >
      <header
        className={statusBarClassName}
        data-region="status-bar"
      >
        <PHeading ref={setHeadingH1TagAttr} className="shell__product-identity min-w-0 break-words">
          OwlBear Cockpit
        </PHeading>
        <span data-testid="traffic-light" data-health={statusHealth} />
        <span data-testid="task-count" />
        {hasLoadedScan && !scanError ? (
          <HealthBadge
            items={normalizedItems}
          />
        ) : null}
        {hasLoadedScan && !scanError ? (
          <RepairPanel
            corruptionCount={normalizedItems.length}
            files={normalizedItems}
            onSuccess={refetch}
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
        <ThemeToggle />
        {pendingDRError ? (
          <span data-testid="dr-polling-error" role="status">
            {pendingDRError.message}
          </span>
        ) : null}
      </header>
      <nav
        className={navRailClassName}
        data-region="nav-rail"
      >
        <PButton
          data-surface="kanban"
          tabIndex={0}
          aria-current="page"
          aria-label="Kanban"
          variant="secondary"
          className="shell__nav-button m-0 block w-10 min-w-0 max-w-10 overflow-hidden"
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 16 16"
            width="16"
            height="16"
            focusable="false"
          >
            <path d="M2 3h5v4H2V3zm7 0h5v4H9V3zM2 9h5v4H2V9zm7 0h5v4H9V9z" fill="currentColor" />
          </svg>
        </PButton>
      </nav>
      <main
        className="shell__workspace min-w-0 overflow-hidden md:overflow-auto"
        data-region="workspace"
        onClickCapture={() => {
          if (isMobileViewport && selectedTaskId === null && tasks.length === 1) {
            select(tasks[0].id)
            setDetailValidationMessage(null)
          }
        }}
      >
        <Routes>
          <Route path="/" element={<KanbanBoard {...kanbanProps} />} />
        </Routes>
      </main>
      <aside
        className={sidecarClassName}
        data-region="sidecar"
      >
        <button
          type="button"
          className="icon-button inline-flex items-center px-3 py-1"
          data-testid="sidecar-collapse"
          aria-expanded={!isSidecarCollapsed}
          aria-controls="shell-sidecar-content"
          onClick={() => setIsSidecarCollapsed((current) => !current)}
        >
          {isSidecarCollapsed ? 'Expand sidecar' : 'Collapse sidecar'}
        </button>
        {isMobileViewport ? (
          <p-sheet
            open={selectedTaskId !== null}
            className={selectedTaskId !== null
              ? [
                'shell__mobile-sheet fixed inset-x-0 bottom-0 z-20 block',
                'max-h-[min(70vh,560px)] overflow-auto border-t',
                'border-[var(--p-color-contrast-low)] bg-[var(--p-color-surface)] md:hidden',
              ].join(' ')
              : 'shell__mobile-sheet hidden md:hidden'}
          >
            <div
              id="shell-sidecar-content"
              className="p-[var(--p-spacing-static-md)]"
              aria-hidden={isSidecarCollapsed ? 'true' : undefined}
            >
              <section data-region="sidecar-header" aria-live="polite">
                <PHeading ref={setHeadingLargeSizeAttr} size="large">
                  {selectedTaskHeading}
                </PHeading>
              </section>
              <PDivider />
              <DecisionViewport
                items={pendingDRItems}
                isLoading={pendingDRLoading}
                error={pendingDRError}
                onItemClick={setSelectedDRId}
              />
              <PDivider />
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
          </p-sheet>
        ) : (
          <div
            id="shell-sidecar-content"
            className="p-[var(--p-spacing-static-md)]"
            aria-hidden={isSidecarCollapsed ? 'true' : undefined}
          >
            <section data-region="sidecar-header" aria-live="polite">
              <PHeading ref={setHeadingLargeSizeAttr} size="large">
                {selectedTaskHeading}
              </PHeading>
            </section>
            <PDivider />
            <DecisionViewport
              items={pendingDRItems}
              isLoading={pendingDRLoading}
              error={pendingDRError}
              onItemClick={setSelectedDRId}
            />
            <PDivider />
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
        )}
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
      <div className="shell__contextual hidden" data-region="contextual" />
    </div>
  )
}

export default Shell
