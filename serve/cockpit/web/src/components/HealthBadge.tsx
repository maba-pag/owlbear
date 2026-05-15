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
  const top = Math.round(rect.bottom + 8)
  const left = Math.round(Math.max(viewportPadding, rect.left))
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
  const issueCount = items.length
  const isHealthy = issueCount === 0
  const health = isHealthy ? 'green' : 'red'
  const ariaLabel = isHealthy ? 'Health: OK' : `Health: ${issueCount} issues`
  const label = isHealthy ? 'OK' : `${issueCount} issues`

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
        data-testid="health-badge"
        data-region="health"
        data-health={health}
        aria-label={ariaLabel}
        onClick={() => setIsOpen((current) => !current)}
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
            <PText>No issues</PText>
          ) : (
            <ul>
              {items.map((item, index) => (
                <li key={`${item.file_path}-${item.code}-${index}`}>
                  <span>{item.file_path}</span>
                  <span>{item.code}</span>
                  <span>{item.detail}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}

