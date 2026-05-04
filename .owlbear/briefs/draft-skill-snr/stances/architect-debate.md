# Architect Debate Log — SNR Tool Pair Design

## Cycle 1

### Draft Position

1. **Deep-dive: Fixed section-batch.** Process files top-to-bottom presenting 3–8 logical sections. Each section: original/proposed/rationale. Scales via size thresholds (<100 = single pass, 300+ = 30–80 line sections).
2. **Broad audit: Ranked table.** Dimensions: absolute size, loaded context budget (file + required_reading), estimated noise ratio, consumer count (flat number).
3. **Coupling: Loose, shared vocabulary only.** No data pipeline. Shared 5-category taxonomy and "signal density" concept. User bridges manually.

### Critic Challenges (Cycle 1)

| # | Severity | Challenge | Verdict |
|---|----------|-----------|---------|
| 1 | Critical | "3–8 sections" is an imposed assumption — corpus is heterogeneous (agents use YAML+XML, skills use ##, prompts vary wildly) | **Accepted.** Revised to adaptive chunking per file type. |
| 2 | Critical | Sections are not semantically independent — agent behavioral intent is distributed across persona/boundaries/examples/output-format | **Accepted.** Revised: chunks are presentation units, not semantic independence claims. Deep-dive evaluates whole-file internally. |
| 3 | Critical | "File + required_reading = total" misses 4+ other load paths (applyTo, companion, body-ref, prompt-ref, directed, organic) | **Accepted.** Revised to "all load paths" metric per WIRING.md documentation. |
| 4 | Critical | Consumer count as single number collapses unlike dependency types (required_reading ≠ applyTo ≠ organic) | **Accepted.** Revised to typed connection profile. |
| 5 | Moderate | Scope baseline unstable (inventory counts differ between sources) | **Noted, not revised.** Minor counting discrepancies don't undermine the architecture. Tools work regardless. |
| 6 | Moderate | "Loose coupling" understated — shared taxonomy/concepts IS semantic coupling | **Accepted.** Revised to acknowledge intentional semantic coupling, mitigated by single-source definition. |
| 7 | Moderate | No durable handoff creates traceability gap between ranked priorities and deep-dive sessions | **Accepted.** Revised: ranking table is a durable snapshot artifact written to a file. |

### Blind Spots Surfaced

- Noise may be rooted in shared sources, not leaf files — partially addressed by universal-file leverage class
- Audit and deep-dive operate at different units (file vs. section) — addressed by clarifying they're complementary, not comparable
- "Reusable across all 80 files" not demonstrated for heterogeneous corpus — addressed by file-type-aware adaptive strategies

## Cycle 2

### Revised Position

1. **Adaptive chunking** by file type (4 strategies). Analysis scope = agent + linked skills. Presentation scope = file-local chunks.
2. **Category-grouped ranking** with typed edges, context budget from all load paths, freshness date.
3. **Inline taxonomy** (small enough to duplicate). Broad audit canonical. User-bridged routing. Taxonomy is context-dependent (patterns, not universal judgments).
4. **File-type awareness** as first-class concern in both tools.

### Critic Challenges (Cycle 2)

| # | Severity | Challenge | Verdict |
|---|----------|-----------|---------|
| 1 | Critical | Peer-scoring + single global ranking = contradiction. Category-grouped scoring can't produce a cross-corpus priority order without normalization. | **Accepted.** Clarified: per-category tables, not a global list. User decides cross-category priority. |
| 2 | Critical | Context budget is session-contingent (prompt-ref, organic edges are conditional) but treated as durable file property | **Accepted.** Reframed as "maximum potential context budget" — a heuristic, not accounting. Noted explicitly in stance. |
| 3 | Critical | Deep-dive analysis scope says "whole-file internally" but the brief says "One agent + linked skills" — file-local evaluation is insufficient for agent contracts | **Accepted.** Expanded: deep-dive loads agent + required_reading for safety evaluation. Compression proposals remain file-local. |
| 4 | Moderate | Taxonomy not category-specific — "prescriptive message templates" could be signal in workflow skills | **Partially accepted.** Categories name patterns; the deep-dive applies constraint calibration to judge whether an instance is noise in context. Taxonomy remains universal but application is context-aware. |
| 5 | Critical | Taxonomy "referenced by name" doesn't mean it's in active context — separate prompt entrypoints don't share state | **Accepted.** Revised to inline duplication (5 items is small enough). Broad audit remains canonical source for evolution. |
| 6 | Moderate | Wiring model may have drift (documented files not matching inventory) | **Noted.** Metric is best-effort from available data. 80% accuracy sufficient for prioritization heuristic. |

### Blind Spots Surfaced

- Universal files (applyTo: **) buried inside category-peer scoring — **Added as separate leverage class**
- No reconciliation mechanism when tools disagree — **Not revised.** Tools are advisory; user judges disagreements. No automated handoff means no formal reconciliation needed.
- No freshness boundary for ranking artifact — **Added freshness date + staleness note**

## Final Assessment

Position stabilized after two cycles. Critic confidence rose from 0.31 to 0.44 (still finding issues but diminishing severity). Key structural decisions are now internally consistent and grounded in the actual corpus characteristics rather than imposed assumptions.

Remaining open edges:
- Whether 4-strategy adaptive chunking is too complex for a .prompt.md file
- Whether "maximum potential" context budget is actionable enough given conditional load paths
- Whether inline taxonomy duplication will drift in practice despite "broad audit is canonical" rule
