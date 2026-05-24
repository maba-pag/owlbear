# Synthesis — Decision Request Data Model

## Summary

Four stances converge strongly on the structural backbone: two kinds, UUID4 identity, single engine writer, Pydantic-validated models, kind-discriminated validation, and engine-mediated blocking semantics. The primary tensions are: (1) whether agents may resolve requests, (2) how `needs-info` is modeled, (3) exact action resolution states, and (4) field size limits where stances disagree on specific caps.

---

## Convergences

All four panelists agree on:

| # | Position |
|---|----------|
| 1 | Two kinds only: `decision` (choose from options) and `action` (approve/deny an outcome) |
| 2 | `request_id` = UUID4; filename = `{request_id}.md` |
| 3 | Single engine writer — no layer writes DR files directly except the engine |
| 4 | Pydantic models with `extra="forbid"` and kind-discriminated cross-field validation |
| 5 | Decisions require ≥2 options; actions have zero options |
| 6 | `confidence: float` (0.0–1.0) per option, independent (not sum-to-1) |
| 7 | At most one `recommended=True` per request |
| 8 | `free_text` always available on resolution (optional, never hidden) |
| 9 | Resolution writes ID-tagged summary to task body (HTML comment marker for idempotency) |
| 10 | `create_request` sets `task.blocked=True`; `resolve_request` unblocks only if no sibling pending requests remain |
| 11 | Malformed files surfaced as error objects, never silently dropped |
| 12 | Agent-controlled content validated at creation (never raw YAML to disk) |
| 13 | Slug-format option IDs (lowercase alphanumeric + hyphens, human-readable) |
| 14 | Resolved files are immutable (audit trail) |
| 15 | Sweep exists as crash-recovery/power-user fallback, not primary resolution path |

---

## Divergence Matrix

| Decision Point | architect | data | enduser | security | Tension |
|----------------|-----------|------|---------|----------|---------|
| **Agent resolve capability** | Yes — both humans and agents via MCP tool; self-resolution blocked by instructions | Silent (no position) | Silent (no position) | **Strong no** — no MCP resolve tool in default surface; human-only oversight | **High** |
| **`needs-info` modeling** | Resolution status (`needs-info` alongside `approved`/`rejected`) | **Not** a resolution — modeled as `Note` in a `notes[]` list; request stays pending | Not addressed | Not addressed | **Medium-High** |
| **Action resolution statuses** | `completed`, `failed`, `rejected` | `done`, `rejected` | "completed-successfully, completed-with-issues, rejected" (notes these are open) | Not specified | **Medium** |
| **Decision resolution statuses** | `approved`, `rejected`, `needs-info` | `approved`, `rejected` (only terminal) | Not specified | Not specified | **Medium** |
| **Max options per request** | Not capped (implied unlimited) | 10 | "5+ is an agent smell" but handle it | 2–8 | **Low** |
| **Option label max chars** | 120 | 120 | Not specified | 200 | **Low** |
| **Option rationale max chars** | 500 | 500 | Not specified | 1000 | **Low** |
| **Option ID regex** | `^[a-z0-9][a-z0-9-]{0,48}[a-z0-9]$` (no trailing hyphen, ~50 max) | `^[a-z0-9][a-z0-9-]{0,62}$` (63 max) | Not specified | `^[a-z0-9][a-z0-9-]*$`, max 64 | **Low** |
| **Notes/clarification thread** | Not mentioned | `notes: list[Note]` (max 20) for needs-info interactions | Not addressed | Not addressed | **Medium** |
| **Resolution atomicity** | Multi-step with marker-based idempotency + sweep recovery | Not specified | Not addressed | `rename()` as commit step; write-back only after successful rename | **Low-Medium** |

---

## Expectation Fit

How the converged approach delivers on the product promise from `context.md`:

| Promise | How the dominant approach satisfies it |
|---------|----------------------------------------|
| **Real choice system** | Structured options with `option_id`, `label`, `confidence`, `rationale`, `recommended` — machine-readable intent from agents |
| **Option cards** | Cockpit receives typed `options[]` from API — no body-text heuristics needed for rendering |
| **Free text always available** | All four stances agree `free_text` is optional but always present in the resolution surface |
| **Mechanical resolution flow-back** | Engine writes ID-tagged summary to task body on resolve; all stances converge on this |
| **Action states** | Actions use distinct resolution states (not option-selection); both architect and enduser confirm different resolver UX for actions vs decisions |
| **Blocking/unblocking** | `create_request` → `blocked=True`; `resolve_request` → conditional unblock (sibling check). Single source of truth is `task.blocked` attribute |

The converged model fully supports the product promise at data-model level. Remaining UI implementation (option cards, quick-confirm, outcome buttons) is Phase 2 frontend work that consumes this model without requiring model changes.

