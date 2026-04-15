# V1 Feature Inventory — Complete Preservation Catalog

> **Purpose:** Comprehensive catalog of every feature, idea, and capability from OwlBear v1 (PydanticAI-based standalone daemon) before the v1/ directory is deleted. Features are tagged for v2 feasibility (VS Code Copilot Chat + MCP servers).
>
> **Source data:** v1/src/ (43 Python modules), v1/tests/ (250+ test files), .owlbear/kanban/v1-archive/ (999 kanban tasks), v1/docs/ (400+ research docs), v1 agent definitions (9 agents).
>
> **Date:** 2026-04-10

---

## Feasibility Legend

| Tag | Meaning |
|-----|---------|
| `v2:exists` | Already implemented in v2 |
| `v2:feasible` | Can be built in v2 (VS Code Copilot Chat + MCP architecture) |
| `v2:partial` | Partially exists in v2, needs extension |
| `v2:blocked` | Not feasible in VS Code Copilot Chat (requires standalone process) |
| `v2:deferred` | Feasible but depends on gh copilot CLI maturity |
| `v2:idea` | Good idea worth evaluating for v2 priority |

---

## 1. AGENT FRAMEWORK

### 1.1 Agent Lifecycle & Orchestration

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 1 | **OwlBearAgent turn lifecycle** | Turn loop: load session → inject board/knowledge context → run LLM → save → record usage → check budget. Per-turn context injection with multiple data sources concatenated into system prompt. | `v2:blocked` |
| 2 | **Agent definition format (YAML+MD)** | Agents defined in markdown files with YAML frontmatter: name, description, role, tools, skills, system_prompt. Human-readable, parsed at load time. | `v2:exists` |
| 3 | **Agent registry & lazy instantiation** | Registry scans a directory, lazy-loads agents with role-based tool filtering. Graceful tool unavailability (skips with warning, never aborts). | `v2:partial` |
| 4 | **Inter-agent delegation** | `delegate_to_agent` tool with immutable DispatchContext. Depth tracking (MAX_DEPTH=5), child deps creation. All errors returned as JSON ToolError for LLM feedback. | `v2:partial` |
| 5 | **Role-based access control (RBAC)** | Two roles: BUILDER (full access), VALIDATOR (allow-list of ~25 read-only tools). Applied at agent construction via `apply_role_policy()`. | `v2:feasible` |
| 6 | **Rigor profiles** | Configurable quality-vs-speed presets per task: LEAN (no review, smoke tests, 15 turns), STANDARD (review, full TDD, 30 turns), THOROUGH (review, full TDD, 50 turns). Selected via `rigor:*` task tag. | `v2:feasible` |
| 7 | **Budget enforcement** | Token/cost budget tracking with 80% warning, 100% hard stop. Budget limit in USD. Agents notified before exceeding. | `v2:feasible` |
| 8 | **Context condenser** | LLM-based history summarization when message count exceeds threshold. Preserves first N + tail, summarizes middle. Tool-call/return boundary alignment kept together during condensation. | `v2:blocked` |
| 9 | **Board context injection** | TTL-cached kanban board state injected into agent system prompt each turn. Force-refresh capability. Graceful degradation on subprocess failure. | `v2:partial` |

### 1.2 Agent Roles (9 Specialized Agents)

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 10 | **Orchestrator agent** | Central coordinator with 8-spec intent router: plan→kanban-planner, build→builder, research→researcher, review→reviewer, docs→writer, close→auditor. Delegation depth=5. | `v2:exists` |
| 11 | **Builder agent** | TDD-mandatory workflow: write failing tests → implement minimum → refactor → full suite + linter. Functions ≤50 lines, type hints required, ≥90% coverage target. | `v2:exists` |
| 12 | **Reviewer agent** | Read-only quality verification: examine every changed file, run pytest+ruff, per-AC evidence with file/line references. PASS/FAIL verdict. Never modifies code. | `v2:exists` |
| 13 | **Architect agent** | Backlog→todo gate: verify research completeness, refine AC (testable+specific), check architecture fit, split/merge tasks. Reject to ideation with block reason. | `v2:exists` |
| 14 | **Researcher agent** | Read-only investigation: search prior art (2+ sources), evaluate alternatives (comparison tables), structured findings with source attribution. | `v2:exists` |
| 15 | **Kanban planner agent** | Entry gate for task creation: clarify idea → elicit requirements → testable AC → decompose to atomic tasks → map dependencies → assign priority. | `v2:exists` |
| 16 | **Writer (doc-writer) agent** | Documentation gate: identify what changed → check docs-gate criteria → update README/instructions/docstrings. Only modifies docs, never source. | `v2:exists` |
| 17 | **Auditor agent** | Exit gate (done→archived): verify AC with specific evidence, score confidence per AC line (0.0–1.0). Archive at ≥0.95, reject <0.95. Never modifies code. | `v2:exists` |
| 18 | **Curator agent** | Knowledge maintenance: deduplicate graph entries, consolidate near-duplicates, signal assessment (HIGH/MEDIUM/LOW/NOISE/CONFLICT), never delete reviewed lessons without confirmation. | `v2:exists` |

