/**
 * Shell PBanner mutation error feedback (task #1498)
 *
 * Covers:
 *   AC-1 — Shell renders <PBanner> (pbanner-stub selector via mock) with open/heading/
 *           description/state bound from bannerError; open=false when bannerError is null
 *   AC-5 — PBanner onDismiss sets bannerError to null (banner closes)
 *   AC-6 — Shell clears bannerError when KanbanBoard calls onMutationSuccess
 *   AC-7 — Shell clears bannerError in onTaskUpdated handler
 *   AC-8 — bannerError persists across selectedTaskId changes and tab switches
 *   AC-9 — selectedTaskError / task-fetch-error and PBanner coexist independently
 */
import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from 'vitest'
import { render, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted) ──────────────────────────────────────────────────

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))

vi.mock('../components/DRStatusIndicator', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/HealthBadge', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/CleanupPanel', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DecisionViewport', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ResolveModal', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ActivityTab', () => ({
  default: vi.fn(() => <div data-testid="activity-tab-stub" />),
}))
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// PBanner stub: renders a div stub when open=true so assertions can inspect
// heading/description/state without relying on PDS shadow DOM internals.
// onDismiss is attached to click so tests can trigger dismissal synchronously.
vi.mock('@porsche-design-system/components-react', async (importOriginal) => {
  const mod =
    await importOriginal<typeof import('@porsche-design-system/components-react')>()
  return {
    ...mod,
    PBanner: vi.fn(
      ({
        open = false,
        heading = '',
        description = '',
        state = 'info',
        onDismiss,
      }: {
        open?: boolean
        heading?: string
        description?: string
        state?: string
        onDismiss?: (e: CustomEvent<void>) => void
      }) =>
        open ? (
          <div
            data-testid="pbanner-stub"
            data-heading={heading}
            data-description={description}
            data-state={state}
            onClick={() => onDismiss?.(new CustomEvent('dismiss') as CustomEvent<void>)}
          />
        ) : null,
    ),
  }
})

// KanbanBoard mock — captures callback props for direct test invocation.
let capturedOnMutationError:
  | ((heading: string, description: string, state: 'error' | 'warning') => void)
  | undefined
let capturedOnMutationSuccess: (() => void) | undefined
let capturedOnSelectTask: ((taskId: number) => void) | undefined

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(
    (props: {
      onMutationError?: (h: string, d: string, s: 'error' | 'warning') => void
      onMutationSuccess?: () => void
      onSelectTask?: (taskId: number) => void
    }) => {
      capturedOnMutationError = props.onMutationError
      capturedOnMutationSuccess = props.onMutationSuccess
      capturedOnSelectTask = props.onSelectTask
      return <div data-testid="kanban-stub" />
    },
  ),
}))

// DetailTab mock — captures onTaskUpdated so AC-7 can call it directly.
let capturedOnTaskUpdated: ((task: object) => void) | undefined

vi.mock('../components/DetailTab', () => ({
  default: vi.fn((props: { onTaskUpdated?: (task: object) => void }) => {
    capturedOnTaskUpdated = props.onTaskUpdated
    return <div data-testid="detail-tab-stub" />
  }),
}))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { useScanPolling } from '../hooks/useScanPolling'
import { usePendingDRs } from '../hooks/usePendingDRs'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import type { Board } from '../hooks/useBoard'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }],
  priorities: ['someday', 'needed'],
  valid_transitions: { todo: ['in-progress'], 'in-progress': ['todo'] },
}

