# End-User Stance — Dep-Status Guidance in start_work

## User Experience Stance

The proposed guidance text is well-calibrated for its consumer (an AI agent receiving advisory JSON) and its channel (a soft gate where the task is already claimed). The original wording needs only one editorial fix. Do not over-engineer the message.

**Proposed (from research-notes):**
```
⚠ This task has unresolved dependencies (IDs: 42, 78). Review and confirm with the user that starting this work is intentional.
```

**Recommended (single fix — emoji consistency):**
```
⚠️ This task has unresolved dependencies (IDs: 42, 78). Review and confirm with the user that starting this work is intentional.
```

## Usability Reasoning

1. **"Review and confirm" is a clear two-step affordance.** "Review" tells the agent to inspect the dependency IDs (which are actionable — the agent can call `show_task` on each). "Confirm with the user" names the human checkpoint. This is not ambiguous; it's a sequence matched to the agent's capabilities.

2. **Advisory tone matches the advisory channel.** The task is already claimed when guidance appears. This is informational, not a gate. The phrasing "confirm … that starting this work is intentional" mirrors the existing skip-transition pattern ("Verify this jump is intentional") — both state condition and recommended action without pretending to be mandatory. Don't harden the directive (e.g., "Ask the human user to confirm") beyond what the system enforces.

3. **Flat format with IDs is sufficient.** The agent gets the dep IDs and can look them up. Per-dep status detail would be gold-plating for a soft advisory on an edge path. The IDs are the escape hatch for curiosity.

4. **Don't embed a risk rationale.** "Blocked" covers multiple dep states (active, missing, non-completion archive). Any single risk description ("work may be incomplete") will be wrong for some cases. The condition name ("unresolved dependencies") is honest and generic. Let the agent or human assess the specific risk after reviewing the deps.

5. **Consistent with existing guidance contract.** The skip-transition pattern is: emoji + condition + action-verb + "intentional." The dep-status message follows the same structure. Tests treat guidance wording as contract-sensitive — consistency reduces test fragility and agent confusion.

## Key Trade-offs

| Choice | Upside | Downside |
|--------|--------|----------|
| Keep advisory tone | Honest about what the channel enforces | Agent *could* ignore it |
| Omit risk clause | Never factually wrong across dep states | Human gets less context upfront |
| Flat IDs, no per-dep detail | Simple, low-cost, no gold-plating | Agent must look up deps manually for context |

## Warnings

- **Do not over-optimize for AI parsing.** The temptation is to restructure the message for agent consumption (e.g., structured prefixes, explicit action labels). But this is a single advisory string in a list — the simpler it is, the more robust it is across different agent models and instruction sets.
- **Emoji consistency matters for pattern matching.** Use ⚠️ (U+26A0 + U+FE0F variation selector), not bare ⚠ (U+26A0). The existing skip-transition guidance uses the variation-selector form. Agents or tests that pattern-match on the emoji prefix will break on inconsistency.

## Confidence

**0.82** — The original text is well-designed for its purpose. My initial instinct to rewrite it for "AI clarity" was an over-correction that the Critic rightly challenged. The one genuine fix is the emoji variant.