---

## 2. HOOK SYSTEM

### 2.1 Lifecycle Hooks

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 19 | **Hook registry (11 event types)** | Centralized event bus: SESSION_START/END, PRE/POST_TOOL_USE, ON_MESSAGE, ON_ERROR, SUBAGENT_COMPLETE, TASK_COMPLETE, QUESTION_PENDING, BUDGET_WARNING, DAEMON_STARTUP. Async dispatch with handler isolation. | `v2:blocked` |
| 20 | **Auto-lint hook** | POST_TOOL_USE: automatically runs `ruff check --fix` on edited `.py` files. Graceful degradation if ruff unavailable. | `v2:blocked` |
| 21 | **Command safety guard** | PRE_TOOL_USE: regex-based blocklist for dangerous commands (rm -rf, git push -f, pip install, .env access, etc.). Optional audit sink callback. | `v2:blocked` |
| 22 | **Test verification hook** | SESSION_END: runs pytest suite, parses passed/failed counts via regex, stores results. 120s timeout. | `v2:blocked` |
| 23 | **Subagent verification hook** | SUBAGENT_COMPLETE: verifies file existence + runs targeted pytest on deliverables. Stores per-file and per-test verification results. | `v2:blocked` |
| 24 | **Notification hook (tiered)** | Two-tier notification: urgent events (errors, budget, questions) → Slack+sound+bell; info events (task_complete) → bell only. Backend chain: first success stops. | `v2:blocked` |
| 25 | **Retrospective hook** | TASK_COMPLETE: generates structured retrospective findings (what_worked, what_failed, error_patterns, reusable_patterns) and ingests into knowledge graph. Eligibility gates: rejection count + priority. | `v2:idea` |
| 26 | **Session memory hook** | SESSION_END: LLM-summarizes conversation, persists to `.owlbear/session-memory.md`. | `v2:feasible` |
| 27 | **Lessons injection hook** | SESSION_START: reads curated lesson files from `.owlbear/lessons/`, concatenates within token budget, injects into agent context. | `v2:feasible` |
| 28 | **Audit map advisory hook** | TASK_COMPLETE: generates advisory markdown artifact for tasks tagged `worker:audit-map`. Background scheduling via supervisor. | `v2:idea` |
| 29 | **Observability hook** | Logs all lifecycle events to JSONL EventStore. Pairs PRE/POST_TOOL_USE for duration tracking. Per-tool stats: call count, error count, avg duration. | `v2:idea` |
| 30 | **Hook reaction router** | Config-driven event→action dispatch: rules match events + optional payload predicates → ordered actions (notify, retry, escalate). Failing actions don't block others. | `v2:blocked` |
| 31 | **Hook worker supervisor** | Bounded-concurrency background task manager with semaphore. Graceful shutdown: cancels all tasks, awaits cleanup. | `v2:blocked` |

### 2.2 Hook Equivalents for v2

> Many v1 hooks ran inside the PydanticAI agent process. In v2 (VS Code Copilot Chat), equivalent behaviors must be implemented as: (a) MCP server tools/resources, (b) agent instruction directives, (c) VS Code extension features, or (d) standalone scripts.

---

## 3. KNOWLEDGE SYSTEM

### 3.1 Data Model & Storage

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 32 | **Entity types** | FILE, FUNCTION, CLASS, DECISION, PATTERN, CONCEPT — typed knowledge graph nodes with importance scoring (0–1). | `v2:exists` |
| 33 | **Relation types** | DEFINES, IMPORTS, DEPENDS_ON, RELATED_TO, IMPLEMENTS, DOCUMENTS, GOVERNED_BY — directed weighted edges. | `v2:exists` |
| 34 | **Knowledge source model** | Registered sources with source_type (URL_LIST, CRAWL, FILE_GLOB), JSON config, enabled flag, priority, refresh tracking. | `v2:exists` |
| 35 | **SQLite schema (v8, migrations v1–v8)** | Tables: documents, entities, edges, chunks, document_status, knowledge_sources, bookmarks, consolidations. Idempotent init. | `v2:exists` |
| 36 | **Scope-based isolation** | All queries support multi-tenant filtering via scope column. Entities, documents, bookmarks, sources all scoped. | `v2:exists` |

