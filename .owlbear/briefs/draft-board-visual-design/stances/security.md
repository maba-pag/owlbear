# Security Stance — Board Visual Design

## Security Assessment

This brief's security delta is small and well-bounded. The work introduces one new runtime behavior — theme preference management — on top of a CSS restructuring pass. No new API endpoints, no new data flows, no new authentication surfaces.

The brief operates on a localhost-only, single-user cockpit (FastAPI on 127.0.0.1:8420) with no authentication. The overall cockpit has pre-existing security characteristics (unauthenticated mutation endpoints, permissive transition validation) that this brief does not alter or expand.

## Risk Assessment

| Concern | Severity | Introduced by this brief? | Action |
|---------|----------|--------------------------|--------|
| localStorage theme value without validation | Low | Yes | Allowlist validate before DOM application |
| Theme resolution runtime logic | Low | Yes | Standard SPA pattern; no sensitive data |
| Expanded CSS selector surface (data-attributes) | Informational | Partially (CSS rules new; DOM attributes pre-existing) | No action needed |
| CSP inline-to-external migration | Informational (positive) | Yes | Track as incremental improvement |
| CSRF on mutation endpoints | Medium | No (pre-existing) | Out of scope; flag for cockpit-level review |
| PDS bootstrap/CDN boundary | Low | No (pre-existing) | Ensure pds-runtime-csp.spec.ts continues passing |
| Server permissive transition validation | Medium | No (pre-existing) | Out of scope; context menu styling improves intent clarity |

## Compliance Implications

None introduced by this brief. The cockpit displays user-authored task content and workflow data. Whether specific content contains sensitive information is a content-classification question for the overall cockpit, not a delta from a styling brief. No new data processing, storage, or transmission is added.

## Least-Privilege Recommendations

1. **Validate localStorage input.** The theme preference read from localStorage must be checked against an allowlist (`["dark", "light", "auto"]`) before being applied as a `data-theme` attribute on the document root. If the value doesn't match, default to `"auto"`. This is defense-in-depth — a poisoned localStorage value cannot execute code via CSS attribute selectors, but constraining the input surface is good hygiene.

2. **Preserve PDS CSP boundary.** The existing `pds-runtime-csp.spec.ts` E2E test enforces that PDS loads from local bundles, not the Porsche CDN. This test must continue passing. If the brief changes PDS provider configuration or token loading, regression coverage exists.

3. **No new CSP relaxation.** The brief should not add new `unsafe-*` directives or relax the existing CSP policy in `vite.config.ts`. Moving inline styles to external CSS files is directionally positive for eventual CSP tightening, but won't enable dropping `style-src 'unsafe-inline'` on its own (other components and PDS Shadow DOM still use inline styles).

## Warnings

### Pre-existing: Unauthenticated mutation surface

The cockpit exposes POST endpoints (`/api/tasks/{id}/move`, `/edit`, `/release`) without authentication on localhost. Any page in the user's browser can issue simple POST requests to these endpoints (CSRF). The server's transition validation is permissive — `valid_transitions` returns all statuses except current, not a strict state machine. This brief does not change this surface, but it bears noting that the context menu being styled is the primary intent-clarity layer in front of a permissive backend.

### Context menu styling is net-positive for intent safety

The current context menu is functionally invisible (no background, no shadow, no hover states). Styling it with proper visual treatment (surface, elevation, hover feedback, clear item labels) *improves* the user's ability to express intentional state transitions. This is a security-relevant improvement, not just cosmetic.

### Theme flash prevention

Initial theme application should happen before React render (in the `<head>` or before `createRoot`) to prevent flash-of-wrong-theme. This is a standard pattern — read localStorage, validate, apply `data-theme` attribute synchronously. The pre-render script should not perform network calls or access any state beyond localStorage.

## Confidence

**0.88** — High confidence that this brief's security delta is low. One actionable defense-in-depth recommendation (allowlist validation). Pre-existing cockpit concerns (CSRF, permissive transitions) are real but unchanged by this work. The Critic correctly pressured the initial over-dismissive framing; the refined position accounts for the full theme resolution behavior and selector surface expansion without inflating the risk beyond what the evidence supports.
