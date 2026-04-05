# Multi-Project Setup Test — Validation Research

> **Owning task:** #25 — Multi-project setup test
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #25 validates the "clone = install" distribution model end-to-end: run `setup.py` from a test project, verify agents/skills/MCP servers work from the project context. Key questions: what's already tested, what requires manual validation, how should the project-specific override mechanism work, and what are the risks?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Copilot customization docs | <https://code.visualstudio.com/docs/copilot/copilot-customization> | .95 |
| 2 | VS Code custom agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | .95 |
| 3 | VS Code agent skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | .90 |
| 4 | VS Code custom instructions docs | <https://code.visualstudio.com/docs/copilot/customization/custom-instructions> | .90 |
| 5 | VS Code MCP configuration reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | .90 |
| 6 | Task #12 (setup script, archived) | `kanban/tasks/012-*.md` | 1.0 |
| 7 | Task #18 (MCP server registry, review) | `kanban/tasks/018-*.md` | .95 |
| 8 | Existing setup.py implementation | `scripts/setup.py` | 1.0 |
| 9 | Setup script unit tests (39 passing) | `tests/test_setup_script.py` | 1.0 |
| 10 | Setup script research doc | `docs/research/setup-script.md` | .85 |

## 3. Analysis

### 3.1 What's Already Tested (Unit Level)

Task #12 delivered 39 passing unit tests covering:

| Area | Tests | Status |
|------|-------|--------|
| settings.json with 3 location types | 11 tests | PASS |
| mcp.json with 4 servers (camelCase) | 8 tests | PASS |
| kanban dir, config reset, setup.ps1 | 6 tests | PASS |
| copilot-instructions.md | 4 tests | PASS |
| Idempotency (merge, skip) | 5 tests | PASS |
| Standalone invocation (__main__) | 4 tests | PASS |
| Path detection | 1 test | PASS |

**All scriptable validation from AC items 1–4 is already covered.** No additional automated tests needed.

### 3.2 VS Code Resolution Mechanisms (from docs)

| Mechanism | Setting | How VS Code resolves |
|-----------|---------|---------------------|
| Agents | `chat.agentFilesLocations` | Recursively searches listed dirs for `.agent.md` files (Source 2) |
| Skills | `chat.agentSkillsLocations` | Recursively searches listed dirs for `SKILL.md` files (Source 3) |
| Instructions | `chat.instructionsFilesLocations` | Recursively searches listed dirs for `*.instructions.md` files (Source 4) |
| MCP servers | `.vscode/mcp.json` | stdio servers started on-demand when tools invoked (Source 5) |
| copilot-instructions | `.github/copilot-instructions.md` | Auto-detected in workspace root; priority: personal > repo > org (Source 4) |

All three `chat.*Locations` settings accept relative paths resolved from workspace root. The setup script generates paths like `../owlbear/agents` — standard documented usage (Sources 2, 3, 4).

### 3.3 Project-Specific Agent Override

VS Code loads agents from ALL configured locations simultaneously (Source 2). A project with `.github/agents/` and `chat.agentFilesLocations` pointing to owlbear gets agents from both.

**Override behavior:** Same-name agents from different locations are NOT deduplicated by VS Code — both appear. To create a true project override, the project agent would need a distinct name or the project must disable the owlbear location in settings.json. This is a UX concern, not a technical blocker.

**Recommended approach:** Project-specific agents should have unique names (e.g., `project-reviewer.agent.md`) rather than overriding owlbear agents. Document this in the setup guide.

### 3.4 MCP Server Readiness

