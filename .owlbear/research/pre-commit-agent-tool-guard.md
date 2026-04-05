# Pre-commit Guard Against Agent Tool Name Regression

> **Owning task:** #132 — Add pre-commit guard against agent tool name regression
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

VS Code silently re-serializes `.agent.md` files when detecting new tool capabilities,
reverting `todos` back to `todo` and re-adding removed tools like `resolveMemoryFileUri`.
This "auto-staging trap" caused a regression in commit `6d76867` that reverted correct
fixes from `ec84b55` (documented in `agent-common.instructions.md` and confirmed by the
auditor in task #36). The existing test suite (`test_agent_port_v2.py`) catches this but
only when explicitly run. A pre-commit hook would block bad commits automatically.

**Question:** What is the best approach for a pre-commit hook that blocks commits
containing agent tool name regressions?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| pre-commit docs — pygrep language | https://pre-commit.com/#pygrep | .90 — built-in regex hook, zero-config |
| pre-commit docs — local hooks | https://pre-commit.com/#repository-local-hooks | .95 — pattern for custom Python scripts |
| OwlBear `.pre-commit-config.yaml` | local: `.pre-commit-config.yaml` | 1.0 — existing `repo: local` with `validate-skills` |
| OwlBear `scripts/validate_skills.py` | local: `scripts/validate_skills.py` | .95 — established pattern for custom hooks |
| OwlBear `test_agent_port_v2.py` | local: `tests/test_agent_port_v2.py` | .90 — existing checks to replicate at commit time |
| OwlBear `port-agents-v2-status.md` | local: `docs/research/port-agents-v2-status.md` | .85 — documents the regression root cause |

## 3. Analysis

### 3a. Why pygrep alone is insufficient

The word `todo` appears legitimately in agent file prose (e.g., "move to todo status",
"advance tasks to todo"). A `\btodo\b` pygrep check on the full file produces false
positives. The check must target only the YAML frontmatter `tools:` line.

For `resolveMemoryFileUri`, pygrep works perfectly — the string should never appear
anywhere in any agent file. But using two different hook strategies adds complexity.

### 3b. Option comparison

| Criterion | pygrep (2 hooks) | Python script | Hybrid |
|-----------|------------------|---------------|--------|
| KISS | High | Medium | Low |
| Precision (no false positives) | Low — `todo` in prose | High — parses frontmatter | Medium |
| Speed | <0.1s | <0.5s | <0.2s |
| Follows project precedent | No | Yes (`validate_skills.py`) | Partial |
| Extensible for future checks | Low | High | Medium |
| Under 1s (AC) | Yes | Yes | Yes |

### 3c. Script design sketch (~30 LOC)

1. Read each `agents/*.agent.md` passed as arguments (or auto-discover)
2. Extract YAML frontmatter (between `---` delimiters)
3. Check frontmatter `tools:` value for `\btodo\b` (word boundary — matches `todo` not `todos`)
4. Check full file content for `resolveMemoryFileUri`
5. Exit 0 if clean, exit 1 with descriptive errors if not

### 3d. Hook configuration

Add to existing `repo: local` section in `.pre-commit-config.yaml`:

```yaml
- id: validate-agents
  name: Validate Agent Tool Names
  language: system
  entry: python scripts/validate_agents.py
  files: ^agents/.*\.agent\.md$
  pass_filenames: true
```

Uses `language: system` (matches `validate-skills` pattern). `files` filter ensures
the hook only runs when agent files are staged — instant skip otherwise.

## 4. Recommendation (.85 confidence)

**Option: Python script** (`scripts/validate_agents.py`) added as a `repo: local` hook.

- Follows the established `validate_skills.py` pattern (project consistency)
- Parses frontmatter precisely, avoiding false positives from prose content
- Runs in <0.5s on 11 files (well under 1s AC requirement)
- Extensible for future agent-file checks (e.g., other renamed tools)
- Risk: minimal — simple regex on small files, no external dependencies

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement validate_agents.py pre-commit hook" --priority nice-to-have --status ideation --tags "phase-1,scope:agents,tooling,type:build" --body "## Objective\nCreate scripts/validate_agents.py and add pre-commit hook to block agent tool name regressions.\n\n## Acceptance Criteria\n- [ ] scripts/validate_agents.py reads agents/*.agent.md frontmatter, fails if tools: contains bare todo (not todos)\n- [ ] Script also fails if resolveMemoryFileUri appears anywhere in any agent file\n- [ ] repo: local hook added to .pre-commit-config.yaml with id: validate-agents, files: ^agents/.*\\.agent\\.md$\n- [ ] pre-commit run validate-agents --all-files exits 0 on current HEAD (after tool name fixes)\n- [ ] Hook runs in less than 1s\n- [ ] Brief note added to README about the hook and the VS Code auto-staging trap\n\n## Architecture Notes\n- Follow validate_skills.py pattern: language: system, entry: python scripts/validate_agents.py\n- Parse YAML frontmatter between --- delimiters, check tools: line for \\btodo\\b regex\n- Check full file content for resolveMemoryFileUri\n- Script ~30 LOC, no external dependencies\n- See docs/research/pre-commit-agent-tool-guard.md"
```
