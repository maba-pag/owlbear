import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { PButton } from '@porsche-design-system/components-react'
import type {
  WorkspaceHealthResponse,
  WorkspaceModuleHealth,
  WorkspaceModuleName,
  WorkspaceModuleStatus,
} from '../hooks/useWorkspaceHealth'

export interface WorkspaceStatusProps {
  health: WorkspaceHealthResponse
  connectionError?: string | null
  taskAction?: (onComplete: () => void) => ReactNode
  onRefresh?: () => void
  portalPopover?: boolean
}

const MODULES: Array<{ name: WorkspaceModuleName; label: string }> = [
  { name: 'tasks', label: 'Tasks' },
  { name: 'requests', label: 'Requests' },
  { name: 'memory', label: 'Memory' },
  { name: 'ideas', label: 'Ideas' },
]

const STATUS_LABELS: Record<WorkspaceModuleStatus, string> = {
  checking: 'Checking',
  unknown: 'Unknown',
  healthy: 'Healthy',
  attention: 'Needs attention',
  unhealthy: 'Unhealthy',
  'check-failed': 'Check failed',
}

function lightClass(status: WorkspaceModuleStatus): string {
  if (status === 'healthy') return 'bg-success ring-success-low'
  if (status === 'attention') return 'bg-warning ring-warning-low'
  if (status === 'unhealthy' || status === 'check-failed') return 'bg-error ring-error-low'
  return 'bg-contrast-medium ring-contrast-low'
}

function getAnchoredPopoverPosition(trigger: HTMLElement): { top: string; left: string } {
  const rect = trigger.getBoundingClientRect()
  const viewportPadding = 16
  const popoverWidth = Math.min(440, window.innerWidth - viewportPadding * 2)
  const maxLeft = Math.max(viewportPadding, window.innerWidth - popoverWidth - viewportPadding)
  return {
    top: `${Math.round(rect.bottom + 8)}px`,
    left: `${Math.round(Math.min(Math.max(viewportPadding, rect.right - popoverWidth), maxLeft))}px`,
  }
}

function findingText(finding: Record<string, unknown>, key: string): string | null {
  const value = finding[key]
  return typeof value === 'string' && value.length > 0 ? value : null
}

function findingPath(finding: Record<string, unknown>): string {
  return findingText(finding, 'path')
    ?? findingText(finding, 'file_path')
    ?? findingText(finding, 'request_id')
    ?? 'Workspace record'
}

function moduleSummary(module: WorkspaceModuleHealth): string {
  const findings = module.findings?.length ?? 0
  const repairable = module.repairable_count ?? 0
  if (module.status === 'checking' || module.status === 'unknown') return STATUS_LABELS[module.status]
  if (module.status === 'check-failed') return 'Check could not complete'
  if (findings === 0) return 'No findings'
  if (repairable > 0) return `${findings} findings, ${repairable} repairable`
  return `${findings} findings`
}

function unresolvedFindings(module: WorkspaceModuleHealth): Array<Record<string, unknown>> {
  if (module.status !== 'unhealthy' && module.status !== 'check-failed') return []
  return (module.findings ?? []).filter((finding) => finding.repairable !== true)
}

