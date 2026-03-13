# IDPI Content Scanning for Browser Extraction

> **Owning task:** #724 — Add IDPI content scanning to browser content extraction
> **Date:** 2026-03-10 **Status:** Complete

## 1. Context and Question

OwlBear agents browse arbitrary web pages. Extracted text flows directly into LLM context without sanitization. An attacker embedding "ignore previous instructions" in page content could hijack agent behavior. PinchTab's IDPI package demonstrates a lightweight defense: scan extracted text for known injection phrases before returning it. Should OwlBear adopt this, and how?

**Current gap:** OwlBear has `URLSafetyGuard` (domain-level protection) but **no content-level injection scanning**. OWASP LLM01:2025 Prevention Strategy #3 explicitly recommends "string-checking to scan for non-allowed content" and Strategy #6 recommends "segregate and identify external content."

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PinchTab `internal/idpi/content.go` | <https://github.com/pinchtab/pinchtab/tree/main/internal/idpi> | .90 — direct prior art, 26 builtin patterns, CheckResult struct, strict/warn modes |
| PinchTab `internal/idpi/idpi_test.go` | (same repo) | .85 — test patterns for content scanning, edge cases |
| ProtectAI/llm-guard `BanSubstrings` | <https://github.com/protectai/llm-guard> | .75 — substring-matching scanner pattern in Python, configurable deny lists |
| ProtectAI/llm-guard `PromptInjection` | <https://protectai.github.io/llm-guard/input_scanners/prompt_injection/> | .60 — ML-based (DeBERTa), higher accuracy but heavy deps |
| ProtectAI/rebuff (archived) | <https://github.com/protectai/rebuff> | .50 — multi-layer defense (heuristic + LLM + VectorDB + canary), archived May 2025 |
| OWASP LLM01:2025 Prompt Injection | <https://genai.owasp.org/llmrisk/llm01-prompt-injection/> | .85 — authoritative mitigation guidance, cites string-checking and content segregation |
| OwlBear `CommandSafetyGuard` | `src/owlbear/core/command_guard.py` | .90 — existing guard pattern to follow |
| OwlBear `URLSafetyGuard` | `src/owlbear/tools/browser/safety.py` | .90 — existing browser guard pattern |

## 3. Analysis

### 3a. Detection Approach Comparison

| Criterion | Pattern matching (.85) | ML classifier (.60) | Multi-layer (.45) |
|-----------|----------------------|---------------------|-------------------|
| **Deps** | 0 (stdlib only) | transformers + model (~500MB) | openai + vectorDB |
| **Latency** | ~0ms | ~100-300ms | ~500-2000ms |
| **Accuracy** | Medium (known phrases only) | High (novel attacks) | Highest |
| **False positives** | Low (precise phrases) | Medium | Medium |
| **KISS/YAGNI** | High | Low | Very low |
| **Prior art** | PinchTab (Go), LLM Guard BanSubstrings (Python) | LLM Guard PromptInjection | Rebuff (archived) |
| **Fits OwlBear** | Yes — mirrors existing guard pattern | No — heavy deps | No — external services |

### 3b. Integration Point Options

| Option | Where | Mechanism | Pros | Cons |
|--------|-------|-----------|------|------|
| **A. Inline in functions** | `browser_read_text`, `extract_content` | Call guard directly after text extraction | Simple, KISS, no infra changes | Guard logic coupled to browser tools |
| **B. POST_TOOL_USE hook** | `HookedToolset` | Scan tool result after execution | Reusable hook pattern | Exceptions swallowed by HookRegistry — can't block |
| **C. Post-guard in HookedToolset** | New `post_guards` field | Run after tool, before return | Clean architecture | Requires HookedToolset changes |

**Recommendation: Option A** (.85 confidence). The guard class is standalone and testable. Integration is 2-3 lines in each function. This matches KISS — no infrastructure changes needed. The guard class itself is reusable if a post-guard pattern is added later.

### 3c. CheckResult Design

Follow PinchTab's struct exactly — it's clean and sufficient:

```
CheckResult(threat: bool, blocked: bool, reason: str, pattern: str)
```

- `threat=True` when any pattern matches (always set on match)
- `blocked=True` only in strict mode (tool returns warning instead of content)
- `blocked=False` in warn mode (content returned, warning logged)
- `reason` — human-readable message (e.g., "possible prompt injection detected: 'ignore previous instructions'")
- `pattern` — the matched phrase string

