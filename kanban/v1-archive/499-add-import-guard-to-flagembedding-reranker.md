---
id: 499
title: Add import guard to FlagEmbedding reranker
status: archived
priority: important
created: 2026-03-04T07:38:12.8421182+01:00
updated: 2026-03-07T18:07:56.3782241+01:00
started: 2026-03-06T17:51:34.1058497+01:00
completed: 2026-03-07T18:07:56.3782241+01:00
tags:
    - audit
    - config
    - knowledge
class: standard
---

F-06: reranker.py does bare FlagEmbedding import without try/except. If knowledge extra not installed, raises raw ModuleNotFoundError instead of actionable message. Follow embeddings.py pattern. See docs/config-dependency-audit.md.

## Research Findings

### Problem

In `src/owlbear/memory/knowledge/reranker.py` L48, `_ensure_model()` does:

`python
from FlagEmbedding import FlagReranker
``n
No try/except guard. Raw `ModuleNotFoundError` if `knowledge` extra not installed.

### Pattern to Follow

The sibling file `src/owlbear/memory/knowledge/embeddings.py` L63-71 already wraps the same kind of import correctly:

`python
try:
    from FlagEmbedding import BGEM3FlagModel
except ImportError:
    msg = (
        'FlagEmbedding is required for BgeM3EmbeddingProvider. '
        'Install it with: uv pip install FlagEmbedding'
    )
    raise ImportError(msg) from None
``n
### Fix Required

Wrap L48-49 in `_ensure_model()` with the same try/except pattern:

`python
try:
    from FlagEmbedding import FlagReranker
except ImportError:
    msg = (
        'FlagEmbedding is required for BGERerankerProvider. '
        'Install it with: uv pip install FlagEmbedding'
    )
    raise ImportError(msg) from None
``n
One method, two lines changed. Trivial fix.

### Acceptance Criteria

- [ ] `_ensure_model()` wraps `from FlagEmbedding import FlagReranker` in try/except ImportError
- [ ] ImportError message includes install instructions
- [ ] Unit test verifies ImportError message when FlagEmbedding unavailable
- [ ] Existing reranker tests still pass
