---
name: session-review
description: "Review another local Copilot chat by session ID, marker, or summary. Use for cross-session review, agent workflow audits, gate checks, and verification of claims from persisted chat history."
argument-hint: "Session ID or marker; optional review focus or gate"
user-invocable: true
disable-model-invocation: false
---

# Session Review

Review another persisted Copilot session without treating its narrative as current authority.

## Step 1 - Locate One Session

Use the local Copilot session store to search summaries, user and assistant turns, checkpoints,
files, and references. Prefer an exact session ID. Otherwise combine the supplied marker with the
current workspace and recency. State the selected session ID and do not silently choose between
plausible matches.

The session store is the primary source for discovery and compact orientation. Query ordered turns,
the latest checkpoint, referenced files, and commit references before opening raw logs.

Use the store's actual SQLite columns; do not invent generic names such as `title`,
`workspace_path`, or `content`:

| Table | Review columns |
| --- | --- |
| `sessions` | `id`, `cwd`, `repository`, `branch`, `summary`, `agent_name`, `created_at`, `updated_at` |
| `turns` | `session_id`, `turn_index`, `user_message`, `assistant_response`, `timestamp` |
| `checkpoints` | `session_id`, `checkpoint_number`, `title`, summary fields, `created_at` |
| `session_files` | `session_id`, `file_path`, `tool_name`, `turn_index`, `first_seen_at` |
| `session_refs` | `session_id`, `ref_type`, `ref_value`, `turn_index`, `created_at` |

Start candidate discovery with `sessions.cwd`, `sessions.summary`, and `sessions.updated_at`; search
`turns.user_message` and `turns.assistant_response` when the marker is absent from the summary. Once
selected, query `turns` by `session_id ORDER BY turn_index` and each supporting table separately.
Use the latest timestamp actually present across the selected session row, turns, and checkpoint;
`sessions.updated_at` alone may not identify the latest persisted event.

## Step 2 - Extract Full Evidence When Needed

Indexed assistant responses can be truncated. When the index omits material context, run the bundled
[transcript extractor](./scripts/extract_transcript.py):

```shell
uv run python .github/skills/session-review/scripts/extract_transcript.py \
  --session-id <session-id> --last-turns 12 --include-tools --format markdown
```

Useful narrowing options:

- `--around <text> --context-turns 2` selects matching whole turns and nearby turns.
- `--around-event <text>` keeps only matching messages, nested prompts, and tool calls inside the
  selected turns. Use it for orchestration sessions whose entire nested execution occupies one turn.
- `--from-turn N --to-turn N` selects a stable one-based turn range.
- `--include-tool-arguments` includes redacted, bounded tool inputs when names alone are insufficient.
- `--transcript <path>` reads an explicit log when automatic session lookup is unavailable.
- `--format json` returns structured output for further analysis.

The extractor streams JSONL, omits model reasoning, redacts likely secrets, bounds content, and does
not write files. Nested agent prompts and responses remain inside their owning top-level turn. Tool
completion records expose a tool-layer completion flag but not result bodies. `success: true` does
not prove a shell exit code, test result, commit, subagent claim, or MCP domain mutation. Verify each
consequential result against its current owner or rerun a read-only proof. If
`incomplete_tool_calls` is non-empty, treat the raw tail as unresolved: compare it with the indexed
turn and verify consequential outcomes against their owning current artifact or public boundary.
Never infer success or failure from a requested or started tool that lacks a completion record.

## Step 3 - Reconstruct The Reviewed Claim

Read enough ordered turns to identify the session's intent, actions, unresolved questions, and
claimed result. Separate:

- **Observed then:** persisted session messages and tool events.
- **Verified now:** current files, Git identities and diffs, tests, application state, or public tool
  results that own the claim.
- **Unresolved:** truncated, stale, ambiguous, or unavailable evidence.

Do not claim continuous monitoring. Review only turns and artifacts that have been persisted. If the
session is active, identify its latest durable point and keep consequential unresolved gates paused.

## Step 4 - Return A Decision

```markdown
## Session Review

- Session: <exact ID and latest persisted timestamp>
- Focus: <reviewed decision, gate, claim, or behavior>
- Verdict: proceed | revise | stop

### Findings

<Highest-severity findings first, each with session and current-workspace evidence.>

### Evidence Limits

<Missing, truncated, stale, or unverified evidence; "None" when fully resolved.>

### Next Action

<One concrete action for the reviewed session.>
```

Use `proceed` only when the reviewed claim and its current owning evidence agree. Use `revise` for a
bounded correctable gap. Use `stop` for conflicting authority, unsafe mutation, an invalid gate, or
insufficient evidence for a consequential action.

## Known Pitfalls

- **Summary substitution:** summaries orient discovery but do not replace ordered turns.
- **Transcript authority:** chat records prove what was said or attempted, not current repository or
  runtime truth.
- **Incomplete raw tail:** unresolved tool calls require indexed-tail and current-owner verification;
  neither source silently substitutes for the missing raw events.
- **Tool completion substitution:** a completed tool event is not its absent output. Verify command
  exit, mutation, and domain result elsewhere.
- **Unbounded extraction:** select recent, ranged, or matching turns; use `--around-event` when one
  top-level turn still contains a large nested run.
- **Identity overstatement:** inspect refs and ancestry before calling preserved commits distinct
  candidates; recovery may preserve an existing source head.
- **Argument exposure:** include tool arguments only when needed; redaction reduces but cannot remove
  every disclosure risk.
