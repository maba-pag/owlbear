# OpenClaw Skills Ecosystem Research

> **Owning task:** #590 — Research: OpenClaw skills (proactive, self-improving, browser, automation)
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

OwlBear needs agent autonomy, self-correction, and web interaction capabilities. OpenClaw (271k stars, MIT) is the most mature open-source AI assistant with always-on daemon behavior. Question: which OpenClaw patterns for proactive behavior, self-improvement, browser automation, and workflow orchestration are reusable in OwlBear's Python/PydanticAI stack?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| OpenClaw main repo | <https://github.com/openclaw/openclaw> | .95 |
| OpenClaw Heartbeat docs | <https://docs.openclaw.ai/gateway/heartbeat> | .90 |
| OpenClaw Hooks docs | <https://docs.openclaw.ai/gateway/hooks> | .85 |
| OpenClaw Cron docs | <https://docs.openclaw.ai/gateway/cron-jobs> | .80 |
| OpenClaw Browser docs | <https://docs.openclaw.ai/tools/browser-use> | .85 |
| OpenClaw Skills docs | <https://docs.openclaw.ai/tools/skills> | .75 |
| OpenClaw Lobster (workflow shell) | <https://github.com/openclaw/lobster> | .70 |
| OpenClaw Agent Loop docs | <https://docs.openclaw.ai/concepts/agent-loop> | .80 |
| OpenClaw Retry Policy docs | <https://docs.openclaw.ai/concepts/retry> | .65 |

## 3. Analysis

### 3a. Proactive Behavior — Heartbeat vs Cron

| Criterion | Heartbeat (.90) | Cron (.75) | OwlBear fit |
|-----------|-----------------|------------|-------------|
| Trigger | Timer (default 30m) | Schedule (cron expr) | Both viable |
| Context | Reads `HEARTBEAT.md` checklist | Creates isolated session | Heartbeat simpler |
| Self-update | Agent edits own `HEARTBEAT.md` | No self-modification | Novel pattern |
| Suppression | `HEARTBEAT_OK` = nothing to do | N/A | Good for idle |
| Active hours | Configurable window | Always runs | Need both |
| Complexity | ~50 LOC wrapper | Full scheduler | Heartbeat first |
| OwlBear mapping | New `HeartbeatRunner` + hook | Extend daemon loop | Phase-able |

**Key insight:** OpenClaw's heartbeat is not a skill — it's a gateway-level timer that wakes the agent with a workspace checklist. The agent can update the checklist itself, creating a self-improving feedback loop. The `HEARTBEAT_OK` response contract prevents empty runs from wasting tokens.

### 3b. Self-Correction Patterns

| Pattern | OpenClaw mechanism | OwlBear status | Gap |
|---------|-------------------|----------------|-----|
| Error retry | Per-tool retry, exponential backoff | `HookedToolset` (3 attempts, tenacity) | ✅ Covered |
| Session memory | `session-memory` hook saves context on reset | No equivalent | New hook needed |
| Boot instructions | `boot-md` hook runs startup checks | `ContextManager` loads instructions | ✅ Partial |
| Self-updating checklist | `HEARTBEAT.md` agent-editable | No equivalent | New pattern |
| Error journal | N/A (OpenClaw lacks this) | `ErrorJournal` JSONL | ✅ OwlBear ahead |
| Compaction hooks | `before/after_compaction` events | No compaction yet | Future need |

### 3c. Browser Automation

| Criterion | OpenClaw (.80) | OwlBear (.75) | Gap |
|-----------|---------------|---------------|-----|
| Engine | CDP + Playwright | CDP + Playwright | Same stack |
| Profile isolation | Managed "openclaw" profile | Config-driven CDP endpoint | OwlBear simpler |
| Snapshot system | AI/role snapshots with numeric refs | `browser_read_text` | OpenClaw richer |
| SSRF guards | Localhost/reserved-IP block | URL allowlist in config | Both adequate |
| Screenshot | Built-in tool | `ScreenshotService` + `ScreenshotOnErrorHook` | ✅ OwlBear ahead |
| Multi-tab | Via CDP tab groups | Tab group research done (#65) | Future work |
| Extension relay | Chrome extension for messages | Not needed (daemon model) | N/A |

### 3d. Workflow Orchestration — Lobster

| Criterion | Lobster (.65) | OwlBear kanban pipeline (.80) | Assessment |
|-----------|--------------|-------------------------------|------------|
| Paradigm | Typed JSON pipelines | Status-column pipeline | Different models |
| Approval gates | Built-in step gates | `ApprovalGateToolset` | ✅ Covered |
| Dependencies | `stdin: $stepId.stdout` | `depends_on` frontmatter | ✅ Covered |
| Scheduling | Manual/cron trigger | Manual + future heartbeat | Gap |
| Reusability | YAML workflow files | Agent definitions | Different approach |
| Complexity | Full workflow engine | Kanban + agent roles | KISS favors OwlBear |

**Assessment:** Lobster's typed pipeline model is over-engineered for OwlBear's needs. The kanban-based pipeline with agent roles (planner→researcher→architect→builder→reviewer→writer→auditor) already provides equivalent workflow orchestration with simpler primitives. YAGNI.

### 3e. Hook System Comparison

| OwlBear HookEvent | OpenClaw equivalent | Notes |
|-------------------|---------------------|-------|
| `SESSION_START` | `agent:bootstrap` | Same concept |
| `SESSION_END` | `session:compact:after` | Different trigger |
| `PRE_TOOL_USE` | `before_tool_call` | Same concept |
| `POST_TOOL_USE` | `after_tool_call` / `tool_result_persist` | OpenClaw splits persist |
| `ON_MESSAGE` | `message:received` | Same concept |
| `ON_ERROR` | (no equivalent) | OwlBear advantage |
| `SUBAGENT_COMPLETE` | (no equivalent) | OwlBear advantage |
| `TASK_COMPLETE` | (no equivalent) | OwlBear advantage |
| `QUESTION_PENDING` | (no equivalent) | OwlBear advantage |
| (missing) | `message:sent` | Could add for logging |
| (missing) | `gateway:startup` | Maps to daemon boot |
| (missing) | `session:compact:before` | Future compaction |

## 4. Recommendation (.85 confidence)

Adopt **3 patterns** from OpenClaw, reject 2:

| Pattern | Action | Confidence | Rationale |
|---------|--------|------------|-----------|
| Heartbeat runner | **Adopt** | .90 | High-value proactive behavior with low complexity (~100 LOC) |
| Session-memory hook | **Adopt** | .80 | Prevents context loss on session reset; small hook |
| `DAEMON_STARTUP` hook event | **Adopt** | .75 | Enables boot-time checks; 1-line enum addition |
| Lobster workflow engine | **Reject** | .30 | YAGNI — kanban pipeline covers our needs |
| Snapshot/ref browser system | **Reject** | .40 | Marginal gain over current `browser_read_text`; high complexity |

**Risk:** Heartbeat runner needs careful token budgeting — empty heartbeat turns waste API quota. OpenClaw's `HEARTBEAT_OK` suppression pattern mitigates this.

## 5. Follow-up Tasks

See kanban commands below.
