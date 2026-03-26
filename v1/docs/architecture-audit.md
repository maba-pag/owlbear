# Architecture and Design Audit — OwlBear

> **Date:** 2026-03-03 **Status:** Complete

## Executive Summary

OwlBear's architecture is fundamentally sound. The system follows a clean composition-root pattern with a procedural `bootstrap()` function wiring together well-separated modules. The channel abstraction via `ChannelPlugin` protocol, the hook-based lifecycle system via `HookRegistry`, and the consistent `FunctionToolset` subclass pattern for tools all demonstrate good design principles. The delegation system with depth-bounded recursion and the error classification taxonomy (`ErrorCategory` + `classify_error()`) are particularly well-executed.

However, the codebase has accumulated several structural debts. The most concerning are: duplicate SQLite connections and parallel infrastructure in bootstrap (knowledge vs. bookmark toolsets create independent instances of the same components), pervasive private-attribute mutation (`SLF001` suppressions) indicating missing public APIs, and a latent import error in the voice channel factory. The bootstrap module itself is growing into a monolith (~894 lines) and the `build_toolsets` function has accrued too many responsibilities.

The hook system's type safety is weak — handlers accept `Callable[[object], object]` with no schema enforcement, and several hooks have signature mismatches that require closure wrappers. The channel protocol is under-specified, forcing runtime `hasattr` checks in downstream consumers. These issues are individually manageable but collectively signal that interfaces need tightening as the system grows.

## 1. Layering and Separation of Concerns

### ARC-01 — CRITICAL: Duplicate Knowledge Infrastructure in Bootstrap

**Description:** `_build_knowledge_toolset()` (line 287) and `_build_bookmark_toolset()` (line 379) each independently call `sqlite3.connect()` to the same `knowledge.db`, create separate `GraphStore`, `BgeM3EmbeddingProvider`, `QdrantVectorStore`, and `IngestPipeline` instances. This means: (a) two SQLite connections with independent transaction visibility, (b) two BGE-M3 model loads (~3 GB RAM each), (c) two Qdrant client instances to the same storage path.

**Affected files:** `src/owlbear/bootstrap.py` (lines 287–370, 379–450)

**Recommendation:** Extract a shared `KnowledgeInfrastructure` dataclass that holds the connection, stores, and providers. Build it once, pass it to both `_build_knowledge_toolset()` and `_build_bookmark_toolset()`. This eliminates duplicate resource allocation and ensures transactional consistency.

---

### ARC-02 — HIGH: Voice Channel Import Path Error

**Description:** `create_channel()` in bootstrap.py imports `from owlbear.channels.voice import VoiceChannel` (line 233), but the `VoiceChannel` class lives at `src/owlbear/voice/channel.py` — there is no `channels/voice.py` module. The `channels/` directory contains only `base.py`, `cli.py`, `slack.py`, and Slack helpers. This is a latent `ImportError` that fires at runtime when `channel_name="voice"`.

**Affected files:** `src/owlbear/bootstrap.py` (line 233), `src/owlbear/voice/channel.py`

**Recommendation:** Fix the import to `from owlbear.voice.channel import VoiceChannel`, or create `channels/voice.py` as a thin re-export. The former is cleaner.

---

### ARC-03 — MEDIUM: VoiceChannel Lives Outside channels/ Package

**Description:** All channel adapters (`CLIChannel`, `SlackChannel`) live under `channels/` except `VoiceChannel`, which is under `voice/`. The `voice/` package contains both the channel adapter *and* the STT/TTS implementation details. This conflates the I/O abstraction layer with the voice processing layer.

**Affected files:** `src/owlbear/voice/channel.py`, `src/owlbear/channels/`

**Recommendation:** Either move `VoiceChannel` to `channels/voice.py` (importing STT/TTS from `voice/`), or accept the current layout and fix ARC-02. The first option keeps channel adapters co-located.

---