### 3d. Pattern List Strategy

PinchTab has 26 builtin patterns. The task AC says "~40 builtin." The builder should expand PinchTab's list to ~40 by adding patterns for:

- **Role hijacking:** "from now on you are", "roleplay as", "developer mode", "jailbreak"
- **Instruction override:** "do not follow your", "bypass your", "override your programming"
- **System prompt extraction:** "repeat your instructions", "what are your instructions", "what is your system prompt"
- **Data exfiltration:** "send the data to", "upload to", "transfer to"

All patterns should be lowercase, matched case-insensitively via `text.lower()`. Custom patterns should be configurable (like PinchTab's `CustomPatterns`).

### 3e. Configuration

Add to `BrowserConfig` (Pydantic model, already handles URL lists):

- `idpi_scan_content: bool = False` — opt-in, disabled by default (matches PinchTab)
- `idpi_strict_mode: bool = False` — block vs warn
- `idpi_custom_patterns: list[str] = []` — user-supplied patterns

Keep IDPI disabled by default so existing behavior is unchanged.

## 4. Recommendation (.90 confidence)

**Adopt PinchTab's pattern-matching approach** with these specifics:

1. **New module:** `src/owlbear/tools/browser/content_guard.py` (alongside `safety.py`)
2. **Standalone class:** `ContentInjectionGuard` with `scan(text) -> CheckResult`
3. **~40 builtin patterns:** Start from PinchTab's 26, expand per 3d above
4. **Config-driven:** Add `idpi_*` fields to `BrowserConfig`
5. **Integration:** Call `guard.scan()` in `browser_read_text` and `extract_content` return paths
6. **Strict mode:** Return `"BLOCKED: {reason}"` instead of content
7. **Warn mode:** Log warning, return content unchanged

**Not recommended:**

- ML-based detection — violates KISS/YAGNI, adds ~500MB model dependency
- Multi-layer (Rebuff-style) — requires external services, project archived
- POST_TOOL_USE hook approach — exceptions swallowed, can't enforce blocking

**Risk:** Pattern matching only catches known phrases. Novel/obfuscated attacks bypass it. This is defense-in-depth (like `CommandSafetyGuard`'s blocklist), not a security boundary. The docstring should state this explicitly.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement ContentInjectionGuard class" --priority needed --status backlog --tag phase-browser --tag scope:core --tag security --body "Implement ContentInjectionGuard in src/owlbear/tools/browser/content_guard.py.\n\n**Source:** docs/research/idpi-content-scanning-research.md\n\n**AC:**\n- [ ] ContentInjectionGuard class with scan(text) -> CheckResult method\n- [ ] CheckResult dataclass with threat, blocked, reason, pattern fields\n- [ ] ~40 builtin injection patterns (case-insensitive substring matching)\n- [ ] Configurable custom_patterns list\n- [ ] Configurable strict_mode (block) vs warn mode (log)\n- [ ] Disabled by default (opt-in)\n- [ ] Defense-in-depth disclaimer in docstring\n- [ ] Unit tests: known injection phrases detected, clean content passes, case-insensitive, custom patterns, strict/warn modes, empty text"
```

```
kanban\kanban-md.exe create "Integrate ContentInjectionGuard into browser extraction paths" --priority needed --status backlog --tag phase-browser --tag scope:core --tag security --body "Wire ContentInjectionGuard into browser_read_text and extract_content output paths.\n\n**Source:** docs/research/idpi-content-scanning-research.md\n**Depends on:** ContentInjectionGuard class task\n\n**AC:**\n- [ ] browser_read_text scans output through ContentInjectionGuard before returning\n- [ ] extract_content scans extraction.text through ContentInjectionGuard before returning\n- [ ] Add idpi_scan_content, idpi_strict_mode, idpi_custom_patterns to BrowserConfig\n- [ ] Strict mode: return 'BLOCKED: {reason}' instead of content\n- [ ] Warn mode: log warning, return content unchanged\n- [ ] Integration tests with mocked page content containing injection phrases\n- [ ] Existing browser tests still pass (IDPI disabled by default)"
```

## 6. Relationship to #725

Task #725 (untrusted content wrapping) is complementary — it wraps content in `<untrusted_web_content>` delimiters. Content scanning (#724) detects threats; wrapping (#725) marks all web content as untrusted. Both should be wired into the same extraction paths. The wrapping should apply **after** scanning (scan raw text, then wrap the result).
