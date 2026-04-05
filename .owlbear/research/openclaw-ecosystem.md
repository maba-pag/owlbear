# OpenClaw Ecosystem & Skills — Epic Synthesis

> **Owning task:** #581 — Research: OpenClaw Ecosystem & Skills
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear is an always-on AI dev system needing agent autonomy, self-correction, and web interaction. This epic synthesizes findings from children (#590 OpenClaw skills, #591 ClawFeed) plus two additional comparison systems (OpenHands, SWE-agent) to produce actionable patterns across three themes.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| OpenClaw (271k stars) | <https://github.com/openclaw/openclaw> | .95 — primary target |
| OpenHands SDK (68.7k stars) | <https://github.com/OpenHands/OpenHands> | .85 — skill/condenser architecture |
| SWE-agent (18.7k stars) | <https://github.com/SWE-agent/SWE-agent> | .75 — retry/self-correction patterns |
| ClawFeed (1.6k stars) | <https://github.com/kevinho/clawfeed> | .70 — feed curation, prompt templates |
| OpenHands Skill docs | <https://docs.openhands.dev/sdk/arch/skill> | .80 — trigger-based skill activation |
| OpenHands Condenser docs | <https://docs.openhands.dev/sdk/arch/condenser> | .80 — context compression |
| SWE-agent config docs | <https://swe-agent.com/latest/reference/agent_config/> | .70 — retry loop config |
| OwlBear agent-patterns-research | docs/research/agent-patterns.md | .90 — prior art baseline |
| OwlBear openclaw-skills-research | docs/research/openclaw-skills.md | .90 — child #590 findings |
| OwlBear clawfeed-research | docs/research/clawfeed.md | .75 — child #591 findings |

## 3. Analysis

### 3a. Agent Autonomy — Proactive Behavior

| Criterion | OpenClaw Heartbeat (.90) | OpenHands Skill Triggers (.80) | SWE-agent RetryLoop (.65) | OwlBear current |
|-----------|------------------------|-------------------------------|--------------------------|-----------------|
| Proactive wake | Timer (30m default) | None (reactive only) | None (reactive only) | None — gap |
| Self-scheduling | Agent edits HEARTBEAT.md | N/A | N/A | None — gap |
| Idle suppression | `HEARTBEAT_OK` contract | N/A | N/A | None — gap |
| Skill activation | Always-on plugins | Keyword/task triggers | YAML tool bundles | SKILL.md on-demand |
| MCP integration | N/A | Skill-embedded MCP config | N/A | None — gap |

**Key finding:** Only OpenClaw has true proactive autonomy (heartbeat). OpenHands and SWE-agent are purely reactive. OwlBear should adopt the heartbeat pattern (from #590 research, .90 confidence).

### 3b. Self-Correction Patterns

| Pattern | OpenClaw | OpenHands | SWE-agent | OwlBear |
|---------|----------|-----------|-----------|---------|
| Tool-level retry | Per-tool backoff | Built-in error handling | `max_requeries=3` | `HookedToolset` (3 attempts, tenacity) ✅ |
| Context compression | LLM compaction | `LLMSummarizingCondenser` (rolling window: keep head+tail, summarize middle) | History processors | None — **gap** |
| Session memory persistence | `session-memory` hook on reset | Event log + condensation events | Trajectory JSONL | None — **gap** |
| Error classification | N/A | N/A | Requery on format/block/syntax errors | `classify_error()` → transient/permanent ✅ |
| Error journal | N/A | N/A | N/A | `ErrorJournal` JSONL ✅ (OwlBear ahead) |
| Boot-time self-check | `boot-md` hook | `AGENTS.md` always-loaded | N/A | `ContextManager` loads instructions ✅ |
| Guard/safety hooks | N/A | `SecurityAnalyzer` risk assessment | N/A | `CommandSafetyGuard` + `BlockedCommandError` ✅ |

**Key finding:** OwlBear's self-correction is strong at tool level (retry, error classification, guards). Two gaps: (1) context compression when context window fills, (2) session-memory persistence on session end. OpenHands' condenser pattern is the most sophisticated — rolling window with LLM summarization, threshold-based triggering, and pipeline chaining.

### 3c. Skill/Plugin Architecture

| Criterion | OpenClaw Skills | OpenHands Skills | SWE-agent Tools | OwlBear Skills |
|-----------|----------------|-----------------|-----------------|----------------|
| Format | Plugin classes | Markdown + YAML frontmatter | YAML tool bundles | Markdown + YAML frontmatter ✅ |
| Activation | Always-on (eager load) | 3 types: always/keyword/task trigger | Static config | On-demand (lazy load) ✅ |
| MCP tools | N/A | Skill-embedded `mcp_tools` config | N/A | None — minor gap |
| Scope/boundaries | Hook matchers | Trigger regex patterns | Per-agent tool config | Per-agent role restrictions ✅ |
| Discovery | ClawHub registry | `.agents/skills/`, `.openhands/` dirs | `config/` YAML files | `.github/skills/*/SKILL.md` ✅ |
| Third-party compat | Own addon format | `.cursorrules`, `AGENTS.md`, `CLAUDE.md` | N/A | None |

**Key finding:** OwlBear's skill system (SKILL.md with YAML frontmatter, lazy loading, per-role restrictions) is already well-aligned with industry patterns. OpenHands adds keyword/task trigger types which could enable auto-activation. MCP tool embedding in skills is a minor gap but low priority (YAGNI until MCP servers are needed).

### 3d. Web Interaction Patterns

| Criterion | OpenClaw | OpenHands | OwlBear |
|-----------|----------|-----------|---------|
| Browser engine | CDP + Playwright | Docker-sandboxed bash/browser | CDP + Playwright ✅ |
| Feed ingestion | N/A | N/A | `RefreshOrchestrator` + `BookmarkPipeline` ✅ |
| Prompt templates | N/A | Skill-embedded instructions | None — minor gap |
| Web search | N/A | N/A | `WebSearchToolset` (ddgs + trafilatura) ✅ |

OwlBear's web interaction is already ahead of both OpenClaw and OpenHands for a single-developer daemon. No major gaps.

## 4. Recommendation (.85 confidence)

### Adopt (3 patterns)

| Pattern | Source | Confidence | Effort | Rationale |
|---------|--------|------------|--------|-----------|
| Heartbeat runner | OpenClaw (#590) | .90 | ~100 LOC | Only path to proactive autonomy; timer + checklist + `HEARTBEAT_OK` suppression |
| Context condenser | OpenHands | .85 | ~200 LOC | Critical for long sessions; rolling-window LLM summarization prevents context overflow |
| Session-memory hook | OpenClaw (#590) | .80 | ~30 LOC | Persist context summary on SESSION_END; prevents knowledge loss across sessions |

### Consider (2 patterns)

| Pattern | Source | Confidence | Rationale |
|---------|--------|------------|-----------|
| Keyword trigger for skills | OpenHands | .60 | Auto-activate skills by message content; useful but current on-demand loading works |
| Externalized prompt templates | ClawFeed (#591) | .55 | Config-driven prompt templates for knowledge injection; nice-to-have |

### Reject (3 patterns)

| Pattern | Source | Confidence | Rationale |
|---------|--------|------------|-----------|
| Lobster workflow engine | OpenClaw | .30 | YAGNI — kanban pipeline covers workflow needs |
| MCP skill embedding | OpenHands | .35 | YAGNI — no MCP servers needed currently |
| Third-party skill compat | OpenHands | .25 | YAGNI — `.cursorrules`/`CLAUDE.md` formats not relevant for OwlBear |

### OwlBear advantages to preserve

- `ErrorJournal` JSONL (no competitor has this)
- `classify_error()` transient/permanent distinction
- `CommandSafetyGuard` with `BlockedCommandError` propagation
- Progressive skill loading (SKILL.md)
- Per-agent role restrictions (`builder` read+write, `reviewer` read-only)

## 5. Follow-up Tasks

Commands below for user review — **do not execute**.

```powershell
kanban\kanban-md.exe create "Implement HeartbeatRunner for proactive agent autonomy" --priority needed --tags "scope:core,phase-research,agent" --body "Implement HeartbeatRunner: asyncio timer (configurable interval, default 30m) that reads HEARTBEAT.md checklist, runs agent turn, checks for HEARTBEAT_OK suppression. Active hours config. Emit DAEMON_STARTUP hook event on bootstrap.\n\nSee docs/research/openclaw-ecosystem.md S4, docs/research/openclaw-skills.md S3a.\n\nAC:\n- [ ] HeartbeatRunner class with configurable interval and active_hours\n- [ ] Reads workspace HEARTBEAT.md as agent context\n- [ ] HEARTBEAT_OK response suppresses further action\n- [ ] DAEMON_STARTUP added to HookEvent enum\n- [ ] Config fields: heartbeat_interval, heartbeat_active_hours\n- [ ] Tests cover timer, suppression, active hours"

kanban\kanban-md.exe create "Implement context condenser for long-session token management" --priority needed --tags "scope:core,phase-research,agent" --body "Implement a rolling-window context condenser inspired by OpenHands LLMSummarizingCondenser. When context exceeds threshold (configurable, default 120 events), keep head (first 4) + tail (recent 56), summarize middle via LLM.\n\nSee docs/research/openclaw-ecosystem.md S3b, S4.\n\nAC:\n- [ ] Condenser base class with should_condense() + condense() contract\n- [ ] LLMSummarizingCondenser implementation with rolling window\n- [ ] Configurable max_size, keep_first, target_size\n- [ ] Condensation event preserves forgotten_event_ids\n- [ ] Integration point in agent loop\n- [ ] Tests cover threshold detection, summarization, event filtering"

kanban\kanban-md.exe create "Implement session-memory hook for context persistence" --priority important --tags "scope:core,phase-research,hooks" --body "Add a SESSION_END hook handler that persists a context summary (key decisions, active tasks, workspace state) to a per-project session memory file. On SESSION_START, load the previous session summary into context.\n\nSee docs/research/openclaw-ecosystem.md S3b, docs/research/openclaw-skills.md S3b.\n\nAC:\n- [ ] SessionMemoryHook registered on SESSION_END\n- [ ] Persists summary to .owlbear/session-memory.md\n- [ ] SESSION_START loads previous summary into context\n- [ ] Summary is LLM-generated (concise, ~500 tokens)\n- [ ] Tests cover persist, load, and empty-state scenarios"
```
