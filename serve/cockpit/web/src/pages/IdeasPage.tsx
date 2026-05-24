import { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { UNSAFE_NavigationContext } from 'react-router'
import { PButton, PModal } from '@porsche-design-system/components-react'
import MarkdownPreview from '../components/MarkdownPreview'

import { fetchIdeas, saveIdeas } from '../api/ideas'
import { WorkspaceHeader } from '../components/WorkspaceHeader'

type NavigationTransaction = {
  retry: () => void
}

type BlockNavigator = {
  block?: (blocker: (tx: NavigationTransaction) => void) => () => void
  push?: (to: string, state?: unknown) => void
  replace?: (to: string, state?: unknown) => void
  go?: (delta: number) => void
}

type IdeasConflictSnapshot = {
  content: string
  updatedAt: string | null
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en').format(value)
}

function formatLastSavedAt(updatedAt: string | null): string {
  if (!updatedAt) {
    return 'Not saved yet'
  }

  const timestamp = Date.parse(updatedAt)
  if (!Number.isFinite(timestamp)) {
    return 'Saved recently'
  }

  const elapsedMs = Math.max(0, Date.now() - timestamp)
  const elapsedMinutes = Math.floor(elapsedMs / 60_000)
  if (elapsedMinutes < 1) {
    return 'just now'
  }

  if (elapsedMinutes < 60) {
    return `${elapsedMinutes}m ago`
  }

  const elapsedHours = Math.floor(elapsedMinutes / 60)
  if (elapsedHours < 24) {
    return `${elapsedHours}h ago`
  }

  const elapsedDays = Math.floor(elapsedHours / 24)
  return `${elapsedDays}d ago`
}

function IdeasPage() {
  const [content, setContent] = useState('')
  const [previewMode, setPreviewMode] = useState(true)
  const [lastSavedContent, setLastSavedContent] = useState('')
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null)
  const [conflictSnapshot, setConflictSnapshot] = useState<IdeasConflictSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false)
  const [ideasCanScrollDown, setIdeasCanScrollDown] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const previewRef = useRef<HTMLDivElement | null>(null)
  const pendingTransitionRef = useRef<(() => void) | null>(null)
  const contentRef = useRef('')
  const lastSavedContentRef = useRef('')
  const stayButtonRef = useRef<HTMLElement | null>(null)
  const navigationContext = useContext(UNSAFE_NavigationContext)

  const isDirty = useMemo(() => content !== lastSavedContent, [content, lastSavedContent])
  const hasConflict = conflictSnapshot !== null
  const navigator = (navigationContext?.navigator ?? {}) as BlockNavigator
  const lineCount = useMemo(
    () => (content.length === 0 ? 0 : content.split(/\r\n|\r|\n/).length),
    [content],
  )
  const wordCount = useMemo(() => {
    const words = content.trim().match(/\S+/g)
    return words?.length ?? 0
  }, [content])
  const saveDisabled = !isDirty || saving || hasConflict
  const lastSavedLabel = useMemo(() => formatLastSavedAt(lastSavedAt), [lastSavedAt])

  const updateIdeasScrollCue = useCallback(() => {
    const surface = previewMode ? previewRef.current : textareaRef.current
    setIdeasCanScrollDown(Boolean(surface && surface.scrollHeight - surface.scrollTop - surface.clientHeight > 1))
  }, [previewMode])

  useEffect(() => {
    contentRef.current = content
  }, [content])

  useEffect(() => {
    updateIdeasScrollCue()
  }, [content, loading, previewMode, updateIdeasScrollCue])

  useEffect(() => {
    window.addEventListener('resize', updateIdeasScrollCue)
    return () => {
      window.removeEventListener('resize', updateIdeasScrollCue)
    }
  }, [updateIdeasScrollCue])

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
        setLastSavedAt(response.updated_at ?? null)
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

  useEffect(() => {
    if (showUnsavedDialog) {
      stayButtonRef.current?.focus()
    }
  }, [showUnsavedDialog])

  const handleSave = useCallback(async () => {
    if (!isDirty || saving || loading || hasConflict) {
      return
    }

    setSaving(true)
    try {
      const updatedAt = await saveIdeas(content)
      setLastSavedContent(content)
      setLastSavedAt(updatedAt ?? new Date().toISOString())
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
          const isDirtyAtResolve = contentRef.current !== lastSavedContentRef.current
          const baselineChangedSinceTrigger = lastSavedContentRef.current !== triggerLastSaved
          if (isDirtyAtResolve || baselineChangedSinceTrigger) {
            return
          }

          setConflictSnapshot(null)
          setContent(response.content)
          setLastSavedContent(response.content)
          setLastSavedAt(response.updated_at ?? null)
          return
        }

        if (response.content !== triggerLastSaved) {
          setConflictSnapshot({ content: response.content, updatedAt: response.updated_at ?? null })
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
    if (conflictSnapshot === null) {
      return
    }

    setLastSavedContent(conflictSnapshot.content)
    setLastSavedAt(conflictSnapshot.updatedAt)
    setConflictSnapshot(null)
  }, [conflictSnapshot])

  const handleConflictDiscard = useCallback(() => {
    if (conflictSnapshot === null) {
      return
    }

    setContent(conflictSnapshot.content)
    setLastSavedContent(conflictSnapshot.content)
    setLastSavedAt(conflictSnapshot.updatedAt)
    setConflictSnapshot(null)
  }, [conflictSnapshot])

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
      <section className="flex h-full min-h-0 flex-col p-static-md text-primary" data-region="ideas-workspace">
        <div
          data-testid="ideas-loading"
          role="status"
          className="flex h-full min-h-[320px] items-center justify-center rounded-lg border border-contrast-low bg-surface text-sm font-semibold text-primary"
        >
          Loading ideas...
        </div>
      </section>
    )
  }

  if (errorMessage && !saving && content.length === 0 && lastSavedContent.length === 0) {
    return (
      <section className="flex h-full min-h-0 flex-col p-static-md text-primary" data-region="ideas-workspace">
        <div
          data-testid="ideas-error"
          role="alert"
          className="flex h-full min-h-[320px] flex-col justify-center gap-static-sm rounded-lg border border-error bg-error-low p-static-lg text-primary"
        >
          <span className="text-xs font-semibold uppercase text-error">Ideas unavailable</span>
          <h1 className="m-0 text-2xl font-semibold leading-tight text-primary">
            Could not open the notebook
          </h1>
          <p className="max-w-[56ch] text-sm leading-normal text-primary">{errorMessage}</p>
        </div>
      </section>
    )
  }

  return (
    <section className="relative flex h-full min-h-0 flex-col overflow-hidden rounded-lg bg-canvas text-primary shadow-sm" data-region="ideas-workspace" aria-labelledby="ideas-title">
      {showUnsavedDialog ? (
        <PModal
          data-testid="ideas-unsaved-dialog"
          role="alertdialog"
          aria-modal="true"
          open
          tabIndex={-1}
          disableBackdropClick
          dismissButton={false}
          aria={{ role: 'alertdialog', 'aria-label': 'Leave this notebook?' }}
          onDismiss={handleStayOnPage}
        >
          <div className="grid w-[min(440px,calc(100vw-2rem))] gap-static-md text-primary">
            <div className="grid gap-static-xs rounded-lg border border-error bg-error-low p-static-md">
              <span className="text-xs font-semibold uppercase text-error">Unsaved draft</span>
              <h2 id="ideas-unsaved-title" className="m-0 text-xl font-semibold leading-tight text-primary">
                Leave this notebook?
              </h2>
              <p id="ideas-unsaved-description" className="m-0 text-sm leading-normal text-primary">
                You have unsaved changes. Leave anyway?
              </p>
            </div>
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={handleLeavePage}>
                Leave
              </PButton>
              <PButton ref={stayButtonRef} type="button" onClick={handleStayOnPage}>
                Cancel
              </PButton>
            </div>
          </div>
        </PModal>
      ) : null}
      <WorkspaceHeader
        title="Ideas"
        titleId="ideas-title"
      />

      <div className="flex min-h-0 flex-1 flex-col gap-static-md p-static-md">
        {hasConflict ? (
          <div
            data-testid="ideas-conflict-notice"
            role="alert"
            className="flex flex-wrap items-center justify-between gap-static-sm rounded-lg border border-error bg-error-low p-static-md text-primary"
          >
            <div className="grid gap-1">
              <span className="text-sm font-semibold text-primary">Ideas were updated externally.</span>
              <span className="text-xs text-primary">Choose which version becomes the saved baseline.</span>
            </div>
            <div className="flex flex-wrap gap-static-xs">
              <PButton
                type="button"
                data-testid="ideas-conflict-overwrite"
                variant="secondary"
                compact
                onClick={handleConflictOverwrite}
              >
                Overwrite
              </PButton>
              <PButton
                type="button"
                data-testid="ideas-conflict-discard"
                compact
                onClick={handleConflictDiscard}
              >
                Discard & Reload
              </PButton>
            </div>
          </div>
        ) : null}
        {errorMessage ? (
          <div
            data-testid="ideas-error"
            role="alert"
            className="rounded-lg border border-error bg-error-low p-static-sm text-sm font-semibold text-primary"
          >
            {errorMessage}
          </div>
        ) : null}

        <div className="grid min-h-0 flex-1 gap-static-md lg:grid-cols-[minmax(0,1fr)_minmax(260px,320px)]">
        <div data-testid="ideas-editor-shell" className="relative flex min-h-0 flex-col overflow-hidden rounded-lg border border-contrast-low bg-canvas">
          <div data-testid="ideas-editor-toolbar" className="flex flex-wrap items-start justify-start gap-static-sm border-b border-contrast-low bg-canvas px-static-sm py-static-sm sm:items-center sm:justify-between sm:px-static-md">
            <div className="flex min-w-0 flex-wrap items-center gap-static-xs text-xs font-semibold uppercase text-primary">
              <span>{previewMode ? 'Markdown preview' : 'Editor'}</span>
              <span aria-hidden="true">/</span>
              <span>{formatNumber(lineCount)} lines</span>
            </div>
            <div data-testid="ideas-toolbar-actions" className="flex w-full min-w-0 flex-wrap items-center gap-static-xs sm:w-auto sm:justify-end">
              {isDirty ? (
                <span data-testid="ideas-dirty" className="rounded-full bg-info-low px-static-xs py-1 text-xs font-semibold text-primary">
                  Unsaved changes
                </span>
              ) : null}
              <PButton
                type="button"
                data-testid="ideas-preview-toggle"
                variant="secondary"
                compact
                icon={previewMode ? 'edit' : 'view'}
                onClick={() => {
                  setPreviewMode((value) => !value)
                }}
              >
                {previewMode ? 'Edit' : 'Preview'}
              </PButton>
              <PButton
                type="button"
                data-testid="ideas-save"
                compact
                icon="save"
                onClick={() => {
                  void handleSave()
                }}
                disabled={saveDisabled}
                aria-disabled={saveDisabled ? 'true' : undefined}
              >
                {saving ? 'Saving...' : 'Save'}
              </PButton>
            </div>
          </div>
          {previewMode ? (
            <div
              ref={previewRef}
              data-testid="ideas-preview"
              className="min-h-0 flex-1 overflow-auto p-static-md"
              onScroll={updateIdeasScrollCue}
            >
              <MarkdownPreview>{content}</MarkdownPreview>
            </div>
          ) : (
            <textarea
              ref={textareaRef}
              value={content}
              aria-label="Ideas draft"
              data-pds-exception="ideas-markdown-editor"
              className="min-h-0 flex-1 resize-none border-0 bg-canvas p-static-md font-mono text-sm leading-relaxed text-primary outline-none focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus)]"
              onChange={(event) => {
                setContent(event.target.value)
              }}
              onScroll={updateIdeasScrollCue}
              placeholder="Capture ideas here..."
            />
          )}
          {ideasCanScrollDown ? (
            <div
              aria-hidden="true"
              data-testid="ideas-scroll-cue"
              className="pointer-events-none absolute inset-x-0 bottom-0 h-10 [background:linear-gradient(to_bottom,transparent,var(--p-color-canvas))]"
            />
          ) : null}
        </div>

        <aside data-testid="ideas-state-panel" className="grid min-w-0 content-start gap-static-md overflow-hidden rounded-lg border border-contrast-low bg-canvas p-static-md text-primary">
          <div className="grid gap-static-xs">
            <span className="text-xs font-semibold uppercase text-primary">Notebook</span>
            <div className="grid gap-static-xs text-sm text-primary">
              <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-static-sm">
                <span className="min-w-0">Changes</span>
                <span className="min-w-0 break-words text-left font-semibold sm:text-right">{isDirty ? 'Changed' : 'Current'}</span>
              </div>
              <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-static-sm">
                <span className="min-w-0">Sync</span>
                <span className="min-w-0 break-words text-left font-semibold sm:text-right">{hasConflict ? 'Needs choice' : 'Ready'}</span>
              </div>
              <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-static-sm">
                <span className="min-w-0">Last saved</span>
                <span data-testid="ideas-last-saved" className="min-w-0 break-words text-left font-semibold sm:text-right">{lastSavedLabel}</span>
              </div>
            </div>
          </div>
          <div className="grid gap-static-xs rounded-md border border-contrast-low bg-surface p-static-sm text-sm leading-normal text-primary">
            <span className="text-xs font-semibold uppercase text-primary">Writing metrics</span>
            <div className="grid gap-static-xs">
              <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-static-sm">
                <span className="min-w-0">Lines</span>
                <span className="min-w-0 break-words text-left font-semibold sm:text-right">{formatNumber(lineCount)}</span>
              </div>
              <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-static-sm">
                <span className="min-w-0">Words</span>
                <span className="min-w-0 break-words text-left font-semibold sm:text-right">{formatNumber(wordCount)}</span>
              </div>
              <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-static-sm">
                <span className="min-w-0">Characters</span>
                <span className="min-w-0 break-words text-left font-semibold sm:text-right">{formatNumber(content.length)}</span>
              </div>
            </div>
          </div>
        </aside>
        </div>
      </div>
    </section>
  )
}

export default IdeasPage
