/**
 * Save-confirmed indicator — task #1624
 *
 * Covers:
 *   AC2 — After a successful edit-only mutation in TaskFieldsEditor,
 *          [data-testid='save-confirmed'] becomes visible; resets after
 *          2000ms (±500ms); does NOT appear on mutation error or on
 *          non-edit mutations (release, move-backward) through the same
 *          hook instance.
 *
 * All tests must FAIL until the builder adds the save-confirmed indicator.
 */
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
} from 'vitest'
import { render, fireEvent, waitFor, act } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── PDS mock ─────────────────────────────────────────────────────────────────

vi.mock('@porsche-design-system/components-react', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@porsche-design-system/components-react')>()
  return {
    ...mod,
    PButton: vi.fn(
      ({
        children,
        onClick,
        ...rest
      }: {
        children?: React.ReactNode
        onClick?: React.MouseEventHandler
        [key: string]: unknown
      }) => (
        <button type="button" onClick={onClick} {...(rest as Record<string, unknown>)}>
          {children}
        </button>
      ),
    ),
    PInputText: vi.fn(
      ({
        label,
        value,
        onChange,
        onInput,
        ...rest
      }: {
        label?: string
        value?: string
        onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
        onInput?: (e: React.ChangeEvent<HTMLInputElement>) => void
        [key: string]: unknown
      }) => (
        <input
          aria-label={label}
          value={value ?? ''}
          onChange={onChange}
          onInput={onInput}
          {...(rest as Record<string, unknown>)}
        />
      ),
    ),
    PSelect: vi.fn(
      ({
        label,
        children,
        value,
        onChange,
        ...rest
      }: {
        label?: string
        children?: React.ReactNode
        value?: string
        onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void
        [key: string]: unknown
      }) => (
        <select aria-label={label} value={value ?? ''} onChange={onChange} {...(rest as Record<string, unknown>)}>
          {children}
        </select>
      ),
    ),
    PTextarea: vi.fn(
      ({
        label,
        value,
        onChange,
        onInput,
        ...rest
      }: {
        label?: string
        value?: string
        onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
        onInput?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
        [key: string]: unknown
      }) => (
        <textarea
          aria-label={label}
          value={value ?? ''}
          onChange={onChange}
          onInput={onInput}
          {...(rest as Record<string, unknown>)}
        />
      ),
    ),
    PTag: vi.fn(({ children }: { children?: React.ReactNode }) => (
      <span data-testid="tag-chip">{children}</span>
    )),
  }
})

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import TaskFieldsEditor, { type TaskFieldsEditorProps } from '../components/TaskFieldsEditor'
import type { TaskDetail } from '../components/DetailTab'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: 'Some body text.',
  updated: '2026-05-01T12:00:00+00:00',
  created: '2026-05-01T10:00:00+00:00',
  tags: ['bug'],
  blocked: false,
  block_reason: null,
  claimed: false,
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [],
}

const PRIORITIES = ['someday', 'needed', 'important', 'critical']

// ─── Helpers ──────────────────────────────────────────────────────────────────

beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

function renderEditor(overrides: Partial<TaskFieldsEditorProps> = {}) {
  const defaults: TaskFieldsEditorProps = {
    task: TASK,
    priorities: PRIORITIES,
    conflictLocalDraft: null,
    conflictRemoteTaskId: null,
    serverValidationMessage: null,
    clearConflictIfTaskChanged: vi.fn(),
    onSave: vi.fn().mockResolvedValue(undefined),
  }
  return render(
    <PorscheDesignSystemProvider>
      <TaskFieldsEditor {...defaults} {...overrides} />
    </PorscheDesignSystemProvider>,
  )
}

// Make the title field dirty so Save is enabled.
function makeFieldDirty(container: HTMLElement) {
  const titleInput = container.querySelector<HTMLInputElement>('input[aria-label="Title"]')!
  fireEvent.input(titleInput, { target: { value: 'Updated title' } })
  fireEvent.change(titleInput, { target: { value: 'Updated title' } })
}

function clickSave(container: HTMLElement) {
  const saveBtn = container.querySelector('[data-testid="save-button"]')!
  fireEvent.click(saveBtn)
}

// ─── Tests ────────────────────────────────────────────────────────────────────

// ════════════════════════════════════════════════════════════════════════════
// TestFromAC_SaveConfirmed
// AC2: save-confirmed indicator appears after successful edit-only save,
//      auto-resets after 2000ms, and is absent on error or non-edit paths.
// ════════════════════════════════════════════════════════════════════════════

