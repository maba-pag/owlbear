import { useEffect, useRef, useState } from 'react'
import { PText } from '@porsche-design-system/components-react'

export interface ScanItem {
  code: string
  detail: string
  file_path: string
}

export interface HealthBadgeProps {
  items: ScanItem[]
}

function getAnchoredPopoverPosition(trigger: HTMLElement): { top: string; left: string } {
  const rect = trigger.getBoundingClientRect()
  const viewportPadding = 16
  const popoverWidth = 420
  const top = Math.round(rect.bottom + 8)
  const maxLeft = window.innerWidth - popoverWidth - viewportPadding
  const left = Math.round(Math.max(viewportPadding, Math.min(rect.left, maxLeft)))
  return {
    top: `${top}px`,
    left: `${left}px`,
  }
}

export default function HealthBadge({ items }: HealthBadgeProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState<{ top: string; left: string }>({ top: '0px', left: '0px' })
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const popoverRef = useRef<HTMLDivElement | null>(null)
  const hadOpenPopoverRef = useRef(false)
  const issueCount = items.length
  const isHealthy = issueCount === 0
  const health = isHealthy ? 'green' : 'red'
  const ariaLabel = isHealthy ? 'Health: OK' : `Health: ${issueCount} issues`
  const label = isHealthy ? 'OK' : `${issueCount} issues`

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

    function updatePosition() {
      if (!triggerRef.current) {
        return
      }
      setPosition(getAnchoredPopoverPosition(triggerRef.current))
    }

    document.addEventListener('keydown', handleDocumentKeyDown)
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      document.removeEventListener('keydown', handleDocumentKeyDown)
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [isOpen])

  return (
    <div>
      <button
        type="button"
        ref={triggerRef}
        className={[
          'inline-flex min-h-7 items-center rounded-full px-static-xs text-xs font-semibold leading-none transition-colors duration-sm',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]',
          isHealthy
            ? 'text-primary hover:bg-surface'
            : 'bg-error-low text-error hover:bg-error-low',
        ].join(' ')}
        data-pds-exception="status-bar-control"
        data-testid="health-badge"
        data-region="health"
        data-health={health}
        aria-label={ariaLabel}
        onClick={togglePopover}
      >
        Health {label}
      </button>
      {isOpen ? (
        <div
          ref={popoverRef}
          data-testid="health-badge-popover"
          role="dialog"
          aria-label="Health details"
          tabIndex={-1}
          className="rounded-lg border border-contrast-low bg-surface p-static-sm text-primary shadow-lg"
          // inline-justified: popover top/left are runtime-computed from trigger geometry.
          style={{
            position: 'fixed',
            top: position.top,
            left: position.left,
            zIndex: 1000,
            width: 'min(calc(100vw - 32px), 420px)',
          }}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.preventDefault()
              setIsOpen(false)
            }
          }}
        >
          <div className="mb-static-sm flex items-start justify-between gap-static-md border-b border-contrast-low pb-static-sm">
            <div className="grid gap-1">
              <span className="text-xs font-semibold uppercase text-primary">Workspace Health</span>
              <span className="text-sm leading-normal text-primary">
                {isHealthy ? 'No scan findings are waiting.' : 'Scan findings need attention before the next run.'}
              </span>
            </div>
            <span className="shrink-0 rounded-full border border-contrast-low bg-canvas px-static-xs py-1 text-xs font-semibold leading-none text-primary">
              {isHealthy ? 'Clear' : `${issueCount} issues`}
            </span>
          </div>
          {items.length === 0 ? (
            <div className="rounded-lg border border-contrast-low bg-canvas p-static-sm">
              <PText>No issues</PText>
            </div>
          ) : (
            <ul className="m-0 flex max-h-[min(60vh,420px)] flex-col gap-static-xs overflow-y-auto p-0 text-sm leading-normal">
              {items.map((item, index) => (
                <li key={`${item.file_path}-${item.code}-${index}`} className="grid gap-static-xs rounded-lg border border-contrast-low bg-canvas p-static-sm shadow-sm">
                  <div className="flex min-w-0 items-start justify-between gap-static-xs">
                    <span className="break-all font-mono text-xs leading-normal text-primary">{item.file_path}</span>
                    <span className="shrink-0 rounded-full border border-error bg-error px-static-xs py-1 text-xs font-semibold leading-none text-canvas">{item.code}</span>
                  </div>
                  <span className="text-sm leading-normal text-primary">{item.detail}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