### 3.2 Ingestion Pipeline

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 37 | **Full ingestion pipeline** | Async orchestration: intake → delta check → chunk → parallel(embed, extract) → store → background enrichment. | `v2:exists` |
| 38 | **Content intake (file, URL, text)** | Three readers: file (with path sandboxing), URL (with retry on 429/502/503/504), raw text. Returns metadata (source_type, fetched_at). | `v2:exists` |
| 39 | **Recursive text chunker** | Separator hierarchy: `## ` → `### ` → `\n\n` → `\n` → ` `. Configurable target_tokens (512), overlap (50). Hard-cap word-level split. | `v2:exists` |
| 40 | **LLM entity extraction** | PydanticAI structured output: entity name, type, description, importance (0–1), relationships. Graceful failure. Usage tracking. | `v2:exists` |
| 41 | **Delta detection (content hash)** | SHA-256 content hashing. Skip ingestion of unchanged sources. DocumentStore tracks status via document_status table. | `v2:exists` |
| 42 | **Document store (CRUD facade)** | Unified facade: status tracking, chunk CRUD, entity/edge persistence, embedding storage, consolidation marking, cascading delete. | `v2:exists` |

### 3.3 Graph Building & Enrichment

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 43 | **Intra-document graph builder** | LLM-inferred relationships within a single document's extracted entities. Batches large sets (>80) by entity_type. Strong-evidence-only edges. | `v2:exists` |
| 44 | **Inter-document graph builder** | Cross-document relationship inference: embed entities → find similar via vector store → LLM-validate candidate pairs. Cosine threshold 0.70. | `v2:exists` |
| 45 | **Background graph enrichment** | GraphEnricher: schedules intra/inter-doc building as background tasks. Semaphore-bounded concurrency. Cooperative cancellation. Drain/shutdown. | `v2:exists` |

### 3.4 Embeddings & Vector Store

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 46 | **BGE-M3 hybrid embeddings** | 1024-d dense + sparse lexical + ColBERT multi-vector. Thread-safe lazy loading. Idle unloading after timeout (~3GB reclaimed). | `v2:exists` |
| 47 | **Qdrant vector store** | Hybrid retrieval: prefetch + rescore (10x multiplier). Temporal decay scoring (importance-weighted). `:memory:` or filesystem persistence. Deterministic UUID5 point IDs. | `v2:exists` |
| 48 | **VectorStoreProtocol** | Abstract interface: store_embedding, get_embedding, search_similar, delete_embedding. HybridEmbedding and SparseVector types. | `v2:exists` |

### 3.5 Retrieval & Query

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 49 | **Knowledge query service** | Per-turn context injection: embed prompt → search → format within token budget. Similarity threshold filtering. Graceful degradation. | `v2:exists` |
| 50 | **Graph-augmented retrieval** | BFS neighbor expansion from vector search results. Configurable depth, importance sorting, token-budget capping. Kill-switch flag. | `v2:exists` |
| 51 | **Consolidation service** | Reads unconsolidated chunks → batch LLM synthesis → stores cross-document insights. Periodic background scheduling. | `v2:exists` |

### 3.6 Source Management & Bookmarking

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 52 | **Knowledge source CRUD** | Create, get (by id/name), list (enabled, priority-ordered). JSON config serialization. Refresh tracking (last_refreshed_at, last_error). | `v2:exists` |
| 53 | **Refresh orchestrator** | Dispatches refresh by source type: URL_LIST (fetch list), CRAWL (delegate), FILE_GLOB (glob workspace). Delta detection. Priority-ordered refresh_all. | `v2:exists` |
| 54 | **Bookmark pipeline** | URL → extract → evaluate relevance → conditionally ingest → store bookmark. Dedup check. Configurable ingest threshold (0.7). | `v2:exists` |
| 55 | **Source evaluator** | LLM-based relevance scoring (0.0–1.0) against project context. Returns: relevance_score, tags, summary, worth_ingesting. | `v2:exists` |

### 3.7 Cancellation & Lifecycle

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 56 | **Cooperative cancellation** | CancelSignal protocol with LinkedCancelSignal (any-of composition). Threaded through all pipeline stages. Preserves partial results. | `v2:exists` |

---

## 4. TOOLS

### 4.1 File & Terminal Tools

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 57 | **Sandboxed filesystem tools** | 5 tools: read_file (line ranges), write_file, create_file, list_directory, search_files (glob+regex). Path traversal guards (null-byte, resolve, is_relative_to). | `v2:blocked` |
| 58 | **Terminal execution** | run_command with intelligent output truncation (head 60% + tail 40% split). Soft-fail classification for exit code 1. Timeout with kill. | `v2:blocked` |
| 59 | **Hooked toolset wrapper** | PRE/POST_TOOL_USE hook emission around every tool call. Transient retry with exponential backoff (3 attempts, 0.5–10s). Guards for blocking. | `v2:blocked` |

