# Command Guard Blocklist — Limitations and Expansion

> **Owning task:** #494 — Expand command guard blocklist and document limitations
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

SEC-04 from `docs/security-audit.md` identifies that `DEFAULT_BLOCKED_COMMANDS` regex patterns in `src/owlbear/core/command_guard.py` are fundamentally bypassable. The audit lists specific bypass vectors: `rm -r -f /`, `git push -f`, `python -m pip install`, PowerShell equivalents, base64 encoding, and environment variable expansion.

**Question:** What patterns should be expanded, and how should the blocklist be documented relative to the overall security architecture?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Claude Code — Security docs | <https://code.claude.com/docs/en/security> | .90 — Production AI coding agent with layered security |
| 2 | Claude Code — Sandboxing docs | <https://code.claude.com/docs/en/sandboxing> | .85 — OS-level sandbox as primary control |
| 3 | Claude Code — Permissions docs | <https://code.claude.com/docs/en/permissions> | .85 — Permission rules + explicit bypass warnings |
| 4 | OpenAI Codex CLI — README | <https://github.com/openai/codex/blob/main/codex-cli/README.md> | .80 — Approval modes + OS sandbox, no command blocklist |
| 5 | Docker seccomp profiles | <https://docs.docker.com/engine/security/seccomp/> | .70 — Allowlist approach at syscall level |
| 6 | OwlBear security-audit.md (SEC-04) | Local: `docs/security-audit.md` | 1.0 — Primary finding driving this work |

## 3. Analysis

### 3.1 How other tools handle command safety

| System | Primary Control | Secondary Control | Uses Blocklist? |
|--------|----------------|-------------------|-----------------|
| Claude Code | OS sandbox (Seatbelt/bubblewrap) | Permission rules + approval prompts | Yes — blocks `curl`, `wget` by default; warns patterns are "fragile" |
| OpenAI Codex CLI | OS sandbox (`sandbox-exec`/Docker) | 3-tier approval mode (Suggest/Auto Edit/Full Auto) | No — relies entirely on sandbox + approval |
| Docker | seccomp allowlist (kernel-enforced) | Capability restrictions (CAP_*) | No — allowlist, not blocklist |
| OwlBear (current) | Approval gate (`run_command` gated) | Regex command blocklist | Yes — 6 patterns |

**Key finding from Claude Code docs** (Source 3): *"Bash permission patterns that try to constrain command arguments are fragile."* They explicitly document this limitation and use OS-level sandboxing as the real boundary.

**Key finding from Codex CLI** (Source 4): Does not use any command blocklist. In Full Auto mode, relies on network-disabled sandbox + working directory confinement.

### 3.2 Defense-in-depth framing

OwlBear's security for shell execution has three layers:

| Layer | Control | Bypassable? | Status |
|-------|---------|-------------|--------|
| 1 (Primary) | Approval gate — `run_command` requires user approval | No — human decides | Active (`config.py` L170) |
| 2 (Secondary) | Working dir confinement — `is_relative_to` check | Difficult — path traversal guarded | Active (copilot-instructions.md) |
| 3 (Tertiary) | Regex blocklist — catches obvious dangerous commands | Yes — trivially | Active but incomplete |

The blocklist is Layer 3: a speed bump that catches accidental or naive dangerous commands. It is **not a security boundary** — it cannot prevent a determined or manipulated LLM from expressing the same operation differently.

### 3.3 Bypass categories the blocklist cannot address

| Category | Example | Why unfixable by regex |
|----------|---------|----------------------|
| Encoding | `echo cm0gLXJmIC8K \| base64 -d \| bash` | Infinite encoding schemes |
| Indirection | `python -c "import shutil; shutil.rmtree('/')"` | Any interpreter can execute destructive ops |
| Variable expansion | `CMD="rm"; $CMD -rf /` | Shell resolves variables before exec |
| Aliasing | `alias r='rm -rf'; r /` | Shell aliases invisible to static regex |
| Chaining | `echo hi && rm -rf /` | After `&&` or `;`, anything goes |

