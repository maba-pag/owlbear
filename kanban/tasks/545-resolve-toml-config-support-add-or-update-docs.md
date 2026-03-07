---
id: 545
title: 'Resolve TOML config support: add or update docs'
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:48.9808448+01:00
updated: 2026-03-07T00:49:22.6556331+01:00
started: 2026-03-07T00:45:03.7727369+01:00
tags:
    - audit
    - config
    - docs
class: standard
---

F-09: copilot-instructions.md claims 'Env vars + TOML config file' but OwlBearSettings only uses env_prefix=OWLBEAR_. No TomlConfigSettingsSource. Either add TOML support or correct docs. See docs/config-dependency-audit.md.

## Research findings (2026-03-07)
See docs/toml-config-resolution-research.md for full analysis.

**Recommendation (.85):* Fix docs (Option A). Change copilot-instructions.md Config row Notes from 'Env vars + TOML config file, validated at startup' to 'Env vars (OWLBEAR_ prefix), validated at startup'. YAGNI/KISS aligned. TOML support can be added later in ~15 LOC if demand arises.

**AC:**
- [ ] copilot-instructions.md Config row says 'Env vars (OWLBEAR_ prefix), validated at startup'
- [ ] No false claims about TOML config file support
- [ ] docs/toml-config-resolution-research.md archived as research artifact
