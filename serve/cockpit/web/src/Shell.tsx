import { Suspense, useCallback, useRef, useEffect, useMemo, useState, type ComponentType, type CSSProperties } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { AnimatePresence, motion } from 'motion/react'
import {
  PBanner,
  PButton,
  PCanvas,
  PHeading,
  PIcon,
  PModal,
  PTag,
  PToast,
  useToastManager,
} from '@porsche-design-system/components-react'
import type { CanvasSidebarStartUpdateEventDetail, IconName } from '@porsche-design-system/components-react'
import DetailTab from './components/DetailTab'
import RepairPanel from './components/RepairPanel'
import RepairReceipt from './components/RepairReceipt'
import ResolveModal from './components/ResolveModal'
import ThemeToggle from './components/ThemeToggle'
import WorkspaceStatus from './components/WorkspaceStatus'
import { useBoardState, useDRState, useTaskSelection } from './hooks/CockpitProvider'
import { usePendingMemoryCount } from './hooks/usePendingMemoryCount'
import type { KanbanBoardProps } from './KanbanBoard'
import { routeConfig } from './routes'
import { priorityToVariant, statusToVariant } from './utils/cardVariants'
import { formatPriority, formatStatus } from './utils/format'
import { OPEN_TASK_DETAIL_EVENT, readOpenTaskDetailEvent } from './utils/openTaskDetail'

function syncHeadingTagAttr(tag: 'h1' | 'h2', size?: 'lg' | 'md' | 'sm') {
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
  kanban: 'steering-wheel',
  decisions: 'route',
  memory: 'brain',
  ideas: 'user-manual',
}

const CANVAS_OVERRIDE_ATTR = 'data-cockpit-canvas-override'

