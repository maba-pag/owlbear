---
id: 906
title: Build EntityExtractor code-corpus recall benchmark harness
status: archived
priority: nice-to-have
created: 2026-03-21T15:13:40.795193+01:00
updated: 2026-03-23T23:06:27.9433484+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - test
    - type:test
    - phase-research
parent: 891
blocked: true
block_reason: 'Umbrella tracker: waiting for child tasks #911, #912, #913, #914 to complete. Do not dispatch to architect again.'
class: standard
---

**Source:** #891 and docs/research/entity-extractor-gleaning-benchmark.md §5

Build a reusable extraction benchmark in tests/benchmarks/ for a curated OwlBear corpus instead of reusing the existing ranx retrieval helpers.

**AC:**

1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs.
2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids.
3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor.
4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked.
5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md.

[[2026-03-21]] Sat 15:53

## Research

Doc: docs/research/entity-extractor-code-corpus-recall-harness.md

Summary: Existing benchmark helpers in tests/benchmarks/harness.py and tests/benchmarks/evaluate.py are retrieval-oriented (`ranx`, `Qrels`, `Run`, `ndcg@10`) and are the wrong seam for #906. The best local precedent is tests/benchmarks/bench_graph_expansion.py: checked-in data, custom scorer, optional `@pytest.mark.benchmark`, and formatted output. Recommendation (.89): keep #906 as the parent tracker and execute it via two RED/GREEN pairs — corpus/schema (#911 -> #912) and harness/reporting (#913 -> #914).

Key findings:

- Use a checked-in OwlBear sample corpus spanning Python and Markdown instead of a live repo crawl.
- Key gold annotations by (normalized_name, entity_type), not Entity.id.
- Implement a small custom scorer for micro recall and per-type recall; do not reuse ranx helpers or add sklearn/spaCy as runtime dependencies.
- Keep normal tests model-free with stub extractor outputs; any live run should stay opt-in under the existing benchmark marker.

Follow-up created:

- #911 Test EntityExtractor benchmark corpus and gold schema (RED)
- #912 Build EntityExtractor benchmark corpus and gold schema
- #913 Test EntityExtractor recall harness and reporting (RED)
- #914 Build EntityExtractor recall harness and reporting

Commands executed:

- kanban\kanban-md.exe create "Test EntityExtractor benchmark corpus and gold schema (RED)" --priority nice-to-have --status ideation --parent 906 -> #911
- kanban\kanban-md.exe create "Build EntityExtractor benchmark corpus and gold schema" --priority nice-to-have --status ideation --parent 906 --depends-on 911 -> #912
- kanban\kanban-md.exe create "Test EntityExtractor recall harness and reporting (RED)" --priority nice-to-have --status ideation --parent 906 --depends-on 912 -> #913
- kanban\kanban-md.exe create "Build EntityExtractor recall harness and reporting" --priority nice-to-have --status ideation --parent 906 --depends-on 912,913 -> #914

Attribution updated: docs/sources/overview.md

[[2026-03-21]] Sat 16:33

## Architecture Review

Verdict: Split

AC Assessment

- AC1 and AC2 belong to the corpus and gold-schema slice and should execute through #911 and #912.
- AC3 through AC5 belong to the harness and reporting slice and should execute through #913 and #914.

Architecture Notes

- tests/benchmarks/bench_graph_expansion.py is the local benchmark precedent for checked-in data, custom scoring, and opt-in benchmark execution.
- tests/benchmarks/harness.py and tests/benchmarks/evaluate.py are ranx retrieval helpers and should not be reused for entity recall.
- src/owlbear/memory/knowledge/extractor.py exposes the async EntityExtractor.extract seam; normal tests should stub that boundary instead of making model calls.
- src/owlbear/memory/knowledge/models.py generates Entity.id as a UUID, so the gold contract must stay on stable textual keys.
- pyproject.toml already registers the benchmark marker and benchmark extra, so the scorer should stay local and dependency-free.
- Keep #906 as the parent tracker and do not advance it directly to a builder.

Changes Made

- Claimed #906 as architect-906.
- Recorded split guidance on the parent tracker without advancing status.

Dependencies

- Verified TDD pair one: #911 before #912.
- Verified TDD pair two: #913 before #914.
- Verified #914 depends on both #912 and #913.

