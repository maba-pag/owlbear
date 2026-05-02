# Data Debate Log — Neutral Shared Layer

## Cycle 1

### Draft Position (pre-Critic)

Seven claims submitted for challenge:

1. Path strings are implicit data contracts — LLM executes against non-existent paths
2. `{variable, e.g. example}` is a schema with no enforcer — LLMs may misparse braces
3. Resolution join is context-window-dependent — skill may load without copilot-instructions.md
4. Stale examples propagate worse than missing data — "transformer attention" favors examples
5. Cross-reference breaks are foreign-key violations — doc-audit loses r-doc-standards; agent-ecosystem lists moved stubs
6. Prose > template syntax categorically for LLM consumers
7. No validation boundary — missing definitions silently fall back to examples (NaN propagation)

Initial confidence: 0.75

### Critic Challenges

**Critical — Claim 3 context-join overclaim:** copilot-instructions.md is documented as always-loaded every turn for every agent. The subagent depth-2 limitation affects agent-catalog injection, not copilot-instructions.md presence. The "skill loads without copilot-instructions context" scenario is unsupported by repo evidence.

**Moderate — Claims 2, 7 attack unchosen design:** D3 in decisions.md already rejects per-project template variables. The actual approach is labeled placeholders as documentation convention, not a runtime resolution system. Spending argument weight on "no enforcer" is critiquing something the brief already declined to build.

**Moderate — Claims 4, 6 unsupported model-behavior assertions:** "Transformer attention" salience claim has no evidence. Template syntax is already used successfully in w-code-review, prompt variables, agent structure templates. Categorical prose > template is overclaimed given existing usage.

**Moderate — Claim 5 partial misdescription:** doc-audit → r-doc-standards dependency is confirmed and real. But agent-ecosystem.instructions.md does NOT list stubs pointing to files that would move — it points to share/README and h-agent-structure only. Second half of claim withdrawn.

**Blind spots identified:**
- No distinction between "correct but misplaced" (authority issue) vs "intrinsically invalid" (data corruption)
- Scope narrowed to placeholder mechanics — missed directory tables, namespace overviews, framing language as data-quality concerns
- Authority boundaries ("which layer owns this fact") absent from draft

Critic confidence in draft position: 0.57 (medium pressure)

### Refinements Applied

1. **Withdrew** context-join-failure claim entirely. copilot-instructions.md is reliably present.
2. **Reframed** from "schema with no enforcer" to "documentation convention with attentional risk" — acknowledging that template syntax works in practice, with a narrower failure mode.
3. **Dropped** unsupported transformer-attention claims. Grounded in practical observation: template syntax works but prose is clearer (per research-notes recommendation).
4. **Corrected** Claim 5: removed agent-ecosystem misdescription, retained confirmed doc-audit → r-doc-standards chain.
5. **Added** authority-migration framing as the core lens — "correct but misplaced" is the actual data problem, not "intrinsically wrong."
6. **Broadened** scope to cover directory tables, namespace overviews, and the completeness of the authority split as integrity concerns.
7. **Added** incomplete-migration as a high-priority risk (split-brain state from partial extraction).

### Post-Critic Position

Confidence raised to 0.80. The core framing shifted from "placeholder syntax is broken" to "this is a data-authority migration that must preserve referential integrity." Template notation is adequate but prose is preferred; the real risks are incomplete migration and cross-reference breakage, not notation failure.

## Exit

Position is solid after one Critic cycle. The challenges narrowed and corrected the stance without invalidating the core analysis. No further cycles needed.
