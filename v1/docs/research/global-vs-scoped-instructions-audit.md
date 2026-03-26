# Audit: Global vs Scoped Instruction File Ratio

> **Owning task:** #705 — Audit global vs scoped instruction file ratio
> **Date:** 2026-03-10 **Status:** Complete

## 1. Context and Question

Stripe's Minions use "almost exclusively" directory/pattern-scoped rules and avoid global
rules because they fill agent context windows before work begins (Source 1). Task #647
flagged this as worth auditing for OwlBear. The question: do any OwlBear `.instructions.md`
files use `applyTo: "**"` that could be scoped more narrowly?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Stripe Minions Part 2 — Rule files | <https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2> | .90 |
| 2 | VS Code — Custom instructions docs | <https://code.visualstudio.com/docs/copilot/customization/custom-instructions> | .95 |

## 3. Current Inventory

| File | `applyTo` | Lines | Est. tokens | Scope type |
|------|-----------|-------|-------------|------------|
| `copilot-instructions.md` | _(always-on)_ | 163 | ~3,760 | Global (inherent) |
| `agent-common.instructions.md` | `**` | 163 | ~3,450 | Global (explicit) |
| `python.instructions.md` | `**/*.py` | 27 | ~400 | Scoped |
| `frontend.instructions.md` | `src/**/ui/**,...` | 39 | ~550 | Scoped |
| `research-docs.instructions.md` | `docs/research/*.md` | 21 | ~300 | Scoped |

**Ratio:** 1 global `.instructions.md` out of 4 (25%). Including `copilot-instructions.md`
(always-on by design), ~7,210 tokens are loaded on every request regardless of context.

## 4. Analysis

### Can `agent-common.instructions.md` be narrowed?

The file covers: task discipline, kanban claiming, evidence standards, skill authority,
orchestrator degradation defense, communication protocol, terminal discipline, confidence
thresholds. These are **agent process rules**, not coding style — they apply regardless
of which files an agent touches.

The file itself documents a prior failure: it was previously scoped to `.github/agents/**`,
which caused it not to load when agents worked exclusively on `src/` or `tests/` files.
The `applyTo: "**"` was an intentional fix.

| Narrow-scoping option | Viable? | Reason |
|----------------------|---------|--------|
| Scope to `src/**,tests/**` | No | Misses docs, kanban, .github edits |
| Scope to `**/*.py,**/*.md` | No | Misses config files (.toml, .yml) |
| Scope to `.github/agents/**` | No | Already tried and failed (see loading note) |
| Split: process rules (global) + reference tables (skill) | **Maybe** | Could move ~40 lines of tables to a skill |
| Keep as-is | **Yes** | Content is legitimately global |

### Stripe's context is different from OwlBear's

Stripe operates at massive scale (1,300+ PRs/week, "enormous repositories") where global
rules would fill a significant percentage of context. OwlBear has 4 instruction files
totaling ~250 lines. The context pressure that motivates Stripe's approach does not exist
here (Sources 1, 2).

### Potential optimization: extract reference tables to a skill

Three sections of `agent-common.instructions.md` are reference material (rarely active
guidance): Self-defense table (~10 lines), Defense-in-depth table (~10 lines),
Confidence thresholds table (~8 lines), Per-agent signal table (~15 lines). Moving these
~43 lines (~600 tokens) to a skill loaded on-demand would trim the always-on payload by
~17%. However, this risks agents not seeing critical thresholds when they need them.

## 5. Recommendation (.85 confidence)

**No changes needed.** The current ratio is healthy:

- The one global `applyTo: "**"` file (`agent-common`) is justified — its content is
  cross-cutting process rules that every agent needs regardless of file context.
- 3/4 `.instructions.md` files are already properly scoped to file patterns.
- Total always-on context (~7,210 tokens) is well within acceptable limits for a
  project with 128K+ context windows.
- The table-extraction optimization saves ~600 tokens but risks missing critical
  guidance and adds complexity (KISS, YAGNI).

**Low-priority optional follow-up:** If `agent-common.instructions.md` grows past ~250
lines (~5,000 tokens), consider extracting the reference tables into a
`agent-communication-protocol` skill. Until then, leave as-is.

## 6. Follow-up Tasks

No immediate follow-up tasks needed — the audit found no actionable scoping changes.

Optional (deferred, not created):

- If `agent-common.instructions.md` grows past 250 lines: create a task to extract
  reference tables (communication protocol, confidence thresholds) into a dedicated skill.
