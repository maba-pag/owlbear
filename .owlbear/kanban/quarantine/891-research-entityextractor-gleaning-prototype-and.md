---
id: 891
title: 'Research: EntityExtractor gleaning prototype and recall benchmark'
status: archived
priority: someday
created: 2026-03-21T13:05:37.8389698+01:00
updated: 2026-03-21T23:41:56.4029461+01:00
tags:
    - research
    - scope:core
    - knowledge
    - phase-research
blocked: true
block_reason: 'Split into #906, #907, #908 - work tracked there'
class: standard
---

**Source:** #734 edgequake-gleaning evaluation, docs/research/edgequake-gleaning.md S6

EntityExtractor.extract() is currently single-pass. EdgeQuake's gleaning pattern (iterative multi-pass: extract then re-prompt for missed entities) delivers +18-25% entity recall on generic document benchmarks. The gleaning mechanism is compatible with ExtractionResult schema, partial-failure semantics, and UsageTracker. The open question is whether the recall improvement justifies 2x LLM cost on OwlBear's code-oriented corpus.

**AC:**

1. Build a benchmark harness (tests/benchmarks/) that ingests a representative set of OwlBear source files and measures entity recall against a ground-truth entity list.
2. Establish a single-pass recall baseline using the current EntityExtractor.
3. Implement gleaning in a feature-flagged branch: Pass 1 = current flow, Pass 2 = re-prompt with found entities asking what was missed, Merge = dedup by entity.name with higher-importance winning.
4. Measure recall delta (target threshold: > 10% improvement before integration).
5. Measure cost delta (token counts, estimated Copilot API cost).
6. If delta > 10%: create implementation follow-up with integration plan. If delta <= 10%: close with findings and explanation.

[[2026-03-21]] Sat 15:16

## Research

Research doc: docs/research/entity-extractor-gleaning-benchmark.md

Key findings:

- Prior art treats gleaning as an optional tuning knob, not a default behavior.
- OwlBear's current extractor does not preserve pass-1 output on a later failure and records usage once per extract call, so a prototype must add both behaviors explicitly.
- The existing tests/benchmarks helpers are retrieval-oriented; this experiment needs a custom entity-recall harness keyed by (name, entity_type).

Follow-up tasks created:

- #906 Build EntityExtractor code-corpus recall benchmark harness
- #907 Prototype feature-flagged EntityExtractor gleaning
- #908 Evaluate EntityExtractor gleaning recall and cost delta

Attribution updated:

- docs/sources/overview.md

[[2026-03-21]] Sat 18:28

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Build a benchmark harness (tests/benchmarks/) that ingests a representative set of OwlBear source files and measures entity recall against a ground-truth entity list. | This is a benchmark-harness domain, not a top-level umbrella responsibility. `tests/benchmarks/bench_graph_expansion.py` is the local benchmark precedent, while `tests/benchmarks/harness.py` and `tests/benchmarks/evaluate.py` remain retrieval-specific ranx seams. | Keep this on child tracker `#906`, which is already decomposed into the TDD pairs `#911 -> #912` and `#913 -> #914`. |
| 2. Establish a single-pass recall baseline using the current EntityExtractor. | Baseline measurement is executable benchmark-runner work, not parent-card scope. It depends on the curated corpus and scorer from `#906` and should run through a reusable opt-in runner in `tests/benchmarks/`. | Keep this on evaluation tracker `#908`, specifically the runner slice `#915` after the harness path is complete. |
| 3. Implement gleaning in a feature-flagged branch: Pass 1 = current flow, Pass 2 = re-prompt with found entities asking what was missed, Merge = dedup by entity.name with higher-importance winning. | This bundles three extractor responsibilities: pass orchestration, pass-2 fallback, and merge or edge-repair behavior. `src/owlbear/memory/knowledge/extractor.py` currently has one `extract()` seam, and `src/owlbear/memory/knowledge/models.py` uses UUID-backed entity ids, so prototype work must stay separated from benchmark and docs concerns. | Keep this on child tracker `#907`, whose current implementation slices are `#917`, `#918`, and `#919`. |
| 4. Measure recall delta (target threshold: > 10% improvement before integration). | Measuring delta is evaluation work layered on top of the completed harness and prototype, then a publication or decision step. It is not builder-ready while the runnable benchmark and the docs recommendation are still coupled. | Keep executable measurement on `#915` and the publish or go-no-go decision on `#916` under parent tracker `#908`. |
| 5. Measure cost delta (token counts, estimated Copilot API cost). | Cost measurement depends on per-pass usage visibility rather than just benchmark scoring. `src/owlbear/memory/usage.py` already provides the usage-recording seam, so this remains downstream evaluation work after `#919` instruments the prototype. | Keep instrumentation on `#919`, then consume it in `#915` and publish it in `#916`; do not route this through the parent. |
| 6. If delta > 10%: create implementation follow-up with integration plan. If delta <= 10%: close with findings and explanation. | This is a docs or decision responsibility in `docs/research/`, not the same domain as benchmark code or extractor prototype work. It is verifiable only after the runner has produced benchmark evidence. | Keep this on docs task `#916`; the parent should remain a tracker above the already-split execution path. |

### Architecture Notes

