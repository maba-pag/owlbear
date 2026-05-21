import { useEffect, useRef, useState } from 'react'
import { PButton, PText } from '@porsche-design-system/components-react'
import type { PendingDR } from '../hooks/usePendingDRs'

export interface DRStatusIndicatorProps {
  count: number
  items: PendingDR[]
  onItemClick: (id: string) => void
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

function formatAge(created: string): string {
  const parsedCreatedAt = Date.parse(created)
  const createdAt = Number.isFinite(parsedCreatedAt) ? parsedCreatedAt : Date.now()
  const ageMs = Math.max(0, Date.now() - createdAt)
  const ageHours = Math.max(1, Math.floor(ageMs / 3_600_000))
  return `${ageHours}h ago`
}

function formatRequestType(requestType: string): string {
  return requestType
    .replace(/-/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export default function DRStatusIndicator({ count, items, onItemClick }: DRStatusIndicatorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState<{ top: string; left: string }>({ top: '0px', left: '0px' })
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const popoverRef = useRef<HTMLDivElement | null>(null)
  const hadOpenPopoverRef = useRef(false)
  const status = count > 0 ? 'attention' : 'dormant'

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
          count > 0
            ? 'bg-warning-low text-warning hover:bg-warning-low'
            : 'text-contrast-high hover:bg-surface',
        ].join(' ')}
        data-pds-exception="status-bar-control"
        data-testid="dr-indicator"
        data-status={status}
        aria-label={`Pending decision requests: ${count}`}
        onClick={togglePopover}
      >
        DR {count}
      </button>

      {isOpen ? (
        <div
          ref={popoverRef}
          data-testid="dr-popover"
          role="dialog"
          aria-label="Pending decision requests"
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
              <span className="text-xs font-semibold uppercase text-primary">Decisions</span>
              <span className="text-sm leading-normal text-primary">
                {count > 0 ? 'Pending requests need a human decision.' : 'No pending decision requests.'}
              </span>
            </div>
            <span className="shrink-0 rounded-full border border-contrast-low bg-canvas px-static-xs py-1 text-xs font-semibold leading-none text-primary">
              {count > 0 ? `${count} waiting` : 'Clear'}
            </span>
          </div>
          {items.length === 0 ? (
            <div className="rounded-lg border border-contrast-low bg-canvas p-static-sm">
              <PText>No pending decision requests</PText>
            </div>
          ) : (
            <ul className="m-0 flex max-h-[min(60vh,420px)] min-w-0 flex-col gap-static-xs overflow-y-auto p-0">
              {items.map((item) => (
                <li key={item.id} className="grid gap-static-sm rounded-lg border border-contrast-low bg-canvas p-static-sm shadow-sm">
                  <button
                    type="button"
                    data-testid={`dr-item-${item.id}`}
                    data-pds-exception="dr-popover-item"
                    className="grid w-full gap-static-xs rounded-md text-left text-primary transition-colors duration-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]"
                    onClick={() => onItemClick(item.id)}
                  >
                    <span className="text-sm font-semibold leading-snug text-primary">{item.title}</span>
                    <span className="flex flex-wrap items-center gap-static-xs text-xs font-medium text-primary">
                      <span className="rounded-full border border-contrast-low bg-surface px-static-xs py-1 leading-none">{item.agent}</span>
                      <span className="rounded-full border border-contrast-low bg-surface px-static-xs py-1 leading-none">Task #{item.task_id}</span>
                      <span className="rounded-full border border-contrast-low bg-surface px-static-xs py-1 leading-none">{formatRequestType(item.request_type)}</span>
                      <span className="rounded-full border border-contrast-low bg-surface px-static-xs py-1 leading-none">{formatAge(item.created)}</span>
                    </span>
                    <span className="line-clamp-2 text-xs leading-normal text-primary">{item.body_preview}</span>
                  </button>
                  <PButton
                    type="button"
                    data-testid="resolve-button"
                    variant="secondary"
                    compact
                    onClick={() => onItemClick(item.id)}
                  >
                    Resolve
                  </PButton>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