### 3.4 Expanded patterns — what CAN be improved

Despite being fundamentally bypassable, expanding patterns catches the **common variations** that an LLM might generate without deliberate evasion. The current 6 patterns miss obvious variants.

| Current Pattern | Bypass Vector | Proposed Fix |
|----------------|---------------|-------------|
| `rm\s+-rf\s+/` | `rm -r -f /`, `rm -Rf /`, `rm -fr /` | Catch any combo of `-r`/`-f` flags |
| `git\s+push\s+--force` | `git push -f` | Add `-f` short flag |
| `pip\s+install` (w/ lookbehind) | `python -m pip install` | Add `python -m pip` pattern |
| `del\s+/[sS]\s+/[qQ]` | `del /Q /S` (reversed order) | Match both orderings |
| (missing) | `Remove-Item -Recurse -Force` | Add PowerShell equivalent |
| (missing) | `find / -delete` | Add find-delete pattern |
| (missing) | `mkfs.`, `dd of=/dev/` | Add disk-destructive commands |
| (missing) | `git push --force-with-lease` | Cover force-with-lease variant |

### 3.5 False positive risk assessment

| Proposed Pattern | False Positive Risk | Mitigation |
|-----------------|--------------------|----|
| `rm` with `-r` and `-f` near `/` | Low — legitimate `rm -rf /tmp/build` is fine if path isn't bare `/` | Anchor to `\s+/\s*$` or `\s+/[^a-zA-Z]` |
| `git push -f` | Low — `-f` is always force-push | None needed |
| `python -m pip install` | Low — uv should always be used | None needed |
| `Remove-Item.*-Recurse.*-Force` | Medium — legitimate PS cleanup | Only match when targeting system roots |
| `mkfs\.` | Very low — never legitimate in dev context | None needed |
| `dd.*of=/dev/` | Very low — never legitimate in dev context | None needed |

## 4. Recommendation (.85 confidence)

1. **Expand patterns** to cover the bypass vectors in §3.4 — bringing the list from 6 to ~14 patterns. This catches LLM-generated "obvious" variations without over-engineering.

2. **Add module-level docstring** to `command_guard.py` explicitly documenting:
   - The blocklist is defense-in-depth (Layer 3), not a security boundary
   - The primary control is the approval gate (Layer 1)
   - Known bypass categories that regex cannot address
   - Reference to SEC-04 in `docs/security-audit.md`

3. **Do NOT** add:
   - Base64 detection (too many false positives, easily varied)
   - Shell chaining detection (requires parsing, not regex)
   - OS-level sandboxing (separate large initiative — future task)

This aligns with KISS (simple pattern expansion, not a shell parser) and YAGNI (the approval gate is the real control; the blocklist just needs to be better, not perfect).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Expand DEFAULT_BLOCKED_COMMANDS patterns to cover common bypass variants" --priority needed --tags "security,scope:core" --body "Expand from 6 to ~14 patterns per docs/command-guard-blocklist-research.md §3.4. Add: rm flag combos (-r -f, -fr, -Rf, --recursive --force), git push -f, python -m pip install, Remove-Item -Recurse -Force, find / -delete, mkfs., dd of=/dev/, git push --force-with-lease, del flag ordering. Update tests to cover new patterns + verify no false positives on safe commands. AC: all patterns from §3.4 implemented, tests green, no false positives on existing safe-command test list."

kanban\kanban-md.exe create "Add defense-in-depth documentation to command_guard.py module docstring" --priority needed --tags "security,docs,scope:core" --body "Add module-level docstring per docs/command-guard-blocklist-research.md §4.2. Document: blocklist is Layer 3 defense-in-depth not a security boundary, primary control is approval gate, known bypass categories (encoding, indirection, variables, aliasing, chaining), reference SEC-04. AC: docstring present, clearly states 'not a security boundary', lists bypass categories."
```
