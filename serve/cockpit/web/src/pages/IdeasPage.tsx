import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { fetchIdeas, saveIdeas } from '../api/ideas'

function IdeasPage() {
  const [content, setContent] = useState('')
  const [lastSavedContent, setLastSavedContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const isDirty = useMemo(() => content !== lastSavedContent, [content, lastSavedContent])

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
    if (!loading && !errorMessage) {
      textareaRef.current?.focus()
    }
  }, [loading, errorMessage])

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
      {errorMessage ? (
        <div data-testid="ideas-error" role="alert">
          {errorMessage}
        </div>
      ) : null}
      {isDirty ? <div data-testid="ideas-dirty">Unsaved changes</div> : null}
      <textarea
        ref={textareaRef}
        value={content}
        onChange={(event) => {
          setContent(event.target.value)
        }}
        placeholder="Capture ideas here..."
      />
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
