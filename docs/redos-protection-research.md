# ReDoS Protection for Filesystem Search Content Regex

> **Owning task:** #496 — Add ReDoS protection to filesystem search content regex
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

SEC-09 from the security audit identified that `_search_files` in `src/owlbear/tools/filesystem.py` compiles LLM-provided `content_regex` via `re.compile()` with no complexity guards. Patterns like `(a+)+b` cause catastrophic backtracking (exponential time) when matched against certain inputs. The LLM generates these patterns, and prompt injection could produce an evil regex intentionally.

**Question:** What is the simplest, KISS-aligned approach to protect against ReDoS in this tool?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OWASP ReDoS | <https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS> | .95 — canonical attack description, evil regex patterns |
| 2 | Google RE2 README | <https://github.com/google/re2> | .85 — linear-time regex engine, safety-first design |
| 3 | `google-re2` PyPI | <https://pypi.org/project/google-re2/> | .80 — Python bindings for RE2, drop-in replacement |
| 4 | `regex` PyPI | <https://pypi.org/project/regex/> | .90 — drop-in `re` replacement with native `timeout` parameter |
| 5 | OwlBear security audit | docs/security-audit.md SEC-09 | 1.0 — original finding with recommendations |

## 3. Analysis

### Evil Regex Patterns (OWASP)

Evil regex = grouping with repetition + inner repetition or overlapping alternation:

- `(a+)+$` — nested quantifiers
- `([a-zA-Z]+)*$` — group with quantifier containing quantifier
- `(a|aa)+$` — alternation with overlap

These cause exponential backtracking in Python's `re` module because it uses NFA with backtracking.

### Option Comparison

| Criterion | A: `regex` + timeout (.85) | B: `google-re2` (.55) | C: Heuristic reject + try/except (.70) |
|-----------|---------------------------|----------------------|----------------------------------------|
| ReDoS safety | **Full** — timeout kills stuck match at C level | **Full** — linear time by construction | **Partial** — catches common patterns, misses edge cases |
| API compatibility | Drop-in for `re` | Mostly compatible, no backrefs/lookaround | Uses `re` directly |
| New dependency | `regex` (pure Python + C ext, ~1 MB) | `google-re2` (requires C++ RE2 lib, ~5 MB) | None |
| Windows support | **Yes** — standard wheel | Fragile — needs C++ build toolchain or pre-built wheel | **Yes** |
| Implementation LOC | ~5 lines changed | ~5 lines changed | ~15 lines (heuristic regex + validation function) |
| KISS alignment | High — one import swap + timeout param | Medium — build dependency complexity | Medium — heuristic is ad-hoc, may need tuning |
| False positives | None — valid patterns still work, just time-limited | Some — rejects valid PCRE features (backrefs) | Some — heuristic may reject legitimate nested groups |
| Failure mode | `TimeoutError` — clean, catchable | `re2.error` — clean, catchable | Silent miss — evil pattern not detected |

### Defense-in-Depth Recommendation

The strongest approach combines **two layers**:

1. **`try/except` on `re.compile()`** (or `regex.compile()`) — catches syntactically invalid patterns (already a gap today).
2. **`timeout` on `search()`** — catches semantically valid but computationally evil patterns.

Layer 1 is free regardless of approach. Layer 2 requires either the `regex` library or `google-re2`.

### Why Not Threading Timeout with `re`?

Using `concurrent.futures.ThreadPoolExecutor` with `re.search()` and a timeout does **not** work: the stuck thread holds the GIL during C-level regex matching and cannot be killed. The thread keeps consuming CPU even after the timeout. Only the `regex` library's built-in timeout (checked inside the C matching loop) or RE2's linear-time guarantee actually stop the computation.

## 4. Recommendation (.85 confidence)

**Use the `regex` library with `timeout` parameter.**

- Swap `import re` → `import regex` in `filesystem.py` only (not project-wide).
- Add `timeout=5` (seconds) to the `compiled.search()` call.
- Wrap `regex.compile()` in `try/except regex.error` for malformed patterns.
- Wrap `compiled.search()` in `try/except TimeoutError` for evil patterns.
- Return a clear error message in both cases.

**Why not `google-re2`?** Windows build complexity violates KISS. The `regex` library has standard wheels for all platforms and is a true drop-in replacement.

**Why not heuristic-only?** Heuristics miss edge cases (alternation overlap, complex nesting). A timeout is the universal safety net — it catches *any* pattern that takes too long, regardless of structure.

**Risk:** The `regex` dependency adds ~1 MB. Acceptable for a security fix.

**Scoping note:** The `regex` import should be limited to `filesystem.py`. No project-wide migration. The `re` module is fine everywhere else where patterns are developer-controlled, not LLM-controlled.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement ReDoS protection in FileToolset._search_files" --priority needed --status backlog --tags "security,tools,phase-4" --body "Swap re→regex in filesystem.py _search_files only. Add timeout=5 to compiled.search(). Wrap compile in try/except regex.error. Wrap search in try/except TimeoutError. Return error messages for both cases. Add regex to pyproject.toml dependencies. AC: (1) malformed regex returns error message, not exception. (2) evil regex like (a+)+$ on 'aaa..a!' input returns timeout error within 10s. (3) valid regex works unchanged. (4) existing tests pass. See docs/redos-protection-research.md §4."
```

```powershell
kanban\kanban-md.exe create "Add ReDoS protection tests for FileToolset" --priority needed --status backlog --tags "security,tools,test,phase-4" --body "Test cases: (1) malformed regex (unclosed group) returns error string. (2) evil regex (a+)+$ with pathological input times out gracefully. (3) normal regex works as before. (4) None/empty content_regex works as before. See docs/redos-protection-research.md §4."
```

