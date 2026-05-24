import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { PButton } from '@porsche-design-system/components-react'
import ConfirmDialog from './ConfirmDialog'
import type { TaskDetail } from './DetailTab'
import type { MutationRunOptions } from '../hooks/useTaskMutation'
import { formatStatusLabel } from '../utils/taskTransitions'

type ConfirmType = 'unblock' | 'unclaim'

export interface TaskActionsProps {
  task: TaskDetail
  moveTargets: string[]
  canArchive: boolean
  runMutation: (
    url: string,
    payload: Record<string, unknown>,
    options: MutationRunOptions,
  ) => Promise<boolean>
  onArchive: (returnFocusTo: HTMLElement | null) => void
}

export default function TaskActions({
  task,
  moveTargets,
  canArchive,
  runMutation,
  onArchive,
}: TaskActionsProps) {
  const [confirmType, setConfirmType] = useState<ConfirmType | null>(null)
  const [moveMenuOpen, setMoveMenuOpen] = useState(false)
  const [pendingFocusRestore, setPendingFocusRestore] = useState<HTMLElement | null>(null)
  const confirmTriggerRef = useRef<HTMLElement | null>(null)
  const moveTriggerRef = useRef<HTMLElement | null>(null)
  const archiveTriggerRef = useRef<HTMLElement | null>(null)
  const moveMenuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (confirmType === null && pendingFocusRestore) {
      if (!pendingFocusRestore.hasAttribute('tabindex')) {
        pendingFocusRestore.setAttribute('tabindex', '-1')
      }
      pendingFocusRestore.focus()
      setPendingFocusRestore(null)
    }
  }, [confirmType, pendingFocusRestore])

  useEffect(() => {
    if (!moveMenuOpen) {
      return undefined
    }

    const firstItem = moveMenuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')
    firstItem?.focus()

    function handlePointerDown(event: PointerEvent) {
      const target = event.target
      if (!(target instanceof Node)) {
        return
      }
      if (moveTriggerRef.current?.contains(target) || moveMenuRef.current?.contains(target)) {
        return
      }
      setMoveMenuOpen(false)
    }

    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        setMoveMenuOpen(false)
        moveTriggerRef.current?.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [moveMenuOpen])

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
  }

  async function handleMove(targetStatus: string) {
    setMoveMenuOpen(false)
    await runMutation(
      `/api/tasks/${task.id}/move`,
      { updated: task.updated, status: targetStatus },
      { errorHeading: 'Move failed' },
    )
  }

  function handleMoveItemKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      event.currentTarget.click()
      return
    }

    const menu = event.currentTarget.parentElement
    if (!menu) {
      return
    }
    const items = Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]'))
    const index = items.indexOf(event.currentTarget)

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      items[(index + 1) % items.length]?.focus()
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      items[(index - 1 + items.length) % items.length]?.focus()
    } else if (event.key === 'Home') {
      event.preventDefault()
      items[0]?.focus()
    } else if (event.key === 'End') {
      event.preventDefault()
      items[items.length - 1]?.focus()
    }
  }

  function handleConfirmCancel() {
    const trigger = confirmTriggerRef.current
    setPendingFocusRestore(trigger)
    setConfirmType(null)
  }

  function openConfirm(type: ConfirmType) {
    let triggerId = 'unblock-action'
    if (type === 'unclaim') {
      triggerId = 'unclaim-action'
    }
    confirmTriggerRef.current = document.querySelector(
      `[data-testid="${triggerId}"]`,
    ) as HTMLElement | null
    setConfirmType(type)
  }

  return (
    <>
      {moveTargets.length > 0 ? (
        <span className="relative inline-flex">
          <PButton
            ref={moveTriggerRef}
            data-testid="task-detail-move-menu-trigger"
            variant="secondary"
            compact
            aria-haspopup="menu"
            aria-expanded={moveMenuOpen ? 'true' : 'false'}
            onClick={() => setMoveMenuOpen((open) => !open)}
          >
            Move
          </PButton>
          {moveMenuOpen ? (
            <div
              ref={moveMenuRef}
              data-testid="task-detail-move-menu"
              role="menu"
              aria-label="Move task"
              className="absolute left-0 top-[calc(100%+0.25rem)] z-30 min-w-[180px] overflow-hidden rounded-md border border-contrast-low bg-surface py-1 shadow-lg"
            >
              {moveTargets.map((target) => (
                <button
                  key={target}
                  type="button"
                  role="menuitem"
                  data-testid="task-detail-move-target"
                  data-status={target}
                  className="block w-full cursor-pointer border-0 bg-transparent px-3 py-2 text-left text-sm text-primary hover:bg-frosted focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus)]"
                  onKeyDown={handleMoveItemKeyDown}
                  onClick={() => void handleMove(target)}
                >
                  Move to {formatStatusLabel(target)}
                </button>
              ))}
            </div>
          ) : null}
        </span>
      ) : null}
      {canArchive ? (
        <PButton
          ref={archiveTriggerRef}
          data-testid="task-detail-archive-action"
          variant="secondary"
          compact
          onClick={() => onArchive(archiveTriggerRef.current)}
        >
          Archive
        </PButton>
      ) : null}
      {task.claimed !== false && (
        <PButton
          data-testid="unclaim-action"
          variant="secondary"
          compact
          onClick={() => openConfirm('unclaim')}
        >
          Unclaim
        </PButton>
      )}
      {task.blocked && (
        <PButton
          data-testid="unblock-action"
          variant="secondary"
          compact
          onClick={() => openConfirm('unblock')}
        >
          Unblock
        </PButton>
      )}

      {confirmType !== null && (
        <ConfirmDialog
          type={confirmType}
          blockReason={task.block_reason}
          onCancel={handleConfirmCancel}
          onConfirm={() => void handleConfirm()}
        />
      )}
    </>
  )
}
