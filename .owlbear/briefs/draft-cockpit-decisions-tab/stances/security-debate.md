# Security Debate Log — Cockpit Decisions Tab

## Cycle 1

### Draft Position

The security posture is adequate for a localhost single-user development tool, with one notable gap: the absence of a Host header check leaves a theoretical DNS rebinding surface.

Strengths: path traversal mitigated by allowlist regex, XSS mitigated by rehype-sanitize, CSRF blocked by JSON Content-Type triggering CORS preflight, network binding limited to 127.0.0.1, input validation via Pydantic with `extra="forbid"`.

Gaps: DNS rebinding (no Host validation), no CSP headers, unbounded notes field, no rate limiting, unauthenticated SSE stream.

Confidence: 0.82

### Critic Challenges (Cycle 1)

**Critical — CSRF scope too narrow.** The CSRF analysis only covers the JSON-backed decisions resolve route. The same app exposes bodyless POST mutations: `sweep`, `cleanup`, `repair`, `compact-activity`, `scan`. These don't require JSON parsing or preflight. The "accidental CSRF protection" claim is too narrow for the posture it asserts.

**Critical — Blast radius understated.** The rebinding impact was narrowed to reading DRs and resolving them. The actual reachable surface is the entire workspace control plane: task listings, full details, activity history, sessions, and multiple task mutations.

**Moderate — CSP meta tag exists.** The draft claimed no CSP when the Vite build config injects a CSP meta tag (`script-src 'self'`, `connect-src 'self'`). Incorrect.

**Moderate — Path traversal trust boundary.** The regex prevents path separators, but the file operations (read, write, hard-link, unlink) follow symlinks without rejection. Separate trust assumption from the regex.

**Blind spots:** Unbounded read surface in GET /api/decisions/pending (full bodies for all items). Local process access model under-examined. Resolve endpoint response oracle (distinguishable error states).

### Refinement

Accepted all challenges. Corrected CSP claim, expanded CSRF scope to cover bodyless mutations with specific blast radius, expanded DNS rebinding blast radius to full API surface, added symlink concern as residual risk.

---

## Cycle 2

### Refined Position

The decisions tab's own additions have strong input validation and sanitization. The broader Cockpit API surface has two unmitigated gaps: (1) bodyless POST mutations are CSRF-vulnerable via cross-origin form submission, and (2) no Host header validation enables DNS rebinding with full API access.

Confidence: 0.85

### Critic Challenges (Cycle 2)

**Critical — CSRF blast radius on cleanup/repair.** The "maintenance operations, not data-destructive" framing is unsupported. `cleanup()` archives tasks and releases claims. `repair()` quarantines files and creates action-required tasks. `compact-activity()` truncates the activity log. These are workspace mutations, not harmless housekeeping.

**Moderate — Cross-consumer sanitization.** The resolve flow appends raw DR body into task bodies via `canonical_summary()`. Cockpit rendering is sanitized, but this doesn't prove end-to-end sanitization across all downstream markdown consumers.

**Moderate — No framing protection.** The CSP meta tag has no `frame-ancestors` directive. No `X-Frame-Options` header. Clickjacking is possible.

**Moderate — Response oracle + DNS rebinding inconsistency.** If DNS rebinding gives full access, the response oracle is useful to the rebinding attacker, not "meaningful only on localhost."

**Blind spots:** SSE event stream as reconnaissance channel. Availability pressure from bulk reads and scans. Missing framing directive for clickjacking.

### Refinement

Accepted blast radius correction — cleanup and repair are real mutations, not trivial maintenance. Accepted cross-consumer sanitization concern as a documented trust boundary. Added framing protection gap. Fixed internal consistency between DNS rebinding and response oracle sections. Added SSE and availability as accepted risks.

### Exit

Position is solid after two cycles. Remaining Critic pressure is pushing into theoretical compound attacks (symlink + rebinding) and availability concerns that are inherent to the localhost no-auth model. The core position — strong feature-level defenses, inherited surface-level gaps, specific recommendations — is stable. Publishing.
