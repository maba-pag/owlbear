/**
 * Save-confirmed indicator — task #1624
 *
 * Covers:
 *   AC2 — After a successful save in TaskFieldsEditor where form was dirty,
 *          [data-testid='save-confirmed'] becomes visible for 2000ms (±500ms),
 *          surviving same-task refetch without unmount. Resets immediately on
 *          task-switch (different task.id).
 *   AC3 — When onSave resolves false (handled mutation failure):
 *          (a) initial dirty save resolves false → indicator never appears;
 *          (b) already-visible indicator is actively cleared and timer cancelled.
 *          Tests MUST use .mockResolvedValue(false) — NOT .mockRejectedValue().
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
        ...rest
      }: {
        label?: string
        value?: string
        onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
        [key: string]: unknown
      }) => (
        <input
          aria-label={label}
          value={value ?? ''}
          onChange={onChange}
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
        ...rest
      }: {
        label?: string
        value?: string
        onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
        [key: string]: unknown
      }) => (
        <textarea
          aria-label={label}
          value={value ?? ''}
          onChange={onChange}
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

  // ─── Timing: save-confirmed auto-resets at 2000ms after same-task refresh ─

  it('save-confirmed auto-resets ~2000ms after surviving a same-task data refresh', async () => {
    // Full lifecycle: save → indicator appears → same-task data refresh →
    // indicator survives the refresh → indicator disappears at ~2000ms.
    //
    // The rerender is wrapped in await act() so the useEffect triggered by
    // task.updated fires during the act() call, not after the assertion.
    // This makes the test correctly detect when the effect clears saveConfirmed.
    //
    // FAILS on current code: the sync effect unconditionally calls
    // setSaveConfirmed(false) when task.updated changes, so the indicator is
    // gone immediately after the act(rerender) completes — the assertion
    // "indicator still visible after refresh" fails.
    // After fix: setSaveConfirmed(false) is guarded by task.id change, so
    // the indicator survives the same-task refresh and disappears at 2000ms.

    vi.useFakeTimers()
    const onSave = vi.fn().mockResolvedValue(true)
    const { container, rerender } = renderEditor({ onSave })

    makeFieldDirty(container)
    clickSave(container)

    // Wait for the indicator to appear after a successful save (onSave returns true).
    await act(async () => { await Promise.resolve() })
    expect(container.querySelector('[data-testid="save-confirmed"]')).not.toBeNull()

    // Simulate a CockpitProvider same-task refetch: same id=42, new updated timestamp.
    // Wrap in await act() to flush the useEffect triggered by the dep change.
    const refreshedTask: TaskDetail = { ...TASK, updated: '2026-05-01T12:01:00+00:00' }
    await act(async () => {
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
    })

    // FAILS on current code: the sync effect [task.id, task.updated, ...] fires
    // inside the act() call above (because task.updated changed) and calls
    // setSaveConfirmed(false) unconditionally — indicator is already gone here.
    // After fix: setSaveConfirmed(false) is guarded by task.id switch, so
    // same-task refresh does NOT clear the indicator.
    expect(container.querySelector('[data-testid="save-confirmed"]')).not.toBeNull()

    // The 2000ms auto-reset timer started at save time must still fire after the refresh.
    await act(async () => { vi.advanceTimersByTime(2001) })
    expect(container.querySelector('[data-testid="save-confirmed"]')).toBeNull()
  })
})

// ════════════════════════════════════════════════════════════════════════════
// TestFromAC_SaveConfirmedFailure
// AC3: When onSave resolves false (handled mutation failure), save-confirmed
//      does NOT appear. If already visible from a prior success, it is
//      actively cleared and its pending timer cancelled.
//      Tests MUST model failure as resolving false — NOT rejecting.
//
// FAILS on current code: handleSave() has no else-if branch that calls
// setSaveConfirmed(false) when mutationSucceeded === false. The catch block
// only fires on thrown exceptions; real useTaskMutation failure paths resolve
// false without throwing, so an already-visible indicator is never cleared.
// ════════════════════════════════════════════════════════════════════════════

describe('TestFromAC_SaveConfirmedFailure', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  // ─── AC3: already-visible indicator cleared when subsequent save resolves false

  it('save-confirmed is cleared when a subsequent save resolves false', async () => {
    // First save: resolves undefined (success) → indicator appears.
    // Second save: resolves false (handled mutation failure) → indicator must be cleared.
    //
    // FAILS on current code: handleSave()'s try block has no branch for the
    // false-return case — the if condition is skipped, catch never fires, and
    // saveConfirmed remains true from the prior success.
    const onSave = vi.fn()
      .mockResolvedValueOnce(undefined)  // first call → success
      .mockResolvedValueOnce(false)       // second call → handled mutation failure

    const { container } = renderEditor({ onSave })

    // ── First save: success path ────────────────────────────────────────────
    makeFieldDirty(container)
    clickSave(container)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="save-confirmed"]')).not.toBeNull()
    })

    // ── Second save: handled-failure path (resolves false) ──────────────────
    // The form is still dirty (local title state ≠ task.title prop) so
    // shouldShowSaveConfirmed=true and onSave is called again.
    clickSave(container)

    // FAILS on current code: indicator remains visible because the false-return
    // path falls through without calling setSaveConfirmed(false).
    await waitFor(() => {
      expect(container.querySelector('[data-testid="save-confirmed"]')).toBeNull()
    })
  })

  // ─── AC3(a): initial dirty save resolves false → indicator never appears

  it('save-confirmed never appears on initial dirty save that resolves false', async () => {
    // AC3(a): first dirty save resolves false (handled mutation failure from the start).
    // The indicator must never appear — not even momentarily.
    // Models the real useTaskMutation false-return path (not exception/rejection).
    const onSave = vi.fn().mockResolvedValue(false)
    const { container } = renderEditor({ onSave })

    makeFieldDirty(container)
    clickSave(container)

    // Allow all microtasks and state updates to settle.
    await act(async () => { await Promise.resolve() })

    // Indicator must remain absent: shouldShowSaveConfirmed is true but
    // mutationSucceeded !== false is false, so setSaveConfirmed(true) never fires.
    expect(container.querySelector('[data-testid="save-confirmed"]')).toBeNull()
  })

  // ─── AC3(b): pending timer cancelled when save resolves false

  it('pending save-confirmed timer is cancelled when subsequent save resolves false', async () => {
    // Full lifecycle with fake timers:
    //   1. First save (success) → indicator visible, 2000ms timer running.
    //   2. At 1000ms: second save resolves false → indicator must clear immediately.
    //   3. At 3000ms: indicator still null — timer was cancelled, not just ignored.
    //
    // FAILS on current code: the false-return path in handleSave() does not call
    // setSaveConfirmed(false) or clearTimeout(), so the indicator stays visible
    // after the second save, and the timer eventually clears it at 2000ms.
    vi.useFakeTimers()

    const onSave = vi.fn()
      .mockResolvedValueOnce(undefined)  // first call → success
      .mockResolvedValueOnce(false)       // second call → handled mutation failure

    const { container } = renderEditor({ onSave })

    // ── First save: success path ────────────────────────────────────────────
    makeFieldDirty(container)
    clickSave(container)

    await act(async () => { await Promise.resolve() })
    expect(container.querySelector('[data-testid="save-confirmed"]')).not.toBeNull()

    // Advance 1000ms — indicator still visible, timer has 1000ms remaining.
    await act(async () => { vi.advanceTimersByTime(1000) })
    expect(container.querySelector('[data-testid="save-confirmed"]')).not.toBeNull()

    // ── Second save at t=1000ms: handled-failure path (resolves false) ──────
    clickSave(container)
    await act(async () => { await Promise.resolve() })

    // FAILS on current code: indicator not cleared by false-return; it stays visible.
    expect(container.querySelector('[data-testid="save-confirmed"]')).toBeNull()

    // Advance 2000ms more (total t=3000ms) — timer was cancelled, so indicator
    // must stay null and not re-appear due to a stale timer callback.
    await act(async () => { vi.advanceTimersByTime(2000) })
    expect(container.querySelector('[data-testid="save-confirmed"]')).toBeNull()
  })
})

// ════════════════════════════════════════════════════════════════════════════
// TestFromAC_SaveConfirmedTaskSwitch
// AC2: Resets immediately on task-switch (different task.id).
//      Proof: rerender with different task.id → indicator gone immediately.
//
// The isTaskSwitch guard in TaskFieldsEditor's sync effect calls
// setSaveConfirmed(false) when previousTaskIdRef.current !== task.id.
// ════════════════════════════════════════════════════════════════════════════

describe('TestFromAC_SaveConfirmedTaskSwitch', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('save-confirmed is cleared immediately when rerendered with a different task.id', async () => {
    // Setup: indicator visible after a successful dirty save.
    const onSave = vi.fn().mockResolvedValue(undefined)
    const { container, rerender } = renderEditor({ onSave })

    makeFieldDirty(container)
    clickSave(container)

    await waitFor(() => {
      expect(container.querySelector('[data-testid="save-confirmed"]')).not.toBeNull()
    })

    // Simulate a task-switch: rerender with a different task.id.
    const switchedTask: TaskDetail = {
      ...TASK,
      id: 99,
      title: 'Different task',
      updated: '2026-05-02T10:00:00+00:00',
    }

    await act(async () => {
      rerender(
        <PorscheDesignSystemProvider>
          <TaskFieldsEditor
            task={switchedTask}
            priorities={PRIORITIES}
            conflictLocalDraft={null}
            conflictRemoteTaskId={null}
            serverValidationMessage={null}
            clearConflictIfTaskChanged={vi.fn()}
            onSave={onSave}
          />
        </PorscheDesignSystemProvider>,
      )
    })

    // Indicator must be gone immediately after the task-switch rerender
    // because the sync effect fires setSaveConfirmed(false) when isTaskSwitch=true.
    expect(container.querySelector('[data-testid="save-confirmed"]')).toBeNull()
  })
})
