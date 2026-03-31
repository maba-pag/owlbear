# Fix-Attempt Agent Design Validation

> **Owning task:** #318 — Create fix-attempt.agent.md with assign-mode tools
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #318 specifies a `fix-attempt.agent.md` — a fresh-context subagent invoked by the builder after 2 same-context failures. The parent research (`docs/research/fresh-context-retry-builder.md`, task #266) defined the overall design. This research **validates the AC** against the research checklist and identifies implementation-ready refinements.

**Prerequisite:** Decision request `docs/decisions/pending/228-fresh-context-retry.md` (Option A: threshold=2) is still pending (`approved: false`). Implementation should not start until approved.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — coordinator/worker, assign mode, nesting depth 5 |
| S2 | VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — agents array overrides disable-model-invocation |
| S3 | Reflexion (Shinn et al., 2023) | https://arxiv.org/abs/2303.11366 | .90 — verbal reinforcement: feedback replaces weight updates |
| S4 | SupaConductor Evaluate-Loop | https://github.com/Ibrahim-3d/orchestrator-supaconductor | .80 — Execute→Evaluate→Fix cycle (max 3), fixer as separate step |
| S5 | OwlBear fresh-context-retry-builder.md | docs/research/fresh-context-retry-builder.md | 1.0 — parent design: tool list, I/O contracts, integration flow |
| S6 | OwlBear subagent-nesting-architecture.md | docs/research/subagent-nesting-architecture.md | .95 — assign mode (.80 conf), nesting validation, threshold=2 |

## 3. Analysis

### 3a. AC Validation

| AC Item | Valid | Confidence | Notes |
|---------|-------|------------|-------|
| 1. Agent file with persona + assign tools + workflow | ✓ | .90 | 9 tools confirmed (S5 §3c, S6 §3c) |
| 2. user-invocable: false, disable-model-invocation: true | ✓ | .90 | More restrictive than S6 recommendation; builder agents array override works per S2 |
| 3. Output: FIXED/FAILED + files_changed + evidence | ✓ | .85 | Aligns with Channel A; matches Conductor Fix step outcome (S4) |
| 4. Input: task_id, test_file, source_files, retry_hint, error_summary | ✓ | .85 | retry_hint follows Reflexion verbal feedback pattern (S3) |
| 5. Max 1 internal retry | ✓ | .80 | fix-attempt IS the fresh perspective — 1 retry keeps cost bounded |
| 6. Never touches kanban | ✓ | .95 | Enforced by excluding owlbear-kanban/* from tool assignment |

### 3b. Tool List Validation

The 9 tools (S5 §3c) — builder tools minus kanban, minus non-essential tools:

| Tool | Purpose | Needed? |
|------|---------|---------|
| vscode/memory | Access repo conventions, instruction files | Yes |
| execute/runInTerminal | Run pytest, ruff | Yes |
| execute/getTerminalOutput | Read terminal results | Yes |
| execute/awaitTerminal | Wait for test completion | Yes |
| execute/killTerminal | Clean up terminals | Yes |
| read/readFile | Read source and test files | Yes |
| edit/editFiles | Apply code fixes | Yes |
| edit/createFile | Create new files if needed | Yes |
| search | Find related code | Yes |

**Excluded tools (justified):**

| Tool | Reason excluded |
|------|----------------|
| owlbear-kanban/* | AC #6 — never touches board |
| agent | No further delegation — fix-attempt is L2 bottom |
| execute/runTests | Redundant — runInTerminal handles pytest invocation |
| execute/testFailure | Builder handles test failure semantics |
| execute/createAndRunTask | Task management is builder's concern |
| read/problems | YAGNI — pytest output sufficient; add later if needed |
| read/viewImage | Not relevant to code repair |
| read/terminalLastCommand | Not needed with explicit getTerminalOutput |
| edit/createDirectory | createFile auto-creates dirs |
| edit/rename | Fix-attempt repairs code, doesn't reorganize files |

### 3c. Security Restriction Design

The AC specifies `disable-model-invocation: true` — stricter than the nesting research recommendation (S6 §4 recommended `false`). This is **intentionally better**: only the builder can invoke fix-attempt via explicit `agents: ['fix-attempt']` override (S2). Other pipeline agents cannot accidentally spawn it.

### 3d. Gaps and Refinements

| Gap | Impact | Recommendation |
|-----|--------|---------------|
| Model not specified in AC | Low | Use builder's model list: `[Claude Sonnet 4.6 (copilot), GPT-5.3-Codex (copilot)]` — code repair needs capable models |
| `agents: []` not in AC | Low | Should be explicit in frontmatter to prevent delegation chains |
| Decision #228 pending | Medium | Task depends on parent #266 (backlog); implementation blocked until decision approved |

## 4. Recommendation (.85 confidence)

AC is **implementation-ready** with two minor additions: explicit `agents: []` and model specification matching the builder. The 9-tool assign set is well-justified — minimal, KISS-aligned, security-enforced. The Reflexion-inspired retry_hint (S3) and Conductor's separate Fix step (S4) confirm the pattern's soundness across multiple independent implementations.

**Risk:** Decision request #228 is still pending. If rejected (e.g., Option D: do nothing), tasks #318–#320 become invalid. Mitigation: architect should verify decision status before advancing to todo.

## 5. Follow-up Tasks

No new follow-up tasks needed — #319 (builder delegation) and #320 (tests) already exist with correct dependencies on #318. Architect should verify the AC addenda (model, agents: []) during gate review.
