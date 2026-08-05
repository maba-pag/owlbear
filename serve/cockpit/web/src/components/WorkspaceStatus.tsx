import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { PButtonPure } from '@porsche-design-system/components-react'
import {
  useWorkspaceHealth,
  WORKSPACE_HEALTH_LABELS,
  type WorkspaceHealthStatus,
} from '../hooks/useWorkspaceHealth'
import { getRailPanelPosition } from './railPanelPosition'

const PANEL_WIDTH = 320
const ESTIMATED_PANEL_HEIGHT = 250
const CONTROL_NAME = 'Memory and Ideas health'
/** The heading names the property checked; the rows name the surfaces; neither repeats the other. */
const PANEL_TITLE = 'Persisted data integrity'
/** Freshness is wall-clock wording, so it is re-rendered on its own cadence and never refetched. */
const FRESHNESS_TICK_MS = 30_000

const DOT_CLASSES: Record<WorkspaceHealthStatus, string> = {
  healthy: 'bg-success',
  attention: 'bg-warning',
  unhealthy: 'bg-error',
  unavailable: 'bg-contrast-medium',
  checking: 'bg-contrast-medium',
}

const STATUS_TEXT_CLASSES: Record<WorkspaceHealthStatus, string> = {
  healthy: 'text-contrast-medium',
  attention: 'text-warning',
  unhealthy: 'text-error',
  unavailable: 'text-contrast-medium',
  checking: 'text-contrast-medium',
}

/** Elapsed wording for the last settled check; the panel never claims freshness it cannot show. */
function checkAge(checkedAt: number | null, now: number): string {
  if (checkedAt === null) return 'Not checked yet'
  const elapsedMinutes = Math.floor(Math.max(0, now - checkedAt) / 60_000)
  if (elapsedMinutes < 1) return 'Checked just now'
  if (elapsedMinutes < 60) return `Checked ${elapsedMinutes}m ago`
  return `Checked ${Math.floor(elapsedMinutes / 60)}h ago`
}

/**
 * `semantic` carries the green/yellow/red/neutral health scale inside the panel. `trigger` keeps the
 * always-visible rail dot neutral while healthy, so only a real problem colours the shell.
 */
function StatusDot({
  status,
  variant = 'semantic',
  className = '',
}: {
  status: WorkspaceHealthStatus
  variant?: 'semantic' | 'trigger'
  className?: string
}) {
  const color = variant === 'trigger' && status === 'healthy' ? 'bg-primary' : DOT_CLASSES[status]
  return <span aria-hidden="true" className={`inline-block size-2.5 shrink-0 rounded-full ${color} ${className}`} />
}

/**
 * Read-only health control for the two persisted-data surfaces the backend reports — the memory
 * store and the ideas file. Nothing here repairs anything: re-running the check is the only action
 * the backend supports.
 */
