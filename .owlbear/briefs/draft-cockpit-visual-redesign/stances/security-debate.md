# Security Stance — Critic Debate Log

## Round 1

### Draft Position (Security Panelist)

**Overall: This redesign has negligible security surface change. No new trust boundaries are crossed. No blocking concerns.**

1. **Supply-chain (Tailwind v4):** Build-time devDependency only. Widely audited, no runtime code ships. Consistent with existing dependency profile.
2. **Font-face trust model unchanged:** CDN trap in main.tsx redirects to self. Assets self-hosted under public/porsche-design-system/. No new external origins.
3. **CSP impact: none.** PostCSS is build-time. Output is static CSS. Existing `'unsafe-inline'` for styles already present.
4. **No XSS from PDS components:** Shadow DOM encapsulation, typed props, no dangerouslySetInnerHTML in production code.
5. **localStorage theme: non-concern.** Stores only validated 'dark' | 'light'. No sensitive data.

### Critic Challenge

**Severity: High. Multiple gaps found.**

1. **Font-face external origin (critical).** `font-face.css` hardcodes all URLs to `https://cdn.ui.porsche.com/...`. The CDN trap only intercepts JS-driven `document.porscheDesignSystem.cdn` loading — it does NOT rewrite CSS `@font-face src:` URLs. The `sync-pds-assets.mjs` script mirrors components and icons but NOT fonts. Importing `global-styles/index.css` introduces a new external origin that breaks the self-hosting model.

2. **CSP scoped to wrong execution mode (moderate).** The CSP plugin is build-only (`apply: 'build'`). Dev mode has no CSP enforcement. Tailwind is exercised in the mode the CSP does not cover.

3. **Supply-chain threat model mismatch (moderate).** "Build-time only" doesn't address devDependencies running with filesystem/repo/secret access on developer and CI machines.

4. **PDS innerHTML sink exists (moderate).** `notification-base.d.ts` exposes an `innerHTML` prop. PDS notification components use `dangerouslySetInnerHTML` when it is set.

Critic confidence in original position: **0.18**

### Panelist Response

**Accepted findings with refinements:**

1. **Font-face external origin — ACCEPTED, MATERIAL.** Verified: `font-face.css` contains 24+ `@font-face` declarations all pointing to `https://cdn.ui.porsche.com/porsche-design-system/fonts/*.woff2`. The CDN trap is JavaScript-only and cannot intercept CSS-declared font URLs. The current CSP `default-src 'self'` would block these font loads entirely (font-src falls back to default-src). This is the most actionable finding. **Mitigation required during implementation: extend sync script to mirror fonts, provide local font-face.css with rewritten self-hosted URLs.**

2. **CSP in dev mode — ACCEPTED, LOW IMPACT.** True that dev mode lacks CSP. However, the cockpit is a localhost-only development tool. In dev mode, the operator IS the developer, on their own machine. Dev-mode CSP absence is defense-in-depth gap, not a trust-boundary violation. The build-time CSP protects the production artifact (the `dist/` bundle served by the FastAPI backend). Not blocking.

3. **Supply-chain threat model — PARTIALLY ACCEPTED.** Valid that devDependencies run in a privileged environment. However, the project already trusts 15+ devDependencies in the same zone (Vite, Babel, TypeScript, ESLint, Rolldown, jsdom, etc.). Adding Tailwind (MIT-licensed, 86k+ stars, Tailwind Labs) is an incremental addition consistent with the existing profile, not a qualitative change. The risk is real but not elevated relative to baseline. **Recommendation: pin exact version, use lockfile integrity checks (already in place via package-lock.json).**

4. **PDS innerHTML sink — ACCEPTED, LATENT RISK.** Verified that `notification-base.d.ts` has `innerHTML?: boolean`. However, verified that current cockpit usage of `PInlineNotification` in ArchivalModal.tsx and ResolveModal.tsx does NOT use this prop — only `description` (string) and `actionLabel` (string) are passed. The `error.message` source is a JavaScript Error object, not user-supplied HTML. The risk is latent: future code could misuse the prop. **Recommendation: ESLint rule to ban `innerHTML` prop on PDS notification components.**

### Position Update

Revised from "negligible surface change" to "low risk with one actionable finding." The font-face external origin is a real trust-boundary expansion that must be mitigated during implementation — not a blocker, but a required implementation constraint.

## Exit

Critic exposed a genuine gap (font-face URLs) that the initial assessment missed by assuming the CDN trap covered all PDS asset loading. Position hardened with specific mitigation. Remaining challenges (dev-mode CSP, supply-chain) are acknowledged as defense-in-depth considerations but do not change the overall risk profile from low.
