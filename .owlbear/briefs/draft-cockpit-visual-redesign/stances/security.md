# Security Stance — Cockpit Visual Redesign

## Security Stance

This redesign is **low risk with one actionable finding** that requires mitigation during implementation. The cockpit is a localhost-only development tool (127.0.0.1:8420) with no external users, no authentication, and no sensitive data beyond local task metadata. The redesign changes visual presentation, not data flows or trust boundaries — with one exception.

## Risk Assessment

### R1: Font-Face External Origin — MEDIUM (actionable)

**Finding:** PDS `font-face.css` (bundled in `global-styles/index.css`) hardcodes all `@font-face src:` URLs to `https://cdn.ui.porsche.com/porsche-design-system/fonts/*.woff2`. This introduces a new external network origin.

**Why it matters:**
- The existing CDN trap (`main.tsx:11-31`) only intercepts JavaScript-driven asset loading via `document.porscheDesignSystem.cdn`. It cannot rewrite CSS `@font-face` `src:` declarations.
- The existing `sync-pds-assets.mjs` script mirrors components and icons but NOT font files.
- The current CSP policy (`default-src 'self'`) would block external font loading — `font-src` falls back to `default-src 'self'` when not explicitly declared.
- Even if CSP were relaxed, loading fonts from an external CDN breaks the self-contained trust model the cockpit was designed around.

**Required mitigation:** Extend the font self-hosting story to match what already exists for components and icons. Either:
- (a) Extend `sync-pds-assets.mjs` to also download font files and provide a local `font-face.css` with URLs rewritten to self-hosted paths. Preserves `'self'`-only CSP.
- (b) Use a Vite plugin or PostCSS transform to rewrite `cdn.ui.porsche.com` font URLs to local paths at build time.

Option (a) is consistent with the existing pattern and recommended. Do NOT solve this by relaxing the CSP to allow `font-src https://cdn.ui.porsche.com` — that trades a build-time fix for a runtime trust expansion.

### R2: Supply-Chain — LOW (monitor)

Adding `tailwindcss` as a devDependency introduces a new package into the build toolchain. Tailwind v4 is MIT-licensed, maintained by Tailwind Labs, widely audited (86k+ GitHub stars). It runs at build time only — no runtime JavaScript ships to the browser. The project already trusts 15+ devDependencies (Vite, Babel, TypeScript, ESLint, Rolldown, jsdom) in the same privileged build environment.

**Incremental risk is consistent with existing profile.** Pin exact version in package.json. Rely on package-lock.json integrity hashes. No special action beyond standard dependency hygiene.

### R3: PDS Component HTML Sink — LOW (latent)

PDS `notification-base` exposes an `innerHTML` boolean prop that, when set, causes the wrapper to use `dangerouslySetInnerHTML`. Current cockpit usage of `PInlineNotification` (in `ArchivalModal.tsx` and `ResolveModal.tsx`) does NOT use this prop — only string props (`description`, `actionLabel`) with Error object messages as source.

**Latent risk:** Future component migration could inadvertently enable the `innerHTML` prop with unsanitized content. The redesign will add more PDS component usage, increasing the surface area.

**Recommendation:** Add an ESLint rule banning the `innerHTML` prop on PDS notification components. This is a preventive control, not a response to a current vulnerability.

### R4: CSS Processing Chain / CSP — NEGLIGIBLE

Switching from LightningCSS-only to PostCSS (for Tailwind) is a build-time change. The output remains static CSS files. The existing CSP meta tag (`style-src 'self' 'unsafe-inline'`) is unchanged and sufficient. The `'unsafe-inline'` is already required by PDS web components that inject shadow DOM styles.

**Note:** The CSP plugin is build-only (`apply: 'build'`). Dev mode (`vite dev`) has no CSP enforcement. This is acceptable for a localhost-only tool where the operator is the developer. Defense-in-depth improvement would be adding CSP to dev mode, but it's not blocking.

### R5: localStorage Theme Storage — NEGLIGIBLE

Stores only `'dark'` | `'light'` (validated by `VALID_STORAGE_THEMES` Set). No sensitive data, no auth tokens, no PII. Both `theme-bootstrap.js` (pre-render) and `useTheme` hook validate input. The redesign does not change this mechanism.

### R6: XSS via PDS Component Props — NEGLIGIBLE

PDS React wrappers use shadow DOM encapsulation. Components accept typed props (strings, enums, booleans), not raw HTML. The cockpit uses `rehype-sanitize` for markdown rendering. Migrating from raw `<button>` to `PButton` does not introduce new injection surfaces. The one exception (notification `innerHTML` prop) is addressed in R3.

## Compliance Implications

None. The cockpit is a local-only development tool with no external users, no authentication requirements, no data residency constraints, and no regulatory scope. The self-hosting model is a design choice for offline-capable operation, not a compliance requirement — but it should be preserved as a defense-in-depth property.

## Least-Privilege Recommendations

1. **Preserve `'self'`-only CSP.** Do not add external origins to the CSP policy. Self-host fonts using the same pattern as components and icons.
2. **Ban PDS `innerHTML` prop.** ESLint rule prevents future misuse of the HTML injection sink.
3. **Pin Tailwind version.** Exact version in package.json, integrity via lockfile.
4. **No new `connect-src` origins.** The redesign should not introduce any new API endpoints or external fetch targets.

## Warnings

1. **The font-face mitigation is a required implementation constraint, not optional polish.** Without it, either fonts fail to load (CSP blocks them) or the CSP must be relaxed (trust boundary expands). Neither outcome is acceptable.
2. **The audit mentions 73+ findings and component migration across many files.** Each migration should be reviewed for accidental use of HTML-injection props (`innerHTML`, `dangerouslySetInnerHTML`). The ESLint ban rule is the systematic guard.

## Confidence

**0.88** — High confidence in the overall "low risk" assessment. The font-face finding is well-evidenced and has a clear mitigation path. The remaining findings are defense-in-depth recommendations, not blockers. Minor uncertainty on whether PDS has additional HTML sinks beyond notification-base that weren't audited (would require full component API surface review).
