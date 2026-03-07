---
id: 535
title: Make logfire import conditional in daemon.py
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:40.4014439+01:00
updated: 2026-03-07T00:31:21.1415164+01:00
started: 2026-03-07T00:29:36.874959+01:00
tags:
    - audit
    - config
    - scope:core
class: standard
---

F-25: import logfire unconditional at daemon.py top level. If logfire not installed, daemon import fails. Add try/except ImportError guard. AC: daemon importable without logfire. See docs/code-quality-audit.md.

## Research (N/A - trivial change)

1. **Theoretical validity** - N/A trivial try/except ImportError guard. Standard Python pattern for optional deps.
2. **Prior art** - N/A. Universal Python idiom (PEP 302 import hooks, stdlib examples like json/simplejson).
3. **Technical feasibility** - N/A. logfire is not in core deps or any optional extra in pyproject.toml. Only used in configure_otel() (line 170), which is gated behind an if-check at call site (line 364-365). Guard the import, set logfire=None, raise early in configure_otel if None.
4. **Architecture fit** - N/A. Single file change, no interface impact.
5. **Implementation approach** - try/except ImportError at line 22, set logfire=None on failure. In configure_otel(), raise RuntimeError if logfire is None.
