/**
 * Tests for #1496: Replace PDS appendChild monkeypatch with property trap on
 * document.porscheDesignSystem.cdn
 *
 * AC-1: installPdsRuntimeScriptRewrite() function, its call site, and the
 *       PDS_CDN_SCRIPT regex are removed from main.tsx
 * AC-2: Before load() is called, an Object.defineProperty trap on
 *       document.porscheDesignSystem.cdn ensures cdn.url returns
 *       window.location.origin regardless of PDS load() assignments
 * AC-3: Post-bootstrap document.porscheDesignSystem reassignment block removed
 * AC-4: E2E tests in pds-runtime-csp.spec.ts pass without modification
 *       (regression guard — file must not be modified by builder)
 *
 * RED reason (AC-1, AC-2, AC-3 tests): current main.tsx still contains the
 * monkeypatch function, PDS_CDN_SCRIPT regex, and post-bootstrap fixup block,
 * and has no Object.defineProperty trap.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

// ─── Path helpers ──────────────────────────────────────────────────────────────

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// This file lives in src/__tests__/; src/ is one level up
const SRC_DIR = resolve(__dirname, '..')
const MAIN_TSX_PATH = resolve(SRC_DIR, 'main.tsx')
const E2E_SPEC_PATH = resolve(SRC_DIR, '..', 'e2e', 'pds-runtime-csp.spec.ts')

// ─── Module-level mocks for behavioral import tests ────────────────────────────
//
// These are hoisted by Vitest before any test runs. They prevent real PDS load(),
// real React DOM rendering, and the complex App component tree from executing
// when main.tsx is dynamically imported in TestFromAC_PdsTrapBehavior.

vi.mock('@porsche-design-system/components-js', () => ({
  load: vi.fn(),
}))

vi.mock('react-dom/client', () => ({
  createRoot: vi.fn(() => ({ render: vi.fn() })),
}))

vi.mock('../App', () => ({
  default: () => null,
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const SIMULATED_CDN_URL = 'https://cdn.ui.porsche.com/porsche-design-system/components/v4.1.0'

// ─── AC-1 and AC-3: Structural source-read tests ─────────────────────────────

describe('TestFromAC_PdsTrapStructural', () => {
  let mainSource: string

  beforeEach(() => {
    mainSource = readFileSync(MAIN_TSX_PATH, 'utf-8')
  })

  // ─── AC-1: monkeypatch function removed ────────────────────────────────────

  it('installPdsRuntimeScriptRewrite function is absent from main.tsx', () => {
    // Fails RED: function currently defined in main.tsx
    expect(mainSource).not.toContain('installPdsRuntimeScriptRewrite')
  })

  it('PDS_CDN_SCRIPT regex constant is absent from main.tsx', () => {
    // Fails RED: PDS_CDN_SCRIPT regex currently defined in main.tsx
    expect(mainSource).not.toContain('PDS_CDN_SCRIPT')
  })

  it('Element.prototype.appendChild monkeypatch is absent from main.tsx', () => {
    // Fails RED: prototype patch on appendChild currently in main.tsx
    expect(mainSource).not.toContain('Element.prototype')
  })

  // ─── AC-2: property trap present ──────────────────────────────────────────

  it('Object.defineProperty trap is present in main.tsx', () => {
    // Fails RED: Object.defineProperty not in current main.tsx
    expect(mainSource).toContain('Object.defineProperty')
  })

  it('Object.defineProperty trap targets document.porscheDesignSystem before load()', () => {
    // Fails RED: no defineProperty trap at all in current source
    const defineIdx = mainSource.indexOf('Object.defineProperty')
    const loadIdx = mainSource.indexOf('load()')
    expect(defineIdx).not.toBe(-1)
    expect(loadIdx).not.toBe(-1)
    // Trap must be installed before load() is invoked
    expect(defineIdx).toBeLessThan(loadIdx)
  })

  // ─── AC-3: post-bootstrap reassignment removed ─────────────────────────────

  it('post-bootstrap porscheDesignSystem reassignment block is absent from main.tsx', () => {
    // Fails RED: current main.tsx lines 38-41 reassign porscheDesignSystem after
    // waitForRequiredPdsElements() — the property trap replaces this fixup.
    // The distinguishing pattern is a spread-merge reassignment of the namespace.
    expect(mainSource).not.toContain('...((document as')
  })
})

// ─── AC-2: Behavioral import tests ────────────────────────────────────────────
//
// These tests dynamically import main.tsx after configuring module mocks so
// that bootstrap() executes fully without real PDS loading or DOM rendering.
// All assertions target the property trap that the NEW main.tsx installs.
// All fail against CURRENT main.tsx (monkeypatch instead of trap).

describe('TestFromAC_PdsTrapBehavior', () => {
  beforeEach(() => {
    // Clear module cache so each test gets a fresh main.tsx execution
    vi.resetModules()
    // Remove any prior namespace state
    delete (document as Record<string, unknown>).porscheDesignSystem
    // Ensure customElements.whenDefined resolves immediately (no real PDS loading)
    vi.spyOn(customElements, 'whenDefined').mockResolvedValue(
      undefined as unknown as CustomElementConstructor,
    )
  })

  afterEach(() => {
    delete (document as Record<string, unknown>).porscheDesignSystem
    vi.restoreAllMocks()
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

    // Act: import main.tsx — triggers installPdsRuntimeScriptRewrite() (current)
    // or trap setup + bootstrap() (new code)
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
    // Fails RED: current code stores cdn as a plain data property (no getter)
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
      // Namespace must be pre-created by trap setup; if absent (current code),
      // the assignment cannot be intercepted — cdnUrlDuringLoad stays undefined
      if (!pds) return
      // Simulate PDS load() direct cdn assignment
      pds.cdn = { url: SIMULATED_CDN_URL, prefixes: [] }
      // Read back: getter trap overrides the assignment in new code
      const cdn = pds.cdn as Record<string, string>
      cdnUrlDuringLoad = cdn.url
    })

    // Act
    await import('../main')
    await new Promise<void>((res) => setTimeout(res, 50))

    // Assert
    // Fails RED: current code has no pre-created namespace before load(), so
    // pds is undefined during load() → cdnUrlDuringLoad stays undefined
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
    // Fails RED: current code calls installPdsRuntimeScriptRewrite() (no defineProperty)
    // so no getter trap is present on cdn when load() is invoked
    expect(trapPresentAtLoadTime).toBe(true)
  })
})

// ─── AC-4: E2E regression guard ───────────────────────────────────────────────
//
// AC-4 states E2E tests in pds-runtime-csp.spec.ts must pass without modification.
// This guard verifies the spec file is structurally intact (builder must not touch it).
// Regression guard — currently PASSES; fails if builder modifies the E2E spec.

describe('TestFromAC_E2eRegressionGuard', () => {
  it('pds-runtime-csp.spec.ts exists and contains key CSP test describe blocks', () => {
    const spec = readFileSync(E2E_SPEC_PATH, 'utf-8')
    // File must contain the two primary describe blocks from the original spec
    expect(spec).toContain('TestFromAC_PDSCustomElementsRegistered')
    expect(spec).toContain('TestFromAC_NoCDNCSPViolations')
  })

  it('pds-runtime-csp.spec.ts is not modified: p-button registration test present', () => {
    const spec = readFileSync(E2E_SPEC_PATH, 'utf-8')
    expect(spec).toContain('p-button custom element is defined after workspace renders')
  })

  it('pds-runtime-csp.spec.ts is not modified: CDN CSP violation test present', () => {
    const spec = readFileSync(E2E_SPEC_PATH, 'utf-8')
    expect(spec).toContain('no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.com')
  })
})
