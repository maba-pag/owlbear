# EntityExtractor Benchmark Corpus Implementation Gate

> **Owning task:** #912 — Build EntityExtractor benchmark corpus and gold schema
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #912 is the GREEN phase for the corpus fixture. Prior research
(#906, #911) established the contract: ≥8 trimmed OwlBear samples, stable
`(normalized_name, entity_type)` gold keys, deterministic order, no live
model calls, no filesystem I/O at load time. This gate validates the
implementation approach before the builder starts, with one critical
correction to the storage format recommendation.

## 2. Sources Studied

| Source | URL / Path | Relevance | What |
|--------|------------|-----------|------|
| RED test contract | `tests/benchmarks/test_entity_extractor_corpus.py` | .99 | Full test suite defining CorpusSample/GoldEntity shape, IO guards, and corpus invariants |
| RED placeholder | `tests/benchmarks/entity_extractor_corpus.py` | .95 | Import-error placeholder confirming module-level replacement is expected |
| routing_dataset.py pattern | `tests/benchmarks/routing_dataset.py` | .95 | Frozen dataclasses with all data as inline Python constants, no file IO |
| bench_graph_expansion.py | `tests/benchmarks/bench_graph_expansion.py` | .90 | Checked-in `SyntheticDoc` dataclasses with deterministic list order |
| spaCy data formats | <https://spacy.io/api/data-formats> | .85 | Text-plus-annotation corpus shapes; `(start, end, label)` and BILUO keying patterns |
| GraphRAG inputs docs | <https://microsoft.github.io/graphrag/index/inputs/> | .85 | Document schema: id, text, title, metadata; text-unit provenance model |
| Prior research (#906) | `docs/research/entity-extractor-code-corpus-recall-harness.md` | .90 | Recommended JSON manifest — contradicted by #911 IO guards |
| Prior research (#911) | `docs/research/entity-extractor-benchmark-corpus-gold-schema.md` | .90 | Gold key design, determinism rules, sample scope guidelines |
| Entity model | `src/owlbear/memory/knowledge/models.py` | .95 | EntityType enum values: file, function, class_, decision, pattern, concept |
| Reviewer evidence (#911) | Task #911 body, Review Evidence section | .90 | AC4 gap: import-time IO detection noted as LAX but not blocking |

## 3. Analysis

### 3.1 Storage Format — Critical Correction

| Option | IO-safe | #911 IO guards pass | Repo fit | Verdict |
|--------|---------|---------------------|----------|---------|
| JSON manifest + loader | No | **FAIL** | Medium | **Reject** |
| Python-only constants | Yes | PASS | High | **Use** |

The #906 research recommended "checked-in JSON manifest plus thin loader"
(§3.2). However, the #911 RED tests patch `builtins.open`,
`Path.read_text`, `Path.read_bytes`, `os.walk`, `os.scandir`,
`Path.iterdir`, `Path.glob`, and `Path.rglob` around both `load_corpus()`
calls **and** module import (via `exec` of compiled bytecode). Any file
read — including JSON — triggers `AssertionError`.

The only viable option is Python-only constants: frozen dataclasses or
`NamedTuple` instances defined directly in the module body, following the
`routing_dataset.py` and `bench_graph_expansion.py` precedent.

### 3.2 Module API Shape

The RED test imports define the exact contract:

| Symbol | Type | Contract |
|--------|------|----------|
| `GoldEntity` | dataclass/NamedTuple | Fields: `normalized_name: str`, `entity_type: str`. No `id` field. |
| `CorpusSample` | dataclass/NamedTuple | Fields: `source_label: str`, `source_kind: str`, `origin_path: str`, `text: str`, `gold_entities: list[GoldEntity]` |
| `ENTITY_EXTRACTOR_CORPUS` | `list[CorpusSample]` | The constant list, ≥8 items |
| `load_corpus` | `() -> list[CorpusSample]` | Returns `list(ENTITY_EXTRACTOR_CORPUS)` (shallow copy) |

`load_corpus()` should return a shallow copy of the constant to ensure
test isolation (callers cannot mutate the source list).

### 3.3 Sample Selection Criteria

| Criterion | Rule | Source |
|-----------|------|--------|
| Count | ≥8 samples | AC1 |
| Source mix | Both `python` and `markdown` | AC2 |
| Origin constraint | `origin_path` starts with `src/` or `tests/` | RED test `_OWLBEAR_PATH_PREFIXES` |
| Stability | Prefer stable knowledge-related modules, not scratch/kanban | #911 research §3.4 |
| Trimming | Pre-trimmed excerpts, no leading/trailing whitespace | RED `test_sample_text_is_trimmed` |
| Labels | Human-readable, not UUID-like | RED `test_source_labels_are_not_uuid_like` |

Recommended samples (4 Python + 4 Markdown minimum):

**Python (`source_kind: "python"`):**

- `models.py` excerpt — EntityType, Entity, Edge definitions
- `extractor.py` excerpt — EntityExtractor class, ExtractionResult
- `graph.py` excerpt — GraphStore class, entity CRUD methods
- `retrieval.py` excerpt — GraphAugmentedRetriever, RetrievalResult
- `chunker.py` excerpt (optional 5th) — TextChunker, Chunk model

**Markdown (`source_kind: "markdown"`):**

- `architecture.md` §1–2 excerpt — system vision, components
- `architecture.md` §4.1 excerpt — OwlBearAgent description
- `architecture.md` §4.2 excerpt — HookRegistry, event types
- `SECURITY.md` excerpt (optional) — safety patterns

Excerpts should be 200–500 words each: long enough for entity richness,
short enough to keep the module reviewable.

### 3.4 Gold Annotation Guidelines

| Rule | Rationale |
|------|-----------|
| Use `EntityType` string values exactly (`file`, `function`, `class_`, `decision`, `pattern`, `concept`) | RED `test_gold_entity_type_values_match_entitytype_strings` |
| No generic `entity` or `Entity` type | RED `test_gold_entity_type_is_not_generic_entity_string` |
| `normalized_name` is lowercase or title-case canonical form, not UUID | RED `test_gold_normalized_name_is_not_uuid` |
| At least one sample has non-empty `gold_entities` | RED `test_at_least_one_sample_has_gold_entities` |
| Gold covers obvious entities only — don't over-annotate | KISS; benchmark measures recall, not precision |

Aim for 3–8 gold entities per Python sample (classes, functions, enums)
and 2–5 per Markdown sample (concepts, patterns, components).

## 4. Recommendation (.92 confidence)

Implement `tests/benchmarks/entity_extractor_corpus.py` as a pure
Python-constants module using frozen `@dataclass` types, following the
`routing_dataset.py` pattern. Embed 8–10 trimmed OwlBear excerpts as
string literals with hand-curated `(normalized_name, entity_type)` gold
annotations. `load_corpus()` returns a shallow copy of the constant list.
No JSON, no file IO, no new dependencies.

Risk: manual gold annotations may drift if source files are heavily
refactored. Mitigation: the corpus is trimmed excerpts frozen at a point
in time — the benchmark measures extractor quality against static gold,
not against the live codebase.

## 5. Follow-up Tasks

Task #912 is the direct follow-up (already exists). No new tasks needed.
Existing downstream: #913 (recall harness RED), #914 (recall harness
GREEN), #922 (corpus authoring contract docs).
