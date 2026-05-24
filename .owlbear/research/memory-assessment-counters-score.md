# Model Fields — Assessment Counters and Score Computation

> **Owning task:** #1841 — P2-02: Model fields — assessment counters and score computation
> **Date:** 2026-05-24 **Status:** Complete

## 1. Context and Question

Task #1841 adds assessment counter fields (`outstanding_count`, `unremarkable_count`, `didnt_use_count`) and a `score` float to the memory model. It also defines scoring constants and a `compute_score()` function. Questions: (a) where do constants and function live, (b) how to handle backward-compatible deserialization of existing entries, (c) dual-package sync between `owlbear_memory` and `owlbear_mcp_memory`.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| serve/memory/src/owlbear_memory/models.py | Codebase | 1.0 — current MemoryEntry model |
| serve/memory/src/owlbear_memory/engine.py | Codebase | 1.0 — save() method, entry creation |
| serve/memory/src/owlbear_memory/storage.py | Codebase | 1.0 — frontmatter serialization |
| serve/mcp-memory/src/owlbear_mcp_memory/models.py | Codebase | 1.0 — duplicate MemoryEntry |
| serve/mcp-memory/src/owlbear_mcp_memory/engine.py | Codebase | 1.0 — duplicate frontmatter serialization |
| .owlbear/briefs/draft-memory-voting/brief.md | Project doc | 1.0 — authoritative scoring formula |
| Stack Overflow reputation system (+10/-2) | Prior art | 0.8 — asymmetric additive scoring |
| Reddit Wilson score interval ranking | Prior art | 0.7 — confidence-based community ranking |

## 3. Analysis

### 3.1 Scoring Formula Validity

The formula `score = confidence + (outstanding × 0.1) - (unremarkable × 0.01)` uses a 10:1 asymmetric weight ratio. Comparable systems:

| System | Positive | Negative | Ratio | Decay |
|--------|----------|----------|-------|-------|
| OwlBear (proposed) | +0.1 | -0.01 | 10:1 | None |
| Stack Overflow | +10 | -2 | 5:1 | None |
| Reddit (hot) | +1 | -1 | 1:1 | Time-based |

The 10:1 ratio is more conservative than SO — one "outstanding" offsets 10 "unremarkable". No time decay; score moves only on evidence. Sound design.

### 3.2 Backward-Compatible Deserialization

Existing `.md` files lack the new YAML fields. Two approaches:

| Approach | Mechanism | Pro | Con |
|----------|-----------|-----|-----|
| A: Field defaults | `score: float = 0.0`, counters: `int = 0` | KISS, no validator | `score=0.0` incorrect until migration |
| B: model_validator | `@model_validator(mode='before')` sets `score=confidence` | Correct on read | Mixes migration logic into model |

**Recommendation: Option A** (confidence: .85). Migration (P2-03) exists as a dedicated task and runs before recall uses `score` for ordering (P2-04). Transient `score=0.0` is harmless since nothing sorts by score until P2-04.

### 3.3 Dual-Package Update Scope

Both packages serialize MemoryEntry to frontmatter explicitly. Changes needed:

| Package | File | Change |
|---------|------|--------|
| owlbear_memory | models.py | Add 4 fields to MemoryEntry |
| owlbear_memory | engine.py | Add constants + `compute_score()` + update `save()` |
| owlbear_memory | storage.py | Add 4 keys to `write_entry()` frontmatter dict |
| owlbear_memory | __init__.py | Export `compute_score`, constants |
| owlbear_mcp_memory | models.py | Mirror 4 fields |
| owlbear_mcp_memory | engine.py | Add 4 keys to `write()` frontmatter dict |

### 3.4 Constants Placement

AC1 specifies "defined in the memory engine module". Module-level constants in `engine.py`:

```python
OUTSTANDING_BOOST: float = 0.1
UNREMARKABLE_PENALTY: float = 0.01
STALE_THRESHOLD: int = 50
```

### 3.5 compute_score Signature

Per AC2: `compute_score(confidence: float, outstanding_count: int, unremarkable_count: int) -> float`. Pure function, no side effects, trivial implementation. Note: `didnt_use_count` is NOT an input — it doesn't affect score directly (feeds slot-efficiency in P2-05).

## 4. Recommendation

Straightforward implementation matching the prescriptive ACs. No design ambiguity.

- Use field defaults (Option A) for backward compat
- Constants in `engine.py`, `compute_score()` exported from package
- Update both packages' model and serialization

Confidence: .90. Challenge: skipped — trivial implementation, prescriptive ACs, no design alternatives to evaluate.

## 5. Follow-up Tasks

No new follow-up tasks needed — the decomposition in #1839 already covers all downstream work (P2-03 migration depends on this, P2-04 recall depends on this). Implementation is ready to proceed.
