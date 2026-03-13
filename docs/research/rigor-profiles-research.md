# Rigor Profiles: Configurable Quality-vs-Speed Per Task Type

> **Owning task:** #618 — Rigor profiles: configurable quality-vs-speed per task type
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear applies the same pipeline rigor (builder → reviewer → writer) to every task regardless of complexity. A typo fix gets the same TDD + code review + docs gate treatment as a security-critical feature. This wastes tokens and time on trivial work but is correct for critical work. Should we add configurable rigor profiles, and how?

## 2. Sources Studied

| Source | URL | Relevance | What We Took |
|--------|-----|-----------|--------------|
| nWave `/nw:rigor` command | <https://github.com/nWave-ai/nWave> | .90 | Profile schema, 5-level system (lean/standard/thorough/exhaustive/custom), settings matrix |
| Conductor eval cycles | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | .75 | Evaluate-loop with max 3 fix cycles, model-agnostic approach |
| OwlBear nwave-research.md | `docs/nwave-research.md` §3.3 P1 | 1.0 | Initial recommendation (.85 confidence) for rigor profiles |
| OwlBear orchestration-research.md | `docs/orchestration-agent-frameworks-research.md` §3.2 | 1.0 | Cross-repo validation (2+ sources) |

## 3. Analysis

### 3.1 What nWave Does (and Where OwlBear Differs)

nWave's rigor system controls 7 settings: `agent_model`, `reviewer_model`, `review_enabled`, `double_review`, `tdd_phases`, `refactor_pass`, `mutation_enabled`. Their system maps to Claude Code models (haiku/sonnet/opus).

OwlBear differs in three key ways:

- **Single LLM provider** (Copilot) — no model tier switching (no haiku/sonnet/opus dial)
- **Kanban-driven pipeline** — statuses enforce gates, not DES hooks
- **Simpler agent topology** — 8 agents, not 23 with paired reviewers

This means OwlBear's rigor profiles control **fewer knobs** than nWave's. Good — KISS.

### 3.2 What OwlBear Can Actually Dial

| Setting | Lean | Standard | Thorough | Controlled By |
|---------|------|----------|----------|---------------|
| Review gate (reviewer agent) | Skip | Single pass | Single pass | Orchestrator dispatch |
| Docs gate (writer agent) | Skip | Single pass | Single pass | Orchestrator dispatch |
| Turn budget (max agent turns) | 15 | 30 | 50 | `OwlBearDeps` / delegation |
| TDD enforcement | Tests optional | TDD required | TDD required | Builder system prompt |
| Ruff lint gate | Yes (always) | Yes | Yes | Non-negotiable |

**Not worth dialing** (YAGNI):

| Setting | Why Skip |
|---------|----------|
| Model switching | Single provider — no model tiers available |
| Double review | Only 1 reviewer agent — add pairing later if needed |
| Mutation testing | Not implemented, not planned |
| Refactoring pass | Already part of builder workflow, no separate toggle needed |

### 3.3 Design Options

| Approach | Description | Complexity | KISS Score |
|----------|-------------|------------|------------|
| **A: Config-only presets** | 3 presets in `OwlBearSettings`, override via kanban tag | Low | High |
| **B: Per-agent YAML fields** | Each agent definition gets rigor-aware fields | Medium | Medium |
| **C: DES-style hook enforcement** | Pre/post tool hooks validate TDD compliance | High | Low |
| **D: nWave-style custom builder** | Interactive CLI to build custom profiles | Medium | Low (YAGNI) |

**Recommendation (.85): Option A** — Config-only presets with kanban tag override.

Rationale: Three presets cover 95% of cases. Custom builder and DES enforcement are over-engineering for a system that already has human approval gates. Per-agent YAML fields (B) couple profile logic to agent definitions rather than keeping it in config where it belongs.

### 3.4 Proposed Config Schema

```toml
[rigor_profiles.lean]
review_enabled = false
docs_gate_enabled = false
turn_budget = 15

[rigor_profiles.standard]  # default
review_enabled = true
docs_gate_enabled = true
turn_budget = 30

[rigor_profiles.thorough]
review_enabled = true
docs_gate_enabled = true
turn_budget = 50
```

- Default profile: `standard` (via `default_rigor_profile` field on `OwlBearSettings`)
- Per-task override: kanban tag `rigor:lean` or `rigor:thorough`
- Profile resolved at dispatch time in `poll_tick()` or orchestrator routing

### 3.5 Integration Points

