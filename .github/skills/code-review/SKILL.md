---
name: code-review
description: "Evidence-based code review workflow: run tests → lint → read code → verify AC → verdict. Use when verifying implementation quality."
---

# Code Review Workflow

Step-by-step process for reviewing a completed implementation task.

## Step 1 — Read the task

1. `kanban\kanban-md.exe show {id}` — read full acceptance criteria
2. Note every AC line — each will be verified individually

## Step 2 — Run tests independently

Do NOT rely on what the builder reported. Run yourself:

```powershell
uv run pytest tests/ -m "not api" --tb=short -q
```

For specific modules:

```powershell
uv run pytest tests/test_{module}.py -v --tb=short
```

Record: passed/failed counts, any failures, any warnings.

## Step 3 — Run lint

```powershell
uv run ruff check src/ tests/
```

Record: errors/warnings or "All checks passed!"

## Step 4 — Run coverage (if applicable)

```powershell
uv run pytest --cov=owlbear --cov-report=term-missing -q
```

Verify touched modules have ≥ 90% coverage.

## Step 5 — Read changed files

Use `read_file` to examine the actual code:

- Type hints present on all signatures?
- Docstrings on public classes and functions?
- `from __future__ import annotations` at top?
- Follows existing patterns in the project?
- No unused imports, dead code, missing error handling?

For agent/prompt files: valid YAML frontmatter, required sections present.

## Step 6 — Verify AC compliance

Build an evidence table — every AC line needs specific proof:

| AC Line | Evidence | Status |
|---------|----------|--------|
| ... | file path + line, test name, command output | PASS/FAIL |

"It looks fine" is NOT evidence. Cite specific line numbers, test names, or output.

## Step 7 — Produce verdict

**PASS** (all criteria met):

- `kanban\kanban-md.exe move {id} docs`
- Your job ends here — writer owns the docs gate

**FAIL** (any criterion unmet):

- List every failing criterion with evidence
- `kanban\kanban-md.exe move {id} todo --block "reason"`

## Review output format

```
## Review: #{id} — {title}

### Test Results
- pytest: {N} passed, {M} failed
- Evidence: {key output}

### Lint Results
- ruff: {clean / N errors}

### Coverage
- {module}: {X}%

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|

### Verdict: PASS / FAIL

### Action Taken
- kanban command executed
```
