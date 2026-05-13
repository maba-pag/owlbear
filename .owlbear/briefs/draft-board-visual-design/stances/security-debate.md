# Security Debate Log — Board Visual Design

## Cycle 1: Initial Position → Critic Challenge

### Initial Position (Security Panelist)

**Overall:** Near-zero security impact. Pure CSS/visual styling task on localhost-only cockpit. No new trust boundaries, data flows, auth surfaces, or API endpoints.

**Findings:**
1. localStorage for theme preference — minimal risk, same-origin scoped, non-sensitive value
2. `data-theme` attribute — no selector injection risk with constrained values
3. CSP improvement from inline-to-external CSS — net security positive
4. Context menu styling — no new trust boundary, transitions server-controlled
5. PDS Web Components — already loaded, no new dependencies
6. No auth, no new APIs — security posture unchanged

**Confidence:** 0.92

### Critic Challenge (Cycle 1)

**Severity: Critical**
1. **Stale scope description.** Brief evolved beyond "pure CSS" — D4 ships both themes, D6 adds auto+manual toggle with localStorage. Theme state management is runtime JS behavior, not CSS.
2. **Localhost ≠ no trust boundary.** Cockpit exposes unauthenticated mutation endpoints (POST /api/tasks/{id}/move, /edit, /release). Any browser tab can POST to localhost:8420. Dismissing the trust boundary is wrong.

**Severity: Moderate**
3. **CSP claim aspirational.** vite.config.ts hardcodes `unsafe-inline`. Other components still use inline styles. Brief won't enable dropping `unsafe-inline`.
4. **PDS bootstrap layer.** CDN trap + explicit `load()` in main.tsx is security-sensitive integration detail, not "already loaded."
5. **Context menu integrity.** Visual ordering and affordance clarity matter for intent integrity in mutation-capable tools.
6. **Data sensitivity.** Task content is user-authored; "no PII" is a content-classification claim, not a structural guarantee.

**Critic Confidence in Original Position:** 0.46

### Panelist Response

Accepted all six challenges. Key refinements:
- Dropped "pure CSS" and "effectively nil" framing
- Acknowledged theme toggle as new runtime behavior requiring its own evaluation
- Downgraded CSP from "net improvement" to "directionally positive, not yet realized"
- Acknowledged CSRF surface as pre-existing context, not dismissed
- Narrowed PDS claim to "pre-existing, unchanged by this brief"
- Qualified data sensitivity as "out of scope for styling brief" rather than "no PII"

---

## Cycle 2: Refined Position → Critic Challenge

### Refined Position (Security Panelist)

**Overall:** Low security impact with one actionable recommendation. Brief's delta: theme state management (localStorage + data-theme attribute + prefers-color-scheme) and CSS restructuring. No new APIs, no new auth surfaces, no new data flows.

**Key addition:** Allowlist validation on localStorage→DOM flow as defense-in-depth.

**Confidence:** 0.90

### Critic Challenge (Cycle 2)

**Severity: Critical**
1. **Server rubber-stamps transitions.** `engine.valid_transitions` returns all configured statuses except current — not a strict state machine. Context menu IS the primary guardrail for user intent, not just a display layer.

**Severity: Moderate**
2. **Delta still too narrow.** Full theme resolution logic (auto + manual + persistence + initial application) is broader than "one constrained string."
3. **PDS controls respond to theme state.** Changing document-root theme touches PDS-rendered components (FilterPanel PSelect/PButton). Existing CSP test covers CDN blocking, not theme initialization.
4. **CSP evidence overstated.** PDS E2E spec tests CDN blocking, not theme behavior. Unit CSP test only checks default-src and script-src presence.
5. **Selector surface expansion.** data-selected, data-priority, data-status attributes already exist on DOM but brief adds CSS rules targeting them — broader selector-driven UI state.
6. **Pre-render bootstrap.** Initial theme application before createRoot is live delta, not background context.

**Critic Confidence in Refined Position:** 0.56

### Panelist Response

Partially accepted:
- **Accepted:** Expanded delta description to full theme resolution logic. Acknowledged permissive server validation as context. Noted selector surface expansion. More precise about CSP evidence scope.
- **Stood firm on delta assessment:** The server's permissive transition validation is pre-existing. This brief doesn't change what transitions appear or how they map to mutations. Styling the context menu (background, shadow, hover states) arguably *improves* intent clarity over the current unstyled invisible menu. The data-attribute selectors already exist in the DOM — the brief adds CSS rules, not new DOM state. Pre-render theme application is standard FOWT-prevention, following the same pattern used by every theme-aware SPA.

**Final assessment:** The Critic correctly identifies real concerns in the overall cockpit architecture (CSRF, permissive transitions, PDS bootstrap) but these are pre-existing conditions. This brief's delta remains genuinely low-risk with one actionable recommendation.
