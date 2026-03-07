# Validator Role Policy Expansion Research

> **Owning task:** #524 — Expand validator role policy denied tools
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

ARC-20 identified that `VALIDATOR_POLICY` in `src/owlbear/core/roles.py` only denies `write_file` and `create_file`. A validator agent could still call `run_command`, `git_commit`, `git_push`, `browser_click`, `browser_type`, and other destructive tools. The question: should we expand the deny-list, or switch to an allow-list model?

**Additional finding:** No agent definition currently declares `role: validator` — all 8 agents default to `role: builder`. The validator role is infrastructure waiting to be used (e.g., by reviewer, writer, auditor agents). The policy must be correct before agents adopt it.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OWASP LLM06:2025 Excessive Agency | <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/> | .95 |
| 2 | NVIDIA NeMo-Guardrails security guidelines | <https://github.com/NVIDIA/NeMo-Guardrails/blob/main/docs/security/guidelines.md> | .70 |
| 3 | OwlBear `roles.py` — current implementation | `src/owlbear/core/roles.py` | 1.0 |
| 4 | OwlBear `agent_registry.py` — policy application | `src/owlbear/core/agent_registry.py` | 1.0 |
| 5 | OwlBear `architecture-audit.md` ARC-20 | `docs/architecture-audit.md` lines 213-220 | 1.0 |

## 3. Complete Tool Inventory by Toolset

| Toolset | Tool name | Mutating? | Risk for validator |
|---------|-----------|-----------|-------------------|
| FileToolset | `read_file` | No | Safe |
| FileToolset | `write_file` | **Yes** | Already denied |
| FileToolset | `create_file` | **Yes** | Already denied |
| FileToolset | `list_directory` | No | Safe |
| FileToolset | `search_files` | No | Safe |
| TerminalToolset | `run_command` | **Yes** | **Arbitrary shell execution** |
| GitLocalToolset | `git_status` | No | Safe |
| GitLocalToolset | `git_diff` | No | Safe |
| GitLocalToolset | `git_log` | No | Safe |
| GitLocalToolset | `git_add` | **Yes** | Stages files |
| GitLocalToolset | `git_commit` | **Yes** | Creates commits |
| GitLocalToolset | `git_branch` | **Yes** | Creates branches |
| GitLocalToolset | `git_push` | **Yes** | Pushes to remote |
| BrowserToolset | `browser_navigate` | **Yes** | Navigation with side effects |
| BrowserToolset | `browser_click` | **Yes** | Triggers UI actions |
| BrowserToolset | `browser_type` | **Yes** | Fills form inputs |
| BrowserToolset | `browser_select` | **Yes** | Selects options |
| BrowserToolset | `browser_read_text` | No | Safe |
| BrowserToolset | `browser_screenshot` | No | Safe |
| GitHubToolset | `create_pr` | **Yes** | Creates pull requests |
| GitHubToolset | `list_prs` | No | Safe |
| GitHubToolset | `list_issues` | No | Safe |
| GitHubToolset | `get_issue` | No | Safe |
| KanbanToolset | `kanban_list` | No | Safe |
| KanbanToolset | `kanban_show` | No | Safe |
| KanbanToolset | `kanban_create` | **Yes** | Creates tasks |
| KanbanToolset | `kanban_move` | **Yes** | Changes task status |
| KanbanToolset | `kanban_edit` | **Yes** | Edits task content |
| KanbanToolset | `kanban_pick` | **Yes** | Claims tasks |
| KanbanToolset | `kanban_context` | No | Safe |
| KnowledgeToolset | `query_knowledge` | No | Safe |
| KnowledgeToolset | `ingest_document` | **Yes** | Writes to knowledge base |
| KnowledgeToolset | `list_knowledge_sources` | No | Safe |
| KnowledgeSourceToolset | `add_source` | **Yes** | Registers sources |
| KnowledgeSourceToolset | `list_sources` | No | Safe |
| KnowledgeSourceToolset | `refresh_source` | **Yes** | Triggers ingestion |
| BookmarkToolset | `bookmark_source` | **Yes** | Creates bookmarks |
| BookmarkToolset | `list_bookmarks` | No | Safe |
| WebSearchToolset | `web_search` | No | Safe |
| WebSearchToolset | `web_read` | No | Safe |
| ProjectToolset | `switch_project` | **Yes** | Changes CWD + toolset roots |
| ProjectToolset | `list_projects` | No | Safe |
| ProjectToolset | `workspace_create_project` | **Yes** | Scaffolds directories |
| VisualFeedbackToolset | `share_screenshot` | **Yes** | Saves files + sends |
| VisualFeedbackToolset | `share_terminal_output` | **Yes** | Saves files + sends |
| DelegationToolset | `delegate_to_agent` | **Yes** | Can invoke builder agents |

## 4. Analysis: Allow-list vs Deny-list

