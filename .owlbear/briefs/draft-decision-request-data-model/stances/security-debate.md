# Security Stance — Critic Debate Log

## Cycle 1: Initial Draft → Critic Response

### Draft Position Summary

- Threat model: hallucinating LLM agents, not malicious humans
- YAML injection eliminated by engine-controlled serialization
- MCP resolve tool: strong no
- Filesystem safety: UUID4 filenames eliminate path traversal
- Auth/CSRF on localhost dismissed as theater
- Validation at engine only; other layers minimal

### Critic Challenges (Cycle 1)

1. **Critical — Malformed DR visibility.** If engine drops malformed DRs on parse failure, task stays blocked but DR is invisible in Cockpit. The stated primary adversary (buggy agent) can bypass the visibility mechanism the stance relies on.

2. **Critical — Localhost/browser threat dismissed without support.** Cockpit auto-opens in browser and exposes mutating endpoints. A malicious site in another tab could attempt cross-origin requests. Dismissing CORS/CSRF as theater is unsupported when the system is browser-facing.

3. **Critical — YAML safety ≠ pipeline safety.** Engine-controlled YAML serialization doesn't protect markdown body content that propagates into task bodies via resolution write-back. Trust boundary is wider than the DR file.

4. **Moderate — Validation boundary too absolute.** Calling boundary-local checks "theater" contradicts the running system which already relies on size limits, field allowlisting, and ID format validation at Cockpit layer.

5. **Moderate — UUID4 filenames describe future state.** Current system uses `{task_id}-{slug}.md` pattern. Stance presents future guarantee as current.

### Blind Spots Surfaced

- Option-set integrity (uniqueness, immutability, count bounds) absent
- Malformed-request observability absent
- Propagation surface (DR → task body) not treated as trust boundary
- Availability concerns largely absent
- Directory-path trust unexamined

### Refinement Response

Accepted all five challenges. Revised stance to: (a) add secondary threat model for cross-origin browser attacks, (b) require malformed DR observability, (c) treat propagation to task body as a separate trust boundary, (d) acknowledge boundary-local checks as legitimate, (e) clarify UUID4 is the new design per D3.

---

## Cycle 2: Revised Draft → Critic Response

### Revised Position Summary

- Two adversary classes: buggy agents + cross-origin browser attacks
- CORS restriction explicit requirement (no wildcard)
- Propagation trust boundary acknowledged
- Malformed DR observability required
- Boundary-local checks legitimate at each layer
- UUID4 clearly stated as new design

### Critic Challenges (Cycle 2)

1. **Critical — "Human-only" enforcement is ungrounded.** Stance says agents shouldn't resolve, but also says no auth. The enforcement mechanism isn't stated. What actually prevents an agent from calling the Cockpit resolve endpoint?

2. **Critical — Stale resolution isn't atomic.** Current code reads state, rewrites file, performs side effects, then moves — two callers can both observe "pending" before either move completes.

3. **Critical — Propagation boundary is ambiguity moved downstream.** Heading+blockquote distinguishes visually but downstream agents still consume task-body markdown as authority. Unless write-back is machine-parseable, the trust boundary is naming, not enforcement.

4. **Moderate — Malformed card actionability.** UUID filename + corrupted frontmatter = card with no task linkage. Human sees opaque malformed entry, can't easily trace back to blocked task.

5. **Moderate — CORS defense is implicit absence.** No CORSMiddleware in source — the boundary is a non-configured default, not an explicit invariant. Fragile against future additions.

### Blind Spots Surfaced

- Agent capability assumptions unstated (do agents have HTTP access?)
- Authoritative task-body consumers not enumerated
- Minimum metadata surviving catastrophic parse failure undefined
- Regression observability for CORS/resolution constraints undefined

### Refinement Response

Accepted all. Final stance addresses: (a) enforcement mechanism is MCP tool surface — agents don't have HTTP access to Cockpit, they only have MCP tools, (b) resolution atomicity via rename-as-check, (c) write-back should be structured/delimited to prevent authority confusion, (d) partial parse for task_id as fallback for malformed entries, (e) CORS restriction as documented invariant not implicit default.