- `tests/benchmarks/bench_graph_expansion.py` is the local pattern for checked-in benchmark data, formatted reporting, and opt-in benchmark execution.
- `tests/benchmarks/harness.py` and `tests/benchmarks/evaluate.py` are retrieval-oriented ranx helpers and are the wrong abstraction for entity-recall scoring.
- `src/owlbear/memory/knowledge/extractor.py` still exposes a single async `extract()` seam that returns an empty `ExtractionResult` on failure, which is why the gleaning prototype must stay isolated from harness and publication work.
- `src/owlbear/memory/knowledge/models.py` gives `Entity.id` a UUID default, so any recall benchmark contract must key gold annotations on stable textual identity rather than ids.
- `tests/test_knowledge_extractor.py` blocks real model requests in normal tests, and `pyproject.toml` already defines the opt-in `benchmark` marker. That is the repo-standard boundary for this benchmark family.
- The board already reflects the correct decomposition: `#906`, `#907`, and `#908` are the three direct child trackers for harness, prototype, and evaluation. Those children are themselves still being tightened into executable TDD slices (`#911`-`#914`, `#917`-`#919`, `#915`, `#916`).
- Conclusion: `#891` is an umbrella tracker, not a task that should advance directly to `todo`.

### Changes Made

- Claimed task `#891` as `architect-891`.
- Reviewed `docs/research/entity-extractor-gleaning-benchmark.md`, `src/owlbear/memory/knowledge/extractor.py`, `src/owlbear/memory/knowledge/models.py`, `tests/test_knowledge_extractor.py`, `tests/benchmarks/bench_graph_expansion.py`, `tests/benchmarks/harness.py`, `tests/benchmarks/evaluate.py`, and `pyproject.toml`.
- Re-checked the existing follow-up tasks `#906`, `#907`, `#908`, `#915`, `#916`, `#917`, `#918`, and `#919` before recording this split review.
- Appended this architecture review and kept the parent in `backlog`.

### Dependencies

- Verified direct child trackers exist: `#906` (harness), `#907` (prototype), `#908` (evaluation).
- Verified the harness branch already has explicit TDD pairs: `#911 -> #912` and `#913 -> #914`.
- Verified the prototype and evaluation branches are not builder-ready at the parent level: `#917`, `#918`, `#919`, `#915`, and `#916` remain downstream ideation slices that need their own architecture gating and TDD handling.
- Added/Removed/Verified: no new tasks were created in this review because the split path already exists on the board.

[[2026-03-21]] Sat 23:41

## Architecture Review

**Verdict:** SPLIT -> #906, #907, #908

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Build a benchmark harness (tests/benchmarks/) that ingests a representative set of OwlBear source files and measures entity recall against a ground-truth entity list. | This is executable harness work under tests/benchmarks, not a parent tracker responsibility. The local benchmark precedent remains tests/benchmarks/bench_graph_expansion.py. | Keep on #906. |
| 2. Establish a single-pass recall baseline using the current EntityExtractor. | This is benchmark-runner execution layered on the harness, not parent-card scope. | Keep on #908, specifically the runner path under #915. |
| 3. Implement gleaning in a feature-flagged branch: Pass 1 = current flow, Pass 2 = re-prompt with found entities asking what was missed, Merge = dedup by entity.name with higher-importance winning. | This is extractor prototype work in src/owlbear/memory/knowledge/extractor.py and mixes pass orchestration, fallback, merge, and usage concerns. | Keep on #907. |
| 4. Measure recall delta (target threshold: > 10% improvement before integration). | This is downstream evaluation work after the harness and prototype land. | Keep on #908 and its runner child #915. |
| 5. Measure cost delta (token counts, estimated Copilot API cost). | Existing usage tracking already lives in src/owlbear/memory/usage.py via record_agent_usage(); this remains downstream evaluation work rather than parent scope. | Keep on #908 with instrumentation supplied by #907/#919. |
| 6. If delta > 10%: create implementation follow-up with integration plan. If delta <= 10%: close with findings and explanation. | This is publication and decision work in docs/research, separate from benchmark code and extractor changes. | Keep on #908 and its publish/results child #916. |

### Architecture Notes

- tests/benchmarks/bench_graph_expansion.py remains the local opt-in benchmark precedent; tests/benchmarks/harness.py and tests/benchmarks/evaluate.py are retrieval-oriented ranx seams, not entity-recall scoring helpers.
- src/owlbear/memory/knowledge/extractor.py still exposes one async extract() path that returns ExtractionResult() on failure, so the gleaning experiment is a separate prototype seam rather than parent-level work.
- src/owlbear/memory/knowledge/models.py still gives Entity.id UUID defaults, so gold annotations and dedup rules must use stable textual identity instead of ids.
- src/owlbear/memory/usage.py plus record_agent_usage() is the existing token/cost seam for downstream comparison work.
- src/owlbear/bootstrap/knowledge.py still wires EntityExtractor(model=chat_model) in one production path, reinforcing that prototype and benchmark work stay isolated from the parent tracker.
- The board already has the correct top-level split: #906 (harness), #907 (prototype), and #908 (evaluation/publish), with further decomposition under those trackers.
- Because the executable contract now lives on the child tasks, #891 should stay blocked as a traceability parent rather than re-enter backlog -> todo flow.

### Changes Made

- Claimed task #891 as architect-891.
- Re-reviewed docs/research/entity-extractor-gleaning-benchmark.md, tests/benchmarks/bench_graph_expansion.py, tests/benchmarks/harness.py, tests/benchmarks/evaluate.py, src/owlbear/memory/knowledge/extractor.py, src/owlbear/memory/knowledge/models.py, src/owlbear/memory/usage.py, src/owlbear/bootstrap/knowledge.py, tests/test_knowledge_extractor.py, and child tasks #906, #907, #908, #911-#919.
- Appended this architecture review and blocked direct execution on #891; no new tasks were created because the split already exists.

### Dependencies

- Verified direct child trackers exist: #906 (harness), #907 (prototype), #908 (evaluation/publish).
- Verified #906 already owns explicit TDD pairs #911 -> #912 and #913 -> #914.
- Verified #891 itself must not route a builder directly; downstream tracker work remains on the child tasks.
