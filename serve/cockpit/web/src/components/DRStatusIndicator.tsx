import { useEffect, useRef, useState } from 'react'
import { PButton, PText } from '@porsche-design-system/components-react'
import type { PendingDR } from '../hooks/usePendingDRs'

export interface DRStatusIndicatorProps {
  count: number
  items: PendingDR[]
  onItemClick: (id: string) => void
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
  const triggerRef = useRef<HTMLElement | null>(null)
  const popoverRef = useRef<HTMLDivElement | null>(null)
  const status = count > 0 ? 'attention' : 'dormant'

  useEffect(() => {
    if (!isOpen) {
      triggerRef.current?.focus()
      return
    }

    popoverRef.current?.focus()

    function handleDocumentKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        setIsOpen(false)
      }
    }

    document.addEventListener('keydown', handleDocumentKeyDown)
    return () => {
      document.removeEventListener('keydown', handleDocumentKeyDown)
    }
  }, [isOpen])

  return (
    <div>
      <PButton
        type="button"
        ref={(element) => {
          triggerRef.current = element as HTMLElement | null
        }}
        data-testid="dr-indicator"
        data-status={status}
        aria-label={`Pending decision requests: ${count}`}
        variant="secondary"
        onClick={() => setIsOpen((current) => !current)}
      >
        DR {count}
      </PButton>

      {isOpen ? (
        <div
          ref={popoverRef}
          data-testid="dr-popover"
          role="dialog"
          aria-label="Pending decision requests"
          tabIndex={-1}
          style={{
            position: 'fixed',
            top: '72px',
            right: '16px',
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
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}

