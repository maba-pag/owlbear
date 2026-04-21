# Data Quality Stance

Brief: `draft-docs-currency-2026-04-19`
Panelist: **The Modeler** (ideation-data)
Critic cycles: 5 (see `stance-data-debate.md`)
Confidence: **0.88** — high confidence on index architecture; moderate uncertainty on diagram-metadata exception acceptability (user judgment required).

---

## Position Summary

The doc-index is the central data artifact in this system. It must be a **deterministic, content-sensitive function of the doc surface** — regenerable from scratch on every invocation, never cached, never hand-edited. Six data integrity constraints follow from the Brief's outcomes and the "index can never disagree with reality" property.

---

## 1. Doc-Index Integrity

**Stance: Allowlist over exclusion globs. Config-driven, not hardcoded.**

The doc surface is structurally stable (~76 files across well-known paths). An **allowlist** of glob patterns defines "what is a product doc":

- `share/agents/*.agent.md`
- `share/skills/*/SKILL.md`
- `share/instructions/*.instructions.md`
- `share/prompts/*.prompt.md`
- `serve/*/README.md`
- `setup/*.md`
- Root `*.md` (`README.md`, `README-consumer.md`, `SECURITY.md`)
- `.github/copilot-instructions.md`

**Excluded (not product docs):** `.owlbear/decisions/`, `.owlbear/sources/`, `.owlbear/briefs/`, `.owlbear/research/`, `.owlbear/kanban/`, `.owlbear/scratch/`, `tests/`, `seed/`, `store/`.

**Why allowlist, not exclusion list:** Exclusion lists fail open — new working directories auto-include as docs. Allowlist fails closed — new paths are excluded until explicitly added. The failure mode of "missing a real doc" is caught by `doc-audit`'s unrecognized-file check (below). The failure mode of "including non-docs" is uncatchable without manual review.

**Config placement:** `.owlbear/doc-index.config.yaml` — single source of truth for the glob patterns. Separates "what counts as a doc" from the generation script. Version-controlled, inspectable, diffable. Changes only when the project's doc structure changes (rare by design).

**Regeneration model:** The index is **content-sensitive** (extracts headings and outbound links from file contents, not just paths). It must regenerate by scanning file contents, not just directory listings. Cost: ~76 files, sub-second in Python. Cheap enough to regenerate on **every** `doc-writer` and `doc-audit` invocation. Never cached. Never trusted from a prior run.

**Tampering/staleness:** A non-concept. The index is a derived artifact. If it disagrees with a fresh regeneration, the fresh one wins. There is no "tampered" vs "stale" distinction — only "current" (just regenerated) and "not yet regenerated." Always regenerate before reading. The index file on disk is a convenience cache, not a source of truth.

**Format constraint: Machine-parseable. Not markdown.**

The index is consumed programmatically by `doc-writer` (lookup, filtering) and `doc-audit` (iteration, cross-reference queries). Markdown tables require fragile regex parsing — an implicit schema assumption that violates the principle of explicit contracts. **YAML** is recommended: human-readable, machine-parseable, supports nested structures (per-file TOC, link lists). JSON is acceptable. Markdown is not.

This is a data integrity constraint, not an implementation preference. The M2 text says "format is planner's call" — the planner should hear that the data panelist rejects markdown.

## 2. Diagram Source-of-Truth Coherence

**Stance: Per-diagram `describes` metadata is required. This is a controlled exception to "no hand-maintained fields."**

Diagrams are descriptive — code is authoritative. `doc-audit` must detect when a diagram has drifted from the code it describes. Without explicit linkage, drift detection is impossible: `doc-audit` can confirm "a `.excalidraw` file exists" but cannot determine if its content matches current system state.

**Mechanism:** Each diagram's index entry includes a `describes` field — a list of paths or concepts the diagram covers. Example:

```yaml
- path: share/skills/h-excalidraw-diagram/pipeline-overview.excalidraw
  describes:
    - share/agents/*.agent.md
    - share/skills/w-*/SKILL.md
    - "pipeline phase transitions"
```

When described paths have newer git timestamps than the diagram, `doc-audit` flags potential drift. This is mechanically checkable.

**The exception:** The `describes` field is hand-authored at diagram creation time by the agent (or human) creating the diagram. It cannot be auto-derived — no algorithm can determine what a diagram "is about" from its Excalidraw JSON. This violates the "no hand-maintained data fields" constraint.

**Why it's acceptable:** The constraint targets the index itself (auto-generated from filesystem). The `describes` field is **source metadata** — analogous to a filename, chosen once at creation. It's authored once, immutable thereafter, and validated by `doc-audit`. It is not a maintained field that drifts. If this exception is unacceptable, the fallback is: diagram drift detection is purely human/LLM judgment in `doc-audit` with no mechanical support — a weaker integrity guarantee.

**User decision required:** Is this controlled exception acceptable, or should diagram drift detection be entirely LLM-based in `doc-audit`?

## 3. Deletion Data Integrity

**Stance: Deletion is a multi-step transaction. Broken inbound links are data corruption.**

When `doc-writer` proposes deletion, the proposal must capture:

| Field | Source | Purpose |
|-------|--------|---------|
| File path | Filesystem | What's being deleted |
| Reasoning | Agent analysis | Why it's stale/orphaned |
| Inbound links | Index cross-reference data | Blast-radius — who references this file |
| Last modified | `git log` | Recency signal — recently-touched files are less likely orphaned |

**After user approval:** deletion and inbound-link repair happen in a **single logical commit**. Deleting a file without fixing its inbound links creates broken references — this is data corruption, not an acceptable intermediate state. The commit message cites the deletion reasoning.

