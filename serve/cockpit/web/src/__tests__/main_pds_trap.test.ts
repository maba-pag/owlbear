/** Durable regression tests for the PDS CDN property trap. */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mined from #1496: the CDN URL remains the application origin during PDS load.

// ─── Module-level mocks for behavioral import tests ────────────────────────────
//
// These are hoisted by Vitest before any test runs so importing main.tsx only
// exercises the bootstrap contract under test.

vi.mock('@porsche-design-system/components-js', () => ({
  load: vi.fn(),
}))

vi.mock('react-dom/client', () => ({
  createRoot: vi.fn(() => ({ render: vi.fn() })),
}))

vi.mock('../App', () => ({
  default: () => null,
}))

// ─── Fixture ──────────────────────────────────────────────────────────────────

const SIMULATED_CDN_URL = 'https://cdn.ui.porsche.com/porsche-design-system/components/v4.1.0'

describe('PdsRuntimeTrapBehavior', () => {
  beforeEach(() => {
    // Clear module cache so each test gets a fresh main.tsx execution
    vi.resetModules()
    document.body.innerHTML = '<div id="root"></div>'
    // Reset prior namespace state without breaking delayed PDS polyfill callbacks.
    ;(document as Record<string, unknown>).porscheDesignSystem = {}
    // Ensure customElements.whenDefined resolves immediately (no real PDS loading)
    vi.spyOn(customElements, 'whenDefined').mockResolvedValue(
      undefined as unknown as CustomElementConstructor,
    )
  })

  afterEach(() => {
    vi.useRealTimers()
    ;(document as Record<string, unknown>).porscheDesignSystem = {}
    vi.restoreAllMocks()
    document.body.replaceChildren()
  })

  it('document.porscheDesignSystem.cdn property descriptor has a getter (accessor trap)', async () => {
    // Arrange: mocked load() simulates PDS direct cdn assignment
    const pdsJs = await import('@porsche-design-system/components-js')
    vi.mocked(pdsJs.load).mockImplementation((): void => {
      const ns = (document as Record<string, unknown>).porscheDesignSystem as
        | Record<string, unknown>
        | undefined
      if (!ns) return
      ns.cdn = { url: SIMULATED_CDN_URL, prefixes: [] }
    })

    // Importing main.tsx triggers trap setup and bootstrap().
    await import('../main')
    // Allow bootstrap() (async void) to complete
    await new Promise<void>((res) => setTimeout(res, 50))

    // Assert: cdn must be an accessor property (getter installed by Object.defineProperty)
    const pds = (document as Record<string, unknown>).porscheDesignSystem as Record<
      string,
      unknown
    >
    expect(pds).toBeDefined()
    const desc = Object.getOwnPropertyDescriptor(pds, 'cdn')
    expect(desc?.get, 'cdn must have a getter (Object.defineProperty accessor trap)').toBeDefined()
    expect(desc?.writable, 'cdn must not be a plain writable data property').toBeUndefined()
  })

  it('cdn.url returns window.location.origin immediately after PDS load() cdn assignment', async () => {
    // Arrange: capture cdn.url as read DURING load() — before any post-bootstrap fixup
    let cdnUrlDuringLoad: string | undefined

    const pdsJs = await import('@porsche-design-system/components-js')
    vi.mocked(pdsJs.load).mockImplementation((): void => {
      const pds = (document as Record<string, unknown>).porscheDesignSystem as
        | Record<string, unknown>
        | undefined
      if (!pds) return
      pds.cdn = { url: SIMULATED_CDN_URL, prefixes: [] }
      const cdn = pds.cdn as Record<string, string>
      cdnUrlDuringLoad = cdn.url
    })

    // Act
    await import('../main')
    await new Promise<void>((res) => setTimeout(res, 50))

    // Assert
    expect(cdnUrlDuringLoad).toBe(window.location.origin)
  })

  it('property trap is installed on document.porscheDesignSystem.cdn before load() is invoked', async () => {
    // Arrange: spy on load() to inspect document state at call time
    let trapPresentAtLoadTime = false

    const pdsJs = await import('@porsche-design-system/components-js')
    vi.mocked(pdsJs.load).mockImplementation((): void => {
      const pds = (document as Record<string, unknown>).porscheDesignSystem as
        | Record<string, unknown>
        | undefined
      const desc = pds ? Object.getOwnPropertyDescriptor(pds, 'cdn') : undefined
      trapPresentAtLoadTime = typeof desc?.get === 'function'
    })

    // Act
    await import('../main')
    await new Promise<void>((res) => setTimeout(res, 50))

    // Assert
    expect(trapPresentAtLoadTime).toBe(true)
  })

  it('renders a visible fallback when required PDS elements never register', async () => {
    vi.useFakeTimers()
    vi.mocked(customElements.whenDefined).mockImplementation(
      () => new Promise<CustomElementConstructor>(() => {}),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await import('../main')
    await Promise.resolve()
    await Promise.resolve()
    await vi.advanceTimersByTimeAsync(10_000)
    await Promise.resolve()
    await Promise.resolve()

    const fallback = document.querySelector<HTMLElement>('#root [role="alert"]')
    expect(fallback).not.toBeNull()
    expect(fallback).toHaveTextContent('OwlBear Cockpit could not load')
    expect(fallback).toHaveTextContent('Reload page')
  })
})
