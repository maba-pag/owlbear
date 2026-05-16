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
  const top = Math.round(rect.bottom + 8)
  const left = Math.round(Math.max(viewportPadding, rect.left))
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

export default function DRStatusIndicator({ count, items, onItemClick }: DRStatusIndicatorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState<{ top: string; left: string }>({ top: '0px', left: '0px' })
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const popoverRef = useRef<HTMLDivElement | null>(null)
  const status = count > 0 ? 'attention' : 'dormant'

  useEffect(() => {
    if (!isOpen) {
      triggerRef.current?.focus()
      return
    }

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
        data-pds-exception="status-bar-control"
        data-testid="dr-indicator"
        data-status={status}
        aria-label={`Pending decision requests: ${count}`}
        onClick={() => setIsOpen((current) => !current)}
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
          style={{
            position: 'fixed',
            top: position.top,
            left: position.left,
            zIndex: 1000,
            maxWidth: '420px',
          }}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.preventDefault()
              setIsOpen(false)
            }
          }}
        >
          {items.length === 0 ? (
            <PText>No pending decision requests</PText>
          ) : (
            <ul>
              {items.map((item) => (
                <li key={item.id}>
                  <PButton
                    type="button"
                    data-testid={`dr-item-${item.id}`}
                    variant="secondary"
                    onClick={() => onItemClick(item.id)}
                  >
                    <span>{item.title}</span>
                    <span>{item.agent}</span>
                    <span>{item.task_id}</span>
                    <span>{formatAge(item.created)}</span>
                  </PButton>
                  <button
                    type="button"
                    data-testid="resolve-button"
                    onClick={() => onItemClick(item.id)}
                  >
                    Resolve
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
