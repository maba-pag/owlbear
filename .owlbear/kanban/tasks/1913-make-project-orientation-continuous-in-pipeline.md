---
id: 1913
title: Make project orientation continuous in pipeline
status: collect
priority: medium
created: 2026-07-12T03:04:01.048065+02:00
updated: 2026-07-12T03:57:59.191441+02:00
tags:
  - scope:agent-config
  - feature
parent: 1914
depends_on:
  - 1912
ac:
  - '`h-project-orientation` is the prominent shared handbook for doc-index, py-index,
    ts-index, direct reads, rg/language-server references, and Semble, with discovery
    explicitly separated from proof.'
  - Shaping records a verified Change Module Map and applies existing 
    deep-module diagnostics; builder and verifier carry and check that map 
    without treating it as source authority.
  - A durable non-ideation follow-up records how the replacement ideation flow 
    should use deep-module evaluation and approach-level module mapping.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Rename and promote the orientation handbook, wire it into shaper/builder/verifier, apply deep-module guidance during shaping, add a per-change module map to Shape Notes, and record deferred ideation integration outside the retiring ideation artifacts.

## Scope
In: `share/agents`, `share/skills`, `share/WIRING.md`, generated doc index, durable future-work note.
Out: changes to the current ideation flow and spec-kit.

Proof guidance: run agent ecosystem structural checks and exact-reference scans.

[[2026-07-12T03:57:59+02:00]]
## Builder Notes
- Renamed project orientation from `h-code-orientation` to `h-project-orientation` and wired it into shaper, builder, verifier, w-research, and task decomposition.
- Added deep-module and Change Module Map guidance to shaping/decomposition, including the bounded shortcut rule for brownfield work.
- Updated `README.md`, `serve/tools/README.md`, `.github/copilot-instructions.md`, `share/WIRING.md`, and the orientation handbook.
- Deferred replacement-ideation integration recorded as task #1915 rather than editing retiring ideation/spec-kit artifacts.
- Validation: `validate_agents.py` pass, focused extraction tests 25 pass, `git diff --check` clean, `builder-challenger` pass after shortcut narrowing.
- No implementation code changed; docs/skills/agent guidance only.