[[2026-03-21]] Sat 17:28

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs. | Corpus-fixture responsibility. `tests/benchmarks/bench_graph_expansion.py` shows the local pattern is checked-in benchmark data, not a generic helper abstraction. | Execute through the corpus RED/GREEN pair `#911 -> #912`; keep this parent as a tracker. |
| 2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids. | Data-schema requirement. `src/owlbear/memory/knowledge/models.py` generates UUID-backed `Entity.id`, so stable textual keys must live in the corpus slice. | Execute through `#911 -> #912`; do not couple this schema work to scorer implementation. |
| 3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor. | Harness/reporting responsibility. `tests/benchmarks/harness.py` and `tests/benchmarks/evaluate.py` are retrieval-oriented ranx seams, not entity-recall seams. | Execute through `#913 -> #914` with a local custom scorer rather than reusing ranx helpers. |
| 4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked. | Verifiable test boundary. `src/owlbear/memory/knowledge/extractor.py` exposes the async `extract()` seam, and `tests/test_knowledge_extractor.py` already demonstrates the repo-standard stubbed model pattern with live requests blocked. | Keep this in `#913 -> #914`; normal tests stub extractor outputs, and any live run stays opt-in under the existing benchmark marker. |
| 5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md. | Reporting/publication concern attached to the harness slice, not the corpus slice. The parent source of truth is still the gleaning benchmark plan, even though the newer code-corpus research doc should remain supporting context. | Keep this in `#913 -> #914` and require the reporting output to preserve a backlink to `docs/research/entity-extractor-gleaning-benchmark.md`; the corpus-specific research doc can be a secondary reference. |

### Architecture Notes

- `tests/benchmarks/bench_graph_expansion.py` is the local benchmark precedent for checked-in data, formatted output, and opt-in benchmark execution.
- `tests/benchmarks/harness.py` and `tests/benchmarks/evaluate.py` are ranx retrieval utilities (`Qrels`, `Run`, `ndcg@10`) and should not be stretched into entity recall.
- `src/owlbear/memory/knowledge/extractor.py` provides the async `EntityExtractor.extract()` seam; benchmark tests should stub that boundary instead of making model calls.
- `tests/test_knowledge_extractor.py` explicitly blocks real model requests, which is the repo-standard contract for normal extractor tests.
- `src/owlbear/memory/knowledge/models.py` uses UUID defaults for `Entity.id`, so benchmark gold must remain keyed by stable textual identity.
- `pyproject.toml` already registers the opt-in `benchmark` marker. This task should stay dependency-light and not add sklearn or spaCy.
- `#906` is an umbrella tracker, not a builder-ready implementation card. The execution path is the existing split `#911 -> #912 -> #913 -> #914`, so the parent should remain in `backlog`.

### Changes Made

- Claimed task `#906` as `architect-906`.
- Reviewed `tests/benchmarks/bench_graph_expansion.py`, `tests/benchmarks/harness.py`, `tests/benchmarks/evaluate.py`, `src/owlbear/memory/knowledge/extractor.py`, `src/owlbear/memory/knowledge/models.py`, `tests/test_knowledge_extractor.py`, and `pyproject.toml`.
- Appended this architecture review and kept the task in `backlog`.

### Dependencies

- Verified existing split tasks: `#911` (`backlog`), `#912` (`ideation`), `#913` (`ideation`), `#914` (`ideation`).
- Verified TDD pairing inside the split: `#911` before `#912`, and `#913` before `#914`.
- Verified downstream tightening still needed when `#913` and `#914` are reviewed: preserve a backlink to `docs/research/entity-extractor-gleaning-benchmark.md` in the runnable output or instructions.
- Added/Removed/Verified: no new package dependencies are needed; reuse the existing benchmark marker and extractor seam.

[[2026-03-21]] Sat 18:14

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs. | Corpus-fixture responsibility. The contract now lives in tests/benchmarks/test_entity_extractor_corpus.py, so the parent should stay decomposed instead of routing corpus work through one mixed builder card. | Keep this on split tasks #911 and #912. |
| 2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids. | Stable-key schema responsibility. src/owlbear/memory/knowledge/models.py gives Entity.id random UUIDs, so benchmark gold must stay on textual keys. | Keep this on #911 and #912. |
| 3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor. | Harness/reporting responsibility. tests/benchmarks/harness.py and tests/benchmarks/evaluate.py are retrieval-oriented ranx utilities, not entity-recall seams. | Keep this on #913 and #914 with a local scorer. |
| 4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked. | Verifiable test boundary. src/owlbear/memory/knowledge/extractor.py exposes a single async extract seam, and tests/test_knowledge_extractor.py blocks live model requests in normal tests. | Keep this on #913 and #914; stub extractor outputs in normal tests and leave live runs benchmark-marked. |
| 5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md. | Cross-doc traceability requirement. The parent source doc is still the gleaning benchmark plan, while the child harness cards currently point at the newer code-corpus harness research doc. | Preserve the split and tighten #913 and #914 at their own architecture review so the runnable output or instructions link back to the source doc. |

