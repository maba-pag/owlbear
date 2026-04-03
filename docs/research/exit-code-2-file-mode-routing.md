# Exit Code 2 Routing via `-File` Invocation in Subagent Context

> **Owning task:** #548 — Verify exit code 2 routing via -File invocation in subagent context
> **Date:** 2026-04-02 **Status:** Theoretical complete, empirical pending

## 1. Context and Question

Task #532 found that exit code 2 via `powershell -Command` one-liners was
classified as NonBlockingError (not model-facing) by the VS Code hooks engine.
However, #210 uses `powershell -File` which has different exit code semantics.
Does `-File` mode correctly propagate exit code 2 so the hooks engine classifies
it as BlockingError (model-facing)?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| MS PS 5.1 about_PowerShell_exe | learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_powershell_exe | .95 — canonical exit code behavior for -File vs -Command |
| VS Code Hooks docs (4/2/2026) | code.visualstudio.com/docs/copilot/customization/hooks | .95 — exit code classification spec |
| OwlBear #532 empirical results | docs/research/posttooluse-subagent-output-routing.md | 1.0 — -Command NonBlockingError finding |
| OwlBear #210 feasibility | docs/research/posttooluse-lint-guard-feasibility.md s6 | 1.0 — -File untested qualification |

## 3. Analysis

### 3.1 Root Cause of #532's NonBlockingError Finding

Microsoft PS 5.1 docs for `-Command` mode state:

> "The exit code is `0` when `$?` is `$true` or `1` when `$?` is `$false`.
> If the last command [...] explicitly sets an exit code other than `0` or `1`,
> that exit code is **converted to `1`**."

So `exit 2` inside `-Command` becomes process exit code 1. The hooks engine
sees exit code 1 (not 2) and classifies it as "Other" → NonBlockingError.

For `-File` mode, the docs state:

> "When the script file terminates with an `exit` command, the process exit
> code is set to the numeric argument used with the `exit` command."

So `exit 2` inside a `.ps1` script invoked via `-File` should become process
exit code 2.

### 3.2 Predicted Classification Chain

| Mode | Script runs | PS process exit | Hooks engine sees | Classification |
|------|------------|----------------|-------------------|----------------|
| `-Command` | `exit 2` | 1 (converted) | 1 | NonBlockingError |
| `-File` | `exit 2` | 2 (preserved) | 2 (predicted) | BlockingError (predicted) |

### 3.3 Risk: Hooks Engine Spawn Intermediary

The prediction assumes the hooks engine reads the PowerShell process exit code
directly. If the hooks engine uses `cmd.exe /c` wrapping (Node.js `exec()`
default on Windows), the propagation chain becomes:

`.ps1 exit 2` → `powershell.exe` exit 2 → `cmd.exe` → Node.js

`cmd.exe /c` generally preserves `%ERRORLEVEL%` from child processes, but edge
cases exist. Without inspecting the hooks engine source (in the copilot-chat
extension), this intermediary cannot be ruled out.

### 3.4 Risk: Hooks Engine Internal Classification

The #532 causal attribution (PS 5.1 `-Command` converts exit codes) is inferred
from documentation, not empirically proven. An alternative explanation: the hooks
engine internally has its own exit code mapping that produces NonBlockingError
for certain conditions. If so, switching to `-File` mode may not change the
classification.

### 3.5 Track Record on Docs-Based Predictions

| Task | Prediction | Outcome |
|------|-----------|---------|
| #209 | systemMessage reaches subagent model | Empirically false |
| #532 | Exit code 2 = BlockingError (model-facing) | Empirically NonBlockingError |
| #548 | Exit code 2 via -File = BlockingError | **Pending verification** |

## 4. Recommendation (.60 confidence)

**Prediction: `-File` mode will produce BlockingError classification.** The PS 5.1
documentation clearly distinguishes exit code behavior between modes, and the
`-Command` conversion to exit code 1 fully explains #532's finding. However:

- .60 (not higher) because of 0-for-2 track record on docs-based hook predictions
- Hooks engine spawn mechanism (shell wrapping, internal mapping) is uninvestigated
- Causal attribution of #532 is inferred, not empirically isolated

Empirical verification via user action request is required before updating any
downstream design assumptions.

Challenge: reconsider (.55 confidence in original). Accepted C1 (hooks engine
spawn intermediary), C2 (causal attribution assumed), C3 (lowered from .85 to
.60). Rebutted A3 partially (understanding mechanisms has architectural value
even if no current task depends on exit code 2).

## 5. Follow-up Tasks

Action request created: `docs/decisions/pending/548-exit-code-2-file-verification.md`

No kanban follow-up tasks until empirical results are available. Downstream
actions depend on the outcome:
- BlockingError confirmed → update routing doc, note exit code 2 viable via -File
- NonBlockingError → investigate hooks engine spawn mechanism or close the avenue
