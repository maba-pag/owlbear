# Data Quality Stance — Body Newline Normalization

## Position

Accept D4's normalize-and-notify design. Implement three-step escape-protected normalization at the MCP server ingress boundary. The escape convention (agent sends `\\\\n` in JSON to preserve intentional literal `\n` after JSON parse) is viable and uses placeholder-based protection. The non-idempotency this introduces is structural — it limits the escape convention's value to first-write fidelity, not full lifecycle preservation.

## Schema and Validation Reasoning

### Body field schema contract

The body field's implicit schema is: **markdown text with actual newline characters as line separators.** The double-escape bug injects the literal two-character sequence `\` + `n` (0x5C 0x6E) where a newline (0x0A) should be. This violates the schema and breaks grep/regex tooling. Normalization enforces the schema contract at the ingress boundary.

### Three-step normalization spec

The function processes post-JSON-parse Python strings. All byte references below are post-JSON-parse values.

1. **Protect:** Replace `\\n` (3 bytes: 0x5C 0x5C 0x6E) → sentinel placeholder. This preserves intentional literal `\n` written by agents using the escape convention.
2. **Normalize:** Replace `\n` (2 bytes: 0x5C 0x6E) → actual newline (0x0A). This fixes the double-escape corruption.
3. **Restore:** Replace placeholder → `\n` (2 bytes: 0x5C 0x6E). Protected literals return to their original form.

**Sentinel choice:** `\x00ESCAPED_NEWLINE\x00`. Null bytes cannot arrive through the JSON-based MCP transport layer (JSON has no native null-byte encoding). Risk is extremely low, not formally zero — the pipeline has no explicit null-byte input validation.

### Escape convention

Agent convention for intentional literal `\n` in body content:

| Agent intent | JSON encoding | After JSON parse | After normalization |
|---|---|---|---|
| Newline (correct) | `\n` | newline (0x0A) | Unchanged |
| Newline (bugged) | `\\n` | `\n` (0x5C 0x6E) | Newline (0x0A) ✓ fixed |
| Literal `\n` | `\\\\n` | `\\n` (0x5C 0x5C 0x6E) | `\n` (0x5C 0x6E) ✓ preserved |

This convention MUST be documented in the MCP tool descriptions for `create_task`, `edit_task`, `end_work`, and `create_dr` — tool descriptions are where agents learn parameter contracts.

### Scope: `\n` only, not `\r\n`

Context confirms the problem is newline-specific — `\t` and `\\` corruption do not occur. Normalizing double-escaped `\r\n` would expand scope and introduce a new false-positive class (bodies discussing `\r\n` as payload) without a corresponding escape convention. **Recommendation:** Normalize `\n` only. If `\r\n` corruption is observed later, add it as a scoped follow-up with its own escape path.

## Key Trade-offs

| Decision | Favored | Sacrificed |
|---|---|---|
| Three-step over simple replace | Escape convention viability (D4 compliance) | Idempotency |
| `\n`-only scope | Consistency with observed problem | Theoretical completeness for `\r\n` |
| Non-idempotent function | First-write fidelity for intentional literals | Full lifecycle preservation on re-edit |
| Sentinel placeholder | Simple implementation | Hard collision guarantee (extremely low risk, not zero) |

## Warnings

### 1. Non-idempotency is structural, not contained

The three-step function is NOT idempotent. Applying it twice converts restored `\n` literals to newlines. This constraint is manageable per-invocation (normalize once at the tool handler), but the content lifecycle is multi-invocation: agents read bodies via `show_task` and re-submit via `edit_task`. Each re-submission triggers normalization. Intentional literals preserved on first write degrade on re-edit by unaware agents.

**Implication:** The escape convention provides first-write fidelity only. Document this as a known limitation.

### 2. `create_dr` contract contradiction

`create_dr` returns `dict[str, object]` (locked by D13 in the DR-script-replacement brief, with existing test assertions on the response shape). It has no `guidance` field. The locked outcomes require both:

- "All text body fields normalized at MCP ingress" → demands normalization for `create_dr`
- "When normalization occurs, guidance informs the agent" → impossible without changing `create_dr`'s response contract

This is an **unresolvable tension within the current brief scope**. Options:

| Option | Honors normalization | Honors notification | Contract impact |
|---|---|---|---|
| (a) Add `guidance` key to `create_dr` response | ✓ | ✓ | Breaks D13 lock + existing tests |
| (b) Normalize without notification | ✓ | ✗ | Silent false positive (D4 rejects this) |
| (c) Skip normalization for `create_dr` | ✗ | N/A | Inconsistent — corrupted DR bodies |

**Recommendation:** This needs a brief-level decision. The data integrity argument favors (a) or (b): corrupted files are worse than missing notifications. If scope constraints force (c), document the asymmetry.

### 3. False-positive frequency is unquantified

The 16.5% stat measures corruption prevalence, not intentional-literal prevalence. The archive contains both corrupted bodies and bodies that intentionally discuss `\n` as payload (e.g., output format strings like `"Relevant knowledge:\\n\\n- title: content"`). These are real false positives, not manufactured ones — converting those literals to newlines changes the described string, not just formatting.

The three-step approach handles both cases correctly. The confidence score reflects this unquantified gap.

### 4. Body fields only

Normalization applies to freeform text body parameters only: `body` in `create_task`/`edit_task`, `append_body` in `edit_task`, `note` in `end_work`, `body` in `create_dr`. Never apply to structured fields (title, tags, IDs, status) — that would violate their schema.

### 5. Normalize exactly once

The function must be called at the MCP tool handler level only. Name it clearly (e.g., `normalize_agent_body`) to signal its single-application constraint. Do not expose it as a shared utility.

## Confidence

**0.75** — The three-step normalization design is sound for first-write correctness. Confidence is reduced by: (1) the `create_dr` contract contradiction remains unresolved, (2) false-positive frequency is unquantified, and (3) the escape convention's practical value depends on agent cooperation that the brief acknowledges is unreliable.
