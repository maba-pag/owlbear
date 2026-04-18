# Security Stance — Cockpit v1

**Panelist:** The Skeptic (ideation-security)
**Hardened after:** 5 Critic cycles
**Confidence:** 0.78 — high on network/auth/CSRF/boundary enforcement; moderate on freshness mechanism (requires architecture input)

---

## 1. Network Binding and Auth Posture

**Position:** Bind `127.0.0.1` only. No authentication for v1.

**Trust model (two layers):**

- **Network layer:** Localhost binding prevents all remote access. Sufficient for single-user laptop.
- **Origin layer:** Cross-origin browser attacks (tabs, iframes) are real on localhost. Addressed by CSRF controls (§4) and clickjacking defense (§4).

**Auth rationale:** On a single-user laptop, all local processes run as the same OS user. A local attacker (process, browser extension, embedded webview) already has filesystem access to task files. App-level auth cannot defend against an attacker at the same privilege level as the authenticated user. Auth adds friction with no defense gain.

**Scope exclusion (explicit):** Local non-browser clients, browser extensions, and same-user webviews are OUT of the v1 threat model. These principals have the same OS-level access as the cockpit user — they can read/write task files directly. App-auth doesn't help; defense is OS-level (don't install malicious software).

**Shoulder-surfer:** Visual-only access during active demos. The user drives the keyboard/mouse. Physical access to an unlocked machine is an OS-level concern. **Residual risk:** task bodies may contain incidental secrets visible on screen during demo (§5).

**DNS rebinding defense:** Host header validation on the backend — reject requests where `Host` is not `localhost`, `127.0.0.1`, or `[::1]`. This is the primary defense against rebinding (attacker keeps the browser on their hostname while DNS resolves to 127.0.0.1). CORS and custom headers provide additional friction but are not the operative control for this attack class.

---

## 2. XSS / Markdown Rendering — The Primary Security Control

**Position:** XSS prevention is the single most critical security control for the cockpit.

### Why XSS Is Elevated

Same-origin XSS gives full API access: the payload can set custom headers, satisfy Origin checks, call any mutation endpoint, and bypass UI-only confirms. The consequences:

1. **Unauthorized mutations:** Move tasks, edit bodies, release claims — all without user awareness or consent.
2. **Indirect agent-pipeline manipulation:** Task bodies are agent context. Agents consume body content as operative instructions. An XSS-injected body edit can steer future automated agent behavior. This is indirect prompt injection into the OwlBear pipeline.

Note: body editing is intended cockpit authority — users are supposed to edit bodies. The security boundary is **authorization** (user chose to edit) vs. **unauthorized** (script edited without user knowledge). XSS removes the user from the loop.

### Defense Layers

**Layer 1 — Sanitization (CRITICAL):** `rehypeSanitize` mandatory in the `react-markdown` pipeline. Configuration:

- Strip all HTML tags except safe subset (headings, lists, emphasis, code blocks, tables, blockquotes).
- Strip `<img>` with external `src`. Allow only relative/same-origin images if needed.
- Strip `<iframe>`, `<object>`, `<embed>`, `<form>`.
- Strip `javascript:`, `data:`, and `vbscript:` link schemes.
- Rewrite external `<a>` links with `rel="noopener noreferrer" target="_blank"`.

**Layer 2 — Content Security Policy (CRITICAL):** Served by the FastAPI backend on every response:

```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self';
connect-src 'self';
frame-src 'none';
frame-ancestors 'none';
form-action 'self';
base-uri 'self';
```

Key effects: `script-src 'self'` blocks inline scripts even if sanitizer misses one. `frame-ancestors 'none'` prevents clickjacking. `form-action 'self'` blocks form-based exfiltration.

**Layer 3 — Frontmatter fields:** Rendered as plain text via React JSX escaping. `dangerouslySetInnerHTML` is forbidden for any field. This includes title, tags, priority, block_reason, depends_on, parent — all user-visible strings from YAML frontmatter.

### Post-XSS Containment (LIMITED — Prevention Must Hold)

If both sanitization AND CSP fail, containment is weak. The attacker operates with full same-origin access. No auth tokens to steal (no auth), but full mutation access. The audit trail (§6) cannot distinguish XSS-driven mutations from legitimate user actions — both log as `actor: "cockpit"`.

**Implication:** Sanitization and CSP are not defense-in-depth luxuries. They are load-bearing. Gaps in either layer must be treated as P0 security bugs.

---

## 3. Agent-Field Boundary Enforcement

**Position:** Enforce at the backend HTTP layer (trust boundary) AND the UI (defense-in-depth).

### Backend Adapter (Trust Boundary)

| Category | Fields/Methods | Enforcement |
|----------|---------------|-------------|
| **Forbidden fields** | `id`, `created_at`, `updated_at`, `claimed_by`, `claimed_at`, `claim_timeout` | HTTP layer rejects mutation. 400 error. |
| **Forbidden methods** | `claim_task`, `start_work`, `end_work`, `pick_dispatchable` | No endpoint exists. Structural enforcement. |
| **Allowed editable fields** | `title`, `tags`, `priority`, `depends_on`, `parent`, `block_reason`, `body` | Allowlisted in adapter. Unknown fields rejected. |
| **Allowed mutations** | `move_task` (via `valid_transitions`), `edit_task` (via field allowlist), `release_task` | Endpoint exists with validation. |

### D4 Invariant Enforcement

The engine's `release_task` unclaims unconditionally — it does not distinguish stuck (expired) from active claims. D4 says "humans release **stuck** work."

**Recommendation:** The backend adapter should check claim expiry before release. If the claim is active (not expired), require an explicit `force: true` parameter. The UI maps this to the confirm dialog (O6). This enforces D4 structurally — important because XSS can bypass UI-only confirms. Without backend enforcement, D4 is a policy-in-prose, not a control.