### 4.2 Git & GitHub

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 60 | **Local git toolset** | 7 tools: status (porcelain), diff (working/staged), add, commit (with Co-authored-by), branch, log (oneline), push. Pre-execution hooks on destructive ops. | `v2:blocked` |
| 61 | **GitHub API toolset** | 4 tools: create_pr, list_prs, list_issues, get_issue. Token auth. Transient retry. Owner/repo from git remote. | `v2:blocked` |

### 4.3 Web & Browser

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 62 | **Web search (DuckDuckGo)** | Two tools: `web_search` (DuckDuckGo query) and `web_read` (fetch + trafilatura extract). URL blocklist/allowlist regex. | `v2:blocked` |
| 63 | **Browser automation (Playwright)** | BrowserManager with launch mode + CDP (attach to Edge) mode. Isolated browser context. Accessibility tree snapshots (interactive/text/full filters). | `v2:blocked` |
| 64 | **7 browser action tools** | navigate (URL safety guard), click, type (fill input), select (dropdown), read_text (page/element), screenshot (base64), snapshot (a11y tree). | `v2:blocked` |
| 65 | **Edge CDP launcher** | Find → launch → probe → connect Edge via Chrome DevTools Protocol. PID-based lifecycle. Corporate-locked Windows laptop support. | `v2:blocked` |
| 66 | **Tab title prefix (MutationObserver)** | Maintains `[OwlBear]` prefix on browser tab titles via injected MutationObserver in CDP mode. | `v2:blocked` |
| 67 | **Web crawler (async BFS)** | Async BFS crawl with depth/page limits, robots.txt compliance, rate limiting, content extraction, HTML caching. | `v2:blocked` |
| 68 | **URL safety guard** | Domain blocklist/allowlist regex evaluation. Blocklist overrides allowlist. Configurable patterns. | `v2:feasible` |
| 69 | **Content injection guard** | Scans extracted text for injection attacks. Future-proofing layer. | `v2:feasible` |
| 70 | **Untrusted content wrapping** | Wraps web-extracted text in `<untrusted_web_content>` sentinel tags to prevent prompt injection from fetched content. | `v2:feasible` |

### 4.4 Kanban Tools

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 71 | **Kanban toolset (7 operations)** | list (filters: status/tag/priority/blocked), show (JSON), create, move, edit (body/tags/priority/append), pick, context. Via kanban-md subprocess. | `v2:exists` |

### 4.5 Knowledge & Memory Tools

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 72 | **Knowledge query tool** | Vector search with top-k results and optional project scoping. | `v2:exists` |
| 73 | **Knowledge ingest tool** | Ingest text/file/URL with sandboxed file paths. | `v2:exists` |
| 74 | **Knowledge source tools** | Add source (url_list/crawl/file_glob with JSON config), list sources, refresh source. | `v2:exists` |
| 75 | **Bookmark tools** | bookmark URL, list sources, list bookmarks (with scope/tag/score filters). | `v2:partial` |

### 4.6 User Interaction

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 76 | **Ask user tool** | Human-in-the-loop prompting: free-text input, numbered options, timeout handling (abort/skip modes), retry logic. Hook integration. | `v2:blocked` |

### 4.7 Visual & Diagram Tools

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 77 | **Diagram generation (Kroki)** | DiagramService: async Kroki API client supporting 6 types: mermaid, plantuml, graphviz, d2, c4plantuml, excalidraw. SVG/PNG output. | `v2:feasible` |
| 78 | **Screenshot service** | Capture browser screenshots via Playwright, save with timestamp-based filenames, deliver via channels. Terminal text encoding fallback. | `v2:blocked` |
| 79 | **Visual feedback tools** | share_screenshot and share_terminal_output — deliver visual artifacts to user via channel. | `v2:blocked` |
| 80 | **Screenshot-on-error hook** | Auto-capture screenshot when tool encounters error. Configurable mode: auto/manual/on_error. | `v2:blocked` |

### 4.8 MCP Integration

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 81 | **MCP server registry** | Central registry for named MCP server instances (stdio/SSE/streamable_http). Async lifecycle management. Health checks. | `v2:exists` |
| 82 | **MCP tool resolution (mcp: prefix)** | Agent definitions reference `mcp:server_name` tools. Registry resolves at agent construction. | `v2:exists` |
| 83 | **GitHub MCP server** | Pre-configured GitHub MCP server (npx with token). | `v2:exists` |

### 4.9 Skill System

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 84 | **Skill registry (progressive loading)** | SkillRegistry scans markdown skills (YAML frontmatter) at startup. Two tools: list_skills, load_skill. Lazy content loading — frontmatter at scan, full content on demand. | `v2:exists` |

---

