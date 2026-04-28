import { useState } from 'react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

export interface ScanItem {
  code: string
  detail: string
  file_path: string
}

export interface HealthBadgeProps {
  items: ScanItem[]
}

export default function HealthBadge({ items }: HealthBadgeProps) {
  const [isOpen, setIsOpen] = useState(false)
  const issueCount = items.length
  const isHealthy = issueCount === 0
  const health = isHealthy ? 'green' : 'red'
  const ariaLabel = isHealthy ? 'Health: OK' : `Health: ${issueCount} issues`
  const label = isHealthy ? 'OK' : `${issueCount} issues`

  return (
    <PorscheDesignSystemProvider>
      <div>
        <button
          type="button"
          data-testid="health-badge"
          data-region="health"
          data-health={health}
          aria-label={ariaLabel}
          onClick={() => setIsOpen((current) => !current)}
        >
          Health {label}
        </button>
        {isOpen ? (
          <div data-testid="health-badge-popover" role="dialog" aria-label="Health details">
            {items.length === 0 ? (
              <p>No issues</p>
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
    </PorscheDesignSystemProvider>
  )
}
