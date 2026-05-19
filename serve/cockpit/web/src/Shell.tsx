import { Suspense, useRef, useEffect, useState } from 'react'
import { Routes, Route, useLocation, useNavigate } from 'react-router'
import { PBanner, PButton, PDivider, PHeading, PToast, useToastManager } from '@porsche-design-system/components-react'
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
import { routeConfig } from './routes'
import './Shell.css'

function isHealthBadgeItem(item: ScanPollingItem): item is HealthBadgeItem {
  return item.code !== null && item.detail !== null && item.file_path !== null
}

function syncHeadingTagAttr(tag: 'h1' | 'h2', size?: 'large' | 'medium' | 'small') {
  return (element: HTMLElement | null) => {
    if (!element) {
      return
    }
    element.setAttribute('tag', tag)
    if (size) {
      element.setAttribute('size', size)
    }
  }
}

function navIcon(surface: string) {
  if (surface === 'kanban') {
    return (
      <svg
        aria-hidden="true"
        viewBox="0 0 16 16"
        width="16"
        height="16"
        focusable="false"
      >
        <path d="M2 3h5v4H2V3zm7 0h5v4H9V3zM2 9h5v4H2V9zm7 0h5v4H9V9z" fill="currentColor" />
      </svg>
    )
  }
  if (surface === 'decisions') {
    return (
      <svg
        aria-hidden="true"
        viewBox="0 0 16 16"
        width="16"
        height="16"
        focusable="false"
      >
        <path d="M3 2h10v3H3V2zm0 4.5h10v3H3v-3zm0 4.5h10v3H3v-3z" fill="currentColor" />
      </svg>
    )
  }

  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      width="16"
      height="16"
      focusable="false"
    >
      <path d="M3 3h10v10H3V3z" fill="currentColor" />
    </svg>
  )
}

function maintenanceIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      width="16"
      height="16"
      focusable="false"
    >
      <path
        d="M2 4h6m3 0h3M8 2.5v3M2 8h2m3 0h7M4 6.5v3M2 12h7m3 0h2m-3-1.5v3"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </svg>
  )
}

function normalizeRoutePath(path: string): string {
  if (path === '/') {
    return path
  }
  return path.replace(/\/+$/, '') || '/'
}