## 5. CLI (BearClaw)

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 85 | **bearclaw chat** | Interactive REPL with --model, --session, --workspace, --project options. Multi-line input via `!end`. Auto-detect GitHub remote. Session naming/persistence. Copilot token auto-detection. | `v2:blocked` |
| 86 | **bearclaw run (daemon)** | Background daemon: concurrent channel_loop + poll_loop. Dispatch cycle: pick→invoke→hooks→metrics. WIP recovery (CONTINUE FORWARD prefix). Signal handling (SIGTERM). On-failure retry. | `v2:blocked` |
| 87 | **bearclaw board** | Rich table kanban display by status. Color-coded by age thresholds. YAML config parsing. Duration display. | `v2:deferred` |
| 88 | **bearclaw browser** | 3 commands: start (launch Edge on port 9222, save PID), stop (kill from PID), status (check CDP connectivity). | `v2:blocked` |
| 89 | **bearclaw auth** | login: GitHub Copilot OAuth device-flow. status: show auth state + configured model + API endpoint. | `v2:blocked` |
| 90 | **bearclaw decisions** | list, show, resolve commands. YAML frontmatter parsing. Pending/resolved directories. Options extraction from markdown. | `v2:deferred` |
| 91 | **bearclaw knowledge-source** | add (url_list/crawl/file_glob + JSON config), list, refresh. Scope filtering. | `v2:deferred` |
| 92 | **bearclaw project** | create, list, switch, archive commands. Workspace binding. Active project tracking via file. | `v2:deferred` |
| 93 | **bearclaw slack** | auth (validate tokens), test (send test message). SSL context via truststore. Bot/app/channel tokens. | `v2:blocked` |
| 94 | **bearclaw usage** | stats: token usage/costs by time window (--last-hour/--last-7d/--all). Aggregate by model. Show premium requests. Cost estimation. | `v2:deferred` |
| 95 | **bearclaw voice** | listen (record+transcribe), speak (TTS), brainstorm (streaming session). Duration/idle-timeout options. | `v2:deferred` |

---

## 6. CHANNELS (I/O Adapters)

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 96 | **ChannelPlugin protocol** | Abstract I/O adapter: send(), receive(), send_file(), send_blocks(), send_image(). Runtime-checkable. | `v2:blocked` |
| 97 | **CLI channel** | stdin/stdout I/O via typer. Supports prompting. | `v2:blocked` |
| 98 | **Slack channel** | SocketMode (WebSocket) + AsyncWebClient (Web API). Per-user rate limiting (deque windows). User ID allowlist. Receive timeout. mrkdwn conversion. DM-only. | `v2:blocked` |
| 99 | **Slack thread registry** | Per-context thread tracking (context_key → thread_ts). Enables threaded conversations. | `v2:blocked` |
| 100 | **Slack Block Kit templates** | Pure-dict builders: proposal blocks (numbered options), approval blocks (approve/deny), progress blocks, status blocks, text fallback variants. | `v2:blocked` |
| 101 | **Slack action callback routing** | Socket mode interactive handler for routing block_actions to callback functions. | `v2:blocked` |

---

## 7. VOICE I/O

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 102 | **Speech-to-text (Moonshine)** | moonshine-voice wrapper. Batch transcription (int16 PCM → float32). Lazy model loading. Language support. | `v2:exists` |
| 103 | **Text-to-speech (pyttsx3)** | pyttsx3 wrapper. Async via asyncio.to_thread. Configurable rate/volume. | `v2:exists` |
| 104 | **Streaming STT** | Live transcription during recording. Open-ended sessions. | `v2:exists` |
| 105 | **Voice channel** | Microphone + speaker I/O via sounddevice. Two modes: quick (fixed-duration batch) + brainstorm (open-ended streaming). | `v2:exists` |
| 106 | **Ideation panel (v2 extension)** | Voice characterizations (ideation-architect, ideation-critic, ideation-data, ideation-enduser, ideation-pragmatist, ideation-security). Multi-voice deliberation. | `v2:exists` |

---

## 8. SAFETY, GATING & AUDIT

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 107 | **Approval gate toolset** | Wraps tool calls in approval flow: policy rule matching → pre-grant check → channel prompt → response parsing (yes/no/approve all). TTL-based session grants with max-uses. | `v2:blocked` |
| 108 | **Approval policy model** | Rules: tool_name (exact or wildcard) + optional arg_pattern regex. Configurable timeouts, grant TTL, max-uses. GrantRecord + ApprovalSession per-session state. | `v2:feasible` |
| 109 | **Security audit log (SQLite)** | Event-type, severity, actor, tool_name, detail, metadata logging. Structured query. | `v2:idea` |
| 110 | **Command safety guard** | Regex blocklist for dangerous commands: rm -rf, git push -f, pip install, .env access, sudo, chmod. Audit sink callback. | `v2:feasible` |
| 111 | **Content safety (untrusted wrapping)** | Wraps fetched web content in `<untrusted_web_content>` sentinel tags to prevent prompt injection. | `v2:feasible` |
| 112 | **Path sandboxing (traversal guard)** | sandbox_path(): null-byte check, resolve against root, is_relative_to validation. Used throughout filesystem tools and knowledge intake. | `v2:feasible` |

