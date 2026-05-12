import { PButton } from '@porsche-design-system/components-react'

export interface ConflictBannerProps {
  showConflict: boolean
  showConflictOverwrite: boolean
  conflictChangedFields: string[]
  conflictRemoteValues: Record<string, string>
  conflictLocalValues: Record<string, string>
  onAcknowledgeOverwrite: () => void
  onDiscardChanges: () => void
  onForceSave: () => void
}

export default function ConflictBanner({
  showConflict,
  showConflictOverwrite,
  conflictChangedFields,
  conflictRemoteValues,
  conflictLocalValues,
  onAcknowledgeOverwrite,
  onDiscardChanges,
  onForceSave,
}: ConflictBannerProps) {
  if (!showConflict) {
    return null
  }

  return (
    <div data-testid="conflict-modal">
      {conflictChangedFields.map((field) => (
        <div key={field}>
          <div data-testid={`conflict-remote-${field}`}>{conflictRemoteValues[field]}</div>
          <div data-testid={`conflict-local-${field}`}>{conflictLocalValues[field]}</div>
        </div>
      ))}
      {!showConflictOverwrite && (
        <PButton
          data-testid="conflict-acknowledge"
          variant="secondary"
          onClick={onAcknowledgeOverwrite}
        >
          Keep my edits
        </PButton>
      )}
      <PButton data-testid="conflict-refresh" variant="secondary" onClick={onDiscardChanges}>
        Discard changes
      </PButton>
      {showConflictOverwrite && (
        <PButton data-testid="conflict-overwrite" onClick={onForceSave}>Force save</PButton>
      )}
    </div>
  )
}