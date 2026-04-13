# GREEN Implementation — IDPI ContentInjectionGuard at Graph Entry

> **Owning task:** #834 — Impl — IDPI ContentInjectionGuard at graph entry
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #834 is the GREEN-phase TDD task implementing `ContentInjectionGuard` and wiring it into `IngestPipeline.ingest()`. The design was established in research #724 (browser path), #768 (graph entry rescope), and #833 (RED tests). This research validates the implementation approach against current codebase state and confirms all 7 ACs are implementable.

**Core question:** What is the correct implementation approach, are there codebase gaps, and does the design hold against current state?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| PinchTab idpishield `patterns/builtin.go` | github.com/pinchtab/idpishield (Apache-2.0) | .90 — 100+ regex patterns across 12 categories, CheckResult-like RiskResult struct |
| ProtectAI llm-guard `BanSubstrings` | github.com/protectai/llm-guard (MIT) | .75 — Python substring-matching scanner, configurable deny lists |
| OWASP LLM01:2025 | genai.owasp.org/llmrisk/llm01-prompt-injection/ | .85 — Strategy #3: string-checking, Strategy #6: segregate content |
| #724 IDPI research | `.owlbear/research/idpi-content-scanning.md` | .90 — CheckResult design, ~40 pattern list, strict/warn modes |
| #768 research | `.owlbear/research/768-content-safety-idpi-wrapping.md` | .90 — Option B: separate `content_guard.py` module |
| #833 RED research | `.owlbear/research/833-idpi-content-guard-red-tests.md` | .95 — test structure, IngestResult "blocked" literal decision |
| `ingest.py` (current) | `serve/knowledge/src/owlbear_knowledge/ingest.py` | .95 — integration point at L200-210 |
| `content_safety.py` (current) | `serve/knowledge/src/owlbear_knowledge/content_safety.py` | .90 — `should_wrap()` predicate, wrapping utility |

## 3. Analysis

### 3a. AC-by-AC Implementation Assessment

| AC | Requirement | Approach | Risk |
|----|-------------|----------|------|
| AC1 | `ContentInjectionGuard` in `content_guard.py` | New module, single class | None |
| AC2 | `CheckResult` dataclass with 4 fields | `@dataclass(frozen=True)` with `threat`, `blocked`, `reason`, `pattern` | None |
| AC3 | ~40 builtin patterns, case-insensitive substring | `_BUILTIN_PATTERNS: tuple[str, ...]`, match via `phrase in text_lower` | Low — pattern selection |
| AC4 | Configurable `custom_patterns` + `strict_mode` | `__init__` params, merged into scan loop | None |
| AC5 | Wire into `ingest()` before entity extraction | Scan chunk text after chunking, before extract comprehension; reuse `should_wrap()` for trust check | Low — integration ordering |
| AC6 | Strict: return blocked; Warn: log + proceed | Strict → early return `IngestResult(status="blocked")`; Warn → `logger.warning()` + continue | None |
| AC7 | All #833 tests pass | Implement to satisfy RED test contracts | None |

### 3b. Pattern Strategy: Substring vs Regex

| Criterion | Substring matching (.85) | Regex matching (.70) |
|-----------|-------------------------|---------------------|
| AC compliance | Yes — AC3 says "case-insensitive substring matching" | Over-spec — AC doesn't require regex |
| Performance | O(n×m) but ~0ms for 40 patterns on typical chunks | Same order with compiled regex |
| Complexity | `phrase in text.lower()` — 1 line | `re.search(pattern, text, re.I)` — needs compilation |
| False positives | Low (precise phrases) | Medium (broader regex groups can over-match) |
| KISS alignment | High | Lower — regex adds complexity without AC requirement |
| PinchTab alignment | Diverges (PinchTab uses regex) | Matches PinchTab |

**Recommendation: Substring matching** (.85). The AC explicitly specifies it. Regex can be added later if needed (YAGNI).

### 3c. Pattern List (~40 substrings from PinchTab categories)

Derived from PinchTab idpishield's 12 categories, simplified to substring form:

| Category | Count | Examples |
|----------|-------|---------|
| Instruction override | 8 | "ignore previous instructions", "disregard your instructions", "forget your instructions", "override your instructions", "ignore the above", "do not follow your", "new instructions:", "stop following your" |
| Role hijack | 7 | "you are now", "pretend you are", "from now on you are", "act as if", "your new identity", "roleplay as", "simulate being" |
| Jailbreak | 7 | "jailbreak", "developer mode", "dan mode", "do anything now", "bypass safety", "bypass the filter", "unrestricted mode" |
| Exfiltration | 6 | "send the data to", "exfiltrate", "leak the data", "send credentials to", "upload to http", "forward to http" |
| Indirect command | 5 | "your new task is", "follow these new rules", "execute the following command", "your real instructions are", "priority override" |
| Social engineering | 4 | "new instructions from the admin", "authorized by the system", "system update:", "security alert:" |
| System prompt extraction | 3 | "repeat your instructions", "what is your system prompt", "reveal your instructions" |
| **Total** | **~40** | |

### 3d. IngestResult.status Change

Current: `Literal["ok", "failed", "skipped", "cancelled"]`
Required: `Literal["ok", "failed", "skipped", "cancelled", "blocked"]`

This is a minor, backward-compatible model change. The `"blocked"` literal is additive — no existing code checks for it, so no breakage. #833 RED tests already assert `status="blocked"`.

### 3e. Integration Point in `ingest()`

Current flow (L185-210):
```
chunks = chunker.chunk(content)  →  should_wrap()  →  extract_coros  →  gather
```

New flow:
```
chunks = chunker.chunk(content)  →  guard.scan(chunk) for untrusted  →  should_wrap()  →  extract_coros  →  gather
```

The guard scan slots in **between** chunking and the extract comprehension. For untrusted sources (`should_wrap() == True`), scan each chunk. On threat detected:
- **Strict mode:** return `IngestResult(status="blocked")` immediately
- **Warn mode:** log warning, continue to wrapping + extraction

Guard instantiation: `ContentInjectionGuard` should be a constructor parameter of `IngestPipeline`, defaulting to `None` (backward-compatible). When `None`, no scanning occurs.

## 4. Recommendation (.88 confidence)

Implement as specified in the ACs. All 7 ACs are directly implementable against current codebase state with no architectural gaps.

Key implementation decisions:
1. Substring matching (not regex) — per AC3
2. ~40 builtin patterns from 7 categories — per AC3 and #724 design
3. `IngestResult.status` gets `"blocked"` literal — per #833 research recommendation
4. Guard is an optional `IngestPipeline` constructor parameter — backward-compatible
5. Scan only untrusted sources via existing `should_wrap()` — per AC5

Challenge: FALLBACK — challenger subagent not available

**Risk:** Pattern matching only catches known phrases. Novel/obfuscated attacks bypass it. This is defense-in-depth (OWASP Strategy #3), not a security boundary. The docstring must state this.

## 5. Follow-up Tasks

No additional follow-up tasks needed. #833 (RED) and #834 (GREEN) compose the full TDD pair under parent #751.