### ARC-04 — MEDIUM: No SQLite Connection Lifecycle Management

**Description:** Knowledge subsystem SQLite connections are created in bootstrap helper functions but never closed. There's no cleanup hook, no context manager usage, and the `BootstrapResult.cleanup` list doesn't include connection closure. On daemon shutdown, connections rely on GC finalization.

**Affected files:** `src/owlbear/bootstrap.py` (lines 298, 403)

**Recommendation:** Track open connections on `BootstrapResult.cleanup` or use a connection-manager class that participates in shutdown. At minimum, add `conn.close()` lambdas to the cleanup list.

## 2. Module Coupling

### ARC-05 — HIGH: Pervasive Private Attribute Mutation (10 SLF001 Suppressions)

**Description:** The codebase has 10 `# noqa: SLF001` suppressions where modules reach into other modules' private attributes. Key violations:

| Location | What's mutated | Why |
|---|---|---|
| `bootstrap.py:880` | `agent._deps.agent_registry` | Injecting registry after construction |
| `bootstrap.py:758` | `inner._agent = agent` | Patching ProjectToolset placeholder |
| `projects/toolset.py:152–154` | `inner._workspace_root`, `inner._root` | Project switch updates |
| `delegation.py:97` | `ctx.deps._delegation_depth` | Reading depth counter |
| `knowledge/dedup.py:124–144` | `graph._conn` (5 occurrences) | Direct SQL through GraphStore's connection |

**Affected files:** `bootstrap.py`, `projects/toolset.py`, `core/delegation.py`, `memory/knowledge/dedup.py`

**Recommendation:** Add public APIs for each: `OwlBearDeps.set_agent_registry()`, `OwlBearDeps.delegation_depth` property, `ProjectToolset.bind_agent()`, toolsets should expose `update_workspace_root()`, `GraphStore` should expose a `merge_entities()` method or a `connection` property.

---

### ARC-06 — MEDIUM: `_update_toolset_roots()` is Fragile Duck-Typing

**Description:** `projects/toolset.py:_update_toolset_roots()` walks toolsets and mutates `_workspace_root` and `_root` by `hasattr` check. Adding a new toolset with a differently-named root attribute (e.g., `_base_path`) breaks silently — the new toolset won't be updated on project switch.

**Affected files:** `src/owlbear/projects/toolset.py` (lines 140–155)

**Recommendation:** Define a `WorkspaceAware` protocol with a public `update_workspace(new_root: Path)` method. Toolsets that need workspace switching implement it explicitly.

---

### ARC-07 — LOW: Approval Gate Checks Channel Capabilities at Runtime

**Description:** `ApprovalGateToolset.call_tool()` uses `hasattr(self.channel, "send_blocks")` to decide between Slack Block Kit and plain text approval prompts. This is runtime duck-typing that bypasses the `ChannelPlugin` protocol.

**Affected files:** `src/owlbear/safety/gate.py` (line 105)

**Recommendation:** Either extend `ChannelPlugin` with an optional `send_blocks` method (default no-op), or use a `RichChannel` protocol for channels supporting structured output.

## 3. Interface Design

### ARC-08 — MEDIUM: Hook Handler Type Is Untyped

**Description:** `Handler = Callable[[object], object]` provides no type safety. Different hook events expect different payload shapes: `ON_MESSAGE` wants `{"prompt": str}`, `PRE_TOOL_USE` wants `{"tool_name": str, "args": dict}`, `ON_ERROR` wants `{"error": Exception, "prompt": str}`. Handlers receive raw `object` and must defensively cast.

**Affected files:** `src/owlbear/core/hooks.py` (line 18)

**Recommendation:** Define typed payload models per event (e.g., `ToolUsePayload`, `ErrorPayload`) and use `TypeVar` or overloads. Even a simpler step — using `dict[str, Any]` instead of `object` — improves ergonomics.

---