| Server | Module | Status | Startable? |
|--------|--------|--------|-----------|
| owlbearKanban | `owlbear_mcp_kanban` | Archived (#14) | YES |
| owlbearKnowledge | `owlbear_mcp_knowledge` | Not built (#16) | NO (stub) |
| owlbearProject | `owlbear_mcp_project` | Partial (#17) | PARTIAL |

**Risk:** Only owlbearKanban is verified operational. MCP config lists all 4 servers but 2 will fail on start. VS Code handles this gracefully (failed servers show errors but don't block others). Validation can only cover owlbearKanban for now.

### 3.5 AC Categorization

| AC Item | Type | Coverage |
|---------|------|----------|
| Create test project directory | Automated | Unit tests (#12) |
| Run owlbear setup | Automated | Unit tests (#12) |
| Verify settings.json | Automated | Unit tests (#12) |
| Verify mcp.json | Automated | Unit tests (#12) |
| Agents appear in agent picker | **Manual** | Requires VS Code UI |
| Skills auto-load | **Manual** | Requires semantic matching in live session |
| MCP tools callable from chat | **Manual** | Requires live MCP server + Copilot session |
| copilot-instructions.md overrides | **Manual** | Check References section in chat response |
| Project-specific agent override | **Manual** | Add agent to `.github/agents/`, verify in picker |
| Document setup experience | **Docs** | Writing task |
| "How to share owlbear" guide | **Docs** | Writing task |

### 3.6 Known Risks

1. **Cross-drive paths (Windows):** `os.path.relpath` raises `ValueError`. Documented in Source 10 §3.2; acceptable limitation.
2. **Stub MCP servers fail on start:** Non-blocking — VS Code starts servers independently.
3. **Agent name collision:** No dedup between project and owlbear agents. Document the convention.
4. **uv must be on PATH:** `uv run --project {rel}` requires uv installed globally. Setup.py doesn't verify this.

## 4. Recommendation (.85 confidence)

**Decompose #25 into two actionable tasks:**

1. **Manual validation checklist** — A human-executed task (not automatable) that walks through opening a test project in VS Code and verifying each mechanism. Tag `rigor:lean` since it's a checklist, not code.
2. **Documentation** — Write the setup-to-working guide and sharing guide. This can go through the pipeline as a docs task. Tag `type:docs`.

The automated testing from #12 (39 tests) is sufficient for the scriptable parts. No additional pytest tests are needed. The remaining work is purely manual VS Code interaction and documentation writing.

**Diagnostics tip:** VS Code's `Diagnostics` view (right-click Chat view) shows all loaded agents, skills, and instructions with source locations — use this for systematic verification (Source 1).

## 5. Follow-up Tasks

Task 1: Manual validation via checklist
```
kanban\kanban-md.exe create "Validate multi-project setup in VS Code (manual)" --priority important --status ideation --tags "phase-2,scope:build,type:test,rigor:lean" --body "## Objective\nManual validation of the clone=install model. Not automatable — requires opening a test project in VS Code.\n\n## Prerequisites\n- owlbear setup script working (#12 archived)\n- MCP server config in place (#18 in review)\n\n## Acceptance Criteria\n- [ ] Create test-project/ sibling to owlbear, run python ../owlbear/scripts/setup.py\n- [ ] Open test-project/ in VS Code, verify owlbear agents appear in agent picker (use Configure Custom Agents to inspect)\n- [ ] Verify owlbear skills appear via /skills menu or auto-load when asking a relevant question\n- [ ] Verify owlbear instructions load (check Diagnostics view: right-click Chat, select Diagnostics)\n- [ ] Invoke an owlbear-kanban MCP tool from chat (e.g., list_tasks)\n- [ ] Verify .github/copilot-instructions.md content appears in chat References section\n- [ ] Add a test agent to test-project/.github/agents/, verify it appears in picker alongside owlbear agents\n- [ ] Verify project-level agents do NOT shadow owlbear agents (both visible with distinct names)\n- [ ] Clean up test-project/ directory\nSee docs/research/multi-project-setup-test.md for research context." --depends-on 18
```

Task 2: Documentation — setup guide and sharing guide
```
kanban\kanban-md.exe create "Document multi-project setup experience and sharing guide" --priority important --status ideation --tags "phase-2,scope:build,type:docs" --body "## Objective\nWrite end-to-end documentation for the multi-project setup experience and a 'How to share owlbear' guide.\n\n## Acceptance Criteria\n- [ ] docs/setup-guide.md: step-by-step from clone to working (prerequisites, setup.py invocation, VS Code opening, verification steps)\n- [ ] docs/setup-guide.md: troubleshooting section (MCP server fails, agents not appearing, instructions not loading)\n- [ ] docs/setup-guide.md: project-specific customization section (adding local agents, overriding instructions, adding MCP servers)\n- [ ] docs/sharing-guide.md: how to share owlbear with teammates (clone, setup, verify)\n- [ ] Both docs reference the VS Code Diagnostics view for debugging\n- [ ] Both docs note the cross-drive Windows limitation\nSee docs/research/multi-project-setup-test.md for research context."
```
