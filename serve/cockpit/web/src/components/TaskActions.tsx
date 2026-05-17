import { useEffect, useRef, useState } from 'react'
import { PButton } from '@porsche-design-system/components-react'
import ConfirmDialog from './ConfirmDialog'
import type { TaskDetail } from './DetailTab'
import type { MutationRunOptions } from '../hooks/useTaskMutation'

type ConfirmType = 'move-backward' | 'unblock' | 'unclaim'

export interface TaskActionsProps {
  task: TaskDetail
  backwardTarget: string | null
  runMutation: (
    url: string,
    payload: Record<string, unknown>,
    options: MutationRunOptions,
  ) => Promise<boolean>
}

export default function TaskActions({
  task,
  backwardTarget,
  runMutation,
}: TaskActionsProps) {
  const [confirmType, setConfirmType] = useState<ConfirmType | null>(null)
  const [pendingFocusRestore, setPendingFocusRestore] = useState<HTMLElement | null>(null)
  const confirmTriggerRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (confirmType === null && pendingFocusRestore) {
      if (!pendingFocusRestore.hasAttribute('tabindex')) {
        pendingFocusRestore.setAttribute('tabindex', '-1')
      }
      pendingFocusRestore.focus()
      setPendingFocusRestore(null)
    }
  }, [confirmType, pendingFocusRestore])

  async function handleConfirm() {
    if (confirmType === 'unblock') {
      await runMutation(
        `/api/tasks/${task.id}/edit`,
        { updated: task.updated, block_reason: null },
        { errorHeading: 'Unblock failed' },
      )
      setConfirmType(null)
      return
    }
    if (confirmType === 'unclaim') {
      await runMutation(
        `/api/tasks/${task.id}/release`,
        { updated: task.updated },
        { errorHeading: 'Unclaim failed' },
      )
      setConfirmType(null)
      return
    }
    if (confirmType === 'move-backward') {
      if (backwardTarget) {
        await runMutation(
          `/api/tasks/${task.id}/move`,
          { updated: task.updated, status: backwardTarget },
          { errorHeading: 'Move failed' },
        )
      }
      setConfirmType(null)
    }
  }

  function handleConfirmCancel() {
    const trigger = confirmTriggerRef.current
    setPendingFocusRestore(trigger)
    setConfirmType(null)
  }

  function openConfirm(type: ConfirmType) {
    let triggerId = 'unblock-action'
    if (type === 'move-backward') {
      triggerId = 'move-backward'
    } else if (type === 'unclaim') {
      triggerId = 'unclaim-action'
    }
    confirmTriggerRef.current = document.querySelector(
      `[data-testid="${triggerId}"]`,
    ) as HTMLElement | null
    setConfirmType(type)
  }

  return (
    <>
      {backwardTarget && (
        <PButton
          data-testid="move-backward"
          variant="secondary"
          onClick={() => openConfirm('move-backward')}
        >
          Move Backward
        </PButton>
      )}
      {task.claimed !== false && (
        <PButton
          data-testid="unclaim-action"
          variant="secondary"
          onClick={() => openConfirm('unclaim')}
        >
          Unclaim
        </PButton>
      )}
      {task.blocked && (
        <PButton
          data-testid="unblock-action"
          variant="secondary"
          onClick={() => openConfirm('unblock')}
        >
          Unblock
        </PButton>
      )}

      {confirmType !== null && (
        <ConfirmDialog
          type={confirmType}
          targetStatus={backwardTarget}
          blockReason={task.block_reason}
          onCancel={handleConfirmCancel}
          onConfirm={() => void handleConfirm()}
        />
      )}
    </>
  )
}