const UPDATED_TASK_DETAIL = {
  id: 42,
  title: 'Updated task',
  status: 'todo',
  priority: 'needed',
  body: '',
  updated: '2026-05-12T00:00:00+00:00',
  created: '2026-05-11T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
  claimed: false,
  claimed_at: null,
  dep_status: null,
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

beforeAll(() => {
  // PDS form component shim (needed if real PDS buttons are rendered in Shell).
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

function stubHooks() {
  vi.mocked(useBoard).mockReturnValue({
    board: BOARD,
    tasks: [],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks: vi.fn(),
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)
  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof useScanPolling>)
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)
}

function renderShell() {
  // Reset captures before each render.
  capturedOnMutationError = undefined
  capturedOnMutationSuccess = undefined
  capturedOnSelectTask = undefined
  capturedOnTaskUpdated = undefined
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ShellPBanner', () => {
  beforeEach(() => {
    stubHooks()
    // Never-resolving fetch prevents Shell task-fetch effects from settling.
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) =>
        new Promise<never>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError')),
          )
        }),
      ),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── AC-1: Shell renders PBanner bound to bannerError ────────────────────

  describe('AC-1: PBanner rendered and bound to bannerError', () => {
    it('renders pbanner-stub element when onMutationError is called', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnMutationError?.('Move failed', 'Server error', 'error')
      })

      expect(container.querySelector('[data-testid="pbanner-stub"]')).not.toBeNull()
    })

    it('pbanner-stub data-heading reflects bannerError heading', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnMutationError?.('Move failed', 'Network error occurred', 'error')
      })

      expect(
        container.querySelector('[data-testid="pbanner-stub"]')?.getAttribute('data-heading'),
      ).toBe('Move failed')
    })

    it('pbanner-stub data-description reflects bannerError description', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnMutationError?.('Edit failed', 'Validation error detail', 'warning')
      })

      expect(
        container.querySelector('[data-testid="pbanner-stub"]')?.getAttribute('data-description'),
      ).toBe('Validation error detail')
    })

    it('pbanner-stub data-state is "error" when bannerError.state is error', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnMutationError?.('Move failed', 'Server error', 'error')
      })

      expect(
        container.querySelector('[data-testid="pbanner-stub"]')?.getAttribute('data-state'),
      ).toBe('error')
    })

    it('pbanner-stub data-state is "warning" when bannerError.state is warning', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnMutationError?.('Edit failed', 'Validation failed', 'warning')
      })

      expect(
        container.querySelector('[data-testid="pbanner-stub"]')?.getAttribute('data-state'),
      ).toBe('warning')
    })

    it('Shell passes onMutationError prop to KanbanBoard', () => {
      renderShell()
      expect(capturedOnMutationError).toBeDefined()
    })
  })

  // ─── AC-5: PBanner onDismiss sets bannerError to null ────────────────────

  describe('AC-5: PBanner onDismiss clears bannerError', () => {
    it('clicking pbanner-stub triggers onDismiss which sets bannerError to null', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnMutationError?.('Move failed', 'Error', 'error')
      })

      const stub = container.querySelector('[data-testid="pbanner-stub"]')
      expect(stub).not.toBeNull() // fails in RED — no banner rendered yet

      // Click fires onDismiss (wired in stub via onClick).
      await act(async () => {
        stub?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      })

      // After dismiss, bannerError=null → open=false → stub renders null.
      await waitFor(() => {
        expect(container.querySelector('[data-testid="pbanner-stub"]')).toBeNull()
      })
    })
  })

  // ─── AC-6: onMutationSuccess clears bannerError ──────────────────────────

  describe('AC-6: KanbanBoard onMutationSuccess clears bannerError', () => {
    it('Shell passes onMutationSuccess prop to KanbanBoard', () => {
      renderShell()
      expect(capturedOnMutationSuccess).toBeDefined()
    })

    it('Shell clears bannerError when KanbanBoard calls onMutationSuccess', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnMutationError?.('Move failed', 'Error', 'error')
      })

      expect(container.querySelector('[data-testid="pbanner-stub"]')).not.toBeNull()

      await act(async () => {
        capturedOnMutationSuccess?.()
      })

      await waitFor(() => {
        expect(container.querySelector('[data-testid="pbanner-stub"]')).toBeNull()
      })
    })
  })

  // ─── AC-7: onTaskUpdated clears bannerError ───────────────────────────────

  describe('AC-7: Shell clears bannerError in onTaskUpdated handler', () => {
    it('Shell clears bannerError when DetailTab triggers onTaskUpdated callback', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnSelectTask?.(42)
      })

      await waitFor(() => {
        expect(capturedOnTaskUpdated).toBeDefined()
      })

      await act(async () => {
        capturedOnMutationError?.('Edit failed', 'Server error', 'error')
      })

      expect(container.querySelector('[data-testid="pbanner-stub"]')).not.toBeNull()

      await act(async () => {
        capturedOnTaskUpdated?.(UPDATED_TASK_DETAIL)
      })

      await waitFor(() => {
        expect(container.querySelector('[data-testid="pbanner-stub"]')).toBeNull()
      })
    })
  })

  // ─── AC-8: bannerError persists across context changes ───────────────────

  describe('AC-8: bannerError persists across selectedTaskId changes and tab switches', () => {
    it('bannerError is not cleared when selectedTaskId changes', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnMutationError?.('Move failed', 'Error', 'error')
      })

      expect(container.querySelector('[data-testid="pbanner-stub"]')).not.toBeNull()

      // Simulate task selection (triggers setSelectedTaskId — does NOT clear bannerError).
      await act(async () => {
        capturedOnSelectTask?.(42)
      })

      // Banner must still be open after task selection change.
      expect(container.querySelector('[data-testid="pbanner-stub"]')).not.toBeNull()
    })

    it('bannerError is not cleared by tab switch (aria-hidden toggle only)', async () => {
      const { container } = renderShell()

      await act(async () => {
        capturedOnMutationError?.('Move failed', 'Error', 'error')
      })

      expect(container.querySelector('[data-testid="pbanner-stub"]')).not.toBeNull()

      // Simulate tab change event (as Shell's tabChange handler does — only
      // toggles aria-hidden, must not clear bannerError).
      const tabs = container.querySelector('p-tabs')
      await act(async () => {
        tabs?.dispatchEvent(
          new CustomEvent('tabChange', { detail: { activeTabIndex: 1 }, bubbles: true }),
        )
      })

      expect(container.querySelector('[data-testid="pbanner-stub"]')).not.toBeNull()
    })
  })

  // ─── AC-9: task-fetch-error and PBanner coexist independently ────────────

  describe('AC-9: selectedTaskError and PBanner coexist independently', () => {
    it('task-fetch-error and pbanner-stub appear simultaneously when both error conditions hold', async () => {
      // Override fetch: task detail returns 500, all other requests pend.
      vi.stubGlobal(
        'fetch',
        vi.fn(async (url: string, init?: RequestInit) => {
          if (/\/api\/tasks\/\d+$/.test(url)) {
            return {
              ok: false,
              status: 500,
              json: async () => ({ detail: 'Internal server error' }),
              text: async () => 'Internal server error',
            } as unknown as Response
          }
          return new Promise<never>((_resolve, reject) => {
            init?.signal?.addEventListener('abort', () =>
              reject(new DOMException('Aborted', 'AbortError')),
            )
          })
        }),
      )

      const { container } = renderShell()

      // Trigger task fetch error by selecting a task.
      await act(async () => {
        capturedOnSelectTask?.(42)
      })

      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-fetch-error"]')).not.toBeNull()
      })

      // Independently trigger banner via mutation error.
      await act(async () => {
        capturedOnMutationError?.('Move failed', 'Network error', 'error')
      })

      // Both error displays must be present simultaneously.
      expect(container.querySelector('[data-testid="task-fetch-error"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="pbanner-stub"]')).not.toBeNull()
    })
  })
})
