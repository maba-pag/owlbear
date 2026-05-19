---
id: 857
title: Reduce owlbear.tools __init__ eager import side effects
status: archived
priority: important
created: 2026-03-19T14:21:48.6304279+01:00
updated: 2026-03-22T19:21:20.7839265+01:00
started: 2026-03-22T19:21:20.7839265+01:00
completed: 2026-03-22T19:21:20.7839265+01:00
tags:
    - architecture
    - bug
    - scope:tools
parent: 850
depends_on:
    - 850
blocked: true
block_reason: 'Research stale: BrowserConfig now lives in owlbear.config, so import owlbear.config no longer loads owlbear.tools. Refresh the research only if eager import owlbear.tools itself still needs action.'
class: standard
---

Follow-up from #850 research.

- #814 made tools/__init__.py an eager public API surface.
- import owlbear.config currently preloads owlbear.tools via owlbear.tools.browser.config, masking the direct daemon circular import.
- Reduce these side effects without reintroducing the core-tools cycle.

## AC

- [ ] In a clean subprocess, import owlbear.config does not load owlbear.tools.github_api or owlbear.core.retry as a side effect
- [ ] import owlbear.tools keeps the supported public surface, or an explicit decision request documents any intentional narrowing
- [ ] targeted import smoke covers import owlbear.tools and import owlbear.config

[[2026-03-19]] Thu 15:12
Research doc: docs/research/tools-init-side-effects.md. Clean subprocess probes show import owlbear.config loads owlbear.tools.github_api and owlbear.core.retry, while import owlbear.daemon still fails unless config preloads owlbear.tools first. Recommendation (.90): after #850, replace eager src/owlbear/tools/__init__.py imports with a cached lazy export map (__getattr__, __dir__, __all__) for the 10 exports established in #814. Follow-up command executed: kanban\\kanban-md.exe create 'Lazy-load owlbear.tools exports to remove config import side effects' --priority important --status ideation --tags architecture,bug,scope:tools --parent 857 --depends-on 850 -> created #859. Attribution updated: docs/sources/overview.md.

[[2026-03-19]] Thu 16:17

## Architecture Review

__Verdict:__ REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| In a clean subprocess, import owlbear.config does not load owlbear.tools.github_api or owlbear.core.retry as a side effect | Correct measurable outcome, but it must remain downstream of #850 so lazy loading does not become another way to mask the core -> tools cycle. | Keep downstream in #859 |
| import owlbear.tools keeps the supported public surface, or an explicit decision request documents any intentional narrowing | Not mechanically precise as written. The supported surface is the exact 10-symbol API established by #814, and the research already rejects narrowing as the default path. | Rewrite downstream as the exact #814 surface; do not dispatch from #857 |
| targeted import smoke covers import owlbear.tools and import owlbear.config | Directionally correct but incomplete for the chosen design. The concrete contract also needs from owlbear.tools import GitHubToolset plus the existing re-export identity coverage. | Rewrite downstream in #859 |

### Architecture Notes

- Verified in src/owlbear/tools/__init__.py that the package still eagerly imports all 10 public re-exports, including GitHubToolset, which pulls in owlbear.tools.github_api at package import time.
- Verified in src/owlbear/config.py and src/owlbear/tools/browser/config.py that importing BrowserConfig from the tools.browser package forces Python to execute owlbear.tools.__init__ first, which is why import owlbear.config currently preloads the tools package.
- Verified in src/owlbear/memory/knowledge/__init__.py that OwlBear already has a cached module-level __getattr__ lazy-export precedent for package surfaces.
- Verified in tests/test_tools_init_reexports.py and tests/test_imports.py that the repo already treats the 10-symbol owlbear.tools surface and import smoke as explicit compatibility requirements.
- Verified #850 is the approved core-layer prerequisite and #859 is the narrower post-#850 implementation candidate produced by the research. Because #859 now carries the executable contract, #857 is a stale umbrella task and should remain in backlog rather than moving to todo.

### Changes Made

- Claimed #857 for architecture review.
- Appended this review clarifying that #857 should remain a tracker task while #859 carries the concrete implementation contract after #850.
- Left #857 in backlog and did not create a builder handoff from this task.

### Dependencies

- Added/Removed/Verified: verified #814 as the public-surface precedent, #850 as the approved prerequisite, and #859 as the narrower follow-up implementation task.

[[2026-03-19]] Thu 17:01
Architect update: added dependency #850 after direct code verification. Prior REFINE verdict stands; #857 remains a backlog tracker, and the narrower implementation work should stay downstream with its own RED predecessor.

[[2026-03-20]] Fri 16:03

## Architecture Review

__Verdict:__ BLOCK

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| In a clean subprocess, import owlbear.config does not load owlbear.tools.github_api or owlbear.core.retry as a side effect | Stale. In the current tree this already passes: a fresh subprocess leaves owlbear.tools, owlbear.tools.github_api, and owlbear.core.retry unloaded after import owlbear.config. | Reject current AC as an implementation target and send back for refreshed research |
| import owlbear.tools keeps the supported public surface, or an explicit decision request documents any intentional narrowing | Still a real compatibility constraint, but it is already enforced by the existing 10-symbol re-export contract and does not by itself justify new lazy-loading work. | Keep as background compatibility evidence only; do not dispatch builder from #857 |
| targeted import smoke covers import owlbear.tools and import owlbear.config | Directionally fine, but the task no longer states a currently failing behavior. If lazy-loading owlbear.tools itself still matters, the contract must be rewritten around that measurable package-import behavior and paired with a RED task. | Send back to ideation for re-scope |

### Architecture Notes

- Verified in src/owlbear/config.py that BrowserConfig is now defined in the leaf config module, not imported from owlbear.tools.browser.
- Verified in src/owlbear/tools/browser/config.py that BrowserConfig is only a compatibility re-export from owlbear.config.
- Verified in tests/test_browser_config_nesting.py that the repo now enforces this leaf-node design: BrowserConfig.__module__ must be owlbear.config and config.py must not import from owlbear.tools.
- Verified with a clean subprocess probe that import owlbear.config no longer loads owlbear.tools, owlbear.tools.github_api, or owlbear.core.retry.
- Verified with a clean subprocess probe that import owlbear.daemon now succeeds directly after #850, and tests/test_blocked_url_error_location.py covers import owlbear.config; import owlbear.daemon without pre-seeding owlbear.tools.
- Verified in src/owlbear/tools/__init__.py and tests/test_tools_init_reexports.py that import owlbear.tools still eagerly loads the 10-symbol public surface, including GitHubToolset. That may still be a potential cleanup topic, but it is not the same problem described in #857's current AC.
- Verified #859 exists as the downstream lazy-export follow-up, but it is currently claimed by another agent and was not modified in this review.
- Conclusion: #857's research and AC are stale relative to the current codebase. Approving it would send a builder after a bug that no longer reproduces, which violates KISS/YAGNI and the evidence-over-claims rule.

### Changes Made

- Claimed #857 for architecture review.
- Re-ran current clean-process import probes instead of relying on the 2026-03-19 task history.
- Appended this review explaining why #857 is no longer executable as written.
- Prepared #857 to return to ideation for refreshed research instead of moving it toward implementation.

### Dependencies

- Added/Removed/Verified: verified #850 is complete and removes the daemon-import prerequisite; verified #814 remains the public-surface contract; verified #859 exists but is not safe to edit from this invocation because it is actively claimed.
