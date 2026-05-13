# Decisions — Body Newline Normalization

## D1 — 2026-05-13 — Project Type

**Decision:** existing-feature/refactor (adding input normalization to an existing MCP server layer).

## D2 — 2026-05-13 — Scope

**Status quo:** 16%+ of task files contain literal `\n` corruption; ongoing in active tasks.
**Decision to make:** Prevention, remediation, or both?

**Options considered:**

- A: Prevention only — normalize at MCP server ingress
- B: Both prevention + one-time archive migration
- C: Remediation only

**Chosen:** A — Prevention only

**Rejected:**

- B because user explicitly scoped to prevention; archive remediation can be a separate task later
- C because the problem is ongoing, prevention is the priority

## D3 — 2026-05-13 — Investment Tier

**Chosen:** Tool — internal utility, narrow blast radius, no external consumers affected. Standard M2, selective panel, full brief.

## D4 — 2026-05-13 — False-Positive Strategy

**Status quo:** Naive `.replace("\\n", "\n")` destroys legitimate literal `\n` in task bodies (code discussions, regex patterns).
**Decision to make:** Accept corruption risk or find a mitigation?

**Options considered:**

- A: Naive replace, accept false positives silently
- B: Normalize-and-notify — replace + inform agent via guidance field; document escape convention for intentional literals
- C: Heuristic detection (only normalize all-single-line bodies, skip bodies with real newlines)
- D: Do nothing — accept the search/grep breakage

**Chosen:** B — Normalize-and-notify

**Rejected:**

- A because silent false positives on code-discussing bodies are unacceptable in this system
- C because heuristics add complexity for marginal accuracy gain; the notify+retry path is simpler and recoverable
- D because 16%+ ongoing corruption rate breaks tooling workflows

## D5 — 2026-05-13 — Layer Placement

**Chosen:** MCP server layer — error originates from agents only, never direct API/engine consumers. Even though "real logic in MCP feels wrong," it's the correct place for agent-specific input sanitization + feedback.