export default function WorkspaceStatus({
  health,
  connectionError = null,
  taskAction,
  onRefresh,
  portalPopover = false,
}: WorkspaceStatusProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState({ top: '0px', left: '0px' })
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const popoverRef = useRef<HTMLDivElement | null>(null)
  const hadOpenPopoverRef = useRef(false)
  const overallLabel = STATUS_LABELS[health.status]
  const ariaLabel = `Workspace status: ${overallLabel}`

  function togglePopover() {
    if (!isOpen && triggerRef.current) setPosition(getAnchoredPopoverPosition(triggerRef.current))
    setIsOpen((current) => !current)
  }

  useEffect(() => {
    if (!isOpen) {
      if (hadOpenPopoverRef.current) {
        triggerRef.current?.focus()
        hadOpenPopoverRef.current = false
      }
      return
    }

    hadOpenPopoverRef.current = true
    if (triggerRef.current) setPosition(getAnchoredPopoverPosition(triggerRef.current))
    popoverRef.current?.focus()

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        setIsOpen(false)
      }
    }

    function closeOutside(event: PointerEvent) {
      const eventPath = event.composedPath()
      if (
        eventPath.includes(triggerRef.current as EventTarget)
        || eventPath.includes(popoverRef.current as EventTarget)
        || eventPath.some(
          (target) => target instanceof Element && target.hasAttribute('data-workspace-status-overlay'),
        )
      ) return
      setIsOpen(false)
    }

    function updatePosition() {
      if (triggerRef.current) setPosition(getAnchoredPopoverPosition(triggerRef.current))
    }

    document.addEventListener('keydown', closeOnEscape)
    document.addEventListener('pointerdown', closeOutside)
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      document.removeEventListener('keydown', closeOnEscape)
      document.removeEventListener('pointerdown', closeOutside)
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [isOpen])

  function handlePopoverKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      setIsOpen(false)
    }
  }

  const popover = isOpen ? (
    <div
      ref={popoverRef}
      tabIndex={-1}
      role="dialog"
      aria-label="Workspace status details"
      data-testid="workspace-status-popover"
      className="rounded-lg border border-contrast-medium bg-surface p-static-sm text-primary shadow-xl"
      data-pds-exception="overlay-surface"
      style={{
        position: 'fixed',
        top: position.top,
        left: position.left,
        zIndex: 1000,
        width: 'min(calc(100vw - 32px), 440px)',
      }}
      onKeyDown={handlePopoverKeyDown}
    >
      <header className="flex items-start justify-between gap-static-sm border-b border-contrast-low pb-static-sm">
        <div className="grid gap-1">
          <span className="text-sm font-semibold text-primary">Workspace Status</span>
          <span className="text-xs text-[var(--p-color-contrast-medium)]">Overall: {overallLabel}</span>
          {connectionError ? (
            <span className="text-sm text-error" role="status">Connection problem: {connectionError}</span>
          ) : null}
        </div>
        {onRefresh && (connectionError || health.status === 'check-failed') ? (
          <PButton compact variant="secondary" onClick={onRefresh}>Run check again</PButton>
        ) : null}
      </header>

      <ul className="m-0 grid max-h-[min(65vh,520px)] list-none overflow-y-auto p-0">
        {MODULES.map(({ name, label }) => {
          const module = health.modules[name] ?? { status: 'unknown' }
          const details = unresolvedFindings(module)
          return (
            <li
              key={name}
              data-testid={`workspace-module-${name}`}
              data-health={module.status}
              className="border-b border-contrast-low py-static-sm last:border-b-0"
            >
              <div className="flex items-start gap-static-sm">
                <span
                  data-testid={`workspace-module-light-${name}`}
                  data-health={module.status}
                  className={`mt-1 size-2.5 flex-none rounded-full ring-2 ${lightClass(module.status)}`}
                  aria-hidden="true"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-start justify-between gap-static-xs">
                    <div className="grid gap-1">
                      <span className="text-sm font-semibold text-primary">{label}</span>
                      <span className="text-xs text-[var(--p-color-contrast-medium)]">
                        {STATUS_LABELS[module.status]} · {moduleSummary(module)}
                      </span>
                    </div>
                    {name === 'tasks' && (module.repairable_count ?? 0) > 0
                      ? taskAction?.(() => setIsOpen(false))
                      : null}
                  </div>
                  {details.length > 0 ? (
                    <ul className="m-0 mt-static-xs grid list-none gap-static-xs p-0">
                      {details.map((finding, index) => (
                        <li key={`${findingPath(finding)}-${findingText(finding, 'code') ?? index}`} className="grid gap-1 border-l-2 border-error pl-static-xs text-xs">
                          <span className="break-all font-mono text-primary">{findingPath(finding)}</span>
                          <span className="font-semibold text-error">{findingText(finding, 'code') ?? 'UNRESOLVED'}</span>
                          {findingText(finding, 'detail') ? <span>{findingText(finding, 'detail')}</span> : null}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  ) : null

  return (
    <div>
      <button
        ref={triggerRef}
        type="button"
        data-testid="workspace-status"
        data-region="health"
        data-health={health.status}
        className="inline-flex size-8 items-center justify-center rounded-full border-0 bg-transparent p-0 transition-colors duration-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]"
        data-pds-exception="status-bar-control"
        aria-label={ariaLabel}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        title={ariaLabel}
        onClick={togglePopover}
      >
        <span
          data-testid="traffic-light"
          data-health={health.status}
          className={`size-2.5 flex-none rounded-full ring-2 ${lightClass(health.status)}`}
          aria-hidden="true"
        />
      </button>
      {portalPopover && typeof document !== 'undefined' && document.body && popover
        ? createPortal(popover, document.body)
        : popover}
    </div>
  )
}
