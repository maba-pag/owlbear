---
id: 620
title: Implement DiagramService wrapping Kroki HTTP API
status: archived
priority: needed
created: 2026-03-07T05:20:55.5155454+01:00
updated: 2026-03-07T18:08:24.0448217+01:00
started: 2026-03-07T06:23:27.4053025+01:00
completed: 2026-03-07T18:08:24.0448217+01:00
tags:
    - phase-research
    - scope:core
    - tooling
depends_on:
    - 617
class: standard
---

**Context:** Builder overreach on #617 implemented the full DiagramService during the test task. 8 of 10 original AC lines are already satisfied. This task covers ONLY the remaining integration work.

**Remaining AC (all that is left):**
- [ ] `kroki_server_url: str` field added to `OwlBearSettings` in `src/owlbear/config.py` (default `'https://kroki.io'`); placed in a new `# --- Diagrams ---` section near the Browser/screenshots block
- [ ] `src/owlbear/tools/diagram/__init__.py` exports `DiagramService` and `DiagramError` (`from .service import DiagramService, DiagramError`)
- [ ] Bootstrap or caller wires `settings.kroki_server_url` into `DiagramService(server_url=...)`  verify pattern by checking how `screenshot_mode` or other config fields flow to service constructors
- [ ] Existing 26 tests in `tests/test_diagram_service.py` still pass
- [ ] `uv run ruff check src/owlbear/tools/diagram/ src/owlbear/config.py` clean

**Already done (by #617 builder overreach  do NOT reimplement):**
- DiagramService class in service.py 
- async generate() method with correct signature 
- POST with Content-Type: text/plain and raw source body (NOT deflate+base64  original AC was wrong, see docs/research/diagram-service-kroki.md) 
- Input validation (diagram_type, output_format, source) 
- DiagramError on non-2xx 
- httpx.AsyncClient with Timeout(30, connect=5) 

Pattern: follow how `screenshot_mode` flows from OwlBearSettings to ScreenshotService.
Ref: docs/research/diagram-service-kroki.md
