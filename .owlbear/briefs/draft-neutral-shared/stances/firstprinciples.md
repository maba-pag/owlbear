# First-Principles Stance

## Irreducible Claims

1. Useful LLM instructions are useful BECAUSE they're opinionated. Strip opinions = ship token cost with zero behavioral steering.
2. One file serving two audiences with no dispatch mechanism is a structural problem. Text edits can't resolve the contradiction.
3. The model already knows "use pytest" and "use uv" — the only value is in opinions the model doesn't have OR project-specific facts.

## Challenged Assumptions

| Assumption | Challenge |
|------------|-----------|
| "Files are in the right place but have wrong content" | Some files may not carry ANY universal opinion the model doesn't already have. They're OwlBear-dev-local artifacts wearing a shared costume. |
| "Generic default" is a coherent concept | For LLM instructions, you either steer behavior (specific) or you don't (generic = useless). There's no useful middle ground for many of these files. |
| "Content refactoring is sufficient" | The contradiction between "specific enough to help" and "generic enough to port" may be structural, not textual. |
| The shared/local axis is the right decomposition | The real axis is **opinion stability**: universal opinions (all projects, model doesn't know) vs. project-volatile opinions. |

## Core Tension

The tension isn't shared-vs-local. It's: **which opinions in these files add value that the model wouldn't produce on its own?**

- Universal + model-doesn't-know → belongs in shared (rare)
- Universal + model-already-knows → noise, could remove entirely
- Project-specific → belongs in consumer's local config
- OwlBear-workflow-specific → belongs in OwlBear-dev local

## Strongest Insight

Don't scrub N files to remove "OwlBear" strings. Instead, triage: which files carry universal opinion the model doesn't already have? The rest are either noise or OwlBear-dev-local. The "shared" set may be much smaller than the current `share/` file count.

**Confidence: 0.75** — high confidence in the framing challenge; less certain about how small the universal set actually is without empirical audit.
