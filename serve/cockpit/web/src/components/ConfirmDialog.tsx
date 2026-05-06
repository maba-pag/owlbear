import { PButton } from '@porsche-design-system/components-react'

export interface ConfirmDialogProps {
  type: 'move-backward' | 'unblock' | 'unclaim'
  blockReason?: string | null
  onCancel: () => void
  onConfirm: () => void
}

export default function ConfirmDialog({ type, blockReason, onCancel, onConfirm }: ConfirmDialogProps) {
  return (
    <div data-testid="confirm-dialog">
      {type === 'unblock' && blockReason && <span>{blockReason}</span>}
      <PButton variant="secondary" onClick={onCancel}>Cancel</PButton>
      <PButton onClick={onConfirm}>Confirm</PButton>
    </div>
  )
}