### ARC-09 — MEDIUM: NotificationHook Signature Mismatch

**Description:** `NotificationHook.__call__` takes `(self, event: HookEvent, data: object)` (2 args), but `HookRegistry.emit` invokes handlers with a single `data` argument. This mismatch is papered over by `_make_handler()` which creates a closure. Other hooks (`CommandSafetyGuard`, `SubagentVerificationHook`) follow the single-arg convention directly.

**Affected files:** `src/owlbear/core/notification_hook.py` (lines 99, 131–138)

**Recommendation:** Refactor `NotificationHook.__call__` to accept `(self, data: object)` like all other hooks, extracting event type from the data dict or from registration context.

---

### ARC-10 — MEDIUM: ChannelPlugin Protocol Is Under-Specified

**Description:** `ChannelPlugin` defines only `name`, `send`, `receive`. But `SlackChannel` adds `send_blocks`, `send_file`, `register_action`, `channel_id` property, and `thread_registry`. The `CLIChannel` adds `send_file`. Consumers check for extended capabilities at runtime.

**Affected files:** `src/owlbear/channels/base.py`, `src/owlbear/safety/gate.py`, `src/owlbear/channels/slack.py`, `src/owlbear/channels/cli.py`

**Recommendation:** Define a `RichChannelPlugin(ChannelPlugin)` protocol for channels that support structured messages, or add optional methods with default implementations to the base protocol.

---

### ARC-11 — LOW: `_safe_path` Duplicated Across Two Toolsets

**Description:** Identical path-traversal guard logic exists in both `FileToolset._safe_path()` and `KnowledgeToolset._safe_path()` — same null-byte check, same resolve-and-check pattern, same error message format.

**Affected files:** `src/owlbear/tools/filesystem.py` (lines 52–66), `src/owlbear/tools/knowledge.py` (lines 81–96)

**Recommendation:** Extract to a shared `sandbox_path(root: Path, user_path: str) -> Path` utility function.

## 4. Bootstrap and Assembly

### ARC-12 — MEDIUM: Bootstrap Is a Growing Monolith (894 Lines)

**Description:** `bootstrap.py` handles project resolution, channel creation, hook assembly, toolset construction (including 5 conditional subsystems), MCP registry, agent registry, session/context/tracker setup, agent construction, and post-construction patching. It's the longest file in the project and accumulates complexity with each new subsystem.

**Affected files:** `src/owlbear/bootstrap.py`

**Recommendation:** Split into focused modules: `bootstrap/hooks.py`, `bootstrap/toolsets.py`, `bootstrap/knowledge.py`, `bootstrap/registry.py`, with a thin `bootstrap/__init__.py` orchestrator. Each module exports a single `build_*` function.

---

### ARC-13 — MEDIUM: `build_toolsets` Has Two Concerns (C901 Suppression)

**Description:** `build_toolsets()` (line 498, ~100 lines) both constructs toolsets *and* applies cross-cutting wrapping (HookedToolset, ApprovalGateToolset). The approval-gate section uses string-matching on class names (`_destructive = {"GitLocalToolset", "TerminalToolset", "GitHubToolset"}`) — a magic-string pattern that breaks if a class is renamed.

**Affected files:** `src/owlbear/bootstrap.py` (lines 498–620)

**Recommendation:** Separate toolset construction from wrapping. Use a marker attribute or registration-time flag (e.g., `destructive=True`) instead of string-matching class names.

---

### ARC-14 — MEDIUM: Post-Construction Patching Pattern

**Description:** `bootstrap()` creates a placeholder object for `ProjectToolset`, then patches the real agent reference after construction via `_patch_project_toolset_agent()`. Similarly, `agent._deps.agent_registry` is set after agent construction. This two-phase initialization creates temporal coupling — code that runs between construction and patching sees incomplete state.

**Affected files:** `src/owlbear/bootstrap.py` (lines 738–758, 878–880)

