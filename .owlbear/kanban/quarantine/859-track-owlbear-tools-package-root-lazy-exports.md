---
id: 859
title: Track owlbear.tools package-root lazy exports
status: archived
priority: important
created: 2026-03-19T15:08:31.0825643+01:00
updated: 2026-03-22T19:17:55.6997064+01:00
started: 2026-03-22T19:17:55.6997064+01:00
completed: 2026-03-22T19:17:55.6997064+01:00
tags:
    - architecture
    - bug
    - scope:tools
parent: 857
depends_on:
    - 850
    - 879
blocked: true
block_reason: 'Resolved by child tasks #878/#879; historical tracker only. Refresh research before reopening.'
class: standard
---

**Source:** #857 post-#850 follow-up

This task tracks the narrowed package-root lazy-export cleanup described in docs/research/tools-root-lazy-exports.md. It is not a direct builder handoff; execution proceeds through child tasks #878 (RED coverage) and #879 (GREEN implementation).

## AC

- [ ] #859 remains the parent tracker for the package-root lazy-export change; no builder handoff is taken directly from this task.
- [ ] The RED child task verifies in a clean subprocess that bare import owlbear.tools does not load owlbear.tools.github_api or owlbear.core.retry, while from owlbear.tools import GitHubToolset and the existing 10-symbol public surface from #814 remain intact.
- [ ] The GREEN child task limits code changes to src/owlbear/tools/**init**.py, uses a cached importlib.import_module-based **getattr** map for the existing 10 names in **all**, and adds no new dependency.
- [ ] import owlbear.config staying clean after #850 remains a regression check, but it is not the primary failing behavior that justifies the lazy-export work.
- [ ] **dir** parity stays out of scope for this track unless a later architect review promotes it into the GREEN child task.

[[2026-03-20]] Fri 16:06

## Research :: doc=docs/research/tools-root-lazy-exports.md :: key-findings=#850 archived; clean subprocess import owlbear.config no longer loads owlbear.tools.github_api or owlbear.core.retry; clean subprocess import owlbear.tools still eagerly loads both modules while preserving the 10-name API from #814 :: recommendation=.91 keep #859 as backlog tracker and refine execution through child tasks #878 (RED coverage) and #879 (GREEN implementation) :: implementation-guidance=use a cached importlib.import_module map in module **getattr**, keep the existing **all**, add no new dependency, and leave **dir** optional unless the architect wants interactive discovery parity :: attribution=docs/sources/overview.md :: follow-up-commands-created=#878 Add RED coverage for owlbear.tools package-root lazy exports; #879 Implement cached lazy exports in owlbear.tools package root

[[2026-03-20]] Fri 16:38

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| after #850, clean subprocess import owlbear.config does not load owlbear.tools.github_api or owlbear.core.retry | Stale. After #850 and the BrowserConfig move, this already passes in the current tree and no longer describes the live failing behavior. | Rewrote #859 as a tracker and kept config-import cleanliness as regression evidence only. |
| import owlbear.tools and from owlbear.tools import GitHubToolset preserve the 10-symbol public surface from #814 | Real compatibility contract, but it belongs to the child RED and GREEN tasks rather than a direct builder handoff from #859. | Reframed #859 around child tasks #878 and #879. |
| targeted import smoke and re-export tests pass | Too vague. The repo already has concrete re-export identity and subprocess side-effect test patterns. | Rewrote the tracker AC to point at those concrete child-task expectations. |

### Architecture Notes

- Verified in src/owlbear/tools/**init**.py that the package still eagerly imports all 10 public names, so bare import owlbear.tools is the remaining live behavior to fix.
- Verified in src/owlbear/memory/knowledge/**init**.py that a cached module-level **getattr** lazy-export map is already an accepted package-root pattern in this repo.
- Verified in tests/test_tools_init_reexports.py that the exact 10-symbol tools API from #814 is the compatibility contract to preserve.
- Verified in src/owlbear/config.py, src/owlbear/tools/browser/config.py, and tests/test_browser_config_nesting.py that import owlbear.config is already clean after the BrowserConfig leaf-node move.
- Because child tasks #878 and #879 already exist, #859 should remain a backlog tracker and not move to todo.

### Changes Made

- Rewrote #859 body to describe the current narrowed scope as a parent tracker after #850.
- Left #859 in backlog and did not create a builder handoff from this task.
- Appended this architecture review.

### Dependencies

- Added/Removed/Verified: verified #850 is archived; verified #878 (RED) and #879 (GREEN) exist as the execution path; verified those child tasks need their own architect reviews before they move toward implementation.

[[2026-03-20]] Fri 18:06

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| #859 remains the parent tracker for the package-root lazy-export change; no builder handoff is taken directly from this task. | Correct parent-task contract. It keeps an umbrella tracker out of the builder queue while child tasks carry executable work. | Keep |
| The RED child task verifies in a clean subprocess that bare import owlbear.tools does not load owlbear.tools.github_api or owlbear.core.retry, while from owlbear.tools import GitHubToolset and the existing 10-symbol public surface from #814 remain intact. | Correct RED contract and already aligned with the approved child task #878 plus the existing compatibility coverage in tests/test_tools_init_reexports.py. | Keep |
| The GREEN child task limits code changes to src/owlbear/tools/**init**.py, uses a cached importlib.import_module-based **getattr** map for the existing 10 names in **all**, and adds no new dependency. | Correct single-file, single-domain implementation contract that follows the existing lazy-export precedent in src/owlbear/memory/knowledge/**init**.py. | Keep |
| import owlbear.config staying clean after #850 remains a regression check, but it is not the primary failing behavior that justifies the lazy-export work. | Correct. src/owlbear/config.py and src/owlbear/tools/browser/config.py already keep the config path clean; the live issue is bare import owlbear.tools. | Keep |
| **dir** parity stays out of scope for this track unless a later architect review promotes it into the GREEN child task. | Correct scope boundary. Optional dir() parity is already isolated in follow-up task #883. | Keep |

### Architecture Notes

- Verified src/owlbear/tools/**init**.py still eagerly imports the 10 public names, so bare package import remains the live behavior to fix.
- Verified src/owlbear/memory/knowledge/**init**.py is the in-repo precedent for a cached module-level **getattr** lazy-export map.
- Verified tests/test_tools_init_reexports.py already defines the 10-name compatibility contract and tests/test_knowledge_exports.py defines the clean-subprocess sys.modules regression pattern.
- Verified #878 is approved to todo as the RED predecessor and #879 remains the single GREEN backlog task, preserving TDD order.
- The remaining mismatch was task metadata, not task scope; the title now reflects the package-root lazy-export issue instead of the already-resolved config-import symptom.

### Changes Made

- Renamed #859 to Track owlbear.tools package-root lazy exports.
- Re-validated the tracker AC against the current source tree, research doc, and child tasks #878, #879, and #883.
- Appended this architecture review.
- Left #859 in backlog as a parent tracker with no direct builder handoff.

### Dependencies

- Added/Removed/Verified: verified #850 archived, #878 approved to todo as RED predecessor, #879 remains the GREEN implementation task in backlog, and #883 isolates optional **dir** parity work.

[[2026-03-21]] Sat 02:41

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| #859 remains the parent tracker for the package-root lazy-export change; no builder handoff is taken directly from this task. | Correct tracker contract. This task should coordinate the narrowed lazy-export work, not enter the builder queue itself. | Keep |
| The RED child task verifies in a clean subprocess that bare import owlbear.tools does not load owlbear.tools.github_api or owlbear.core.retry, while from owlbear.tools import GitHubToolset and the existing 10-symbol public surface from #814 remain intact. | Correct RED contract and still aligned with the current child task. `tests/test_tools_init_reexports.py` now contains the subprocess side-effect check plus the 10-name compatibility coverage. | Keep |
| The GREEN child task limits code changes to src/owlbear/tools/**init**.py, uses a cached importlib.import_module-based **getattr** map for the existing 10 names in **all**, and adds no new dependency. | Correct single-file GREEN contract that matches the accepted in-repo precedent in src/owlbear/memory/knowledge/**init**.py and stays inside the tools layer. | Keep |
| import owlbear.config staying clean after #850 remains a regression check, but it is not the primary failing behavior that justifies the lazy-export work. | Correct boundary. The live behavior is still eager package-root imports in src/owlbear/tools/**init**.py, not config-path pollution. | Keep |
| **dir** parity stays out of scope for this track unless a later architect review promotes it into the GREEN child task. | Correct scope isolation. Optional discovery parity is already separated into follow-up task #883 instead of widening the core runtime fix. | Keep |

### Architecture Notes

- Verified src/owlbear/tools/**init**.py still eagerly imports the 10 public names at module import time, so bare import owlbear.tools remains the live package-root side-effect to fix.
- Verified src/owlbear/memory/knowledge/**init**.py is the current repo precedent for a cached importlib.import_module plus globals()[name] module-level **getattr** lazy-export map.
- Verified tests/test_tools_init_reexports.py defines the public 10-name compatibility contract and now includes the subprocess sys.modules side-effect check; tests/test_knowledge_exports.py remains the local subprocess pattern precedent.
- Verified child-task staging is still correct: #878 is the RED predecessor already advanced to docs, #879 is the GREEN implementation task in todo, and #883 remains ideation as an optional follow-up.
- The actual refinement needed on #859 was board-shape metadata, not AC wording: as a parent tracker, it should depend on #879 so backlog filters stop redispatching it while the executable child task is still active.
- Failure mode map: not applicable for this tracker task because it does not introduce or modify a runtime codepath itself.

### Changes Made

- Re-validated the tracker AC against the current source tree, research doc, and child tasks #878, #879, and #883.
- Added dependency on #879 so the parent tracker stays gated on the active GREEN child instead of appearing as a dispatchable backlog task.
- Appended this architecture review.
- Left #859 in backlog as a parent tracker with no direct builder handoff.

### Dependencies

- Added/Removed/Verified: kept dependency on #850 as historical prerequisite; added dependency on #879 as the active execution gate; verified #878 already satisfies the RED predecessor role through #879; verified #883 remains optional and out of scope for closing the core lazy-export track.

[[2026-03-21]] Sat 05:18

## Architecture Review

**Verdict:** BLOCK

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| #859 remains the parent tracker for the package-root lazy-export change; no builder handoff is taken directly from this task. | Satisfied and now historical only. The executable RED/GREEN contract has already run through child tasks #878 and #879. | Move the tracker out of backlog; do not dispatch a builder from #859. |
| The RED child task verifies in a clean subprocess that bare import owlbear.tools does not load owlbear.tools.github_api or owlbear.core.retry, while from owlbear.tools import GitHubToolset and the existing 10-symbol public surface from #814 remain intact. | Satisfied by archived task #878 and the current subprocess plus compatibility coverage in tests/test_tools_init_reexports.py. | Keep as historical evidence only; no further refinement needed here. |
| The GREEN child task limits code changes to src/owlbear/tools/**init**.py, uses a cached importlib.import_module-based **getattr** map for the existing 10 names in **all**, and adds no new dependency. | Satisfied in current source. src/owlbear/tools/**init**.py now exposes the approved explicit **all**, _LAZY_IMPORTS map, cached **getattr**, and no new runtime dependency. | Keep closed under #879 rather than reopening #859. |
| import owlbear.config staying clean after #850 remains a regression check, but it is not the primary failing behavior that justifies the lazy-export work. | Satisfied in current source. BrowserConfig lives in src/owlbear/config.py, src/owlbear/tools/browser/config.py is only a re-export, and tests/test_browser_config_nesting.py preserves that boundary. | Keep as regression evidence only, not a new implementation target. |
| **dir** parity stays out of scope for this track unless a later architect review promotes it into the GREEN child task. | Satisfied and still isolated. src/owlbear/tools/**init**.py adds no **dir**, and optional parity work remains separated into #883. | Keep out of the completed core lazy-export track. |

### Architecture Notes

- Verified src/owlbear/tools/**init**.py now matches the approved lazy-export shape: explicit 10-name **all**, _LAZY_IMPORTS, cached **getattr**, and no new dependency.
- Verified tests/test_tools_init_reexports.py now contains both the clean-subprocess side-effect regression and the 10-name compatibility contract.
- Verified src/owlbear/config.py, src/owlbear/tools/browser/config.py, and tests/test_browser_config_nesting.py still enforce the post-#850 leaf-node config boundary, so config-path cleanliness remains regression evidence only.
- Verified board state: #878 is archived, #879 is done, #883 remains optional in ideation, and #882 is a separate docs follow-up not required to close the runtime lazy-export track.
- Leaving #859 in backlog would keep redispatching a historical parent tracker whose executable contract is already complete. The correct next state is blocked ideation: historical tracker only, refresh research or create a new task if a new lazy-export regression appears.
- Failure mode map: not applicable for this tracker task because it no longer introduces or changes a runtime codepath.

### Changes Made

- Re-validated #859 against the current source tree, regression tests, research doc, and child-task state.
- Appended this architecture review.
- Prepared #859 to leave the active backlog by moving it to blocked ideation as a historical tracker.

### Dependencies

- Added/Removed/Verified: verified #850 remains the config-boundary prerequisite, #878 is archived as the RED predecessor, #879 is done as the GREEN implementation, #883 remains optional for **dir** parity, and #882 is a separate docs-only follow-up.
