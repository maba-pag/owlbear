# architecture.md Rewrite — Discrepancy Analysis

> **Owning task:** #462 — Rewrite architecture.md to match actual codebase
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

architecture.md v0.2 (2026-02-28) has drifted severely from the codebase. The documentation audit (docs/documentation-audit.md, F-01) flagged it as **critically outdated**. This research catalogs every discrepancy to inform a precise rewrite of sections 3, 4.3, 4.4, 5.2, 6, and 7.

**Approach decision:** Full rewrite of affected sections is correct (not incremental patches) because the drift is structural — entire packages and agents are missing, not just stale line items.

## 2. Sources

| Source | What | Relevance |
|--------|------|-----------|
| `src/owlbear/` (full directory listing) | Ground truth for package structure | 1.0 |
| `docs/documentation-audit.md` (F-01) | Initial gap identification | 0.9 |
| `src/owlbear/bootstrap.py` (942 LOC) | Confirms assembly gap resolved | 1.0 |
| `.github/copilot-instructions.md` | Agent inventory (8 agents) | 0.8 |

## 3. Discrepancy Matrix

### 3.1 Agent Definitions (§3, §4.4)

| Doc claims | Actual | Status |
|------------|--------|--------|
| coder.md | **Does not exist** | Renamed to builder.md |
| orchestrator.md | orchestrator.md | ✅ |
| researcher.md | researcher.md | ✅ |
| reviewer.md | reviewer.md | ✅ |
| writer.md | writer.md | ✅ |
| _(missing)_ | architect.md | ❌ Not listed |
| _(missing)_ | builder.md | ❌ Not listed |
| _(missing)_ | closer.md | ❌ Not listed |
| _(missing)_ | kanban-planner.md | ❌ Not listed |

**Total:** Doc says 5, reality is **8**. Doc-audit said 7 — writer.md exists now (8 total).

### 3.2 Missing Packages/Modules (§3)

| Package | Files | In doc? |
|---------|-------|---------|
| `planning/` | `__init__.py`, extractor.py, markdown.py, models.py | ❌ Missing entirely |
| `projects/` | `__init__.py`, models.py, store.py, toolset.py, workspace.py | ❌ Missing entirely |
| `safety/` | `__init__.py`, gate.py, policy.py | ❌ Missing entirely |
| `bootstrap.py` | 942 LOC — wires all components | ❌ Missing entirely |

### 3.3 Missing Files in Listed Packages (§3)

| Package | Missing from doc |
|---------|-----------------|
| `core/` (+3) | errors.py, escalation.py, progress.py |
| `channels/` (+2) | slack_mrkdwn.py, slack_templates.py |
| `memory/` (+2) | consolidation.py, error_journal.py |
| `knowledge/` (+9) | bookmark.py, bookmark_pipeline.py, bookmark_toolset.py, evaluator.py, inter_doc_graph_builder.py, query_service.py, refresh.py, retrieval.py, source_store.py |
| `tools/` (+7) | kanban.py, knowledge.py, knowledge_source.py, screenshot.py, screenshot_hook.py, visual_feedback.py, web_search.py |

**Knowledge count:** Doc says "14 files, ~2500 LOC" → reality is **23 files**.

### 3.4 Toolset Wiring Status (§4.3)

Doc marks 4 toolsets as "⚠ Built, not wired":

| Toolset | Doc status | Actual status |
|---------|-----------|---------------|
| DelegationToolset | Not wired | ✅ Wired in bootstrap.py |
| BrowserToolset | Not wired | ✅ Wired in bootstrap.py |
| HookedToolset | Not wired | ✅ Wired in bootstrap.py |
| MCPServerRegistry | Not wired | ✅ Wired in bootstrap.py |

Additionally, 7 toolsets exist but are not listed at all:

- KanbanToolset, KnowledgeToolset, KnowledgeSourceToolset
- ScreenshotService, VisualFeedbackToolset
- WebSearchToolset, ProjectToolset

### 3.5 Assembly Gap (§6) — Fully Stale

Section 6 claims "no bootstrap layer wires them into a working system" and marks task #263 as critical blocker. `bootstrap.py` (942 LOC) now exists and wires:

- All hooks (7 of 7), all toolsets, agent registry, delegation, MCP servers, channels, knowledge pipeline, project store.

**Entire section must be replaced** with a description of how bootstrap.py works.

### 3.6 Phase Table (§7) — Stale Entries

- PX (Bootstrap/Assembly) marked "🚨 Critical" — now done
- "Critical path" statement at bottom is stale

### 3.7 Data Flow §5.2 — Label Stale

§5.2 is labeled "Target (after bootstrap, task #263)" — bootstrap is done, so this is now the **current** data flow, not a target.

## 4. Recommendation (.95 confidence)

Full rewrite of sections 3, 4.3, 4.4, 5.2, 6, 7. One task, not multiple — sections are interdependent and a single writer pass ensures consistency.

**Risk:** Low. This is documentation, fully reversible, no code changes.

**Sections to rewrite:**

- §3: Add planning/, projects/, safety/, bootstrap.py; update all file listings
- §4.3: Add 7 missing toolsets; mark all as wired; remove "not wired" markers
- §4.4: Update to 8 agents with correct names and roles
- §4.6: Update knowledge file count (23 not 14); add new subsystems (bookmarks, sources, refresh, query service)
- §5.2: Relabel as "Current" data flow (not target)
- §6: Replace "Assembly Gap" with "Bootstrap Layer" — describe bootstrap.py
- §7: Update PX status to Done; update critical path statement

**Scope note for §2 diagram:** The ASCII diagram in §2 also has stale items ("5 agent defs", "Knowledge pipeline (not wired yet)"). Writer should update those references while rewriting neighboring sections.

## 5. Follow-up Tasks

Single task — the existing #462 covers the full scope. No additional tasks needed. The AC already specifies exactly the right sections. Add §4.6 and §5.2 to the scope (minor additions identified during this research).