**Recommendation:** For `agent_registry`: accept it as a constructor parameter on `OwlBearDeps`. For `ProjectToolset`: use a lazy `property` that reads from a shared registry rather than a patched reference. Or reorder construction to make the agent available earlier.

## 5. Scalability of Design

### ARC-15 — MEDIUM: Tool Resolver Requires Manual Alias Map

**Description:** `build_agent_registry()` (line 659) maintains a hardcoded `_aliases` dict mapping short names to class names. Adding a new toolset requires updating this map — there's no auto-discovery or registration mechanism.

**Affected files:** `src/owlbear/bootstrap.py` (lines 659–700)

**Recommendation:** Have toolsets self-register with a canonical short name (e.g., class attribute `tool_alias = "filesystem"`), or use a decorator-based registry pattern. The alias map becomes derived rather than manually maintained.

---

### ARC-16 — LOW: Agent Definitions Are File-Scanned, Not Registered

**Description:** `AgentRegistry.scan()` globs `*.md` files from a directory. This works for static definitions but doesn't support programmatic agent registration. All agents must be markdown files — no API for dynamic agent creation.

**Affected files:** `src/owlbear/core/agent_registry.py` (lines 90–107)

**Recommendation:** Add a `register(defn: AgentDefinition)` method alongside `scan()` to support both file-based and programmatic agent definitions.

## 6. Design Patterns

### ARC-17 — INFO: Consistent FunctionToolset Pattern

**Description:** All 12+ toolsets follow a clean, consistent pattern: subclass `FunctionToolset`, accept dependencies via constructor, register tools in `_register_tools()`, each tool is a method with proper docstring and type hints. The WrapperToolset chain (`HookedToolset` → `ApprovalGateToolset` → inner) is a well-applied decorator pattern.

**Affected files:** All `src/owlbear/tools/*.py`

**Recommendation:** None — this is good design. Document the pattern so new contributors follow it.

---

### ARC-18 — INFO: Error Classification Taxonomy

**Description:** `ErrorCategory` (TRANSIENT / AUTH / PERMANENT / TOOL_SEMANTIC) with `classify_error()` as a pure function is clean, testable, and used consistently across the daemon loop, HookedToolset retry, and delegation error handling.

**Affected files:** `src/owlbear/core/errors.py`

**Recommendation:** None — solid pattern.

## 7. Single Responsibility

### ARC-19 — MEDIUM: `ContextInjectionHook` Blocks Event Loop

**Description:** `ContextInjectionHook._run_kanban()` calls `subprocess.run()` synchronously inside an async hook handler. Since `HookRegistry.emit()` awaits handlers, this blocks the event loop for the duration of the kanban command.

**Affected files:** `src/owlbear/core/context_hook.py` (lines 105–120)

**Recommendation:** Use `asyncio.create_subprocess_exec()` instead of `subprocess.run()`, consistent with how `TerminalToolset` and `GitLocalToolset` execute subprocesses.

---

### ARC-20 — LOW: Validator Role Policy Is Incomplete

**Description:** `VALIDATOR_POLICY` only denies `write_file` and `create_file`. It doesn't restrict `run_command`, `git_commit`, `git_push`, or `browser_type` — a validator agent could still execute arbitrary shell commands, commit code, or interact with web pages.

**Affected files:** `src/owlbear/core/roles.py` (lines 59–67)

**Recommendation:** Expand the denied set to include `run_command`, `git_commit`, `git_push`, `git_add`, `browser_click`, `browser_type` — or invert the model to an allow-list for validators.

## 8. Error Boundaries

### ARC-21 — MEDIUM: Dual Error Handling on ON_ERROR Events

**Description:** The daemon loop (`run_daemon`) catches exceptions from `agent.turn()` and calls `_recover_from_error()`. However, `agent.turn()` also emits `ON_ERROR` via hooks before re-raising. If `EscalationHook` is registered, the user gets prompted *twice* — once by the hook and once by the daemon recovery. The hook handler runs first (inside `turn()`), then the daemon's `_recover_from_error` runs after the exception propagates.

