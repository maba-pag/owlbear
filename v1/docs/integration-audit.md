# OwlBear Integration Audit

> **Date:** 2026-03-03  **Status:** Complete

## 1. Module Dependency Map

```
bearclaw/cli ──→ auth, config, memory, tools.browser, tools.github_api, projects, bootstrap, daemon
bootstrap ─────→ core (all), channels.cli, memory, projects, providers, tools (15+), safety, skills
daemon ────────→ core.errors, providers.copilot
core/errors ───→ core.command_guard ⚠ inverted
safety/gate ───→ channels.slack_templates ⚠ cross-module
memory/knowledge/refresh ──→ tools.browser ⚠ upward dependency
```

## 2. Interface Findings

| ID | Sev | Title | Affected | Recommendation |
|---|---|---|---|---|
| INT-01 | CRIT | Broken voice channel import | `bootstrap.py` L232 | Change import to `owlbear.voice.channel` — current `owlbear.channels.voice` doesn't exist, crashes at runtime |
| INT-02 | HIGH | 2× BGE-M3 model load in bootstrap | `bootstrap.py` | `_build_knowledge_toolset` and `_build_bookmark_toolset` each create `BgeM3EmbeddingProvider` (~3 GB), QdrantVectorStore, GraphStore, IngestPipeline independently. Extract shared `_build_knowledge_core()` |
| INT-03 | HIGH | 3 documented features never wired | `core/escalation.py`, `memory/error_journal.py`, `memory/consolidation.py` | EscalationHook, ErrorJournal, MemoryConsolidator implemented but never instantiated in bootstrap. Wire or remove from docs |
| INT-04 | HIGH | KnowledgeSourceToolset dead | `tools/knowledge_source.py` | Never built in `build_toolsets()`. Agents can't manage knowledge sources. Wire or document CLI-only |
| INT-05 | HIGH | Untyped hook payloads | `core/hooks.py` | `Handler = Callable[[object], object]` — no schema per event. POST_TOOL_USE shape differs between HookedToolset and ApprovalGateToolset. Define TypedDict per event |
| INT-06 | HIGH | ChannelPlugin too narrow | `channels/base.py` | Protocol has only `name/send/receive`. `send_file` (CLI), `send_blocks/send_image` (Slack) are duck-typed via `hasattr`. Define `RichChannelPlugin` or split protocols |
| INT-07 | MED | memory → tools upward dep | `memory/knowledge/refresh.py` | Imports `tools.browser.crawl_config` and `tools.browser.integration`. Inject crawl function as callback instead |
| INT-08 | MED | safety → Slack coupling | `safety/gate.py` L30 | Top-level `from channels.slack_templates import format_approval_blocks`. Move behind `hasattr` check with lazy import |
| INT-09 | MED | Inverted error dependency | `core/errors.py` L27 | Imports `BlockedCommandError` from `command_guard`. Move exception to `errors.py` or use base class matching |
| INT-10 | MED | 7 empty `__init__.py` | auth, planning, projects, providers, safety, tools, tools/browser | No public API surface. Add re-exports to at least auth, projects, providers, safety |
| INT-11 | MED | knowledge over-exports | `memory/knowledge/__init__.py` | 35+ symbols including `init_db`, `compute_content_hash`, `IngestPipeline`. Target ≤15 public re-exports |
| INT-12 | MED | Incomplete alias map | `bootstrap.py` `build_agent_registry()` | Missing: bookmark, visual_feedback, knowledge_source, project. Agent defs referencing these fail |
| INT-13 | MED | CLI refresh always errors | `bearclaw/cli.py` | `_make_refresh_orchestrator()` raises `NotImplementedError`. Implement or remove command |
| INT-14 | MED | Dead knowledge modules | `knowledge/dedup.py`, `knowledge/reranker.py` | Never imported anywhere. Wire into pipeline or delete |
| INT-15 | LOW | Scattered model defaults | bootstrap, agent_registry | `"gpt-4o"` hardcoded in 3+ places. Derive from `OwlBearSettings.chat_model` |
| INT-16 | LOW | Private-attr patching | `bootstrap.py`, `projects/toolset.py` | `ProjectToolset._agent = agent` (noqa SLF001). Use lazy resolver callback |
| INT-17 | LOW | Slack missing send_file | `channels/slack.py` | `ScreenshotService.deliver` tries `send_file`, silently skips on Slack. Add via `files_upload_v2` |
| INT-18 | LOW | BrowserConfig not in settings | `tools/browser/config.py` | Not configurable via `OWLBEAR_` env vars. Nest into OwlBearSettings |

### Key Details

