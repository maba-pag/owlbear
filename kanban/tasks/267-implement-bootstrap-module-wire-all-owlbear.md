---
id: 267
title: Implement bootstrap() module - wire all OwlBear components
status: archived
priority: critical
created: 2026-02-28T14:20:33.9684834+01:00
updated: 2026-02-28T23:54:32.1975558+01:00
started: 2026-02-28T15:05:22.2848598+01:00
completed: 2026-02-28T23:54:32.1975558+01:00
tags:
    - phase-8
    - agent
    - core
depends_on:
    - 265
    - 266
class: standard
---

## Context
The main assembly layer deliverable. Procedural bootstrap() wires all unwired interactions.
See docs/bootstrap-assembly-research.md S3.3 for full design.
Current state: bearclaw chat wires ~40%% (hooks: 1/6, toolsets: 4/7, no MCP, no AgentRegistry).
bearclaw run wires ~10%% (no hooks, no toolsets, no MCP).

## Acceptance Criteria
- [ ] src/owlbear/bootstrap.py module
- [ ] async def bootstrap(settings: OwlBearSettings, *, channel_name: str = 'cli', workspace_root: Path | None = None) -> BootstrapResult
- [ ] BootstrapResult dataclass with fields: agent (OwlBearAgent), channel (ChannelPlugin), mcp_registry (MCPServerRegistry | None), hooks (HookRegistry), cleanup (list[Callable] for teardown)
- [ ] build_hooks(settings, workspace_root) -> HookRegistry: registers CommandSafetyGuard (PRE_TOOL_USE), AutoLintHook (POST_TOOL_USE), ObservabilityHook (all events), SubagentVerificationHook (SUBAGENT_COMPLETE), TestVerificationHook (SESSION_END), NotificationHook (TASK_COMPLETE + QUESTION_PENDING)
- [ ] build_toolsets(settings, workspace, hooks, channel) -> list[AbstractToolset]: FileToolset, TerminalToolset, AskUserToolset, SkillRegistry (if skills_dir exists), GitLocalToolset, GitHubToolset (if github_token), BrowserToolset, DelegationToolset
- [ ] create_channel(settings, channel_name) -> ChannelPlugin: factory dispatching to CLIChannel / SlackChannel / VoiceChannel with lazy imports for optional deps
- [ ] build_mcp_registry(settings) -> MCPServerRegistry: delegates to register_default_servers() from tools.mcp_servers
- [ ] build_agent_registry(settings, toolsets, mcp_registry) -> AgentRegistry: scans .github/agents/ dir
- [ ] Wraps all non-DelegationToolset toolsets in HookedToolset for PRE/POST_TOOL_USE hook emission
- [ ] Constructs OwlBearAgent with model instance (from create_copilot_model), session, context, hooks, tracker, hooked toolsets
- [ ] Sets agent._deps.agent_registry after construction
- [ ] Each helper function is independently testable (pure function or single side-effect)
- [ ] ~150 LOC total (bootstrap ~40, helpers ~80, BootstrapResult ~10, imports ~20)

## Architecture Notes
- create_channel() here replaces the need for a separate ChannelManager class (#268) — see architecture decision below
- Bootstrap is procedural (not a builder pattern) following nanobot and KISS
- HookedToolset wrapping: DelegationToolset should NOT be wrapped (it's internal dispatch, not user tooling)
- BrowserToolset: include in toolsets but do NOT call setup() — browser is lazy-initialized on first use
- MCP registry: skip if settings.mcp_servers is None/empty
- URLSafetyGuard: register on hooks if BrowserToolset is included (hooks=hooks in BrowserConfig)
- ContextInjectionHook: include in build_hooks for SESSION_START
- Error handling: individual component failures should not prevent bootstrap from completing (log warning, continue)

## TDD
- Unit test task: #273 (integration test) depends on this
- Builder should write unit tests for each helper function in tests/test_bootstrap.py alongside implementation

## Dependencies
depends_on: [265, 266]