---

## 9. DAEMON & AUTONOMOUS MODE

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 113 | **Poll-dispatch-reconcile loop** | Autonomous daemon loop: poll kanban → pick tasks → dispatch to agents → reconcile outcomes. Configurable poll interval, max concurrent tasks. | `v2:blocked` |
| 114 | **WIP continuity store** | Per-task JSONL files for work-in-progress checkpoints. Save/load/clear per agent+task_id. Short-lived recovery for multi-cycle agent autonomy. | `v2:idea` |
| 115 | **Heartbeat runner** | Proactive wakeups via HEARTBEAT.md prompt. UTC active-hours windowing. Non-OK findings forwarded to user. Configurable interval. | `v2:blocked` |
| 116 | **Stale execution detector** | Auto-cancel tasks exceeding timeout (default 300s). Prevents stuck agents. | `v2:blocked` |
| 117 | **Task-level retry (exponential backoff)** | Per-task retry with configurable max attempts, backoff base, and backoff max. | `v2:deferred` |
| 118 | **Dispatch context (immutable)** | Frozen dataclass carrying task_id, agent_name, delegation_depth, workspace_root, etc. through delegation chains. | `v2:partial` |

---

## 10. MEMORY & SESSION

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 119 | **Session store (JSONL)** | Append-only PydanticAI message history persistence. Load/append/save. Backup (.bak). Metadata tracking (last_consolidated index). | `v2:blocked` |
| 120 | **Usage tracker** | Per-turn logging: model, provider, input/output/cache tokens, requests, tool_calls, estimated_cost_usd, premium_requests, operation. JSONL windowed query + summary aggregation. | `v2:idea` |
| 121 | **Usage cost calculation** | genai-prices.calc_price() integration. Provider alias mapping (copilot→openai). Graceful failure with None fallback. | `v2:idea` |
| 122 | **Error journal (rotated JSONL)** | ErrorEntry: timestamp, error_type, tool_name, exc_message, action_taken, attempt, resolved, session_id. Auto-rotation (cap 10K). Agents query history to learn from past failures. | `v2:idea` |
| 123 | **Context manager (static files)** | Loads context.md + MEMORY.md + session-memory.md → composites into single instruction string for agent. | `v2:partial` |
| 124 | **Session memory persistence** | LLM-summarized conversation saved to `.owlbear/session-memory.md` at session end. | `v2:feasible` |
| 125 | **Lessons-learned injection** | Curated markdown lessons from `.owlbear/lessons/` injected into agent context at session start. Token-budgeted. | `v2:feasible` |

---

## 11. OBSERVABILITY & ANALYTICS

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 126 | **Event store (append-only JSONL)** | Timedelta-windowed query + aggregation of lifecycle events. Per-tool call/error/duration breakdown. | `v2:idea` |
| 127 | **Improvement proposals (self-improvement)** | Auto-generated review-only suggestions from observability metrics. Thresholds: ≥5 calls, ≥3 per tool, 50%+ error rate, 3000+ ms latency. Categories: reliability, performance. | `v2:idea` |
| 128 | **Per-tool statistics** | Call count, error count, avg/max duration per tool. Computed from EventStore data. | `v2:idea` |
| 129 | **OpenTelemetry support** | Optional OTel collector endpoint for external observability. | `v2:idea` |
| 130 | **Progress reporter** | Background heartbeat via channel with activity gate. Configurable interval (30s) and detail level (brief/detailed). | `v2:blocked` |

---

## 12. ERROR HANDLING & RESILIENCE

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 131 | **Error classification (4 categories)** | Pure function: classify_error() → TRANSIENT, AUTH, PERMANENT, TOOL_SEMANTIC. No I/O, side effects, or logging. Drives retry policy. | `v2:feasible` |
| 132 | **Circuit breaker (async state machine)** | Three states: closed→open→half_open. Fast-fail for transient API outages. Applied to Copilot API transport. | `v2:blocked` |
| 133 | **HTTP transport retry** | AsyncTenacityTransport wrapping httpx: retry on 429/502/503/504. Retry-After header respecting. Exponential backoff. Max 3 attempts. | `v2:blocked` |
| 134 | **Error-to-user message sanitization** | Converts raw exceptions to safe user-facing messages. Applied at all channel-facing code paths. | `v2:feasible` |
| 135 | **Exception hierarchy** | OwlBearError base → AgentError, ToolError, ConfigError, etc. Structured error typing for catch logic. | `v2:feasible` |