export default function WorkspaceStatus() {
  const { status, modules, isChecking, lastCheckedAt, refresh } = useWorkspaceHealth()
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState({ top: '0px', left: '0px' })
  const [now, setNow] = useState(() => Date.now())
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)

  // Only the open panel shows elapsed wording, so the closed control keeps no interval running.
  useEffect(() => {
    if (!isOpen) return
    setNow(Date.now())
    const ticker = window.setInterval(() => { setNow(Date.now()) }, FRESHNESS_TICK_MS)
    return () => { window.clearInterval(ticker) }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return

    panelRef.current?.focus()

    const closeOnPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null
      if (!target) return
      if (triggerRef.current?.contains(target) || panelRef.current?.contains(target)) return
      setIsOpen(false)
    }

    const updatePosition = () => {
      if (triggerRef.current) {
        setPosition(getRailPanelPosition(triggerRef.current, PANEL_WIDTH, panelRef.current?.offsetHeight || ESTIMATED_PANEL_HEIGHT))
      }
    }

    updatePosition()
    document.addEventListener('pointerdown', closeOnPointerDown)
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)

    return () => {
      document.removeEventListener('pointerdown', closeOnPointerDown)
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [isOpen])

  function close(restoreFocus: boolean) {
    setIsOpen(false)
    if (restoreFocus) triggerRef.current?.focus()
  }

  function handlePanelKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      close(true)
    }
  }

  function toggle() {
    if (isOpen) {
      setIsOpen(false)
      return
    }
    if (triggerRef.current) {
      setPosition(getRailPanelPosition(triggerRef.current, PANEL_WIDTH, ESTIMATED_PANEL_HEIGHT))
    }
    refresh()
    setIsOpen(true)
  }

  const statusLabel = WORKSPACE_HEALTH_LABELS[status]

  const panel = isOpen ? createPortal(
    <div
      ref={panelRef}
      role="dialog"
      aria-label={CONTROL_NAME}
      tabIndex={-1}
      data-testid="workspace-status-panel"
      className="fixed z-[80] grid w-[320px] max-w-[calc(100vw-24px)] gap-static-sm overflow-hidden rounded-sm border border-contrast-low bg-canvas p-static-md text-primary shadow-[0_16px_48px_rgb(0_0_0_/_0.16)]"
      style={position}
      onKeyDown={handlePanelKeyDown}
    >
      {/* Every module is always listed, so an overall status word here would only repeat the rows. */}
      <strong className="min-w-0 truncate text-sm leading-tight">{PANEL_TITLE}</strong>

      <ul className="m-0 grid list-none gap-0 divide-y divide-contrast-low border-y border-contrast-low p-0">
        {modules.map((module) => (
          <li key={module.id} className="grid min-w-0 gap-1 py-static-sm" data-testid={`workspace-status-module-${module.id}`}>
            <span className="flex min-w-0 items-center gap-static-xs text-sm">
              <StatusDot status={module.status} />
              <span className="min-w-0 flex-1 truncate font-semibold">{module.label}</span>
              {/* Only healthy is dropped from view: the green dot already says it. Every problem
                  state keeps visible text, because colour must never carry it alone. */}
              <span
                data-testid={`workspace-status-module-${module.id}-state`}
                className={module.status === 'healthy'
                  ? 'sr-only'
                  : `shrink-0 text-xs ${STATUS_TEXT_CLASSES[module.status]}`}
              >
                {WORKSPACE_HEALTH_LABELS[module.status]}
              </span>
            </span>
            {module.summary ? (
              <span className="break-words pl-[calc(0.625rem+var(--spacing-static-xs))] text-xs text-contrast-medium">{module.summary}</span>
            ) : null}
            {module.findings.length > 0 ? (
              <ul className="m-0 grid max-h-40 list-none gap-1 overflow-y-auto p-0 pl-[calc(0.625rem+var(--spacing-static-xs))] text-xs">
                {module.findings.slice(0, 8).map((finding) => (
                  <li key={finding} className="break-words font-mono text-error">{finding}</li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-center justify-between gap-static-xs">
        <span className="text-xs text-contrast-medium" data-testid="workspace-status-freshness">
          {isChecking ? 'Checking...' : checkAge(lastCheckedAt, now)}
        </span>
        <PButtonPure
          type="button"
          icon="refresh"
          size="small"
          data-testid="workspace-status-recheck"
          onClick={() => refresh()}
        >
          Re-check
        </PButtonPure>
      </div>
    </div>,
    document.body,
  ) : null

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        data-testid="workspace-status"
        data-pds-exception="status-bar-control"
        data-status={status}
        className={[
          'inline-flex size-8 items-center justify-center rounded-full border-0 bg-transparent p-0 text-primary transition-colors duration-sm',
          'hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]',
          isOpen ? 'bg-surface' : '',
        ].join(' ')}
        aria-haspopup="dialog"
        aria-expanded={isOpen ? 'true' : 'false'}
        aria-label={`${CONTROL_NAME}: ${statusLabel}; open health details`}
        title={`${CONTROL_NAME}: ${statusLabel}`}
        onClick={toggle}
      >
        <StatusDot status={status} variant="trigger" className="size-3" />
      </button>
      {panel}
    </>
  )
}