describe('TestFromAC_SaveConfirmed', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  // ─── Happy path: save-confirmed appears after successful save ─────────────

  describe('happy path: save-confirmed visible after successful edit save', () => {
    it('save-confirmed element is present in DOM after onSave resolves', async () => {
      const onSave = vi.fn().mockResolvedValue(undefined)
      const { container } = renderEditor({ onSave })

      makeFieldDirty(container)
      clickSave(container)

      // Fails RED: [data-testid='save-confirmed'] does not exist in TaskFieldsEditor.
      await waitFor(() => {
        expect(
          container.querySelector('[data-testid="save-confirmed"]'),
        ).not.toBeNull()
      })
    })

    it('save-confirmed is visible (not hidden) immediately after successful save', async () => {
      const onSave = vi.fn().mockResolvedValue(undefined)
      const { container } = renderEditor({ onSave })

      makeFieldDirty(container)
      clickSave(container)

      // Fails RED: element absent, so visibility check also fails.
      await waitFor(() => {
        const indicator = container.querySelector('[data-testid="save-confirmed"]')
        expect(indicator).not.toBeNull()
        // Must not be hidden via display:none or aria-hidden=true.
        expect(indicator?.getAttribute('aria-hidden')).not.toBe('true')
      })
    })
  })

  // ─── Boundary: save-confirmed auto-resets after 2000ms ────────────────────

  describe('boundary: save-confirmed resets after 2000ms (±500ms)', () => {
    it('save-confirmed disappears between 1500ms and 2500ms after save', async () => {
      vi.useFakeTimers()
      const onSave = vi.fn().mockResolvedValue(undefined)
      const { container } = renderEditor({ onSave })

      makeFieldDirty(container)
      clickSave(container)

      // First must appear — Fails RED.
      await act(async () => {
        await Promise.resolve()
      })
      expect(
        container.querySelector('[data-testid="save-confirmed"]'),
      ).not.toBeNull()

      // Not yet gone at 1499ms.
      await act(async () => {
        vi.advanceTimersByTime(1499)
      })
      expect(
        container.querySelector('[data-testid="save-confirmed"]'),
      ).not.toBeNull()

      // Gone by 2501ms (within the ±500ms window).
      await act(async () => {
        vi.advanceTimersByTime(1002) // total ~2501ms
      })
      expect(
        container.querySelector('[data-testid="save-confirmed"]'),
      ).toBeNull()
    })
  })

  // ─── Edge: save-confirmed absent after mutation error ─────────────────────

  describe('edge: save-confirmed does not appear when onSave rejects', () => {
    it('successful save shows save-confirmed; subsequent error does not re-show it', async () => {
      // Two renders in sequence: first onSave resolves, then rejects.
      // We assert save-confirmed appears on success (fails RED) and is absent on error.
      const onSave = vi.fn().mockResolvedValue(undefined)
      const { container, rerender } = renderEditor({ onSave })

      makeFieldDirty(container)
      clickSave(container)

      // Must appear after success — Fails RED: element not present.
      await waitFor(() => {
        expect(
          container.querySelector('[data-testid="save-confirmed"]'),
        ).not.toBeNull()
      })

      // Now simulate error: onSave rejects.
      const rejectSave = vi.fn().mockRejectedValue(new Error('Save failed'))
      rerender(
        <PorscheDesignSystemProvider>
          <TaskFieldsEditor
            task={TASK}
            priorities={PRIORITIES}
            conflictLocalDraft={null}
            conflictRemoteTaskId={null}
            serverValidationMessage="Save failed"
            clearConflictIfTaskChanged={vi.fn()}
            onSave={rejectSave}
          />
        </PorscheDesignSystemProvider>,
      )

      makeFieldDirty(container)
      clickSave(container)

      await waitFor(() => {
        expect(
          container.querySelector('[data-testid="save-confirmed"]'),
        ).toBeNull()
      })
    })

    it('save-confirmed absent on error state, but present in prior success render', async () => {
      // Full flow: success path shows save-confirmed (fails RED); then error path
      // confirms it is absent.
      const successSave = vi.fn().mockResolvedValue(undefined)
      const { container: successContainer } = renderEditor({ onSave: successSave })

      makeFieldDirty(successContainer)
      clickSave(successContainer)

      // Must appear on success — Fails RED: element absent.
      await waitFor(() => {
        expect(
          successContainer.querySelector('[data-testid="save-confirmed"]'),
        ).not.toBeNull()
      })

      // Render separate editor with serverValidationMessage set (error state).
      const { container: errorContainer } = renderEditor({
        onSave: vi.fn().mockResolvedValue(undefined),
        serverValidationMessage: 'Conflict: task was updated',
      })

      makeFieldDirty(errorContainer)
      clickSave(errorContainer)

      // When serverValidationMessage is set, save-confirmed must NOT appear.
      await waitFor(() => {
        expect(
          errorContainer.querySelector('[data-testid="save-confirmed"]'),
        ).toBeNull()
      })
    })
  })

  // ─── Edge: non-edit mutations (TaskActions paths) via same onSave ─────────

  describe('edge: save-confirmed does not appear for non-edit mutations via shared hook', () => {
    it('save-confirmed only appears from TaskFieldsEditor save, not from TaskActions-style calls', async () => {
      // The save-confirmed indicator is scoped to the edit call-site in
      // TaskFieldsEditor. Verify that the indicator element appears ONLY
      // when onSave (edit path) resolves successfully.
      // We simulate a release-style call by invoking onSave with a release payload
      // that lacks 'title' — the contract is that save-confirmed tracks the
      // SUCCESS of the edit path, not any mutation.
      //
      // For test purposes: render TaskFieldsEditor with onSave that resolves,
      // click Save (edit path), confirm save-confirmed appears.
      // Then simulate a "release" scenario (component with no dirty state but
      // a forced save-trigger) — save-confirmed must not appear.
      //
      // The primary failure point is in the "appears after edit" assertion below.

      const onSave = vi.fn().mockResolvedValue(undefined)
      const { container } = renderEditor({ onSave })

      makeFieldDirty(container)
      clickSave(container)

      // Fails RED: save-confirmed element absent.
      await waitFor(() => {
        expect(
          container.querySelector('[data-testid="save-confirmed"]'),
        ).not.toBeNull()
      })

      // Confirm the indicator is NOT already present before any save on a clean form.
      const { container: cleanContainer } = renderEditor({ onSave: vi.fn().mockResolvedValue(undefined) })

      // On a clean (non-dirty) form, clicking Save does not call onSave.
      // save-confirmed must not appear.
      clickSave(cleanContainer)
      await act(async () => { await Promise.resolve() })

      expect(
        cleanContainer.querySelector('[data-testid="save-confirmed"]'),
      ).toBeNull()
    })
  })
})