---

## 13. CONFIGURATION SYSTEM

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 136 | **Pydantic-settings (env vars)** | 90+ settings with OWLBEAR_ prefix, type validation, defaults. Pydantic-settings BaseSettings. | `v2:partial` |
| 137 | **Browser config model** | Frozen Pydantic model: allowed/blocked URLs, headless, viewport, timeout, CDP endpoint/port, browser executable, auto_launch, content scan mode, cookie profiles. | `v2:blocked` |
| 138 | **Hook reaction rules** | Event→action dispatch config: events list, actions list (notify/retry/escalate), optional match predicate. | `v2:blocked` |
| 139 | **Autonomous mode settings** | poll_interval, max_concurrent_tasks, stale_task_timeout, task_retry_max_attempts, backoff_base, backoff_max. | `v2:blocked` |
| 140 | **Feature flags (10+)** | audit_map_worker_enabled, condenser_enabled, consolidation_enabled, session_memory_enabled, lessons_injection_enabled, prehydration_enabled, heartbeat_enabled, knowledge_graph_expansion, inter_doc_graph_building, lint_gate_enabled, board_context_enabled. | `v2:partial` |

---

## 14. PROJECT MANAGEMENT

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 141 | **Project CRUD** | Create, list (active/all), archive, switch projects. Per-project workspace paths. Active tracking via file. JSON storage under ~/.config/owlbear/projects/. | `v2:partial` |
| 142 | **Workspace scaffolding** | Templates: bare, python-uv, python-pip, node. Git init, kanban-md init, .gitignore generation, README templating. | `v2:feasible` |
| 143 | **Project definition extraction** | LLM-based structured extraction: name, description, goals, requirements (functional/non-functional), AC, tech_stack, risks, open_questions. Markdown generation from definition. | `v2:feasible` |
| 144 | **Multi-project session** | Switch between projects within a daemon session. Workspace binding persisted. | `v2:blocked` |

---

## 15. AUTHENTICATION

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 145 | **Copilot OAuth device flow** | request_device_code → poll_for_access_token (handles authorization_pending, slow_down) → exchange_for_copilot_token. Truststore SSL. Token caching (~/.config/owlbear/copilot_token.json). 60s refresh margin. | `v2:blocked` |

---

## 16. BOOTSTRAP & WIRING

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 146 | **Bootstrap assembly (10 phases)** | Project resolution → channel creation → hook assembly (8 hooks) → model creation → toolset assembly → knowledge infra → MCP registry → agent registry → session/context/tracker → agent construction. | `v2:blocked` |
| 147 | **Channel factory** | Config-driven: create CLI/Slack/Voice channel with secret validation. | `v2:blocked` |
| 148 | **Toolset assembly (wrapping chain)** | FileToolset → HookedToolset → ApprovalGateToolset. Security audit sink binding. Project/session context binding. | `v2:blocked` |

---

## 17. UNIQUE/NICHE IDEAS WORTH PRESERVING

| # | Feature | Description | Tag |
|---|---------|-------------|-----|
| 149 | **Temporal decay scoring** | Vector search results weighted by recency. Importance-weighted exponential decay. Configurable rate and weight. Entities with high importance resist decay. | `v2:exists` |
| 150 | **Entity importance by type** | Different entity types have different base importance scores influencing search ranking and decay resistance. | `v2:exists` |
| 151 | **Error journal → agent learning** | Agents query error history to learn from past failures and avoid repeating patterns. JSONL queryable by tool_name, error_type, last_n. | `v2:idea` |
| 152 | **WIP recovery (CONTINUE FORWARD)** | When daemon resumes a previously interrupted task, provides summary with "CONTINUE FORWARD" prefix (500 char limit). Agent continues from where it left off. | `v2:idea` |
| 153 | **Idle embedding unload** | BGE-M3 model auto-unloads after idle timeout (~3GB reclaimed). Reloads on next request. Configurable timeout. | `v2:exists` |
| 154 | **Soft-fail exit classification** | Terminal exit code 1 classified as potential soft failure (e.g., "no matches found") rather than hard error. | `v2:feasible` |
| 155 | **Tool-call/return boundary alignment** | Context condenser keeps tool-call and tool-return message pairs together during summarization to prevent broken conversations. | `v2:blocked` |
| 156 | **Copilot premium request multipliers** | Pricing tiers for input/output tokens by model. Used for cost estimation beyond basic token counting. | `v2:idea` |
| 157 | **Self-improvement proposals (review-only)** | Non-autonomous suggestions generated from metrics: "tool X has 60% error rate, suggest retry logic". Human reviews before any change is applied. | `v2:idea` |
| 158 | **Retrospective findings → knowledge graph** | Task completions generate structured retrospectives (what_worked, what_failed, error_patterns, reusable_patterns) that get ingested into the knowledge graph for institutional learning. | `v2:idea` |
| 159 | **Eligibility gates for retrospectives** | Only generate retrospectives for non-trivial tasks: requires rejection count > 0 or priority ≥ "needed". Avoids noise from easy tasks. | `v2:idea` |
| 160 | **Slack structured proposals** | Block Kit templates that let users approve/deny/choose between options in Slack DM. Interactive buttons with callback routing. | `v2:blocked` |
| 161 | **Cookie persistence profiles** | Named browser profiles for maintaining login state across crawl sessions. Profile_name + profile_dir pair. | `v2:blocked` |
| 162 | **Accessibility tree snapshots** | browser_snapshot tool: returns accessibility tree from browser (interactive elements, text content, full tree). Three filter modes. | `v2:blocked` |
| 163 | **Tab title MutationObserver** | In CDP mode, injects JavaScript MutationObserver to maintain `[OwlBear]` prefix on browser tab titles so user can identify managed tabs. | `v2:blocked` |
| 164 | **HTML cache layer** | Caches raw rendered HTML from browser to avoid re-rendering during crawl. Deduplication for content extraction. | `v2:blocked` |

