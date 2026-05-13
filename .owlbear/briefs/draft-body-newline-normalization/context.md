# Context — Body Newline Normalization

## Problem Snapshot

LLM agents frequently double-escape newlines in MCP tool call JSON arguments, sending `\\n` (which JSON deserializes to the literal two-character string `\n`) instead of `\n` (actual newline). This corrupts markdown body content in kanban task files — bodies contain literal `\n` instead of actual line breaks.

The problem is **ongoing** (visible in active tasks, not just archive). It cannot be fixed upstream because LLM tool-calling serialization behavior is non-deterministic.

**Primary impact:** Search and grep (especially regex) break on literal `\n` in task bodies — patterns designed for newline-delimited markdown content fail to match.

**Secondary impact:** Reduced readability for human users viewing task files directly (minor).

**Non-impact:** Agents likely interpret the escaped sequences as intended line breaks anyway — agent comprehension is not degraded.

## Active Tension

A naive `text.replace("\\n", "\n")` has a **false-positive problem**: task bodies that discuss escape sequences, regex patterns, or code behavior (including *this very task*) contain legitimate literal `\n` that should be preserved. The two cases are indistinguishable at the string level.

**Resolution approach:** Normalize-and-notify. Always replace, but inform the agent via the existing `guidance` response field that normalization occurred. The agent can retry with triple-escaping if the literal was intentional. False positives become recoverable rather than silent corruption.

## Outcomes (locked)

- All text body fields normalized at MCP ingress — search/grep works against task files as expected
- When normalization occurs, guidance informs the agent (uses existing `SingleTaskResponse.guidance` infrastructure)
- Agent has a documented escape path for intentional literal `\n` (triple-escape or alternative encoding)
- MCP server layer only — engine and storage untouched
- Prevention only — existing corrupted files out of scope

## Scope

Prevention only: normalize text inputs at the MCP server ingress boundary. No archive remediation.

## Affected Surface

Single file: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
Affected parameters: `body` in `create_task`/`edit_task`, `append_body` in `edit_task`, `note` in `end_work`, `body` in `create_dr`.

## Project Type

existing-feature/refactor
