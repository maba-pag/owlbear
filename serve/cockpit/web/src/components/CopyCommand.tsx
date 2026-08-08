import { useEffect, useRef, useState, type MouseEvent } from 'react'

interface CopyCommandProps {
  command: string
  className?: string
}

type CopyState = 'idle' | 'copied' | 'failed'

export default function CopyCommand({ command, className = '' }: CopyCommandProps) {
  const [copyState, setCopyState] = useState<CopyState>('idle')
  const resetTimer = useRef<number | null>(null)

  useEffect(() => () => {
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current)
  }, [])

  const copy = async (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault()
    event.stopPropagation()
    try {
      await navigator.clipboard.writeText(command)
      setCopyState('copied')
    } catch {
      setCopyState('failed')
    }
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current)
    resetTimer.current = window.setTimeout(() => setCopyState('idle'), 1_500)
  }

  const announcement = copyState === 'copied'
    ? `Copied ${command}`
    : copyState === 'failed' ? `Could not copy ${command}` : ''

  return (
    <span className="inline-flex max-w-full">
      <button
        type="button"
        className={[
          'relative z-[1] max-w-full cursor-copy border-0 bg-transparent p-0 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
          copyState === 'copied' ? 'text-success' : copyState === 'failed' ? 'text-error' : 'text-contrast-medium hover:text-primary',
          className,
        ].join(' ')}
        aria-label={`Copy command ${command}`}
        title={announcement || `Copy ${command}`}
        onClick={(event) => void copy(event)}
      >
        <code className="block max-w-full break-all text-inherit">{command}</code>
      </button>
      <span className="sr-only" role="status" aria-live="polite">{announcement}</span>
    </span>
  )
}
