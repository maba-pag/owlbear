# BearClaw CLI: Decision Request Commands

> **Owning task:** #767 — BearClaw CLI: decision request commands
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

The decision-request process (`docs/decisions/`) is fully file-based. Agents create
YAML-frontmatter markdown files in `pending/`, users resolve them by hand-editing and
moving to `resolved/`. The question: what is the best CLI implementation approach for
`bearclaw decisions {list,show,resolve}` that fits OwlBear's stack and patterns?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | python-frontmatter 1.1.0 | <https://github.com/eyeseast/python-frontmatter> | .70 — mature YAML+markdown parser (409★, typed, MIT) |
| 2 | Typer prompt docs | <https://typer.tiangolo.com/tutorial/prompt/> | .85 — `typer.prompt()`, `typer.confirm()`, `Prompt.ask()` |
| 3 | Rich prompt module | <https://rich.readthedocs.io/en/stable/prompt.html> | .80 — `Prompt.ask(choices=...)`, `Confirm.ask()` |
| 4 | Existing BearClaw commands | `src/bearclaw/commands/project.py`, `knowledge_source.py` | .95 — established patterns (sub-Typer, Rich Table, deferred imports) |
| 5 | Existing frontmatter parsing | `src/owlbear/core/agent_def.py`, `src/owlbear/skills/registry.py` | .90 — manual `yaml.safe_load` on `---` delimiters (no external dep) |

## 3. Analysis

### A: Frontmatter parsing — add `python-frontmatter` vs. hand-roll

| Criterion | python-frontmatter (.65) | Manual yaml.safe_load (.85) |
|-----------|--------------------------|----------------------------|
| New dep | +1 package (PyYAML already present) | 0 new deps |
| Consistency | Introduces new pattern | Matches agent_def.py + registry.py |
| KISS/YAGNI | Overkill for 6 fields | ~15 LOC helper, covers exact need |
| Write-back | `frontmatter.dump()` round-trips | Need 2-step: update YAML block + reassemble |
| Risk | None (mature lib) | Minor: must preserve content after frontmatter |

**Verdict (.85):** Manual parsing. The codebase already has two `yaml.safe_load`-based
frontmatter parsers. A thin `_parse_decision_file()` function (~20 LOC) keeps deps at zero
and matches existing patterns. Write-back is slightly more work but only needed for
`resolve` (one place, one operation — change `status` field).

### B: Resolve UX — interactive prompt vs. option flags

| Criterion | Interactive (Rich Prompt) (.80) | Flag-based (.70) |
|-----------|--------------------------------|-------------------|
| UX | Guided flow, hard to miss fields | Fast for scripts, terse |
| Testable | Needs `input` patching or CliRunner `input=` | Straightforward |
| AC match | AC says "interactive resolution flow" | Does not match AC |
| Precedent | Typer/Rich prompt well-documented | All existing commands use flags |

**Verdict (.80):** Interactive via `Rich.Prompt.ask(choices=...)` for option selection,
`typer.prompt()` for notes, `typer.confirm()` for final confirmation. This matches
the AC ("interactive resolution flow") and degrades to a simple 3-step prompt
(pick option → add notes → confirm). The flag-based approach can be added later as
`--decision` / `--notes` args with defaults.

### C: File location — hardcode `docs/decisions/` vs. configurable

| Criterion | Hardcoded (.85) | Configurable (.55) |
|-----------|-----------------|---------------------|
| KISS | Single source: `docs/decisions/` | Over-engineered |
| YAGNI | Only one decision dir exists | No use case for multiple |
| Precedent | Matches instruction files' hardcoded paths | None |

**Verdict (.85):** Hardcode `docs/decisions/` relative to workspace root (resolved via
`Path.cwd()` or a shared `_workspace_root()` helper). Make it a module constant for
easy change later without configurability overhead.

## 4. Recommendation (.85 confidence)

Create `src/bearclaw/commands/decisions.py` following the existing command pattern:

1. **`bearclaw decisions list`** — scan `pending/` for `*.md`, parse frontmatter,
   Rich Table output (columns: Task ID, Title, Age, Urgency, Type).
2. **`bearclaw decisions show {task_id}`** — find file by `task_id` in frontmatter,
   print full markdown content via `rich.markdown.Markdown`.
3. **`bearclaw decisions resolve {task_id}`** — parse file, extract `## Options`
   section headings, present choices via `Prompt.ask(choices=...)`, collect notes
   via `typer.prompt()`, update frontmatter `status: resolved`, write `## Resolution`
   section, move file to `resolved/`.

**Key implementation details:**

- Frontmatter parser: reuse `yaml.safe_load` pattern from `agent_def.py`, no new deps
- Locate by task ID: glob `pending/*.md`, match `task_id` frontmatter field
- Age calculation: `datetime.now() - created` from frontmatter, display as "X days"
- File move: `shutil.move()` from `pending/` to `resolved/`
- Registration: `app.add_typer(decisions_app)` in `cli.py` as named sub-group

**Risks:**

- Option extraction from markdown body requires heading parsing (~10 LOC regex)
- If `## Options` section doesn't follow template, fall back to free-text decision input

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement bearclaw decisions list/show/resolve commands" --priority nice-to-have --status ideation --tags cli,process --body "## Context\nCLI commands for the file-based decision-request workflow.\nSee docs/research/bearclaw-decision-commands.md for research.\n\n## Acceptance Criteria\n- [ ] New file: src/bearclaw/commands/decisions.py\n- [ ] 'bearclaw decisions list' scans pending/ and outputs Rich Table (Task ID, Title, Age, Urgency, Type)\n- [ ] 'bearclaw decisions show {task_id}' displays full file content via rich.markdown.Markdown\n- [ ] 'bearclaw decisions resolve {task_id}' interactive flow: extract options from ## Options headings, Prompt.ask(choices), prompt for notes, write Resolution section, update frontmatter status, move to resolved/\n- [ ] Registered in cli.py via app.add_typer(decisions_app)\n- [ ] No new dependencies (use yaml.safe_load pattern from agent_def.py)\n- [ ] Graceful error messages for: no pending decisions, task_id not found, malformed frontmatter"
```

```
kanban\kanban-md.exe create "Tests for bearclaw decisions commands" --priority nice-to-have --status ideation --tags cli,process,test --body "## Context\nTDD tests for the decisions CLI subcommands.\nSee docs/research/bearclaw-decision-commands.md for research.\n\n## Acceptance Criteria\n- [ ] tests/test_cli_decisions.py using CliRunner + tmp_path fixtures\n- [ ] Test list with 0, 1, 2+ pending decisions\n- [ ] Test show by task_id (found + not found)\n- [ ] Test resolve interactive flow with CliRunner input= mocking\n- [ ] Test resolve moves file from pending/ to resolved/\n- [ ] Test malformed frontmatter graceful error\n- [ ] Coverage >= 90% for decisions.py"
```