**Affected files:** `src/owlbear/daemon.py` (lines 243–322), `src/owlbear/core/agent.py` (lines 133–136), `src/owlbear/core/escalation.py`

**Recommendation:** Choose one error-handling authority. Either remove the escalation from the hook and keep it in the daemon loop only, or have the hook set a flag that `_recover_from_error` checks before acting.

---

### ARC-22 — LOW: Broad Exception Swallowing in Bootstrap

**Description:** Every optional subsystem in bootstrap (`_build_knowledge_toolset`, `_build_bookmark_toolset`, `_build_web_search_toolset`, SkillRegistry, GitHubToolset) catches `Exception` and silently continues with a WARNING log. While this makes bootstrap resilient, it can mask configuration errors (e.g., wrong DB path, invalid API key) that the user would want to know about immediately.

**Affected files:** `src/owlbear/bootstrap.py` (lines 360, 450, 468, 536, 548)

**Recommendation:** Log at ERROR level (not WARNING) and include the exception type/message in a startup summary. Consider a `--strict` mode that raises instead of swallowing.

---

## Findings Summary

| ID | Severity | Category | Title |
|---|---|---|---|
| ARC-01 | CRITICAL | Layering | Duplicate knowledge infrastructure in bootstrap |
| ARC-02 | HIGH | Layering | Voice channel import path error |
| ARC-05 | HIGH | Coupling | 10 private-attribute mutations (SLF001) |
| ARC-03 | MEDIUM | Layering | VoiceChannel lives outside channels/ |
| ARC-04 | MEDIUM | Layering | No SQLite connection lifecycle management |
| ARC-06 | MEDIUM | Coupling | `_update_toolset_roots()` fragile duck typing |
| ARC-08 | MEDIUM | Interfaces | Hook handler type is untyped |
| ARC-09 | MEDIUM | Interfaces | NotificationHook signature mismatch |
| ARC-10 | MEDIUM | Interfaces | ChannelPlugin protocol under-specified |
| ARC-12 | MEDIUM | Bootstrap | Bootstrap is a 894-line monolith |
| ARC-13 | MEDIUM | Bootstrap | `build_toolsets` has two concerns |
| ARC-14 | MEDIUM | Bootstrap | Post-construction patching pattern |
| ARC-15 | MEDIUM | Scalability | Tool resolver requires manual alias map |
| ARC-19 | MEDIUM | SRP | ContextInjectionHook blocks event loop |
| ARC-21 | MEDIUM | Errors | Dual error handling on ON_ERROR |
| ARC-07 | LOW | Coupling | Approval gate runtime capability check |
| ARC-11 | LOW | Interfaces | `_safe_path` duplicated in two toolsets |
| ARC-16 | LOW | Scalability | No programmatic agent registration |
| ARC-20 | LOW | SRP | Validator role policy incomplete |
| ARC-22 | LOW | Errors | Broad exception swallowing in bootstrap |
| ARC-17 | INFO | Patterns | Consistent FunctionToolset pattern |
| ARC-18 | INFO | Patterns | Error classification taxonomy |

## Follow-up Tasks