### Architecture Notes

- tests/benchmarks/bench_graph_expansion.py remains the local precedent for checked-in benchmark data, formatted output, and opt-in benchmark execution.
- tests/benchmarks/test_entity_extractor_corpus.py confirms the corpus and schema contract already lives in its own RED task and should not be merged back into the parent.
- tests/benchmarks/harness.py and tests/benchmarks/evaluate.py are retrieval helpers around ranx metrics and would be the wrong abstraction for entity recall.
- src/owlbear/memory/knowledge/models.py uses UUID-backed Entity.id, so gold annotations must remain keyed by stable textual identity.
- src/owlbear/memory/knowledge/extractor.py returns empty results on failure and exposes a single async extract seam; normal tests should stub that seam instead of making live model calls.
- pyproject.toml already registers the benchmark marker, so recall scoring should stay dependency-light.
- #906 is still an umbrella tracker. The executable path is the existing split #911, #912, #913, and #914.

### Changes Made

- Re-checked the current board state and codebase seams for the split path.
- Confirmed #911 is already active work, which reinforces that the parent should remain a tracker.
- Appended this architecture review and kept the parent in backlog.
- No new kanban tasks created.

### Dependencies

- Verified child task state: #911 is in-progress.
- Verified downstream task order: #912 depends on #911, and #914 depends on #912 plus #913.
- Verified no additional package dependency is required beyond the existing benchmark extra and marker.

[[2026-03-21]] Sat 23:18

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs. | Corpus-fixture responsibility. tests/benchmarks/test_entity_extractor_corpus.py now carries the RED contract for checked-in ordered samples, so this should not be routed through a mixed parent builder card. | Keep this on #911 and #912. |
| 2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids. | Stable-key schema responsibility. src/owlbear/memory/knowledge/models.py still gives Entity.id UUID-backed defaults, so gold identity must remain a separate corpus concern. | Keep this on #911 and #912. |
| 3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor. | Harness/reporting responsibility. tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain ranx retrieval seams and are the wrong abstraction for entity recall. | Keep this on #913 and #914 with a local scorer. |
| 4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked. | Verifiable execution-boundary requirement. src/owlbear/memory/knowledge/extractor.py exposes a single async extract seam, and tests/test_knowledge_extractor.py keeps normal tests model-free. | Keep this on #913 and #914; normal tests stub extractor outputs and any live run stays benchmark-marked. |
| 5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md. | Traceability requirement attached to the runnable harness/reporting slice, not the corpus slice. The child harness cards currently cite the newer corpus-harness doc, so this backlink still needs to be preserved when those cards are reviewed. | Keep this on #913 and #914; do not collapse the parent back into one task. |

### Architecture Notes

- tests/benchmarks/bench_graph_expansion.py remains the local benchmark precedent for checked-in data, custom scoring, and opt-in benchmark execution.
- tests/benchmarks/test_entity_extractor_corpus.py confirms the corpus and gold-schema contract already lives in its own RED task, reinforcing the split instead of weakening it.
- tests/benchmarks/harness.py and tests/benchmarks/evaluate.py are retrieval helpers around ranx metrics and should not be stretched into entity recall.
- src/owlbear/memory/knowledge/models.py uses UUID-backed Entity.id values, so benchmark gold must remain keyed by stable textual identity.
- src/owlbear/memory/knowledge/extractor.py returns an empty result on failure and exposes one async extract seam; normal tests should stub that seam rather than make live model calls.
- #906 remains an umbrella tracker. The executable path is the existing split #911 -> #912 -> #913 -> #914.

### Changes Made

- Claimed task #906 as architect-906.
- Re-checked the current code seams, research docs, child task contracts, and active RED coverage.
- Appended this architecture review and kept the parent in backlog.
- No new tasks created.

### Dependencies

- Verified child task state: #911 is in-progress; #912, #913, and #914 remain downstream work.
- Verified dependency order: #912 depends on #911, #913 depends on #912, and #914 depends on #912 plus #913.
- Verified no new package dependency is required beyond the existing benchmark marker flow.

