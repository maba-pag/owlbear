# Synthesis — Cockpit Memory Tab

## Summary

Four stances converge strongly on the core shape: a Memory tab in the cockpit backed by a shared engine, reading memory files from disk, enforcing state machine integrity, and rendering content safely. The primary structural disagreement is whether engine extraction (`serve/memory/`) is a hard prerequisite or an acceptable-if-tested deferral. All stances agree on OCC via `expected_updated_at`, the state transition table, client-side filtering, and id-addressed mutations. The UX stance proposes inline accordion detail; no stance objects. Security flags XSS as the highest-impact risk, requiring sanitized markdown rendering.

## Convergences

### Full Agreement (4/4)

| Point | Sources |
|-------|---------|
| State machine transitions: `pending→curated→approved`, `approved→curated` on edit, `curated/approved→deleted` (terminal), `pending` = hard-delete | architect §State Machine, data §Transition Guards, enduser §State-Action Matrix, security §3 |
| OCC via `expected_updated_at` for cockpit mutations; MCP tools may bypass | architect §OCC, data §Race Condition, security §8 |
| Client-side filtering (D5); single GET returning all entries | context D5, enduser §Filtering, architect §API Surface |
| ID-addressed mutations only — never accept filenames/paths from client | architect §API, data §ID Uniqueness, security §2 |
| Immutable server-owned fields: `id`, `source_agent`, `created_at`, `updated_at`, `approved_at`, `state` | data §State Machine, security §3 |
| Edit of approved entry auto-downgrades to curated, clears `approved_at` | architect §State Machine, data §Edit Downgrade, enduser §Confirmation, security §3 |
| Confirmation dialogs for both hard-delete (pending) and soft-delete (curated/approved) | enduser §Confirmation (security agrees delete is destructive) |
| Path containment: `resolved.is_relative_to(memory_dir)`, reject symlinks | architect (implied by disk reader), security §2 |
| Safe YAML parsing only (`safe_load`); catch errors, skip malformed files | data §Malformed File, security §5 |
| Deleted state is terminal — no transitions out | all four stances explicitly |

### Strong Agreement (3/4, one silent)

| Point | Agreeing | Silent |
|-------|----------|--------|
| Nav-rail badge showing pending count | enduser, architect, context | security |
| Markdown rendering must sanitize HTML (rehype-sanitize or allowlist) | security (HIGH), enduser (implied by PDS), architect (implied) | data |
| Atomic writes via temp-file + rename | architect, data, security | enduser |
| File size bound (~8KB) as defense against malformed files | security §5, data §Malformed File | architect, enduser |
| `parse_errors` count in response metadata | data §Malformed File | others silent but non-contradicting |

## Disagreements

### 1. Engine Extraction: Hard Prerequisite vs Acceptable Deferral

| Position | Stance | Key Argument |
|----------|--------|--------------|
| Extract `serve/memory/` first, tab depends on it | **architect** (strong) | "Do not build the tab before the extraction." Logic drift is a category of bug testing cannot fully prevent. |
| Recommend extraction, but tested duplication is acceptable | **data** | Contract tests against `owlbear_mcp_memory.models` catch drift at CI time. Extraction is scope, not integrity. |
| Not a security requirement — document canonical spec and test both surfaces | **security** | Shared package eliminates a maintenance cost but logic drift is medium-severity, not high. |
| Silent | **enduser** | No opinion on internal packaging. |

**Tension level:** Medium. Architect is firm; data and security accept either path if tested. The decision affects task sequencing (prerequisite extraction task vs. parallel development).

### 2. SSE / Real-Time Updates

| Position | Stance |
|----------|--------|
| Add SSE for memory events (~4 integration points, non-trivial but bounded) | **architect** |
| No SSE for V1; refetch after user action + poll-on-focus | **enduser** |
| Silent | **data**, **security** |

**Tension level:** Low-Medium. Architect frames SSE as expected given kanban precedent; enduser argues mutations are user-initiated so freshness is cheap without SSE. This is a scope/sequencing choice, not a correctness one.

### 3. Deleted Entry Default Visibility

| Position | Stance |
|----------|--------|
| Show deleted entries with clear state badging (they exist on disk) | **architect** (recommendation) |
| Exclude from default view; available via state filter opt-in | **enduser** |
| Silent | **data**, **security** |

**Tension level:** Low. Both positions allow viewing deleted entries — the disagreement is only about the default filter state. Enduser position is UX-grounded (reduce noise); architect position is transparency-grounded. These are compatible if the filter defaults to excluding deleted but makes opt-in trivial.

### 4. Detail Pattern (D4 — deferred to mediation)

| Position | Stance |
|----------|--------|
| Inline accordion expand (PAccordion) | **enduser** (detailed justification) |
| No position taken | **architect**, **data**, **security** |

**Tension level:** None. Only one stance addresses this. Enduser's reasoning is well-grounded (content ≤1024 chars, serial review workflow, no drawer pattern in cockpit). No objection from any other stance.

### 5. Duplicate ID Handling

| Position | Stance |
|----------|--------|
| Keep later `updated_at` file, log warning, surface count in metadata | **data** |
| Silent | others |

**Tension level:** None. Uncontested recommendation from the data stance.

## Recommendation

**Approach:** Extract `serve/memory/` as a shared engine package (architect position), then build the cockpit tab consuming it.

**Justification:** Three of four stances either require or prefer extraction. The data stance's fallback (contract tests) is viable but adds ongoing maintenance. The architect's strongest argument — that logic drift between two state machines is a category of bug testing cannot fully prevent — is sound. The extraction is described as "cheap" (most code moves, little rewritten) and follows proven kanban precedent. The sequencing cost is one prerequisite task.

**V1 scope within that structure:**
- Full mutation set (D3: browse + filter + delete + approve + edit)
- Client-side filtering with all-entries GET endpoint
- Inline accordion detail (enduser position, uncontested)
- No SSE — refetch-after-action + poll-on-focus (enduser position; add SSE as follow-on)
- Deleted entries excluded from default filter, opt-in via state filter
- Sanitized markdown rendering (security §1)
- OCC via `expected_updated_at`

**Confidence: 0.80**

High structural agreement on the core shape. The extraction-vs-deferral tension is the only substantive disagreement, and precedent + risk analysis favor extraction. SSE deferral is low-risk and reversible.

## Open Questions

1. **Git commit lifecycle for cockpit mutations.** Architect flags this as needing fresh design during extraction — per-mutation commits vs. batched. No stance resolves it. User decision needed.

2. **Migration sweep for cross-field invariants.** Data stance warns that enabling strict validation on read will surface existing entries violating invariants (e.g., deleted entries with stale `approved_at`). Should the extraction include a one-time migration, or should the reader be lenient on read and strict on write?

3. **Tab infrastructure dependency (#1638).** Context notes this is still in research. Should memory tab work begin before #1638 lands (requiring temporary Shell.tsx modification), or block on it? Architect notes the pre-#1638 shell modification is "real work, not a trivial wire-up."

4. **Approval provenance.** Security notes there is no `approved_by` field. Is this acceptable for V1, or should the extraction add it? (All stances treat this as future enhancement.)

5. **Remote image blocking in rendered markdown.** Security flags outbound beacon exfiltration via image `src` as lower severity than script execution. Should the sanitizer block remote images in V1, or defer?