---

## Recommended Resolution

### 1. Agent Resolve Capability — **Defer (no tool now, gate conditions for future)**

**Reasoning:** Security's position is structurally correct — the blocking mechanism's purpose is human oversight. The architect's pragmatic concern (agents sometimes need to resolve) is real but speculative today. The security stance provides explicit gate conditions for adding it later. Ship without MCP resolve tool; document the gate conditions as a future-unlock checklist.

### 2. `needs-info` Modeling — **Adopt Data's `notes[]` approach**

**Reasoning:** The architect's `needs-info` as a resolution status creates a "resolved but still blocking" contradiction (data stance L105). Modeling it as a Note keeps the request pending and the task blocked — which is the correct semantic: the decision is NOT made yet. The notes list is lightweight (max 20 entries, simple model). The enduser stance's feedback loop naturally accommodates this: a "request more info" action appends a note and returns the user to the list.

### 3. Action Resolution Statuses — **`done` + `rejected`**

**Reasoning:** Data's minimal pair (`done`, `rejected`) covers the terminal states cleanly. The enduser's "completed-with-issues" is captured via `free_text` on a `done` resolution — the outcome is still "done" but with notes. Adding `failed` (architect) as distinct from `rejected` conflates "I tried and it didn't work" with terminal state semantics that don't map to the user's approval power. If the user approves, it's `done`; if they deny, it's `rejected`. Execution details go in `free_text`.

### 4. Decision Resolution Statuses — **`approved` + `rejected`**

**Reasoning:** Follows from adopting notes for `needs-info`. Terminal-only resolution is cleaner. `approved` requires `selected_option_id`; `rejected` forbids it (per data stance). Both allow optional `free_text`.

### 5. Max Options — **10 (with agent instruction guidance toward 2–4)**

**Reasoning:** Security's 8 is defensible but arbitrary; data's 10 gives marginal breathing room at negligible cost. Enduser's "5+ is an agent smell" belongs in agent instructions, not schema enforcement.

### 6. Field Sizes — **Architect/Data alignment (120 label, 500 rationale)**

**Reasoning:** Security's larger caps (200/1000) aren't grounded in an observed need. The tighter caps from architect+data prevent bloat in the task-body write-back. If too tight in practice, loosening later is non-breaking.

### 7. Option ID Regex — **`^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$` (max 63, no trailing hyphen)**

**Reasoning:** Merge data's 63-char DNS-label length limit with architect's no-trailing-hyphen constraint. 63 chars is a well-understood boundary (DNS labels). Forbidding trailing hyphens prevents YAML rendering edge cases.

### 8. Notes List — **Include (per data stance)**

**Reasoning:** Required to support `needs-info` as non-terminal interaction. Bounded at 20 entries. Simple `Note(author, timestamp, content)` model. Adds one field to the schema but eliminates the needs-info semantic contradiction.

### 9. Resolution Atomicity — **Rename-as-check (security) + marker idempotency (architect)**

**Reasoning:** Not contradictory — combine both. Use `rename()` as the commit step to prevent duplicate resolution (security). Use the HTML comment marker in task body to prevent duplicate write-back on crash recovery (architect). Belt and suspenders for a multi-step operation.

---

## Open Questions

| # | Question | Why user input needed |
|---|----------|---------------------|
| 1 | **Action resolution: is `done`/`rejected` sufficient, or do you want a third state?** The enduser stance floated "completed-with-issues" as distinct from "done." Do you use `free_text` for that nuance, or want it as a separate status? | Affects model enum, UI button count, and downstream agent interpretation |
| 2 | **Notes interaction: who writes notes?** Data proposes a `notes[]` list for needs-info exchanges. Can both the user (via Cockpit) and agents (via MCP) append notes? Or is it user-only? | Determines whether an `append_note` MCP tool is needed |
| 3 | **Quick-confirm mode: build it in Phase 2 or defer?** Enduser proposes pre-selecting the recommended option when confidence spread is high. This is UX logic on top of the data model (no model change needed). Worth the implementation cost for a low-volume single-user system? | Scoping question for Phase 2 frontend |
| 4 | **CORS invariant enforcement: test assertion or explicit middleware?** Security requires CORS restriction as a tested invariant. Prefer (a) a test that asserts no permissive CORS middleware exists, or (b) an explicit restrictive CORSMiddleware that allowlists only the served origin? | Implementation choice with different maintenance profiles |
| 5 | **Confidence: 0.74–0.82 range across stances.** All positions are qualified but not fully confident. Are you comfortable proceeding to Brief with these resolutions, or do any divergences warrant another round? | Meta-decision on process |