| Component | Change | Files |
|-----------|--------|-------|
| `OwlBearSettings` | Add `RigorProfile` model + `rigor_profiles` dict + `default_rigor_profile` | `config.py` |
| `OwlBearDeps` | Add `rigor_profile: RigorProfile` field | `deps.py` |
| `poll_tick()` | Read task tags → resolve profile → pass into deps | `daemon.py` |
| Orchestrator | Check `review_enabled`/`docs_gate_enabled` before delegating to reviewer/writer | `orchestrator.md` prompt or delegation logic |
| `DelegationToolset` | Propagate `rigor_profile` through child deps | `delegation.py` |
| Builder prompt | Conditional TDD enforcement based on profile | `builder.md` (prompt wording) |

### 3.6 Profile Resolution Order

1. Task kanban tag (`rigor:lean`) — highest priority
2. `default_rigor_profile` setting — fallback
3. Hardcoded `standard` — ultimate fallback

### 3.7 Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Lean profile ships broken code | Medium | Ruff lint is always enforced (non-negotiable) |
| Tag typo (`rigor:lena`) silently ignored | Medium | Validate against known profiles, warn on unknown |
| Config complexity creep | Low | Fixed 3 presets, no custom builder |
| Turn budget too low for complex tasks | Medium | Thorough profile at 50, user can always override |

## 4. Recommendation (.85 confidence)

Implement **Option A: Config-only presets** with three profiles (lean/standard/thorough). Profile is stored in `OwlBearSettings`, resolved per-task via kanban tags, and consumed by the orchestrator at dispatch time. The `RigorProfile` Pydantic model holds `review_enabled`, `docs_gate_enabled`, and `turn_budget`.

KISS: 1 new model, 1 new config section, 3 integration points. No DES hooks, no custom builder, no model switching.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement RigorProfile config model" --priority needed --tags "scope:core,config,phase-7" --body "Add RigorProfile Pydantic model to config.py with fields: review_enabled (bool), docs_gate_enabled (bool), turn_budget (int). Add rigor_profiles dict and default_rigor_profile to OwlBearSettings. 3 presets: lean/standard/thorough per docs/rigor-profiles-research.md §3.4.@nAC:@n- [ ] RigorProfile model with 3 fields@n- [ ] rigor_profiles dict on OwlBearSettings with lean/standard/thorough presets@n- [ ] default_rigor_profile field defaults to 'standard'@n- [ ] Validated: unknown profile name raises ValueError@n- [ ] Tests cover all 3 presets + default fallback" --status backlog

kanban\kanban-md.exe create "Add rigor_profile to OwlBearDeps" --priority needed --tags "scope:core,config,phase-7" --body "Add rigor_profile: RigorProfile field to OwlBearDeps dataclass. Propagate through DelegationToolset child deps. See docs/rigor-profiles-research.md §3.5.@nDepends on: RigorProfile config model task.@nAC:@n- [ ] OwlBearDeps has rigor_profile field with default standard profile@n- [ ] DelegationToolset copies rigor_profile to child deps@n- [ ] Tests verify profile propagation through delegation" --status backlog

kanban\kanban-md.exe create "Resolve rigor profile from kanban tags at dispatch" --priority needed --tags "scope:core,config,phase-7" --body "In poll_tick() and orchestrator routing, read task kanban tags for rigor:lean/rigor:thorough override. Resolution order: tag > default_rigor_profile > standard. Warn on unknown rigor: tags. See docs/rigor-profiles-research.md §3.6.@nDepends on: RigorProfile config model + OwlBearDeps tasks.@nAC:@n- [ ] poll_tick reads rigor: tag from task metadata@n- [ ] Unknown rigor: tag logs warning and falls back to default@n- [ ] Resolution order: tag > config default > standard@n- [ ] Tests cover tag override, missing tag fallback, unknown tag warning" --status backlog

kanban\kanban-md.exe create "Gate reviewer/writer dispatch on rigor profile" --priority needed --tags "scope:core,config,phase-7" --body "When rigor_profile.review_enabled is False, orchestrator skips reviewer delegation. When docs_gate_enabled is False, skip writer delegation. Task moves directly to done. See docs/rigor-profiles-research.md §3.5.@nDepends on: rigor tag resolution task.@nAC:@n- [ ] Lean profile skips reviewer agent@n- [ ] Lean profile skips writer agent@n- [ ] Standard/thorough profiles run full pipeline@n- [ ] Tests verify gate skipping for lean profile" --status backlog
```