[[2026-03-21]] Sat 23:58

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs. | Corpus-fixture responsibility. tests/benchmarks/test_entity_extractor_corpus.py now exists as the RED contract for checked-in ordered samples, so the parent should remain decomposed instead of becoming a mixed builder card. | Keep this on #911 and #912. |
| 2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids. | Stable-key schema responsibility. src/owlbear/memory/knowledge/models.py still gives Entity.id UUID-backed defaults, so gold identity remains a separate corpus concern. | Keep this on #911 and #912. |
| 3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor. | Harness/reporting responsibility. tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain ranx retrieval seams and are still the wrong abstraction for entity recall. | Keep this on #913 and #914 with a local scorer. |
| 4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked. | Verifiable execution-boundary requirement. src/owlbear/memory/knowledge/extractor.py exposes a single async extract seam, and tests/test_knowledge_extractor.py keeps normal tests model-free. | Keep this on #913 and #914; normal tests stub extractor outputs and any live run stays benchmark-marked. |
| 5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md. | Traceability requirement attached to the runnable harness/reporting slice, not the corpus slice. The child harness cards still point at the newer code-corpus harness doc, so the parent should stay split and preserve this backlink requirement when #913 and #914 are reviewed. | Keep this on #913 and #914; do not collapse the parent back into one task. |

### Architecture Notes

- Current repo state strengthens the split instead of weakening it: tests/benchmarks/test_entity_extractor_corpus.py already exists, and #911 is in-progress against that RED seam.
- Approving #906 as a single implementation task would violate single-responsibility and TDD pairing by bundling corpus fixtures plus harness/reporting into one builder card.
- tests/benchmarks/bench_graph_expansion.py remains the local benchmark precedent for checked-in data and opt-in benchmark execution, while tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain retrieval-specific helpers.
- src/owlbear/memory/knowledge/models.py uses UUID-backed Entity.id values, so stable textual keys must remain in the corpus/schema slice.
- src/owlbear/memory/knowledge/extractor.py returns empty results on failure and exposes one async extract seam; normal tests should continue to stub that seam rather than make live model calls.
- #906 is still an umbrella tracker. The executable path remains #911 -> #912 -> #913 -> #914.

### Changes Made

- Claimed task #906 as architect-906.
- Re-read the parent card, child tasks #911 through #914, docs/research/entity-extractor-code-corpus-recall-harness.md, and the current benchmark and extractor seams.
- Appended this architecture review and kept the parent in backlog.
- No new tasks created.

### Dependencies

- Verified child task state: #911 is in-progress; #912, #913, and #914 remain downstream work.
- Verified dependency order: #912 depends on #911, #913 depends on #912, and #914 depends on #912 plus #913.
- Verified the active RED artifact tests/benchmarks/test_entity_extractor_corpus.py aligns with the split path.
- Verified #913 and #914 still need their own architecture review to preserve the backlink to docs/research/entity-extractor-gleaning-benchmark.md in runnable instructions or output.

[[2026-03-22]] Sun 04:28

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs. | Corpus-fixture responsibility. The active RED seam already exists in tests/benchmarks/test_entity_extractor_corpus.py and task #911. | Keep on #911 -> #912. |
| 2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids. | Stable-key schema concern. src/owlbear/memory/knowledge/models.py gives Entity.id UUID defaults, so textual keys must stay in the corpus slice. | Keep on #911 -> #912. |
| 3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor. | Harness/reporting concern. tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain ranx retrieval helpers, not entity-recall seams. | Keep on #913 -> #914 with a local scorer. |
| 4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked. | Execution-boundary requirement. src/owlbear/memory/knowledge/extractor.py exposes one async extract seam, and tests/test_knowledge_extractor.py keeps normal tests model-free. | Keep on #913 -> #914; normal tests stub extractor outputs and live runs stay benchmark-marked. |
| 5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md. | Traceability requirement attached to the runnable harness/reporting slice. The current child cards cite the newer code-corpus harness doc, so the source-doc backlink must be preserved downstream. | Keep on #913 -> #914 and tighten during those child reviews. |

### Architecture Notes

- Current repo state still supports the split rather than weakening it: tests/benchmarks/bench_graph_expansion.py is the local checked-in benchmark pattern, while tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain retrieval-specific ranx helpers.
- Child task order is executable and TDD-correct: #911 is in-progress, #912 depends on #911, #913 depends on #912, and #914 depends on #912 plus #913.
- #906 remains an umbrella tracker and should not advance directly to a builder.

### Changes Made

- Claimed task #906 as architect-906.
- Re-checked the parent card, child tasks #911 through #914, docs/research/entity-extractor-code-corpus-recall-harness.md, and the current benchmark/extractor seams.
- Appended this architecture review and kept the parent in backlog.

