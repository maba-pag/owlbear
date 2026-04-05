---
id: 500
title: Add import guard to bookmark_pipeline trafilatura
status: archived
priority: important
created: 2026-03-04T07:38:13.5690379+01:00
updated: 2026-03-07T18:07:56.8969566+01:00
started: 2026-03-06T20:28:35.1240247+01:00
completed: 2026-03-07T18:07:56.8969566+01:00
tags:
    - audit
    - config
    - knowledge
depends_on:
    - 607
class: standard
---

F-07: bookmark_pipeline.py _default_web_read() imports trafilatura without guard. Raises raw ModuleNotFoundError without crawl/search extras.

Research (2026-03-06): Trivial fix. Identical pattern exists in embeddings.py L65-72 and reranker.py L46-54 (try/except ImportError with actionable message). trafilatura is provided by both crawl and search extras (pyproject.toml L30-32). See docs/config-dependency-audit.md F-07.

AC:

- [ ] In _default_web_read() (bookmark_pipeline.py ~L181), wrap `import trafilatura` in try/except ImportError
- [ ] On ImportError, `raise ImportError(msg) from None` where msg includes install command `uv pip install 'owlbear[search]'`
- [ ] Guard uses `from None` to suppress chained traceback (matching embeddings.py and reranker.py pattern)
- [ ] Only trafilatura is guarded; httpx and owlbear.core.retry are core deps and remain bare imports
- [ ] `uv run pytest tests/test_bookmark_pipeline.py -q --tb=short` passes
- [ ] `uv run ruff check src/owlbear/memory/knowledge/bookmark_pipeline.py` clean
