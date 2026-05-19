import { Suspense, useRef, useEffect, useState } from 'react'
import { Routes, Route, useLocation, useNavigate } from 'react-router'
import { AnimatePresence, motion } from 'framer-motion'
import {
  PBanner,
  PButton,
  PButtonPure,
  PDivider,
  PFlyout,
  PHeading,
  PIcon,
  PTabsBar,
  PToast,
  useToastManager,
} from '@porsche-design-system/components-react'
import type { IconName } from '@porsche-design-system/components-react'
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

const NAV_ICONS: Record<string, IconName> = {
  kanban: 'grid',
  decisions: 'document',
  memory: 'brain',
}

function normalizeRoutePath(path: string): string {
  if (path === '/') {
    return path
  }
  return path.replace(/\/+$/, '') || '/'
}

function Shell() {
  const location = useLocation()
  const { pathname } = location
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
  const [isMaintenanceOpen, setIsMaintenanceOpen] = useState(false)
  const [isMobileViewport, setIsMobileViewport] = useState(false)
  const [selectedTaskSubtab, setSelectedTaskSubtab] = useState<string | null>(null)
  const [detailValidationMessage, setDetailValidationMessage] = useState<string | null>(null)
  const [bannerError, setBannerError] = useState<{
    heading: string
    description: string
    state: 'error' | 'warning'
  } | null>(null)
  const tabsRef = useRef<HTMLElement>(null)
  const navTabsRef = useRef<HTMLElement>(null)
  const detailRef = useRef<HTMLDivElement>(null)
  const activityRef = useRef<HTMLDivElement>(null)
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

  // Compute active nav index from pathname
  const normalizedPathname = normalizeRoutePath(pathname)
  const activeNavIndex = routeConfig.findIndex(
    (route) => normalizeRoutePath(route.path) === normalizedPathname,
  )
  const matchedRoute = activeNavIndex >= 0 ? routeConfig[activeNavIndex] : undefined
  const hasSidecar = matchedRoute?.hasSidecar !== false

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

  useEffect(() => {
    const navTabs = navTabsRef.current
    if (!navTabs) return
    const onNavTabChange = (e: Event) => {
      const index = (e as CustomEvent<{ activeTabIndex: number }>).detail.activeTabIndex
      const route = routeConfig[index]
      if (route) {
        navigate(route.path)
      }
    }
    navTabs.addEventListener('tabChange', onNavTabChange)
    return () => navTabs.removeEventListener('tabChange', onNavTabChange)
  }, [navigate])

  // Sidecar width (no PDS utility exists for this specific clamp)
  const sidecarWidth = isSidecarCollapsed
    ? '48px'
    : 'clamp(320px, 24vw, 380px)'

  const gridCols = hasSidecar
    ? `grid-cols-[1fr_${sidecarWidth}]`
    : 'grid-cols-[1fr]'

  const mobileGridCols = hasSidecar
    ? 'max-md:grid-cols-[1fr] max-md:grid-rows-[auto_auto_1fr_minmax(0,0.7fr)]'
    : 'max-md:grid-cols-[1fr] max-md:grid-rows-[auto_auto_1fr]'

  return (
    <div
      className={[
        'shell grid h-screen min-w-0 grid-rows-[auto_auto_1fr] bg-canvas text-primary',
        "font-[family-name:'Porsche_Next','Arial_Narrow',Arial,sans-serif]",
        gridCols,
        mobileGridCols,
        'transition-[grid-template-columns] duration-sm',
      ].join(' ')}
      data-sidecar-collapsed={isSidecarCollapsed || undefined}
      data-no-sidecar={!hasSidecar || undefined}
    >
      <PToast />

      {/* ─── Header ──────────────────────────────────────────────────────────── */}
      <header
        className={[
          'col-span-full flex min-h-14 items-center justify-between',
          'gap-static-md border-b border-contrast-low bg-surface px-static-md',
          'max-md:flex-wrap max-md:items-start max-md:gap-y-2 max-md:py-2',
        ].join(' ')}
        data-region="status-bar"
      >
        <div className="flex items-baseline gap-static-sm min-w-0">
          <PHeading
            ref={syncHeadingTagAttr('h1', 'medium')}
            size="medium"
            tag="h1"
            className="min-w-0 break-words"
          >
            OwlBear Cockpit
          </PHeading>
        </div>

        <div className="flex flex-1 items-center justify-end gap-static-md" aria-label="Cockpit status and actions">
          {/* Status cluster */}
          <div className="flex items-center gap-static-xs border-r border-contrast-low pr-static-sm" aria-label="System status">
            <span
              className={[
                'size-2.5 flex-none rounded-full',
                statusHealth === 'red' ? 'bg-[var(--p-color-error)] shadow-[0_0_0_3px_var(--p-color-error-low)]' :
                statusHealth === 'yellow' ? 'bg-[var(--p-color-warning)] shadow-[0_0_0_3px_var(--p-color-warning-low)]' :
                'bg-[var(--p-color-success)] shadow-[0_0_0_3px_var(--p-color-success-low)]',
              ].join(' ')}
              data-testid="traffic-light"
              data-health={statusHealth}
            />
            <span
              className="whitespace-nowrap rounded-full border border-contrast-low bg-[var(--p-color-frosted-soft)] px-2 py-0.5 text-xs font-semibold"
              data-testid="task-count"
            >
              {tasks.length} tasks
            </span>
            {hasLoadedScan && !scanError ? (
              <HealthBadge items={normalizedItems} />
            ) : null}
            {scanError ? (
              <span className="text-xs text-[var(--p-color-error)] whitespace-nowrap" data-testid="scan-error" data-health="error" role="status">
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

          {/* Maintenance action */}
          <div className="relative flex items-center gap-static-xs border-r border-contrast-low pr-static-sm" aria-label="Maintenance actions">
            <PButtonPure
              type="button"
              icon="wrench"
              hideLabel
              data-testid="maintenance-menu-toggle"
              aria-label="Maintenance actions"
              aria-expanded={isMaintenanceOpen}
              aria-controls="shell-maintenance-menu"
              onClick={() => setIsMaintenanceOpen((c) => !c)}
            >
              Maintenance
            </PButtonPure>
            {normalizedItems.length > 0 ? (
              <span className="absolute -top-1 -right-1 inline-flex size-4 items-center justify-center rounded-full bg-[var(--p-color-warning)] text-[10px] font-semibold leading-none border border-surface" aria-hidden="true">
                {normalizedItems.length}
              </span>
            ) : null}
            <PFlyout
              open={isMaintenanceOpen}
              onDismiss={() => setIsMaintenanceOpen(false)}
              aria-label="Maintenance actions"
            >
              <div
                id="shell-maintenance-menu"
                data-testid="maintenance-menu"
                className="flex flex-col gap-static-sm p-static-sm"
              >
                <div className="flex items-center justify-between text-xs font-semibold uppercase text-contrast-high">
                  <span>Maintenance</span>
                  <span>{normalizedItems.length > 0 ? `${normalizedItems.length} issues` : 'Ready'}</span>
                </div>
                <div className="flex flex-col gap-static-xs">
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
            </PFlyout>
          </div>

          {/* Theme toggle */}
          <div className="flex items-center" aria-label="View settings">
            <ThemeToggle />
          </div>

          {pendingDRError ? (
            <span className="text-xs text-[var(--p-color-error)]" data-testid="dr-polling-error" role="status">
              {pendingDRError.message}
            </span>
          ) : null}
        </div>
      </header>

      {/* ─── Navigation Bar ──────────────────────────────────────────────────── */}
      <nav
        className="col-span-full flex items-center bg-surface border-b border-contrast-low px-static-md"
        data-region="nav-rail"
        role="navigation"
        aria-label="Workspaces"
      >
        <div aria-label="Workspace switcher">
          <PTabsBar
            ref={navTabsRef}
            activeTabIndex={activeNavIndex >= 0 ? activeNavIndex : 0}
          >
            {routeConfig.map((route) => {
              const isActive = normalizedPathname === normalizeRoutePath(route.path)
              const isDecisions = route.icon === 'decisions'
              const badgeCount = isDecisions ? pendingDRCount : 0
              const label = isDecisions && badgeCount > 0
                ? `${route.label} (${badgeCount} pending)`
                : route.label
              return (
                <button
                  key={route.path}
                  type="button"
                  data-surface={route.icon}
                  data-pds-exception={`nav-${route.icon}`}
                  aria-current={isActive ? 'page' : undefined}
                  aria-label={label}
                  onClick={() => navigate(route.path)}
                >
                  <PIcon
                    name={NAV_ICONS[route.icon] || 'grid'}
                    size="small"
                    className="mr-static-xs"
                    aria-hidden="true"
                  />
                  {route.label}
                  {isDecisions && badgeCount > 0 ? (
                    <span
                      data-testid="nav-badge"
                      className="ml-static-xs inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-error px-1 text-[0.65rem] font-bold leading-none text-canvas"
                    >
                      {badgeCount}
                    </span>
                  ) : null}
                </button>
              )
            })}
          </PTabsBar>
        </div>
      </nav>

      {/* ─── Main Workspace ──────────────────────────────────────────────────── */}
      <main
        className="min-w-0 overflow-auto bg-canvas"
        data-region="workspace"
        onClickCapture={() => {
          if (isMobileViewport && selectedTaskId === null && tasks.length === 1) {
            select(tasks[0].id)
            setDetailValidationMessage(null)
          }
        }}
      >
        <Suspense fallback={<div data-testid="route-loading" />}>
          <AnimatePresence mode="wait">
            {matchedRoute ? (
              <motion.div
                key={pathname}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
                className="flex min-h-0 flex-1 flex-col"
              >
                <Routes location={location}>
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
              </motion.div>
            ) : null}
          </AnimatePresence>
        </Suspense>
      </main>

      {/* ─── Sidecar Inspector ───────────────────────────────────────────────── */}
      {hasSidecar ? (
        <motion.aside
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
          className="relative min-w-0 border-l border-contrast-low bg-surface max-md:border-l-0 max-md:border-t"
          data-region="sidecar"
        >
          {/* Collapse toggle (desktop only) */}
          <button
            type="button"
            className={[
              'absolute top-1/2 -left-8 z-10 -translate-y-1/2',
              'inline-flex h-18 w-8 items-center justify-center',
              'rounded-l-full border-r-0 bg-surface shadow-sm',
              'text-primary transition-all duration-sm',
              'hover:bg-[var(--p-color-frosted-soft)] hover:shadow-md hover:-translate-x-0.5 hover:-translate-y-1/2',
              'max-md:hidden',
            ].join(' ')}
            data-testid="sidecar-collapse"
            data-sidecar-state={isSidecarCollapsed ? 'collapsed' : 'expanded'}
            aria-expanded={!isSidecarCollapsed}
            aria-label={isSidecarCollapsed ? 'Show inspector' : 'Hide inspector'}
            title={isSidecarCollapsed ? 'Show inspector' : 'Hide inspector'}
            aria-controls="shell-sidecar-content"
            onClick={() => setIsSidecarCollapsed((current) => !current)}
          >
            <PIcon
              name={isSidecarCollapsed ? 'arrow-compact-right' : 'arrow-last'}
              size="small"
              aria-hidden="true"
            />
          </button>

          {isMobileViewport ? (
            <p-sheet
              open
              className="fixed inset-x-0 bottom-0 z-20 block max-h-[min(70vh,560px)] overflow-auto border-t border-contrast-low bg-surface md:hidden"
            >
              <div
                id="shell-sidecar-content"
                className="p-static-md"
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
              className="box-border h-full overflow-x-hidden overflow-y-auto p-static-md"
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
        </motion.aside>
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
      <div className="hidden" data-region="contextual" />
    </div>
  )
}

export default Shell