### Dependencies

- Verified: #911 is in-progress.
- Verified: #912 depends on #911.
- Verified: #913 depends on #912.
- Verified: #914 depends on #912 and #913.
- Verified: no new runtime dependency is needed beyond the existing benchmark marker and benchmark extra.

[[2026-03-22]] Sun 17:18

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs. | Corpus-fixture responsibility. The live RED seam already exists in tests/benchmarks/test_entity_extractor_corpus.py, and the implementation module is still absent. | Keep on #911 -> #912. |
| 2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids. | Stable-key schema concern. src/owlbear/memory/knowledge/models.py still gives Entity.id UUID defaults, so textual keys must stay in the corpus slice. | Keep on #911 -> #912. |
| 3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor. | Harness/reporting concern. tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain ranx retrieval helpers, not entity-recall seams. | Keep on #913 -> #914 with a local scorer. |
| 4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked. | Execution-boundary requirement. src/owlbear/memory/knowledge/extractor.py still exposes a single async extract() seam, and tests/test_knowledge_extractor.py keeps normal tests model-free. | Keep on #913 -> #914; stub extractor outputs in normal tests and leave live runs benchmark-marked. |
| 5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md. | Traceability belongs to the harness/reporting slice. Child cards still cite the code-corpus harness doc as source, so this backlink must be preserved when #913 and #914 are reviewed. | Keep on #913 -> #914 and tighten during those child reviews. |

### Architecture Notes

- The split still matches the live repo state: tests/benchmarks/test_entity_extractor_corpus.py exists as the RED contract, while tests/benchmarks/entity_extractor_corpus.py, tests/benchmarks/test_entity_extractor_recall.py, and tests/benchmarks/bench_entity_extractor_recall.py are still absent.
- tests/benchmarks/bench_graph_expansion.py remains the local precedent for checked-in benchmark data and opt-in benchmark execution.
- tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain retrieval-specific ranx seams and are the wrong abstraction for entity-recall scoring.
- src/owlbear/memory/knowledge/models.py still uses UUID-backed Entity.id values, so benchmark gold must remain keyed by stable textual identity.
- src/owlbear/memory/knowledge/extractor.py still exposes a single async extract() seam that returns empty results on failure; normal tests should continue to stub that boundary.
- pyproject.toml still registers the benchmark marker, so no new runtime dependency is needed for the scorer/reporting slice.
- #906 remains an umbrella tracker. The executable path is still #911 -> #912 -> #913 -> #914.

### Changes Made

- Claimed task #906 as architect-906.
- Re-read #906, #911, #912, #913, and #914 plus the linked research docs.
- Re-checked the live benchmark/extractor seams and the current RED artifact.
- Appended this architecture review and kept the parent in backlog.

### Dependencies

- Verified: #911 is in-progress and acts as the RED predecessor for #912.
- Verified: #912 depends on #911.
- Verified: #913 depends on #912.
- Verified: #914 depends on #912 and #913.
- Verified: no new package dependency is needed beyond the existing benchmark marker and benchmark extras.

[[2026-03-22]] Sun 17:30

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs. | Corpus-fixture concern. The active RED contract already exists in tests/benchmarks/test_entity_extractor_corpus.py and child task #911. | Keep on #911 -> #912; do not route this through a mixed parent builder card. |
| 2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids. | Stable-key schema concern. src/owlbear/memory/knowledge/models.py gives Entity.id UUID defaults, so benchmark identity must stay textual. | Keep on #911 -> #912. |
| 3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor. | Harness/reporting concern. tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain ranx retrieval utilities and do not fit entity recall. | Keep on #913 -> #914 with a local scorer. |
| 4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked. | Verifiable execution boundary. tests/test_knowledge_extractor.py disables real model requests, and src/owlbear/memory/knowledge/extractor.py exposes one async extract() seam. | Keep on #913 -> #914; normal tests stub extractor outputs and any live path stays benchmark-marked. |
| 5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md. | Traceability belongs to the runnable harness/reporting slice. The child harness cards currently cite docs/research/entity-extractor-code-corpus-recall-harness.md instead of the original benchmark plan. | Keep on #913 -> #914 and tighten those child cards when they reach backlog so the runnable output or instructions link back to docs/research/entity-extractor-gleaning-benchmark.md. |

### Architecture Notes

