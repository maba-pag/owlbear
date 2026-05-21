import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { PText } from '@porsche-design-system/components-react'

export interface ScanItem {
  code: string
  detail: string
  file_path: string
}

export interface HealthBadgeProps {
  items: ScanItem[]
  status?: 'green' | 'yellow' | 'red'
  message?: string
  actions?: ReactNode
  portalPopover?: boolean
}

function getAnchoredPopoverPosition(trigger: HTMLElement): { top: string; left: string } {
  const rect = trigger.getBoundingClientRect()
  const viewportPadding = 16
  const popoverWidth = Math.min(420, window.innerWidth - viewportPadding * 2)
  const top = Math.round(rect.bottom + 8)
  const maxLeft = Math.max(viewportPadding, window.innerWidth - popoverWidth - viewportPadding)
  const left = Math.round(Math.min(Math.max(viewportPadding, rect.right - popoverWidth), maxLeft))
  return {
    top: `${top}px`,
    left: `${left}px`,
  }
}

export default function HealthBadge({ items, status, message, actions, portalPopover = false }: HealthBadgeProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState<{ top: string; left: string }>({ top: '0px', left: '0px' })
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const popoverRef = useRef<HTMLDivElement | null>(null)
  const hadOpenPopoverRef = useRef(false)
  const issueCount = items.length
  const isHealthy = issueCount === 0
  const health = issueCount > 0 ? 'red' : (status ?? 'green')
  const statusLabel = issueCount > 0
    ? `${issueCount} issues`
    : health === 'yellow'
      ? 'Stale'
      : health === 'red'
        ? 'Check failed'
        : 'OK'
  const ariaLabel = `Workspace status: ${statusLabel}`

  function togglePopover() {
    if (!isOpen && triggerRef.current) {
      setPosition(getAnchoredPopoverPosition(triggerRef.current))
    }
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

    const trigger = triggerRef.current
    if (trigger) {
      setPosition(getAnchoredPopoverPosition(trigger))
    }

    popoverRef.current?.focus()

    function handleDocumentKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        setIsOpen(false)
      }
    }

    function handleDocumentPointerDown(event: PointerEvent) {
      const target = event.target
      if (!(target instanceof Node)) {
        return
      }
      if (triggerRef.current?.contains(target) || popoverRef.current?.contains(target)) {
        return
      }
      setIsOpen(false)
    }

    function updatePosition() {
      if (!triggerRef.current) {
        return
      }
      setPosition(getAnchoredPopoverPosition(triggerRef.current))
    }

    document.addEventListener('keydown', handleDocumentKeyDown)
    document.addEventListener('pointerdown', handleDocumentPointerDown)
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      document.removeEventListener('keydown', handleDocumentKeyDown)
      document.removeEventListener('pointerdown', handleDocumentPointerDown)
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
      data-testid="health-badge-popover"
      ref={popoverRef}
      tabIndex={-1}
      role="dialog"
      aria-label="Workspace status details"
      style={{
        position: 'fixed',
        top: position.top,
        left: position.left,
        zIndex: 1000,
        width: 'min(calc(100vw - 32px), 420px)',
      }}
      className="rounded-lg border border-contrast-medium bg-surface p-static-sm text-primary shadow-xl"
      data-pds-exception="overlay-surface"
      onKeyDown={handlePopoverKeyDown}
    >
      <div className="mb-static-xs flex items-start justify-between gap-static-md border-b border-contrast-low pb-static-xs">
        <div className="grid gap-1">
          <span className="text-xs font-semibold uppercase text-primary">Workspace Status</span>
          <span className="text-sm leading-normal text-primary">
            {message ?? (isHealthy ? 'No scan findings are waiting.' : 'Scan findings need attention before the next run.')}
          </span>
        </div>
        <span className="shrink-0 rounded-full border border-contrast-low bg-canvas px-static-xs py-1 text-xs font-semibold leading-none text-primary">
          {statusLabel}
        </span>
      </div>
      {isHealthy ? (
        <PText>No issues</PText>
      ) : (
        <ul className="m-0 flex max-h-[min(60vh,420px)] flex-col gap-static-xs overflow-y-auto p-0 text-sm leading-normal">
          {items.map((item) => (
            <li key={`${item.file_path}-${item.code}`} className="grid gap-1 rounded-md border border-contrast-medium bg-canvas p-static-xs">
              <div className="flex items-start justify-between gap-static-xs">
                <span className="break-all font-mono text-xs text-primary">{item.file_path}</span>
                <span className="shrink-0 rounded-full bg-error px-static-xs py-1 text-xs font-semibold leading-none text-canvas">{item.code}</span>
              </div>
              <span>{item.detail}</span>
            </li>
          ))}
        </ul>
      )}
      {actions ? (
        <div data-testid="workspace-status-actions" className="mt-static-sm flex flex-wrap items-center justify-end gap-static-xs border-t border-contrast-low pt-static-sm">
          {actions}
        </div>
      ) : null}
    </div>
  ) : null

  const renderedPopover = portalPopover && typeof document !== 'undefined' && document.body && popover
    ? createPortal(popover, document.body)
    : popover

  return (
    <div>
      <button
        type="button"
        ref={triggerRef}
        className={[
          'inline-flex size-11 items-center justify-center rounded-full bg-transparent p-0 transition-colors duration-sm',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]',
          health === 'green'
            ? 'hover:bg-surface'
            : health === 'yellow'
              ? 'hover:bg-warning-low'
              : 'hover:bg-error-low',
        ].join(' ')}
        data-pds-exception="status-bar-control"
        data-testid="health-badge"
        data-region="health"
        data-health={health}
        aria-label={ariaLabel}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        title={ariaLabel}
        onClick={togglePopover}
      >
        <span
          className={[
            'size-2.5 flex-none rounded-full',
            health === 'red' ? 'bg-error ring-3 ring-error-low' :
            health === 'yellow' ? 'bg-warning ring-3 ring-warning-low' :
            'bg-success ring-3 ring-success-low',
          ].join(' ')}
          data-testid="traffic-light"
          data-health={health}
          aria-hidden="true"
        />
      </button>
      {renderedPopover}
    </div>
  )
}
