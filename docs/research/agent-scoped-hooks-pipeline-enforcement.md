# Agent-Scoped Hooks for Pipeline Enforcement

> **Owning task:** #86 — Evaluate agent-scoped hooks for pipeline enforcement (scoped AC)
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

OwlBear's CI pipeline runs through 11 agents in a strict sequence
(`ideation → backlog → todo → in-progress → review → docs → done`). Enforcement of
quality gates, task-claiming discipline, and commit hygiene currently relies entirely on
agent instructions and human oversight. VS Code agent-scoped hooks (preview) offer a
mechanism to reinforce these behaviors automatically.

**Two distinct hook layers exist in OwlBear** (per architect's note in task #86):

| Layer | Location | Mechanism | Blocking? |
|-------|----------|-----------|-----------|
| **Internal HookRegistry** | `src/owlbear/core/hooks.py` | Python pub-sub; `HookEvent` enum + callbacks | Observational only — non-blocking by design (architecture-standards) |
| **VS Code agent-scoped hooks** | `.agent.md` frontmatter `hooks:` key | Prompt injection into agent context at lifecycle events | Soft enforcement only — prompt injection, not exit codes |

These are different mechanisms serving different purposes. This document covers only the
VS Code layer. Do not conflate them; enforcing blocking behavior via VS Code hooks is not
aligned with the internal HookRegistry contract.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Hooks docs | https://code.visualstudio.com/docs/copilot/customization/hooks | .85 — canonical agent-scoped hook spec |
| VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .95 — hook field in .agent.md |
| OwlBear agent-md-format research (#4) | `docs/research/agent-md-format.md` §7 | 1.0 — prior hooks survey with examples |
| nWave-ai/nWave research (#589) | `docs/research/nwave.md` §3.3 | .75 — DES pre/postToolUse enforcement pattern |
| OwlBear agent-common.instructions.md | `instructions/agent-common.instructions.md` | 1.0 — current pipeline discipline model |

## 3. VS Code Hook Capabilities and Constraints

### 3.1 Hook Types

| Hook Type | Trigger | Typical Use |
|-----------|---------|-------------|
| `preToolUse` | Before a tool invocation executes | Warn agent before performing an action |
| `postToolUse` | After a tool invocation completes | Trigger follow-up checks after an action |
| `stop` | When an agent session ends | End-of-session reminders, commit guards |

### 3.2 Hook Definition Format

Hooks are declared under the `hooks:` key in `.agent.md` YAML frontmatter:

```yaml
hooks:
  postToolUse:
    - when: "tool == 'edit/editFiles'"
      prompt: "Run ruff check on the files you just modified."
  stop:
    - prompt: "Before ending, verify you have committed your changes."
```

Each hook entry may include:

- `when` (optional): condition expression that gates whether the hook fires. The condition
  can filter on `tool` name (e.g., `tool == 'edit/editFiles'`).
- `prompt`: text injected into the agent's conversation context when the hook fires.

### 3.3 Constraints and Limitations

| Constraint | Detail | Implication |
|------------|--------|-------------|
| **Preview feature** | Requires `chat.useCustomAgentHooks: true` VS Code setting; API may change | Not suitable for hard production guarantees |
| **Soft enforcement only** | Hooks inject prompts — the model can still ignore them | Cannot replace `tools:` restrictions for hard access control |
| **No blocking** | VS Code hooks do not support exit codes (unlike Claude Code / nWave DES which use code 2 to abort) | Hooks guide behaviour, not enforce it unconditionally |
| **Per-agent scope** | A hook in `builder.agent.md` does not fire for any other agent | Cannot create a cross-agent enforcement layer through this mechanism |
| **Context window cost** | Every hook firing consumes tokens (prompt injected into context) | Overuse on high-frequency tools (e.g., `readFile`) will inflate context significantly |
| **Condition expression syntax** | Only simple equality expressions supported; no content inspection | Cannot detect "did this terminal command run pytest?" from the shell output |
| **Hook execution order** | Multiple entries in the same hook type fire in definition order | Keep hooks short; long prompts compound context bloat |
| **No guaranteed side effects** | Hooks cannot run shell commands (unlike Claude Code RunCommand hook type) | Cannot auto-run tools; must rely on agent following the injected prompt |

## 4. Pipeline Enforcement Candidates

### Candidate 1 — PostToolUse Lint Guard (builder)

**What it does:** After the builder edits a source file, inject a reminder to run ruff
before continuing.

```yaml
# builder.agent.md
hooks:
  postToolUse:
    - when: "tool == 'edit/editFiles' || tool == 'edit/createFile'"
      prompt: |
        You just modified source files. Run:
          uv run ruff check {modified files}
        before proceeding. Fix any lint errors before your next edit.
```

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Catches lint regressions immediately after each edit rather than at step 7 | 
| **Trade-offs** | Fires after every file edit (even doc edits not needing lint). Multiple edits → multiple injections → context bloat. |
| **Failure modes** | Agent ignores prompt; ruff run fails due to import errors mid-implementation; fires on documentation files where ruff is irrelevant |
| **Effort** | 5 lines in `builder.agent.md` frontmatter |
| **Confidence** | .75 |

### Candidate 2 — PreToolUse Kanban Claim Enforcement (all pipeline agents)

**What it does:** Before any write operation, remind the agent to verify it has claimed
the task on the kanban board.

```yaml
# builder.agent.md (and other pipeline agents)
hooks:
  preToolUse:
    - when: "tool == 'edit/editFiles' || tool == 'edit/createFile'"
      prompt: |
        CHECKPOINT: Before editing files, confirm you have claimed this task with:
          kanban\kanban-md.exe edit {ID} --claim builder
        Do not proceed with code changes without an active claim.
```

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Provides a just-in-time reminder at the exact moment where an unclaimed edit would breach discipline |
| **Trade-offs** | Fires on every file write even after claim is already active — all injections after the first are pure noise. No state awareness (cannot check actual claim status). |
| **Failure modes** | Agent reads the reminder, decides it has already claimed, continues without rechecking. Cannot distinguish claimed vs. unclaimed sessions. |
| **Effort** | 6 lines per agent in frontmatter |
| **Confidence** | .55 — low value due to no state awareness |

### Candidate 3 — Stop Commit Guard (builder, writer)

**What it does:** At session end, remind the agent to commit work before the session
finishes.

```yaml
# builder.agent.md
hooks:
  stop:
    - prompt: |
        Before ending this session, run:
          git status --short
        If there are uncommitted files related to this task, commit them now
        following the commit discipline in agent-common.instructions.md.
```

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Last-chance guard against abandoned uncommitted work; cheap to implement (fires once per session) |
| **Trade-offs** | Fires for every session end, including sessions where no code was written (e.g., research tasks). Only fires once so the agent cannot be re-reminded. |
| **Failure modes** | Agent reaches stop hook after already having committed — prompt is noise. Session may end mid-edit (crash) and the hook fires too late. |
| **Effort** | 4 lines in `builder.agent.md` (and optionally `writer.agent.md`) |
| **Confidence** | .80 — good value-to-noise ratio, limited to 1 fire per session |

### Candidate 4 — PostToolUse Test Coverage Reminder (builder)

**What it does:** After pytest runs via the terminal, remind the builder to check coverage.

```yaml
# builder.agent.md
hooks:
  postToolUse:
    - when: "tool == 'execute/runInTerminal'"
      prompt: |
        If you just ran pytest, check the coverage output. Coverage must be ≥ 90%
        on touched modules before advancing to review.
```

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Reinforces the 90% coverage gate as a post-test reminder |
| **Trade-offs** | Fires after every terminal command, not just pytest. Any `kanban-md.exe` run, `git` command, or `uv run ruff` will also trigger this prompt. High noise ratio. |
| **Failure modes** | Cannot detect whether the terminal command was actually pytest; no condition expression targeting command content. Context bloat from every terminal invocation. |
| **Effort** | 4 lines, but creates a high-noise hook |
| **Confidence** | .45 — too noisy for the terminal tool scope |

### Candidate 5 — PreToolUse Read-Only Guard (reviewer)

**What it does:** Before a write tool fires in the reviewer's context, inject a hard
stop reminder.

```yaml
# reviewer.agent.md
hooks:
  preToolUse:
    - when: "tool == 'edit/editFiles' || tool == 'edit/createFile'"
      prompt: |
        STOP. You are the reviewer agent. Your role is read-only verification.
        Do NOT edit source files. If a fix is needed, note it in the task body
        and return FAIL with the specific issue.
```

| Dimension | Assessment |
|-----------|-----------|
| **Value** | Reinforces the reviewer's read-only contract at exactly the moment where a violation would occur |
| **Trade-offs** | The reviewer's `tools:` list in frontmatter already restricts `edit/editFiles` — this hook is redundant if tool restrictions are correct |
| **Failure modes** | If the reviewer does not have edit tools in its tool list, this hook fires on an unreachable code path (no risk but wasted config). If edit tools are accidentally granted, the hook is the right fallback defense. |
| **Effort** | 5 lines in `reviewer.agent.md` |
| **Confidence** | .65 — useful as defense-in-depth only; primary enforcement is `tools:` restriction |

## 5. Recommendation Matrix

| Candidate | Hook Type | Agent | Value | Noise | Effort | Confidence | Recommendation |
|-----------|-----------|-------|-------|-------|--------|------------|----------------|
| C1: PostToolUse lint guard | postToolUse | builder | High | Medium | Low | .75 | **Adopt (Phase 2)** |
| C2: PreToolUse claim enforcement | preToolUse | all pipeline | Low | High | Medium | .55 | Skip |
| C3: Stop commit guard | stop | builder, writer | Medium | Low | Low | .80 | **Adopt (Phase 1)** |
| C4: PostToolUse test coverage | postToolUse | builder | Low | High | Low | .45 | Skip |
| C5: PreToolUse read-only guard | preToolUse | reviewer | Medium | Low | Low | .65 | Adopt (Phase 2, defense-in-depth) |

### Recommended Path (.80 confidence)

**Enable hooks in two phases, starting with lowest-noise, highest-value hooks.**

**Phase 1 (MVP — stop hook only):**
- Add the stop commit guard to `builder.agent.md` and `writer.agent.md`
- One hook entry fires once per session — essentially zero context cost
- Catches the most common pipeline discipline failure: sessions that end without committing

**Phase 2 (selective postToolUse):**
- Add the PostToolUse lint guard to `builder.agent.md` but gate it narrowly on file edits only
- Optionally add the preToolUse read-only guard to `reviewer.agent.md` as defense-in-depth
- Monitor context window usage; if context inflation becomes measurable, remove postToolUse hooks

**Skip permanently:**
- C2 (claim enforcement via preToolUse): zero state awareness — cannot distinguish claimed from unclaimed; every firing is noise
- C4 (coverage reminder via terminal postToolUse): fires on every terminal command, not just pytest

## 6. Rollout Guidance

### Prerequisites

1. All agent files must be in `agents/*.agent.md` and tracked in git
2. Agents must be using correct tool names (no `todo` → `todos` regression — confirmed fixed by #36)
3. VS Code version must support `chat.useCustomAgentHooks` — verify in VS Code Copilot changelog
4. Team/user understands that hooks inject prompts (soft enforcement), not block tool execution

### Required Settings

Add to `.vscode/settings.json`:

```json
"chat.useCustomAgentHooks": true
```

This setting is a global opt-in for all agent-scoped hooks in the workspace. Without it,
all `hooks:` frontmatter blocks are silently ignored.

### Phased Adoption Plan

| Phase | Scope | Files Changed | Risk |
|-------|-------|--------------|------|
| Phase 1 | Enable stop hooks on builder + writer | `agents/builder.agent.md`, `agents/writer.agent.md` | Very low — 1 prompt per session end |
| Phase 2 | Add postToolUse lint guard on builder | `agents/builder.agent.md` | Low-medium — monitor context inflation |
| Phase 3 | Add preToolUse read-only guard on reviewer | `agents/reviewer.agent.md` | Very low — defense-in-depth |

Each phase should be merged separately and observed for:
- Unexpected context window inflation
- Hooks firing on unintended tool invocations
- Agents acting confused by conflicting prompt signals

### When Not to Use Hooks

Do not use VS Code agent-scoped hooks when:

1. **Hard blocking is required.** VS Code hooks inject prompts — they cannot exit with a failure code. If a behaviour must be unconditionally enforced (e.g., reviewer must never edit files), use `tools:` restrictions in the agent's frontmatter, not hooks.
2. **Cross-agent enforcement is needed.** Hooks apply only to the agent that defines them. A hook on `builder.agent.md` does not fire when the orchestrator invokes a subagent. Use `instructions/agent-common.instructions.md` rules for cross-agent policy.
3. **Stateful checks are required.** Hooks cannot query external state (kanban board, git status). A claim-enforcement hook cannot verify whether the agent has actually claimed the task. Stateless reminders are fine; guards requiring current state must be implemented in agent instructions or skills.
4. **High-frequency tools are involved.** postToolUse on `read/readFile` or `execute/runInTerminal` would inject a prompt on every file read or terminal command — likely 20–50+ times per session. Context cost is prohibitive. Gate on the most specific tool name available.
5. **The hook would duplicate existing instruction coverage.** If `agent-common.instructions.md` already covers the behaviour (e.g., "commit before advancing"), a hook adds noise without adding enforcement power. Reserve hooks for behaviour that agents demonstrably forget mid-session.

## 7. Conclusion

VS Code agent-scoped hooks are a useful but limited tool. They excel as low-noise,
end-of-session reminders (the `stop` hook) and targeted mid-session nudges for a
specific critical action. They are not suitable for hard enforcement, cross-agent policy,
or stateful checks.

**Adopt the stop commit guard (Phase 1) immediately.** It is the highest-value, lowest-cost
hook configuration available. Phase 2 (lint guard) adds value but requires monitoring.
Skip all candidates that rely on state awareness or fire on high-frequency tools.

The internal HookRegistry (`core/hooks.py`) remains the correct mechanism for
observational, structured event handling within OwlBear's Python runtime. VS Code hooks
complement it at the agent-conversation layer but must not be treated as equivalent.
