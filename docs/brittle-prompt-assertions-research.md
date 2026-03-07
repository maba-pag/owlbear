# Replace Brittle Prompt Substring Assertions

> **Owning task:** #554 — Replace brittle prompt substring assertions with semantic checks
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Tests assert exact substrings in agent system prompts. Any prompt rewording breaks them.
Task #554 asks: should we replace these with semantic/structural checks? What patterns exist?

The audit in `docs/test-quality-audit.md` (finding M1) identified this as a medium-severity issue.
Two tests in `TestOrchestratorKanbanPrompt` were already failing due to prompt refactoring.

## 2. Sources Studied

| Source | URL | Relevance | What we learned |
|--------|-----|-----------|-----------------|
| PydanticAI test_agent.py | github.com/pydantic/pydantic-ai/blob/main/tests/test_agent.py | .90 | Tests agent behavior/output, never asserts on prompt content. Uses `snapshot()` for structural matching. |
| OwlBear test_agent_definitions.py | Local: `tests/test_agent_definitions.py` | .85 | Already uses non-brittle pattern: checks line count ranges, tool lists, skills — never prompt substrings. |
| CheckList (Ribeiro et al. 2020) | arxiv.org/abs/2005.04118 | .70 | Invariance/directional testing for ML. Principle: test behavioral properties, not exact outputs. |
| Eugene Yan — Testing ML Systems | eugeneyan.com/writing/testing-ml | .65 | Distinguishes implementation tests vs learned-behavior tests. Assert on properties, not literals. |

## 3. Analysis

### 3.1 Inventory of Prompt Assertions (8 test files, 30+ assertions)

| File | Assertions | Brittleness | Risk | Action |
|------|-----------|-------------|------|--------|
| test_kanban_pipeline.py | 10 (exact substrings in orchestrator.md prompt) | **HIGH** | 2 already failing | **Must fix** |
| test_source_evaluator.py | 3 (exact project description in dynamic prompt) | **MEDIUM** | Breaks if project description changes | Fix |
| test_knowledge_extractor.py | 2 (keyword checks on EXTRACTION_PROMPT) | LOW | Only checks "json" | Optional |
| test_project_definition_extractor.py | 4 (keyword checks on EXTRACTION_PROMPT) | LOW | Checks "json", "name", "goals" | Optional |
| test_agent_def.py | 5 (exact equality on controlled test input) | NONE | Tests parser, not real prompts | Skip |
| test_agent_definitions.py | 1 (line count range check) | NONE | Already structural | Skip |
| test_approval_gate.py | 3 (tool name in dynamic output) | NONE | Tests runtime behavior | Skip |
| test_slack_interactive.py | 2 (tool name in dynamic output) | NONE | Tests runtime behavior | Skip |

### 3.2 Brittleness Categories

| Category | Pattern | Example | Fix |
|----------|---------|---------|-----|
| Exact section heading | `"Kanban Pipeline" in prompt` | Broke when prompt refactored | Regex: `re.search(r"(?i)kanban", prompt)` |
| Tool name in prompt body | `"kanban_pick" in prompt` | Fragile to tool renames | Check `defn.tools` metadata instead |
| Common word in prompt | `"review" in prompt` | False positives, too vague | Check `defn.tools` or use regex with context |
| Exact project description | `"always-on AI development system" in prompt` | Breaks on any description edit | Check `SAMPLE_PROJECT_CONTEXT.name in prompt` |
| Keyword in static prompt | `"json" in EXTRACTION_PROMPT.lower()` | Low risk, acceptable | No change needed |

### 3.3 Replacement Strategy Comparison

| Strategy | Resilience | Effort | KISS | When to use |
|----------|-----------|--------|------|-------------|
| Check `defn.tools` list | High | Low | High | When testing "agent has capability X" |
| Regex with semantic groups | Medium | Low | Medium | When testing "prompt covers topic X" |
| Line count / section count | High | Low | High | When testing "prompt is substantive" |
| Test behavior (run agent) | Highest | High | Low | When testing "agent does X correctly" |
| Keyword `in` checks | Low | Lowest | High | Only for truly stable keywords |

## 4. Recommendation (.85 confidence)

**Replace content assertions with metadata + structural checks.** Rationale:

1. **Test the contract, not the prose.** If the orchestrator needs kanban tools,
   verify `"kanban" in defn.tools` — not that the prompt mentions "kanban_pick".
2. **Use regex only when content matters.** Status names (`todo`, `in-progress`) are
   domain constants — a regex like `r"(?i)todo.*in-progress"` is acceptable.
3. **Already proven in codebase.** `test_agent_definitions.py` already uses the right
   pattern (tool list checks, line count ranges). Extend this pattern.

Risk: Some tests intentionally verify prompt content guides agent behavior. For these,
regex with alternation (`r"blocked|unblocked|dependency"`) preserves intent while
tolerating rewording.

## 5. Implementation Plan Per File

### test_kanban_pipeline.py (10 assertions → 7 structural checks)

| Current assertion | Replacement |
|-------------------|-------------|
| `"Kanban Pipeline" in defn.system_prompt` | `re.search(r"(?i)##.*kanban", defn.system_prompt)` |
| `"kanban_pick" in defn.system_prompt` | `"kanban" in defn.tools` |
| `"todo" in prompt` | `re.search(r"(?i)todo.*in-progress", prompt)` |
| `"in-progress" in prompt` | (merged with above) |
| `"review" in prompt` | `re.search(r"(?i)review", prompt)` |
| `"unblocked" in prompt or "kanban_list" in prompt` | `"kanban" in defn.tools` |
| `"kanban_edit" in defn.system_prompt` | `"kanban" in defn.tools` |
| `"block" in defn.system_prompt.lower()` | `re.search(r"(?i)block", prompt)` |
| `"kanban_show" in prompt` | `"kanban" in defn.tools` |
| `"kanban_move" in prompt` | `"kanban" in defn.tools` |

### test_source_evaluator.py (3 assertions → 2)

| Current | Replacement |
|---------|-------------|
| `"always-on AI development system" in prompt_text` | `SAMPLE_PROJECT_CONTEXT.name in prompt_text` |
| `"Autonomous coding" in prompt_text` | `any(g in prompt_text for g in SAMPLE_PROJECT_CONTEXT.goals[:1])` |
| `"OwlBear" in prompt_text` | Keep as-is (project name is stable) |

### test_knowledge_extractor.py, test_project_definition_extractor.py

No changes needed — keyword checks on static prompts are low-risk and appropriate.

## 6. Follow-up Tasks

```
kanban\kanban-md.exe create "Replace brittle prompt assertions in test_kanban_pipeline.py" --priority important --status todo --tags "test,audit" --description "Replace 10 exact-substring assertions in TestOrchestratorKanbanPrompt with metadata checks (defn.tools) and regex patterns. See docs/brittle-prompt-assertions-research.md section 5. This also fixes the 2 currently failing tests."

kanban\kanban-md.exe create "Replace brittle project-description assertions in test_source_evaluator.py" --priority nice-to-have --status todo --tags "test,audit" --description "Replace 2 exact project-description assertions with checks against SAMPLE_PROJECT_CONTEXT fields. See docs/brittle-prompt-assertions-research.md section 5."
```
