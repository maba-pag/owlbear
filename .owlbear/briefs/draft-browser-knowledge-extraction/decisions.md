# Authenticated Content Pipeline — Decisions

## Investment Tier: Production

**Rationale:** Mission-critical capability. The knowledge DB's quality determines whether OwlBear can produce work that meets corporate standards. All domain opinions, extended research, full depth.

## D1: HTML Cleaning + Hash Fix — Ship Together
Parallel tracks: browser infrastructure + pipeline quality fixes (HTML cleaner, hash-on-cleaned-content) converge at first authenticated ingestion. No graph corruption from day one.

## D2: Browser Tool Surface — Full Tools, Single Surface
Full interactive tool set (navigate, click, type, select, read_text, snapshot). Trust the user approval gate. No artificial split between discovery and extraction tools. Simpler architecture.

## D4: URL Guard Enforcement — Tool-Level
URL allowlist enforcement at tool implementation level, not via HookRegistry hooks (which swallow exceptions). Non-negotiable per ideation-security finding.

## D5: New Pages During Refresh — Queue for Re-Approval
New pages discovered during refresh are queued for explicit user approval before ingestion. More conservative than auto-include, but consistent with user-as-gate principle.