### UI Layer (Defense-in-Depth)

- Read-only fields: no interactive affordances (no edit buttons, no inputs, no contenteditable).
- Agent-only operations: no UI buttons or routes.
- Missing backend enforcement is a **P0 bug** regardless of UI state.

---

## 4. CSRF / Same-Origin / Clickjacking

**Position:** CSRF is a real concern on localhost. Three-layer defense:

| Layer | Control | What It Stops |
|-------|---------|--------------|
| **Primary** | Custom header `X-Cockpit-Request: 1` on all mutations | Cross-origin form submissions, simple requests. Forces CORS preflight. |
| **Secondary** | CORS: `Access-Control-Allow-Origin: http://localhost:PORT` (exact, no wildcards) | Cross-origin JavaScript reads and preflighted requests from other origins. |
| **Tertiary** | `Origin` header validation on mutations; `Host` header validation on all requests | Spoofed origins, DNS rebinding. Host validation is the primary rebinding defense. |

**Clickjacking:** `frame-ancestors 'none'` in CSP (§2) prevents the cockpit from being framed by a hostile page.

**Scope:** These controls defend against browser-based attacks. Local processes and extensions are out of scope (§1).

---

## 5. Secrets Exposure

**Position:** Low structural risk for v1. Task data and activity log entries contain no MCP config, API keys, or environment variables.

**Residual risk — incidental secrets in task bodies:** Users or agents may paste credentials, internal paths, or operational snippets into markdown bodies. The cockpit cannot distinguish secrets from legitimate content.

Mitigations:
- CSP blocks script-based exfiltration of displayed content.
- Sanitization blocks XSS-based extraction.
- Localhost binding prevents remote eavesdropping on HTTP traffic.
- Visual exposure during demo: **accepted residual risk** — user discipline and OS screen controls.

**Remote-bind rule:** If `--allow-remote` is enabled (§7), auth must protect ALL endpoints — reads AND mutations. Task bodies with incidental secrets must not be readable without authentication over a network.

**Future-surface rule:** Cockpit surfaces must NEVER render MCP config, API keys, or environment variables. Any surface that touches config files requires a secrets-redaction contract before implementation.

---

## 6. Audit Trail

**Position:** `actor: "cockpit"` for all GUI-initiated mutations. Sufficient for v1.

The engine must accept and propagate the `actor` parameter to `activity.jsonl`. This distinguishes human-via-cockpit mutations from agent mutations (which use agent names like `"builder"`, `"orchestrator"`).

**Limitation (accepted):** For single-user v1, `"cockpit"` identifies the channel, not the individual. Multi-user attribution (`"cockpit:<user>"`) is deferred until multi-user is in scope. Additionally, XSS-driven mutations also log as `"cockpit"` — the audit trail cannot distinguish legitimate from injected operations (§2). This is inherent to any same-origin attack and reinforces why XSS prevention is the primary control.

---

## 7. Highest-Risk Security Assumption

**"Binding to localhost is sufficient network isolation."**

### Why This Is the Riskiest

If this assumption is violated — whether by DNS rebinding, a deliberate `--host 0.0.0.0` for demo, or a future requirement for remote access — the entire security posture collapses simultaneously: no auth, limited CSRF protection, secrets readable over the network.

### Safeguard

The server startup must **refuse to bind to any address other than `127.0.0.1`** unless an explicit `--allow-remote` flag is provided. When `--allow-remote` is set:

1. Log a prominent startup warning.
2. Require a bearer token on ALL endpoints (reads + mutations).
3. Document that the single-user no-auth model no longer applies.

Make the safe path the default. Make the unsafe path require deliberate opt-in with compensating controls.

### Validation

- **Test:** Default bind is `127.0.0.1`.
- **Test:** Non-localhost bind without `--allow-remote` raises a startup error.
- **Document:** Localhost binding as a load-bearing security boundary in the architecture contract (O7).

---

## Risk Assessment Summary

| Risk | Severity | Mitigation | Residual |
|------|----------|------------|----------|
| XSS → agent pipeline manipulation | **High** | rehypeSanitize + CSP (both critical) | Low if both layers hold; High if either fails |
| CSRF from cross-tab | Medium | Custom header + CORS + Origin/Host validation | Low |
| Stale view → clobbered edits | Medium | Filesystem-level change detection + traffic light | Medium (3s window inherent) |
| Incidental secrets on screen | Medium | CSP + sanitization + localhost binding | Medium (visual exposure during demo) |
| Localhost assumption violated | **High** | --allow-remote gate + mandatory auth | Low if gate holds |
| D4 violation (release active work) | Medium | Backend stuck-only check with force parameter | Low |
| DNS rebinding | Medium | Host header validation | Low |
| Clickjacking | Low | `frame-ancestors 'none'` in CSP | Negligible |

---

## Warnings

1. **XSS sanitization and CSP are load-bearing, not optional.** If either has a gap, the cockpit becomes an indirect agent control plane. Treat sanitization bypasses as P0 security bugs.
2. **The cross-process freshness mechanism is a security prerequisite.** The traffic light's trustworthiness — and therefore the stale-write acceptance — depends on detecting external filesystem mutations. The per-instance revision counter is insufficient. The implementation mechanism (mtime, inotify, hash comparison) is an architecture decision, but the requirement is non-negotiable.
3. **Never add `--host 0.0.0.0` without the `--allow-remote` gate.** A one-line config change should not collapse the entire security model.
4. **`dangerouslySetInnerHTML` is forbidden** for any field rendered from task data. This includes frontmatter strings and body content. Violations are P0.
