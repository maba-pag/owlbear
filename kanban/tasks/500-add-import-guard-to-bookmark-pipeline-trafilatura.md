---
id: 500
title: Add import guard to bookmark_pipeline trafilatura
status: backlog
priority: important
created: 2026-03-04T07:38:13.5690379+01:00
updated: 2026-03-06T19:22:42.9045336+01:00
tags:
    - audit
    - config
    - knowledge
class: standard
---

F-07: bookmark_pipeline.py _default_web_read() imports trafilatura without guard. Raises raw ModuleNotFoundError without crawl/search extras.

Research (2026-03-06): Trivial fix. Identical pattern exists in embeddings.py L65-72 and reranker.py L46-54 (try/except ImportError with actionable message). trafilatura is provided by both `crawl` and `search` extras (pyproject.toml L30-32). Wrap `import trafilatura` in try/except ImportError, raise with message pointing to `uv pip install 'owlbear[search]'`. See docs/config-dependency-audit.md F-07.

AC:
- [ ] `import trafilatura` in _default_web_read() wrapped in try/except ImportError
- [ ] Error message includes install command: `uv pip install 'owlbear[search]'`
- [ ] Pattern matches existing guards in embeddings.py and reranker.py
- [ ] Existing tests still pass
