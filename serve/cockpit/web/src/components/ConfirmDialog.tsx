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
      <button onClick={onCancel}>Cancel</button>
      <button onClick={onConfirm}>Confirm</button>
    </div>
  )
}