- Current repo state strengthens the split instead of weakening it: tests/benchmarks/test_entity_extractor_corpus.py already carries the RED corpus/schema contract, and #911 is in-progress against that seam.
- tests/benchmarks/bench_graph_expansion.py is still the local pattern for checked-in benchmark data, formatted output, and an opt-in @pytest.mark.benchmark entry point.
- tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain retrieval-specific ranx helpers (Qrels, Run, ndcg) and should not be reused for entity recall.
- src/owlbear/memory/knowledge/models.py uses UUID-backed Entity.id values, so stable textual keys must remain in the corpus/schema slice.
- src/owlbear/memory/knowledge/extractor.py exposes one async extract() boundary and returns an empty ExtractionResult on failure; normal tests should keep stubbing that seam rather than making live model calls.
- Failure mode map is deferred to #913 and #914 because #906 remains a tracker with no direct executable codepath change.
- Approving #906 as a single implementation task would violate single responsibility and TDD pairing by collapsing #911 -> #912 -> #913 -> #914 back into one mixed builder card.

### Changes Made

- Claimed task #906 as architect-906.
- Re-read #906, child tasks #911 through #914, docs/research/entity-extractor-code-corpus-recall-harness.md, tests/benchmarks/test_entity_extractor_corpus.py, tests/benchmarks/bench_graph_expansion.py, tests/benchmarks/harness.py, tests/benchmarks/evaluate.py, src/owlbear/memory/knowledge/extractor.py, src/owlbear/memory/knowledge/models.py, tests/test_knowledge_extractor.py, and pyproject.toml.
- Appended this architecture review and kept the parent in backlog.
- No new tasks created.

### Dependencies

- Verified: #911 is in-progress.
- Verified: #912 depends on #911.
- Verified: #913 depends on #912.
- Verified: #914 depends on #912 and #913.
- Verified: no new package dependency is needed beyond the existing benchmark marker flow.

[[2026-03-22]] Sun 17:42

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs. | Corpus-fixture concern. The active RED contract already exists in tests/benchmarks/test_entity_extractor_corpus.py under child task #911. | Keep on #911 -> #912; do not route this through a mixed parent builder card. |
| 2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids. | Stable-key schema concern. src/owlbear/memory/knowledge/models.py still gives Entity.id UUID defaults, so benchmark identity must stay textual. | Keep on #911 -> #912. |
| 3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor. | Harness/reporting concern. tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain ranx retrieval utilities and do not fit entity recall. | Keep on #913 -> #914 with a local scorer. |
| 4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked. | Verifiable execution boundary. src/owlbear/memory/knowledge/extractor.py exposes one async extract() seam, and tests/test_knowledge_extractor.py keeps normal tests model-free. | Keep on #913 -> #914; normal tests stub extractor outputs and any live path stays benchmark-marked. |
| 5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md. | Traceability belongs to the runnable harness/reporting slice. Child cards #913 and #914 still cite the supporting code-corpus harness research doc, so this backlink needs to be tightened when those cards reach backlog. | Keep on #913 -> #914; preserve the source-doc backlink during those child reviews. |

### Architecture Notes

- Current repo state still strengthens the split instead of weakening it: tests/benchmarks/test_entity_extractor_corpus.py exists as the active RED artifact, while no implementation-side entity-extractor benchmark module exists yet under tests/benchmarks/.
- tests/benchmarks/bench_graph_expansion.py remains the local pattern for checked-in benchmark data, formatted output, and an opt-in benchmark entry point.
- tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain retrieval-specific ranx helpers and should not be stretched into entity recall scoring.
- src/owlbear/memory/knowledge/models.py uses UUID-backed Entity.id values, so stable textual keys must remain in the corpus/schema slice.
- src/owlbear/memory/knowledge/extractor.py exposes one async extract() boundary and returns an empty ExtractionResult on failure; normal tests should continue to stub that seam rather than make live model calls.
- pyproject.toml already registers the benchmark marker and benchmark extras; no new sklearn or spaCy dependency is justified here.
- Failure mode mapping is deferred to #913 and #914 because #906 remains a tracker with no direct executable codepath change.
- Approving #906 as a single implementation card would violate single responsibility and TDD pairing by collapsing #911 -> #912 -> #913 -> #914 back into one mixed task.

### Changes Made

- Claimed task #906 as architect-906.
- Re-read #906, docs/research/entity-extractor-code-corpus-recall-harness.md, child tasks #911 through #914, and the live benchmark and extractor seams.
- Appended this architecture review and kept the parent in backlog.
- No new tasks created.

### Dependencies

- Verified: #911 is in-progress and acts as the RED predecessor for #912.
- Verified: #912 depends on #911.
- Verified: #913 depends on #912.
- Verified: #914 depends on #912 and #913.
- Verified: no new package dependency is needed beyond the existing benchmark marker and benchmark extras.