```
kanban\kanban-md.exe create "Fix duplicate knowledge infrastructure in bootstrap" --priority critical --status backlog --tags "phase-13,config,scope:core" --body "ARC-01: _build_knowledge_toolset and _build_bookmark_toolset create independent SQLite connections, embedding providers, and vector stores to the same DB. Extract shared KnowledgeInfrastructure dataclass built once and passed to both. See docs/architecture-audit.md §ARC-01. AC: single SQLite connection, single BgeM3 instance, single QdrantVectorStore shared across knowledge and bookmark toolsets."

kanban\kanban-md.exe create "Fix voice channel import path in bootstrap" --priority needed --status backlog --tags "phase-13,config,scope:core" --body "ARC-02: create_channel() imports from owlbear.channels.voice but VoiceChannel lives at owlbear.voice.channel. Fix import to correct path. See docs/architecture-audit.md §ARC-02. AC: bearclaw run --channel voice starts without ImportError."

kanban\kanban-md.exe create "Add public APIs to eliminate SLF001 suppressions" --priority needed --status backlog --tags "phase-13,scope:core" --body "ARC-05: 10 instances of private attribute mutation across bootstrap, delegation, projects/toolset, knowledge/dedup. Add: OwlBearDeps.set_agent_registry(), delegation_depth property, ProjectToolset.bind_agent(), toolset update_workspace_root(), GraphStore.merge_entities(). See docs/architecture-audit.md §ARC-05. AC: zero SLF001 suppressions remain."

kanban\kanban-md.exe create "Extract shared sandbox_path utility from FileToolset and KnowledgeToolset" --priority nice-to-have --status backlog --tags "phase-13,tooling,scope:core" --body "ARC-11: Identical _safe_path logic duplicated in FileToolset and KnowledgeToolset. Extract to owlbear.tools.sandbox.sandbox_path(). See docs/architecture-audit.md §ARC-11. AC: single implementation, both toolsets use it, tests pass."

kanban\kanban-md.exe create "Split bootstrap.py into focused submodules" --priority important --status backlog --tags "phase-13,config,scope:core" --body "ARC-12/13: bootstrap.py is 894 lines with build_toolsets having 2 concerns (C901). Split into bootstrap/ package with hooks.py, toolsets.py, knowledge.py, registry.py. Use marker attributes instead of class-name strings for destructive toolset detection. See docs/architecture-audit.md §ARC-12, ARC-13. AC: bootstrap.py < 200 lines, no C901 suppression, no magic class-name strings."

kanban\kanban-md.exe create "Fix dual error handling in daemon + ON_ERROR hook" --priority important --status backlog --tags "phase-13,scope:core" --body "ARC-21: EscalationHook and _recover_from_error both handle errors, causing double user prompts. Choose one authority. See docs/architecture-audit.md §ARC-21. AC: user sees exactly one error prompt per failure, not two."

kanban\kanban-md.exe create "Fix ContextInjectionHook blocking event loop" --priority important --status backlog --tags "phase-13,scope:core" --body "ARC-19: _run_kanban() uses subprocess.run() synchronously in an async handler. Replace with asyncio.create_subprocess_exec(). See docs/architecture-audit.md §ARC-19. AC: hook handler is fully async, no sync subprocess calls."

kanban\kanban-md.exe create "Add SQLite connection lifecycle to bootstrap cleanup" --priority important --status backlog --tags "phase-13,config,scope:core" --body "ARC-04: Knowledge SQLite connections created in bootstrap but never closed. Add conn.close() to BootstrapResult.cleanup. See docs/architecture-audit.md §ARC-04. AC: connections are closed on daemon shutdown."

kanban\kanban-md.exe create "Define WorkspaceAware protocol for toolset root updates" --priority nice-to-have --status backlog --tags "phase-13,scope:core" --body "ARC-06: _update_toolset_roots() uses fragile hasattr duck-typing. Define WorkspaceAware protocol with update_workspace(root). See docs/architecture-audit.md §ARC-06. AC: all workspace-dependent toolsets implement protocol, no hasattr checks."

kanban\kanban-md.exe create "Expand validator role policy denied tools" --priority nice-to-have --status backlog --tags "phase-13,agent,scope:core" --body "ARC-20: VALIDATOR_POLICY only denies write_file/create_file. Add run_command, git_commit, git_push, git_add, browser_click, browser_type. See docs/architecture-audit.md §ARC-20. AC: validator agents cannot execute shell commands or destructive git ops."
```
