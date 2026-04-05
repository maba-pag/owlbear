# Standardize Docstring Style to Google-Style

> **Owning task:** #543 — Standardize docstring style to Google-style across codebase
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

The codebase mixes Google-style (`Args:`, `Returns:`) and numpy-style (`Parameters\n----------`) docstrings. All `D` (pydocstyle) rules are currently disabled in ruff. We need to decide: which convention, which rules to enable, and how to migrate.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Ruff pydocstyle convention docs | <https://docs.astral.sh/ruff/settings/#lintpydocstyleconvention> | 1.0 |
| Ruff FAQ: Google/NumPy docstrings | <https://docs.astral.sh/ruff/faq/#does-ruff-support-numpy-or-google-style-docstrings> | 1.0 |
| OwlBear documentation-audit.md | Local: `docs/documentation-audit.md` (F-03) | 0.9 |
| Google Python Style Guide (docstrings) | <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings> | 0.8 |

## 3. Analysis

### 3.1 Current State (Codebase Audit)

| Metric | Count |
|--------|-------|
| Total `.py` files in `src/` | 111 |
| Google-style `Args:` sections | 113 |
| Google-style `Returns:` sections | 55 |
| Google-style `Raises:` sections | 40 |
| Numpy-style `Parameters` sections | 46 |
| Numpy-style underline separators | 50 |
| Files with numpy-style docstrings | 20 |

**Google-style is already the majority** (~70% of section headers). Numpy-style is concentrated in 20 files, mostly `memory/knowledge/`, `channels/slack*`, `projects/`, and `daemon.py`.

### 3.2 Ruff D-Rule Violation Counts

| Scenario | Violations | Auto-fixable |
|----------|-----------|-------------|
| All D rules, no convention set | 283 | 200 |
| All D rules, `convention = "google"` | 103 | 23 |

With `convention = "google"`, ruff auto-ignores incompatible rules (D203, D204, D213, D215, D400, D401, D404, D406, D407, D408, D409, D410, D411, D413, D414). Remaining violations:

| Rule | Count | Fixable | Description |
|------|-------|---------|-------------|
| D416 | 23 | Yes | Section name missing colon (numpy-style `Returns` instead of `Returns:`) |
| D107 | 65 | No | Undocumented `__init__` |
| D102 | 7 | No | Undocumented public method |
| D105 | 4 | No | Undocumented magic method |
| D301 | 3 | No | Escape sequence in docstring (use raw string) |
| D104 | 1 | No | Undocumented public package |

### 3.3 Incremental Enablement Options

| Option | Rules enabled | Violations | Effort | KISS |
|--------|--------------|-----------|--------|------|
| A: Full D + convention=google | All D (minus google-excluded) | 103 | High (65 `__init__` docstrings) | Low |
| B: Selective D (no D1xx) | D2xx, D3xx, D4xx | 26 | Low (23 auto-fixable D416 + 3 D301) | **High** |
| C: D416 only | D416 | 23 | Minimal (auto-fixable) | Medium |

## 4. Recommendation (.90 confidence)

**Option B: Enable D rules with `convention = "google"`, ignore D1xx (missing docstring rules).**

Config change in `pyproject.toml`:

```toml
# Replace:
#   "D",      # pydocstyle -- we use Google-style docstrings, not enforced by ruff
# With:
#   "D100",   # undocumented-public-module — not requiring module docstrings yet
#   "D101",   # undocumented-public-class — not requiring class docstrings yet
#   "D102",   # undocumented-public-method — not requiring method docstrings yet
#   "D103",   # undocumented-public-function — not requiring function docstrings yet
#   "D104",   # undocumented-public-package — not requiring package docstrings yet
#   "D105",   # undocumented-public-magic-method — not requiring magic docstrings yet
#   "D106",   # undocumented-public-nested-class — not requiring nested class docstrings yet
#   "D107",   # undocumented-public-init — not requiring init docstrings yet

# Add:
# [tool.ruff.lint.pydocstyle]
# convention = "google"
```

This means: remove `"D"` from `ignore`, add `"D1"` to `ignore` instead, and add the convention setting. The D2xx/D3xx/D4xx rules enforce *style consistency* without mandating docstring *presence*. Only 26 violations to fix, 23 of which are auto-fixable.

**Rationale:**

- KISS: enforces the convention we already use, minimal effort
- YAGNI: D1xx (missing docstring) rules can be enabled later as coverage improves
- D416 auto-fix converts numpy `Returns` to `Returns:` — handles ~half the migration automatically
- Remaining 20 files need manual numpy-to-google section header conversion

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Enable ruff D rules with Google convention (ignore D1xx)" --priority needed --tags config,tooling,code-quality --body "Change pyproject.toml: remove 'D' from ignore, add 'D1' to ignore. Add [tool.ruff.lint.pydocstyle] convention = 'google'. Run ruff --fix for D416. Fix remaining D301 (3 files). See docs/research/docstring-style.md."

kanban\kanban-md.exe create "Convert numpy-style docstrings to Google-style in 20 files" --priority nice-to-have --tags docs,code-quality --body "Files: channels/slack.py, channels/slack_templates.py, core/progress.py, daemon.py, memory/knowledge/{bookmark,bookmark_pipeline,chunker,evaluator,graph,graph_builder,ingest,inter_doc_graph_builder,qdrant,refresh,retrieval,schema,source_store}.py, projects/{store,workspace}.py, tools/browser/integration.py. Change 'Parameters\n----------' to 'Args:', 'Returns\n-------' to 'Returns:'. See docs/research/docstring-style.md." --depends-on 543

kanban\kanban-md.exe create "Enable D1xx rules incrementally (docstring presence)" --priority someday --tags docs,code-quality --body "Once docstring coverage improves, enable D1xx rules. Start with D100 (module docstring) or D107 (init docstring). Currently 65 D107 violations. See docs/research/docstring-style.md."
```

## 6. Research Checklist

- [x] Theoretical validity — Google-style is the de facto standard for Python projects using ruff/Black; aligns with existing majority
- [x] Prior art — Ruff docs (convention setting), Google Style Guide (section format)
- [x] Technical feasibility — `convention = "google"` is a first-class ruff feature; auto-fix handles D416
- [x] Architecture fit — config-only change in pyproject.toml; no code architecture impact
- [x] Implementation approach — incremental: convention+style rules first (D2-D4), presence rules later (D1)
