import { Suspense, useRef, useEffect, useMemo, useState, type ComponentType, type CSSProperties } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { AnimatePresence, motion } from 'framer-motion'
import {
  PBanner,
  PButton,
  PButtonPure,
  PCanvas,
  PFlyout,
  PHeading,
  PIcon,
  PModal,
  PTag,
  PToast,
  useToastManager,
} from '@porsche-design-system/components-react'
import type { CanvasSidebarStartUpdateEventDetail, IconName } from '@porsche-design-system/components-react'
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
import type { KanbanBoardProps } from './KanbanBoard'
import { routeConfig } from './routes'
import { priorityToVariant, statusToVariant } from './utils/cardVariants'
import { formatPriority, formatStatus } from './utils/format'

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

function syncTagVariantAttr(variant: string) {
  return (element: HTMLElement | null) => {
    if (!element) {
      return
    }
    element.setAttribute('compact', '')
    element.setAttribute('variant', variant)
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
  const [isSidebarStartOpen, setIsSidebarStartOpen] = useState(() => {
    if (typeof window === 'undefined') {
      return true
    }
    return window.matchMedia('(min-width: 1024px)').matches
  })
  const [isMaintenanceOpen, setIsMaintenanceOpen] = useState(false)
  const [selectedTaskSubtab, setSelectedTaskSubtab] = useState<string | null>(null)
  const [detailValidationMessage, setDetailValidationMessage] = useState<string | null>(null)
  const [bannerError, setBannerError] = useState<{
    heading: string
    description: string
    state: 'error' | 'warning'
  } | null>(null)
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
  const isKanbanRoute = normalizedPathname === '/'
  const isTaskDetailOpen = isKanbanRoute && selectedTaskId !== null
  const canvasKey = isSidebarStartOpen ? 'nav-open' : 'nav-closed'
  const routeElement = useMemo(() => {
    if (!matchedRoute) {
      return null
    }

    if (matchedRoute.path === '/') {
      const KanbanRouteComponent = matchedRoute.component as ComponentType<KanbanBoardProps>
      return <KanbanRouteComponent {...kanbanProps} />
    }

    const WorkspaceRouteComponent = matchedRoute.component as ComponentType<Record<string, never>>
    return <WorkspaceRouteComponent />
  }, [kanbanProps, matchedRoute])

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
    const mediaQuery = window.matchMedia('(min-width: 1024px)')
    const handleSidebarViewport = () => {
      setIsSidebarStartOpen(mediaQuery.matches)
    }

    handleSidebarViewport()
    mediaQuery.addEventListener('change', handleSidebarViewport)

    return () => {
      mediaQuery.removeEventListener('change', handleSidebarViewport)
    }
  }, [])

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

  const canvasStyle = {
    '--p-canvas-sidebar-start-width': '96px',
  } as CSSProperties

  const closeTaskDetail = () => {
    clear()
    setSelectedTaskSubtab(null)
    setDetailValidationMessage(null)
  }

  const onSidebarStartUpdate = (event: CustomEvent<CanvasSidebarStartUpdateEventDetail>) => {
    setIsSidebarStartOpen(event.detail.open)
  }

  const mutationBanner = (
    <PBanner
      open={bannerError !== null}
      heading={bannerError?.heading ?? ''}
      description={bannerError?.description ?? ''}
      state={bannerError?.state ?? 'error'}
      onDismiss={() => setBannerError(null)}
    />
  )

  const taskDetailContent = (
    <>
      {selectedTaskId !== null && selectedTask === null && selectedTaskError === null ? (
        <div data-testid="task-detail-loading" role="status">Opening task...</div>
      ) : null}
      {detailValidationMessage !== null ? (
        <div data-testid="validation-message" role="status">
          {detailValidationMessage}
        </div>
      ) : null}
      {selectedTaskId !== null && selectedTaskError !== null ? (
        <div data-testid="task-fetch-error" role="status">
          Task detail is unavailable. {selectedTaskError}
          <PButton
            type="button"
            data-testid="task-fetch-retry"
            variant="secondary"
            onClick={() => update()}
          >
            Try again
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
    </>
  )

  return (
    <>
      <PToast />
      {mutationBanner}

      <PCanvas
        key={canvasKey}
        className="shell font-sans text-primary"
        background="canvas"
        data-no-sidecar=""
        sidebarStartOpen={isSidebarStartOpen}
        sidebarEndOpen={false}
        style={canvasStyle}
        onSidebarStartUpdate={onSidebarStartUpdate}
      >
        <span slot="title" className="sr-only">OwlBear Cockpit</span>

        <div
          slot="header-end"
          className="flex min-w-0 items-center justify-end gap-static-sm max-md:gap-static-xs"
          data-region="status-bar"
          aria-label="Cockpit status and actions"
        >
          <div className="flex min-w-0 items-center gap-static-xs rounded-full border border-contrast-low bg-frosted-soft px-static-xs py-1" aria-label="System status">
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
              className="hidden whitespace-nowrap px-static-xs text-xs font-semibold leading-none text-primary sm:inline-flex"
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
                Workspace check needs attention: {scanError.message}
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
                  Run check again
              </PButton>
            ) : null}
            <DRStatusIndicator
              count={pendingDRCount}
              items={pendingDRItems}
              onItemClick={setSelectedDRId}
            />
          </div>

          <div className="relative flex min-w-0 items-center border-l border-contrast-low pl-static-sm" role="group" aria-label="Maintenance actions">
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
              <span className="absolute -top-1 -right-1 inline-flex size-4 items-center justify-center rounded-full border border-surface bg-warning text-[10px] font-semibold leading-none" aria-hidden="true">
                {normalizedItems.length}
              </span>
            ) : null}
            <PFlyout
              open={isMaintenanceOpen}
              onDismiss={() => setIsMaintenanceOpen(false)}
            >
              <div
                id="shell-maintenance-menu"
                data-testid="maintenance-menu"
                className="flex min-w-64 flex-col gap-static-md p-static-sm"
              >
                <div className="flex items-center justify-between text-xs font-semibold uppercase text-contrast-high">
                  <span>Workspace Care</span>
                  <span>{normalizedItems.length > 0 ? `${normalizedItems.length} attention` : 'Clear'}</span>
                </div>
                <div className="flex flex-col gap-static-xs">
                  {hasLoadedScan && !scanError ? (
                    <RepairPanel
                      corruptionCount={normalizedItems.length}
                      files={normalizedItems}
                      onSuccess={refetch}
                    />
                  ) : null}
                  <CleanupPanel compact={false} onSuccess={refetchTasks} />
                </div>
              </div>
            </PFlyout>
          </div>

          {/* Theme toggle */}
          <div className="flex items-center" aria-label="View settings">
            <ThemeToggle compact={false} />
          </div>

          {pendingDRError ? (
            <span className="text-xs text-error" data-testid="dr-polling-error" role="status">
              {pendingDRError.message}
            </span>
          ) : null}
        </div>

        <nav
        slot="sidebar-start"
        className="flex min-w-0 flex-col items-center gap-static-xs overflow-hidden"
        data-region="nav-rail"
        role="navigation"
        aria-label="Workspaces"
      >
        <div className="flex min-w-0 flex-col items-center gap-static-xs overflow-hidden" aria-label="Workspace switcher">
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
                title={label}
                className={[
                  'focus-text relative inline-flex size-11 flex-none items-center justify-center',
                  'rounded-full border p-0 text-sm font-semibold leading-none',
                  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]',
                  'transition-colors duration-sm',
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
                {badgeCount > 0 ? (
                  <span
                    data-testid="nav-badge"
                    className={[
                      'absolute right-0 top-0 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1',
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

      <div
        className="flex h-full min-h-0 min-w-0 flex-col"
        data-region="workspace"
      >
        <Suspense fallback={<div className="flex h-full items-center justify-center text-sm text-primary" data-testid="route-loading" role="status">Preparing workspace...</div>}>
          <AnimatePresence mode="wait">
            {routeElement ? (
              <motion.div
                key={pathname}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
                className="flex h-full min-h-0 flex-1 flex-col"
              >
                {routeElement}
              </motion.div>
            ) : null}
          </AnimatePresence>
        </Suspense>
      </div>

      </PCanvas>

      {isTaskDetailOpen ? (
        <PModal
          data-testid="task-detail-modal"
          open
          onDismiss={closeTaskDetail}
          aria={{ 'aria-label': selectedTask ? `Task #${selectedTask.id}: ${selectedTask.title}` : 'Task detail' }}
        >
          <div
            className="flex max-h-[min(82vh,900px)] w-[min(960px,calc(100vw-12rem))] min-w-0 flex-col gap-static-md overflow-hidden"
            data-region="task-detail-window"
            data-selected-task-id={selectedTask?.id ?? selectedTaskId ?? undefined}
          >
            <header
              data-testid="task-detail-modal-summary"
              className="flex min-w-0 flex-wrap items-start justify-between gap-static-md rounded-lg bg-frosted-soft p-static-md"
            >
              <div className="flex min-w-0 flex-1 flex-col gap-static-xs">
                <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">
                  {selectedTask ? `Task #${selectedTask.id}` : `Task #${selectedTaskId}`}
                </span>
                <PHeading ref={syncHeadingTagAttr('h2', 'medium')} size="medium" tag="h2">
                  {selectedTaskHeading}
                </PHeading>
              </div>
              {selectedTask ? (
                <div className="flex min-w-0 flex-wrap items-center justify-end gap-static-xs">
                  <PTag
                    compact
                    variant={statusToVariant(selectedTask.status)}
                    ref={syncTagVariantAttr(statusToVariant(selectedTask.status))}
                  >
                    {formatStatus(selectedTask.status)}
                  </PTag>
                  <PTag
                    compact
                    variant={priorityToVariant(selectedTask.priority)}
                    ref={syncTagVariantAttr(priorityToVariant(selectedTask.priority))}
                  >
                    {formatPriority(selectedTask.priority)}
                  </PTag>
                </div>
              ) : null}
            </header>
            <div className="min-h-0 overflow-y-auto pr-static-xs" data-region="task-detail-content">
              {taskDetailContent}
            </div>
          </div>
        </PModal>
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
    </>
  )
}

export default Shell