---

## Summary Statistics

| Category | Total Features | v2:exists | v2:partial | v2:feasible | v2:idea | v2:blocked | v2:deferred |
|----------|---------------|-----------|------------|-------------|---------|------------|-------------|
| Agent Framework | 9 | 1 | 3 | 3 | 0 | 2 | 0 |
| Agent Roles | 9 | 9 | 0 | 0 | 0 | 0 | 0 |
| Hook System | 13 | 0 | 0 | 2 | 3 | 8 | 0 |
| Knowledge System | 25 | 24 | 1 | 0 | 0 | 0 | 0 |
| Tools | 28 | 7 | 1 | 5 | 0 | 15 | 0 |
| CLI | 11 | 0 | 0 | 0 | 0 | 5 | 6 |
| Channels | 6 | 0 | 0 | 0 | 0 | 6 | 0 |
| Voice | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| Safety & Audit | 6 | 0 | 0 | 4 | 1 | 1 | 0 |
| Daemon/Autonomous | 6 | 0 | 1 | 0 | 1 | 4 | 0 |
| Memory & Session | 7 | 0 | 1 | 2 | 3 | 1 | 0 |
| Observability | 5 | 0 | 0 | 0 | 4 | 1 | 0 |
| Error Handling | 5 | 0 | 0 | 3 | 0 | 2 | 0 |
| Configuration | 5 | 0 | 2 | 0 | 0 | 3 | 0 |
| Project Management | 4 | 0 | 1 | 2 | 0 | 1 | 0 |
| Authentication | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| Bootstrap | 3 | 0 | 0 | 0 | 0 | 3 | 0 |
| Unique/Niche Ideas | 16 | 3 | 0 | 1 | 6 | 6 | 0 |
| **TOTAL** | **164** | **49** | **10** | **22** | **18** | **59** | **6** |

---

## Priority Recommendations

### Highest Value — Good ideas not yet in v2 (`v2:idea` + `v2:feasible`)

**Quick wins (feasible, high value):**
1. **#5 Role-based access control** — VALIDATOR role prevents agents from writing files. Simple allow-list.
2. **#6 Rigor profiles** — Task-tagged quality presets (lean/standard/thorough). Low effort.
3. **#7 Budget enforcement** — Token/cost tracking with hard stops. Prevents runaway sessions.
4. **#108 Approval policy model** — Configurable tool-approval rules. Foundation for safety.
5. **#131 Error classification** — Pure function driving retry decisions. Zero dependencies.
6. **#134 Error-to-user sanitization** — Safe messaging at all channel boundaries.
7. **#135 Exception hierarchy** — Structured error types for catch logic.

**High value ideas (need design but worth it):**
1. **#25 Retrospective findings → KG** — Institutional learning from completed tasks.
2. **#120–121 Usage tracking + cost** — LLM cost visibility across sessions.
3. **#122 Error journal for agent learning** — Agents query past failures to avoid repeats.
4. **#127 Self-improvement proposals** — Auto-generated suggestions from metrics (review-only).
5. **#152 WIP recovery** — Resume interrupted work with context summary.

### Already in v2 (no action needed): 49 features
### Blocked by architecture (can't do in VS Code Chat): 59 features — most relate to standalone daemon, browser automation, CLI REPL, channels.
### Deferred pending CLI maturity: 6 features — CLI commands that could run via `gh copilot`.
