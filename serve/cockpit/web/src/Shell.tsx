import { Suspense, useRef, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { AnimatePresence, motion } from 'framer-motion'
import {
  PBanner,
  PButton,
  PButtonPure,
  PDivider,
  PFlyout,
  PHeading,
  PIcon,
  PSheet,
  PToast,
  useToastManager,
} from '@porsche-design-system/components-react'
import type { IconName } from '@porsche-design-system/components-react'
import ActivityTab from './components/ActivityTab'
import CleanupPanel from './components/CleanupPanel'
import DetailTab from './components/DetailTab'
import DRStatusIndicator from './components/DRStatusIndicator'
import HealthBadge, { type ScanItem as HealthBadgeItem } from './components/HealthBadge'
import RepairPanel from './components/RepairPanel'
import ResolveModal from './components/ResolveModal'
import ThemeToggle from './components/ThemeToggle'
import { useBoardState, useDRState, useTaskSelection } from './hooks/CockpitProvider'
import { usePendingMemoryCount } from './hooks/usePendingMemoryCount'
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
  const toastManagerRef = useRef(toastManager)
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
    error: pendingDRError,
    refetch: refetchPendingDRs,
    setSelectedDRId,
    selectedDR,
  } = useDRState()
  const { count: pendingMemoryCount } = usePendingMemoryCount()
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
  const detailRef = useRef<HTMLDivElement>(null)
  const activityRef = useRef<HTMLDivElement>(null)
  const toastMockClearedRef = useRef(false)

  const kanbanProps = useMemo(
    () => ({
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
          toastManagerRef.current.addMessage({
            text: message,
            state: 'success',
          })
        }
      },
      selectedId: selectedTaskId,
      pendingDRIds: new Set(pendingDRItems.map((dr) => dr.task_id)),
    }),
    [board, error, loading, pendingDRItems, refetchTasks, select, selectedTaskId, tasks],
  )

  // Compute active nav index from pathname
  const normalizedPathname = normalizeRoutePath(pathname)
  const activeNavIndex = routeConfig.findIndex(
    (route) => normalizeRoutePath(route.path) === normalizedPathname,
  )
  const matchedRoute = activeNavIndex >= 0 ? routeConfig[activeNavIndex] : undefined
  const MatchedRouteComponent = matchedRoute?.component
  const hasSidecar = matchedRoute?.hasSidecar !== false
  const isTaskInspectorOpen = hasSidecar && selectedTaskId !== null
  const routeElement = useMemo(
    () => (MatchedRouteComponent ? <MatchedRouteComponent {...kanbanProps} /> : null),
    [MatchedRouteComponent, kanbanProps],
  )

  useEffect(() => {
    if (!isLoading) {
      setHasLoadedScan(true)
    }
  }, [isLoading])

  useEffect(() => {
    toastManagerRef.current = toastManager
  }, [toastManager])

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

  const shellColumnsClass = !hasSidecar || !isTaskInspectorOpen
    ? 'md:[grid-template-columns:220px_minmax(0,1fr)_0px]'
    : isSidecarCollapsed
      ? 'md:[grid-template-columns:220px_minmax(0,1fr)_48px]'
      : 'md:[grid-template-columns:220px_minmax(0,1fr)_clamp(320px,24vw,380px)]'

  return (
    <div
      className={[
        'shell grid h-screen min-w-0 bg-canvas font-sans text-primary',
        'grid-rows-[auto_auto_minmax(0,1fr)] md:grid-rows-[auto_minmax(0,1fr)]',
        'transition-[grid-template-columns] duration-sm',
        shellColumnsClass,
      ].join(' ')}
      data-sidecar-collapsed={isSidecarCollapsed || undefined}
      data-no-sidecar={!hasSidecar || undefined}
    >
      <PToast />

      {/* ─── Header ──────────────────────────────────────────────────────────── */}
      <header
        className={[
          'sticky top-0 z-20 col-span-full grid min-h-14 min-w-0',
          'grid-cols-[minmax(0,1fr)_auto] items-center gap-static-sm',
          'border-b border-contrast-low bg-surface px-static-md py-static-sm',
        ].join(' ')}
        data-region="status-bar"
      >
        <h1 className="m-0 min-w-0 truncate text-sm font-semibold leading-tight text-primary">
          <a
            href="/"
            className="focus-text block truncate text-primary no-underline"
            onClick={(event) => {
              event.preventDefault()
              navigate('/')
            }}
          >
            OwlBear Cockpit
          </a>
        </h1>

        <div className="flex min-w-0 items-center justify-end gap-static-sm max-md:gap-static-xs" aria-label="Cockpit status and actions">
          {/* Status cluster */}
          <div className="flex min-w-0 items-center gap-static-xs border-r border-contrast-low pr-static-sm max-md:pr-static-xs" aria-label="System status">
            <span
              className={[
                'size-2.5 flex-none rounded-full',
                statusHealth === 'red' ? 'bg-error ring-3 ring-error-low' :
                statusHealth === 'yellow' ? 'bg-warning ring-3 ring-warning-low' :
                'bg-success ring-3 ring-success-low',
              ].join(' ')}
              data-testid="traffic-light"
              data-health={statusHealth}
            />
            <span
              className="hidden whitespace-nowrap rounded-full border border-contrast-low bg-frosted-soft px-2 py-0.5 text-xs font-semibold sm:inline-flex"
              data-testid="task-count"
            >
              {tasks.length} tasks
            </span>
            {hasLoadedScan && !scanError ? (
              <span className="hidden sm:inline-flex">
                <HealthBadge items={normalizedItems} />
              </span>
            ) : null}
            {scanError ? (
              <span className="text-xs text-error whitespace-nowrap" data-testid="scan-error" data-health="error" role="status">
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

          {isMobileViewport ? (
            <div className="flex min-w-0 items-center border-r border-contrast-low pr-static-xs" aria-label="Cleanup actions">
              <CleanupPanel compact onSuccess={refetchTasks} />
            </div>
          ) : (
            <div className="relative flex min-w-0 items-center gap-static-xs border-r border-contrast-low pr-static-sm" aria-label="Maintenance actions">
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
                <span className="absolute -top-1 -right-1 inline-flex size-4 items-center justify-center rounded-full bg-warning text-[10px] font-semibold leading-none border border-surface" aria-hidden="true">
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
                  </div>
                </div>
              </PFlyout>
              <CleanupPanel onSuccess={refetchTasks} />
            </div>
          )}

          {/* Theme toggle */}
          <div className="flex items-center" aria-label="View settings">
            <ThemeToggle compact={isMobileViewport} />
          </div>

          {pendingDRError ? (
            <span className="text-xs text-error" data-testid="dr-polling-error" role="status">
              {pendingDRError.message}
            </span>
          ) : null}
        </div>
      </header>

      {/* ─── Navigation Bar ──────────────────────────────────────────────────── */}
      <nav
        className={[
          'z-10 flex min-w-0 border-b border-contrast-low bg-surface px-static-sm py-static-xs',
          'md:col-start-1 md:row-start-2 md:min-h-0 md:flex-col md:gap-static-md',
          'md:border-b-0 md:border-r md:p-static-md',
        ].join(' ')}
        data-region="nav-rail"
        role="navigation"
        aria-label="Workspaces"
      >
        <div className="flex min-w-0 gap-static-xs overflow-x-auto md:flex-col md:overflow-visible" aria-label="Workspace switcher">
          {routeConfig.map((route) => {
            const isActive = normalizedPathname === normalizeRoutePath(route.path)
            const isDecisions = route.icon === 'decisions'
            const isMemory = route.icon === 'memory'
            const badgeCount = isDecisions ? pendingDRCount : isMemory ? pendingMemoryCount : 0
            const label = badgeCount > 0
              ? `${route.label} (${badgeCount} pending)`
              : route.label
            return (
              <button
                key={route.path}
                type="button"
                className={[
                  'focus-text relative inline-flex h-10 min-w-10 flex-none items-center justify-center',
                  'gap-static-xs rounded-full border px-static-sm text-sm font-semibold leading-none',
                  'transition-colors duration-sm md:w-full md:justify-start md:px-static-md',
                  isActive
                    ? 'border-primary bg-primary text-canvas'
                    : 'border-transparent bg-frosted-soft text-primary hover:bg-frosted',
                ].join(' ')}
                data-surface={route.icon}
                data-pds-exception={`nav-${route.icon}`}
                aria-current={isActive ? 'page' : undefined}
                aria-label={label}
                onClick={() => navigate(route.path)}
              >
                <PIcon
                  name={NAV_ICONS[route.icon] || 'grid'}
                  color="inherit"
                  size="small"
                  aria-hidden="true"
                />
                <span className="max-sm:sr-only">{route.label}</span>
                {badgeCount > 0 ? (
                  <span
                    data-testid="nav-badge"
                    className={[
                      'inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1',
                      'text-[0.65rem] font-bold leading-none',
                      isActive ? 'bg-surface text-primary' : 'bg-error text-canvas',
                    ].join(' ')}
                  >
                    {badgeCount}
                  </span>
                ) : null}
              </button>
            )
          })}
        </div>
      </nav>

      {/* ─── Main Workspace ──────────────────────────────────────────────────── */}
      <main
        className="min-w-0 overflow-auto bg-canvas md:col-start-2 md:row-start-2"
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
            {routeElement ? (
              <motion.div
                key={pathname}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
                className="flex min-h-0 flex-1 flex-col"
              >
                {routeElement}
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
          className={[
            'contents',
            'md:relative md:col-start-3 md:row-start-2 md:block md:min-w-0 md:overflow-hidden',
            'md:border-l md:border-contrast-low md:bg-surface',
            isTaskInspectorOpen ? '' : 'md:pointer-events-none md:border-l-0',
          ].join(' ')}
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
              'hover:bg-frosted-soft hover:shadow-md hover:-translate-x-0.5 hover:-translate-y-1/2',
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
            <PSheet
              open={isTaskInspectorOpen}
              onDismiss={() => {
                clear()
                setSelectedTaskSubtab(null)
                setDetailValidationMessage(null)
              }}
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
            </PSheet>
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
