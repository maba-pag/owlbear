import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useBlocker } from 'react-router'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

import { fetchIdeas, saveIdeas } from '../api/ideas'

function IdeasPage() {
  const [content, setContent] = useState('')
  const [previewMode, setPreviewMode] = useState(false)
  const [lastSavedContent, setLastSavedContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const isDirty = useMemo(() => content !== lastSavedContent, [content, lastSavedContent])
  const blocker = useBlocker(isDirty)

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
    if (!isDirty || saving || loading) {
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
  }, [content, isDirty, loading, saving])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const isSaveKey = event.key.toLowerCase() === 's' && (event.metaKey || event.ctrlKey)
      if (!isSaveKey) {
        return
      }

      event.preventDefault()
      if (!isDirty) {
        return
      }

      void handleSave()
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [handleSave, isDirty])

  useEffect(() => {
    if (!isDirty) {
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
      {blocker.state === 'blocked' ? (
        <div role="alertdialog" aria-modal="true" aria-label="Unsaved changes">
          <p>You have unsaved changes. Leave anyway?</p>
          <button
            type="button"
            onClick={() => {
              blocker.proceed()
            }}
          >
            Leave
          </button>
          <button
            type="button"
            onClick={() => {
              blocker.reset()
            }}
          >
            Cancel
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
        disabled={!isDirty || saving}
      >
        Save
      </button>
    </section>
  )
}

export default IdeasPage