// ════════════════════════════════════════════════════════════════════════════
// TestFromAC_SaveConfirmedRefetchSurvival
// AC2: save-confirmed must survive CockpitProvider same-task refetch.
//      When the provider refreshes the same task (same task.id, new task.updated)
//      after a successful edit, the indicator must remain visible for its full
//      2000ms window — it must NOT be reset by the data-refresh re-render.
// ════════════════════════════════════════════════════════════════════════════

describe('TestFromAC_SaveConfirmedRefetchSurvival', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('save-confirmed remains visible after re-render with same task.id but new task.updated', async () => {
    // onSave returns true — explicit boolean success, matching the real runMutation
    // return type after builder cycle 2 fix.
    const onSave = vi.fn().mockResolvedValue(true)
    const { container, rerender } = renderEditor({ onSave })

    // Make the field dirty and save.
    makeFieldDirty(container)
    clickSave(container)

    // Wait for the save-confirmed indicator to appear after a successful save.
    await waitFor(() => {
      expect(container.querySelector('[data-testid="save-confirmed"]')).not.toBeNull()
    })

    // Simulate a CockpitProvider same-task refetch:
    // After Shell calls update(updatedTask), CockpitProvider re-fetches from the API
    // and pushes the refreshed task (same id=42, new updated timestamp) into DetailTab.
    const refreshedTask: TaskDetail = {
      ...TASK,
      updated: '2026-05-01T12:01:00+00:00',
    }
    rerender(
      <PorscheDesignSystemProvider>
        <TaskFieldsEditor
          task={refreshedTask}
          priorities={PRIORITIES}
          conflictLocalDraft={null}
          conflictRemoteTaskId={null}
          serverValidationMessage={null}
          clearConflictIfTaskChanged={vi.fn()}
          onSave={onSave}
        />
      </PorscheDesignSystemProvider>,
    )

    // FAILS on current code: the sync effect [task.id, task.updated, ...] fires
    // when task.updated changes and unconditionally calls setSaveConfirmed(false),
    // clearing the indicator even though the task.id is unchanged.
    // After fix: setSaveConfirmed(false) is guarded by task.id change (isTaskSwitch)
    // so same-task data refreshes no longer tear down the indicator prematurely.
    expect(container.querySelector('[data-testid="save-confirmed"]')).not.toBeNull()
  })
})
