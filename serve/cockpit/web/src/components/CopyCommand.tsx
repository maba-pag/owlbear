import { PIcon, useToastManager } from '@porsche-design-system/components-react'
import { useEffect, useRef, useState, type MouseEvent } from 'react'

interface CopyCommandProps {
  command: string
  className?: string
}

export type CopyState = 'idle' | 'copied' | 'failed'

export function useCopyToClipboard() {
  const [copyState, setCopyState] = useState<CopyState>('idle')
  const resetTimer = useRef<number | null>(null)
  const { addMessage } = useToastManager()

  useEffect(() => () => {
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current)
  }, [])

  const copy = async (value: string, messages: { success: string; failure: string }): Promise<boolean> => {
    let copied = false
    try {
      await navigator.clipboard.writeText(value)
      setCopyState('copied')
      addMessage({ text: messages.success, state: 'success' })
      copied = true
    } catch {
      setCopyState('failed')
      addMessage({ text: messages.failure, state: 'error' })
    }
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current)
    resetTimer.current = window.setTimeout(() => setCopyState('idle'), 1_500)
    return copied
  }

  return { copyState, copy }
}

export default function CopyCommand({ command, className = '' }: CopyCommandProps) {
  const { copyState, copy } = useCopyToClipboard()
  const stateIcon = copyState === 'copied' ? 'check' : copyState === 'failed' ? 'error' : null

  const copyCommand = async (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault()
    event.stopPropagation()
    await copy(command, {
      success: `Copied ${command}`,
      failure: `Could not copy ${command}`,
    })
  }

  return (
    <span className="inline-flex max-w-full align-middle leading-none">
      <button
        type="button"
        className={[
          'relative z-[1] inline-flex max-w-full cursor-copy items-center gap-1 border-0 bg-transparent p-0 text-left leading-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
          copyState === 'copied' ? 'text-success' : copyState === 'failed' ? 'text-error' : 'text-contrast-medium hover:text-primary',
          className,
        ].join(' ')}
        aria-label={`Copy command ${command}`}
        title={copyState === 'copied' ? `Copied ${command}` : copyState === 'failed' ? `Could not copy ${command}` : `Copy ${command}`}
        onClick={(event) => void copyCommand(event)}
      >
        <PIcon className="shrink-0" name="ai-code" size="2xs" color="inherit" aria-hidden="true" />
        <code className="max-w-full break-all text-inherit leading-none">{command}</code>
        {stateIcon ? <PIcon className="shrink-0" name={stateIcon} size="2xs" color="inherit" aria-hidden="true" /> : null}
      </button>
    </span>
  )
}