**Approval granularity:** Per-proposal. Each proposal is one document + its full blast radius (list of files that will need link updates). If the blast radius is large, the user sees that and can reject, scope down, or split. No batch-delete-and-hope.

**Recovery:** Git history. The file existed in a prior commit; `git show` recovers it. No special recovery mechanism needed. The deletion commit message provides the reasoning trail.

## 4. Cross-Reference Integrity

**Stance: The index must capture outbound internal links per file. This is auto-generated, not hand-maintained.**

Outbound links are mechanically extractable from markdown. The extraction specification:

1. Parse markdown, **skipping fenced code blocks** (``` delimited regions) — links in code blocks are examples, not live references.
2. Extract all markdown links: `[text](target)`.
3. Filter to **workspace-relative paths only**: exclude `http://`, `https://`, `#anchor-only`, image extensions (`.png`, `.svg`, `.jpg`, `.gif`, `.webp`).
4. Normalize paths (resolve `../`, strip leading `/`).

The result: per-file, a list of internal doc cross-references. **Inbound links are computed by reversing the outbound graph** — no separate extraction needed.

This directly supports:
- **Deletion blast-radius:** "Which files link to `bar.agent.md`?" → query the outbound graph in reverse.
- **Orphan detection:** "Which files have zero inbound links and aren't root-level entry points?" → candidate orphans.
- **Integrity auditing:** "Are all outbound link targets valid files?" → detect broken references before they reach users.

## 5. Inventory Drift Detection

**Stance: The index detects structural drift (files/links/headings). Semantic drift detection lives in `doc-audit`, not the index.**

The index answers: "Does this file exist? What are its headings? What does it link to?" It cannot answer: "Does this file's content accurately describe the current system behavior?"

**Semantic drift detection** — the hard problem — belongs in `doc-audit` dimension D4 (Quality). The mechanism is necessarily **LLM-based**: read a doc file, identify claims about system behavior (imports, paths, API signatures, CLI commands, architectural assertions), and spot-check them against the actual codebase.

The index supports this workflow: `doc-audit` iterates the index (not the filesystem) to ensure audit coverage matches the doc surface exactly. The index is the coverage map; `doc-audit` is the drift detector.

**No mechanical shortcut exists.** Signature matching or keyword diffing will miss semantic drift ("the doc says X uses polling but the code was refactored to use webhooks"). LLM-based reading is the appropriate tool for this class of problem. `doc-audit` should sample strategically — high-churn files first, using git history to prioritize.

## 6. Verification Log Integrity

**Stance: The verification log must contain reproducible evidence, not self-certification.**

A log where `doc-writer` v2 writes "pass" for its own test cases is worthless — self-certifying. The log must contain enough information for independent reproduction:

| Field | Content |
|-------|---------|
| Task ID | The kanban task used as input |
| Behavioral mode | Which of the ~6 modes is being tested (no-op, prose update, diagram maintenance, diagram creation, deletion proposal, ambiguous) |
| Input conditions | What state the repo/task was in before the run |
| Observable output | Commit SHA, Channel A message text, or explicit no-op with reasoning |
| Expected outcome | What the test case was designed to prove |

**Location:** `.owlbear/` (this is operational evidence, not a product doc). Specific placement deferred to planner — `.owlbear/decisions/` or `.owlbear/research/` are both reasonable.

**Lifespan: Permanent.** This is a one-time artifact proving the v2 redesign was verified. It answers "did anyone test doc-writer v2?" for all future time. Ephemeral verification defeats its purpose. The log is small (6 entries); storage cost is negligible.

**Format:** Machine-parseable (YAML or JSON) for the same reasons as the index — if anyone needs to query or extend the verification log, markdown tables fail.

---

## Key Trade-offs

| Decision | Trade-off | Recommendation |
|----------|-----------|----------------|
| Allowlist vs exclusion list | Allowlist fails closed (misses new docs) vs exclusion fails open (includes non-docs) | Allowlist + doc-audit unrecognized-file check (fail closed loudly) |
| Diagram `describes` field | Violates "no hand-maintained fields" vs no mechanical drift detection | Accept as controlled exception; user call |
| Index format | Markdown (human-friendly) vs YAML/JSON (machine-parseable) | YAML — programmatic consumers require it |
| Outbound link storage | Larger index vs no cross-reference capability | Store outbound links — the cost is trivial, the capability is load-bearing |
| Verification log lifespan | Permanent (storage) vs ephemeral (loses evidence) | Permanent — 6 entries, negligible cost |

## Warnings

1. **The diagram `describes` exception is the weakest point.** If the team rejects hand-authored metadata, diagram drift detection falls back to pure LLM judgment — significantly weaker. This is a genuine trade-off, not a hedged "it depends."

2. **Markdown format for the index would be a data integrity failure.** Programmatic consumers parsing markdown tables is exactly the implicit-schema-assumption pattern that causes silent data corruption downstream. YAML or JSON. Full stop.

3. **Semantic drift detection has no mechanical guarantee.** LLM-based spot-checking in `doc-audit` is the best available mechanism, but it's probabilistic, not exhaustive. The system can miss semantic drift between audit runs. The periodic `doc-audit` cadence is the mitigation, not a fix.

4. **Deletion without inbound-link repair is data corruption.** The system must treat deletion as a transaction (delete + fix links), not two independent operations. If the deletion pipeline allows "delete now, fix links later," broken references will accumulate.

5. **The index config file (`.owlbear/doc-index.config.yaml`) is itself a maintained artifact.** It changes rarely, but when the doc surface structure changes, someone must update it. `doc-audit`'s unrecognized-file check is the safety net for forgetting.
