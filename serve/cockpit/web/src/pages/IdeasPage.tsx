import { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { UNSAFE_NavigationContext } from 'react-router'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

import { fetchIdeas, saveIdeas } from '../api/ideas'

type NavigationTransaction = {
  retry: () => void
}

type BlockNavigator = {
  block?: (blocker: (tx: NavigationTransaction) => void) => () => void
  push?: (to: string, state?: unknown) => void
  replace?: (to: string, state?: unknown) => void
  go?: (delta: number) => void
}

function IdeasPage() {
  const [content, setContent] = useState('')
  const [previewMode, setPreviewMode] = useState(false)
  const [lastSavedContent, setLastSavedContent] = useState('')
  const [conflictContent, setConflictContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const pendingTransitionRef = useRef<(() => void) | null>(null)
  const contentRef = useRef('')
  const lastSavedContentRef = useRef('')
  const navigationContext = useContext(UNSAFE_NavigationContext)

  const isDirty = useMemo(() => content !== lastSavedContent, [content, lastSavedContent])
  const hasConflict = conflictContent !== null
  const navigator = (navigationContext?.navigator ?? {}) as BlockNavigator

  useEffect(() => {
    contentRef.current = content
  }, [content])

  useEffect(() => {
    lastSavedContentRef.current = lastSavedContent
  }, [lastSavedContent])

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const response = await fetchIdeas()
        if (cancelled) {
          return
        }
        setContent(response.content)
        setLastSavedContent(response.content)
        setErrorMessage(null)
      } catch (error) {
        if (cancelled) {
          return
        }
        const message = error instanceof Error ? error.message : 'Failed to load ideas'
        setErrorMessage(message)
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!loading && !errorMessage && !previewMode) {
      textareaRef.current?.focus()
    }
  }, [errorMessage, loading, previewMode])

  const handleSave = useCallback(async () => {
    if (!isDirty || saving || loading || hasConflict) {
      return
    }

    setSaving(true)
    try {
      await saveIdeas(content)
      setLastSavedContent(content)
      setErrorMessage(null)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save ideas'
      setErrorMessage(message)
    } finally {
      setSaving(false)
    }
  }, [content, hasConflict, isDirty, loading, saving])

  useEffect(() => {
    const refetchIdeas = async () => {
      const triggerContent = contentRef.current
      const triggerLastSaved = lastSavedContentRef.current
      const wasDirtyAtTrigger = triggerContent !== triggerLastSaved

      try {
        const response = await fetchIdeas()

        if (!wasDirtyAtTrigger) {
          setConflictContent(null)
          setContent(response.content)
          setLastSavedContent(response.content)
          return
        }

        if (response.content !== triggerLastSaved) {
          setConflictContent(response.content)
        }
      } catch {
        // Background refetch failure is intentionally silent.
      }
    }

    const onVisibilityChange = () => {
      if (document.visibilityState !== 'visible') {
        return
      }

      void refetchIdeas()
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const isSaveKey = event.key.toLowerCase() === 's' && (event.metaKey || event.ctrlKey)
      if (!isSaveKey) {
        return
      }

      event.preventDefault()
      if (!isDirty || hasConflict) {
        return
      }

      void handleSave()
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [handleSave, hasConflict, isDirty])

  const handleConflictOverwrite = useCallback(() => {
    if (conflictContent === null) {
      return
    }

    setLastSavedContent(conflictContent)
    setConflictContent(null)
  }, [conflictContent])

  const handleConflictDiscard = useCallback(() => {
    if (conflictContent === null) {
      return
    }

    setContent(conflictContent)
    setLastSavedContent(conflictContent)
    setConflictContent(null)
  }, [conflictContent])

  useEffect(() => {
    if (!isDirty) {
      pendingTransitionRef.current = null
      setShowUnsavedDialog(false)
      return
    }

    if (!navigator.block) {
      return
    }

    const unblock = navigator.block((tx) => {
      if (pendingTransitionRef.current !== null) {
        return
      }
      pendingTransitionRef.current = () => {
        unblock()
        tx.retry()
      }
      setShowUnsavedDialog(true)
    })

    return () => {
      unblock()
      pendingTransitionRef.current = null
      setShowUnsavedDialog(false)
    }
  }, [isDirty, navigator])

  useEffect(() => {
    if (!isDirty || navigator.block) {
      return
    }

    const originalPush = navigator.push
    const originalReplace = navigator.replace
    const originalGo = navigator.go

    const queueTransition = (retry: () => void) => {
      if (pendingTransitionRef.current !== null) {
        return
      }
      pendingTransitionRef.current = retry
      setShowUnsavedDialog(true)
    }

    if (originalPush) {
      navigator.push = (to, state) => {
        queueTransition(() => {
          originalPush(to, state)
        })
      }
    }

    if (originalReplace) {
      navigator.replace = (to, state) => {
        queueTransition(() => {
          originalReplace(to, state)
        })
      }
    }

    if (originalGo) {
      navigator.go = (delta) => {
        queueTransition(() => {
          originalGo(delta)
        })
      }
    }

    return () => {
      if (originalPush) {
        navigator.push = originalPush
      }
      if (originalReplace) {
        navigator.replace = originalReplace
      }
      if (originalGo) {
        navigator.go = originalGo
      }
      pendingTransitionRef.current = null
      setShowUnsavedDialog(false)
    }
  }, [isDirty, navigator])

  useEffect(() => {
    if (!isDirty) {
      pendingTransitionRef.current = null
      setShowUnsavedDialog(false)
      return
    }

    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
    }

    window.addEventListener('beforeunload', onBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
    }
  }, [isDirty])

  const handleLeavePage = useCallback(() => {
    const proceed = pendingTransitionRef.current
    pendingTransitionRef.current = null
    setShowUnsavedDialog(false)
    proceed?.()
  }, [])

  const handleStayOnPage = useCallback(() => {
    pendingTransitionRef.current = null
    setShowUnsavedDialog(false)
  }, [])

  if (loading) {
    return (
      <section>
        <div data-testid="ideas-loading" role="status">
          Loading ideas...
        </div>
      </section>
    )
  }

  if (errorMessage && !saving && content.length === 0 && lastSavedContent.length === 0) {
    return (
      <section>
        <div data-testid="ideas-error" role="alert">
          {errorMessage}
        </div>
      </section>
    )
  }

  return (
    <section>
      {showUnsavedDialog ? (
        <div role="alertdialog" aria-modal="true" aria-label="Unsaved changes">
          <p>You have unsaved changes. Leave anyway?</p>
          <button type="button" onClick={handleLeavePage}>
            Leave
          </button>
          <button type="button" onClick={handleStayOnPage}>
            Cancel
          </button>
        </div>
      ) : null}
      {hasConflict ? (
        <div data-testid="ideas-conflict-notice" role="alert">
          <p>Ideas were updated externally.</p>
          <button
            type="button"
            data-testid="ideas-conflict-overwrite"
            onClick={handleConflictOverwrite}
          >
            Overwrite
          </button>
          <button
            type="button"
            data-testid="ideas-conflict-discard"
            onClick={handleConflictDiscard}
          >
            Discard & Reload
          </button>
        </div>
      ) : null}
      {errorMessage ? (
        <div data-testid="ideas-error" role="alert">
          {errorMessage}
        </div>
      ) : null}
      {isDirty ? <div data-testid="ideas-dirty">Unsaved changes</div> : null}
      <button
        type="button"
        data-testid="ideas-preview-toggle"
        onClick={() => {
          setPreviewMode((value) => !value)
        }}
      >
        {previewMode ? 'Edit' : 'Preview'}
      </button>
      {previewMode ? (
        <div data-testid="ideas-preview">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
            {content}
          </ReactMarkdown>
        </div>
      ) : (
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(event) => {
            setContent(event.target.value)
          }}
          placeholder="Capture ideas here..."
        />
      )}
      <button
        type="button"
        data-testid="ideas-save"
        onClick={() => {
          void handleSave()
        }}
        disabled={!isDirty || saving || hasConflict}
      >
        Save
      </button>
    </section>
  )
}

export default IdeasPage