**INT-01:** `create_channel("voice")` does `from owlbear.channels.voice import VoiceChannel` — no such module. `VoiceChannel` lives at `owlbear.voice.channel`.

**INT-05 payload shapes:**

| Event | Shape(s) |
|---|---|
| PRE_TOOL_USE | `{"tool_name", "args"}` |
| POST_TOOL_USE | `{"tool_name", "result"}` (HookedToolset) or `{"tool_name", "event_type", "approval_required"}` (Gate) |
| ON_ERROR | `{"error", "prompt"}` or `{"error", "tool_name", "attempt"}` |

**INT-06 channel method matrix:**

| Method | CLI | Slack | Voice | Protocol? |
|---|---|---|---|---|
| send_file | ✅ | ❌ | ❌ | ❌ |
| send_blocks | ❌ | ✅ | ❌ | ❌ |
| send_image | ❌ | ✅ | ❌ | ❌ |

## 3. Integration Risk Areas

| Risk | Severity | Impact |
|---|---|---|
| Voice channel crashes at runtime | Critical | Any `channel_name="voice"` call fails |
| 2× BGE-M3 model load (~6 GB) | High | OOM on laptops <16 GB RAM |
| 3 documented features never wired | High | Docs promise capabilities that don't exist |
| Hook payloads untyped | High | Subtle bugs when shapes diverge across emitters |
| memory → tools dependency | Medium | Cannot isolate knowledge subsystem |
| CLI refresh command broken | Medium | User-facing always errors |
| 4 dead knowledge modules | Medium | Maintenance burden on unused code |

## 4. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Fix broken voice channel import in bootstrap" --priority critical --tags "config,phase-12" --description "bootstrap.py L232 imports owlbear.channels.voice (doesn't exist). Change to owlbear.voice.channel. INT-01."
kanban\kanban-md.exe create "Deduplicate knowledge infra in bootstrap" --priority needed --tags "config,phase-12" --description "Extract shared _build_knowledge_core() — avoid 2× BgeM3/Qdrant/GraphStore. INT-02."
kanban\kanban-md.exe create "Wire EscalationHook, ErrorJournal, MemoryConsolidator" --priority needed --tags "config,hooks,phase-12" --description "Three documented features never instantiated in bootstrap. INT-03."
kanban\kanban-md.exe create "Wire KnowledgeSourceToolset in bootstrap" --priority important --tags "tooling,phase-12" --description "Implemented but never registered in build_toolsets(). INT-04."
kanban\kanban-md.exe create "Define TypedDict payloads for hook events" --priority important --tags "hooks,phase-12" --description "Replace Handler=Callable[[object],object] with typed payloads. INT-05."
kanban\kanban-md.exe create "Extend ChannelPlugin protocol" --priority important --tags "channels,phase-12" --description "send_file/send_blocks/send_image duck-typed. Define RichChannelPlugin. INT-06."
kanban\kanban-md.exe create "Break memory→tools upward dependency" --priority important --tags "config,phase-12" --description "refresh.py imports tools.browser. Inject crawl as callback. INT-07."
kanban\kanban-md.exe create "Lazy-import slack_templates in safety/gate.py" --priority important --tags "safety,phase-12" --description "Move behind hasattr check. INT-08."
kanban\kanban-md.exe create "Move BlockedCommandError to core/errors.py" --priority nice-to-have --tags "config,phase-12" --description "Eliminate inverted dep. INT-09."
kanban\kanban-md.exe create "Add re-exports to empty __init__.py" --priority nice-to-have --tags "config,phase-12" --description "auth/projects/providers/safety have empty __init__. INT-10."
kanban\kanban-md.exe create "Trim knowledge __init__.py to ≤15 exports" --priority nice-to-have --tags "config,phase-12" --description "Currently 35+ symbols. INT-11."
kanban\kanban-md.exe create "Complete agent registry alias map" --priority nice-to-have --tags "config,phase-12" --description "Missing: bookmark, visual_feedback, knowledge_source, project. INT-12."
kanban\kanban-md.exe create "Fix or remove CLI knowledge-source refresh" --priority important --tags "cli,phase-12" --description "Raises NotImplementedError. INT-13."
kanban\kanban-md.exe create "Remove or wire dedup/reranker modules" --priority nice-to-have --tags "tooling,phase-12" --description "Dead code — never imported. INT-14."
```

## 5. Sources

| Source | What | Where Used |
|---|---|---|
| OwlBear codebase | All `__init__.py`, bootstrap, config, all module files | This audit |
| PydanticAI docs | AbstractToolset/FunctionToolset/WrapperToolset patterns | Protocol analysis |
| Python typing docs | Protocol, runtime_checkable, TypedDict | Recommendations |
