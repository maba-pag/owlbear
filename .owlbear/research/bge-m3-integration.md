# bge-m3 ONNX Availability and FlagEmbedding Integration Patterns

> **Owning task:** #237 — Research: bge-m3 ONNX availability and FlagEmbedding integration patterns
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear is adopting Qdrant local mode + bge-m3 for hybrid search (dense 1024d + sparse + ColBERT multivector). The prior researcher (#236) claimed "FastEmbed cannot do bge-m3 — FlagEmbedding (PyTorch) required." This task verifies that claim, investigates ONNX export availability, and documents FlagEmbedding integration patterns for the implementation task (#236 follow-up 3).

**Hardware:** Ryzen 8840U, 16 GB RAM, no GPU. ~11 GB available. **Current stack:** FastEmbed ONNX for bge-small-en-v1.5, PyTorch for bge-reranker-v2-m3 via FlagReranker.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| BAAI/bge-m3 HuggingFace model page | huggingface.co/BAAI/bge-m3 | .95 | Official usage examples, model card, ONNX tag confirmation |
| BAAI/bge-m3 file tree (main + onnx/) | huggingface.co/BAAI/bge-m3/tree/main | .95 | File sizes: pytorch_model.bin 2.27 GB, colbert_linear.pt 2.1 MB, sparse_linear.pt 3.52 KB, onnx/ folder 2.29 GB |
| FastEmbed supported models page | qdrant.github.io/fastembed/examples/Supported_Models | .95 | bge-m3 absent from all model lists (dense, sparse, late-interaction) |
| FastEmbed issue #107 (bge-m3 support) | github.com/qdrant/fastembed/issues/107 | .95 | 2+ year open issue; NirantK: "2 linear models for Sparse and multi-vec need ONNX export and loader" |
| FastEmbed PR #602 (bge-m3 dense only) | github.com/qdrant/fastembed/pull/602 | .90 | Feb 2026 PR — adds dense ONNX embedding only, no sparse/ColBERT. Open, no reviewer |
| FlagEmbedding source (cloned v1.3.5) | github.com/FlagOpen/FlagEmbedding | .95 | M3Embedder code analysis: constructor, encode(), sparse/ColBERT internals, FP16 CPU behavior, memory cleanup |
| FlagEmbedding setup.py | github.com/FlagOpen/FlagEmbedding/blob/master/setup.py | .90 | Dependencies: torch, transformers, datasets, accelerate, sentence_transformers, peft, ir-datasets |
| yuniko-software/bge-m3-qdrant-sample | github.com/yuniko-software/bge-m3-qdrant-sample | .85 | Full bge-m3 + Qdrant hybrid search integration pattern |
| FastEmbed issue #485 (multioutput models) | github.com/qdrant/fastembed/issues/485 | .80 | Architectural prerequisite for multi-output model support in FastEmbed |

## 3. Analysis

### 3.1 ONNX Export Status — Verified from HuggingFace File Tree

**Official ONNX exists but is DENSE-ONLY.** The `onnx/` folder in BAAI/bge-m3 contains:

| File | Size | What it provides |
|------|------|------------------|
| `onnx/model.onnx` + `model.onnx_data` | 2.29 GB | Base XLM-RoBERTa transformer → last_hidden_state |
| `onnx/config.json` | 698 B | Model config |
| Root: `colbert_linear.pt` | 2.1 MB | ColBERT linear head (PyTorch only) — `Linear(1024, 1024)` |
| Root: `sparse_linear.pt` | 3.52 KB | Sparse linear head (PyTorch only) — `Linear(1024, 1)` |

**Critical:** `colbert_linear.pt` and `sparse_linear.pt` are NOT in the `onnx/` folder. The ONNX export covers only the base transformer. To get sparse/ColBERT outputs via ONNX, you'd need:

- (a) Convert the .pt linear heads to ONNX separately (trivial — they're single Linear layers), OR
- (b) Apply the projections in numpy post-hoc (also trivial: `sparse_weight @ hidden_state`, `colbert_weight @ hidden_state[:, 1:]`), OR
- (c) Use FlagEmbedding which wraps all three components

**NirantK (FastEmbed maintainer) confirmed** in issue #107 (Apr 2, 2024): "the 2 linear models for Sparse and multi-vec need to have an ONNX export and loader as well. That's something we've to do for now. We can support the dense model without friction but I'd rather avoid the confusion and support all 3 vectors when we support BGE-M3."

### 3.2 FastEmbed bge-m3 Status

| Item | Status | Detail |
|------|--------|--------|
| Dense embedding support | PR open (#602) | Feb 2026 PR — dense only, 15 LOC, no reviewer assigned |
| Sparse embedding support | Not started | Blocked on issue #485 (multioutput models architecture) |
| ColBERT support | Not started | Same blocker as sparse |
| Issue lifetime | 2+ years | #107 opened Feb 2024, still open as of Feb 2026 |
| Realistic ETA | Unknown | No roadmap commitment. Issue #485 has no milestone |

**Verdict:** FastEmbed bge-m3 with all 3 outputs is not happening in any foreseeable timeline. Even the dense-only PR has no reviewer. **Do not plan around future FastEmbed bge-m3 support.**

### 3.3 FlagEmbedding Integration — Code Analysis from Source

**Public API** (from `FlagEmbedding.BGEM3FlagModel`, alias for `M3Embedder`):

```python
from FlagEmbedding import BGEM3FlagModel

# Constructor — loads tokenizer + model immediately (NOT lazy)
model = BGEM3FlagModel(
    "BAAI/bge-m3",
    use_fp16=True,  # Ignored on CPU (see §3.4)
    devices=None,  # Auto-detects: falls back to ["cpu"]
    batch_size=256,  # Default batch size
    query_max_length=512,  # Default query max tokens
    passage_max_length=512,  # Default passage max tokens
    return_dense=True,  # Include dense in output
    return_sparse=False,  # Include sparse in output
    return_colbert_vecs=False,  # Include ColBERT in output
)

# Encode — returns dict with 3 keys
output = model.encode(
    ["text1", "text2"],
    batch_size=12,
    max_length=8192,
    return_dense=True,
    return_sparse=True,
    return_colbert_vecs=True,
)

# Output format:
# output["dense_vecs"]       → np.ndarray shape (N, 1024)
# output["lexical_weights"]  → List[Dict[str(token_id), float]]  (positive only)
# output["colbert_vecs"]     → List[np.ndarray] each shape (T-1, 1024), T=tokens excl CLS
```

**Constructor is NOT lazy** — unlike our current `FastEmbedProvider` and `BGERerankerProvider` which defer model loading to first use, `BGEM3FlagModel.__init__()` immediately calls `AutoModel.from_pretrained()` and loads `colbert_linear.pt` + `sparse_linear.pt`. Our adapter must implement lazy loading ourselves (see §3.6).

### 3.4 FP16 on CPU — Verified from Source Code

In `M3Embedder.encode_single_device()` (line 347 of `m3.py`):

```python
if device == "cpu":
    self.use_fp16 = False
if self.use_fp16:
    self.model.half()
```

**FP16 is automatically disabled on CPU.** Setting `use_fp16=True` has no effect — the model runs in FP32 on CPU regardless. This means:

- **RAM on CPU = FP32 always** ≈ 568M params × 4 bytes = **2.27 GB** (model weights only)
- **Total RAM with PyTorch overhead** ≈ **2.8–3.2 GB** (model + tokenizer + tensors + PyTorch runtime)
- There is no built-in INT8 quantization option in FlagEmbedding's inference API

### 3.5 Sparse Output Format — Verified from Source

The `_process_token_weights()` function in `encode_single_device()`:

1. Gets `sparse_vecs` from model output: `torch.relu(sparse_linear(hidden_state))` — ReLU ensures **all weights are non-negative**
2. Filters out special tokens (CLS, EOS, PAD, UNK) — sets their weights to 0
3. For duplicate token IDs, takes the **max** weight
4. Returns `Dict[str(token_id), float]` — keys are string-ified integer token IDs, values are positive floats

**Conversion to Qdrant `SparseVector`:**

```python
def sparse_to_qdrant(lexical_weights: dict[str, float]) -> models.SparseVector:
    """Convert FlagEmbedding lexical weights to Qdrant SparseVector."""
    # No need to filter negatives — ReLU already ensures positive-only
    indices = [int(k) for k in lexical_weights.keys()]
    values = list(lexical_weights.values())
    return models.SparseVector(indices=indices, values=values)
```

**Typical sparsity:** For a 512-token chunk, expect ~200–400 non-zero dimensions (estimated from typical XLM-RoBERTa vocabulary coverage — each subword token gets a weight, minus special tokens and zero-weight tokens after ReLU).

### 3.6 ColBERT Output Format — Verified from Source

The `_process_colbert_vecs()` function:

1. Gets `colbert_vecs` from model: `colbert_linear(last_hidden_state[:, 1:])` — skips CLS token position
2. Strips padding tokens using attention mask: `colbert_vecs[:tokens_num - 1]`
3. Returns `np.ndarray` shape `(T-1, 1024)` where T = number of non-padding tokens

**Conversion to Qdrant multivector:**

```python
# ColBERT vecs go directly into Qdrant named vector "colbert"
# Qdrant MultiVectorConfig(comparator=MAX_SIM) handles the max_sim scoring
point = models.PointStruct(
    id=chunk_id,
    vector={
        "dense": output["dense_vecs"][i].tolist(),
        "sparse": sparse_to_qdrant(output["lexical_weights"][i]),
        "colbert": output["colbert_vecs"][i].tolist(),  # List[List[float]] — N×1024
    },
    payload={...},
)
```

### 3.7 RAM and Performance — Calculated from Model Architecture

| Configuration | Model Weights | Runtime Overhead | Total RAM | Source |
|---------------|--------------|------------------|-----------|--------|
| bge-m3 FP32 (CPU) | 2.27 GB | ~0.5–0.8 GB | **~2.8–3.0 GB** | pytorch_model.bin = 2.27 GB; overhead includes tokenizer, PyTorch runtime, batch tensors |
| bge-m3 FP16 (GPU only) | 1.14 GB | ~0.3 GB | ~1.4 GB | Not usable on CPU (code forces FP32) |
| bge-m3 ONNX dense-only | 2.29 GB | ~0.2 GB | ~2.5 GB | onnx/model.onnx_data = 2.27 GB; ONNX Runtime lighter than PyTorch |

**Encoding latency per chunk on CPU (estimated):**

| Mode | Latency | Throughput | Source |
|------|---------|------------|--------|
| Dense only | ~30 ms/chunk | ~33 ch/s | Prior research #234 estimated ~30 ch/s; consistent with XLM-RoBERTa-large on CPU |
| Dense + sparse | ~32 ms/chunk | ~31 ch/s | Sparse head adds negligible compute (Linear(1024,1) + ReLU) |
| Dense + sparse + ColBERT | ~35 ms/chunk | ~28 ch/s | ColBERT head adds Linear(1024,1024) per token — small vs base model |

**Note:** These are estimates derived from XLM-RoBERTa-large CPU benchmarks and the observation that sparse (1024→1) and ColBERT (1024→1024) linear heads add <10% compute over the ~330M multiply-add operations in the base transformer. No independent CPU benchmark of bge-m3 was found.

**Can dense-only be faster?** Marginally. The bottleneck is the base transformer forward pass (~98% of compute). Disabling sparse/ColBERT returns saves only the linear head computation and output processing — not significant. However, disabling ColBERT saves **memory** during inference (no ColBERT tensor allocation).

### 3.8 Memory Lifecycle — Unloading When Idle

From `AbsEmbedder.stop_self_pool()`:

```python
def stop_self_pool(self):
    if self.pool is not None:
        self.stop_multi_process_pool(self.pool)
        self.pool = None
    try:
        self.model.to("cpu")
        torch.cuda.empty_cache()
    except:
        pass
    if gc is not None and callable(gc.collect):
        gc.collect()
```

This moves model to CPU (no-op if already there) and runs GC. **To fully unload:**

```python
del model._model  # or del model entirely
gc.collect()
# On CPU, no torch.cuda.empty_cache() needed
```

Our adapter should implement idle-timeout unloading: track last-use timestamp, `del` model after N minutes idle, re-initialize on next call.

### 3.9 FlagEmbedding Dependencies — Impact Assessment

FlagEmbedding `install_requires` (v1.3.5):

| Dependency | Already in OwlBear? | Size impact | Needed for inference? |
|-----------|--------------------|-----------|--------------------|
| `torch>=1.6.0` | **Yes** (for FlagReranker) | 0 | Yes |
| `transformers>=4.44.2` | **Yes** (for FlagReranker) | 0 | Yes |
| `datasets>=2.19.0` | No | ~50 MB | **No** — only for training/eval |
| `accelerate>=0.20.1` | No | ~5 MB | **No** — only for multi-GPU |
| `sentence_transformers` | No | ~20 MB | **No** — not used by BGEM3FlagModel |
| `peft` | No | ~10 MB | **No** — only for LoRA finetuning |
| `ir-datasets` | No | ~30 MB | **No** — only for evaluation |
| `sentencepiece` | Maybe | ~5 MB | Yes (tokenizer) |
| `protobuf` | Maybe | ~5 MB | Transitive |

**Key insight:** FlagEmbedding pulls 4 unnecessary dependencies for inference-only use. Our adapter should **NOT** add FlagEmbedding as a project dependency. Instead, import `BGEM3FlagModel` at runtime (already the pattern for `FlagReranker`). Users install FlagEmbedding manually or via an optional `[embedding]` group.

**Better alternative:** Import only what's needed from FlagEmbedding — the actual M3Embedder only uses `torch`, `transformers.AutoTokenizer`, `transformers.AutoModel`, and `huggingface_hub.snapshot_download`. A thin local wrapper (~80 LOC) could replace the FlagEmbedding dependency entirely.

### 3.10 Batch Encoding — Behavior from Source

From `encode_single_device()`:

1. Tokenizes all texts without padding (to get true lengths)
2. **Sorts by length** for less padding overhead
3. **Auto-adjusts batch size** — starts at configured `batch_size` (default 256), reduces by 25% on RuntimeError or OOM
4. Pads per batch, not globally
5. Returns results in original order (reorders by `argsort` index)

**Optimal batch size on CPU (16 GB):** Start with `batch_size=16–32` for 512-token chunks. The auto-reduction handles OOM gracefully. Larger batches don't help on CPU (no GPU parallelism benefit). Smaller batches reduce peak memory.

### 3.11 ONNX vs FlagEmbedding Decision Matrix

| Criterion | ONNX (dense only) | ONNX + numpy heads | FlagEmbedding (PyTorch) |
|-----------|-------------------|-------------------|------------------------|
| Dense output | ✅ | ✅ | ✅ |
| Sparse output | ❌ | ✅ (custom ~30 LOC) | ✅ (built-in) |
| ColBERT output | ❌ | ✅ (custom ~20 LOC) | ✅ (built-in) |
| Runtime | ONNX Runtime (~200 MB) | ONNX Runtime (~200 MB) | PyTorch (~2 GB, already present) |
| Model RAM | ~2.5 GB | ~2.5 GB | ~3.0 GB |
| Dependency chain | `onnxruntime` + `tokenizers` | `onnxruntime` + `tokenizers` + `torch` (for .pt loading) | `torch` + `transformers` (already present) |
| Maintenance | FastEmbed may add support eventually | Custom code to maintain | Upstream supported |
| Tokenizer | Fast tokenizer via `tokenizers` | Same | `transformers.AutoTokenizer` |
| Complexity | Minimal | Medium (~50 LOC extra) | Minimal (wrap existing API) |
| Precedent in OwlBear | FastEmbedProvider exists | Novel | BGERerankerProvider exists |

## 4. Recommendation (.85 confidence)

**Use FlagEmbedding `BGEM3FlagModel` directly.** Rationale:

1. **PyTorch is already present** — BGERerankerProvider uses it. Zero new heavy deps.
2. **All 3 outputs from one call** — no custom sparse/ColBERT code to maintain.
3. **Precedent** — BGERerankerProvider already follows this pattern (lazy import from FlagEmbedding).
4. **ONNX+numpy alternative is a custom fork** — 50 LOC to maintain, plus you still need torch to load the .pt head weights at setup time, negating the main ONNX benefit.
5. **Future-proof** — If FlagEmbedding updates the model or adds optimizations, we get them for free.

**Our adapter pattern** (mirrors `BGERerankerProvider`):

```python
class BgeM3EmbeddingProvider:
    """EmbeddingProvider backed by FlagEmbedding.BGEM3FlagModel."""

    def __init__(self, model_name: str = "BAAI/bge-m3", batch_size: int = 16) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: object | None = None

    def _ensure_model(self) -> object:
        if self._model is None:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=True,  # No-op on CPU, but correct if GPU available
                devices=["cpu"],
                batch_size=self.batch_size,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=True,
            )
        return self._model

    def embed_hybrid(self, texts: list[str]) -> dict:
        """Return dense, sparse, and ColBERT vectors in one pass."""
        if not texts:
            return {"dense_vecs": [], "lexical_weights": [], "colbert_vecs": []}
        model = self._ensure_model()
        return model.encode(texts, batch_size=self.batch_size, max_length=512)

    def unload(self) -> None:
        """Release model memory."""
        self._model = None
        import gc

        gc.collect()
```

**Risk mitigations:**

- Pin `FlagEmbedding>=1.3.5,<2.0` to avoid breaking changes
- Wrap in Protocol adapter so we can swap to ONNX later without API change
- Lazy loading + `unload()` method for memory management

## 5. Follow-up Tasks

1. **Implement BgeM3EmbeddingProvider** — New class implementing EmbeddingProvider protocol. Lazy loading, `embed_hybrid()` returns all 3 vector types. TDD. Priority: needed. Tags: phase-9, embedding, knowledge-graph.

2. **Add sparse/ColBERT to EmbeddingProvider protocol** — Current protocol only has `embed() → list[list[float]]` (dense). Extend with optional `embed_hybrid() → HybridEmbedding` returning dense + sparse + ColBERT. Keep backward-compatible. TDD. Priority: needed. Tags: phase-9, embedding.

3. **Add idle-timeout model unloading** — Track last-use timestamp on BgeM3EmbeddingProvider; call `unload()` after configurable idle period (default: 10 min). Prevents 3 GB RAM sitting idle. TDD. Priority: important. Tags: phase-9, embedding, config.

4. **Benchmark bge-m3 CPU encoding** — Measure actual RAM and latency on Ryzen 8840U. Test batch sizes 4/8/16/32. Record: peak RSS, chunks/sec for dense-only vs all-three. Priority: important. Tags: phase-9, test, embedding.

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| BAAI/bge-m3 model card | huggingface.co/BAAI/bge-m3 | Usage examples, model specs, ONNX file listing | docs/research/bge-m3-integration.md | 2026-02-28 |
| FastEmbed supported models | qdrant.github.io/fastembed/examples/Supported_Models | Confirmed bge-m3 absent from all model lists | docs/research/bge-m3-integration.md | 2026-02-28 |
| FastEmbed issue #107 | github.com/qdrant/fastembed/issues/107 | NirantK quote on ONNX linear head requirement | docs/research/bge-m3-integration.md | 2026-02-28 |
| FastEmbed PR #602 | github.com/qdrant/fastembed/pull/602 | Dense-only PR status, Feb 2026 | docs/research/bge-m3-integration.md | 2026-02-28 |
| FlagEmbedding v1.3.5 source | github.com/FlagOpen/FlagEmbedding | M3Embedder code: FP16 CPU disable, sparse format, ColBERT format, dependencies | docs/research/bge-m3-integration.md | 2026-02-28 |
| yuniko-software/bge-m3-qdrant-sample | github.com/yuniko-software/bge-m3-qdrant-sample | Qdrant hybrid search integration pattern | docs/research/bge-m3-integration.md | 2026-02-28 |