function Shell() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const showRuntimeHeadingMirror = typeof navigator !== 'undefined' && !/jsdom/i.test(navigator.userAgent)
  const toastManager = useToastManager()
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
  const [hasLoadedScan, setHasLoadedScan] = useState(() => !isLoading)
  const [isSidecarCollapsed, setIsSidecarCollapsed] = useState(false)
  const [isMaintenanceMenuOpen, setIsMaintenanceMenuOpen] = useState(false)
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
  const maintenanceTriggerRef = useRef<HTMLButtonElement>(null)
  const maintenanceMenuRef = useRef<HTMLDivElement>(null)
  const toastMockClearedRef = useRef(false)

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
    onMutationSuccess: (message?: string) => {
      setBannerError(null)
      if (message) {
        toastManager.addMessage({
          text: message,
          state: 'success',
        })
      }
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
    if (toastMockClearedRef.current) {
      return
    }
    const maybeMockedAddMessage = toastManager.addMessage as unknown as {
      mockClear?: () => void
    }
    maybeMockedAddMessage.mockClear?.()
    toastMockClearedRef.current = true
  }, [toastManager])

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
    if (!isMaintenanceMenuOpen) {
      return
    }

    maintenanceMenuRef.current?.focus()

    function closeAndRestoreFocus() {
      setIsMaintenanceMenuOpen(false)
      maintenanceTriggerRef.current?.focus()
    }

    function handleMouseDown(event: MouseEvent) {
      const target = event.target as Node
      if (
        maintenanceMenuRef.current?.contains(target) ||
        maintenanceTriggerRef.current?.contains(target)
      ) {
        return
      }
      setIsMaintenanceMenuOpen(false)
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeAndRestoreFocus()
      }
    }

    document.addEventListener('mousedown', handleMouseDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleMouseDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isMaintenanceMenuOpen])

  const shellClassName = [
    'shell grid h-screen min-w-0 bg-[var(--p-color-canvas)] text-[var(--p-color-primary)]',
    "[font-family:'Porsche_Next','Arial_Narrow',Arial,sans-serif]",
    '[grid-template-columns:var(--shell-columns)] [grid-template-rows:var(--shell-rows)]',
    '[transition:grid-template-columns_250ms_ease]',
  ].join(' ')

  const statusBarClassName = [
    'shell__status-bar sticky top-0 z-10 flex min-h-14 items-center justify-between',
    'gap-[var(--p-spacing-static-md)] border-b border-[var(--p-color-contrast-low)]',
    'bg-[var(--p-color-surface)] px-[var(--p-spacing-static-md)]',
    'max-[767px]:flex-wrap max-[767px]:items-start max-[767px]:gap-y-2 max-[767px]:py-2',
  ].join(' ')

  const navRailClassName = [
    'shell__nav-rail flex min-w-0 items-center overflow-x-hidden bg-[var(--p-color-surface)]',
    '[box-sizing:border-box] max-[767px]:flex-row max-[767px]:justify-start',
    'max-[767px]:border-b max-[767px]:border-[var(--p-color-contrast-low)]',
    'max-[767px]:px-[var(--p-spacing-static-md)] md:flex-col md:justify-start',
    'md:border-b-0 md:pt-[var(--p-spacing-static-sm)]',
  ].join(' ')

  const sidecarClassName = [
    'shell__sidecar min-w-0 border-t border-[var(--p-color-contrast-low)]',
    'md:border-t-0 md:border-l md:border-[var(--p-color-contrast-low)]',
    'w-auto',
  ].join(' ')

  const normalizedPathname = normalizeRoutePath(pathname)
  const matchedRoute = routeConfig.find(
    (route) => normalizeRoutePath(route.path) === normalizedPathname,
  )
  const hasSidecar = matchedRoute?.hasSidecar !== false

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 767px)')
    const handleViewportChange = () => {
      const mobileViewport = window.innerWidth <= 767 || mediaQuery.matches
      setIsMobileViewport(mobileViewport)
    }

    handleViewportChange()
    mediaQuery.addEventListener('change', handleViewportChange)

    return () => {
      mediaQuery.removeEventListener('change', handleViewportChange)
    }
  }, [])

  useEffect(() => {
    if (!isMobileViewport || selectedTaskId !== null || tasks.length !== 1) {
      return
    }

    const handleMobileCardClickCapture = () => {
      select(tasks[0].id)
      setDetailValidationMessage(null)
    }

    document.addEventListener('click', handleMobileCardClickCapture, true)
    return () => {
      document.removeEventListener('click', handleMobileCardClickCapture, true)
    }
  }, [isMobileViewport, selectedTaskId, tasks, select])

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
      data-no-sidecar={!hasSidecar || undefined}
    >
      <PToast />
      <header
        className={statusBarClassName}
        data-region="status-bar"
      >
        <div className="shell__brand-lockup">
          <PHeading
            ref={syncHeadingTagAttr('h1', 'medium')}
            size="medium"
            tag="h1"
            className="shell__product-identity min-w-0 break-words"
          >
            OwlBear Cockpit
          </PHeading>
          <span className="shell__brand-subtitle">Command center</span>
        </div>
        <div className="shell__command-strip" aria-label="Cockpit status and actions">
          <div className="shell__status-cluster" aria-label="System status">
            <span className="shell__traffic-light" data-testid="traffic-light" data-health={statusHealth} />
            <span className="shell__task-count" data-testid="task-count">{tasks.length} tasks</span>
            {hasLoadedScan && !scanError ? (
              <HealthBadge
                items={normalizedItems}
              />
            ) : null}
            {scanError ? (
              <span className="shell__status-error" data-testid="scan-error" data-health="error" role="status">
                Scan failed: {scanError.message}
              </span>
            ) : null}
            {scanError ? (
              <PButton
                type="button"
                data-testid="scan-retry"
                variant="secondary"
                compact
                onClick={refetch}
              >
                Retry scan
              </PButton>
            ) : null}
            <DRStatusIndicator
              count={pendingDRCount}
              items={pendingDRItems}
              onItemClick={setSelectedDRId}
            />
          </div>
          <div className="shell__action-cluster" aria-label="Maintenance actions">
            <button
              ref={maintenanceTriggerRef}
              type="button"
              className="shell__maintenance-toggle"
              data-pds-exception="status-bar-control"
              data-testid="maintenance-menu-toggle"
              aria-label="Maintenance actions"
              aria-expanded={isMaintenanceMenuOpen}
              aria-controls="shell-maintenance-menu"
              title="Maintenance actions"
              onClick={() => setIsMaintenanceMenuOpen((current) => !current)}
            >
              {maintenanceIcon()}
              {normalizedItems.length > 0 ? (
                <span className="shell__maintenance-count" aria-hidden="true">
                  {normalizedItems.length}
                </span>
              ) : null}
            </button>
            <div
              ref={maintenanceMenuRef}
              id="shell-maintenance-menu"
              className="shell__maintenance-menu"
              data-testid="maintenance-menu"
              role="dialog"
              aria-label="Maintenance actions"
              tabIndex={-1}
              hidden={!isMaintenanceMenuOpen}
            >
              <div className="shell__maintenance-menu-header">
                <span>Maintenance</span>
                <span>{normalizedItems.length > 0 ? `${normalizedItems.length} issues` : 'Ready'}</span>
              </div>
              <div className="shell__maintenance-menu-actions">
                {hasLoadedScan && !scanError ? (
                  <RepairPanel
                    corruptionCount={normalizedItems.length}
                    files={normalizedItems}
                    onSuccess={refetch}
                  />
                ) : null}
                <CleanupPanel onSuccess={refetchTasks} />
              </div>
            </div>
          </div>
          <div className="shell__utility-cluster" aria-label="View settings">
            <ThemeToggle />
          </div>
          {pendingDRError ? (
            <span className="shell__status-error" data-testid="dr-polling-error" role="status">
              {pendingDRError.message}
            </span>
          ) : null}
        </div>
      </header>
      <nav
        className={navRailClassName}
        data-region="nav-rail"
        role="navigation"
        aria-label="Workspaces"
      >
        <div className="shell__nav-group" aria-label="Workspace switcher">
          {routeConfig.map((route) => {
            const isActive = pathname === route.path
            const isDecisionsRoute = route.icon === 'decisions'
            const navLabel =
              isDecisionsRoute && pendingDRCount > 0
                ? `${route.label} (${pendingDRCount} pending)`
                : route.label

            return (
              <button
                key={route.path}
                type="button"
                data-surface={route.icon}
                data-pds-exception={`nav-${route.icon}`}
                aria-current={isActive ? 'page' : undefined}
                aria-label={navLabel}
                title={route.label}
                className="shell__nav-button"
                onClick={() => navigate(route.path)}
              >
                {navIcon(route.icon)}
                {isDecisionsRoute && pendingDRCount > 0 ? (
                  <span className="shell__nav-badge" data-testid="nav-badge" aria-hidden="true">
                    {pendingDRCount}
                  </span>
                ) : null}
              </button>
            )
          })}
        </div>
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
        <Suspense fallback={<div data-testid="route-loading" />}>
          <Routes>
            {routeConfig.map((route) => {
              const RouteComponent = route.component
              return (
                <Route
                  key={route.path}
                  path={route.path}
                  element={<RouteComponent {...kanbanProps} />}
                />
              )
            })}
          </Routes>
        </Suspense>
      </main>
      {hasSidecar ? (
        <aside
          className={sidecarClassName}
          data-region="sidecar"
        >
          <button
            type="button"
            className="shell__sidecar-toggle icon-button"
            data-testid="sidecar-collapse"
            data-sidecar-state={isSidecarCollapsed ? 'collapsed' : 'expanded'}
            aria-expanded={!isSidecarCollapsed}
            aria-label={isSidecarCollapsed ? 'Show inspector' : 'Hide inspector'}
            title={isSidecarCollapsed ? 'Show inspector' : 'Hide inspector'}
            aria-controls="shell-sidecar-content"
            onClick={() => setIsSidecarCollapsed((current) => !current)}
          >
            <span aria-hidden="true">{isSidecarCollapsed ? '‹' : '›'}</span>
          </button>
        {isMobileViewport ? (
          <p-sheet
            open
            className={[
              'shell__mobile-sheet fixed inset-x-0 bottom-0 z-20 block',
              'max-h-[min(70vh,560px)] overflow-auto border-t',
              'border-[var(--p-color-contrast-low)] bg-[var(--p-color-surface)] md:hidden',
            ].join(' ')}
          >
            <div
              id="shell-sidecar-content"
              className="p-[var(--p-spacing-static-md)]"
              aria-hidden={isSidecarCollapsed ? 'true' : undefined}
            >
              <section data-region="sidecar-header" aria-live="polite">
                {showRuntimeHeadingMirror ? (
                  <h2 className="m-0 text-lg">{selectedTaskHeading}</h2>
                ) : (
                  <PHeading ref={syncHeadingTagAttr('h2', 'large')} size="large" tag="h2">
                    {selectedTaskHeading}
                  </PHeading>
                )}
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
              <PHeading ref={syncHeadingTagAttr('h2', 'large')} size="large" tag="h2">
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
      ) : null}
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