function applyCockpitCanvasOverrides(canvas: HTMLElement | null): boolean {
  const shadowRoot = canvas?.shadowRoot
  if (!shadowRoot) {
    return false
  }

  if (shadowRoot.querySelector(`[${CANVAS_OVERRIDE_ATTR}]`)) {
    return true
  }

  const style = document.createElement('style')
  style.setAttribute(CANVAS_OVERRIDE_ATTR, '')
  style.textContent = [
    ':host{height:100dvh!important;max-height:100dvh!important;overflow:clip!important;}',
    '.root{height:100dvh!important;min-height:0!important;overflow:visible!important;}',
    '.main{min-height:0!important;overflow:clip!important;}',
    '.header{background:var(--p-color-canvas)!important;color:var(--p-color-contrast-high)!important;}',
    '.header__crest,.header__wordmark{display:none!important;grid-column:2!important;grid-row:1!important;}',
    '.header__area--start{grid-column:1!important;grid-row:1!important;min-width:0!important;}',
    '.header__area--end{grid-column:3!important;grid-row:1!important;min-width:0!important;}',
    '.sidebar--start{padding-inline:var(--cockpit-sidebar-start-padding)!important;}',
    '.sidebar__header--start{margin-inline:calc(-1 * var(--cockpit-sidebar-start-padding))!important;padding-inline:var(--cockpit-sidebar-start-padding)!important;}',
  ].join('')
  shadowRoot.append(style)
  const canvasRoot = shadowRoot.querySelector<HTMLElement>('.root')
  if (canvasRoot) {
    if (typeof canvasRoot.scrollTo === 'function') {
      canvasRoot.scrollTo({ left: 0, top: 0 })
    } else {
      canvasRoot.scrollLeft = 0
      canvasRoot.scrollTop = 0
    }
  }
  return true
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
  const canvasRef = useRef<HTMLElement | null>(null)
  const {
    board,
    tasks,
    loading,
    error,
    refetchTasks,
    workspaceHealth,
  } = useBoardState()
  const {
    count: pendingDRCount,
    items: pendingDRItems,
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
  const [isSidebarStartOpen, setIsSidebarStartOpen] = useState(() => {
    if (typeof window === 'undefined') {
      return true
    }
    return window.matchMedia('(min-width: 1024px)').matches
  })
  const [selectedTaskSubtab, setSelectedTaskSubtab] = useState<string | null>(null)
  const [detailValidationMessage, setDetailValidationMessage] = useState<string | null>(null)
  const [bannerError, setBannerError] = useState<{
    heading: string
    description: string
    state: 'error' | 'warning'
  } | null>(null)
  const [isTaskDetailDirty, setIsTaskDetailDirty] = useState(false)
  const [isTaskDetailEditing, setIsTaskDetailEditing] = useState(false)
  const [isTaskDetailRouteOverlayOpen, setIsTaskDetailRouteOverlayOpen] = useState(false)
  const [taskDetailBackStack, setTaskDetailBackStack] = useState<number[]>([])
  const [showTaskDetailUnsavedDialog, setShowTaskDetailUnsavedDialog] = useState(false)
  const pendingTaskDetailActionRef = useRef<(() => void) | null>(null)
  const taskDetailStayButtonRef = useRef<HTMLElement | null>(null)
  const taskDetailContentRef = useRef<HTMLDivElement | null>(null)
  const [taskDetailActionPortalTarget, setTaskDetailActionPortalTarget] = useState<HTMLDivElement | null>(null)
  const [taskDetailCanScrollDown, setTaskDetailCanScrollDown] = useState(false)
  const toastMockClearedRef = useRef(false)

  const runTaskDetailAction = useCallback((action: () => void) => {
    pendingTaskDetailActionRef.current = null
    setShowTaskDetailUnsavedDialog(false)
    setIsTaskDetailDirty(false)
    action()
  }, [])

  const requestTaskDetailAction = useCallback((action: () => void) => {
    if (!isTaskDetailDirty) {
      action()
      return
    }

    if (pendingTaskDetailActionRef.current !== null) {
      return
    }

    pendingTaskDetailActionRef.current = action
    setShowTaskDetailUnsavedDialog(true)
  }, [isTaskDetailDirty])

  const confirmTaskDetailLeave = useCallback(() => {
    const pendingAction = pendingTaskDetailActionRef.current
    if (pendingAction) {
      runTaskDetailAction(pendingAction)
      return
    }

    setShowTaskDetailUnsavedDialog(false)
  }, [runTaskDetailAction])

  const cancelTaskDetailLeave = useCallback(() => {
    pendingTaskDetailActionRef.current = null
    setShowTaskDetailUnsavedDialog(false)
  }, [])

  const updateTaskDetailScrollCue = useCallback(() => {
    const content = taskDetailContentRef.current
    setTaskDetailCanScrollDown(Boolean(
      content && content.scrollHeight - content.scrollTop - content.clientHeight > 1,
    ))
  }, [])

  const selectTaskFromBoard = useCallback((taskId: number) => {
    const action = () => {
      setIsTaskDetailRouteOverlayOpen(false)
      setTaskDetailBackStack([])
      select(taskId)
      setDetailValidationMessage(null)
    }

    if (selectedTaskId === taskId) {
      action()
      return
    }

    requestTaskDetailAction(action)
  }, [requestTaskDetailAction, select, selectedTaskId])

  const kanbanProps = useMemo(
    () => ({
      board,
      tasks,
      loading,
      error,
      refetchTasks,
      onSelectTask: (taskId: number) => {
        selectTaskFromBoard(taskId)
      },
      onMutationError: (heading: string, description: string, state: 'error' | 'warning') => {
        setBannerError({ heading, description, state })
      },
      onMutationSuccess: (message?: string) => {
        setBannerError(null)
        workspaceHealth.refreshAfterMutation()
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
    [board, error, loading, pendingDRItems, refetchTasks, selectTaskFromBoard, selectedTaskId, tasks, workspaceHealth],
  )

  // Compute active nav index from pathname
  const normalizedPathname = normalizeRoutePath(pathname)
  const activeNavIndex = routeConfig.findIndex(
    (route) => normalizeRoutePath(route.path) === normalizedPathname,
  )
  const matchedRoute = activeNavIndex >= 0 ? routeConfig[activeNavIndex] : undefined
  const isKanbanRoute = normalizedPathname === '/'
  const isTaskDetailOpen = selectedTaskId !== null && (isKanbanRoute || isTaskDetailRouteOverlayOpen)
  const isNavRailOpen = isSidebarStartOpen
  const canvasKey = isNavRailOpen ? 'nav-open' : 'nav-closed'
  const navigateWorkspace = useCallback((path: string) => {
    if (normalizeRoutePath(path) === normalizedPathname) {
      return
    }

    requestTaskDetailAction(() => {
      setIsTaskDetailRouteOverlayOpen(false)
      navigate(path)
    })
  }, [navigate, normalizedPathname, requestTaskDetailAction])
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
    if (showTaskDetailUnsavedDialog) {
      taskDetailStayButtonRef.current?.focus()
    }
  }, [showTaskDetailUnsavedDialog])

  useEffect(() => {
    if (!isTaskDetailDirty) {
      pendingTaskDetailActionRef.current = null
      setShowTaskDetailUnsavedDialog(false)
      return
    }

    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
    }

    window.addEventListener('beforeunload', onBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
    }
  }, [isTaskDetailDirty])

  useEffect(() => {
    if (!isTaskDetailOpen) {
      setIsTaskDetailDirty(false)
      setIsTaskDetailEditing(false)
    }
  }, [isTaskDetailOpen])

  useEffect(() => {
    updateTaskDetailScrollCue()

    const content = taskDetailContentRef.current
    if (!isTaskDetailOpen || !content || typeof ResizeObserver === 'undefined') {
      return
    }

    const observer = new ResizeObserver(updateTaskDetailScrollCue)
    observer.observe(content)
    return () => {
      observer.disconnect()
    }
  }, [detailValidationMessage, isTaskDetailOpen, selectedTask?.updated, selectedTaskError, updateTaskDetailScrollCue])

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

  useEffect(() => {
    let animationFrame = 0
    let attempts = 0

    const applyCanvasOverrides = () => {
      if (applyCockpitCanvasOverrides(canvasRef.current) || attempts >= 5) {
        return
      }

      attempts += 1
      animationFrame = window.requestAnimationFrame(applyCanvasOverrides)
    }

    applyCanvasOverrides()

    return () => {
      if (animationFrame !== 0) {
        window.cancelAnimationFrame(animationFrame)
      }
    }
  }, [canvasKey])

  const canvasStyle = {
    '--p-canvas-sidebar-start-width': '72px',
    '--cockpit-sidebar-start-padding': '14px',
  } as CSSProperties

  const closeTaskDetail = useCallback(() => {
    requestTaskDetailAction(() => {
      clear()
      setIsTaskDetailRouteOverlayOpen(false)
      setTaskDetailBackStack([])
      setSelectedTaskSubtab(null)
      setDetailValidationMessage(null)
    })
  }, [clear, requestTaskDetailAction])

  const selectTaskFromDetail = useCallback((taskId: number, subtab?: string | null) => {
    const action = () => {
      setIsTaskDetailRouteOverlayOpen(true)
      if (selectedTaskId !== null && selectedTaskId !== taskId) {
        setTaskDetailBackStack((current) => [...current, selectedTaskId])
      }
      select(taskId)
      setSelectedTaskSubtab((current) => subtab ?? current)
      setDetailValidationMessage(null)
    }

    if (selectedTaskId === taskId) {
      action()
      return
    }

    requestTaskDetailAction(action)
  }, [requestTaskDetailAction, select, selectedTaskId])

  const navigateTaskDetailBack = useCallback(() => {
    const previousTaskId = taskDetailBackStack[taskDetailBackStack.length - 1]
    if (previousTaskId === undefined) {
      return
    }

    requestTaskDetailAction(() => {
      setTaskDetailBackStack((current) => current.slice(0, -1))
      select(previousTaskId)
      setSelectedTaskSubtab(null)
      setDetailValidationMessage(null)
    })
  }, [requestTaskDetailAction, select, taskDetailBackStack])

  useEffect(() => {
    const handleOpenTaskDetail = (event: Event) => {
      const taskId = readOpenTaskDetailEvent(event)
      if (taskId === null) {
        return
      }
      selectTaskFromDetail(taskId)
    }

    window.addEventListener(OPEN_TASK_DETAIL_EVENT, handleOpenTaskDetail)
    return () => {
      window.removeEventListener(OPEN_TASK_DETAIL_EVENT, handleOpenTaskDetail)
    }
  }, [selectTaskFromDetail])

  const onSidebarStartUpdate = (event: CustomEvent<CanvasSidebarStartUpdateEventDetail>) => {
    setIsSidebarStartOpen(event.detail.open)
  }

  const mutationBanner = (
    <PBanner
      open={bannerError !== null}
      heading={bannerError?.heading ?? ''}
      state={bannerError?.state ?? 'error'}
      onDismiss={() => setBannerError(null)}
    >
      {bannerError?.description ?? ''}
    </PBanner>
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
        taskReferences={tasks}
        initialSubtab={selectedTaskSubtab}
        onSelectTask={(taskId, subtab) => {
          selectTaskFromDetail(taskId, subtab)
        }}
        onDirtyChange={setIsTaskDetailDirty}
        onEditingChange={setIsTaskDetailEditing}
        actionPortalTarget={taskDetailActionPortalTarget}
        onTaskCleared={(message) => {
          clear()
          setTaskDetailBackStack([])
          setIsTaskDetailDirty(false)
          setIsTaskDetailEditing(false)
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
        ref={canvasRef}
        className="shell h-dvh max-h-dvh overflow-hidden font-sans text-primary"
        background="canvas"
        data-no-sidecar=""
        sidebarStartOpen={isNavRailOpen}
        sidebarEndOpen={false}
        style={canvasStyle}
        onSidebarStartUpdate={onSidebarStartUpdate}
      >
        <span slot="title" className="sr-only">OwlBear Cockpit</span>

        <span
          slot="header-start"
          className="pointer-events-none absolute left-1/2 top-1/2 z-10 flex min-w-0 -translate-x-1/2 -translate-y-1/2 items-baseline gap-static-xs whitespace-nowrap text-lg font-semibold leading-none text-primary"
          data-testid="app-identity"
          aria-label="OwlBear Cockpit"
        >
          <span className="truncate">OwlBear</span>
          <span className="hidden font-medium text-[var(--p-color-contrast-medium)] md:inline">Cockpit</span>
        </span>

        <div
          slot="header-end"
          className="flex min-w-0 items-center justify-end gap-static-sm max-md:gap-static-xs"
          data-region="status-bar"
          aria-label="Cockpit status and actions"
        >
          <div className="flex min-w-0 items-center gap-static-xs" aria-label="Workspace status">
            <span className="inline-flex">
              <WorkspaceStatus
                health={workspaceHealth.health}
                connectionError={workspaceHealth.connectionError}
                onRefresh={workspaceHealth.refresh}
                portalPopover
                taskAction={(closeStatus) => (
                  <RepairPanel
                    repairableCount={workspaceHealth.health.modules.tasks?.repairable_count ?? 0}
                    onSuccess={(repair) => {
                      workspaceHealth.mergeRepair(repair)
                      closeStatus()
                    }}
                    portalConfirmDialog
                  />
                )}
              />
            </span>
            {workspaceHealth.receipt ? (
              <RepairReceipt receipt={workspaceHealth.receipt} onDismiss={workspaceHealth.dismissReceipt} />
            ) : null}
          </div>

          {/* Theme toggle */}
          <div className="flex items-center" aria-label="View settings">
            <ThemeToggle compact />
          </div>
        </div>

        <nav
          slot="sidebar-start"
          className={[
            'flex min-w-0 flex-col items-center overflow-hidden transition-opacity duration-sm',
            isNavRailOpen ? 'opacity-100' : 'pointer-events-none invisible opacity-0',
          ].join(' ')}
          data-region="nav-rail"
          role="navigation"
          aria-label="Workspaces"
          aria-hidden={isNavRailOpen ? undefined : true}
        >
          <div
            className="flex min-w-0 flex-col items-center gap-static-sm rounded-full border border-contrast-low bg-frosted-soft p-static-xs backdrop-blur-sm"
            data-testid="nav-rail-dock"
            aria-label="Workspace switcher"
          >
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
                    'rounded-full border border-transparent p-0 text-sm font-semibold leading-none',
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]',
                    'transition-[background-color,color,box-shadow,transform] duration-sm',
                    isActive
                      ? 'bg-primary text-canvas'
                      : 'text-contrast-high hover:bg-surface hover:shadow-sm',
                  ].join(' ')}
                  data-surface={route.icon}
                  data-pds-exception={`nav-${route.icon}`}
                  aria-current={isActive ? 'page' : undefined}
                  aria-label={label}
                  tabIndex={isNavRailOpen ? 0 : -1}
                  onClick={() => navigateWorkspace(route.path)}
                >
                  <PIcon
                    name={NAV_ICONS[route.icon] || 'grid'}
                    color="inherit"
                    size="sm"
                    aria-hidden="true"
                  />
                  {badgeCount > 0 ? (
                    <span
                      data-testid="nav-badge"
                      className={[
                        'absolute right-0 top-0 z-10 inline-flex h-4 min-w-4 items-center justify-center rounded-full border border-surface px-1 shadow-sm',
                        'text-[0.6rem] font-bold leading-none',
                        isActive ? 'bg-surface text-primary' : 'bg-warning text-primary',
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
          onDismiss={showTaskDetailUnsavedDialog ? cancelTaskDetailLeave : closeTaskDetail}
          aria={{ 'aria-label': selectedTask ? `Task #${selectedTask.id}: ${selectedTask.title}` : 'Task detail' }}
        >
          <div
            className="relative flex h-[min(84dvh,820px)] max-h-[min(84dvh,820px)] w-[min(1280px,calc(100vw-18.5rem))] max-w-full min-w-0 flex-col gap-static-md overflow-hidden md:h-[min(84vh,820px)] md:max-h-[min(84vh,820px)]"
            data-region="task-detail-window"
            data-selected-task-id={selectedTask?.id ?? selectedTaskId ?? undefined}
          >
            <header
              data-testid="task-detail-modal-summary"
              className="flex min-w-0 flex-wrap items-start justify-between gap-static-md rounded-lg border border-contrast-low bg-canvas p-static-md max-lg:pr-[4.75rem]"
            >
              <div className="flex min-w-0 flex-1 flex-col gap-static-xs">
                <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">
                  {selectedTask ? `Task #${selectedTask.id}` : `Task #${selectedTaskId}`}
                </span>
                <PHeading ref={syncHeadingTagAttr('h2', 'md')} size="md" tag="h2">
                  {selectedTaskHeading}
                </PHeading>
              </div>
              {selectedTask ? (
                <div className="flex w-full min-w-0 flex-wrap items-center justify-start gap-static-xs lg:w-auto lg:justify-end">
                  {taskDetailBackStack.length > 0 ? (
                    <PButton
                      type="button"
                      data-testid="task-detail-back"
                      variant="secondary"
                      icon="arrow-left"
                      compact
                      onClick={navigateTaskDetailBack}
                    >
                      Back
                    </PButton>
                  ) : null}
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
            <div
              ref={setTaskDetailActionPortalTarget}
              data-testid="task-detail-action-host"
              className={isTaskDetailEditing ? '-mt-static-md flex-none rounded-b-lg border-x border-b border-contrast-low bg-canvas' : 'hidden'}
              aria-hidden={isTaskDetailEditing ? undefined : true}
            />
            <div className="relative min-h-0 flex-1 overflow-hidden" data-testid="task-detail-scroll-shell">
              <div ref={taskDetailContentRef} onScroll={updateTaskDetailScrollCue} className="absolute inset-0 min-h-0 overflow-x-hidden overflow-y-auto pb-static-lg pr-static-xs" data-region="task-detail-content">
                {taskDetailContent}
              </div>
              {taskDetailCanScrollDown && !isTaskDetailEditing ? (
                <div
                  aria-hidden="true"
                  data-testid="task-detail-scroll-cue"
                  className="pointer-events-none absolute inset-x-0 bottom-0 h-10 [background:linear-gradient(to_bottom,transparent,var(--p-color-canvas))]"
                />
              ) : null}
            </div>
            {showTaskDetailUnsavedDialog ? (
              <div
                data-testid="task-detail-unsaved-dialog"
                role="alertdialog"
                aria-modal="true"
                aria-labelledby="task-detail-unsaved-title"
                aria-describedby="task-detail-unsaved-description"
                className="absolute inset-0 z-30 flex items-center justify-center bg-frosted-soft p-static-lg text-primary backdrop-blur-sm"
              >
                <div className="grid w-[min(440px,100%)] gap-static-md rounded-lg border border-contrast-low bg-canvas p-static-md shadow-lg">
                  <div className="grid gap-static-xs rounded-lg border border-error bg-error-low p-static-md">
                    <span className="text-xs font-semibold uppercase text-error">Unsaved changes</span>
                    <h2 id="task-detail-unsaved-title" className="m-0 text-xl font-semibold leading-tight text-primary">
                      Leave task detail?
                    </h2>
                    <p id="task-detail-unsaved-description" className="m-0 text-sm leading-normal text-primary">
                      You have unsaved changes. Leave anyway?
                    </p>
                  </div>
                  <div className="flex flex-wrap justify-end gap-static-xs">
                    <PButton type="button" variant="secondary" onClick={confirmTaskDetailLeave}>
                      Leave
                    </PButton>
                    <PButton ref={taskDetailStayButtonRef} type="button" onClick={cancelTaskDetailLeave}>
                      Cancel
                    </PButton>
                  </div>
                </div>
              </div>
            ) : null}
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