[[2026-03-22]] Sun 17:59

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1-2 | Corpus fixture and gold-schema concerns. The active RED seam already exists in tests/benchmarks/test_entity_extractor_corpus.py and task #911. | Keep on #911 -> #912. |
| 3-5 | Harness/reporting concerns. tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain ranx retrieval helpers, not entity-recall seams. | Keep on #913 -> #914 with a repo-native scorer and report layer. |

### Architecture Notes

- The split is still correct. Approving #906 as a single implementation card would collapse the active TDD seam in tests/benchmarks/test_entity_extractor_corpus.py back into mixed corpus-plus-harness work.
- tests/benchmarks/bench_graph_expansion.py remains the local precedent for checked-in benchmark data and opt-in benchmark execution.
- src/owlbear/memory/knowledge/models.py still gives Entity.id UUID-backed defaults, so stable (normalized_name, entity_type) gold keys must remain in the corpus/schema slice.
- src/owlbear/memory/knowledge/extractor.py still exposes one async extract() boundary and returns empty results on failure; normal tests should continue to stub that seam, consistent with tests/test_knowledge_extractor.py.
- pyproject.toml already provides the existing opt-in benchmark marker, so the harness slice can stay dependency-light.
- #906 remains an umbrella tracker and should not advance directly to todo.

### Changes Made

- Re-reviewed #906, the supporting research docs, child tasks #911 through #914, the active RED corpus test, benchmark helper seams, extractor/model seams, and benchmark marker config.
- Appended this architecture review and kept #906 in backlog.
- No new tasks created.

### Dependencies

- Verified child task order remains TDD-correct: #911 is in-progress, #912 depends on #911, #913 depends on #912, and #914 depends on both #912 and #913.
- Verified the active RED artifact tests/benchmarks/test_entity_extractor_corpus.py aligns with the split execution path.
- Verified the harness/reporting child cards still need their own architecture tightening to preserve a backlink to docs/research/entity-extractor-gleaning-benchmark.md in runnable instructions or output.

[[2026-03-22]] Sun 18:40

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate a representative OwlBear benchmark sample spanning Python source and Markdown docs. | Corpus-fixture responsibility. The active RED seam already exists in tests/benchmarks/test_entity_extractor_corpus.py, and the implementation path is already decomposed. | Keep on #911 -> #912. |
| 2. Store gold entity annotations keyed by (name, entity_type) rather than random entity ids. | Stable-key schema concern. src/owlbear/memory/knowledge/models.py gives Entity.id UUID-backed defaults, so gold identity must remain textual. | Keep on #911 -> #912. |
| 3. Add scorer/reporting helpers that compute micro recall and per-type recall for a run of the current EntityExtractor. | Harness/reporting concern. tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain ranx retrieval helpers, not entity-recall seams. | Keep on #913 -> #914 with a local scorer. |
| 4. Keep the harness runnable without real model calls in unit tests; real benchmark runs may be opt-in or marked. | Execution-boundary concern. src/owlbear/memory/knowledge/extractor.py exposes a single async extract seam, and tests/test_knowledge_extractor.py demonstrates the repo-standard model-free stub pattern. | Keep on #913 -> #914; normal tests stub extractor outputs and any live run stays benchmark-marked. |
| 5. Link results or run instructions back to docs/research/entity-extractor-gleaning-benchmark.md. | Traceability concern. The parent source doc is still the upstream benchmark plan, while the child harness cards currently cite the newer code-corpus harness doc. | Keep on #913 -> #914 and tighten that backlink during those child reviews. |

### Architecture Notes

- tests/benchmarks/bench_graph_expansion.py remains the local pattern for checked-in benchmark data, custom scoring, and opt-in benchmark execution.
- tests/benchmarks/harness.py and tests/benchmarks/evaluate.py are retrieval-oriented ranx utilities and should not be reused for entity recall.
- tests/benchmarks/test_entity_extractor_corpus.py now exists as the active RED contract, confirming that the corpus/schema slice is already separated from harness/reporting work.
- src/owlbear/memory/knowledge/extractor.py returns an empty ExtractionResult on failure and exposes a single async extract seam, so normal tests should stub that boundary rather than make live model calls.
- src/owlbear/memory/knowledge/models.py uses UUID-backed Entity.id values, so benchmark gold must remain keyed by stable textual identity.
- pyproject.toml already registers the benchmark marker and benchmark extras; no new scoring dependency is justified.
- #906 remains an umbrella tracker. The executable path is #911 -> #912 -> #913 -> #914, not a direct builder handoff from this parent card.

