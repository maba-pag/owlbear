---
id: 261
title: BgeM3 idle-timeout model unloading
status: in-progress
priority: important
created: 2026-02-28T12:42:18.8860493+01:00
updated: 2026-03-01T00:10:53.5394722+01:00
started: 2026-02-28T22:56:17.0533744+01:00
tags:
    - phase-9
    - embedding
    - config
depends_on:
    - 248
    - 287
class: standard
---

Add idle-timeout auto-unload to BgeM3EmbeddingProvider to free ~3GB RAM when not in use.

AC:
- [ ] BgeM3EmbeddingProvider gains _last_used: float tracking via time.monotonic()
- [ ] threading.Timer fires unload() after idle_timeout seconds (default 600)
- [ ] Timer resets on every embed()/embed_hybrid() call (cancel + restart)
- [ ] unload() sets self._model = None and calls gc.collect() (existing pattern)
- [ ] Next embed()/embed_hybrid() transparently re-initializes via existing _ensure_model()
- [ ] OwlBearSettings gains embedding_idle_timeout: int = 600 (OWLBEAR_EMBEDDING_IDLE_TIMEOUT env var)
- [ ] Thread-safe: threading.Lock around timer reset and model access in _ensure_model()

Keep in BgeM3EmbeddingProvider (KISS, no separate ModelManager).
See docs/bge-m3-integration-research.md section 3.8
