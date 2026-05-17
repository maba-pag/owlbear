# Security Stance — Cockpit Decisions Tab

## Security Stance

The decisions tab's own additions are well-defended: strict path-traversal prevention, consistent XSS sanitization, and typed input validation. The feature inherits two unmitigated gaps from the pre-existing Cockpit API surface — CSRF on bodyless mutation endpoints and DNS rebinding without Host header validation — neither introduced by this design, but both amplified by adding another state-changing endpoint.

## Risk Assessment

### Strong Defenses (decisions tab scope)

**Path Traversal — Mitigated.**
Decision ID validation (`^[a-zA-Z0-9][a-zA-Z0-9_-]*$`) is an allowlist that excludes path separators, dots, null bytes, and all special characters. File paths are composed as `decisions_dir / "pending" / f"{decision_id}.md"`, keeping resolution within the expected directory. The regex is checked by `_validate_decision_id()` before any file I/O. This is correct and sufficient for the stated threat model.

Residual: the file operations (read, write, hard-link, unlink) follow symlinks without rejection. A compound attack requiring local symlink placement plus remote trigger (DNS rebinding) is theoretically possible but requires prior local filesystem access to plant the symlink — the same trust boundary that the no-auth model already accepts.

**XSS — Mitigated.**
All markdown rendering paths (ResolveModal, DetailTab, TaskFieldsEditor) use ReactMarkdown + rehype-sanitize (default GitHub schema), stripping scripts, event handlers, iframes, and dangerous attributes. DR bodies are agent-authored content — the sanitization pipeline handles this correctly. The Vite build injects a CSP meta tag (`script-src 'self'`, `connect-src 'self'`), providing defense-in-depth. Test coverage verifies plugin wiring (ResolveModal.plugins.test.tsx, DetailTab.gfm-plugins.test.tsx).

Residual: the resolve flow appends the raw DR body into the linked task body via `canonical_summary()`. If any downstream markdown consumer outside the Cockpit renders task bodies without sanitization, injected content could be effective. Within the current system, the only consumers are the Cockpit (sanitized) and agents reading `.md` files as text (no HTML rendering). This is a cross-consumer trust boundary worth documenting.

**Input Validation — Adequate.**
`ResolveRequest` uses `extra="forbid"` and constrains `response` to a `Literal["approved", "needs-info", "rejected"]`. The notes field is `str | None` with no length bound — an unbounded write to disk, but self-inflicted in the single-user context. A length cap (e.g., 10KB) would be cheap defense-in-depth.

### Inherited Gaps (pre-existing Cockpit surface)

**CSRF on Bodyless Mutations — Unmitigated.**
The decisions resolve endpoint requires a JSON body, triggering CORS preflight which fails (no CORSMiddleware) — protected by accident. However, the same app exposes bodyless POST endpoints: `sweep` (releases expired claims), `cleanup` (archives tasks, releases claims), `repair` (quarantines corrupt files, creates action-required tasks), `compact-activity` (truncates activity log), and `scan` (read-only). A cross-origin `<form method="POST">` submission executes these without triggering preflight. The attacker cannot read the response but side effects execute.

Blast radius: `cleanup` and `repair` modify task state and move files. This is not harmless housekeeping — it's unintended workspace mutation. The decisions tab's own resolve endpoint is NOT vulnerable to this (JSON body required), but it shares the API surface.

**DNS Rebinding — Unmitigated.**
No Host header validation middleware. A malicious page could rebind a domain to 127.0.0.1 and bypass same-origin policy, gaining full read/write API access. The exposed surface includes: all task listings, full task details with bodies, activity and session history (including agent names, timing, source data), all pending DR content, mutation endpoints (task edits, moves, claims), maintenance operations, and the SSE event stream (workspace activity reconnaissance).

This is the highest-impact gap. It converts the localhost binding (network-layer protection) into a browser-layer bypass. Combined with CSRF, a rebinding attacker gets both read AND write access to the entire workspace control plane.

**No Framing Protection — Unmitigated.**
The CSP meta tag has no `frame-ancestors` directive, and no `X-Frame-Options` header is set. The Cockpit page could be embedded in an attacker-controlled iframe for clickjacking. Low-probability for a localhost tool but a defense gap.

### Accepted Risks (inherent to deployment model)

**Local Process Access.**
Any process on the host can reach the unauthenticated loopback API. This includes malicious browser extensions (full page privileges, unrestricted localhost access), other local applications, and local malware. Adding authentication would change the product's deployment model. Accepted.

**Response Oracle.**
The resolve endpoint returns distinguishable error responses for: invalid ID (422), missing ID (404), cockpit-resolved ID (404), and agent-resolved ID (409). This reveals state to any caller. Under DNS rebinding, this oracle is useful for reconnaissance. Low impact in isolation but worth noting for consistency.

**Availability Pressure.**
`GET /api/decisions/pending` iterates all pending files and returns full bodies. Large or numerous DR files could produce heavy responses. Scan and corruption-check endpoints walk task and archive trees. No pagination or size limits. Meaningful only as self-inflicted local DoS.

## Compliance Implications

None. This is a laptop-resident single-user development tool with no multi-tenant data, no PII processing, no external network exposure, and no regulatory surface. The security posture is evaluated against the tool's own integrity, not external compliance frameworks.

## Least-Privilege Recommendations

1. **Host header validation middleware** — reject requests where the Host header is not `127.0.0.1:{port}` or `localhost:{port}`. This is the single highest-value mitigation: it closes DNS rebinding and substantially reduces the cross-origin attack surface. Cheap to implement (one middleware function).

2. **`frame-ancestors 'none'`** — add to the CSP meta tag or serve as a response header. Closes clickjacking.

3. **Notes length cap** — add `max_length=10_000` (or similar) to the notes field in `ResolveRequest`. Cheap defense-in-depth against unbounded disk writes.

4. **Consider `SameSite=Strict` or origin-check middleware** for bodyless POST endpoints — this would close the CSRF gap on sweep/cleanup/repair/compact-activity without requiring full auth.

Recommendations 1 and 2 are low-effort, high-value. Recommendations 3 and 4 are low-effort, low-value (given single-user context) but contribute to defense-in-depth.

## Warnings

- Do NOT introduce CORSMiddleware with permissive origins. The current no-CORS state is actually more secure than `Access-Control-Allow-Origin: *` — it prevents cross-origin reads while the JSON body requirement blocks cross-origin writes for body-bearing endpoints.
- The DNS rebinding gap predates this feature and affects the entire Cockpit. If Host validation is added, it should be app-wide middleware, not per-route.
- The cross-consumer sanitization concern (notes appended to task bodies → read by agents) is theoretical today but becomes concrete if any future UI renders task bodies without rehype-sanitize.

## Confidence

0.87

The decisions tab design itself is sound. The inherited gaps (DNS rebinding, bodyless CSRF, no framing protection) are real but pre-existing and appropriate for a separate mitigation task, not a blocker for this feature. The Host header validation recommendation is the single most impactful improvement the team could make.
