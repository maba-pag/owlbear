import { useState } from 'react'
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
  const issueCount = items.length
  const isHealthy = issueCount === 0
  const health = isHealthy ? 'green' : 'red'
  const ariaLabel = isHealthy ? 'Health: OK' : `Health: ${issueCount} issues`
  const label = isHealthy ? 'OK' : `${issueCount} issues`

  return (
    <div>
      <PButton
        type="button"
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
        <div data-testid="health-badge-popover" role="dialog" aria-label="Health details">
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
