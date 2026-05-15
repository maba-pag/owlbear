import { useEffect, useRef, useState } from 'react'
import { PButton, PText } from '@porsche-design-system/components-react'
import RepairPanel from './RepairPanel'

export interface ScanItem {
  code: string
  detail: string
  file_path: string
}

export interface HealthBadgeProps {
  items: ScanItem[]
  corruptionCount?: number
  onRepairSuccess?: () => void
}

export default function HealthBadge({ items, corruptionCount = 0, onRepairSuccess }: HealthBadgeProps) {
  const [isOpen, setIsOpen] = useState(false)
  const triggerRef = useRef<HTMLElement | null>(null)
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
        data-testid="health-badge"
        data-region="health"
        data-health={health}
        aria-label={ariaLabel}
        variant="secondary"
        onClick={() => setIsOpen((current) => !current)}
      >
        Health {label}
      </PButton>
      {isOpen ? (
        <div
          ref={popoverRef}
          data-testid="health-badge-popover"
          role="dialog"
          aria-label="Health details"
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
          {corruptionCount > 0 ? (
            <RepairPanel corruptionCount={corruptionCount} onSuccess={onRepairSuccess} files={items} />
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

