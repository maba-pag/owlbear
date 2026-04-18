# E2E Kanban Board Tests — Research

> **Owning task:** #955 — E2E kanban board tests: DnD highlights, card density, scroll
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Three kanban board AC items from #931 cannot be tested in jsdom: DnD target highlighting (mid-drag visual state), card density (48-56px height), and horizontal/vertical scroll behavior. All require a real browser with a layout engine.

**Key question:** Which E2E framework best handles these 3 test scenarios for a React 19 + Vite 6 + Porsche DS 3.34.0 frontend?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | Playwright intro + DnD docs (playwright.dev/docs/intro, /docs/input#drag-and-drop) | 0.95 |
| S2 | Playwright Locator API — boundingBox, dragTo, scrollIntoViewIfNeeded (playwright.dev/docs/api/class-locator) | 0.95 |
| S3 | Vitest Browser Mode docs (vitest.dev/guide/browser/) | 0.90 |
| S4 | Vitest Component Testing docs (vitest.dev/guide/browser/component-testing) | 0.85 |
| S5 | `.owlbear/research/931-kanban-board-tests.md` — prior research, §3.2 jsdom feasibility matrix | 0.95 |
| S6 | `serve/cockpit/web/package.json` — current deps, no E2E infra | 0.90 |
| S7 | `serve/cockpit/web/vite.config.ts` — PDS partials plugin, jsdom test env | 0.90 |
| S8 | `serve/cockpit/web/vitest.setup.ts` — jsdom-specific PDS polyfill + CDN skip | 0.85 |

## 3. Analysis

### 3.1 Framework Comparison

| Criterion | Playwright Test | Vitest Browser Mode |
|-----------|----------------|---------------------|
| DnD mid-drag assertion | `page.mouse.down()/move()` + assert between moves — first-class [S1] | `userEvent` wraps CDP but no documented mid-drag inspection API [S3] |
| Card density (boundingBox) | `locator.boundingBox()` returns `{x,y,width,height}` [S2] | `element.getBoundingClientRect()` via DOM — works but needs PDS styles loaded |
| Scroll testing | `mouse.wheel()`, `scrollIntoViewIfNeeded()`, `evaluate(e => e.scrollTop)` [S1,S2] | Real browser overflow works, but no scroll-specific helpers |
| PDS shadow DOM | Full page render — components load naturally, no special setup | Needs separate setup file; jsdom polyfill doesn't apply; CDN requests need interception |
| Style pipeline | Uses actual `index.html` with PDS partials plugin — styles present | Component render has no `index.html` — PDS initial styles absent, density measurements unreliable |
| Dev server | `webServer` config auto-starts Vite (~10 lines config) [S1] | Not needed — renders components directly |
| Test runner | Separate (`@playwright/test`) — `npm run test:e2e` | Same runner (`vitest`) — `npm test` |
| React 19 compat | No framework coupling — tests interact with rendered page | Depends on `vitest-browser-react` (community pkg, React 19 compat unverified) |
| CI cost | ~200MB browser binary download | Same ~200MB (uses Playwright under the hood) |
| Future growth | Full E2E: visual regression, cross-browser, accessibility audits | Component-level only |

### 3.2 DnD Mid-Drag State Assertion (Critical)

The DnD test requires asserting visual state *during* a drag: hover over valid column → assert highlight; hover over invalid column → assert dim. This is a multi-step mouse sequence:

```
mousedown on card → mousemove to column A → assert highlight → mousemove to column B → assert dim → mouseup
```

Playwright supports this natively via `page.mouse` [S1,S2]. Vitest browser mode's `userEvent` wraps CDP for higher-level interactions but does not document mid-drag DOM inspection [S3]. This is the primary use case — the tool must support it.

### 3.3 Risk Assessment

| Risk | Playwright Test | Vitest Browser Mode |
|------|----------------|---------------------|
| DnD mid-drag works | Low — documented API [S1] | High — unverified capability |
| PDS styles load | Low — full page render | High — no index.html style injection |
| Maintenance burden | Low — Microsoft-backed | Medium — community render pkg |
| Migration cost if wrong | N/A | Must migrate to Playwright later |

## 4. Recommendation

**Use Playwright Test (standalone)** for E2E kanban board tests.

Confidence: **0.85**

Rationale:
- First-class DnD support with mid-drag state assertion via `page.mouse` [S1,S2]
- `locator.boundingBox()` for reliable card density measurement [S2]
- Full page render ensures PDS styles are present (via `pdsPartialsPlugin`) [S7]
- `webServer` config auto-starts Vite dev server — minimal infrastructure
- Future-proof: visual regression, cross-browser, accessibility audits
- Aligned with task AC's explicit Playwright recommendation
- No shadow DOM complications — tests interact with rendered page

Challenge: `block` on original Vitest Browser Mode recommendation (challenger confidence 0.35). Revised to Playwright Test after re-evaluation. Challenger correctly identified that DnD mid-drag assertion is the primary use case and Vitest browser mode lacks verified support for it. PDS style pipeline gap and community package risk compounded the concern.

### Implementation Approach

```
serve/cockpit/web/
  e2e/
    kanban-board.spec.ts    ← DnD highlights, card density, scroll
  playwright.config.ts      ← webServer: vite preview, chromium only
```

New devDep: `@playwright/test`
New script: `"test:e2e": "playwright test"`

Separation: `npm test` (vitest/jsdom, fast) stays untouched. `npm run test:e2e` (playwright, slow) runs browser tests.

## 5. Follow-up Tasks

1. **RED: Write failing Playwright E2E tests** for kanban board DnD highlights, card density, scroll — depends on kanban board GREEN completion
2. **Setup: Add Playwright to cockpit web** — install `@playwright/test`, create `playwright.config.ts` with `webServer`, add `test:e2e` script