### Changes Made

- Claimed task #906 as architect-906.
- Re-validated child tasks #911, #912, #913, and #914 against the current code seams and research docs.
- Appended this architecture review and kept the parent in backlog.
- No new tasks created.

### Dependencies

- Verified: #911 is in-progress and carries the corpus RED contract.
- Verified: #912 depends on #911.
- Verified: #913 depends on #912.
- Verified: #914 depends on #912 and #913.
- Verified: #907 and #908 still treat #906 as the upstream benchmark prerequisite, so the parent should remain a tracker rather than be deleted.
- Added/Removed/Verified: no new runtime dependency is needed beyond the existing benchmark marker flow.

[[2026-03-23]] Mon 17:31

## Architecture Review

**Verdict:** Refine

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1-2 | Corpus fixture and gold-schema work already lives on the RED/GREEN pair #911 -> #912, with the live RED seam in tests/benchmarks/test_entity_extractor_corpus.py. | Keep this parent as a tracker in backlog; do not advance it to todo. |
| 3-5 | Harness, reporting, model-free execution, and research backlink work is a separate runnable slice on #913 -> #914. | Keep execution on #913 -> #914; preserve the backlink to docs/research/entity-extractor-gleaning-benchmark.md when those child cards are reviewed. |

### Architecture Notes

- tests/benchmarks/test_entity_extractor_corpus.py is the live RED seam for the corpus/schema slice.
- tests/benchmarks/bench_graph_expansion.py remains the local benchmark pattern for checked-in data and opt-in execution.
- tests/benchmarks/harness.py and tests/benchmarks/evaluate.py remain ranx retrieval helpers and are the wrong abstraction for entity-recall scoring.
- src/owlbear/memory/knowledge/models.py still uses UUID-backed Entity.id values, so benchmark gold must remain keyed by stable textual identity.
- src/owlbear/memory/knowledge/extractor.py exposes a single async extract() seam and returns empty results on failure; normal tests should stub that boundary.
- #906 remains an umbrella tracker. The executable path is #911 -> #912 -> #913 -> #914.

### Changes Made

- Re-validated #906, child tasks #911, #912, #913, and #914, the supporting research doc, and the live benchmark/extractor seams.
- Appended this architecture review and left #906 in backlog.
- Released the claim after review.

### Dependencies

- Verified: #911 is in-progress.
- Verified: #912 depends on #911.
- Verified: #913 depends on #912.
- Verified: #914 depends on #912 and #913.
- Verified: no new runtime dependency is needed beyond the existing benchmark marker flow in pyproject.toml.
- Noted: preserve the backlink to docs/research/entity-extractor-gleaning-benchmark.md when #913 and #914 reach architecture review.

## Architecture Review

**Verdict:** Split (blocked as umbrella tracker)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Curate benchmark sample | Corpus-fixture responsibility, already covered by #911 (RED, in-progress) and #912 (GREEN, ideation). | Keep on #911 -> #912. |
| 2. Gold annotations keyed by (name, entity_type) | Stable-key schema concern, already scoped to #911 -> #912. | Keep on #911 -> #912. |
| 3. Scorer/reporting helpers | Harness/reporting concern, already scoped to #913 -> #914 with local scorer. | Keep on #913 -> #914. |
| 4. Runnable without real model calls | Execution-boundary requirement, scoped to #913 -> #914. | Keep on #913 -> #914. |
| 5. Link back to gleaning benchmark doc | Traceability requirement, attached to harness slice. | Tighten when #913/#914 reach their own arch review. |

### Architecture Notes

- This is the 7th architecture review of #906. The verdict has been Split every time.
- The root cause of repeated dispatch is that the task sat in backlog without a block flag, so the planner kept re-routing it to the architect.
- Now blocked as an umbrella tracker. The executable path remains #911 -> #912 -> #913 -> #914.
- When all children reach done/archived, unblock #906 and advance it to done as a completed tracker.

### Changes Made

- Blocked #906 with reason: umbrella tracker waiting for child tasks.
- No new tasks created. No status change (stays in backlog, blocked).

### Dependencies

- Verified: #911 is in-progress (RED tests for corpus/schema).
- Verified: #912 depends on #911 (GREEN corpus/schema, ideation).
- Verified: #913 depends on #912 (RED harness/reporting, ideation).
- Verified: #914 depends on #912 and #913 (GREEN harness/reporting, ideation).
