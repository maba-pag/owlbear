# deer-flow Broad Survey: Architecture, Context Engineering, Guardrails, Tooling

> **Owning task:** #429 — deer-flow broad survey: architecture, context engineering, guardrails, tooling patterns
> **Date:** 2026-04-01 **Status:** Complete
> **Scope:** Everything EXCEPT memory system and subagent delegation (covered in #428)
> **Prior art:** docs/research/deer-flow-adoptable-patterns.md (#386, rapid overview)

## 1. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| deer-flow repo (v2 main, cloned) | github.com/bytedance/deer-flow | Primary — full codebase (.95) |
| deer-flow test_harness_boundary.py | In-repo: backend/tests/test_harness_boundary.py | Boundary enforcement pattern (.90) |
| deer-flow skills/validation.py | In-repo: packages/harness/deerflow/skills/validation.py | Skill validation patterns (.85) |
| LangChain SummarizationMiddleware | LangChain agents middleware (bundled in deer-flow) | Context summarization design (.80) |
| OwlBear validate_skills.py | scripts/validate_skills.py | Current OwlBear validation baseline (.95) |
| OwlBear agent-common.instructions.md | instructions/agent-common.instructions.md | Existing loop/error handling (.95) |

## 2. Areas Surveyed

### 2A. Harness/App Boundary Enforcement (.80 confidence)

**deer-flow:** Strict split between `packages/harness/deerflow/` (publishable framework) and `app/` (application). CI test (`test_harness_boundary.py`, ~50 LOC) uses AST parsing to scan every `.py` file in harness for `from app.` or `import app.` statements. Fails on any violation.

**OwlBear:** Six packages under `packages/` with no automated import boundary enforcement. Cross-package coupling could silently accumulate.

**Verdict: Adopt (.80).** A simple AST-based test prevents architectural decay. ~50 LOC, no dependencies, CI-runnable. Define allowed import directions between OwlBear packages.

### 2B. Middleware Chain Pattern (.50 confidence)

**deer-flow:** 14 ordered middlewares (LangGraph `AgentMiddleware`) wrapping agent lifecycle. Each middleware has `wrap_tool_call` / `wrap_model_call` hooks. Order enforced programmatically.

**OwlBear:** No middleware chain — behavior via instructions, skills, and VS Code's agent system. The _specific behaviors_ deer-flow implements as middlewares (loop detection, error handling) are already adopted via agent instructions (#432, #433, #434).

**Verdict: Don't adopt (.50).** Wrong architecture model. OwlBear's instruction-based approach achieves the same outcomes without runtime middleware.

### 2C. GuardrailProvider Protocol (.55 confidence)

**deer-flow:** Clean protocol: `GuardrailRequest` (tool_name, tool_input, agent_id, thread_id) → `GuardrailProvider.evaluate()` → `GuardrailDecision` (allow/deny + structured reasons). `AllowlistProvider` for zero-dep filtering. `fail_closed=True` default. Denied calls return error ToolMessage so agent can adapt.

**OwlBear:** Tool authorization via VS Code's `tools:` field in `.agent.md`. No runtime tool-call inspection. VS Code manages tool safety.

**Verdict: Note for future (.55).** Premature for OwlBear's current VS Code-native model. The protocol design (Request/Decision dataclasses, structured reasons, fail-closed default) is worth adopting if OwlBear ever adds direct code execution or custom tool auth.

### 2D. Skill Validation Hardening (.75 confidence)

**deer-flow:** `validation.py` enforces: property allowlist (8 allowed keys), naming convention (hyphen-case, no consecutive hyphens, max 64 chars), required fields (name, description), description safety (rejects HTML tags).

**OwlBear:** `validate_skills.py` strips OwlBear vendor fields and delegates to `skills_ref/` validator. No naming convention enforcement, no description safety checks, no max length.

**Verdict: Adopt (.75).** Enhance `validate_skills.py` with: hyphen-case naming enforcement, max name length (64 chars), description safety checking (reject HTML). Low effort, prevents drift.

### 2E. Context Summarization (.65 confidence)

**deer-flow:** `SummarizationMiddleware` with configurable triggers: message count, token count, or fraction of model max tokens. Keep-recent policy: preserve N most recent messages after summarizing older ones. Uses lightweight model for cost savings.

**OwlBear:** Long orchestration sessions accumulate context. VS Code manages context window opaquely (truncation). No explicit summarization control.

**Verdict: Research further (.65).** Relevant problem, uncertain solution. VS Code's context management may already handle this. Needs investigation into what VS Code does natively before building custom summarization.

### 2F. Progressive Skill Loading / State Management (.50 confidence)

**deer-flow:** Skills scanned from `public/` and `custom/` dirs. `ExtensionsConfig` manages enabled/disabled state per skill. `.skill` archive installation with zip safety validation.

**OwlBear:** Skills auto-load by relevance via VS Code's `description` matching. No enabled/disabled toggle needed — `user-invocable: false` hides pipeline-only skills. No archive installation.

**Verdict: Don't adopt (.50).** VS Code handles skill discovery and loading. The pattern doesn't map to OwlBear's architecture.

### 2G. Sandbox Audit / Command Classification (.45 confidence)

**deer-flow:** `SandboxAuditMiddleware` classifies bash commands as block/warn/pass using regex patterns. High-risk (rm -rf /, curl|sh) blocked. Medium-risk (pip install) warned. Structured audit log.

**OwlBear:** No bash execution. VS Code's built-in tool safety handles authorization.

**Verdict: Don't adopt (.45).** Not applicable — OwlBear doesn't execute arbitrary shell commands.

### 2H. Config Auto-Reload via mtime (.40 confidence)

**deer-flow:** `get_app_config()` tracks config file mtime. Reloads on change. Same pattern for MCP cache and extensions config.

**OwlBear:** Stateless/on-demand. Reads fresh state each cycle. No persistent process to reload into.

**Verdict: Don't adopt (.40).** Not applicable to OwlBear's model.

### 2I. Embedded Python Client (DeerFlowClient) (.35 confidence)

**deer-flow:** In-process client with `chat()` and `stream()`. No HTTP/Gateway needed. Conformance tests.

**OwlBear:** Uses `copilot --acp --stdio` (CLI+NDJSON). Different integration model.

**Verdict: Don't adopt (.35).** Different architecture. OwlBear's CLI integration is appropriate.

### 2J. Reflection / Dynamic Class Resolution (.40 confidence)

**deer-flow:** `resolve_variable()` and `resolve_class()` load Python objects from string paths with dependency hints.

**OwlBear:** No plugin architecture requiring dynamic resolution.

**Verdict: Don't adopt (.40).** No current need. Note for future plugin extensibility.

## 3. Comparison: Top Patterns

| Pattern | Confidence | Effort | Impact | Adoption? |
|---------|-----------|--------|--------|-----------|
| Package boundary test | .80 | ~1 day | High — prevents coupling | **Yes** |
| Skill validation hardening | .75 | ~0.5 day | Medium — prevents drift | **Yes** |
| Context summarization | .65 | ~3 days (research + build) | Medium — improves long sessions | **Research first** |
| GuardrailProvider protocol | .55 | ~3 days | Low (no current need) | **Note for future** |
| Progressive skill loading | .50 | N/A | N/A (VS Code handles) | **No** |

## 4. Recommendation

**Top 2 immediate adoptions (T1):** Package boundary enforcement test and skill validation hardening. Both are low-effort, high-confidence improvements to existing infrastructure.

**Top research-first item (T2/T3):** Context summarization for orchestration sessions. Needs investigation into VS Code's native context handling before committing to implementation.

**Decision request:** Created at `docs/decisions/pending/429-deer-flow-patterns-adoption.md` for user to approve top patterns.

## 5. Follow-up Tasks

Created at `ideation` status (T1 items — autonomous):

```
kanban\kanban-md.exe create "Add AST-based package boundary enforcement test" ...
kanban\kanban-md.exe create "Harden skill validation with deer-flow patterns" ...
```

Decision request covers T2/T3 items (context summarization, guardrail protocol future planning).
