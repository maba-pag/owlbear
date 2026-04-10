---
id: 545
title: 'Resolve TOML config support: add or update docs'
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:48.9808448+01:00
updated: 2026-03-22T19:20:07.3309858+01:00
started: 2026-03-07T00:45:03.7727369+01:00
completed: 2026-03-22T19:20:07.3309858+01:00
tags:
    - audit
    - config
    - docs
blocked: true
block_reason: 'Stale backlog card: the authoritative config docs were already corrected in-repo on 2026-03-19, so routing #545 to builder would duplicate completed docs work.'
class: standard
---

F-09: copilot-instructions.md claims 'Env vars + TOML config file' but OwlBearSettings only uses env_prefix=OWLBEAR_. No TomlConfigSettingsSource. Either add TOML support or correct docs. See docs/config-dependency-audit.md.

## Research findings (2026-03-07)
See docs/research/toml-config-resolution.md for full analysis.

**Recommendation (.85):* Fix docs (Option A). Change copilot-instructions.md Config row Notes from 'Env vars + TOML config file, validated at startup' to 'Env vars (OWLBEAR_ prefix), validated at startup'. YAGNI/KISS aligned. TOML support can be added later in ~15 LOC if demand arises.

**AC:**
- [ ] copilot-instructions.md Config row says 'Env vars (OWLBEAR_ prefix), validated at startup'
- [ ] No false claims about TOML config file support
- [ ] docs/research/toml-config-resolution.md archived as research artifact

[[2026-03-21]] Sat 04:12
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| copilot-instructions.md Config row says 'Env vars (OWLBEAR_ prefix), validated at startup' | Already satisfied in .github/copilot-instructions.md; the Config row now documents env-only settings with the OWLBEAR_ prefix. | Do not dispatch; task outcome already present in repo |
| No false claims about TOML config file support | The only authoritative project doc that carried the false runtime claim has already been corrected; remaining TOML mentions are research or audit artifacts, not active product docs. | Do not dispatch; treat current card wording as stale |
| docs/research/toml-config-resolution.md archived as research artifact | Already satisfied; the research document exists under docs/research and records the docs-fix recommendation plus future TOML-support option. | Do not dispatch; research artifact already present |

### Architecture Notes
- Repo state already resolves the docs side of F-09. .github/copilot-instructions.md now says the config system uses env vars with the OWLBEAR_ prefix, while src/owlbear/config.py still exposes env-only BaseSettings sources with no TomlConfigSettingsSource or settings_customise_sources override.
- git blame shows the authoritative Config row was corrected on 2026-03-19 (commit fe078f1e), after this task was created. The backlog card still reflects the pre-fix problem statement rather than pending work.
- This is a docs-only task, so TDD and a RED predecessor are not applicable. There is no runtime behavior change to verify, only board metadata drift to prevent from re-entering builder flow.
- Sending this to todo would duplicate already-landed documentation work and violate KISS/YAGNI.

### Changes Made
- Claimed #545 as architect.
- Appended this architecture review with repo-state evidence.
- Blocking the task to prevent stale redispatch.

### Dependencies
- Verified: docs/research/toml-config-resolution.md exists and supports the docs-fix recommendation.
- Verified: src/owlbear/config.py remains env-only, so the current authoritative docs are consistent with implementation.
- Gap noted: task body still describes work that the repo already contains.
