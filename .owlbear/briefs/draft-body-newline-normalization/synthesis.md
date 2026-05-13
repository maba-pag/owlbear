# Synthesis — Body Newline Normalization

## Summary

Two stances (architect, data) converge on the viability and placement of normalize-and-notify at the MCP server ingress boundary for the 5 identified text body parameters. They diverge on **implementation mechanics** (simple replace vs. three-step placeholder protection) and on the **honesty of the escape convention** — whether a documented retry path actually works in practice. Both flag the `create_dr` response contract as a concrete blocker requiring a decision.

---

## Convergences

| Point | Architect | Data |
|-------|-----------|------|
| **Layer placement** | MCP server boundary (`server.py`) — correct and sufficient | Same — ingress-only, schema enforcement |
| **Scope: 5 parameters** | `body` (create/edit), `append_body`, `note`, `body` (create_dr) | Same enumeration, same "structured fields never" rule |
| **Scope: `\n` only** | Implicit (only discusses `\n`) | Explicit recommendation — no `\r\n` expansion |
| **Named helper, not inline** | Yes — documents intent, centralizes | Yes — name signals single-application constraint |
| **Guidance append ordering** | MUST come after the existing `if not result.guidance` block | (Not discussed, but compatible — no contradiction) |
| **Tool metadata documentation** | Required — agents learn contracts from descriptions | Required — same reasoning |
| **`create_dr` is a problem** | Acknowledges dict shape change needs downstream check | Calls it an unresolvable tension within current scope |
| **No clean escape at byte level** | Explicitly states the circularity; triple-escape doesn't work | Proposes a convention (`\\\\n` in JSON → preserved) but flags non-idempotency as structural |
| **Test surface is broader than the diff** | Warns MCP mutation tests pin exact bodies and guidance | Compatible (implicit) |

---

## Disagreements

### 1. Simple replace vs. three-step placeholder protection

| | Architect | Data |
|--|-----------|------|
| **Design** | `text.replace("\\n", "\n")` — one-liner, detect-before-call pattern | Protect → Normalize → Restore with null-byte sentinel |
| **Rationale** | Triple-escape is circular; no escape path exists; keep it simple | Escape convention is viable for first-write; three-step makes it work |
| **Trade-off accepted** | Rare false positives on intentional literals, offset by notification transparency | Non-idempotency (re-edit degrades preserved literals) |

**Tension level: Medium.** This is the central design fork. Simple replace is smaller and acknowledges no escape path exists. Three-step is larger but offers first-write protection for agents that cooperate. Both agree the escape convention has limited lifecycle value.

### 2. Escape convention viability

| | Architect | Data |
|--|-----------|------|
| **Position** | "Unresolvable at the string level" — documenting limitation is better than promising a mechanism | Viable for first-write via `\\\\n` JSON encoding; degrade-on-re-edit is a documented limitation |
| **Implication** | Guidance message is transparency, not a functional retry path | Guidance message enables an agent to retry with the escape convention |

**Tension level: Low-Medium.** Both agree the convention degrades over the content lifecycle. The disagreement is whether to offer it at all (architect: don't promise what doesn't fully work) vs. offer it with documented caveats (data: first-write fidelity has value).

### 3. `create_dr` notification path

| | Architect | Data |
|--|-----------|------|
| **Position** | Add `guidance` key to the dict — 3 lines, acceptable | Flags this as a contradiction with D13 lock; needs a brief-level decision among options (a)/(b)/(c) |

**Tension level: Low.** Both favor option (a) in substance. The data stance is more cautious about the contract-break implications.

---

## Recommendation

Implement the **simple replace** (architect's design) with the **data stance's documentation discipline** (tool metadata, `\n`-only scope constraint, "normalize exactly once" naming signal). The three-step placeholder design adds complexity for an escape convention both stances agree degrades on re-edit — the marginal first-write benefit does not justify the sentinel risk and non-idempotency maintenance burden.

For `create_dr`: add the `guidance` key (option a) and update affected tests. The contract break is minor and contained.

**Confidence: 0.72** — Grounded in the convergence on layer placement and the shared skepticism about escape convention lifecycle viability. Reduced because the escape convention question is genuinely a values call (simplicity vs. first-write correctness) that the stances don't fully resolve.

---

## Open Questions

1. **Simple replace or three-step?** The stances diverge here. User decision needed: accept that no escape path exists (architect) or offer a first-write-only escape convention (data)?

2. **`create_dr` response shape:** Both stances favor adding a `guidance` key, but data flags a potential D13 lock conflict. Confirm that adding an optional key to the dict is acceptable.

3. **Guidance message wording:** Should it reference an escape convention (implying one exists) or simply state that normalization occurred (no promise of a workaround)?

4. **Test scope in task AC:** Architect warns that MCP mutation tests will break. Should updating pinned test assertions be an explicit AC item or left to implementation discretion?