| Criterion | Deny-list (expand current) | Allow-list (invert model) |
|-----------|---------------------------|--------------------------|
| **Safety default** | Unsafe — new tools are allowed until denied | **Safe — new tools are denied until allowed** |
| **Maintenance** | Must remember to deny each new tool | Must remember to allow each new tool |
| **Failure mode** | Validator gains unintended power (bad) | **Validator loses needed tool (recoverable)** |
| **OWASP alignment** | Partially aligned (still "excessive functionality") | **Fully aligned with LLM06 "minimize extensions"** |
| **Complexity** | Low — one `frozenset` | Low — one `frozenset` + changed filter logic |
| **KISS** | Simpler data, riskier semantics | Same complexity, safer semantics |

**OWASP LLM06:2025 guidance (Source 1):** "Limit the extensions that LLM agents are allowed to call to only the minimum necessary." "Avoid the use of open-ended extensions." "Limit the functions that are implemented in LLM extensions to the minimum necessary." These all point toward allow-list.

**NVIDIA NeMo-Guardrails (Source 2):** Recommends scoped action permissions where agents only access tools explicitly granted, matching allow-list semantics.

## 5. Recommendation (.90 confidence)

**Switch `RolePolicy` to an allow-list model.** Add an `allowed_tools` field alongside (or replacing) `denied_tools`. When `allowed_tools` is non-empty, only those tools are available. This is a minimal change to `roles.py` + `apply_role_policy`.

### Proposed validator allow-list

These are the tools a validator (reviewer, writer, auditor) legitimately needs:

| Tool | Rationale |
|------|-----------|
| `read_file` | Read source code and tests |
| `list_directory` | Browse workspace structure |
| `search_files` | Find files by pattern |
| `git_status` | Check working tree state |
| `git_diff` | Review changes |
| `git_log` | Review commit history |
| `browser_read_text` | Read page content for verification |
| `browser_screenshot` | Capture evidence screenshots |
| `query_knowledge` | Search knowledge base |
| `list_knowledge_sources` | Check knowledge sources |
| `list_bookmarks` | Check bookmarks |
| `web_search` | Research verification |
| `web_read` | Read web pages |
| `kanban_list` | View board state |
| `kanban_show` | Read task details |
| `kanban_context` | Board context |
| `list_prs` | Check PR state |
| `list_issues` | Check issues |
| `get_issue` | Read issue details |
| `list_projects` | View projects |
| `list_sources` | View sources |
| `delegate_to_agent` | May need to delegate |

**Note:** `kanban_move` and `kanban_edit` are intentionally excluded — validators should report findings, not directly mutate tasks. If specific validator agents (e.g., auditor) need `kanban_move`, use a separate `AUDITOR_POLICY` with targeted additions. `run_command` is excluded — validators use `git_status`/`git_diff`/`git_log` for verification, not arbitrary shell access.

### Risk: `delegate_to_agent`

Including `delegate_to_agent` on the allow-list means a validator could delegate to a builder, indirectly gaining write access. Mitigation options:

- Exclude it from the validator allow-list (simplest).
- Or: the delegation target inherits the caller's role policy (requires deeper changes).

**Recommendation:** Exclude `delegate_to_agent` for now (.85 confidence). Validators report findings; orchestrator handles re-dispatch.

## 6. Implementation Approach

1. Add `allowed_tools: frozenset[str]` to `RolePolicy` (default empty = no allowlist restriction).
2. Update `apply_role_policy` filter: if `allowed_tools` is non-empty, tool must be in `allowed_tools` AND not in `denied_tools`.
3. Define `VALIDATOR_POLICY` with the allow-list above (drop the 2-item deny-list).
4. Add `AUDITOR_POLICY` variant if auditor needs `kanban_move` + `kanban_edit`.
5. Update agent definitions to assign `role: validator` to reviewer, writer, and optionally auditor.
6. Add tests verifying the allow-list filters correctly.

## 7. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement allow-list model for RolePolicy" --priority needed --tags "security,scope:core,phase-13" --body "Add allowed_tools field to RolePolicy. When non-empty, only listed tools pass apply_role_policy filter. Update VALIDATOR_POLICY with read-only allow-list (see docs/validator-role-policy-research.md section 5). Update apply_role_policy filter logic. AC: (1) RolePolicy supports allowed_tools frozenset, (2) apply_role_policy filters to intersection of allowed minus denied, (3) VALIDATOR_POLICY uses allow-list of ~22 read-only tools, (4) tests verify new tool added to toolset is NOT available to validator by default."

kanban\kanban-md.exe create "Assign validator role to read-only agents" --priority needed --tags "security,scope:core,phase-13" --depends-on 524 --body "Update agent definitions for reviewer, writer, and auditor to declare role: validator. Consider AUDITOR_POLICY variant if auditor needs kanban_move/kanban_edit. AC: (1) reviewer.agent.md has role: validator, (2) writer.agent.md has role: validator, (3) auditor role assignment decided and applied, (4) integration test confirms filtered toolsets."

kanban\kanban-md.exe create "Add tests for expanded role policy" --priority needed --tags "test,security,scope:core,phase-13" --depends-on 524 --body "Unit tests for allow-list RolePolicy behavior. AC: (1) test allowed_tools filters correctly, (2) test denied_tools still works for builder, (3) test new-tool-default-denied for validator, (4) test empty allowed_tools means no restriction, (5) coverage >= 90% for roles.py."
```
