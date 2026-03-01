# Project Definition Workflow — Structured Idea-to-Spec Pipeline

> **Owning task:** #294 — Project definition workflow — structured idea-to-spec pipeline
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

When a user says "I have an idea: X", OwlBear needs a structured workflow to turn that into an actionable project spec — a `ProjectDefinition` Pydantic model — and then decompose it into kanban tasks. This is the CORE planning loop. The planner agent (#293, done), knowledge toolset (#291, done), and web search toolset (#292, done) are all available.

**Key questions:**

1. Is a Pydantic model the right shape? Should output be structured (`output_type=ProjectDefinition`) or free-form markdown produced by the LLM?
2. How should the workflow be encoded — skill file, system prompt, code, or combination?
3. How do other AI coding tools handle idea→spec flows?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI output docs | <https://ai.pydantic.dev/output/> | .95 | `output_type=SomeModel` for structured output, tool output mode, output validators, streaming structured output |
| gpt-engineer preprompts | <https://github.com/gpt-engineer-org/gpt-engineer/tree/main/gpt_engineer/preprompts> | .85 | `clarify` → `generate` two-phase pipeline; clarify asks one question at a time; philosophy sets coding constraints |
| Devika ARCHITECTURE.md | <https://github.com/stitionai/devika/blob/main/ARCHITECTURE.md> | .85 | Agent Core → Planner → Researcher → Coder pipeline; Planner generates step-by-step plan with focus area; agents are stateless, core manages state |
| aider chat modes | <https://aider.chat/docs/usage/modes.html> | .80 | ask/code workflow — discuss first, execute second; architect mode pairs reasoning model with editor model |
| OwlBear planner agent | `src/owlbear/agents/planner.md` | 1.0 | Current planner system prompt: clarify → elicit → AC → decompose → dependencies → priority |
| OwlBear consolidation.py | `src/owlbear/memory/consolidation.py` | .90 | Proven pattern: `Agent[None, ConsolidationResult]` with `output_type=` for structured extraction |
| OwlBear extractor.py | `src/owlbear/memory/knowledge/extractor.py` | .90 | Proven pattern: `Agent[None, ExtractionResult]` with `output_type=` for entity extraction |
| OwlBear conversation-router-research | `docs/conversation-router-research.md` | .85 | Intent taxonomy: "I have an idea" → `planner` agent via orchestrator routing |
| OwlBear pydantic-ai-multi-agent-research | `docs/pydantic-ai-multi-agent-research.md` | .80 | Structured output for delegation: `output_type=TaskResult` pattern |
| OwlBear agent_registry.py | `src/owlbear/core/agent_registry.py` | .90 | `_build_agent` always creates `Agent[OwlBearDeps, str]` — all agents return str today |

## 3. Analysis

### 3.1 Output Strategy — Structured Model vs. Markdown String

| Approach | How it works | Pros | Cons | Confidence |
|----------|-------------|------|------|------------|
| **A. `output_type=ProjectDefinition`** | Planner agent returns a validated Pydantic model | Type-safe, testable fields, downstream code can consume model directly | Requires changing `AgentRegistry._build_agent` to support non-str output; breaks `Agent[OwlBearDeps, str]` contract; LLM must populate ALL fields in one shot | .45 |
| **B. Internal structured extraction** | A separate lightweight `Agent[None, ProjectDefinition]` extracts structure from the planner's conversation; planner itself stays `output_type=str` | No registry changes; extraction agent is a utility like `ConsolidationResult`/`ExtractionResult`; planner can converse freely, then structured model is extracted at the end | Extra LLM call for extraction; slight indirection | **.80** |
| **C. Pure markdown output** | Planner produces a markdown doc; no Pydantic model | Simplest; no schema constraints on LLM output | Can't programmatically access fields; can't validate completeness; kanban task creation requires manual parsing | .35 |

**Recommendation (.80):** Approach B. The planner agent engages in a multi-turn conversation with the user (clarify → research → propose → iterate), producing markdown. At the end, a lightweight extraction agent (`Agent[None, ProjectDefinition]`) validates and structures the final output. This follows the proven `ConsolidationResult` and `ExtractionResult` patterns already in the codebase.

### 3.2 Workflow Phase Comparison (Prior Art)

| Phase | gpt-engineer | Devika | aider | OwlBear (proposed) |
|-------|-------------|--------|-------|-------------------|
| 1. Receive idea | `prompt` file | Chat UI message | `/ask` mode | User message routed via orchestrator |
| 2. Clarify | `clarify` preprompt: ask one question or "Nothing to clarify" | N/A (goes straight to planning) | Ask mode discussion | `ask_user` tool: targeted questions |
| 3. Research | N/A | Researcher agent: keyword extraction → web search → crawl | N/A | `query_knowledge` + `web_search` tools |
| 4. Plan | `generate` preprompt: lay out classes/functions | Planner agent: step-by-step plan with focus area | Architect proposes approach | Planner produces structured project definition |
| 5. Iterate | N/A | N/A | Bounce between `/ask` and `/code` | `ask_user` for user feedback loops |
| 6. Output | Code files | Code files | Code edits | Project definition doc + kanban tasks |

**Key insight:** gpt-engineer and Devika are code generators — their planning phase produces code scaffolds. OwlBear's planner produces *project specifications*, not code. This is upstream of code generation. The closest analogy is aider's ask/code split, where the ask phase produces a shared understanding before the code phase executes.

### 3.3 ProjectDefinition Model Design

Based on prior art patterns and the AC requirements:

| Field | Type | Required | Rationale |
|-------|------|----------|-----------|
| `name` | `str` | Yes | Project identifier |
| `description` | `str` | Yes | One-paragraph summary |
| `goals` | `list[str]` | Yes | What the project achieves (3–5 items) |
| `requirements` | `list[Requirement]` | Yes | Nested: `description`, `kind` (functional/non-functional) |
| `acceptance_criteria` | `list[str]` | Yes | Testable AC lines |
| `tech_stack` | `list[str]` | No | Languages, frameworks, libraries |
| `risks` | `list[str]` | No | Known risks and mitigations |
| `open_questions` | `list[str]` | No | Unresolved items needing user input |

The `Requirement` sub-model:

| Field | Type | Required |
|-------|------|----------|
| `description` | `str` | Yes |
| `kind` | `Literal["functional", "non-functional"]` | Yes |
| `priority` | `str` | No (default "important") |

**KISS consideration:** Keep the model flat where possible. `goals`, `acceptance_criteria`, `risks`, and `open_questions` are simple `list[str]`. Only `requirements` benefits from a nested model (to distinguish functional vs. non-functional).

### 3.4 Workflow Encoding — Skill File vs. System Prompt vs. Code

| Approach | Description | KISS | Testability | Confidence |
|----------|------------|------|-------------|------------|
| **A. System prompt only** | Full workflow instructions in `planner.md` body | High | Medium — must mock full LLM conversation | .50 |
| **B. Skill file** | Workflow steps in a skill file; planner loads it via `load_skill` | High | Medium — same testing challenge | .55 |
| **C. Skill file + extraction code** | Skill defines the conversational workflow; Python code handles `ProjectDefinition` extraction and markdown generation | Medium | **High** — extraction and generation are unit-testable | **.80** |

**Recommendation (.80):** Approach C. The planner's system prompt stays concise (it already has a good 6-step workflow). A new `project-definition` skill file documents the detailed project definition template and workflow steps. Python code in `src/owlbear/planning/` handles: (1) `ProjectDefinition` Pydantic model, (2) extraction agent, (3) markdown document generation, (4) kanban task creation helper.

### 3.5 Planner Agent Tool Expansion

The planner currently has `[filesystem, ask_user, delegation]`. For the project definition workflow, it also needs `knowledge` and `web_search` (both now available).

| Tool | Class | Purpose in workflow |
|------|-------|-------------------|
| `filesystem` | `FileToolset` | Write project definition doc to workspace |
| `ask_user` | `AskUserToolset` | Clarifying questions, propose options, iterate |
| `delegation` | `DelegationToolset` | Delegate research to researcher agent |
| `knowledge` | `KnowledgeToolset` | Search knowledge base for prior art, context |
| `web_search` | `WebSearchToolset` | Find libraries, frameworks, similar projects |

Both `knowledge` and `web_search` are in `KNOWN_TOOLSETS`? No — they need to be added to the test's `KNOWN_TOOLSETS` set and the planner's tool list updated.

### 3.6 Testing Strategy

| Test | Type | What it verifies |
|------|------|-----------------|
| `ProjectDefinition` model validation | Unit | Required fields, optional defaults, `Requirement` nesting |
| Markdown generation from model | Unit | `ProjectDefinition` → markdown string is well-formed |
| Extraction agent | Unit with `TestModel` | Given conversation text, produces valid `ProjectDefinition` |
| Planner integration | Integration with `FunctionModel` | Mock multi-turn: idea → clarify → research → define → output |
| Agent definition update | Parametrized | Planner now lists `knowledge` and `web_search` tools |

## 4. Recommendation (.80 confidence)

**Build the project definition workflow as three components:**

1. **`ProjectDefinition` Pydantic model + `Requirement` sub-model** in `src/owlbear/planning/models.py` (~40 LOC). Flat where possible, nested only for requirements.

2. **`ProjectDefinitionExtractor`** in `src/owlbear/planning/extractor.py` (~50 LOC). A lightweight `Agent[None, ProjectDefinition]` with `output_type=ProjectDefinition` that takes a conversation summary and extracts structured fields. Follows the proven `ConsolidationResult`/`ExtractionResult` pattern.

3. **`project-definition` skill file** in `.github/skills/project-definition/SKILL.md` (~60 lines). Documents the workflow template and project definition structure for the planner agent to load via `load_skill`.

4. **Update planner agent** — add `knowledge` and `web_search` to its tools list. Update `KNOWN_TOOLSETS` in tests.

5. **Markdown generator** in `src/owlbear/planning/markdown.py` (~40 LOC). Converts `ProjectDefinition` → markdown document.

**Risks:** (1) LLM may not fill all fields accurately during extraction — mitigate with Pydantic defaults and output validator retry. (2) Multi-turn conversation may be hard to mock in tests — mitigate with `FunctionModel` that returns predetermined responses. (3) `knowledge` and `web_search` tools conditional in bootstrap — planner must degrade gracefully if unavailable.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "ProjectDefinition Pydantic model and Requirement sub-model" --priority needed --tags "phase-11,planning,agent" --body "## Acceptance Criteria\n- [ ] Create src/owlbear/planning/__init__.py and src/owlbear/planning/models.py\n- [ ] ProjectDefinition model: name, description, goals, requirements, acceptance_criteria, tech_stack, risks, open_questions\n- [ ] Requirement sub-model: description, kind (functional/non-functional), priority\n- [ ] All optional fields have sensible defaults (empty lists)\n- [ ] Unit tests: valid model, missing required fields, Requirement kind validation\n\nSee docs/project-definition-workflow-research.md §3.3"

kanban\kanban-md.exe create "ProjectDefinitionExtractor — structured extraction from conversation" --priority needed --tags "phase-11,planning,agent" --body "## Acceptance Criteria\n- [ ] Create src/owlbear/planning/extractor.py\n- [ ] ProjectDefinitionExtractor class with Agent[None, ProjectDefinition] and output_type=ProjectDefinition\n- [ ] Follows ConsolidationResult/ExtractionResult pattern (consolidation.py, extractor.py)\n- [ ] System prompt instructs LLM to extract project definition fields from conversation text\n- [ ] Returns empty/default ProjectDefinition on failure (never raises)\n- [ ] Unit test with TestModel: given sample conversation, produces valid ProjectDefinition\n\nSee docs/project-definition-workflow-research.md §4" --depends-on 295

kanban\kanban-md.exe create "Project definition markdown generator" --priority needed --tags "phase-11,planning,agent" --body "## Acceptance Criteria\n- [ ] Create src/owlbear/planning/markdown.py\n- [ ] Function: project_definition_to_markdown(defn: ProjectDefinition) -> str\n- [ ] Output: well-formatted markdown with sections for goals, requirements, AC, tech stack, risks, open questions\n- [ ] Unit test: round-trip model -> markdown -> verify sections present\n\nSee docs/project-definition-workflow-research.md §4" --depends-on 295

kanban\kanban-md.exe create "project-definition skill file for planner agent" --priority needed --tags "phase-11,planning,agent,docs" --body "## Acceptance Criteria\n- [ ] Create .github/skills/project-definition/SKILL.md\n- [ ] YAML frontmatter: name, description\n- [ ] Workflow template: receive idea -> ask clarifying questions -> research feasibility -> propose definition -> iterate with user -> finalize\n- [ ] ProjectDefinition field reference table for the LLM\n- [ ] Example interaction showing how to use ask_user for option presentation\n- [ ] Skill is loadable by SkillRegistry (test: parse frontmatter)\n\nSee docs/project-definition-workflow-research.md §3.4"

kanban\kanban-md.exe create "Update planner agent tools: add knowledge and web_search" --priority needed --tags "phase-11,planning,agent" --body "## Acceptance Criteria\n- [ ] Update src/owlbear/agents/planner.md: add knowledge and web_search to tools list\n- [ ] Update tests/test_agent_definitions.py: add knowledge and web_search to KNOWN_TOOLSETS\n- [ ] Update EXPECTED_AGENTS planner entry with new tools\n- [ ] Add project-definition to planner skills list\n- [ ] All existing tests still pass (uv run pytest tests/test_agent_definitions.py)\n\nSee docs/project-definition-workflow-research.md §3.5" --depends-on 295

kanban\kanban-md.exe create "Integration test: mock LLM project definition flow" --priority important --tags "phase-11,planning,agent,test" --body "## Acceptance Criteria\n- [ ] Create tests/test_project_definition_flow.py\n- [ ] Use FunctionModel to simulate multi-turn: user idea -> planner asks clarification -> user answers -> planner proposes definition -> extraction produces ProjectDefinition\n- [ ] Verify ProjectDefinition has populated name, description, goals, requirements\n- [ ] Verify markdown output is generated\n- [ ] Test covers the ask_user -> knowledge query -> web_search -> definition path\n\nSee docs/project-definition-workflow-research.md §3.6" --depends-on 296,297,298
```

Note: Task IDs above (295–300) are placeholders — actual IDs will be assigned by `kanban-md create`. The `--depends-on` references should be updated to match actual IDs after creation.
